import datetime
from typing import Literal

import pandas as pd

from src.app.config import Settings
from src.database.models import NameSuggestion
from src.tasks.etl.base import ETL
from src.tasks.name_generation import generate_activity_name_with_gemini


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
        number_of_options: int = 10,
    ):
        super().__init__(settings=settings)
        self.llm_model = llm_model
        self.activity_id = activity_id
        self.days = days
        self.temperature = temperature
        self.number_of_options = number_of_options

    def extract(self):
        self._activity = self.db.get_activity_by_id(activity_id=self.activity_id)
        athlete_id = self._activity.athlete_id

        before = self._activity.start_date_local + datetime.timedelta(days=1)
        after = before - datetime.timedelta(days=self.days)

        activities = self.db.get_activities_by_date_range(
            athlete_id=athlete_id, before=before, after=after
        )

        self._activities = [self._activity] + activities

    def transform(self):
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
        ]

        activities_df = activities_df[
            activities_df["sport_type"] == self._activity.sport_type
        ]

        activities_df = activities_df[columns]
        activities_df = activities_df.dropna(axis=1, how="all")

        self._activities_df = activities_df.rename({"activity_id": "id"}, axis=1)

    def load(self):
        name_results, prompt_response = generate_activity_name_with_gemini(
            activity_id=self.activity_id,
            llm_model=self.llm_model,
            data=self._activities_df,
            number_of_options=self.number_of_options,
            temperature=self.temperature,
            settings=self.settings,
        )

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
