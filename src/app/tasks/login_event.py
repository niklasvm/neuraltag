from stravalib import Client
from src.app.db.adapter import Database
from src.app.schemas.login_request import LoginRequest


def process_login_event(
    login_request: LoginRequest,
    client_id: int,
    client_secret: str,
    postgres_connection_string: str,
):
    code = login_request.code
    scope = login_request.scope

    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=client_id,
        client_secret=client_secret,
        code=code,
    )
    access_token = token_response.get("access_token")

    # get athlete
    client.access_token = access_token
    athlete = client.get_athlete()

    db = Database(postgres_connection_string)

    # add/update athlete to database
    uuid = db.add_athlete(athlete)

    # add/update auth to database
    db.add_auth(
        access_token=access_token,
        athlete_id=athlete.id,
        refresh_token=token_response["refresh_token"],
        expires_at=token_response["expires_at"],
        scope=scope,
    )

    athlete = db.get_athlete(uuid=uuid)

    return athlete
