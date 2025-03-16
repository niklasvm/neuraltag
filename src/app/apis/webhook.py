import logging
from typing import Annotated

from fastapi import APIRouter, Query, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from src.app.schemas.webhook_get_request import WebhookGetRequest
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.app.tasks.post_event import process_post_event
from src.app.core.config import settings

load_dotenv(override=True)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook")
async def handle_post_event(
    content: WebhookPostRequest, background_tasks: BackgroundTasks
):
    """
    Handles the webhook event from Strava.
    """
    background_tasks.add_task(
        process_post_event,
        content,
        settings.strava_client_id,
        settings.strava_client_secret,
        settings.postgres_connection_string,
        settings.gemini_api_key,
        settings.pushbullet_api_key,
    )

    return JSONResponse(content={"message": "Received webhook event"}, status_code=200)


@router.get("/webhook")
async def verify_strava_subscription(
    request: Request, webhook_get_request: Annotated[WebhookGetRequest, Query()]
):
    """
    Handles the webhook verification request from Strava.
    """

    if (
        webhook_get_request.hub_mode == "subscribe"
        and webhook_get_request.hub_verify_token == settings.strava_verify_token
    ):
        return JSONResponse(
            content={"hub.challenge": webhook_get_request.hub_challenge},
            status_code=200,
        )
    else:
        raise HTTPException(status_code=400, detail="Verification failed")
