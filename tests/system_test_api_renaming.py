import os
from pprint import pp
from dotenv import load_dotenv
import requests
import json

load_dotenv(override=True)


def post_webhook(url, data):
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    pp(f"Response from {url}: {response.json()}")


localhost_8000_url = "http://localhost:8000/webhook"
# # create
# event_data = {
#     "aspect_type": "create",
#     "event_time": 13787607165,
#     "object_type": "activity",
#     "owner_id": 1411289,
#     "subscription_id": 999999,
#     "object_id": 14069608165,
# }


# update
event_data = {
    "aspect_type": "update",
    "event_time": 13787607165,
    "object_type": "activity",
    "owner_id": int(os.environ["MY_ATHLETE_ID"]),
    "subscription_id": 999999,
    "object_id": int(os.environ["MY_ACTIVITY_ID"]),
    "updates": {
        "title": "Rename",
    },
}


post_webhook(localhost_8000_url, event_data)
