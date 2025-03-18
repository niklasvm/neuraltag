import logging

from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.workflows import rename_workflow  # Import your route modules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_post_event(
    content: WebhookPostRequest,
    client_id: str,
    client_secret: str,
    postgres_connection_string: str,
    gemini_api_key: str,
    pushbullet_api_key: str,
    encryption_key: bytes,
):
    """
    Processes the Strava webhook event by renaming the activity.
    """
    logger.info(f"Received webhook event: {content}")
    if (content.aspect_type == "create" and content.object_type == "activity") or (
        content.aspect_type == "update"
        and content.object_type == "activity"
        and content.updates is not None
        and "title" in content.updates
        and content.updates.get("title") == "Rename"
    ):
        activity_id = content.object_id
        athlete_id = content.owner_id

        try:
            rename_workflow(
                activity_id=activity_id,
                athlete_id=athlete_id,
                client_id=client_id,
                client_secret=client_secret,
                gemini_api_key=gemini_api_key,
                pushbullet_api_key=pushbullet_api_key,
                postgres_connection_string=postgres_connection_string,
                encryption_key=encryption_key,
            )
        except Exception:
            logger.exception(
                f"Error renaming activity {activity_id} for athlete {athlete_id}:"
            )
