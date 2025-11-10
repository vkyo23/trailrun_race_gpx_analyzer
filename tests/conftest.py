"""
Pytest configuration and shared fixtures.
"""

import io
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests
from gpxpy.gpx import GPX, GPXTrack, GPXTrackPoint, GPXTrackSegment


@pytest.fixture(scope="session")
def streamlit_app():
    """
    Start the Streamlit application for e2e tests.

    This fixture starts the app on port 8080 and waits for it to be ready.
    After all tests complete, it shuts down the server.

    Yields:
        str: URL of the running application
    """
    # Start Streamlit app
    uv_path = shutil.which("uv")
    if not uv_path:
        msg = "uv executable not found in PATH"
        raise RuntimeError(msg)

    process = subprocess.Popen(  # noqa: S603
        [uv_path, "run", "streamlit", "run", "app.py", "--server.port=8080", "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for app to be ready (max 30 seconds)
    app_url = "http://localhost:8080"
    max_retries = 60
    retry_delay = 0.5

    for _ in range(max_retries):
        try:
            response = requests.get(app_url, timeout=1)
            if response.status_code == 200:
                break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(retry_delay)
    else:
        process.terminate()
        process.wait()
        msg = "Streamlit app failed to start within timeout period"
        raise RuntimeError(msg)

    yield app_url

    # Cleanup: terminate the process
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(autouse=True)
def setup_e2e_tests(request):
    """
    Automatically ensure the Streamlit app is running for e2e tests.

    This fixture runs automatically for all tests and starts the app
    only when the test is marked with 'e2e'.

    Args:
        request: Pytest request object
    """
    # Only apply to e2e tests
    if "e2e" in [marker.name for marker in request.node.iter_markers()]:
        # Request the streamlit_app fixture to ensure it starts
        request.getfixturevalue("streamlit_app")


@pytest.fixture
def sample_gpx() -> GPX:
    """
    Create a sample GPX object for testing.

    Returns:
        GPX object with a simple track
    """
    gpx = GPX()

    # Create track
    track = GPXTrack()
    gpx.tracks.append(track)

    # Create segment
    segment = GPXTrackSegment()
    track.segments.append(segment)

    # Add some points along a path
    # Simulating a trail from start to finish with elevation changes
    points_data = [
        (35.3606, 138.7274, 1000.0),  # Start
        (35.3620, 138.7280, 1020.0),  # +20m
        (35.3640, 138.7290, 1050.0),  # +30m
        (35.3660, 138.7310, 1080.0),  # +30m
        (35.3680, 138.7330, 1100.0),  # +20m
        (35.3700, 138.7350, 1090.0),  # -10m
        (35.3720, 138.7370, 1070.0),  # -20m
        (35.3740, 138.7390, 1060.0),  # -10m
        (35.3760, 138.7410, 1050.0),  # -10m
        (35.3780, 138.7430, 1040.0),  # -10m
    ]

    for lat, lon, ele in points_data:
        point = GPXTrackPoint(latitude=lat, longitude=lon, elevation=ele)
        segment.points.append(point)

    return gpx


@pytest.fixture
def sample_gpx_bytes(sample_gpx: GPX) -> io.BytesIO:
    """
    Convert sample GPX to bytes for file upload simulation.

    Args:
        sample_gpx: Sample GPX fixture

    Returns:
        BytesIO object containing GPX data
    """
    gpx_string = sample_gpx.to_xml()
    return io.BytesIO(gpx_string.encode("utf-8"))


@pytest.fixture
def sample_gpx_file(tmp_path: Path, sample_gpx: GPX) -> Path:
    """
    Create a temporary GPX file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture
        sample_gpx: Sample GPX fixture

    Returns:
        Path to the temporary GPX file
    """
    gpx_file = tmp_path / "test_track.gpx"
    with gpx_file.open("w", encoding="utf-8") as f:
        f.write(sample_gpx.to_xml())
    return gpx_file
