import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse
from stravalib import Client

from src.flows import login_user, new_activity_created_workflow

app = FastAPI(openapi_url=None)

AUTHORIZATION_CALLBACK = "/login"


@app.post("/webhook")
def strava_webhook(content: dict):
    """
    Handles the webhook event from Strava.
    """
    print(content)

    # Validate input to prevent injection attacks
    if not isinstance(content, dict):
        return JSONResponse(
            content={"error": "Invalid webhook content"}, status_code=400
        )

    if (
        content.get("aspect_type") in ("create", "update")
        and content.get("object_type") == "activity"
    ):
        activity_id = content.get("object_id")
        athlete_id = content.get("owner_id")

        if not isinstance(activity_id, int) or not isinstance(athlete_id, int):
            return JSONResponse(
                content={"error": "Invalid activity or athlete ID"}, status_code=400
            )

        new_activity_created_workflow(activity_id=activity_id, athlete_id=athlete_id)

    return JSONResponse(content={"message": "Received webhook event"}, status_code=200)


@app.get("/webhook")
async def verify_strava_subscription(
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_mode: str = Query(None, alias="hub.mode"),
):
    """
    Handles the webhook verification request from Strava.
    """
    load_dotenv(override=True)
    if hub_mode == "subscribe" and hub_verify_token == os.environ.get(
        "STRAVA_VERIFY_TOKEN"
    ):
        return JSONResponse(content={"hub.challenge": hub_challenge}, status_code=200)
    else:
        return JSONResponse(content={"error": "Verification failed"}, status_code=400)


@app.get("/authorization")
async def authorization() -> RedirectResponse:
    load_dotenv(override=True)

    client = Client()

    application_url = os.environ["APPLICATION_URL"]
    redirect_uri = application_url + AUTHORIZATION_CALLBACK
    url = client.authorization_url(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        redirect_uri=redirect_uri,
        scope=["activity:read_all", "activity:write"],
    )

    # redirect to strava authorization url
    return RedirectResponse(url=url)


@app.get(AUTHORIZATION_CALLBACK)
async def login(code: str, scope: str, response: Response) -> dict[str, str]:
    athlete_id = login_user(code=code, scope=scope)
    return {"message": f"Logged in as athlete {athlete_id}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
