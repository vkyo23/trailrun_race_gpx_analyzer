"""
Unit tests for GPX analyzer module.
"""

import numpy as np
import pytest
from gpxpy.gpx import GPX

from project.data_accessors.gpx_analyzer import GPXAnalyzer


class TestGPXAnalyzer:
    """Test cases for GPXAnalyzer class."""

    def test_extract_track_points(self, sample_gpx: GPX) -> None:
        """Test extracting track points from GPX."""
        analyzer = GPXAnalyzer(sample_gpx)
        points = analyzer.extract_track_points()

        assert len(points) == 10
        assert points[0].latitude == pytest.approx(35.3606)
        assert points[0].longitude == pytest.approx(138.7274)
        assert points[0].elevation == pytest.approx(1000.0)
        assert points[0].distance_from_start == pytest.approx(0.0)
        assert points[0].index == 0

    def test_get_dataframe(self, sample_gpx: GPX) -> None:
        """Test getting track data as DataFrame."""
        analyzer = GPXAnalyzer(sample_gpx)
        df = analyzer.get_dataframe()

        assert df.shape[0] == 10
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "elevation" in df.columns
        assert "distance" in df.columns
        assert "index" in df.columns

    def test_calculate_stats(self, sample_gpx: GPX) -> None:
        """Test calculating track statistics."""
        analyzer = GPXAnalyzer(sample_gpx)
        stats = analyzer.calculate_stats()

        assert stats.total_points == 10
        assert stats.total_distance > 0
        assert stats.min_elevation == pytest.approx(1000.0)
        assert stats.max_elevation == pytest.approx(1100.0)
        # Total ascent should be roughly 100m (accounting for smoothing and threshold)
        assert stats.total_ascent > 0
        assert stats.total_descent > 0

    def test_find_nearest_point(self, sample_gpx: GPX) -> None:
        """Test finding nearest point on track."""
        analyzer = GPXAnalyzer(sample_gpx)

        # Find point near the third track point
        nearest = analyzer.find_nearest_point(35.3641, 138.7291)

        assert nearest.latitude == pytest.approx(35.3640, abs=0.001)
        assert nearest.longitude == pytest.approx(138.7290, abs=0.001)

    def test_get_segment_between_points(self, sample_gpx: GPX) -> None:
        """Test getting segment between two points."""
        analyzer = GPXAnalyzer(sample_gpx)
        points = analyzer.extract_track_points()

        # Get segment between first and fifth point
        segment, distance, ascent, descent = analyzer.get_segment_between_points(points[0], points[4])

        assert len(segment) == 5
        assert distance > 0
        assert ascent > 0  # Should be ascending
        assert descent >= 0

    def test_haversine_distance(self) -> None:
        """Test haversine distance calculation."""
        # Tokyo to Yokohama (approximate)
        distance = GPXAnalyzer._haversine_distance(
            35.6762,
            139.6503,  # Tokyo
            35.4437,
            139.6380,  # Yokohama
        )

        # Should be approximately 26-28 km
        assert 25000 < distance < 30000

    def test_smooth_elevation(self) -> None:
        """Test elevation smoothing."""
        # Create noisy elevation data with enough points for smoothing (>= 20)
        # Smoothing is skipped for datasets < 20 points to preserve elevation changes in short tracks
        elevations = np.array(
            [
                100,
                102,
                99,
                101,
                103,
                98,
                100,
                102,
                101,
                99,
                100,
                103,
                99,
                102,
                104,
                98,
                101,
                103,
                100,
                99,
                101,
                102,
                100,
                101,
            ]
        )

        smoothed = GPXAnalyzer._smooth_elevation_advanced(elevations)

        assert len(smoothed) == len(elevations)
        # Smoothed values should have less or equal variance (never more)
        assert np.std(smoothed) <= np.std(elevations)

    def test_calculate_elevation_gain_loss(self) -> None:
        """Test elevation gain/loss calculation with threshold."""
        # Create elevation profile with clear ascent and descent
        elevations = np.array(
            [
                100.0,
                105.0,
                110.0,
                115.0,  # +15m ascent
                115.0,
                110.0,
                105.0,
                100.0,  # -15m descent
            ]
        )

        ascent, descent = GPXAnalyzer._calculate_elevation_gain_loss(elevations)

        # Should detect significant elevation changes
        assert ascent > 0
        assert descent > 0

    def test_empty_gpx(self) -> None:
        """Test handling empty GPX file."""
        empty_gpx = GPX()
        analyzer = GPXAnalyzer(empty_gpx)

        with pytest.raises(ValueError, match="No track points found"):
            analyzer.extract_track_points()
