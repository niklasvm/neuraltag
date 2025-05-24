import logging


from src.database.adapter import Database
from src.app.config import Settings

from src.tasks.strava import get_strava_client
from src.tasks.telegram import TelegramBot

NEURALTAG_SIGNATURE = "named with NeuralTag 🤖"

# Set up logging
logger = logging.getLogger(__name__)

PUBLISH_TELEGRAM_NOTIFICATION_TEMPLATE = """
<b>Activity rename workflow completed</b>

<b>Activity ID:</b> {activity_id}
<b>Athlete ID:</b> {athlete_id}
<b>Athlete Name:</b> {athlete_name} {athlete_lastname}
<b>Name:</b> {name}
<b>Description:</b> {description}
<b>Probability:</b> {probability:.0f}%
""".strip()


def publish_new_activity_name(activity_id: int, settings: Settings):
    db = Database(
        settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )

    # get details from database
    activity = db.get_activity_by_id(activity_id=activity_id)
    auth = db.get_auth_by_athlete_id(
        athlete_id=activity.athlete_id,
    )
    name_suggestions = db.get_name_suggestions_by_activity_id(activity_id=activity_id)
    athlete = db.get_user_by_athlete_id(
        athlete_id=activity.athlete_id,
    )

    # get new name and description
    name_suggestions = sorted(
        name_suggestions, key=lambda x: x.probability, reverse=True
    )
    idx = 0

    selected_name_suggestion = name_suggestions[idx]
    new_name = selected_name_suggestion.name
    suggestion_description = selected_name_suggestion.description

    existing_description = activity.description
    if NEURALTAG_SIGNATURE not in str(existing_description):
        updated_activity_description = (
            f"{existing_description}\n\n{NEURALTAG_SIGNATURE}".strip()
        )
    else:
        updated_activity_description = existing_description
    new_probability = selected_name_suggestion.probability

    # publish the new name to strava
    client = get_strava_client(
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        expires_at=auth.expires_at,
        strava_client_id=settings.strava_client_id,
        strava_client_secret=settings.strava_client_secret,
    )
    client.update_activity(
        activity_id=activity_id,
        name=new_name,
        description=updated_activity_description,
    )
    logger.info(
        f"Updated activity {activity.activity_id} for athlete {activity.athlete_id} with new name `{new_name}` and description `{updated_activity_description}`"
    )

    # publish notification to telegram
    telegram_message = PUBLISH_TELEGRAM_NOTIFICATION_TEMPLATE.format(
        activity_id=activity.activity_id,
        athlete_id=activity.athlete_id,
        athlete_name=athlete.name,
        athlete_lastname=athlete.lastname,
        name=new_name,
        description=suggestion_description,
        probability=new_probability * 100,
    )

    tb = TelegramBot(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        parse_mode="HTML",
    )
    try:
        tb.send_message(
            message=telegram_message,
        )
        print()
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")


if __name__ == "__main__":
    from src.app.config import settings
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Example usage

    publish_new_activity_name(activity_id=14570364200, settings=settings)
