import os

from dotenv import load_dotenv
import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, RedirectResponse
from stravalib import Client


load_dotenv(override=True)

app = FastAPI(openapi_url=None)
# app = FastAPI()

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
        content.get("aspect_type") == "create"
        and content.get("object_type") == "activity"
    ):
        activity_id = content.get("object_id")
        athlete_id = content.get("owner_id")

        if not isinstance(activity_id, int) or not isinstance(athlete_id, int):
            return JSONResponse(
                content={"error": "Invalid activity or athlete ID"}, status_code=400
            )

        trigger_gha(dict(activity_id=activity_id))

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
    # load_dotenv(override=True)
    if hub_mode == "subscribe" and hub_verify_token == os.environ.get(
        "STRAVA_VERIFY_TOKEN"
    ):
        return JSONResponse(content={"hub.challenge": hub_challenge}, status_code=200)
    else:
        return JSONResponse(content={"error": "Verification failed"}, status_code=400)


@app.get("/authorization")
async def authorization() -> RedirectResponse:
    # load_dotenv(override=True)

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
async def login(code: str, scope: str) -> dict[str, str]:
    from src.workflows import login_user

    athlete_id = login_user(code=code, scope=scope)
    return {"message": f"Logged in as athlete {athlete_id}"}


def trigger_gha(inputs: dict) -> None:
    """Triggers a GitHub Actions workflow dispatch.

    This function retrieves necessary environment variables (GITHUB_USER, REPO,
    GITHUB_PAT, WORKFLOW_FILE) and uses them to construct the API endpoint for
    triggering a workflow dispatch. It then sends a POST request to the GitHub API
    with the required headers and data to initiate the workflow run.  The function
    checks the response status code and prints a success or failure message
    accordingly.

    Raises:
        KeyError: If any of the required environment variables are not set.
        requests.exceptions.RequestException: If the API request fails.
    """

    GITHUB_USER = os.environ.get("GITHUB_USER")
    REPO = os.environ.get("REPO")
    GITHUB_PAT = os.environ.get("GITHUB_PAT")
    WORKFLOW_FILE = os.environ.get("WORKFLOW_FILE")
    ENDPOINT = f"https://api.github.com/repos/{GITHUB_USER}/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    REF = "master"

    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    data = {
        "ref": f"{REF}",
        "inputs": inputs,
    }

    response = requests.post(ENDPOINT, headers=headers, json=data)

    if response.status_code == 204:
        print("Workflow dispatch triggered successfully.")
    else:
        print(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
