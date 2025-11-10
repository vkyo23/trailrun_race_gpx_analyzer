"""
Application settings module using pydantic-settings.

This module defines the configuration settings for the Trail Running GPX Analysis application.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings class."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "Trail Running Race GPX Analyzer"
    app_version: str = "0.0.1"
    debug: bool = False

    # GPX processing settings
    elevation_smoothing_window: int = 5  # Window size for Savitzky-Golay filter
    elevation_threshold_meters: float = 0.5  # Minimum elevation change to count (adjusted for better accuracy)
    distance_resampling_meters: float = 10.0  # Distance interval for resampling (10-50m is industry standard)
    min_distance_for_resampling: float = 100.0  # Minimum track distance to apply resampling (meters)
    max_gpx_file_size_mb: int = 50  # Maximum GPX file size in MB

    # Map settings
    default_map_zoom: int = 13
    map_height: int = 600

    # Chart settings
    elevation_chart_height: int = 400


# Global settings instance
settings = Settings()
