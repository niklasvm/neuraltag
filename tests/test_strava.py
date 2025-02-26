import unittest
from unittest.mock import patch, MagicMock
import datetime
import os

from stravalib.model import SummaryActivity

from src.strava import authenticate_strava, get_strava_activities


class TestStrava(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "STRAVA_CLIENT_ID": "test_client_id",
            "STRAVA_CLIENT_SECRET": "test_client_secret",
        },
    )
    @patch("src.strava.Client")
    def test_authenticate_strava(self, MockClient):
        token_dict = {
            "STRAVA_CLIENT_ID": "test_client_id",
            "STRAVA_CLIENT_SECRET": "test_client_secret",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": datetime.datetime.now(),
        }
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance

        client = authenticate_strava(token_dict)

        MockClient.assert_called_with(
            access_token=token_dict["access_token"],
            refresh_token=token_dict["refresh_token"],
            token_expires=token_dict["expires_at"],
        )
        mock_client_instance.refresh_access_token.assert_called_with(
            client_id=token_dict["STRAVA_CLIENT_ID"],
            client_secret=token_dict["STRAVA_CLIENT_SECRET"],
            refresh_token=token_dict["refresh_token"],
        )
        self.assertEqual(client, mock_client_instance)

    @patch("src.strava.datetime")
    @patch("src.strava.Client")
    def test_get_strava_activities(self, MockClient, MockDatetime):
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance
        mock_activity = SummaryActivity(id=123)
        mock_client_instance.get_activities.return_value = [mock_activity]

        # Mock datetime to return a fixed date for consistent testing
        fixed_date = datetime.datetime(2024, 1, 20)
        MockDatetime.datetime.now.return_value = fixed_date
        MockDatetime.timedelta.return_value = datetime.timedelta(days=7)

        activities = get_strava_activities(mock_client_instance, 7)

        mock_client_instance.get_activities.assert_called_with(after="2024-01-13")
        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], SummaryActivity)


if __name__ == "__main__":
    unittest.main()
