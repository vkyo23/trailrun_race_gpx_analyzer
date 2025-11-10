# Trail Running Race GPX Analyzer

A comprehensive Streamlit web application for analyzing GPX files from trail running races. Calculate distances, elevation gains, and segment statistics with interactive maps and charts.

![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)
![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **GPX File Upload**: Load GPX files from local storage or URL
- **Automatic Waypoint Import**: Automatically loads waypoints (start/goal/aid stations) from GPX files
- **Interactive Map**: YAMAP-style UI with clickable track line and direction arrows
- **Direction Visualization**: Blue arrows showing track direction every 2km
- **Elevation Profile**: View elevation changes along your route with interactive charts
- **Marker Management**: Add markers by clicking on the track line or entering coordinates
- **Marker Reordering**: Move markers up/down with arrow buttons
- **Segment Analysis**: Calculate distance, elevation gain/loss, and average gradient between markers
- **CSV Export**: Export segment data for further analysis

## Demo

### Main Interface
- Upload GPX files and view track statistics
- Interactive map with route visualization
- Add markers to key points along the route

### Segment Analysis
- Calculate distances and elevation changes between markers
- Export data to CSV for race planning
- Compare multiple segments with charts

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (optional, for containerized deployment)

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/vkyo23/trailrun_race_gpx_analyzer.git
cd trailrun_race_gpx_analyzer
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Run the application:
```bash
uv run streamlit run app.py
```

4. Open your browser and navigate to `http://localhost:8501`

### Docker Setup

1. Build and run with Docker Compose:
```bash
docker compose up --build
```

2. Access the application at `http://localhost:8501`

## Usage

### 1. Upload a GPX File

**From Local File:**
- Click "����ա��" (Local File)
- Select your GPX file
- Wait for the file to load

**From URL:**
- Click "URL"
- Enter the GPX file URL
- Click "URLから読み込む" (Load from URL)

### 2. View Track Statistics

After loading a GPX file, you'll see:
- Total distance (km)
- Total elevation gain (m)
- Total elevation loss (m)
- Elevation range (min-max)
- Number of track points

### 3. Add Markers

**Automatic Registration:**
When you load a GPX file, the following markers are automatically registered:
- Track start point (スタート)
- Waypoints from GPX file (aid stations, checkpoints, etc.)
- Track end point (ゴール)

**By Track Click:**
1. Enter a marker name (previous name is retained for easy consecutive additions)
2. Select "トラッククリック" (Track Click)
3. Click on the orange track line on the map
4. Click "マーカーを追加" (Add Marker)
- New markers are inserted before the goal marker

**By Coordinates:**
1. Enter a marker name
2. Select "緯度経度入力" (Coordinate Input)
3. Enter latitude and longitude
4. Click "マーカーを追加" (Add Marker)

**Marker Management:**
- **↑↓ buttons**: Reorder markers (move up/down)
- **削除 button**: Delete individual marker
- **すべてのマーカーをクリア**: Clear all markers

### 4. Analyze Segments

Once you have 2+ markers:
- View segment analysis table with:
  - Distance (km)
  - Elevation gain (m)
  - Elevation loss (m)
  - Average gradient (%) = elevation gain / distance × 100
- Select segments to highlight instantly on map (red line) and chart
- Download segment data as CSV

## Architecture

### Project Structure

```
trailrun_race_gpx_analyzer/
├── app.py                        # Main application entry point
├── project/
│   ├── application_services/     # Business logic layer
│   │   ├── gpx_service.py        # High-level GPX operations
│   │   └── marker_manager.py     # Marker and segment management
│   ├── data_accessors/           # Data access layer
│   │   ├── gpx_analyzer.py       # GPX analysis and calculations
│   │   └── gpx_loader.py         # GPX file loading
│   ├── views/                    # UI components
│   │   ├── chart_view.py         # Elevation charts
│   │   └── map_view.py           # Interactive maps
│   ├── settings.py               # Application configuration
│   └── ui.py                     # Main UI logic
├── tests/
│   ├── unit/                     # Unit tests
│   └── e2e/                      # End-to-end tests
├── usages/
│   └── usage.md                  # Detailed usage guide (Japanese)
├── Dockerfile                    # Docker configuration
├── compose.yaml                  # Docker Compose configuration
└── pyproject.toml                # Project dependencies and config
```

### Technology Stack

- **Framework**: Streamlit
- **Data Processing**: Polars, NumPy, SciPy
- **GPX Parsing**: gpxpy
- **Visualization**: Plotly, Folium
- **Configuration**: pydantic-settings
- **Testing**: pytest, Playwright
- **Package Management**: uv

## Elevation Calculation

The application uses industry-standard elevation calculation methods similar to Strava, Garmin, and Coros:

### 1. Smoothing
- Applies a moving average filter to reduce GPS noise
- Default window size: 5 points
- Configurable in `settings.py`

### 2. Threshold-Based Accumulation
- Only counts elevation changes >= 3m (default)
- Prevents GPS noise from inflating elevation gain
- Separate tracking for ascent and descent

### 3. Distance Calculation
- Uses Haversine formula for great-circle distance
- Markers snap to nearest point on GPX track
- Calculates cumulative distance along the track

## Development

### Running Tests

**Unit Tests:**
```bash
uv run pytest tests/unit/ -v
```

**E2E Tests (requires running app):**
```bash
playwright install

# Run E2E tests
uv run pytest tests/e2e/ -v -m e2e
```

**All Tests:**
```bash
uv run pytest -v
```

### Code Quality

**Linting:**
```bash
uv run ruff check .
```

**Formatting:**
```bash
uv run ruff format .
```

**Type Checking:**
```bash
uv run mypy project/ tests/
```

### CI/CD

The project uses GitHub Actions for continuous integration:
- Linting and type checking
- Unit tests
- Docker build verification

## Configuration

### Application Settings

Edit [project/settings.py](project/settings.py) to configure:

```python
# Elevation calculation
elevation_smoothing_window: int = 5
elevation_threshold_meters: float = 3.0

# File limits
max_gpx_file_size_mb: int = 50

# UI settings
default_map_zoom: int = 13
map_height: int = 600
elevation_chart_height: int = 400
```

### Streamlit Configuration

Edit [.streamlit/config.toml](.streamlit/config.toml) for Streamlit-specific settings.

## Docker Deployment

### Production Deployment

1. Remove the volume mount in `compose.yaml` for production:
```yaml
volumes:
  # Comment out for production
  # - .:/app
  - streamlit-cache:/root/.streamlit
```

2. Build and run:
```bash
docker compose up -d
```

### Environment Variables

Configure via environment variables in `compose.yaml`:
```yaml
environment:
  - DEBUG=false
  - ELEVATION_SMOOTHING_WINDOW=5
  - ELEVATION_THRESHOLD_METERS=3.0
```

## Use Cases

### Race Preparation
1. Upload official race GPX file
2. Add markers at aid stations and checkpoints
3. Calculate segment distances and elevation
4. Export data for pacing strategy and crew planning

### Training Planning
1. Upload training route GPX
2. Mark key segments for interval training
3. Analyze elevation profiles for specific sections

### Course Reconnaissance
1. Upload reconnaissance run GPX
2. Mark difficult sections and key points
3. Review elevation changes for race strategy

## Troubleshooting

### GPX File Won't Load
- Ensure file format is valid GPX
- Check file size is under 50MB
- Verify track data is present

### Elevation Values Differ from Other Services
- GPS accuracy and smoothing algorithms vary between services
- Our app uses standard industry methods
- Small differences (±5%) are normal

### Markers Not Adding
- Ensure marker name is entered
- Click on the orange track line (not outside the track)
- Check coordinates are specified (click track or enter lat/lon)
- Verify GPX file is loaded

### Direction Arrows Not Showing
- If GPX file doesn't contain course data, direction is calculated from adjacent points
- Arrows appear every 2km
- Very short tracks (< 2km) may not show arrows

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- GPX parsing: [gpxpy](https://github.com/tkrajina/gpxpy)
- Data processing: [Polars](https://www.pola.rs/)
- Web framework: [Streamlit](https://streamlit.io/)
- Mapping: [Folium](https://python-visualization.github.io/folium/)
- Charts: [Plotly](https://plotly.com/)

## Support

For issues and questions:
- Open an issue on GitHub
- Check the [usage guide](usages/usage.md) (Japanese)
- Review the help tab in the application

## Changelog

### Version 0.0.1 (Current)

**Features:**
- Automatic waypoint import from GPX files
- YAMAP-style track visualization with direction arrows
- Marker reordering functionality
- Average gradient calculation in segment analysis
- Improved UI with track-only click detection
- Marker name retention for consecutive additions

**UI Improvements:**
- Removed emoji icons for cleaner interface
- Streamlined pre-upload display
- Instant segment highlighting
- Better visual feedback for track interaction

---

Made with ❤️ for trail runners
