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


def rename_workflow(activity: Activity, settings: Settings, rename: bool):
    db = Database(
        settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )

    time_start = datetime.datetime.now()
    existing_description = activity.description

    if not rename:
        days = 365
        temperature = 2.0
        etl = NameSuggestionETL(
            llm_model="google-gla:gemini-2.5-pro-exp-03-25",
            settings=settings,
            activity_id=activity.activity_id,
            days=days,
            temperature=temperature,
        )
        name_suggestions = etl.run()
    else:
        name_suggestions = db.get_name_suggestions_by_activity_id(
            activity_id=activity.activity_id,
        )
        if len(name_suggestions) == 0:
            rename_workflow(
                activity=activity,
                settings=settings,
                rename=False,
            )
            return

    # order to get the best name suggestion first
    name_suggestions = sorted(
        name_suggestions,
        key=lambda x: x.probability,
        reverse=True,
    )
    if not rename:
        idx = 0
    else:
        existing_index = [
            name_suggestion.name for name_suggestion in name_suggestions
        ].index(activity.name)
        idx = existing_index + 1
        if idx >= len(name_suggestions):
            idx = 0

        logger.info(
            f"Activity {activity.activity_id} already exists in the database. Updating the name suggestion index to {idx}."
        )

    top_name_suggestion = name_suggestions[idx].name
    top_name_description = name_suggestions[idx].description
    top_name_probability = name_suggestions[idx].probability

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

    # publish the new name to strava
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
    db.add_rename_history(
        activity_id=activity.activity_id,
        new_name=top_name_suggestion,
        old_name=activity.name,
    )

    # notify via pushbullet
    pb = Pushbullet(settings.pushbullet_api_key)
    pb_response = pb.push_note(
        title=top_name_suggestion,
        body=top_name_description + f"\nProbability: {top_name_probability:.2f}%",
    )
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
