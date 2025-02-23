import datetime
import re
from stravalib.client import Client
import os
from stravalib.model import RelaxedSportType
from pushbullet import Pushbullet


def update_weight_training_activity_names(days, token_dict):
    """Updates the names of weight training activities on Strava based on the day of the week.

    Args:
        days (int): The number of days back to check for activities.
        token_dict (dict): A dictionary containing the Strava API access token, refresh token, and expiration time.
            The dictionary should have the following keys:
                - "access_token" (str): The Strava API access token.
                - "refresh_token" (str): The Strava API refresh token.
                - "expires_at" (int): The expiration time of the access token as a Unix timestamp.

    Returns:
        None: This function does not return any value. It updates the activity names directly on Strava
              and sends push notifications via Pushbullet.

    Raises:
        Exception: If there are issues connecting to the Strava API or Pushbullet.

    Details:
        The function retrieves weight training activities from Strava within the specified number of days.
        It infers a new name for each activity based on the day of the week the activity occurred:
            - Monday/Tuesday: "Pull day"
            - Wednesday/Thursday: "Leg day"
            - Friday/Saturday: "Push day 💪"
            - Sunday: "Unknown"
        It then updates the activity name on Strava and sends a push notification using Pushbullet
        to confirm the update.  It only updates activities whose names contain "Weight Training".
    """
    client = Client(
        access_token=token_dict["access_token"],
        refresh_token=token_dict["refresh_token"],
        token_expires=token_dict["expires_at"],
    )
    client.refresh_access_token(
        client_id=token_dict["STRAVA_CLIENT_ID"],
        client_secret=token_dict["STRAVA_CLIENT_SECRET"],
        refresh_token=token_dict["refresh_token"],
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
            inferred_name = "Push day 💪"
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

    pb = Pushbullet(os.environ["PUSHBULLET_API_KEY"])

    for result in results:
        print(f"Renaming {result['id']} to {result['inferred_name']}")
        client.update_activity(activity_id=result["id"], name=result["inferred_name"])
        pb.push_note(
            "Strava Activity Renamed",
            f"Activity {result['id']} renamed to {result['inferred_name']}",
        )


if __name__ == "__main__":
    # with open("token.json", "r") as f:
    #     token_dict = load(f)
    import json
    from dotenv import load_dotenv

    load_dotenv(override=True)
    token_dict = json.loads(os.environ["STRAVA_TOKEN"])
    update_weight_training_activity_names(days=1, token_dict=token_dict)
