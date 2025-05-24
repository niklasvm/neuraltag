from __future__ import annotations

import pandas as pd


import logging
# from google import genai


from pathlib import Path
import jinja2 as j2

from src.tasks.etl.naming_strategies.base import BaseNamingStrategy

logger = logging.getLogger(__name__)


PROMPT_V2 = j2.Template(
    (Path(__file__).parent / "prompt_v2.j2").read_text(), undefined=j2.StrictUndefined
)


class NamingStrategyV2(BaseNamingStrategy):
    def _preprocess_data(self):
        self.data["avg_elevation_gain_per_km"] = (
            1.0 * self.data["total_elevation_gain"] / self.data["distance_km"]
        )
        columns_to_percentile = [
            "average_heartrate",
            "max_heartrate",
            "total_elevation_gain",
            "weighted_average_watts",
            "moving_time_minutes",
            "distance_km",
            "pace_min_per_km",
            "suffer_score",
            "avg_elevation_gain_per_km",
        ]
        for column in columns_to_percentile:
            if column in self.data:
                self.data[f"{column}_percentile"] = (
                    self.data[column].rank(pct=True).round(2)
                )

    def _create_prompt(self, input: pd.Series, context_data: pd.DataFrame) -> str:
        return PROMPT_V2.render(
            context_data=context_data.to_string(index=False),
            input=input.to_string(index=True),
            number_of_options=self.number_of_options,
        )
