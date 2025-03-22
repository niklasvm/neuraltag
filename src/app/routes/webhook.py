import logging
from typing import Annotated

from fastapi import APIRouter, Query, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from src.app.schemas.webhook_get_request import WebhookGetRequest
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.app.config import settings
from src.tasks.post_event import process_post_request

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
    background_tasks.add_task(process_post_request, content, settings=settings)

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
