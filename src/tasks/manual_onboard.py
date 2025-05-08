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

auth_uuid="XXXX-XXXX-XXXX-XXXX"  # Replace with the actual auth_uuid

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