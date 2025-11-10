"""
Unit tests for GPX service module.
"""

import io

import pytest

from project.application_services.gpx_service import GPXService


class TestGPXService:
    """Test cases for GPXService class."""

    def test_initialization(self) -> None:
        """Test service initialization."""
        service = GPXService()

        assert not service.is_loaded()

    def test_load_from_file(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test loading GPX from file."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)

        assert service.is_loaded()

    def test_get_stats_before_loading(self) -> None:
        """Test getting stats before loading GPX."""
        service = GPXService()

        with pytest.raises(ValueError, match="No GPX data loaded"):
            service.get_stats()

    def test_get_stats_after_loading(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test getting stats after loading GPX."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)

        stats = service.get_stats()

        assert stats.total_points == 10
        assert stats.total_distance > 0
        assert stats.total_ascent > 0
        assert stats.total_descent > 0

    def test_get_track_dataframe(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test getting track as DataFrame."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)

        df = service.get_track_dataframe()

        assert df.shape[0] == 10
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "elevation" in df.columns

    def test_add_marker(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test adding markers."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()

        service.add_marker("Start", 35.3606, 138.7274)
        service.add_marker("Checkpoint", 35.3700, 138.7350)

        markers = service.get_markers()
        assert len(markers) == 2
        assert markers[0].name == "Start"
        assert markers[1].name == "Checkpoint"

    def test_add_marker_before_loading(self) -> None:
        """Test adding marker before loading GPX."""
        service = GPXService()

        with pytest.raises(ValueError, match="No GPX data loaded"):
            service.add_marker("Test", 35.0, 138.0)

    def test_remove_marker(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test removing markers."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()

        service.add_marker("Marker1", 35.3606, 138.7274)
        service.add_marker("Marker2", 35.3700, 138.7350)
        service.add_marker("Marker3", 35.3780, 138.7430)

        assert len(service.get_markers()) == 3

        service.remove_marker(1)
        markers = service.get_markers()

        assert len(markers) == 2
        assert markers[0].name == "Marker1"
        assert markers[1].name == "Marker3"

    def test_clear_markers(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test clearing all markers."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)

        service.add_marker("Marker1", 35.3606, 138.7274)
        service.add_marker("Marker2", 35.3700, 138.7350)

        service.clear_markers()

        assert len(service.get_markers()) == 0

    def test_get_segments(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test getting segments between markers."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()

        service.add_marker("Start", 35.3606, 138.7274)
        service.add_marker("Mid", 35.3700, 138.7350)
        service.add_marker("End", 35.3780, 138.7430)

        segments = service.get_segments()

        assert len(segments) == 2
        assert segments[0].start_marker.name == "Start"
        assert segments[0].end_marker.name == "Mid"
        assert segments[1].start_marker.name == "Mid"
        assert segments[1].end_marker.name == "End"

    def test_get_segment(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test getting a specific segment."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()

        service.add_marker("Start", 35.3606, 138.7274)
        service.add_marker("End", 35.3780, 138.7430)

        segment = service.get_segment(0, 1)

        assert segment is not None
        assert segment.start_marker.name == "Start"
        assert segment.end_marker.name == "End"
        assert segment.distance > 0

    def test_get_segments_dataframe(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test getting segments as DataFrame."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()

        service.add_marker("Start", 35.3606, 138.7274)
        service.add_marker("Mid", 35.3700, 138.7350)
        service.add_marker("End", 35.3780, 138.7430)

        df = service.get_segments_dataframe()

        assert df.shape[0] == 2
        assert "segment" in df.columns
        assert "start" in df.columns
        assert "end" in df.columns
        assert "distance_km" in df.columns
        assert "ascent_m" in df.columns
        assert "descent_m" in df.columns

    def test_get_segments_dataframe_no_markers(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test getting segments DataFrame with no markers."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()

        df = service.get_segments_dataframe()

        assert df.shape[0] == 0
        assert "segment" in df.columns

    def test_reset(self, sample_gpx_bytes: io.BytesIO) -> None:
        """Test resetting the service."""
        service = GPXService()
        service.load_from_file(sample_gpx_bytes)
        
        # Clear auto-added markers (スタート and ゴール)
        service.clear_markers()
        service.add_marker("Test", 35.3606, 138.7274)

        assert service.is_loaded()
        assert len(service.get_markers()) == 1

        service.reset()

        assert not service.is_loaded()
