"""
GPX file loader module for loading GPX data from local files or URLs.

This module provides functionality to load and parse GPX files from various sources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import gpxpy
import gpxpy.gpx
import requests

from project.settings import settings

if TYPE_CHECKING:
    from pathlib import Path
    from typing import BinaryIO

    from gpxpy.gpx import GPX


class GPXLoadError(Exception):
    """Exception raised when GPX file cannot be loaded or parsed."""


class GPXLoader:
    """Class responsible for loading GPX files from various sources."""

    @staticmethod
    def load_from_file(file: BinaryIO) -> GPX:
        """
        Load GPX data from an uploaded file object.

        Args:
            file: Binary file object containing GPX data

        Returns:
            Parsed GPX object

        Raises:
            GPXLoadError: If the file cannot be parsed as valid GPX

        """
        # Read file content
        content = file.read()

        # Check file size
        file_size_mb = len(content) / (1024 * 1024)
        max_size = settings.max_gpx_file_size_mb
        if file_size_mb > max_size:
            msg = f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size}MB)"
            raise GPXLoadError(msg)

        # Parse GPX (decode bytes to string)
        try:
            content_str = content.decode("utf-8")
            return gpxpy.parse(content_str)
        except UnicodeDecodeError as e:
            msg = f"Error decoding GPX file: {e!s}"
            raise GPXLoadError(msg) from e
        except gpxpy.gpx.GPXException as e:
            msg = f"Invalid GPX file format: {e!s}"
            raise GPXLoadError(msg) from e
        except OSError as e:
            msg = f"Error loading GPX file: {e!s}"
            raise GPXLoadError(msg) from e

    @staticmethod
    def load_from_url(url: str, timeout: int = 30) -> GPX:
        """
        Load GPX data from a URL.

        Args:
            url: URL pointing to a GPX file
            timeout: Request timeout in seconds (default: 30)

        Returns:
            Parsed GPX object

        Raises:
            GPXLoadError: If the URL cannot be accessed or parsed as valid GPX

        """
        try:
            # Fetch GPX file from URL
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            msg = f"Error fetching GPX from URL: {e!s}"
            raise GPXLoadError(msg) from e

        # Check content size
        content_length = len(response.content)
        file_size_mb = content_length / (1024 * 1024)
        max_size = settings.max_gpx_file_size_mb
        if file_size_mb > max_size:
            msg = f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size}MB)"
            raise GPXLoadError(msg)

        # Parse GPX
        try:
            return gpxpy.parse(response.text)
        except gpxpy.gpx.GPXException as e:
            msg = f"Invalid GPX file format: {e!s}"
            raise GPXLoadError(msg) from e
        except OSError as e:
            msg = f"Error loading GPX from URL: {e!s}"
            raise GPXLoadError(msg) from e

    @staticmethod
    def load_from_path(file_path: Path) -> GPX:
        """
        Load GPX data from a local file path.

        Args:
            file_path: Path to the GPX file

        Returns:
            Parsed GPX object

        Raises:
            GPXLoadError: If the file cannot be found or parsed as valid GPX

        """
        try:
            with file_path.open("rb") as f:
                return GPXLoader.load_from_file(f)
        except FileNotFoundError as e:
            msg = f"File not found: {file_path}"
            raise GPXLoadError(msg) from e
        except OSError as e:
            msg = f"Error loading GPX file: {e!s}"
            raise GPXLoadError(msg) from e
