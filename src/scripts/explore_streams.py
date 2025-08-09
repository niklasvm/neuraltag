

import os
import pandas as pd

import plotly.graph_objects as go
from src.tasks.etl.single_activity_etl import SingleActivityETL, _make_streams_png_plot
from src.app.config import settings
from src.tasks.strava import get_strava_client


import logging

logger = logging.getLogger(__name__)



etl = SingleActivityETL(activity_id=15395278540, athlete_id=1411289,settings=settings)

etl.extract()

etl.transform()

etl.load()

auth = etl.db.get_auth_by_athlete_id(etl.athlete_id)

client = get_strava_client(
    access_token=auth.access_token,
    refresh_token=auth.refresh_token,
    expires_at=auth.expires_at,
    strava_client_id=etl.settings.strava_client_id,
    strava_client_secret=etl.settings.strava_client_secret,
)

# get activity streams
activity_streams = client.get_activity_streams(
    activity_id=etl.activity_id,
    resolution="high",
)
activity_streams_df = pd.DataFrame.from_records({k: v.data for k, v in activity_streams.items()})

binary_png_data = _make_streams_png_plot(activity_streams_df)

with open("png.png","wb") as f:
    f.write(binary_png_data)


activity_laps = client.get_activity_laps(activity_id=etl.activity_id)
activity_laps = [x for x in activity_laps]

for lap in activity_laps:
    print(f"{lap.name} {lap.average_heartrate}")

pd.DataFrame([x.__dict__ for x in activity_laps])

len(activity_laps)
activity_laps[0]

# convert dict to df

for k, v in activity_streams.items():
    print(k)
    print(f"Type: {v.series_type}")
    print(f"Original size: {v.original_size}")
    print(f"Data: {v.data[:10]}")
    print()



activity_streams_df["distance"] = activity_streams_df["distance"]/1000

# convert m/s to min/km
activity_streams_df["pace"] = 1000 / (60*activity_streams_df["velocity_smooth"])
activity_streams_df["speed"] = activity_streams_df["velocity_smooth"] * 3.6  # convert m/s to km/h



make_streams_png_plot(activity_streams_df,filename="activity_plot.png")

    

activity_streams_df