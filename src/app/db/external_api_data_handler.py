"""
This module contains the ExternalAPIDataHandler class which is responsible for
interacting with external APIs and storing the data in the database.
"""

from __future__ import annotations
import datetime
import uuid
import pandas as pd
from stravalib import Client
from src.app.core.config import Settings
from src.app.db.adapter import Database
from src.app.db.models import Activity, Auth, NameSuggestion, User
from src.data import summary_activity_to_activity_model
from src.gemini import NameResult, generate_activity_name_with_gemini
from src.strava import exchange_code_for_token


class ExternalAPIDataHandler:
    def __init__(self, auth_uuid: int, settings: Settings):
        self.auth_uuid = auth_uuid
        self.settings = settings

        self.db = Database(
            self.settings.postgres_connection_string,
            encryption_key=self.settings.encryption_key,
        )
        auth = self.db.get_auth(auth_uuid)

        self.client: Client = Client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            token_expires=auth.expires_at,
        )
        self.client.refresh_access_token(
            client_id=self.settings.strava_client_id,
            client_secret=self.settings.strava_client_secret,
            refresh_token=auth.refresh_token,
        )

    @classmethod
    def from_athlete_id(
        cls,
        athlete_id: int,
        settings: Settings,
    ):
        db = Database(
            settings.postgres_connection_string, encryption_key=settings.encryption_key
        )
        auth = db.get_auth_by_athlete_id(athlete_id)
        return cls(auth_uuid=auth.uuid, settings=settings)

    @classmethod
    def authenticate_and_store(
        cls,
        code: str,
        scope: str,
        settings: Settings,
    ) -> ExternalAPIDataHandler:
        token_response = exchange_code_for_token(
            strava_client_id=settings.strava_client_id,
            strava_client_secret=settings.strava_client_secret,
            code=code,
        )
        db = Database(
            settings.postgres_connection_string, encryption_key=settings.encryption_key
        )

        auth = Auth(
            uuid=uuid.uuid4(),
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=token_response["expires_at"],
            scope=scope,
        )
        db.add_auth(auth)

        return cls(auth_uuid=auth.uuid, settings=settings)

    def fetch_and_load_historic_activities(
        self,
        before: datetime.datetime,
        after: datetime.datetime,
    ) -> list[Activity]:
        # load athlete into db
        athlete = self.client.get_athlete()
        self.db.add_user(User(athlete_id=athlete.id, auth_uuid=self.auth_uuid))

        summary_activities = self.client.get_activities(after=after, before=before)
        summary_activities = [x for x in summary_activities]

        activities: list[Activity] = []
        for summary_activity in summary_activities:
            activity = summary_activity_to_activity_model(summary_activity)
            activities.append(activity)

        self.db.add_activities_bulk(activities)

        return activities

    def fetch_and_load_activity(
        self,
        activity_id: int,
    ) -> Activity:
        activity = self.client.get_activity(activity_id)
        activity = summary_activity_to_activity_model(activity)
        self.db.add_activity(activity)
        return activity

    def fetch_and_load_name_suggestions(
        self,
        activity_id: int,
        activities_df: pd.DataFrame,
        number_of_options: int,
        temperature: int,
    ) -> list[NameSuggestion]:
        name_results: list[NameResult] = generate_activity_name_with_gemini(
            activity_id=activity_id,
            data=activities_df,
            number_of_options=number_of_options,
            api_key=self.settings.gemini_api_key,
            temperature=temperature,
        )

        name_suggestions = []
        for name_result in name_results:
            name_suggestion = NameSuggestion(
                activity_id=activity_id,
                name=name_result.name,
                description=name_result.description,
                probability=name_result.probability,
            )
            self.db.add_name_suggestion(name_suggestion)
            name_suggestions.append(name_suggestion)

        return name_suggestions
