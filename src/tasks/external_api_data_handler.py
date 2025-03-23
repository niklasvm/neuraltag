"""
This module contains the ExternalAPIDataHandler class which is responsible for
interacting with external APIs and storing the data in the database.
"""

from __future__ import annotations
import datetime
import logging
from typing import Optional
import uuid
import pandas as pd
from pydantic import BaseModel
from stravalib import Client
from src.app.config import Settings
from src.database.adapter import Database
from src.database.models import Activity, Auth, NameSuggestion, PromptResponse, User
from src.tasks.data import summary_activity_to_activity_model
from google import genai
from src.tasks.strava import exchange_code_for_token

logger = logging.getLogger(__name__)


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
        logger.info(f"Fetched {len(summary_activities)} activities")

        activities: list[Activity] = []

        logger.info("Processing activities...")
        for summary_activity in summary_activities:
            activity = summary_activity_to_activity_model(summary_activity)
            activities.append(activity)

        logger.info("Loading activities into the database...")
        self.db.add_activities_bulk(activities)
        logger.info("Activities loaded into the database")

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
        name_results, prompt_response = generate_activity_name_with_gemini(
            activity_id=activity_id,
            data=activities_df,
            number_of_options=number_of_options,
            api_key=self.settings.gemini_api_key,
            temperature=temperature,
        )

        self.db.add_prompt_response(prompt_response)

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


class NameResult(BaseModel):
    name: str
    description: str
    probability: float


prompt = """
[BEGIN CONTEXT]
{context_data}
[END CONTEXT]

Given the following input:
{input}

[PROMPT]
Provide {number_of_options} options for a name for the input activity that is consistent with the data. The names can have one or more emojis. For each name, explain in detail why it was chosen.
Avoid using boring names like Afternoon Run, Evening Pilates or Morning Swim witin the name. Rather be creative and use names that are fun and engaging.
"""


def generate_activity_name_with_gemini(
    activity_id: int,
    data: pd.DataFrame,
    number_of_options: int,
    api_key: str,
    temperature: Optional[float] = None,
) -> tuple[list[NameResult], PromptResponse]:
    input = data[data["id"] == activity_id].iloc[0]
    context_data = data.drop(data[data["id"] == activity_id].index)

    del input["name"]
    del input["id"]
    del context_data["id"]

    # create context
    rendered_prompt = prompt.format(
        context_data=context_data.to_string(index=False),
        input=input.to_string(index=True),
        number_of_options=number_of_options,
    )

    with open("prompt.txt", "w") as f:
        f.write(rendered_prompt)

    client = genai.Client(api_key=api_key)

    config = {
        "response_schema": list[NameResult],
        "response_mime_type": "application/json",
    }
    if temperature:
        config["temperature"] = temperature

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=rendered_prompt,
        config=config,
    )

    prompt_response = PromptResponse(
        activity_id=activity_id,
        prompt=rendered_prompt,
        response=response.text,
    )

    # parse response
    results = response.parsed

    return results, prompt_response
