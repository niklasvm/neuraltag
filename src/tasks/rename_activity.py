import datetime
import logging

import pandas as pd
from pushbullet import Pushbullet


from src.database.adapter import Database
from src.app.config import Settings

from src.database.models import Activity
from src.tasks.external_api_data_handler import ExternalAPIDataHandler
from src.tasks.telegram import TelegramBot

NEURALTAG_SIGNATURE = "named with NeuralTag 🤖"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rename_workflow(activity: Activity, settings: Settings):
    time_start = datetime.datetime.now()

    days = 365
    temperature = 2
    is_test = False

    strava_db_operations = ExternalAPIDataHandler.from_athlete_id(
        athlete_id=activity.athlete_id,
        settings=settings,
    )

    existing_description = activity.description

    # if (
    #     not is_test
    #     and NEURALTAG_SIGNATURE in str(existing_description)
    #     and activity.name != "Rename"
    # ):
    #     logger.info(f"Activity {activity.activity_id} already named")
    #     return

    db = Database(
        connection_string=settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )

    before = activity.start_date_local + datetime.timedelta(days=1)
    after = before - datetime.timedelta(days=days)
    activities = db.get_activities_by_date_range(
        athlete_id=activity.athlete_id, before=before, after=after
    )

    activities = [activity] + activities

    activities_df = pd.DataFrame([activity.dict() for activity in activities])

    columns = [
        "activity_id",
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
        "pace_min_per_km",
        "map_centroid_lat",
        "map_centroid_lon",
        "map_area",
        "suffer_score",
    ]

    activities_df = activities_df[activities_df["sport_type"] == activity.sport_type]

    activities_df = activities_df[columns]
    activities_df = activities_df.dropna(axis=1, how="all")

    activities_df = activities_df.rename({"activity_id": "id"}, axis=1)

    name_suggestions = strava_db_operations.fetch_and_load_name_suggestions(
        activity_id=activity.activity_id,
        activities_df=activities_df,
        number_of_options=10,
        temperature=temperature,
    )
    if len(name_suggestions) == 0:
        logger.info(f"No name suggestions for activity {activity.activity_id}")
        return

    # sort names descending by probability
    name_suggestions = sorted(
        name_suggestions, key=lambda x: x.probability, reverse=True
    )

    # print suggestions
    for i, result in enumerate(name_suggestions):
        logger.info(
            f"Name suggestion {i + 1}: {result.name} ({result.probability}): {result.description}"
        )

    top_name_suggestion = name_suggestions[0].name
    top_name_description = name_suggestions[0].description
    logger.info(
        f"Top name suggestion for activity {activity.activity_id}: {top_name_suggestion}: {top_name_description}"
    )

    time_end = datetime.datetime.now()
    duration_seconds = (time_end - time_start).total_seconds()
    logger.info(f"Duration: {duration_seconds} seconds")

    if existing_description is None:
        existing_description = ""

    if NEURALTAG_SIGNATURE not in str(existing_description):
        new_description = f"{existing_description}\n\n{NEURALTAG_SIGNATURE}".strip()
    else:
        new_description = existing_description
    logger.info(f"New description: {new_description}")

    if not is_test:
        client = strava_db_operations.client
        client.update_activity(
            activity_id=activity.activity_id,
            name=top_name_suggestion,
            description=new_description,
        )

        # notify via pushbullet
        pb = Pushbullet(settings.pushbullet_api_key)
        pb_response = pb.push_note(title=top_name_suggestion, body=top_name_description)
        logger.info(pb_response)

        tb = TelegramBot(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            parse_mode="HTML",
        )
        tb.send_message(
            message=f"<b>Activity Renamed:</b> {top_name_suggestion}\n\n{top_name_description}"
        )
