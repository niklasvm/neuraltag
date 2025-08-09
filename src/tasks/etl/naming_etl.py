from __future__ import annotations
import datetime
import re
from typing import Literal

import pandas as pd

from src.app.config import Settings
from src.database.models import NameSuggestion
from src.tasks.etl.base import ETL

import logging


from src.tasks.etl.naming_strategies.v1.naming_strategy_v1 import NamingStrategyV1
from src.tasks.etl.naming_strategies.v2.naming_strategy_v2 import NamingStrategyV2

logger = logging.getLogger(__name__)


def run_name_activity_etl(
    llm_model: str,
    settings: Settings,
    activity_id: int,
    naming_strategy_version: str | None = None,
    days: int = 365,
    temperature: float = 2.0,
):
    etl = NameSuggestionETL(
        llm_model=llm_model,
        settings=settings,
        activity_id=activity_id,
        days=days,
        temperature=temperature,
        naming_strategy_version=naming_strategy_version,
    )
    return etl.run()


class NameSuggestionETL(ETL):
    def __init__(
        self,
        llm_model: Literal[
            # "openai:gpt-4o",
            # "openai:gpt-4o-mini",
            "google-gla:gemini-2.5-pro-exp-03-25",
            "google-gla:gemini-2.0-flash",
        ],
        settings: Settings,
        activity_id: int,
        days: int,
        temperature: float,
        naming_strategy_version: str | None = None,
        number_of_options: int = 10,
    ):
        super().__init__(settings=settings)
        self.llm_model = llm_model
        self.activity_id = activity_id
        self.days = days
        self.temperature = temperature
        self.number_of_options = number_of_options
        self.naming_strategy_version = naming_strategy_version

        if self.naming_strategy_version is None:
            self.naming_strategy_version = (
                self.db.get_naming_strategy_version_by_activity_id(self.activity_id)
            )

    def extract(self):
        self._activity = self.db.get_activity_by_id(activity_id=self.activity_id)
        athlete_id = self._activity.athlete_id

        before = self._activity.start_date_local + datetime.timedelta(days=1)
        after = before - datetime.timedelta(days=self.days)

        activities = self.db.get_activities_by_date_range(
            athlete_id=athlete_id, before=before, after=after
        )

        # exclude the activity itself from the list of activities
        activities = [
            activity
            for activity in activities
            if activity.activity_id != self.activity_id
        ]

        self._activities = [self._activity] + activities

    def transform(self):
        # blank out activities that have been named with NeuralTag 🤖 or match base strava names
        base_strava_name_regex = r"(Morning|Lunch|Afternoon|Evening|Night) (Run|Ride|Swim|Pilates|Mountain Bike Ride|Workout|Weight Training|Trail Run|HIIT)"
        blanked_out_count = 0
        for idx, activity in enumerate(self._activities):
            activity.description = str(activity.description)
            if (
                str(activity.description)
                and "named with NeuralTag 🤖" in activity.description
                or re.search(base_strava_name_regex, activity.name)
            ):
                activity.name = ""
                activity.description = ""

                # update the activity in the database
                self._activities[idx] = activity

                blanked_out_count += 1

        logger.info(
            f"Blanked out {blanked_out_count} activities with NeuralTag 🤖 or base Strava names."
        )

        activities_df = pd.DataFrame([activity.dict() for activity in self._activities])
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
            "stream_data"
        ]

        activities_df = activities_df[
            activities_df["sport_type"] == self._activity.sport_type
        ]

        activities_df = activities_df[columns]
        activities_df = activities_df.dropna(axis=1, how="all")

        self._activities_df = activities_df.rename({"activity_id": "id"}, axis=1)

    def load(self):
        mapping = {"v1": NamingStrategyV1, "v2": NamingStrategyV2}

        try:
            cls = mapping[self.naming_strategy_version]
        except KeyError:
            raise ValueError(
                f"Prompt version {self.naming_strategy_version} not supported. Supported versions are: {', '.join(mapping.keys())}"
            )

        naming_strategy = cls(
            activity_id=self.activity_id,
            llm_model=self.llm_model,
            data=self._activities_df,
            number_of_options=self.number_of_options,
            temperature=self.temperature,
            settings=self.settings,
        )

        name_results, prompt_response = naming_strategy.run()


        self.db.add_prompt_response(prompt_response)

        # sort names descending by probability
        name_results = sorted(name_results, key=lambda x: x.probability, reverse=True)

        name_suggestions = []
        for name_result in name_results:
            name_suggestion = NameSuggestion(
                activity_id=self.activity_id,
                name=name_result.name,
                description=name_result.description,
                probability=name_result.probability,
                prompt_response_id=prompt_response.uuid,
            )
            self.db.add_name_suggestion(name_suggestion)
            name_suggestions.append(name_suggestion)

        return name_suggestions


# TODO: Remove as unused
# def run_genai(
#     activity_id: int, api_key: str, temperature: Optional[float], rendered_prompt: str
# ):
#     client = genai.Client(api_key=api_key)

#     config = {
#         "response_schema": list[NameResult],
#         "response_mime_type": "application/json",
#     }
#     if temperature:
#         config["temperature"] = temperature

#     # MODEL="gemini-2.0-flash"
#     MODEL = "gemini-2.5-pro-exp-03-25"
#     response = client.models.generate_content(
#         model=MODEL,
#         contents=rendered_prompt,
#         config=config,
#     )

#     prompt_response = PromptResponse(
#         activity_id=activity_id,
#         prompt=rendered_prompt,
#         response=response.text,
#     )

#     # parse response
#     results = response.parsed
#     return prompt_response, results
