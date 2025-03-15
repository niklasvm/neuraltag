from src.app.db.adapter import Database
from src.app.schemas.login_request import LoginRequest
from src.strava import exchange_code_for_athlete_and_token


def process_login_event(
    login_request: LoginRequest,
    client_id: int,
    client_secret: str,
    postgres_connection_string: str,
):
    code = login_request.code
    scope = login_request.scope

    athlete, token_response = exchange_code_for_athlete_and_token(
        strava_client_id=client_id, strava_client_secret=client_secret, code=code
    )


    db = Database(postgres_connection_string)

    # add/update athlete to database
    athlete_uuid = db.add_athlete(athlete)

    # add/update auth to database
    db.add_auth(
        access_token=token_response["access_token"],
        athlete_id=athlete.id,
        refresh_token=token_response["refresh_token"],
        expires_at=token_response["expires_at"],
        scope=scope,
    )

    athlete = db.get_athlete(uuid=athlete_uuid)

    return athlete
