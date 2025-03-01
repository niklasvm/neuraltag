import re
import pandas as pd
import polyline
from shapely.geometry import Polygon
from stravalib.model import SummaryActivity


def pre_process_data(activities: list[SummaryActivity], supported_sports: list[str]):
    dd = []
    sport_regex = "|".join(supported_sports)
    rename_regex = rf"(Morning|Afternoon|Evening|Night)\s({sport_regex})"
    for activity in activities:
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
            sport_type=activity.sport_type.root,
            # location_country=activity.location_country,
        )

        # pace features
        try:
            d["pace_min_per_km"] = d["moving_time_minutes"] / d["distance_km"]
        except ZeroDivisionError:
            d["pace_min_per_km"] = None

        # location features
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

        d["rename"] = False
        if re.search(rename_regex, d["name"]):
            d["rename"] = True

        dd.append(d)

    df = pd.DataFrame(dd)
    return df
