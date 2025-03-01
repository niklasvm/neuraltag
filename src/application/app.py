from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import os
from dotenv import load_dotenv

app = FastAPI()


def dispatch(content: dict):
    if content["object_type"] == "activity":
        if content["aspect_type"] == "update" or content["aspect_type"] == "create":
            trigger_gha()
            return "Activity created or updated"


def trigger_gha():
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
    load_dotenv()

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

    data = {"ref": f"{REF}"}

    response = requests.post(ENDPOINT, headers=headers, json=data)

    if response.status_code == 204:
        print("Workflow dispatch triggered successfully.")
    else:
        print(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )


@app.get("/webhook")
async def verify_webhook(
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_mode: str = Query(None, alias="hub.mode"),
):
    """
    Handles the webhook verification request from Strava.
    """
    if hub_mode == "subscribe" and hub_verify_token == "STRAVA":
        return JSONResponse(content={"hub.challenge": hub_challenge}, status_code=200)
    else:
        return JSONResponse(content={"error": "Verification failed"}, status_code=400)


@app.post("/webhook")
def handle_webhook(content: dict):
    """
    Handles the webhook event from Strava.
    """
    print(content)

    dispatch(content)

    return JSONResponse(content={"message": "Received webhook event"}, status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
