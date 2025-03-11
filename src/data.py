import polyline
from stravalib.model import SummaryActivity
from typing import Any
from shapely.geometry import Polygon


def process_activity(activity: SummaryActivity) -> dict[str, Any]:
    activity_dict = activity.model_dump()

    # process columns
    if activity_dict["start_latlng"]:
        activity_dict["start_lat"] = activity_dict["start_latlng"][0]
        activity_dict["start_lng"] = activity_dict["start_latlng"][1]
    del activity_dict["start_latlng"]

    if activity_dict["end_latlng"]:
        activity_dict["end_lat"] = activity_dict["end_latlng"][0]
        activity_dict["end_lng"] = activity_dict["end_latlng"][1]
    del activity_dict["end_latlng"]

    activity_dict["date"] = activity_dict["start_date_local"].date()
    activity_dict["time"] = activity_dict["start_date_local"].time()
    activity_dict["day_of_week"] = activity_dict["start_date_local"].strftime("%A")
    activity_dict["moving_time_minutes"] = activity_dict["moving_time"] / 60
    activity_dict["distance_km"] = activity_dict["distance"] / 1000

    try:
        activity_dict["pace_min_per_km"] = (
            1.0 * activity_dict["moving_time_minutes"] / activity_dict["distance_km"]
        )
    except ZeroDivisionError:
        activity_dict["pace_min_per_km"] = None

    decoded = polyline.decode(activity_dict["map"]["summary_polyline"])
    if len(decoded) > 0:
        poly = Polygon(decoded)
        centroid = poly.centroid
        centroid_lat = centroid.x
        centroid_lon = centroid.y
        area = poly.area

        activity_dict["map_centroid_lat"] = centroid_lat
        activity_dict["map_centroid_lon"] = centroid_lon
        activity_dict["map_area"] = area
    return activity_dict
