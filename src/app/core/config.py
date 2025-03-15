import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

load_dotenv(override=True)


class Settings(BaseModel):
    strava_client_id: int
    strava_client_secret: str
    strava_verify_token: str
    application_url: str
    postgres_connection_string: str

    @field_validator("*")
    def not_empty(cls, value):
        if not value:
            raise ValueError("Field cannot be empty")
        return value


try:
    settings = Settings(
        strava_client_id=int(os.environ["STRAVA_CLIENT_ID"]),
        strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        strava_verify_token=os.environ["STRAVA_VERIFY_TOKEN"],
        application_url=os.environ["APPLICATION_URL"],
        postgres_connection_string=os.environ["POSTGRES_CONNECTION_STRING"],
    )
except ValueError as e:
    print(f"Configuration error: {e}")
    raise  # Re-raise the exception to prevent the app from starting with invalid config
