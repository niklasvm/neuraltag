import json
import os
from pushbullet import Pushbullet
from dotenv import load_dotenv

from src.data import (
    pre_process_data,
)
from src.gemini import generate_activity_name_with_gemini
from src.strava import authenticate_strava, get_strava_activities


def name_all_activities(days: int = 365):
    load_dotenv(override=True)

    # get strava activities
    token_dict = json.loads(os.environ["STRAVA_TOKEN"])
    client = authenticate_strava(token_dict)
    activities = get_strava_activities(client, days=days)

    df = pre_process_data(
        activities=activities, supported_sports=["Run", "Weight Training"]
    )
    # df.iloc[-3:, df.columns.get_loc("rename")] = True  # to simulate

    ids_to_rename = df[df["rename"]]["id"].to_list()
    print(f"Found {len(ids_to_rename)} activities to rename")

    pb = Pushbullet(os.environ["PUSHBULLET_API_KEY"])
    for activity_id in ids_to_rename:
        sport_type = df[df["id"] == activity_id]["sport_type"].values[0]
        existing_name = df[df["id"] == activity_id]["name"].values[0]
        date = df[df["id"] == activity_id]["date"].values[0]

        sport_activities = df[df["sport_type"] == sport_type]
        del sport_activities["sport_type"]

        # remove columns that are all NaN
        sport_activities = sport_activities.dropna(axis=1, how="all")
        del sport_activities["rename"]

        # generate name
        name_results = generate_activity_name_with_gemini(
            activity_id=activity_id,
            data=sport_activities,
            number_of_options=3,
            api_key=os.environ["GEMINI_API_KEY"],
        )

        # publish name
        best_name = name_results[0].name
        options = "\n".join(
            [f"{result.name}: {result.description}" for result in name_results]
        )
        print(f"Renaming: {activity_id} on {date} {existing_name} --> {best_name}")
        client.update_activity(
            activity_id=activity_id,
            name=f"{best_name}",
            description="automagically named with Gemini 🤖",
        )
        pb.push_note(
            title=f"Updated activity {id} to {best_name}",
            body=f"Options:\n{options}",
        )


if __name__ == "__main__":
    name_all_activities(days=365)
