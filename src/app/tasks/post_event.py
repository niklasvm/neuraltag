import logging

from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.workflows import rename_workflow  # Import your route modules
from src.app.core.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_post_event(content: WebhookPostRequest, settings: Settings):
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
                activity_id=activity_id, athlete_id=athlete_id, settings=settings
            )
        except Exception:
            logger.exception(
                f"Error renaming activity {activity_id} for athlete {athlete_id}:"
            )
