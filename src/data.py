import pandas as pd
import polyline
from shapely.geometry import Polygon
from stravalib.model import RelaxedSportType, SummaryActivity


def extract_data_from_weight_training_activities(activities: list[SummaryActivity]):
    dd = []
    for activity in activities:
        if activity.sport_type != RelaxedSportType("WeightTraining"):
            continue

        d = dict(
            id=activity.id,
            date=activity.start_date_local.strftime("%Y-%m-%d"),
            time=activity.start_date_local.strftime("%H:%M:%S"),
            day_of_week=activity.start_date_local.strftime("%A"),
            name=activity.name,
            average_heartrate=activity.average_heartrate,
            max_heartrate=activity.max_heartrate,
            moving_time_minutes=activity.moving_time / 60,
            location_country=activity.location_country,
        )

        dd.append(d)

    df = pd.DataFrame(dd)
    return df


def extract_data_from_run_activities(activities: list[SummaryActivity]):
    dd = []
    for activity in activities:
        if activity.sport_type != RelaxedSportType("Run"):
            continue

        d = dict(
            id=activity.id,
            date=activity.start_date_local.strftime("%Y-%m-%d"),
            time=activity.start_date_local.strftime("%H:%M:%S"),
            day_of_week=activity.start_date_local.strftime("%A"),
            name=activity.name,
            average_heartrate=activity.average_heartrate,
            max_heartrate=activity.max_heartrate,
            total_elevation_gain=activity.total_elevation_gain,
            weighted_average_watts=activity.weighted_average_watts,
            moving_time_minutes=activity.moving_time / 60,
            distance_km=activity.distance / 1000,
            # location_country=activity.location_country,
            pace_min_per_km=(activity.moving_time / 60) / (activity.distance / 1000),
        )
        if activity.start_latlng:
            d["lat"] = activity.start_latlng.lat
            d["lng"] = activity.start_latlng.lon
        if activity.end_latlng:
            d["end_lat"] = activity.end_latlng.lat
            d["end_lng"] = activity.end_latlng.lon

        decoded = polyline.decode(activity.map.summary_polyline)
        if len(decoded) > 0:
            poly = Polygon(decoded)
            centroid = poly.centroid
            centroid_lat = centroid.x
            centroid_lon = centroid.y
            area = poly.area

            d["centroid_lat"] = centroid_lat
            d["centroid_lon"] = centroid_lon
            d["area"] = area

        dd.append(d)

    df = pd.DataFrame(dd)
    return df
