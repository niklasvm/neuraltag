import logging
import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, validator

from src.app.pages import home
from src.app.schemas.login_request import LoginRequest
from src.app.schemas.webhook_get_request import WebhookGetRequest
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.app.db.adapter import Database
from src.app.tasks.login_event import process_login_event

from src.app.tasks.post_event import process_post_event

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZATION_CALLBACK = "/login"

app = FastAPI()

templates = Jinja2Templates(directory="src/app/templates")  # Configure Jinja2

# Include your route handlers
app.include_router(home.router)


class Settings(BaseModel):
    strava_client_id: str
    strava_client_secret: str
    strava_verify_token: str
    application_url: str
    postgres_connection_string: str

    @validator("*")
    def not_empty(cls, value):
        if not value:
            raise ValueError("Field cannot be empty")
        return value


try:
    settings = Settings(
        strava_client_id=os.environ["STRAVA_CLIENT_ID"],
        strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        strava_verify_token=os.environ["STRAVA_VERIFY_TOKEN"],
        application_url=os.environ["APPLICATION_URL"],
        postgres_connection_string=os.environ["POSTGRES_CONNECTION_STRING"],
    )
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise  # Re-raise the exception to prevent the app from starting with invalid config


@app.get("/authorization")
async def authorization() -> RedirectResponse:
    from stravalib import Client

    client = Client()

    redirect_uri = settings.application_url + AUTHORIZATION_CALLBACK
    url = client.authorization_url(
        client_id=settings.strava_client_id,
        redirect_uri=redirect_uri,
        scope=["activity:read_all", "activity:write"],
    )

    # redirect to strava authorization url
    return RedirectResponse(url=url)


@app.get(AUTHORIZATION_CALLBACK)
async def login(
    request: Request, login_request: Annotated[LoginRequest, Query()]
) -> RedirectResponse:
    if login_request.error is not None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error": login_request.error},
        )

    try:
        athlete = process_login_event(
            login_request=login_request,
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            postgres_connection_string=settings.postgres_connection_string,
        )
        uuid = athlete.uuid
    except Exception:
        logger.exception("Error during login:")
        raise HTTPException(status_code=500, detail="Failed to log in user")

    return RedirectResponse(url=f"/welcome?uuid={uuid}")


@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request, uuid: str):
    db = Database(settings.postgres_connection_string)

    try:
        athlete = db.get_athlete(uuid)
        if athlete is None:
            return templates.TemplateResponse(
                request, "error.html", {"error": "Athlete not found"}
            )  # Provide error message
        return templates.TemplateResponse(request, "welcome.html", {"athlete": athlete})
    except Exception:
        logger.exception(f"Error fetching athlete with UUID {uuid}:")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve athlete data"
        )  # Use HTTPException


@app.post("/webhook")
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
    )

    return JSONResponse(content={"message": "Received webhook event"}, status_code=200)


@app.get("/webhook")
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
