import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.app.pages import home

from src.app.routes import login, webhook, authorization


load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

templates = Jinja2Templates(directory="src/app/templates")  # Configure Jinja2

# Include your route handlers
app.include_router(home.router)
app.include_router(login.router)
app.include_router(webhook.router)
app.include_router(authorization.router)
app.mount("/static", StaticFiles(directory="src/app/static"), name="static")


@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    if request.query_params:
        raise HTTPException(
            status_code=400, detail="Query parameters are not supported."
        )
    return templates.TemplateResponse(request, "welcome.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse("src/app/static/images/favicon.ico")
