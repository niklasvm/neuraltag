import unittest
from unittest.mock import MagicMock, patch
from src.data import pre_process_data
from stravalib.model import SummaryActivity


class TestPreProcessData(unittest.TestCase):
    def test_empty_activities(self):
        activities = []
        supported_sports = ["Run", "Ride"]
        df = pre_process_data(activities, supported_sports)
        self.assertTrue(df.empty)

    @patch("src.data.polyline.decode")
    @patch("src.data.Polygon")
    def test_activity_with_location(self, mock_polygon, mock_polyline_decode):
        mock_polyline_decode.return_value = [(1, 2), (3, 4)]
        mock_poly_instance = MagicMock()
        mock_polygon.return_value = mock_poly_instance
        mock_poly_instance.centroid = MagicMock()
        mock_poly_instance.centroid.x = 5
        mock_poly_instance.centroid.y = 6
        mock_poly_instance.area = 10

        activity = MagicMock(spec=SummaryActivity)
        activity.id = 123
        activity.start_date_local = MagicMock()
        activity.start_date_local.strftime.return_value = "2023-01-01"
        activity.name = "Test Activity"
        activity.average_heartrate = 150
        activity.max_heartrate = 180
        activity.total_elevation_gain = 100
        activity.weighted_average_watts = 200
        activity.moving_time = 3600
        activity.distance = 10000
        activity.sport_type = MagicMock()
        activity.sport_type.root = "Run"
        activity.start_latlng = MagicMock()
        activity.start_latlng.lat = 40.0
        activity.start_latlng.lon = -70.0
        activity.end_latlng = MagicMock()
        activity.end_latlng.lat = 41.0
        activity.end_latlng.lon = -71.0
        activity.map = MagicMock()
        activity.map.summary_polyline = "encoded_polyline"

        activities = [activity]
        supported_sports = ["Run"]
        df = pre_process_data(activities, supported_sports)

        self.assertEqual(len(df), 1)
        self.assertEqual(df["id"][0], 123)
        self.assertEqual(df["lat"][0], 40.0)
        self.assertEqual(df["lng"][0], -70.0)
        self.assertEqual(df["end_lat"][0], 41.0)
        self.assertEqual(df["end_lng"][0], -71.0)
        self.assertIn("centroid_lat", df.columns)
        self.assertIn("centroid_lon", df.columns)
        self.assertIn("area", df.columns)
        self.assertEqual(df["centroid_lat"][0], 5)
        self.assertEqual(df["centroid_lon"][0], 6)
        self.assertEqual(df["area"][0], 10)

    @patch("src.data.polyline.decode")
    @patch("src.data.Polygon")
    def test_activity_without_location(self, mock_polygon, mock_polyline_decode):
        mock_polyline_decode.return_value = [(1, 2), (3, 4)]
        mock_poly_instance = MagicMock()
        mock_polygon.return_value = mock_poly_instance
        mock_poly_instance.centroid = MagicMock()
        mock_poly_instance.centroid.x = 5
        mock_poly_instance.centroid.y = 6
        mock_poly_instance.area = 10

        activity = MagicMock(spec=SummaryActivity)
        activity.id = 123
        activity.start_date_local = MagicMock()
        activity.start_date_local.strftime.return_value = "2023-01-01"
        activity.name = "Test Activity"
        activity.average_heartrate = None
        activity.max_heartrate = None
        activity.total_elevation_gain = 100
        activity.weighted_average_watts = None
        activity.moving_time = 3600
        activity.distance = 10000
        activity.sport_type = MagicMock()
        activity.sport_type.root = "Run"
        activity.start_latlng = None
        activity.end_latlng = None
        activity.map = MagicMock()
        activity.map.summary_polyline = "encoded_polyline"

        activities = [activity]
        supported_sports = ["Run"]
        df = pre_process_data(activities, supported_sports)

        self.assertEqual(len(df), 1)
        self.assertNotIn("lat", df.columns)
        self.assertNotIn("lng", df.columns)
        self.assertNotIn("end_lat", df.columns)
        self.assertNotIn("end_lng", df.columns)
        self.assertIn("centroid_lat", df.columns)
        self.assertIn("centroid_lon", df.columns)
        self.assertIn("area", df.columns)
        self.assertEqual(df["centroid_lat"][0], 5)
        self.assertEqual(df["centroid_lon"][0], 6)
        self.assertEqual(df["area"][0], 10)

    @patch("src.data.polyline.decode")
    @patch("src.data.Polygon")
    def test_activity_zero_distance(self, mock_polygon, mock_polyline_decode):
        mock_polyline_decode.return_value = [(1, 2), (3, 4)]
        mock_poly_instance = MagicMock()
        mock_polygon.return_value = mock_poly_instance
        mock_poly_instance.centroid = MagicMock()
        mock_poly_instance.centroid.x = 5
        mock_poly_instance.centroid.y = 6
        mock_poly_instance.area = 10

        activity = MagicMock(spec=SummaryActivity)
        activity.id = 123
        activity.start_date_local = MagicMock()
        activity.start_date_local.strftime.return_value = "2023-01-01"
        activity.name = "Test Activity"
        activity.average_heartrate = 150
        activity.max_heartrate = 180
        activity.total_elevation_gain = 100
        activity.weighted_average_watts = 200
        activity.moving_time = 3600
        activity.distance = 0
        activity.sport_type = MagicMock()
        activity.sport_type.root = "Run"
        activity.start_latlng = MagicMock()
        activity.start_latlng.lat = 40.0
        activity.start_latlng.lon = -70.0
        activity.end_latlng = MagicMock()
        activity.end_latlng.lat = 41.0
        activity.end_latlng.lon = -71.0
        activity.map = MagicMock()
        activity.map.summary_polyline = "encoded_polyline"

        activities = [activity]
        supported_sports = ["Run"]
        df = pre_process_data(activities, supported_sports)

        self.assertEqual(len(df), 1)
        self.assertIsNone(df["pace_min_per_km"][0])
        self.assertEqual(df["centroid_lat"][0], 5)
        self.assertEqual(df["centroid_lon"][0], 6)
        self.assertEqual(df["area"][0], 10)

    @patch("src.data.polyline.decode")
    @patch("src.data.Polygon")
    def test_activity_rename(self, mock_polygon, mock_polyline_decode):
        mock_polyline_decode.return_value = [(1, 2), (3, 4)]
        mock_poly_instance = MagicMock()
        mock_polygon.return_value = mock_poly_instance
        mock_poly_instance.centroid = MagicMock()
        mock_poly_instance.centroid.x = 5
        mock_poly_instance.centroid.y = 6
        mock_poly_instance.area = 10

        activity = MagicMock(spec=SummaryActivity)
        activity.id = 123
        activity.start_date_local = MagicMock()
        activity.start_date_local.strftime.return_value = "2023-01-01"
        activity.name = "Morning Run"
        activity.average_heartrate = 150
        activity.max_heartrate = 180
        activity.total_elevation_gain = 100
        activity.weighted_average_watts = 200
        activity.moving_time = 3600
        activity.distance = 10000
        activity.sport_type = MagicMock()
        activity.sport_type.root = "Run"
        activity.start_latlng = MagicMock()
        activity.start_latlng.lat = 40.0
        activity.start_latlng.lon = -70.0
        activity.end_latlng = MagicMock()
        activity.end_latlng.lat = 41.0
        activity.end_latlng.lon = -71.0
        activity.map = MagicMock()
        activity.map.summary_polyline = "encoded_polyline"

        activities = [activity]
        supported_sports = ["Run"]
        df = pre_process_data(activities, supported_sports)

        self.assertEqual(len(df), 1)
        self.assertTrue(df["rename"][0])
        self.assertEqual(df["centroid_lat"][0], 5)
        self.assertEqual(df["centroid_lon"][0], 6)
        self.assertEqual(df["area"][0], 10)

    @patch("src.data.polyline.decode")
    @patch("src.data.Polygon")
    def test_activity_no_rename(self, mock_polygon, mock_polyline_decode):
        mock_polyline_decode.return_value = [(1, 2), (3, 4)]
        mock_poly_instance = MagicMock()
        mock_polygon.return_value = mock_poly_instance
        mock_poly_instance.centroid = MagicMock()
        mock_poly_instance.centroid.x = 5
        mock_poly_instance.centroid.y = 6
        mock_poly_instance.area = 10

        activity = MagicMock(spec=SummaryActivity)
        activity.id = 123
        activity.start_date_local = MagicMock()
        activity.start_date_local.strftime.return_value = "2023-01-01"
        activity.name = "Test Activity"
        activity.average_heartrate = 150
        activity.max_heartrate = 180
        activity.total_elevation_gain = 100
        activity.weighted_average_watts = 200
        activity.moving_time = 3600
        activity.distance = 10000
        activity.sport_type = MagicMock()
        activity.sport_type.root = "Run"
        activity.start_latlng = MagicMock()
        activity.start_latlng.lat = 40.0
        activity.start_latlng.lon = -70.0
        activity.end_latlng = MagicMock()
        activity.end_latlng.lat = 41.0
        activity.end_latlng.lon = -71.0
        activity.map = MagicMock()
        activity.map.summary_polyline = "encoded_polyline"

        activities = [activity]
        supported_sports = ["Run"]
        df = pre_process_data(activities, supported_sports)

        self.assertEqual(len(df), 1)
        self.assertFalse(df["rename"][0])
        self.assertEqual(df["centroid_lat"][0], 5)
        self.assertEqual(df["centroid_lon"][0], 6)
        self.assertEqual(df["area"][0], 10)


if __name__ == "__main__":
    unittest.main()
