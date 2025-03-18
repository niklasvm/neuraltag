import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.app.pages import home

from src.app.apis import auth, webhook

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
async def welcome(request: Request):
    return templates.TemplateResponse(request, "welcome.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("src/app/static/images/favicon.ico")
