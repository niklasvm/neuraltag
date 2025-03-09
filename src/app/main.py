import logging
import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.app.pages import home
from src.app.schemas.login_request import LoginRequest
from src.app.schemas.webhook_get_request import WebhookGetRequest
from src.app.schemas.webhook_post_request import WebhookPostRequest
from src.app.db.adapter import Database
from src.workflows import rename_workflow  # Import your route modules

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZATION_CALLBACK = "/login"

app = FastAPI()

templates = Jinja2Templates(directory="src/app/templates")  # Configure Jinja2

# Include your route handlers
app.include_router(home.router)


@app.get("/authorization")
async def authorization() -> RedirectResponse:
    from stravalib import Client

    client = Client()

    application_url = os.environ["APPLICATION_URL"]
    redirect_uri = application_url + AUTHORIZATION_CALLBACK
    url = client.authorization_url(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        redirect_uri=redirect_uri,
        scope=["activity:read_all", "activity:write"],
    )

    # redirect to strava authorization url
    return RedirectResponse(url=url)


@app.get(AUTHORIZATION_CALLBACK)
async def login(
    request: Request, login_request: Annotated[LoginRequest, Query()]
) -> RedirectResponse:
    from src.workflows import login_user

    if login_request.error is not None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": login_request.error}
        )

    code = login_request.code
    scope = login_request.scope

    athlete = login_user(code=code, scope=scope)
    uuid = athlete.uuid

    return RedirectResponse(url=f"/welcome?uuid={uuid}")


@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request, uuid: str):
    db = Database(os.environ["POSTGRES_CONNECTION_STRING"])

    athlete = db.get_athlete(uuid)
    if athlete is None:
        return templates.TemplateResponse(
            "error.html", {"request": request, "athlete": athlete}
        )
    return templates.TemplateResponse(
        "welcome.html", {"request": request, "athlete": athlete}
    )


@app.post("/webhook")
async def strava_webhook(content: WebhookPostRequest):
    """
    Handles the webhook event from Strava.
    """
    # logger.info(f"Received webhook event: {content}")

    if (content.aspect_type == "create" and content.object_type == "activity") or (
        content.aspect_type == "update"
        and content.object_type == "activity"
        and content.updates is not None
        and "title" in content.updates
        and content.updates.get("title") == "Rename"
    ):
        activity_id = content.object_id
        athlete_id = content.owner_id

        if not isinstance(activity_id, int) or not isinstance(athlete_id, int):
            return JSONResponse(
                content={"error": "Invalid activity or athlete ID"}, status_code=400
            )

        strava_db = Database(os.environ["POSTGRES_CONNECTION_STRING"])
        auth = strava_db.get_auth(athlete_id=athlete_id)
        rename_workflow(
            activity_id=activity_id,
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            client_id=os.environ["STRAVA_CLIENT_ID"],
            client_secret=os.environ["STRAVA_CLIENT_SECRET"],
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
        and webhook_get_request.hub_verify_token
        == os.environ.get("STRAVA_VERIFY_TOKEN")
    ):
        return JSONResponse(
            content={"hub.challenge": webhook_get_request.hub_challenge},
            status_code=200,
        )
    else:
        return JSONResponse(content={"error": "Verification failed"}, status_code=400)
