from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="src/app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.query_params:
        raise HTTPException(
            status_code=400, detail="Query parameters are not supported."
        )
    return templates.TemplateResponse(request, "index.html", {"title": "Home Page"})
