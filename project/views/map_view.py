"""
Map visualization module for displaying GPX tracks and markers.

This module provides functionality to render interactive maps with track data and markers.
"""

import math
from typing import cast

import folium
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from project.application_services.marker_manager import Marker
from project.settings import settings


class MapView:
    """Class for rendering interactive maps with GPX tracks and markers."""

    @staticmethod
    def render_map(
        track_df: pl.DataFrame,
        markers: list[Marker] | None = None,
        highlight_segment: tuple[int, int] | None = None,
        pending_coordinates: tuple[float, float] | None = None,
    ) -> dict | None:
        """
        Render an interactive map with the GPX track and markers.

        Args:
            track_df: DataFrame containing track points (latitude, longitude, elevation, distance)
            markers: List of Marker objects to display on the map
            highlight_segment: Optional tuple of (start_index, end_index) to highlight a segment
            pending_coordinates: Optional tuple of (latitude, longitude) for showing a temporary marker

        Returns:
            Dictionary containing map interaction data (clicked coordinates, etc.)
        """
        if track_df.is_empty():
            st.warning("トラックデータがありません")
            return None

        # Calculate center of the track
        lat_mean = track_df["latitude"].mean()
        lon_mean = track_df["longitude"].mean()
        # Polars mean() returns a complex union type but at runtime it's always a numeric value
        center_lat = float(cast("float", lat_mean)) if lat_mean is not None else 0.0
        center_lon = float(cast("float", lon_mean)) if lon_mean is not None else 0.0

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=settings.default_map_zoom,
            tiles="OpenStreetMap",
        )

        # Convert track data to list of coordinates
        track_coords = [
            [float(row[0]), float(row[1])] for row in track_df.select(["latitude", "longitude"]).iter_rows()
        ]

        # Add the main track line with enhanced visibility (YAMAP-style)
        # Make the track thick and prominent for better clickability
        folium.PolyLine(
            track_coords,
            color="#FF6B35",  # Vibrant orange color for better visibility
            weight=5,
            opacity=0.85,
            tooltip="トラックをクリックしてマーカーを配置",
        ).add_to(m)

        # Add direction arrows along the track if course data is available
        MapView._add_direction_arrows(m, track_df)

        # Highlight segment if specified
        if highlight_segment is not None and markers is not None:
            start_idx, end_idx = highlight_segment
            if 0 <= start_idx < len(markers) and 0 <= end_idx < len(markers):
                start_marker = markers[start_idx]
                end_marker = markers[end_idx]

                # Find track points between markers
                start_dist = start_marker.track_point.distance_from_start
                end_dist = end_marker.track_point.distance_from_start

                segment_df = track_df.filter(
                    (pl.col("distance") >= min(start_dist, end_dist))
                    & (pl.col("distance") <= max(start_dist, end_dist))
                )

                segment_coords = [
                    [float(row[0]), float(row[1])] for row in segment_df.select(["latitude", "longitude"]).iter_rows()
                ]

                folium.PolyLine(
                    segment_coords,
                    color="#FF0000",  # Bright red for highlighted segments
                    weight=7,
                    opacity=0.95,
                    popup=f"{start_marker.name} → {end_marker.name}",
                ).add_to(m)

        # Add markers
        if markers:
            for i, marker in enumerate(markers):
                distance_km = marker.track_point.distance_from_start / 1000
                elevation = marker.track_point.elevation
                course = marker.track_point.course

                # Build popup text with course information if available
                popup_text = f"<b>{marker.name}</b><br>距離: {distance_km:.2f}km<br>標高: {elevation:.0f}m"
                if course is not None:
                    # Convert course to cardinal direction
                    directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
                    direction_index = int((course + 22.5) / 45) % 8
                    direction = directions[direction_index]
                    popup_text += f"<br>方角: {course:.1f}° ({direction})"

                folium.Marker(
                    location=[marker.latitude, marker.longitude],
                    popup=popup_text,
                    tooltip=marker.name,
                    icon=folium.Icon(
                        color="red" if i == 0 else "green" if i == len(markers) - 1 else "blue",
                        icon="info-sign",
                    ),
                ).add_to(m)

        # Add pending/temporary marker for selected coordinates
        if pending_coordinates is not None:
            lat, lon = pending_coordinates
            folium.Marker(
                location=[lat, lon],
                popup="選択中の位置<br>マーカーを追加してください",
                tooltip="選択中",
                icon=folium.Icon(color="orange", icon="star", prefix="fa"),
            ).add_to(m)

        # Render map with streamlit-folium
        map_data = st_folium(
            m,
            width=None,
            height=settings.map_height,
            returned_objects=["last_clicked"],
        )

        return map_data

    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the bearing (direction) between two points.

        Args:
            lat1: Latitude of first point in degrees
            lon1: Longitude of first point in degrees
            lat2: Latitude of second point in degrees
            lon2: Longitude of second point in degrees

        Returns:
            Bearing in degrees (0-360)
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lon_diff = math.radians(lon2 - lon1)

        # Calculate bearing
        x = math.sin(lon_diff) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon_diff)

        bearing_rad = math.atan2(x, y)
        bearing_deg = math.degrees(bearing_rad)

        # Normalize to 0-360
        return (bearing_deg + 360) % 360

    @staticmethod
    def _add_direction_arrows(m: folium.Map, track_df: pl.DataFrame) -> None:
        """
        Add direction arrows along the track to show the direction of travel.

        Args:
            m: Folium map object
            track_df: DataFrame containing track points with course information
        """
        if track_df.is_empty() or len(track_df) < 2:
            return

        # Add arrows at regular intervals (every 2km)
        arrow_interval_meters = 2000
        total_distance_val = track_df["distance"].max()

        if total_distance_val is None:
            return

        total_distance = float(cast("float", total_distance_val))
        current_dist = arrow_interval_meters  # Start from first interval, not at start

        while current_dist <= total_distance:
            # Find the point closest to this distance
            point_row = track_df.filter(pl.col("distance") >= current_dist).head(1)

            if not point_row.is_empty():
                current_index = int(point_row["index"][0])
                lat = float(point_row["latitude"][0])
                lon = float(point_row["longitude"][0])

                # Try to get course from GPX data first
                course = None
                if "course" in track_df.columns:
                    course_val = point_row["course"][0]
                    if course_val is not None:
                        course = float(course_val)

                # If no course data, calculate from adjacent points
                if course is None and current_index > 0 and current_index < len(track_df) - 1:
                    # Get previous and next points for better accuracy
                    prev_row = track_df.filter(pl.col("index") == current_index - 1).head(1)
                    next_row = track_df.filter(pl.col("index") == current_index + 1).head(1)

                    if not prev_row.is_empty() and not next_row.is_empty():
                        prev_lat = float(prev_row["latitude"][0])
                        prev_lon = float(prev_row["longitude"][0])
                        next_lat = float(next_row["latitude"][0])
                        next_lon = float(next_row["longitude"][0])

                        # Calculate bearing from previous to next point
                        course = MapView._calculate_bearing(prev_lat, prev_lon, next_lat, next_lon)

                # Add arrow if we have a course (from data or calculated)
                if course is not None:
                    # Convert course to cardinal direction for tooltip
                    directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
                    direction_index = int((course + 22.5) / 45) % 8
                    direction = directions[direction_index]

                    # Create a custom arrow icon using DivIcon with CSS
                    arrow_html = f"""
                    <div style="
                        width: 0;
                        height: 0;
                        border-left: 8px solid transparent;
                        border-right: 8px solid transparent;
                        border-bottom: 24px solid #4169E1;
                        transform: rotate({course}deg);
                        transform-origin: center 16px;
                        filter: drop-shadow(0 0 2px white);
                    "></div>
                    """

                    folium.Marker(
                        location=[lat, lon],
                        icon=folium.DivIcon(html=arrow_html, icon_size=(16, 24), icon_anchor=(8, 16)),
                        tooltip=f"方角: {direction} ({course:.0f}°)",
                    ).add_to(m)

            current_dist += arrow_interval_meters

    @staticmethod
    def get_clicked_coordinates(map_data: dict | None) -> tuple[float, float] | None:
        """
        Extract clicked coordinates from map interaction data.

        Args:
            map_data: Dictionary returned from st_folium

        Returns:
            Tuple of (latitude, longitude) or None if no click detected
        """
        if map_data is None:
            return None

        last_clicked = map_data.get("last_clicked")
        if last_clicked is None:
            return None

        lat = last_clicked.get("lat")
        lng = last_clicked.get("lng")

        if lat is not None and lng is not None:
            return (float(lat), float(lng))

        return None
