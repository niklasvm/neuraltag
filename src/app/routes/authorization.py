import logging

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from src.app.config import settings
from src.database.models import UserType

load_dotenv(override=True)

logger = logging.getLogger(__name__)

AUTHORIZATION_CALLBACK = "/login"

router = APIRouter()


@router.get("/authorization")
async def authorization() -> RedirectResponse:
    from stravalib import Client

    client = Client()

    logger.info("Redirecting to Strava authorization URL")
    redirect_uri = settings.application_url + AUTHORIZATION_CALLBACK


    state = settings.state + "-" + UserType.NEURALTAG.value

    url = client.authorization_url(
        client_id=settings.strava_client_id,
        redirect_uri=redirect_uri,
        scope=["activity:read", "activity:write"],
        state=state,
    )

    # redirect to strava authorization url
    return RedirectResponse(url=url)


@router.get("/history-login")
async def history_login() -> RedirectResponse:
    from stravalib import Client

    client = Client()

    logger.info("Redirecting to Strava authorization URL")
    redirect_uri = settings.application_url + AUTHORIZATION_CALLBACK


    state = settings.state + "-" + UserType.HISTORY.value

    url = client.authorization_url(
        client_id=settings.strava_client_id,
        redirect_uri=redirect_uri,
        scope=["activity:read","activity:read_all"],
        state=state,
    )

    # redirect to strava authorization url
    return RedirectResponse(url=url)
