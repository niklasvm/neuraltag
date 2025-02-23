from pprint import pp
import datetime
from json import load
import re
from stravalib.client import Client
import os
from stravalib.model import RelaxedSportType


def update_weight_training_activity_names(days, token_dict):
    client = Client(
        access_token=token_dict["access_token"],
        refresh_token=token_dict["refresh_token"],
        token_expires=token_dict["expires_at"],
    )

    after = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )

    activities = client.get_activities(after=after)
    activities = [x for x in activities]
    print(f"Found {len(activities)} activities")

    weight_training_activities = [
        x for x in activities if x.sport_type == RelaxedSportType("WeightTraining")
    ]
    print(f"Found {len(weight_training_activities)} weight training activities")

    results = []
    for activity in weight_training_activities:
        if not re.search(r".*Weight Training.*", activity.name):
            continue

        start_date = activity.start_date
        weekday = start_date.strftime("%A")
        if weekday in ["Monday", "Tuesday"]:
            inferred_name = "Pull day"
        elif weekday in ["Wednesday", "Thursday"]:
            inferred_name = "Leg day"
        elif weekday in ["Friday", "Saturday"]:
            inferred_name = "Push day"
        else:
            inferred_name = "Unknown"
        element = {
            "id": activity.id,
            "name": activity.name,
            "inferred_name": inferred_name,
        }
        results.append(element)

        print(
            f"{activity.id} : {activity.start_date} Renaming {activity.name} --> {inferred_name}"
        )

    print(f"Found {len(results)} activities to rename")

    for result in results:
        print(f"Renaming {result['id']} to {result['inferred_name']}")
        client.update_activity(activity_id=result["id"], name=result["inferred_name"])


if __name__ == "__main__":
    with open("token.json", "r") as f:
        token_dict = load(f)
    update_weight_training_activity_names(days=30, token_dict=token_dict)
