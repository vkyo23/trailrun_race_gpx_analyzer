"""
Chart visualization module for displaying elevation profiles.

This module provides functionality to render elevation profile charts with interactive features.
"""

import plotly.graph_objects as go
import polars as pl
import streamlit as st

from project.application_services.marker_manager import Marker, Segment
from project.settings import settings


class ChartView:
    """Class for rendering elevation profile charts."""

    @staticmethod
    def render_elevation_profile(
        track_df: pl.DataFrame,
        markers: list[Marker] | None = None,
        highlight_segment: Segment | None = None,
    ) -> None:
        """
        Render an interactive elevation profile chart.

        Args:
            track_df: DataFrame containing track points (distance, elevation)
            markers: Optional list of Marker objects to display on the chart
            highlight_segment: Optional segment to highlight on the chart
        """
        if track_df.is_empty():
            st.warning("トラックデータがありません")
            return

        # Convert distance to kilometers
        distances_km = (track_df["distance"] / 1000.0).to_numpy()
        elevations = track_df["elevation"].to_numpy()

        # Create figure
        fig = go.Figure()

        # Add main elevation profile
        fig.add_trace(
            go.Scatter(
                x=distances_km,
                y=elevations,
                mode="lines",
                name="標高プロファイル",
                line={"color": "blue", "width": 2},
                fill="tozeroy",
                fillcolor="rgba(0, 100, 255, 0.2)",
                hovertemplate="<b>距離:</b> %{x:.2f}km<br><b>標高:</b> %{y:.0f}m<extra></extra>",
            )
        )

        # Highlight segment if specified
        if highlight_segment is not None:
            segment_distances = [p.distance_from_start / 1000.0 for p in highlight_segment.track_points]
            segment_elevations = [p.elevation for p in highlight_segment.track_points]

            fig.add_trace(
                go.Scatter(
                    x=segment_distances,
                    y=segment_elevations,
                    mode="lines",
                    name=f"{highlight_segment.start_marker.name} → {highlight_segment.end_marker.name}",
                    line={"color": "red", "width": 4},
                    hovertemplate="<b>距離:</b> %{x:.2f}km<br><b>標高:</b> %{y:.0f}m<extra></extra>",
                )
            )

        # Add marker annotations
        if markers:
            for marker in markers:
                distance_km = marker.track_point.distance_from_start / 1000.0
                elevation = marker.track_point.elevation

                fig.add_trace(
                    go.Scatter(
                        x=[distance_km],
                        y=[elevation],
                        mode="markers+text",
                        name=marker.name,
                        marker={"size": 10, "color": "red"},
                        text=[marker.name],
                        textposition="top center",
                        hovertemplate=(
                            f"<b>{marker.name}</b><br>"
                            f"距離: {distance_km:.2f}km<br>"
                            f"標高: {elevation:.0f}m<extra></extra>"
                        ),
                    )
                )

        # Update layout
        fig.update_layout(
            title="標高プロファイル",
            xaxis_title="距離 (km)",
            yaxis_title="標高 (m)",
            height=settings.elevation_chart_height,
            hovermode="x unified",
            showlegend=True,
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        )

        # Display chart
        st.plotly_chart(fig, width="stretch")
