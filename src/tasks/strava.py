"""Module for interacting with the Strava API."""

from stravalib import Client
import datetime
from stravalib.model import DetailedActivity, SummaryActivity

def get_strava_client(
    access_token: str,
    refresh_token: str,
    expires_at: int,
    strava_client_id: int,
    strava_client_secret: str,
) -> Client:
    """Get a Strava client with the given credentials."""
    client = Client(
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires=expires_at,
    )
    client.refresh_access_token(
        client_id=strava_client_id,
        client_secret=strava_client_secret,
        refresh_token=refresh_token,
    )

    return client


