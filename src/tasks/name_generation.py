"""
This module contains the ExternalAPIDataHandler class which is responsible for
interacting with external APIs and storing the data in the database.
"""

from __future__ import annotations
import logging
from typing import Optional
import pandas as pd
from pydantic import BaseModel
from src.database.models import PromptResponse
from google import genai
# from src.tasks.strava import exchange_code_for_token

logger = logging.getLogger(__name__)


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
Also provide a probability to describe confidence in the name. Order the final names from highest to lowest probability.
Avoid using boring names like Afternoon Run, Evening Pilates or Morning Swim witin the name. Rather be creative and use names that are fun and engaging.
"""

# MODEL="gemini-2.0-flash"
MODEL = "gemini-2.5-pro-exp-03-25"


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

    return results, prompt_response
