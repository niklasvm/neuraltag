from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi_throttle import RateLimiter

router = APIRouter()
templates = Jinja2Templates(directory="src/app/templates")


@router.get(
    "/",
    response_class=HTMLResponse,
    dependencies=[
        Depends(
            RateLimiter(
                times=5,
                seconds=5,
            )
        )
    ],
)
async def home(request: Request):
    # if request.query_params:
    #     raise HTTPException(
    #         status_code=400, detail="Query parameters are not supported."
    #     )
    return templates.TemplateResponse(request, "index.html", {"title": "Home Page"})
