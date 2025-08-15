import io
import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.app.config import Settings
from src.tasks.data import summary_activity_to_activity_model
from src.tasks.etl.base import ETL
from src.tasks.strava import get_strava_client

logger = logging.getLogger(__name__)


class SingleActivityETL(ETL):
    def __init__(self, settings: Settings, activity_id: int, athlete_id: int):
        super().__init__(settings=settings)
        self.activity_id = activity_id
        self.athlete_id = athlete_id

    def extract(self):
        auth = self.db.get_auth_by_athlete_id(self.athlete_id)

        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )

        # get activity
        self._activity = client.get_activity(self.activity_id)

        # get activity streams data
        activity_streams = client.get_activity_streams(
            activity_id=self.activity_id,
            resolution="high",
        )
        self._activity_streams_df = pd.DataFrame.from_records(
            {k: v.data for k, v in activity_streams.items()}
        )

    def transform(self):
        self._activity_model = summary_activity_to_activity_model(self._activity)

        self._activity_model.stream_data = _make_streams_png_plot_with_matplotlib(
            self._activity_streams_df
        )

    def load(self):
        self.db.add_activity(self._activity_model)
        return self._activity_model


def _make_streams_png_plot_with_plotly(
    streams_df: pd.DataFrame, filename="activity_plot.png"
) -> bytes | None:
    """
    Generates a PNG plot visualizing activity stream data (such as speed, heartrate, altitude, and cadence)
    against distance, using Plotly. The plot is returned as PNG image bytes.

    Parameters:
        streams_df (pd.DataFrame): DataFrame containing activity stream data. Must include a 'distance' column
            and may include columns such as 'speed', 'heartrate', 'altitude', and 'cadence'.
        filename (str, optional): Filename for the plot (not used for saving, only for Plotly metadata).

    Returns:
        bytes: PNG image bytes of the generated plot if required columns are present.
        None: If the 'distance' column is missing or none of the expected data columns are found.
    """
    x_axis = "distance"

    # validate x_axis present
    if x_axis not in streams_df.columns:
        logger.warning(
            f"Column '{x_axis}' not found in DataFrame. Available columns: {streams_df.columns.tolist()}. Returning None"
        )
        return None

    # Define plot configuration in a dict
    plot_config = {
        "speed": {
            "chart_title": "Speed",
            "fillcolor": "rgba(0, 0, 255, 0.4)",
            "line_color": "blue",
            "y_label": "Speed (km/h)",
        },
        "heartrate": {
            "chart_title": "Heart Rate",
            "fillcolor": "rgba(255, 0, 0, 0.4)",
            "line_color": "red",
            "y_label": "Heart Rate (bpm)",
        },
        "altitude": {
            "chart_title": "Altitude",
            "fillcolor": "rgba(0, 255, 0, 0.4)",
            "line_color": "green",
            "y_label": "Altitude (m)",
        },
        "cadence": {
            "chart_title": "Cadence",
            "fillcolor": "rgba(255, 255, 0, 0.4)",
            "line_color": "yellow",
            "y_label": "Cadence (rpm)",
        },
    }

    columns_found = [col for col in plot_config if col in streams_df.columns]
    if not columns_found:
        logger.warning(
            f"None of the columns {list(plot_config.keys())} found in DataFrame. Available columns: {streams_df.columns.tolist()}. Returning None"
        )
        return None

    number_of_plots = len(columns_found)
    fig = make_subplots(
        rows=number_of_plots,
        cols=1,
        subplot_titles=[plot_config[col]["chart_title"] for col in columns_found],
        vertical_spacing=0.08,
    )

    for i, col in enumerate(columns_found, start=1):
        params = plot_config[col]
        fig.add_trace(
            go.Scatter(
                x=streams_df[x_axis],
                y=streams_df[col],
                fill="tonexty",
                fillcolor=params["fillcolor"],
                line_color=params["line_color"],
                name=params["chart_title"],
            ),
            row=i,
            col=1,
        )
        fig.update_yaxes(title_text=params["y_label"], row=i, col=1)

        # Add min, max, median lines and labels
        min_val = streams_df[col].min()
        max_val = streams_df[col].max()
        median_val = streams_df[col].median()

        fig.add_hline(
            y=min_val,
            line_dash="dot",
            line_color="gray",
            row=i,
            col=1,
            annotation_text=f"Min: {min_val:.2f}",
            annotation_position="bottom left",
            annotation_font_color="gray",
        )
        fig.add_hline(
            y=max_val,
            line_dash="dot",
            line_color="gray",
            row=i,
            col=1,
            annotation_text=f"Max: {max_val:.2f}",
            annotation_position="top left",
            annotation_font_color="gray",
        )
        fig.add_hline(
            y=median_val,
            line_dash="dash",
            line_color="white",
            row=i,
            col=1,
            annotation_text=f"Median: {median_val:.2f}",
            annotation_position="top right",
            annotation_font_color="white",
        )

    fig.update_layout(
        height=800,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font_color="white",
        showlegend=False,
    )

    fig.update_xaxes(title_text="Distance (km)", row=number_of_plots, col=1)

    width = 1200
    height = number_of_plots * 400

    fig.write_image(filename, scale=2, width=width, height=height)

    with open(filename, "rb") as f:
        binary_data = f.read()

    os.remove(filename)

    return binary_data


def _make_streams_png_plot_with_matplotlib(
    streams_df: pd.DataFrame, filename="activity_plot.png"
) -> bytes | None:
    """
    Generates a PNG plot visualizing activity stream data (such as speed, heartrate, altitude, and cadence)
    against distance, using matplotlib. The plot is returned as PNG image bytes.

    Parameters:
        streams_df (pd.DataFrame): DataFrame containing activity stream data. Must include a 'distance' column
            and may include columns such as 'speed', 'heartrate', 'altitude', and 'cadence'.
        filename (str, optional): Filename for the plot (not used for saving, only for metadata).

    Returns:
        bytes: PNG image bytes of the generated plot if required columns are present.
        None: If the 'distance' column is missing or none of the expected data columns are found.
    """

    x_axis = "distance"

    # validate x_axis present
    if x_axis not in streams_df.columns:
        logger.warning(
            f"Column '{x_axis}' not found in DataFrame. Available columns: {streams_df.columns.tolist()}. Returning None"
        )
        return None

    # Define plot configuration in a dict
    plot_config = {
        "speed": {
            "chart_title": "Speed",
            "fillcolor": (0, 0, 1, 0.4),  # RGBA
            "line_color": "blue",
            "y_label": "Speed (km/h)",
        },
        "heartrate": {
            "chart_title": "Heart Rate",
            "fillcolor": (1, 0, 0, 0.4),  # RGBA
            "line_color": "red",
            "y_label": "Heart Rate (bpm)",
        },
        "altitude": {
            "chart_title": "Altitude",
            "fillcolor": (0, 1, 0, 0.4),  # RGBA
            "line_color": "green",
            "y_label": "Altitude (m)",
        },
        "cadence": {
            "chart_title": "Cadence",
            "fillcolor": (1, 1, 0, 0.4),  # RGBA
            "line_color": "yellow",
            "y_label": "Cadence (rpm)",
        },
    }

    columns_found = [col for col in plot_config if col in streams_df.columns]
    if not columns_found:
        logger.warning(
            f"None of the columns {list(plot_config.keys())} found in DataFrame. Available columns: {streams_df.columns.tolist()}. Returning None"
        )
        return None

    number_of_plots = len(columns_found)

    # Set up the figure with dark background similar to Plotly
    plt.style.use("dark_background")
    fig, axes = plt.subplots(
        nrows=number_of_plots,
        ncols=1,
        figsize=(12, number_of_plots * 4),
        facecolor="black",
    )

    # Ensure axes is always indexable for consistent access
    if number_of_plots == 1:
        # For single subplot, make it a list
        axes_list = [axes]
    else:
        # For multiple subplots, axes is already an array
        axes_list = list(axes)

    for i, col in enumerate(columns_found):
        ax = axes_list[i]
        params = plot_config[col]

        # Plot the main line and fill
        ax.plot(
            streams_df[x_axis],
            streams_df[col],
            color=params["line_color"],
            linewidth=1.5,
        )
        ax.fill_between(
            streams_df[x_axis], streams_df[col], color=params["fillcolor"], alpha=0.4
        )

        # Calculate statistics
        min_val = streams_df[col].min()
        max_val = streams_df[col].max()
        median_val = streams_df[col].median()

        # Add horizontal lines for min, max, median
        ax.axhline(y=min_val, color="gray", linestyle=":", alpha=0.7)
        ax.axhline(y=max_val, color="gray", linestyle=":", alpha=0.7)
        ax.axhline(y=median_val, color="white", linestyle="--", alpha=0.7)

        # Add text annotations for statistics
        ax.text(
            0.02,
            0.05,
            f"Min: {min_val:.2f}",
            transform=ax.transAxes,
            color="gray",
            fontsize=10,
            verticalalignment="bottom",
        )
        ax.text(
            0.02,
            0.95,
            f"Max: {max_val:.2f}",
            transform=ax.transAxes,
            color="gray",
            fontsize=10,
            verticalalignment="top",
        )
        ax.text(
            0.98,
            0.95,
            f"Median: {median_val:.2f}",
            transform=ax.transAxes,
            color="white",
            fontsize=10,
            verticalalignment="top",
            horizontalalignment="right",
        )

        # Set labels and title
        ax.set_ylabel(params["y_label"], color="white")
        ax.set_title(params["chart_title"], color="white", pad=20)

        # Style the axes
        ax.tick_params(colors="white")
        ax.spines["bottom"].set_color("white")
        ax.spines["top"].set_color("white")
        ax.spines["right"].set_color("white")
        ax.spines["left"].set_color("white")

        # Only add x-axis label to the bottom plot
        if i == number_of_plots - 1:
            ax.set_xlabel("Distance (km)", color="white")

    # Adjust layout to prevent overlap
    plt.tight_layout()

    # Save to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(
        buffer,
        format="png",
        dpi=300,
        bbox_inches="tight",
        facecolor="black",
        edgecolor="none",
    )
    plt.close(fig)  # Close the figure to free memory

    buffer.seek(0)
    binary_data = buffer.read()
    buffer.close()

    return binary_data
