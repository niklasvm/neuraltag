import logging

from src.database.adapter import Database
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.tasks.etl import SingleActivityETL
from src.tasks.etl.naming_etl import run_name_activity_etl
from src.tasks.publish_name import publish_new_activity_name
from src.app.config import Settings


logger = logging.getLogger(__name__)


def process_post_request(content: WebhookPostRequest, settings: Settings):
    logger.info(f"Received webhook event: {content}")

    if content.object_type == "activity":
        if content.aspect_type in ("create", "update"):
            activity_id = content.object_id
            athlete_id = content.owner_id

            logger.info(
                f"Running single activity etl for athlete {athlete_id} for activity {activity_id}"
            )
            SingleActivityETL(
                settings=settings,
                activity_id=activity_id,
                athlete_id=athlete_id,
            ).run()
            logger.info(
                f"Successfully ran single activity etl for athlete {athlete_id} for activity {activity_id}"
            )

            if content.aspect_type == "create" or (
                content.aspect_type == "update"
                and content.object_type == "activity"
                and content.updates is not None
                and "title" in content.updates
                and content.updates.get("title") == "Rename"
            ):
                logger.info(f"Running name activity etl for activity {activity_id}")
                run_name_activity_etl(
                    activity_id=activity_id,
                    llm_model="google-gla:gemini-2.5-pro-exp-03-25",
                    settings=settings,
                    days=365,
                    temperature=2.0,
                )
                logger.info(
                    f"Successfully ran name activity etl for activity {activity_id}"
                )

                logger.info(f"Running rename workflow for activity {activity_id}")
                publish_new_activity_name(
                    activity_id=activity_id,
                    settings=settings,
                )
                logger.info(
                    f"Successfully ran rename workflow for activity {activity_id}"
                )

        elif content.aspect_type == "delete" and content.object_type == "activity":
            logger.info(f"Deleting activity {content.object_id} from database")
            # delete activity from database
            activity_id = content.object_id
            db = Database(
                settings.postgres_connection_string,
                encryption_key=settings.encryption_key,
            )
            db.delete_activity(activity_id=activity_id, athlete_id=content.owner_id)
            logger.info(f"Successfully deleted activity {activity_id} from database")

        else:
            print("Unsupported activity event aspect type detected")

    elif content.object_type == "athlete":
        if (
            content.aspect_type == "update"
            and content.updates is not None
            and "authorized" in content.updates
        ):
            if content.updates.get("authorized") == "false":
                logger.info(f"Deleting athlete {content.owner_id} from database")
                athlete_id = content.owner_id
                db = Database(
                    settings.postgres_connection_string,
                    encryption_key=settings.encryption_key,
                )
                db.delete_user(athlete_id)
                logger.info(f"Successfully deleted athlete {athlete_id} from database")

    else:
        print("Unknown event type detected")
