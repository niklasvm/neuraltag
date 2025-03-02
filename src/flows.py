import datetime
import logging
import os

from dotenv import load_dotenv
import pandas as pd
from stravalib import Client

from src.data.db import StravaDatabase

from src.gemini import generate_activity_name_with_gemini

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


def auto_name_activity(athlete_id: int, activity_id: int, days: int):
    load_dotenv(override=True)

    db = StravaDatabase(connection_string=os.environ["DB_CONNECTION_STRING"])

    activity = db.get_activity(activity_id=activity_id)

    after = datetime.datetime.now() - datetime.timedelta(days=days)

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

    name_results = generate_activity_name_with_gemini(
        activity_id=activity_id,
        data=activities_df,
        number_of_options=3,
        api_key=os.environ["GEMINI_API_KEY"],
    )

    for result in name_results:
        db.add_name_suggestion(
            activity_id=activity_id,
            name=result.name,
            description=result.description,
            probability=result.probability,
        )


if __name__ == "__main__":
    load_all_historic_activities(athlete_id=1411289, days=3000, force=True)
    # auto_name_activity(athlete_id=1411289, activity_id=11721753637, days=365)
