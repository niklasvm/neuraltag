import logging

from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.app.db.adapter import Database
from src.workflows import rename_workflow  # Import your route modules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_post_event(
    content: WebhookPostRequest,
    client_id: str,
    client_secret: str,
    postgres_connection_string: str,
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
        strava_db = Database(postgres_connection_string)
        auth = strava_db.get_auth(athlete_id=athlete_id)
        try:
            rename_workflow(
                activity_id=activity_id,
                access_token=auth.access_token,
                refresh_token=auth.refresh_token,
                expires_at=auth.expires_at,
                client_id=client_id,
                client_secret=client_secret,
            )
        except Exception:
            logger.exception(
                f"Error renaming activity {activity_id} for athlete {athlete_id}:"
            )
