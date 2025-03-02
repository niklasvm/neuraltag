import datetime
import logging
import os

from dotenv import load_dotenv
from stravalib import Client

from src.data.db import StravaDatabase
from src.data.models import SummaryActivity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def new_user(code: str, scope: str):
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


def load_historic_activities(athlete_id: int, days: int):
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

    # get latest date
    latest_date = (
        db.session.query(SummaryActivity)
        .order_by(SummaryActivity.start_date.desc())
        .first()
        .start_date
    )
    logger.info(f"Latest date: {latest_date}")

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

    earliest_date = datetime.datetime.now() - datetime.timedelta(days=days)
    if latest_date:
        after = max(latest_date, earliest_date)

    after = after.strftime("%Y-%m-%d")

    activities = client.get_activities(after=after)
    activities = [x for x in activities]
    logger.info(f"Number of activities to load: {len(activities)}")

    db.add_activities(activities)


if __name__ == "__main__":
    load_historic_activities(athlete_id=1411289, days=365)
