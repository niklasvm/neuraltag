import logging

from src.database.adapter import Database
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.tasks.etl import SingleActivityETL
from src.tasks.rename_activity import rename_workflow  # Import your route modules
from src.app.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_post_request(content: WebhookPostRequest, settings: Settings):
    """
    Processes the Strava webhook event by renaming the activity.
    """

    # handle activity creation and activity update events
    logger.info(f"Received webhook event: {content}")
    if (content.aspect_type == "create" and content.object_type == "activity") or (
        content.aspect_type == "update"
        and content.object_type == "activity"
        and content.updates is not None
        and "title" in content.updates
        and content.updates.get("title") == "Rename"
    ):
        handle_activity_create_or_update_event(content, settings)

    # handle unsubscribe events
    elif content.object_type == "athlete" and content.aspect_type == "update":
        if content.updates is not None and "authorized" in content.updates:
            if content.updates.get("authorized") == "false":
                handle_unsubscribe_event(content, settings)

    # handle activity delete events
    elif content.aspect_type == "delete" and content.object_type == "activity":
        handle_activity_delete_event(content, settings)

    else:
        logger.info(f"Received unsupported event: {content}")


def handle_activity_create_or_update_event(content, settings):
    logger.info(f"Received create or update event: {content}")
    activity_id = content.object_id
    athlete_id = content.owner_id

    activity = SingleActivityETL(
        settings=settings,
        activity_id=activity_id,
        athlete_id=athlete_id,
    ).run()

    if content.aspect_type == "create" or (
        content.aspect_type == "update"
        and content.updates is not None
        and "title" in content.updates
        and content.updates.get("title") == "Rename"
    ):
        rename_workflow(activity=activity, settings=settings)


def handle_activity_delete_event(content, settings):
    logger.info(f"Received delete event: {content}")
    # delete activity from database
    activity_id = content.object_id
    db = Database(
        settings.postgres_connection_string, encryption_key=settings.encryption_key
    )
    db.delete_activity(activity_id=activity_id, athlete_id=content.owner_id)
    logger.info(f"Successfully deleted activity {activity_id} from database")


def handle_unsubscribe_event(content, settings):
    logger.info(f"Received unsubscribe event: {content}")
    # delete athlete from database

    logger.info(f"Deleting athlete {content.owner_id} from database")
    athlete_id = content.owner_id
    db = Database(
        settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )
    db.delete_user(athlete_id)
    logger.info(f"Successfully deleted athlete {athlete_id} from database")
