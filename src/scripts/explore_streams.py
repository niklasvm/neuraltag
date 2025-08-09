
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from src.tasks.etl.single_activity_etl import SingleActivityETL
from src.app.config import settings
from src.tasks.strava import get_strava_client
from io import BytesIO

import logging

logger = logging.getLogger(__name__)

def make_plot(df: pd.DataFrame, filename="activity_plot.png", return_binary=False) -> bytes | None:
    x_axis = "distance"

    # validate x_axis present
    if x_axis not in df.columns:
        logger.warning(f"Column '{x_axis}' not found in DataFrame. Available columns: {df.columns.tolist()}. Returning None")
        return None

    # Define plot configuration in a dict
    plot_config = {
        "speed": {
            "chart_title": "Speed",
            "fillcolor": 'rgba(0, 0, 255, 0.4)',
            "line_color": 'blue',
            "y_label": "Speed (km/h)"
        },
        "heartrate": {
            "chart_title": "Heart Rate",
            "fillcolor": 'rgba(255, 0, 0, 0.4)',
            "line_color": 'red',
            "y_label": "Heart Rate (bpm)"
        },
        "altitude": {
            "chart_title": "Altitude",
            "fillcolor": 'rgba(0, 255, 0, 0.4)',
            "line_color": 'green',
            "y_label": "Altitude (m)"
        },
        "cadence": {
            "chart_title": "Cadence",
            "fillcolor": 'rgba(255, 255, 0, 0.4)',
            "line_color": 'yellow',
            "y_label": "Cadence (rpm)"
        }
    }

    columns_found = [col for col in plot_config if col in df.columns]
    if not columns_found:
        logger.warning(f"None of the columns {list(plot_config.keys())} found in DataFrame. Available columns: {df.columns.tolist()}. Returning None")
        return None

    number_of_plots = len(columns_found)
    fig = make_subplots(
        rows=number_of_plots, cols=1,
        subplot_titles=[plot_config[col]["chart_title"] for col in columns_found],
        vertical_spacing=0.08
    )

    for i, col in enumerate(columns_found, start=1):
        params = plot_config[col]
        fig.add_trace(
            go.Scatter(
                x=df[x_axis], y=df[col],
                fill='tonexty',
                fillcolor=params["fillcolor"],
                line_color=params["line_color"],
                name=params["chart_title"]
            ),
            row=i, col=1
        )
        fig.update_yaxes(title_text=params["y_label"], row=i, col=1)

        # Add min, max, median lines and labels
        min_val = df[col].min()
        max_val = df[col].max()
        median_val = df[col].median()

        fig.add_hline(
            y=min_val,
            line_dash="dot",
            line_color="gray",
            row=i, col=1,
            annotation_text=f"Min: {min_val:.2f}",
            annotation_position="bottom left",
            annotation_font_color="gray"
        )
        fig.add_hline(
            y=max_val,
            line_dash="dot",
            line_color="gray",
            row=i, col=1,
            annotation_text=f"Max: {max_val:.2f}",
            annotation_position="top left",
            annotation_font_color="gray"
        )
        fig.add_hline(
            y=median_val,
            line_dash="dash",
            line_color="white",
            row=i, col=1,
            annotation_text=f"Median: {median_val:.2f}",
            annotation_position="top right",
            annotation_font_color="white"
        )

    fig.update_layout(
        height=800,
        plot_bgcolor="black", 
        paper_bgcolor="black", 
        font_color="white",
        showlegend=False
    )

    fig.update_xaxes(title_text="Distance (km)", row=number_of_plots, col=1)

    width = 1200
    height = number_of_plots * 400

    fig.write_image(filename,scale=2,width=width,height=height)

etl = SingleActivityETL(activity_id=15395278540, athlete_id=1411289,settings=settings)

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

df = pd.DataFrame.from_records({k: v.data for k, v in activity_streams.items()})

df["distance"] = df["distance"]/1000

# convert m/s to min/km
df["pace"] = 1000 / (60*df["velocity_smooth"])
df["speed"] = df["velocity_smooth"] * 3.6  # convert m/s to km/h



make_plot(df,filename="activity_plot.png")

    

df