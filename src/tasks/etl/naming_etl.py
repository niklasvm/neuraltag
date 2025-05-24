from __future__ import annotations
import datetime
from typing import Literal

import pandas as pd

from src.app.config import Settings
from src.database.models import NameSuggestion
from src.tasks.etl.base import ETL

import logging
from typing import Optional
from pydantic import BaseModel
from src.database.models import PromptResponse
from google import genai

from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from prompts import PROMPT_V1

logger = logging.getLogger(__name__)


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


class NameResult(BaseModel):
    name: str
    description: str
    probability: float


def _run_agent(
    *, activity_id: int, rendered_prompt: str, temperature: float, llm_model: str
):
    # ollama_model = OpenAIModel(
    #     model_name='deepseek-r1:latest', provider=OpenAIProvider(base_url='http://localhost:11434/v1')
    # )
    fallback_nodel = FallbackModel(
        llm_model,
        "google-gla:gemini-2.0-flash",
        "google-gla:gemini-1.5-pro",
        "google-gla:gemini-1.5-flash",
    )
    naming_agent = Agent(
        # "google-gla:gemini-1.5-pro",
        # "google-gla:gemini-2.0-flash-lite-preview-02-05",
        # "google-gla:gemini-2.5-pro-exp-03-25",
        # llm_model,
        # "openai:gpt-4o",
        # "google-vertex:gemini-2.0-flash"
        # "openai:gpt-4o-mini"
        # ollama_model,
        fallback_nodel,
        instrument=True,
        retries=1,
        result_type=list[NameResult],
        model_settings=ModelSettings(
            temperature=temperature,
        ),
    )

    result = naming_agent.run_sync(
        rendered_prompt,
    )

    prompt_response = PromptResponse(
        activity_id=activity_id,
        prompt=rendered_prompt,
        response=str(result.data),
        llm_model=llm_model,
        temperature=temperature,
    )

    # parse response
    return prompt_response, result.data


def run_genai(
    activity_id: int, api_key: str, temperature: Optional[float], rendered_prompt: str
):
    client = genai.Client(api_key=api_key)

    config = {
        "response_schema": list[NameResult],
        "response_mime_type": "application/json",
    }
    if temperature:
        config["temperature"] = temperature

    # MODEL="gemini-2.0-flash"
    MODEL = "gemini-2.5-pro-exp-03-25"
    response = client.models.generate_content(
        model=MODEL,
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
    return prompt_response, results


def generate_activity_name_with_gemini(
    activity_id: int,
    llm_model: str,
    data: pd.DataFrame,
    number_of_options: int,
    temperature: float,
    settings: Settings,
) -> tuple[list[NameResult], PromptResponse]:
    input = data[data["id"] == activity_id].iloc[0]
    context_data = data.drop(data[data["id"] == activity_id].index)

    del input["name"]
    del input["id"]
    del context_data["id"]

    # create context
    rendered_prompt = PROMPT_V1.render(
        context_data=context_data.to_string(index=False),
        input=input.to_string(index=True),
        number_of_options=number_of_options,
    )

    with open("prompt.txt", "w") as f:
        f.write(rendered_prompt)

    # prompt_response_old, results_old = run_genai(
    #     activity_id, api_key, temperature, rendered_prompt
    # )
    prompt_response, results = _run_agent(
        activity_id=activity_id,
        llm_model=llm_model,
        rendered_prompt=rendered_prompt,
        temperature=temperature,
    )

    return results, prompt_response
