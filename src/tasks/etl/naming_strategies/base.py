from __future__ import annotations
from abc import ABC, abstractmethod

import pandas as pd

from src.app.config import Settings

from src.database.models import PromptResponse
# from google import genai


from src.tasks.etl.naming_strategies.agent import NameResult, run_naming_agent


class BaseNamingStrategy(ABC):
    def __init__(
        self,
        activity_id: int,
        llm_model: str,
        data: pd.DataFrame,
        number_of_options: int,
        temperature: float,
        settings: Settings,
    ):
        self.activity_id = activity_id
        self.llm_model = llm_model
        self.data = data
        self.number_of_options = number_of_options
        self.temperature = temperature
        self.settings = settings

    def run(self) -> tuple[list[NameResult], PromptResponse]:
        self._preprocess_data()

        input = self.data[self.data["id"] == self.activity_id].iloc[0]
        context_data = self.data.drop(
            self.data[self.data["id"] == self.activity_id].index
        )

        del input["name"]
        del input["id"]
        del context_data["id"]
        rendered_prompt = self._create_prompt(input, context_data)

        with open("prompt.txt", "w") as f:
            f.write(rendered_prompt)

        prompt_response, results = run_naming_agent(
            activity_id=self.activity_id,
            llm_model=self.llm_model,
            rendered_prompt=rendered_prompt,
            temperature=self.temperature,
        )

        return results, prompt_response

    def _preprocess_data(self):
        """Preprocess the data before creating the prompt."""

    @abstractmethod
    def _create_prompt(self, input: pd.Series, context_data: pd.DataFrame) -> str:
        """Create the prompt for the naming strategy."""
