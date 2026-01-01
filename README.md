# RTL433 Geo-Logger

A geolocation logger for RTL433 sensor data with web map visualization and RSSI heatmap support.

## Protocol Support

RTL433 Geo-Logger supports **all RTL433 protocols**, including:
- ✅ Standard built-in protocols (Acurite, Oregon Scientific, LaCrosse, etc.)
- ✅ Custom protocols defined with flex decoder
- ✅ Protocols with non-standard field names
- ✅ Minimal data without standard fields

See [PROTOCOLS.md](PROTOCOLS.md) for detailed information about protocol support.

### How It Works

The logger uses flexible field extraction that works with any protocol:
- **Complete data preservation**: All JSON data stored in `data_json` field
- **Smart field detection**: Extracts protocol, device ID, and RSSI from various field names
- **Graceful fallback**: Continues logging even if standard fields are missing

## Features

- **SQLite Database Storage**: Stores RTL433 sensor data with GPS coordinates
- **Universal Protocol Support**: Works with all RTL433 protocols including custom ones
- **GPS Integration**: Captures GPS timestamp, coordinates, and altitude via GPSD
- **Protocol & Device ID Support**: Automatically extracts protocol and device ID from RTL433 data
- **RSSI Tracking**: Records signal strength for heatmap visualization
- **Web Map Interface**: Interactive Leaflet map with:
  - Real-time data visualization
  - RSSI-based heatmap
  - Filter by protocol and device ID
  - Auto-refresh capability
- **REST API**: Query and filter logged data

## Documentation

- **[README.md](README.md)** - Main documentation (this file)
- **[PROTOCOLS.md](PROTOCOLS.md)** - Protocol support and custom protocol guide
- **[API.md](API.md)** - REST API documentation and usage examples
- **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration examples and production setup
- **[TESTING.md](TESTING.md)** - Testing guide and troubleshooting
- **[examples/](examples/)** - Example data and test scripts

## Requirements

- Python 3.7+
- RTL433 (for receiving sensor data)
- GPSD (optional, for GPS support)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/remiserriere/rtl433-geo-logger.git
cd rtl433-geo-logger
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or
pip install -e .
```

## Usage

### Data Collection

The logger reads RTL433 JSON output from stdin and stores it with GPS data:

```bash
# Basic usage (without GPS)
rtl_433 -F json | rtl433-logger --no-gps

# With GPS support (requires GPSD running)
rtl_433 -F json | rtl433-logger

# Specify custom database location
rtl_433 -F json | rtl433-logger --db /path/to/data.db

# Custom GPSD connection
rtl_433 -F json | rtl433-logger --gps-host 192.168.1.100 --gps-port 2947
```

### Web Interface

Start the web server to view data on a map:

```bash
# Start web server (default: http://0.0.0.0:5000)
rtl433-web

# Custom database and port
rtl433-web --db /path/to/data.db --port 8080

# Enable debug mode
rtl433-web --debug
```

Then open your browser to `http://localhost:5000`

### Web Interface Features

- **Map View**: Displays all logged data points with GPS coordinates
- **Markers**: Click on markers to see detailed information (protocol, device ID, RSSI, timestamp, altitude)
- **Heatmap**: Toggle button to switch between marker view and RSSI-based heatmap
- **Filters**: 
  - Filter by protocol (all available protocols in dropdown)
  - Filter by device ID (all available devices in dropdown)
  - Clear filters button to reset
- **Auto-refresh**: Enable to automatically refresh data every 10 seconds
- **Statistics Panel**: Shows total logs, GPS coverage, unique protocols/devices

## Database Schema

The SQLite database contains a single table `rtl433_logs`:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | DATETIME | RTL433 reading timestamp |
| gps_timestamp | DATETIME | GPS timestamp (if available) |
| latitude | REAL | GPS latitude |
| longitude | REAL | GPS longitude |
| altitude | REAL | GPS altitude in meters |
| protocol | TEXT | Device protocol/model |
| device_id | TEXT | Device identifier |
| rssi | INTEGER | Signal strength in dBm |
| data_json | TEXT | Complete RTL433 data as JSON |
| created_at | DATETIME | Database insertion timestamp |

## API Endpoints

### GET /api/logs

Get logs with optional filters:

Query parameters:
- `limit`: Maximum records to return (default: 100)
- `offset`: Pagination offset (default: 0)
- `device_id`: Filter by device ID
- `protocol`: Filter by protocol
- `hours`: Get logs from last N hours

Example:
```bash
curl "http://localhost:5000/api/logs?protocol=Acurite-Tower&limit=50"
```

### GET /api/logs/location

Get logs with GPS location data:

Query parameters:
- `limit`: Maximum records to return (default: 1000)
- `hours`: Get logs from last N hours

Example:
```bash
curl "http://localhost:5000/api/logs/location?hours=24"
```

### GET /api/statistics

Get database statistics:

```bash
curl "http://localhost:5000/api/statistics"
```

Returns:
```json
{
  "total_logs": 1523,
  "logs_with_gps": 1401,
  "unique_protocols": 8,
  "unique_devices": 12,
  "earliest_log": "2024-01-01T10:00:00",
  "latest_log": "2024-01-15T18:30:00"
}
```

## Example RTL433 Setup

Complete setup example with GPS:

```bash
# Terminal 1: Start GPSD
gpsd -N /dev/ttyUSB0

# Terminal 2: Start data collection
rtl_433 -F json | rtl433-logger

# Terminal 3: Start web interface
rtl433-web

# Open browser to http://localhost:5000
```

## Device ID Support

The logger automatically extracts device IDs from various RTL433 outputs. Common field names:
- `id`
- `device_id`
- `device`
- `sensor_id`
- `address`
- `code`

If no device ID field is found, the entry is still logged but without a device ID.

## RSSI Heatmap

The heatmap visualization uses RSSI values to show signal strength distribution:
- **Blue**: Weak signals (-100 dBm)
- **Green**: Moderate signals (-50 dBm)
- **Yellow**: Strong signals (-30 dBm)
- **Red**: Very strong signals (0 dBm)

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.