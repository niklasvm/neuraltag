import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.application.app import app
import os
from dotenv import load_dotenv

load_dotenv()


class TestApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.strava_verify_token = os.environ.get("STRAVA_VERIFY_TOKEN")
        self.github_user = os.environ.get("GITHUB_USER")
        self.repo = os.environ.get("REPO")
        self.github_pat = os.environ.get("GITHUB_PAT")
        self.workflow_file = os.environ.get("WORKFLOW_FILE")

    def test_verify_webhook_success(self):
        response = self.client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": self.strava_verify_token,
                "hub.challenge": "challenge_string",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"hub.challenge": "challenge_string"})

    def test_verify_webhook_failure(self):
        response = self.client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "challenge_string",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Verification failed"})

    def test_handle_webhook(self):
        response = self.client.post(
            "/webhook", json={"aspect_type": "create", "object_type": "activity"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Received webhook event"})

    @patch("requests.post")
    def test_trigger_gha(self, mock_post):
        from src.application.app import trigger_gha

        trigger_gha()
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(
            args[0],
            f"https://api.github.com/repos/{self.github_user}/{self.repo}/actions/workflows/{self.workflow_file}/dispatches",
        )
        self.assertEqual(
            kwargs["headers"]["Authorization"], f"Bearer {self.github_pat}"
        )
        self.assertEqual(kwargs["json"]["ref"], "master")

    @patch("src.application.app.trigger_gha")
    def test_dispatch_activity_create(self, mock_trigger_gha):
        from src.application.app import dispatch

        content = {"object_type": "activity", "aspect_type": "create"}
        dispatch(content)
        mock_trigger_gha.assert_called_once()

    @patch("src.application.app.trigger_gha")
    def test_dispatch_activity_update(self, mock_trigger_gha):
        from src.application.app import dispatch

        content = {"object_type": "activity", "aspect_type": "update"}
        dispatch(content)
        mock_trigger_gha.assert_called_once()

    @patch("src.application.app.trigger_gha")
    def test_dispatch_no_activity(self, mock_trigger_gha):
        from src.application.app import dispatch

        content = {"object_type": "athlete", "aspect_type": "update"}
        dispatch(content)
        mock_trigger_gha.assert_not_called()


if __name__ == "__main__":
    unittest.main()
