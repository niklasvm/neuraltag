from stravalib import Client
import datetime
from stravalib.model import DetailedActivity, SummaryActivity, SummaryAthlete



def exchange_code_for_athlete_and_token(
    strava_client_id: int, strava_client_secret: str, code: str
) -> tuple[SummaryAthlete,dict[str, str]]:
    """Exchange a Strava code for an access token."""
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=strava_client_id,
        client_secret=strava_client_secret,
        code=code,
    )
    
    access_token = token_response.get("access_token")
    client.access_token = access_token

    athlete = client.get_athlete()
    
    return athlete, token_response

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


def fetch_historic_activity_data(
    client: Client, after: datetime.datetime, before: datetime.datetime
) -> list[SummaryActivity]:
    activities = client.get_activities(after=after, before=before)
    activities = [x for x in activities]

    return activities


def fetch_activity_data(client: Client, activity_id: int) -> DetailedActivity:
    activity = client.get_activity(activity_id)
    return activity