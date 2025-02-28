from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from src.naming import name_all_activities

app = FastAPI()

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
    name_all_activities(days=365)
    return JSONResponse(content={"message": "Received webhook event"}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


    
