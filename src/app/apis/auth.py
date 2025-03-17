import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from src.app.schemas.login_request import LoginRequest
from src.app.tasks.login_event import login_new_user, onboard_new_user
from src.app.core.config import settings

load_dotenv(override=True)

logger = logging.getLogger(__name__)

AUTHORIZATION_CALLBACK = "/login"

router = APIRouter()

templates = Jinja2Templates(directory="src/app/templates")


@router.get("/authorization")
async def authorization() -> RedirectResponse:
    from stravalib import Client

    client = Client()

    redirect_uri = settings.application_url + AUTHORIZATION_CALLBACK
    url = client.authorization_url(
        client_id=settings.strava_client_id,
        redirect_uri=redirect_uri,
        scope=["activity:read", "activity:write"],
    )

    # redirect to strava authorization url
    return RedirectResponse(url=url)


@router.get(AUTHORIZATION_CALLBACK)
async def login(
    request: Request,
    login_request: Annotated[LoginRequest, Query()],
    background_tasks: BackgroundTasks,
) -> RedirectResponse:
    if login_request.error is not None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error": login_request.error},
        )

    try:
        athlete = login_new_user(
            login_request=login_request,
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            postgres_connection_string=settings.postgres_connection_string,
            encryption_key=settings.encryption_key,
        )
        uuid = athlete.uuid
    except Exception:
        logger.exception("Error during login:")
        raise HTTPException(status_code=500, detail="Failed to log in user")

    background_tasks.add_task(
        onboard_new_user,
        athlete_id=athlete.athlete_id,
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        postgres_connection_string=settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )

    return RedirectResponse(url=f"/welcome?uuid={uuid}")
