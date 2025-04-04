import hashlib
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
    gemini_api_key: str
    pushbullet_api_key: str
    encryption_key: bytes
    state: str
    telegram_bot_token: str
    telegram_chat_id: str
    logfire_token: str

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
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        pushbullet_api_key=os.environ["PUSHBULLET_API_KEY"],
        encryption_key=os.environ["ENCRYPTION_KEY"].encode(),
        state=hashlib.sha256(os.urandom(1024)).hexdigest(),
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
        logfire_token=os.environ["LOGFIRE_TOKEN"],
    )
except ValueError as e:
    print(f"Configuration error: {e}")
    raise  # Re-raise the exception to prevent the app from starting with invalid config
