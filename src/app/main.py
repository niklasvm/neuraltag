import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.app.pages import home
from src.app.db.adapter import Database

from src.app.apis import auth, webhook
from src.app.core.config import settings

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZATION_CALLBACK = "/login"

app = FastAPI(debug=True)

templates = Jinja2Templates(directory="src/app/templates")  # Configure Jinja2

# Include your route handlers
app.include_router(home.router)
app.include_router(auth.router)
app.include_router(webhook.router)
app.mount("/static", StaticFiles(directory="src/app/static"), name="static")


@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request, uuid: str):
    db = Database(
        settings.postgres_connection_string, encryption_key=settings.encryption_key
    )

    try:
        user = db.get_user(uuid)
        if user is None:
            return templates.TemplateResponse(
                request, "error.html", {"error": "User not found"}
            )  # Provide error message
        return templates.TemplateResponse(request, "welcome.html")
    except Exception:
        logger.exception(f"Error fetching User with UUID {uuid}:")
        return templates.TemplateResponse(
            request, "error.html", {"error": "User not found"}
        )  # Provide error message
