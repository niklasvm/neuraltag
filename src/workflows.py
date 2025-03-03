import datetime
import json
import logging
import os

from dotenv import load_dotenv
import pandas as pd

from stravalib import Client

from src.data import (
    fetch_activity_data,
    fetch_historic_activity_data,
    process_activity,
)

from src.gemini import generate_activity_name_with_gemini
from pushbullet import Pushbullet
import argparse



def login_user(code: str, scope: str) -> int | None:
    """Exchanges a Strava authorization code for an access token, retrieves the athlete's information, and stores the authentication details and athlete data in a database.
    Args:
        code (str): The Strava authorization code received from the user.
        scope (str): The scope of the authorization.
    """

    # load_dotenv(override=True)

    # exchange code for token
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        code=code,
    )
    access_token = token_response["access_token"]

    token_response["STRAVA_CLIENT_ID"] = os.environ["STRAVA_CLIENT_ID"]
    token_response["STRAVA_CLIENT_SECRET"] = os.environ["STRAVA_CLIENT_SECRET"]

    with open("token.json", "w") as f:
        json.dump(token_response, f)

    # get athlete
    client.access_token = access_token
    athlete = client.get_athlete()

    return athlete.id


def rename_workflow(activity_id: int):
    load_dotenv(override=True)

    days = 365
    temperature = 2

    gemini_named_description = "automagically named with Gemini 🤖"

    token = json.loads(os.environ["STRAVA_TOKEN"])
    for key, value in token.items():
        os.environ[key] = str(value)

    client = Client(
        access_token=os.environ["access_token"],
        refresh_token=os.environ["refresh_token"],
        token_expires=os.environ["expires_at"],
    )
    client.refresh_access_token(
        client_id=os.environ["STRAVA_CLIENT_ID"],
        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
        refresh_token=os.environ["refresh_token"],
    )

    activity = fetch_activity_data(
        client=client,
        activity_id=activity_id,
    )

    # if gemini_named_description in str(activity.description):
    #     print(f"Activity {activity_id} already named with Gemini 🤖")
    #     return

    before = activity.start_date_local + datetime.timedelta(days=1)
    after = before - datetime.timedelta(days=days)
    activities = fetch_historic_activity_data(
        client=client,
        after=after,
        before=before,
    )

    activity = process_activity(activity)
    activities = [process_activity(x) for x in activities]

    activities_df = pd.DataFrame(activities)

    columns = [
        "id",
        "date",
        "time",
        "day_of_week",
        "name",
        "average_heartrate",
        "max_heartrate",
        "total_elevation_gain",
        "weighted_average_watts",
        "moving_time_minutes",
        "distance_km",
        "sport_type",
        "start_lat",
        "start_lng",
        "end_lat",
        "end_lng",
        "map_centroid_lat",
        "map_centroid_lon",
        "map_area",
    ]
    activities_df = activities_df[columns]

    activities_df = activities_df[activities_df["sport_type"] == activity["sport_type"]]
    activities_df = activities_df.dropna(axis=1, how="all")

    name_results = generate_activity_name_with_gemini(
        activity_id=activity_id,
        data=activities_df,
        number_of_options=3,
        api_key=os.environ["GEMINI_API_KEY"],
        temperature=temperature,
    )
    print(f"Name suggestions: {name_results}")

    top_name_suggestion = name_results[0].name
    top_name_description = name_results[0].description
    print(
        f"Top name suggestion for activity {activity_id}: {top_name_suggestion}"
    )

    client.update_activity(
        activity_id=activity_id,
        name=top_name_suggestion,
        description=gemini_named_description,
    )

    # notify via pushbullet
    pb = Pushbullet(os.environ["PUSHBULLET_API_KEY"])
    pb.push_note(title=top_name_suggestion, body=top_name_description)


if __name__ == "__main__":
    # get arg from command line

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--activity_id", type=int, required=True, help="Strava activity ID"
    )
    args = parser.parse_args()

    rename_workflow(activity_id=args.activity_id)
