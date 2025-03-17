import datetime
from stravalib import Client
from src.app.db.adapter import Database
from src.app.db.models import Auth, User
from src.app.schemas.login_request import LoginRequest
from src.data import summary_activity_to_activity_model
from src.strava import exchange_code_for_athlete_and_token


def login_new_user(
    login_request: LoginRequest,
    client_id: int,
    client_secret: str,
    postgres_connection_string: str,
    encryption_key: bytes,
):
    code = login_request.code
    scope = login_request.scope

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


def onboard_new_user(
    athlete_id, client_id, client_secret, postgres_connection_string, encryption_key
):
    db = Database(postgres_connection_string, encryption_key=encryption_key)
    auth = db.get_auth_by_athlete_id(athlete_id)

    before = datetime.datetime.now()
    after = before - datetime.timedelta(days=365)

    client = Client(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        token_expires=auth.expires_at,
    )
    client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=auth.refresh_token,
    )
    activities = client.get_activities(after=after, before=before)
    activities = [x for x in activities]
    for summary_activity in activities:
        activity = summary_activity_to_activity_model(summary_activity)
        db.add_activity(activity)
