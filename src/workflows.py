import datetime
import logging
import os

from dotenv import load_dotenv
import pandas as pd

from stravalib import Client

from src.data import (
    fetch_activity_data,
    fetch_historic_activity_data,
    process_activity,
)

from src.app.db.adapter import Database
from src.gemini import generate_activity_name_with_gemini
from pushbullet import Pushbullet

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def login_user(code: str, scope: str):
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

    # get athlete
    client.access_token = access_token
    athlete = client.get_athlete()

    db = Database(os.environ["POSTGRES_CONNECTION_STRING"])
    db.add_athlete(athlete)
    db.add_auth(
        access_token=access_token,
        athlete_id=athlete.id,
        refresh_token=token_response["refresh_token"],
        expires_at=token_response["expires_at"],
        scope=scope,
    )

    return athlete


def rename_workflow(
    activity_id: int,
    access_token: str,
    refresh_token: str,
    expires_at: int,
    client_id: int,
    client_secret: str,
):
    time_start = datetime.datetime.now()

    load_dotenv(override=True)

    days = 365
    temperature = 2

    gemini_named_description = "automagically named with Gemini 🤖"

    client = Client(
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires=expires_at,
    )
    client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
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
