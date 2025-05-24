import os
from unittest.mock import patch
from dotenv import load_dotenv
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.app.config import settings
from src.tasks.post_event import process_post_request, Database
import logging
import logfire

logfire.configure()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
#
#  suppress logging from stravalib and httpx
logging.getLogger("stravalib").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("stravalib.util.limiter.SleepingRateLimitRule").setLevel(
    logging.ERROR
)

athlete_id = os.environ.get("TEST_ATHLETE_ID")
activity_id = os.environ.get("TEST_ACTIVITY_ID")

load_dotenv(override=True)


# activity create
def test_activity_create(athlete_id, activity_id):
    request = WebhookPostRequest(
        object_type="activity",
        aspect_type="create",
        object_id=activity_id,
        owner_id=athlete_id,
        subscription_id=123,
        event_time=98734987345,
        updates={},
    )
    process_post_request(
        content=request,
        settings=settings,
    )


# activity update
def test_activity_update(athlete_id, activity_id):
    request = WebhookPostRequest(
        object_type="activity",
        aspect_type="update",
        object_id=activity_id,
        owner_id=athlete_id,
        subscription_id=123,
        event_time=98734987345,
        updates={"title": "Testing"},
    )
    process_post_request(
        content=request,
        settings=settings,
    )


# activity update rename
def test_activity_update_rename(athlete_id, activity_id):
    request = WebhookPostRequest(
        object_type="activity",
        aspect_type="update",
        object_id=activity_id,
        owner_id=athlete_id,
        subscription_id=123,
        event_time=98734987345,
        updates={"title": "Rename"},
    )
    process_post_request(
        content=request,
        settings=settings,
    )


def test_activity_delete(athlete_id, activity_id):
    with patch.object(Database, "delete_activity") as mock_delete_activity:
        request = WebhookPostRequest(
            object_type="activity",
            aspect_type="delete",
            object_id=activity_id,
            owner_id=athlete_id,
            subscription_id=123,
            event_time=98734987345,
            updates={},
        )
        process_post_request(
            content=request,
            settings=settings,
        )
        mock_delete_activity.assert_called()


def test_athlete_unsubscribe(athlete_id):
    with patch.object(Database, "delete_user") as mock_delete_athlete:
        request = WebhookPostRequest(
            object_type="athlete",
            aspect_type="update",
            object_id=athlete_id,
            owner_id=athlete_id,
            subscription_id=123,
            event_time=98734987345,
            updates={"authorized": "false"},
        )
        process_post_request(
            content=request,
            settings=settings,
        )

        mock_delete_athlete.assert_called()


if __name__ == "__main__":
    test_activity_create(athlete_id, activity_id)
    test_activity_update(athlete_id, activity_id)
    test_activity_update_rename(athlete_id, activity_id)
    test_activity_delete(athlete_id, activity_id)
    # test_athlete_unsubscribe(athlete_id)
