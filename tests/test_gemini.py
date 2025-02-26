import unittest
from unittest.mock import patch
import pandas as pd
from src.gemini import generate_activity_name_with_gemini, NameResult


class TestGemini(unittest.TestCase):
    @patch("src.gemini.genai.Client")
    def test_generate_activity_name_with_gemini_success(self, mock_client):
        # Mock the Gemini response
        mock_response = unittest.mock.MagicMock()
        mock_response.text = """
        ```json
        [
            {
                "name": "Morning Run",
                "description": "A brisk run in the morning.",
                "probability": 0.9
            },
            {
                "name": "Evening Stroll",
                "description": "A relaxing walk in the evening.",
                "probability": 0.8
            }
        ]
        ```
        """
        mock_client.return_value.models.generate_content.return_value = mock_response

        # Create sample data
        data = pd.DataFrame(
            {
                "id": [1, 2],
                "name": ["Activity 1", "Activity 2"],
                "distance": [1000, 2000],
                "duration": [600, 1200],
            }
        )

        # Call the function
        results = generate_activity_name_with_gemini(
            activity_id=1, data=data, number_of_options=2, api_key="test_api_key"
        )

        # Assertions
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], NameResult)
        self.assertEqual(results[0].name, "Morning Run")
        self.assertEqual(results[0].description, "A brisk run in the morning.")
        self.assertEqual(results[0].probability, 0.9)

    @patch("src.gemini.genai.Client")
    def test_generate_activity_name_with_gemini_empty_response(self, mock_client):
        # Mock the Gemini response to be empty
        mock_response = unittest.mock.MagicMock()
        mock_response.text = """
        ```json
        []
        ```
        """
        mock_client.return_value.models.generate_content.return_value = mock_response

        # Create sample data
        data = pd.DataFrame(
            {
                "id": [1],
                "name": ["Activity 1"],
                "distance": [1000],
                "duration": [600],
            },
            {
                "id": [2],
                "name": ["Activity 2"],
                "distance": [2000],
                "duration": [1200],
            },
        )

        # Call the function
        results = generate_activity_name_with_gemini(
            activity_id=1, data=data, number_of_options=1, api_key="test_api_key"
        )

        # Assertions
        self.assertEqual(len(results), 0)

    @patch("src.gemini.genai.Client")
    def test_generate_activity_name_with_gemini_invalid_json(self, mock_client):
        # Mock the Gemini response to be invalid JSON
        mock_response = unittest.mock.MagicMock()
        mock_response.text = "Invalid JSON"
        mock_client.return_value.models.generate_content.return_value = mock_response

        # Create sample data
        data = pd.DataFrame(
            {
                "id": [1],
                "name": ["Activity 1"],
                "distance": [1000],
                "duration": [600],
            }
        )

        # Call the function and assert that it raises an exception
        with self.assertRaises(Exception):
            generate_activity_name_with_gemini(
                activity_id=1, data=data, number_of_options=1, api_key="test_api_key"
            )


if __name__ == "__main__":
    unittest.main()
