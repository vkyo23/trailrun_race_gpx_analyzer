"""
GPX analyzer module for extracting and analyzing GPX track data.

This module provides functionality to extract track points, calculate distances,
and process elevation data from GPX files using industry-standard algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import polars as pl
from scipy.signal import savgol_filter

from project.settings import settings

if TYPE_CHECKING:
    from gpxpy.gpx import GPX, GPXTrackPoint


@dataclass
class TrackPoint:
    """Represents a single point on the GPS track."""

    latitude: float
    longitude: float
    elevation: float
    distance_from_start: float  # Cumulative distance in meters
    index: int  # Index in the original track
    course: float | None = None  # Direction of travel in degrees (0-360, None if not available)


@dataclass
class Waypoint:
    """Represents a waypoint from GPX file."""

    name: str
    latitude: float
    longitude: float
    elevation: float | None = None
    description: str | None = None


@dataclass
class GPXStats:
    """Statistics extracted from GPX data."""

    total_distance: float  # Total distance in meters
    total_ascent: float  # Total elevation gain in meters
    total_descent: float  # Total elevation loss in meters
    min_elevation: float  # Minimum elevation in meters
    max_elevation: float  # Maximum elevation in meters
    total_points: int  # Number of track points


class GPXAnalyzer:
    """Class for analyzing GPX track data."""

    def __init__(self, gpx: GPX) -> None:
        """
        Initialize the GPX analyzer.

        Args:
            gpx: Parsed GPX object to analyze

        """
        self.gpx = gpx
        self._track_points: list[TrackPoint] | None = None
        self._dataframe: pl.DataFrame | None = None
        self._stats: GPXStats | None = None
        self._waypoints: list[Waypoint] | None = None

    def extract_track_points(self) -> list[TrackPoint]:
        """
        Extract all track points from the GPX file with cumulative distances.

        Returns:
            List of TrackPoint objects

        Raises:
            ValueError: If no track points are found in the GPX file

        """
        if self._track_points is not None:
            return self._track_points

        track_points: list[TrackPoint] = []
        cumulative_distance = 0.0
        prev_point: GPXTrackPoint | None = None
        index = 0

        # Extract points from all tracks and segments
        for track in self.gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    # Calculate distance from previous point
                    if prev_point is not None:
                        distance = self._haversine_distance(
                            prev_point.latitude,
                            prev_point.longitude,
                            point.latitude,
                            point.longitude,
                        )
                        cumulative_distance += distance

                    track_points.append(
                        TrackPoint(
                            latitude=point.latitude,
                            longitude=point.longitude,
                            elevation=point.elevation or 0.0,
                            distance_from_start=cumulative_distance,
                            index=index,
                            course=point.course if hasattr(point, "course") else None,
                        )
                    )

                    prev_point = point
                    index += 1

        if not track_points:
            msg = "No track points found in GPX file"
            raise ValueError(msg)

        self._track_points = track_points
        return track_points

    def get_dataframe(self) -> pl.DataFrame:
        """
        Get track data as a Polars DataFrame.

        Returns:
            DataFrame with columns: latitude, longitude, elevation, distance, index

        """
        if self._dataframe is not None:
            return self._dataframe

        points = self.extract_track_points()

        self._dataframe = pl.DataFrame(
            {
                "latitude": [p.latitude for p in points],
                "longitude": [p.longitude for p in points],
                "elevation": [p.elevation for p in points],
                "distance": [p.distance_from_start for p in points],
                "index": [p.index for p in points],
                "course": [p.course for p in points],
            }
        )

        return self._dataframe

    def extract_waypoints(self) -> list[Waypoint]:
        """
        Extract all waypoints from the GPX file.

        Returns:
            List of Waypoint objects
        """
        if self._waypoints is not None:
            return self._waypoints

        # Extract waypoints from GPX using list comprehension
        waypoints = [
            Waypoint(
                name=waypoint.name or "Waypoint",
                latitude=waypoint.latitude,
                longitude=waypoint.longitude,
                elevation=waypoint.elevation,
                description=waypoint.description,
            )
            for waypoint in self.gpx.waypoints
        ]

        self._waypoints = waypoints
        return waypoints

    def calculate_stats(self) -> GPXStats:
        """
        Calculate overall statistics for the GPX track.

        This method uses Strava/Garmin/COROS-compliant elevation calculation with:
        1. Distance-based resampling (normalize sampling density)
        2. Outlier removal (IQR method)
        3. Savitzky-Golay smoothing filter
        4. Threshold filter (1-3m) to ignore GPS noise

        Returns:
            GPXStats object containing track statistics

        """
        if self._stats is not None:
            return self._stats

        points = self.extract_track_points()
        df = self.get_dataframe()

        # Get raw elevation and distance data
        distances = df["distance"].to_numpy()
        elevations = df["elevation"].to_numpy()

        # Step 1: Resample at regular distance intervals (only for long tracks)
        # This normalizes sampling density and reduces impact of variable recording rates
        total_distance = distances[-1] if len(distances) > 0 else 0.0
        if total_distance > settings.min_distance_for_resampling:
            _, resampled_elevations = self._resample_by_distance(
                distances, elevations, settings.distance_resampling_meters
            )
        else:
            # Skip resampling for short tracks
            resampled_elevations = elevations

        # Step 2: Remove outliers (GPS errors, unrealistic spikes)
        cleaned_elevations = self._remove_outliers(resampled_elevations)

        # Step 3: Apply advanced smoothing (Savitzky-Golay filter)
        smoothed_elevations = self._smooth_elevation_advanced(cleaned_elevations)

        # Step 4: Calculate ascent/descent with threshold filter
        ascent, descent = self._calculate_elevation_gain_loss(smoothed_elevations)

        # Get min/max elevation values from original data
        elevations_array = df["elevation"].to_numpy()

        self._stats = GPXStats(
            total_distance=points[-1].distance_from_start if points else 0.0,
            total_ascent=ascent,
            total_descent=descent,
            min_elevation=float(np.min(elevations_array)),
            max_elevation=float(np.max(elevations_array)),
            total_points=len(points),
        )

        return self._stats

    def find_nearest_point(self, latitude: float, longitude: float) -> TrackPoint:
        """
        Find the nearest track point to the given coordinates.

        Args:
            latitude: Target latitude
            longitude: Target longitude

        Returns:
            The nearest TrackPoint on the track

        """
        points = self.extract_track_points()

        min_distance = float("inf")
        nearest_point = points[0]

        for point in points:
            distance = self._haversine_distance(latitude, longitude, point.latitude, point.longitude)
            if distance < min_distance:
                min_distance = distance
                nearest_point = point

        return nearest_point

    def get_segment_between_points(
        self, start_point: TrackPoint, end_point: TrackPoint
    ) -> tuple[list[TrackPoint], float, float, float]:
        """
        Get track segment between two points and calculate statistics.

        Args:
            start_point: Starting track point
            end_point: Ending track point

        Returns:
            Tuple of (segment_points, distance, ascent, descent)

        """
        points = self.extract_track_points()

        # Ensure start comes before end
        start_idx = start_point.index
        end_idx = end_point.index
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        # Extract segment
        segment = points[start_idx : end_idx + 1]

        # Calculate distance
        distance = end_point.distance_from_start - start_point.distance_from_start

        # Calculate elevation gain/loss for segment using same method as full track
        elevations = np.array([p.elevation for p in segment])
        distances_segment = np.array([p.distance_from_start - start_point.distance_from_start for p in segment])

        # Step 1: Resample at regular distance intervals (only for long segments)
        segment_distance = abs(distance)
        if segment_distance > settings.min_distance_for_resampling:
            _, resampled_elevations = self._resample_by_distance(
                distances_segment, elevations, settings.distance_resampling_meters
            )
        else:
            # Skip resampling for short segments
            resampled_elevations = elevations

        # Step 2: Remove outliers
        cleaned_elevations = self._remove_outliers(resampled_elevations)

        # Step 3: Apply smoothing
        smoothed_elevations = self._smooth_elevation_advanced(cleaned_elevations)

        # Step 4: Calculate with threshold
        ascent, descent = self._calculate_elevation_gain_loss(smoothed_elevations)

        return segment, abs(distance), ascent, descent

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        Args:
            lat1: Latitude of first point in degrees
            lon1: Longitude of first point in degrees
            lat2: Latitude of second point in degrees
            lon2: Longitude of second point in degrees

        Returns:
            Distance in meters

        """
        # Convert to radians
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
        c = 2 * np.arcsin(np.sqrt(a))

        # Earth radius in meters
        earth_radius = 6371000

        return float(earth_radius * c)

    @staticmethod
    def _resample_by_distance(
        distances: np.ndarray, elevations: np.ndarray, interval: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Resample elevation data at regular distance intervals.

        This approach is used by professional GPS platforms to normalize
        sampling density and reduce the impact of variable recording rates.

        Args:
            distances: Array of cumulative distances from start (meters)
            elevations: Array of elevation values (meters)
            interval: Distance interval for resampling (meters)

        Returns:
            Tuple of (resampled_distances, resampled_elevations)

        """
        if len(distances) < 2 or len(elevations) < 2:
            return distances, elevations

        # Create new distance array at regular intervals
        total_distance = distances[-1]
        num_samples = int(total_distance / interval) + 1
        new_distances = np.linspace(0, total_distance, num_samples)

        # Interpolate elevation at new distances
        new_elevations = np.interp(new_distances, distances, elevations)

        return new_distances, new_elevations

    @staticmethod
    def _remove_outliers(elevations: np.ndarray) -> np.ndarray:
        """
        Remove outliers from elevation data using IQR method.

        This helps eliminate GPS errors and unrealistic elevation spikes.

        Args:
            elevations: Array of elevation values

        Returns:
            Cleaned elevation array with outliers replaced by interpolation

        """
        # For very short datasets or insufficient data, skip outlier removal
        if len(elevations) < 20:
            return elevations

        # Calculate IQR
        q1 = np.percentile(elevations, 25)
        q3 = np.percentile(elevations, 75)
        iqr = q3 - q1

        # Define outlier bounds
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Identify outliers
        outliers = (elevations < lower_bound) | (elevations > upper_bound)

        # Replace outliers with interpolated values
        cleaned = elevations.copy()
        if np.any(outliers):
            # Use linear interpolation for outliers
            indices = np.arange(len(elevations))
            good_indices = indices[~outliers]
            good_values = elevations[~outliers]

            if len(good_values) > 0:
                cleaned[outliers] = np.interp(indices[outliers], good_indices, good_values)

        return cleaned

    @staticmethod
    def _smooth_elevation_advanced(elevations: np.ndarray) -> np.ndarray:
        """
        Smooth elevation data using Savitzky-Golay filter.

        This is a more sophisticated smoothing method used by professional
        GPS devices and platforms like Strava. It preserves the shape of
        the elevation profile better than simple moving averages.

        Args:
            elevations: Array of elevation values

        Returns:
            Smoothed elevation array

        """
        window_length = settings.elevation_smoothing_window

        # For very short datasets, skip smoothing to preserve elevation changes
        # (testing/short tracks with < 20 points)
        if len(elevations) < 20:
            return elevations

        # For short datasets, use minimal smoothing
        if len(elevations) < 50:
            window_length = 3
        elif len(elevations) < window_length:
            # For medium-length tracks, use adaptive window
            window_length = len(elevations) if len(elevations) % 2 == 1 else len(elevations) - 1

        if window_length < 3:
            return elevations

        # Ensure window length is odd
        if window_length % 2 == 0:
            window_length -= 1

        # Use polynomial order 2 for smoothing (preserves trends)
        polyorder = min(2, window_length - 1)

        try:
            smoothed = savgol_filter(
                elevations,
                window_length=window_length,
                polyorder=polyorder,
                mode="nearest",
            )
        except (ValueError, np.linalg.LinAlgError):
            # Fallback to original if smoothing fails
            return elevations
        else:
            return smoothed

    @staticmethod
    def _calculate_elevation_gain_loss(
        elevations: np.ndarray, threshold: float = settings.elevation_threshold_meters
    ) -> tuple[float, float]:
        """
        Calculate total elevation gain and loss using industry-standard method.

        This method follows the approach used by Strava, Garmin, and Coros:
        - Apply threshold filter (1-3m is industry standard) to ignore noise
        - Sum positive changes above threshold for ascent
        - Sum negative changes above threshold for descent

        The threshold helps eliminate GPS jitter and small elevation fluctuations
        that don't represent real climbing/descending.

        Args:
            elevations: Array of smoothed elevation values
            threshold: Minimum elevation change to count (meters)

        Returns:
            Tuple of (total_ascent, total_descent) in meters

        """
        if len(elevations) < 2:
            return 0.0, 0.0

        # Calculate elevation changes between consecutive points
        elevation_diffs = np.diff(elevations)

        # Apply threshold filter: only count changes above threshold
        # This is the key difference from naive implementation
        total_ascent = float(np.sum(elevation_diffs[elevation_diffs > threshold]))
        total_descent = float(np.abs(np.sum(elevation_diffs[elevation_diffs < -threshold])))

        return total_ascent, total_descent
