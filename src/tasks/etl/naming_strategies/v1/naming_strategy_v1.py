from __future__ import annotations

import pandas as pd


import logging
# from google import genai


from pathlib import Path
import jinja2 as j2

from src.tasks.etl.naming_strategies.base import BaseNamingStrategy

logger = logging.getLogger(__name__)


PROMPT_V1 = j2.Template(
    (Path(__file__).parent / "prompt_v1.j2").read_text(), undefined=j2.StrictUndefined
)


class NamingStrategyV1(BaseNamingStrategy):
    def _create_prompt(self, input: pd.Series, context_data: pd.DataFrame) -> str:
        return PROMPT_V1.render(
            context_data=context_data.to_string(index=False),
            input=input.to_string(index=True),
            number_of_options=self.number_of_options,
        )
