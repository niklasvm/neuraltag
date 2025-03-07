import datetime
import json
import logging
import os

from dotenv import load_dotenv
import pandas as pd

import requests
from stravalib import Client

from src.data import (
    fetch_activity_data,
    fetch_historic_activity_data,
    process_activity,
)

from src.gemini import generate_activity_name_with_gemini
from pushbullet import Pushbullet
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def login_user(code: str, scope: str) -> int | None:
    """Exchanges a Strava authorization code for an access token, retrieves the athlete's information, and stores the authentication details and athlete data in a database.
    Args:
        code (str): The Strava authorization code received from the user.
        scope (str): The scope of the authorization.
    """

    # load_dotenv(override=True)

    # exchange code for token
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        code=code,
    )
    access_token = token_response["access_token"]

    token_response["STRAVA_CLIENT_ID"] = os.environ["STRAVA_CLIENT_ID"]
    token_response["STRAVA_CLIENT_SECRET"] = os.environ["STRAVA_CLIENT_SECRET"]

    with open("token.json", "w") as f:
        json.dump(token_response, f)

    # get athlete
    client.access_token = access_token
    athlete = client.get_athlete()

    return athlete.id


def rename_workflow(activity_id: int):
    time_start = datetime.datetime.now()

    load_dotenv(override=True)

    days = 365
    temperature = 2

    gemini_named_description = "automagically named with Gemini 🤖"

    token = json.loads(os.environ["STRAVA_TOKEN"])
    for key, value in token.items():
        os.environ[key] = str(value)

    client = Client(
        access_token=os.environ["access_token"],
        refresh_token=os.environ["refresh_token"],
        token_expires=os.environ["expires_at"],
    )
    client.refresh_access_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        refresh_token=os.environ["refresh_token"],
    )

    activity = fetch_activity_data(
        client=client,
        activity_id=activity_id,
    )

    if (
        gemini_named_description in str(activity.description)
        and activity.name != "Rename"
    ):
        logger.info(f"Activity {activity_id} already named with Gemini 🤖")
        return

    before = activity.start_date_local + datetime.timedelta(days=1)
    after = before - datetime.timedelta(days=days)
    activities = fetch_historic_activity_data(
        client=client,
        after=after,
        before=before,
    )

    activity = process_activity(activity)
    activities = [process_activity(x) for x in activities]

    activities_df = pd.DataFrame(activities)

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
        "pace_min_per_km",
        "map_centroid_lat",
        "map_centroid_lon",
        "map_area",
    ]

    activities_df = activities_df[activities_df["sport_type"] == activity["sport_type"]]
    activities_df = activities_df[columns]
    activities_df = activities_df.dropna(axis=1, how="all")

    name_results = generate_activity_name_with_gemini(
        activity_id=activity_id,
        data=activities_df,
        number_of_options=3,
        api_key=os.environ["GEMINI_API_KEY"],
        temperature=temperature,
    )
    logger.info(f"Name suggestions: {name_results}")

    top_name_suggestion = name_results[0].name
    top_name_description = name_results[0].description
    logger.info(
        f"Top name suggestion for activity {activity_id}: {top_name_suggestion}"
    )

    time_end = datetime.datetime.now()
    duration_seconds = (time_end - time_start).total_seconds()
    logger.info(f"Duration: {duration_seconds} seconds")
    client.update_activity(
        activity_id=activity_id,
        name=top_name_suggestion,
        description=gemini_named_description,
    )

    # notify via pushbullet
    pb = Pushbullet(os.environ["PUSHBULLET_API_KEY"])
    pb.push_note(title=top_name_suggestion, body=top_name_description)


def trigger_gha(inputs: dict) -> None:
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

    data = {
        "ref": f"{REF}",
        "inputs": inputs,
    }

    response = requests.post(ENDPOINT, headers=headers, json=data)

    if response.status_code == 204:
        print("Workflow dispatch triggered successfully.")
    else:
        print(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )
        raise requests.exceptions.RequestException(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )


if __name__ == "__main__":
    # get arg from command line

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--activity_id", type=int, required=True, help="Strava activity ID"
    )
    args = parser.parse_args()

    rename_workflow(activity_id=args.activity_id)
