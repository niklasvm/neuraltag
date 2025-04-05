"""
ETL for:
* Athlete
* Historic Activities
* Name Suggestions

Onboarding etl = athlete + historic activities
"""

from abc import ABC, abstractmethod
import datetime
from typing import Literal
import uuid

import pandas as pd
from stravalib import Client

from src.app.config import Settings
from src.database.adapter import Database
from src.database.models import Activity, Auth, NameSuggestion, User
from src.tasks.data import summary_activity_to_activity_model
from src.tasks.name_generation import generate_activity_name_with_gemini
from src.tasks.strava import get_strava_client


class ETL(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

        self.db = Database(
            connection_string=settings.postgres_connection_string,
            encryption_key=settings.encryption_key,
        )

    def extract(self):
        """Extract data from the source."""

    def transform(self):
        """Transform data"""

    @abstractmethod
    def load(self):
        """Load data into the target."""

    def run(self):
        """Run the ETL process."""
        self.extract()
        self.transform()
        return self.load()


class AuthETL(ETL):
    def __init__(self, code: str, scope: str, settings: Settings):
        super().__init__(settings=settings)
        self.code = code
        self.scope = scope

    def extract(self):
        client = Client()
        self._token_response = client.exchange_code_for_token(
            client_id=self.settings.strava_client_id,
            client_secret=self.settings.strava_client_secret,
            code=self.code,
        )

    def load(self):
        auth = Auth(
            uuid=uuid.uuid4(),
            access_token=self._token_response["access_token"],
            refresh_token=self._token_response["refresh_token"],
            expires_at=self._token_response["expires_at"],
            scope=self.scope,
        )
        self.db.add_auth(auth)
        return auth.uuid


class UserETL(ETL):
    def __init__(self, settings: Settings, auth_uuid: int):
        super().__init__(settings=settings)
        self.auth_uuid = auth_uuid

    def extract(self):
        auth = self.db.get_auth(self.auth_uuid)
        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )
        self._athlete = client.get_athlete()

    def load(self):
        self.db.add_user(
            User(
                athlete_id=self._athlete.id,
                auth_uuid=self.auth_uuid,
                name=self._athlete.firstname,
                lastname=self._athlete.lastname,
                sex=self._athlete.sex,
                profile=self._athlete.profile,
                profile_medium=self._athlete.profile_medium,
                city=self._athlete.city,
                state=self._athlete.state,
                country=self._athlete.country,
            )
        )


class SingleActivityETL(ETL):
    def __init__(self, settings: Settings, activity_id: int, athlete_id: int):
        super().__init__(settings=settings)
        self.activity_id = activity_id
        self.athlete_id = athlete_id

    def extract(self):
        auth = self.db.get_auth_by_athlete_id(self.athlete_id)

        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )
        self._activity = client.get_activity(self.activity_id)

    def transform(self):
        self._activity_model = summary_activity_to_activity_model(self._activity)

    def load(self):
        self.db.add_activity(self._activity_model)
        return self._activity_model


class ActivitiesETL(ETL):
    def __init__(
        self,
        settings: Settings,
        auth_uuid: int,
        before: datetime.datetime,
        after: datetime.datetime,
    ):
        super().__init__(settings=settings)
        self.auth_uuid = auth_uuid
        self.before = before
        self.after = after

    def extract(self):
        auth = self.db.get_auth(self.auth_uuid)
        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )
        self._summary_activities = client.get_activities(
            after=self.after, before=self.before
        )
        self._summary_activities = [x for x in self._summary_activities]

    def transform(self):
        self._activities: list[Activity] = []
        for summary_activity in self._summary_activities:
            activity = summary_activity_to_activity_model(summary_activity)
            self._activities.append(activity)

    def load(self):
        self.db.add_activities_bulk(self._activities)


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
