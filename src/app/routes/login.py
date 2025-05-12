import logging
import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from src.app.routes.authorization import AUTHORIZATION_CALLBACK
from src.app.schemas.login_request import LoginRequest
from src.app.config import settings
from src.tasks.etl import AuthETL, UserETL, ActivitiesETL

from src.database.adapter import Database
from src.tasks.telegram import TelegramBot


load_dotenv(override=True)

logger = logging.getLogger(__name__)


router = APIRouter()

templates = Jinja2Templates(directory="src/app/templates")


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

    if login_request.state != settings.state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        auth_uuid = AuthETL(
            code=login_request.code,
            scope=login_request.scope,
            settings=settings,
        ).run()
    except Exception:
        logger.exception("Error during login:")
        raise HTTPException(status_code=500, detail="Failed to log in user")

    UserETL(
        auth_uuid=auth_uuid,
        settings=settings,
    ).run()

    # fetch and load historic activities
    background_tasks.add_task(run_historic_activity_etl, auth_uuid=auth_uuid)

    return RedirectResponse(url="/welcome")


def run_historic_activity_etl(auth_uuid):
    logger.info(f"Starting historic activity ETL | auth_uuid: {auth_uuid}")
    try:
        days = 365 * 3
        # days = 365 * 5
        before: datetime.datetime = datetime.datetime.now()
        after: datetime.datetime = before - datetime.timedelta(days=days)
        activities_etl = ActivitiesETL(
            auth_uuid=auth_uuid,
            settings=settings,
            after=after,
            before=before,
        )
        activities_etl.run()

        try:
            send_new_user_message(auth_uuid=auth_uuid)
        except Exception:
            logger.exception(
                f"Error new user message to telegram bot | auth_uuid: {auth_uuid}"
            )

    except:
        logger.exception(f"Error during historic activity ETL | auth_uuid: {auth_uuid}")
        # reraise
        raise

    logger.info(
        f"Historic activity ETL completed | auth_uuid: {auth_uuid} | days: {days}"
    )
    logger.info(f"User {auth_uuid} has been onboarded successfully")


def send_new_user_message(auth_uuid: str):
    db = Database(
        connection_string=settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )
    user = db.get_user_by_auth_id(auth_uuid)

    tb = TelegramBot(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        parse_mode="HTML",
    )
    tb.send_message(
        message=f"New user: {user.name} {user.lastname} ({user.athlete_id})\n",
    )
