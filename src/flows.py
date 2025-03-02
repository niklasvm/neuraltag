import datetime
import logging
import os

from dotenv import load_dotenv
import pandas as pd
import requests
from stravalib import Client

from src.data.db import StravaDatabase

from src.data.models import NameSuggestion
from src.gemini import generate_activity_name_with_gemini
from pushbullet import Pushbullet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def login_user(code: str, scope: str) -> int | None:
    """Exchanges a Strava authorization code for an access token, retrieves the athlete's information, and stores the authentication details and athlete data in a database.
    Args:
        code (str): The Strava authorization code received from the user.
        scope (str): The scope of the authorization.
    """

    load_dotenv()

    # exchange code for token
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        code=code,
    )
    access_token = token_response["access_token"]
    refresh_token = token_response["refresh_token"]
    expires_at = token_response["expires_at"]

    # get athlete
    client.access_token = access_token
    athlete = client.get_athlete()

    # add auth
    connection_string = os.environ["DB_CONNECTION_STRING"]

    # add athlete
    db = StravaDatabase(connection_string)

    # add auth
    db.add_auth(athlete.id, access_token, refresh_token, expires_at, scope)
    db.add_athlete(athlete)

    return athlete.id


def new_activity_created_workflow(athlete_id: int, activity_id: int):
    load_dotenv(override=True)

    db = StravaDatabase(connection_string=os.environ["DB_CONNECTION_STRING"])

    # add activity
    token = db.get_auth(athlete_id)
    client = Client(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        token_expires=token.expires_at,
    )
    client.refresh_access_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        refresh_token=token.refresh_token,
    )

    activity = client.get_activity(activity_id=activity_id)
    db.add_activity(activity)

    # query name suggestions
    query_name_suggestions_for_activity(
        athlete_id=athlete_id, activity_id=activity_id, days=365
    )

    # get name with highest probability field valiue
    name_suggestions = (
        db.session.query(NameSuggestion)
        .filter(NameSuggestion.activity_id == activity_id)
        .all()
    )
    name_suggestions = sorted(
        name_suggestions, key=lambda x: x.probability, reverse=True
    )
    top_name_suggestion = name_suggestions[0]
    logger.info(
        f"Top name suggestion for activity {activity_id}: {top_name_suggestion.name}"
    )

    # update strava activity name
    description = "automagically named with Gemini 🤖"
    if activity.description is None or activity.description not in description:
        client.update_activity(
            activity_id=activity_id,
            name=top_name_suggestion.name,
            description=description,
        )

        # notify via pushbullet
        pb = Pushbullet(os.environ["PUSHBULLET_API_KEY"])
        pb.push_note(
            title=top_name_suggestion.name, body=top_name_suggestion.description
        )
    else:
        logger.info(f"Activity {activity_id} already named with Gemini 🤖")


def load_all_historic_activities(
    athlete_id: int, after: datetime.datetime, before: datetime.datetime
):
    """Loads activities from Strava for a given athlete and number of days.

    It retrieves the latest activity date from the database, fetches activities from Strava
    since that date (or a specified number of days if no activities exist in the DB),
    and saves the new activities to the database.

        Args:
            athlete_id (int): The ID of the athlete.
            days (int): The number of days to load activities for.
    """
    load_dotenv()
    db = StravaDatabase(connection_string=os.environ["DB_CONNECTION_STRING"])
    token = db.get_auth(athlete_id)

    client = Client(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        token_expires=token.expires_at,
    )
    client.refresh_access_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        refresh_token=token.refresh_token,
    )

    activities = client.get_activities(after=after, before=before)
    activities = [x for x in activities]
    logger.info(f"Number of activities to load: {len(activities)}")

    db.add_activities(activities)

    return len(activities)


def query_name_suggestions_for_activity(athlete_id: int, activity_id: int, days: int):
    """Generates activity name suggestions using a Gemini model and stores them in the database.

    Args:
        athlete_id (int): The ID of the athlete.
        activity_id (int): The ID of the activity to generate name suggestions for.
        days (int): The number of past days to consider for similar activities.
    """
    load_dotenv(override=True)

    db = StravaDatabase(connection_string=os.environ["DB_CONNECTION_STRING"])
    activity = db.get_activity(activity_id=activity_id)

    # cancel if activity already has name suggestions
    if activity.name_suggestions:
        logger.info(f"Activity {activity_id} already has name suggestions")
        return

    # prepare context data
    after = activity.start_date - datetime.timedelta(days=days)
    activities = db.get_activities(athlete_id=athlete_id, after=after)

    activities_df = pd.DataFrame([x.to_dict() for x in activities])
    columns = [
        "id",
        "date",
        "time",
        "day_of_week",
        "name",
        "average_heartrate",
        "max_heartrate",
        "total_elevation_gain",
        "weighted_average_watts",
        "moving_time_minutes",
        "distance_km",
        "sport_type",
        "start_lat",
        "start_lng",
        "end_lat",
        "end_lng",
        "map_centroid_lat",
        "map_centroid_lon",
        "map_area",
    ]
    activities_df = activities_df[columns]
    activities_df = activities_df[activities_df["sport_type"] == activity.sport_type]
    activities_df = activities_df.dropna(axis=1, how="all")

    # query api
    name_results = generate_activity_name_with_gemini(
        activity_id=activity_id,
        data=activities_df,
        number_of_options=3,
        api_key=os.environ["GEMINI_API_KEY"],
    )

    # add name suggestions to the database
    for result in name_results:
        logger.info(f"Adding name suggestion for activity {activity_id}: {result.name}")
        db.add_name_suggestion(
            activity_id=activity_id,
            name=result.name,
            description=result.description,
            probability=result.probability,
        )


def trigger_gha():
    """Triggers a GitHub Actions workflow dispatch.

    This function retrieves necessary environment variables (GITHUB_USER, REPO,
    GITHUB_PAT, WORKFLOW_FILE) and uses them to construct the API endpoint for
    triggering a workflow dispatch. It then sends a POST request to the GitHub API
    with the required headers and data to initiate the workflow run.  The function
    checks the response status code and prints a success or failure message
    accordingly.

    Raises:
        KeyError: If any of the required environment variables are not set.
        requests.exceptions.RequestException: If the API request fails.
    """
    load_dotenv(override=True)

    GITHUB_USER = os.environ.get("GITHUB_USER")
    REPO = os.environ.get("REPO")
    GITHUB_PAT = os.environ.get("GITHUB_PAT")
    WORKFLOW_FILE = os.environ.get("WORKFLOW_FILE")
    ENDPOINT = f"https://api.github.com/repos/{GITHUB_USER}/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    REF = "master"

    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    data = {"ref": f"{REF}"}

    response = requests.post(ENDPOINT, headers=headers, json=data)

    if response.status_code == 204:
        print("Workflow dispatch triggered successfully.")
    else:
        print(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )


if __name__ == "__main__":
    new_activity_created_workflow(athlete_id=1411289, activity_id=13630433447)
    # query_name_suggestions_for_activity(athlete_id=1411289, activity_id=2156152415,days=365)
