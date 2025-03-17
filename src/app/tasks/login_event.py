import datetime
from stravalib import Client
from src.app.db.adapter import Database
from src.app.db.models import Activity, Auth, User
from src.data import summary_activity_to_activity_model
from src.strava import exchange_code_for_athlete_and_token


def strava_authenticate_and_load_user_and_auth(
    code: str,
    scope: str,
    client_id: int,
    client_secret: str,
    postgres_connection_string: str,
    encryption_key: bytes,
) -> User:
    user, token_response = exchange_code_for_athlete_and_token(
        strava_client_id=client_id, strava_client_secret=client_secret, code=code
    )
    db = Database(postgres_connection_string, encryption_key=encryption_key)

    db.add_auth(
        Auth(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=token_response["expires_at"],
            scope=scope,
            athlete_id=user.id,
        )
    )

    # add/update athlete to database
    user_uuid = db.add_user(User(athlete_id=user.id))

    user = db.get_user(uuid=user_uuid)
    return user


def strava_fetch_and_load_historic_activities(
    athlete_id: int,
    client_id: int,
    client_secret: str,
    postgres_connection_string: str,
    encryption_key: bytes,
    before: datetime.datetime,
    after: datetime.datetime,
) -> list[Activity]:
    db = Database(postgres_connection_string, encryption_key=encryption_key)
    auth = db.get_auth_by_athlete_id(athlete_id)

    client: Client = Client(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        token_expires=auth.expires_at,
    )
    client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=auth.refresh_token,
    )
    summary_activities = client.get_activities(after=after, before=before)
    summary_activities = [x for x in summary_activities]

    activities:list[Activity] = []
    for summary_activity in summary_activities:
        activity = summary_activity_to_activity_model(summary_activity)
        db.add_activity(activity)
        activities.append(activity)

    return activities

def strava_fetch_and_load_activity(activity_id:int, athlete_id, client_id: int,
    client_secret: str,
    postgres_connection_string: str,
    encryption_key: bytes):

    db = Database(postgres_connection_string, encryption_key=encryption_key)
    auth = db.get_auth_by_athlete_id(athlete_id)

    client: Client = Client(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        token_expires=auth.expires_at,
    )
    client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=auth.refresh_token,
    )
    activity = client.get_activity(activity_id)
    activity = summary_activity_to_activity_model(activity)
    db.add_activity(activity)
    return activity

