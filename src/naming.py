import json
import os
from pushbullet import Pushbullet
from dotenv import load_dotenv

from src.data import (
    extract_data_from_run_activities,
    extract_data_from_weight_training_activities,
)
from src.gemini import generate_activity_name_with_gemini
from src.strava import authenticate_strava, get_strava_activities


def name_all_activities(days: int = 365):
    load_dotenv(override=True)

    # get strava activities
    token_dict = json.loads(os.environ["STRAVA_TOKEN"])
    client = authenticate_strava(token_dict)
    activities = get_strava_activities(client, days=days)

    # name activities
    run_names = name_run_activities(activities)
    weight_training_names = name_weight_training_activities(activities)
    all_names = run_names | weight_training_names

    # publish names
    pb = Pushbullet(os.environ["PUSHBULLET_API_KEY"])
    for id, name_results in all_names.items():
        best_name = name_results[0].name
        options = "\n".join(
            [f"{result.name}: {result.description}" for result in name_results]
        )
        print(f"{id}: {best_name}")
        client.update_activity(activity_id=id, name=best_name)
        pb.push_note(
            title=f"Updated activity {id} to {best_name}",
            body=f"Options:\n{options}",
        )


def name_run_activities(activities: list):
    run_regex = r"(Morning|Afternoon|Evening|Night)\sRun"
    run_activities = extract_data_from_run_activities(activities)

    unnamed_activities = run_activities[
        run_activities["name"].str.contains(run_regex, regex=True)
    ]
    unnamed_activity_ids = unnamed_activities["id"].to_list()

    names = {}
    for id in unnamed_activity_ids:
        names[id] = generate_activity_name_with_gemini(
            activity_id=id,
            data=run_activities,
            number_of_options=3,
            api_key=os.environ["GEMINI_API_KEY"],
        )

    return names


def name_weight_training_activities(activities: list):
    weight_training_regex = r"(Morning|Afternoon|Evening|Night)\sWeight Training"
    weight_training_activities = extract_data_from_weight_training_activities(
        activities
    )

    unnamed_activities = weight_training_activities[
        weight_training_activities["name"].str.contains(
            weight_training_regex, regex=True
        )
    ]
    unnamed_activity_ids = unnamed_activities["id"].to_list()

    names = {}
    for id in unnamed_activity_ids:
        names[id] = generate_activity_name_with_gemini(
            activity_id=id,
            data=weight_training_activities,
            number_of_options=3,
            api_key=os.environ["GEMINI_API_KEY"],
        )
    return names


if __name__ == "__main__":
    name_all_activities(days=365)

    # test
    with open("README.md", "a") as f:
        f.write("hello world")
