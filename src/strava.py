import os
from stravalib.client import Client
import datetime

from stravalib.model import SummaryActivity


def authenticate_strava(token_dict: dict[str, str]):
    os.environ["STRAVA_CLIENT_ID"] = token_dict["STRAVA_CLIENT_ID"]
    os.environ["STRAVA_CLIENT_SECRET"] = token_dict["STRAVA_CLIENT_SECRET"]
    client = Client(
        access_token=token_dict["access_token"],
        refresh_token=token_dict["refresh_token"],
        token_expires=token_dict["expires_at"],
    )
    client.refresh_access_token(
        client_id=token_dict["STRAVA_CLIENT_ID"],
        client_secret=token_dict["STRAVA_CLIENT_SECRET"],
        refresh_token=token_dict["refresh_token"],
    )
    return client


def get_strava_activities(client: Client, days: int) -> list[SummaryActivity]:
    after = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )

    activities = client.get_activities(after=after)
    activities = [x for x in activities]
    print(f"Found {len(activities)} activities")

    return activities
