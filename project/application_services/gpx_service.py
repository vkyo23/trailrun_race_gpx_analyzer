"""
GPX service module that provides high-level operations for GPX analysis.

This module serves as the main interface for GPX-related operations in the application.
"""

from typing import TYPE_CHECKING, BinaryIO

import polars as pl

from project.application_services.marker_manager import MarkerManager, Segment
from project.data_accessors.gpx_analyzer import GPXAnalyzer, GPXStats
from project.data_accessors.gpx_loader import GPXLoader

if TYPE_CHECKING:
    from gpxpy.gpx import GPX


class GPXService:
    """Service class for GPX analysis operations."""

    def __init__(self) -> None:
        """Initialize the GPX service."""
        self._gpx: GPX | None = None
        self._analyzer: GPXAnalyzer | None = None
        self._marker_manager: MarkerManager | None = None

    def load_from_file(self, file: BinaryIO) -> None:
        """
        Load GPX data from an uploaded file.

        Args:
            file: Binary file object containing GPX data

        Raises:
            GPXLoadError: If the file cannot be loaded or parsed
        """
        self._gpx = GPXLoader.load_from_file(file)
        self._analyzer = GPXAnalyzer(self._gpx)
        self._marker_manager = MarkerManager(self._analyzer)
        self._load_waypoints_as_markers()

    def load_from_url(self, url: str) -> None:
        """
        Load GPX data from a URL.

        Args:
            url: URL pointing to a GPX file

        Raises:
            GPXLoadError: If the URL cannot be accessed or parsed
        """
        self._gpx = GPXLoader.load_from_url(url)
        self._analyzer = GPXAnalyzer(self._gpx)
        self._marker_manager = MarkerManager(self._analyzer)
        self._load_waypoints_as_markers()

    def is_loaded(self) -> bool:
        """
        Check if GPX data is loaded.

        Returns:
            True if GPX data is loaded, False otherwise
        """
        return self._gpx is not None

    def get_stats(self) -> GPXStats:
        """
        Get overall statistics for the loaded GPX track.

        Returns:
            GPXStats object containing track statistics

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._analyzer is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._analyzer.calculate_stats()

    def get_track_dataframe(self) -> pl.DataFrame:
        """
        Get track data as a Polars DataFrame.

        Returns:
            DataFrame with track points

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._analyzer is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._analyzer.get_dataframe()

    def add_marker(self, name: str, latitude: float, longitude: float, insert_before_last: bool = False) -> None:
        """
        Add a marker to the track.

        Args:
            name: Name/label for the marker
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            insert_before_last: If True, insert before the last marker (useful for inserting before goal)

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        self._marker_manager.add_marker(name, latitude, longitude, insert_before_last)

    def remove_marker(self, index: int) -> None:
        """
        Remove a marker by its index.

        Args:
            index: Index of the marker to remove

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        self._marker_manager.remove_marker(index)

    def clear_markers(self) -> None:
        """
        Remove all markers.

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        self._marker_manager.clear_markers()

    def get_markers(self) -> list:
        """
        Get all markers.

        Returns:
            List of Marker objects

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._marker_manager.get_all_markers()

    def get_segments(self) -> list[Segment]:
        """
        Get all segments between consecutive markers.

        Returns:
            List of Segment objects

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._marker_manager.get_all_segments()

    def get_segment(self, start_index: int, end_index: int) -> Segment | None:
        """
        Get a segment between two specific markers.

        Args:
            start_index: Index of the starting marker
            end_index: Index of the ending marker

        Returns:
            Segment object or None if indices are invalid

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._marker_manager.get_segment(start_index, end_index)

    def get_segments_dataframe(self) -> pl.DataFrame:
        """
        Get segment summary as a Polars DataFrame.

        Returns:
            DataFrame with columns: segment, start, end, distance_km, ascent_m, descent_m, gradient_pct

        Raises:
            ValueError: If no GPX data is loaded
        """
        segments = self.get_segments()

        if not segments:
            return pl.DataFrame(
                {
                    "segment": [],
                    "start": [],
                    "end": [],
                    "distance_km": [],
                    "ascent_m": [],
                    "descent_m": [],
                    "gradient_pct": [],
                }
            )

        data = {
            "segment": [f"{i + 1}" for i in range(len(segments))],
            "start": [seg.start_marker.name for seg in segments],
            "end": [seg.end_marker.name for seg in segments],
            "distance_km": [seg.distance / 1000.0 for seg in segments],
            "ascent_m": [seg.ascent for seg in segments],
            "descent_m": [seg.descent for seg in segments],
            "gradient_pct": [seg.avg_gradient for seg in segments],
        }

        return pl.DataFrame(data)

    def move_marker_up(self, index: int) -> bool:
        """
        Move a marker up in the list.

        Args:
            index: Index of the marker to move

        Returns:
            True if the marker was moved, False otherwise

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._marker_manager.move_marker_up(index)

    def move_marker_down(self, index: int) -> bool:
        """
        Move a marker down in the list.

        Args:
            index: Index of the marker to move

        Returns:
            True if the marker was moved, False otherwise

        Raises:
            ValueError: If no GPX data is loaded
        """
        if self._marker_manager is None:
            msg = "No GPX data loaded"
            raise ValueError(msg)
        return self._marker_manager.move_marker_down(index)

    def _load_waypoints_as_markers(self) -> None:
        """
        Load waypoints from GPX file as markers.

        This method automatically adds all waypoints from the GPX file as markers,
        including start and end points.
        """
        if self._analyzer is None or self._marker_manager is None:
            return

        # Get track points to add start and end as markers
        track_points = self._analyzer.extract_track_points()

        if track_points:
            # Add start point as first marker
            start_point = track_points[0]
            self._marker_manager.add_marker(
                name="スタート",
                latitude=start_point.latitude,
                longitude=start_point.longitude,
            )

            # Add waypoints from GPX
            waypoints = self._analyzer.extract_waypoints()
            for waypoint in waypoints:
                self._marker_manager.add_marker(
                    name=waypoint.name,
                    latitude=waypoint.latitude,
                    longitude=waypoint.longitude,
                )

            # Add end point as last marker
            if len(track_points) > 1:
                end_point = track_points[-1]
                self._marker_manager.add_marker(
                    name="ゴール",
                    latitude=end_point.latitude,
                    longitude=end_point.longitude,
                )

    def get_waypoint_count(self) -> int:
        """
        Get the number of waypoints loaded from the GPX file.

        Returns:
            Number of waypoints
        """
        if self._analyzer is None:
            return 0
        return len(self._analyzer.extract_waypoints())

    def reset(self) -> None:
        """Reset the service, clearing all loaded data and markers."""
        self._gpx = None
        self._analyzer = None
        self._marker_manager = None
