import logging
import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from src.app.schemas.login_request import LoginRequest
from src.app.db.external_api_data_handler import (
    ExternalAPIDataHandler,
)
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
        strava_db_operations = ExternalAPIDataHandler.authenticate_and_store(
            code=login_request.code,
            scope=login_request.scope,
            settings=settings,
        )
    except Exception:
        logger.exception("Error during login:")
        raise HTTPException(status_code=500, detail="Failed to log in user")

    # fetch and load historic activities
    days = 365
    before: datetime.datetime = datetime.datetime.now()
    after: datetime.datetime = before - datetime.timedelta(days=days)
    background_tasks.add_task(
        strava_db_operations.fetch_and_load_historic_activities,
        before=before,
        after=after,
    )

    return RedirectResponse(url="/welcome")
