"""
This module contains the ExternalAPIDataHandler class which is responsible for
interacting with external APIs and storing the data in the database.
"""

from __future__ import annotations
import logging
from typing import Optional
import pandas as pd
from pydantic import BaseModel
from src.app.config import Settings
from src.database.models import PromptResponse
from google import genai

from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
import jinja2 as j2

from src.tasks.prompts import PROMPT_V1

logger = logging.getLogger(__name__)


class NameResult(BaseModel):
    name: str
    description: str
    probability: float


def run_agent(
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
    prompt_response, results = run_agent(
        activity_id=activity_id,
        llm_model=llm_model,
        rendered_prompt=rendered_prompt,
        temperature=temperature,
    )

    return results, prompt_response
