import unittest
from unittest.mock import patch
import pandas as pd
from stravalib.model import RelaxedSportType

from src.gemini import NameResult
import src.naming


class TestNaming(unittest.TestCase):
    @patch.object(src.naming, "Pushbullet")
    @patch.object(src.naming, "generate_activity_name_with_gemini")
    @patch.object(src.naming, "extract_data_from_weight_training_activities")
    @patch.object(src.naming, "extract_data_from_run_activities")
    @patch.object(src.naming, "get_strava_activities")
    @patch.object(src.naming, "authenticate_strava")
    @patch.object(src.naming, "load_dotenv")
    def test_end_to_end(
        self,
        mock_load_dotenv,
        mock_client,
        mock_get_activities,
        mock_extract_run,
        mock_extract_weight_training,
        mock_gemini,
        mock_pb,
    ):
        mock_get_activities.return_value = pd.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "name": [
                    "Morning Run",
                    "Afternoon Run",
                    "Morning Weight Training",
                    "Afternoon Weight Training",
                ],
                "sport_type": [
                    RelaxedSportType("Run"),
                    RelaxedSportType("Run"),
                    RelaxedSportType("WeightTraining"),
                    RelaxedSportType("WeightTraining"),
                ],
            }
        )
        mock_extract_run.return_value = pd.DataFrame(
            {
                "id": [1, 2],
                "name": ["Morning Run", "Afternoon Run"],
            }
        )
        mock_extract_weight_training.return_value = pd.DataFrame(
            {
                "id": [3, 4],
                "name": ["Morning Weight Training", "Afternoon Weight Training"],
            }
        )
        mock_gemini.return_value = [
            NameResult(name="Morning Run", description="Morning Run", probability=0.9),
            NameResult(
                name="Afternoon Run", description="Afternoon Run", probability=0.9
            ),
        ]
        src.naming.name_all_activities(days=365)


if __name__ == "__main__":
    unittest.main()
