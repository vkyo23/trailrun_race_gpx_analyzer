"""
Marker manager module for managing track markers and calculating segment statistics.

This module provides functionality to manage markers on the GPX track and
calculate distances and elevation changes between them.
"""

from dataclasses import dataclass

from project.data_accessors.gpx_analyzer import GPXAnalyzer, TrackPoint


@dataclass
class Marker:
    """Represents a marker on the track."""

    name: str
    latitude: float
    longitude: float
    track_point: TrackPoint  # The actual point on the GPX track
    index: int  # Marker index in the list


@dataclass
class Segment:
    """Represents a segment between two markers."""

    start_marker: Marker
    end_marker: Marker
    distance: float  # Distance in meters
    ascent: float  # Elevation gain in meters
    descent: float  # Elevation loss in meters
    track_points: list[TrackPoint]  # Points along the segment
    avg_gradient: float  # Average gradient in percentage


class MarkerManager:
    """Class for managing markers on a GPX track."""

    def __init__(self, analyzer: GPXAnalyzer):
        """
        Initialize the marker manager.

        Args:
            analyzer: GPXAnalyzer instance for the track
        """
        self.analyzer = analyzer
        self.markers: list[Marker] = []

    def add_marker(self, name: str, latitude: float, longitude: float, insert_before_last: bool = False) -> Marker:
        """
        Add a marker to the track.

        The marker will be placed at the nearest point on the actual GPX track.

        Args:
            name: Name/label for the marker
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            insert_before_last: If True, insert before the last marker (useful for inserting before goal)

        Returns:
            The created Marker object
        """
        # Find nearest point on track
        track_point = self.analyzer.find_nearest_point(latitude, longitude)

        # Determine insertion position
        insert_position = len(self.markers) - 1 if insert_before_last and len(self.markers) >= 1 else len(self.markers)

        # Create marker
        marker = Marker(
            name=name,
            latitude=track_point.latitude,
            longitude=track_point.longitude,
            track_point=track_point,
            index=insert_position,
        )

        # Insert at the determined position
        self.markers.insert(insert_position, marker)

        # Update indices of all markers after the insertion point
        for i in range(insert_position + 1, len(self.markers)):
            self.markers[i].index = i

        return marker

    def remove_marker(self, index: int) -> None:
        """
        Remove a marker by its index.

        Args:
            index: Index of the marker to remove
        """
        if 0 <= index < len(self.markers):
            self.markers.pop(index)
            # Update indices of remaining markers
            for i, marker in enumerate(self.markers):
                marker.index = i

    def clear_markers(self) -> None:
        """Remove all markers."""
        self.markers.clear()

    def get_marker(self, index: int) -> Marker | None:
        """
        Get a marker by its index.

        Args:
            index: Index of the marker

        Returns:
            Marker object or None if index is invalid
        """
        if 0 <= index < len(self.markers):
            return self.markers[index]
        return None

    def get_all_markers(self) -> list[Marker]:
        """
        Get all markers.

        Returns:
            List of all markers
        """
        return self.markers.copy()

    def get_segment(self, start_index: int, end_index: int) -> Segment | None:
        """
        Get a segment between two markers.

        Args:
            start_index: Index of the starting marker
            end_index: Index of the ending marker

        Returns:
            Segment object or None if indices are invalid
        """
        start_marker = self.get_marker(start_index)
        end_marker = self.get_marker(end_index)

        if start_marker is None or end_marker is None:
            return None

        # Get segment data from analyzer
        track_points, distance, ascent, descent = self.analyzer.get_segment_between_points(
            start_marker.track_point, end_marker.track_point
        )

        # Calculate average gradient (ascent / distance * 100)
        avg_gradient = (ascent / distance * 100) if distance > 0 else 0.0

        return Segment(
            start_marker=start_marker,
            end_marker=end_marker,
            distance=distance,
            ascent=ascent,
            descent=descent,
            track_points=track_points,
            avg_gradient=avg_gradient,
        )

    def get_all_segments(self) -> list[Segment]:
        """
        Get all segments between consecutive markers.

        Returns:
            List of Segment objects
        """
        segments = []
        for i in range(len(self.markers) - 1):
            segment = self.get_segment(i, i + 1)
            if segment is not None:
                segments.append(segment)
        return segments

    def get_marker_count(self) -> int:
        """
        Get the total number of markers.

        Returns:
            Number of markers
        """
        return len(self.markers)

    def move_marker_up(self, index: int) -> bool:
        """
        Move a marker up in the list (swap with previous marker).

        Args:
            index: Index of the marker to move

        Returns:
            True if the marker was moved, False otherwise
        """
        if index <= 0 or index >= len(self.markers):
            return False

        # Swap with previous marker
        self.markers[index], self.markers[index - 1] = self.markers[index - 1], self.markers[index]

        # Update indices
        self.markers[index - 1].index = index - 1
        self.markers[index].index = index

        return True

    def move_marker_down(self, index: int) -> bool:
        """
        Move a marker down in the list (swap with next marker).

        Args:
            index: Index of the marker to move

        Returns:
            True if the marker was moved, False otherwise
        """
        if index < 0 or index >= len(self.markers) - 1:
            return False

        # Swap with next marker
        self.markers[index], self.markers[index + 1] = self.markers[index + 1], self.markers[index]

        # Update indices
        self.markers[index].index = index
        self.markers[index + 1].index = index + 1

        return True
