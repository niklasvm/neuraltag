import unittest
from unittest.mock import patch
import pandas as pd
from stravalib.model import RelaxedSportType

from src.gemini import NameResult
import src.naming


class TestNaming(unittest.TestCase):
    @patch.dict(
        src.naming.os.environ,
        {
            "STRAVA_TOKEN": '{"access_token": ""}',
            "GEMINI_API_KEY": "",
            "PUSHBULLET_API_KEY": "",
        },
    )
    @patch.object(src.naming, "Pushbullet")
    @patch.object(src.naming, "generate_activity_name_with_gemini")
    @patch.object(src.naming, "pre_process_data")
    @patch.object(src.naming, "get_strava_activities")
    @patch.object(src.naming, "authenticate_strava")
    @patch.object(src.naming, "load_dotenv")
    def test_end_to_end(
        self,
        mock_load_dotenv,
        mock_client,
        mock_get_activities,
        mock_pre_process_data,
        mock_gemini,
        mock_pb,
    ):
        mock_pre_process_data.return_value = pd.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "date": ["2022-01-01", "2022-01-01", "2022-01-01", "2022-01-01"],
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
                "rename": [True, False, True, False],
            }
        )

        mock_gemini.return_value = [
            NameResult(name="Morning Run", description="Morning Run", probability=0.9),
            NameResult(
                name="Afternoon Run", description="Afternoon Run", probability=0.9
            ),
        ]
        src.naming.name_all_activities(days=365)

        mock_gemini.assert_called()
        mock_pb.assert_called()


if __name__ == "__main__":
    unittest.main()
