import datetime
import logging

from pushbullet import Pushbullet


from src.database.adapter import Database
from src.app.config import Settings

from src.database.models import Activity
from src.tasks.etl import NameSuggestionETL
from src.tasks.strava import get_strava_client
from src.tasks.telegram import TelegramBot

NEURALTAG_SIGNATURE = "named with NeuralTag 🤖"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rename_workflow(activity: Activity, settings: Settings):
    db = Database(
        settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )

    time_start = datetime.datetime.now()
    existing_description = activity.description

    days = 365
    temperature = 2.0

    etl = NameSuggestionETL(
        settings=settings,
        activity_id=activity.activity_id,
        days=days,
        temperature=temperature,
    )
    name_suggestions = etl.run()

    name_suggestions = db.get_name_suggestions_by_activity_id(
        activity_id=activity.activity_id,
    )

    top_name_suggestion = name_suggestions[0].name
    top_name_description = name_suggestions[0].description

    time_end = datetime.datetime.now()
    duration_seconds = (time_end - time_start).total_seconds()
    logger.info(f"Duration: {duration_seconds} seconds")

    if existing_description is None:
        existing_description = ""

    if NEURALTAG_SIGNATURE not in str(existing_description):
        new_description = f"{existing_description}\n\n{NEURALTAG_SIGNATURE}".strip()
    else:
        new_description = existing_description
    logger.info(f"New description: {new_description}")

    auth = db.get_auth_by_athlete_id(
        athlete_id=activity.athlete_id,
    )

    client = get_strava_client(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        expires_at=auth.expires_at,
        strava_client_id=settings.strava_client_id,
        strava_client_secret=settings.strava_client_secret,
    )
    client.update_activity(
        activity_id=activity.activity_id,
        name=top_name_suggestion,
        description=new_description,
    )

    # notify via pushbullet
    pb = Pushbullet(settings.pushbullet_api_key)
    pb_response = pb.push_note(title=top_name_suggestion, body=top_name_description)
    logger.info(pb_response)

    tb = TelegramBot(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        parse_mode="HTML",
    )
    telegram_message = "<b>New activity update:</b>\n\n"
    for idx, name_suggestion in enumerate(name_suggestions[:5]):
        telegram_message += (
            f"<b>{idx + 1} {name_suggestion.name}</b>\n"
            f"<i>Probability: {name_suggestion.probability}</i>\n"
            f"{name_suggestion.description}\n\n"
        )

    telegram_message = telegram_message.strip()
    response = tb.send_message(
        message=telegram_message,
    )
    logger.info(response)
