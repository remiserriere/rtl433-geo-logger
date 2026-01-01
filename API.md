# API Usage Examples

This document provides practical examples of using the RTL433 Geo-Logger REST API.

## Base URL

When running locally:
```
http://localhost:5000
```

## Authentication

Currently no authentication is required. For production use, consider adding authentication.

## API Endpoints

### 1. Get Statistics

**Endpoint:** `GET /api/statistics`

**Description:** Returns overall database statistics.

**Example Request:**
```bash
curl http://localhost:5000/api/statistics
```

**Example Response:**
```json
{
  "total_logs": 1523,
  "logs_with_gps": 1401,
  "unique_protocols": 8,
  "unique_devices": 12,
  "earliest_log": "2024-01-15T10:00:00",
  "latest_log": "2024-01-15T18:30:00"
}
```

**Python Example:**
```python
import requests
import json

response = requests.get('http://localhost:5000/api/statistics')
stats = response.json()

print(f"Total logs: {stats['total_logs']}")
print(f"Coverage: {stats['logs_with_gps']/stats['total_logs']*100:.1f}% with GPS")
```

### 2. Get Logs

**Endpoint:** `GET /api/logs`

**Description:** Retrieve logs with optional filtering and pagination.

**Query Parameters:**
- `limit` (int): Maximum records to return (default: 100)
- `offset` (int): Pagination offset (default: 0)
- `device_id` (string): Filter by device ID
- `protocol` (string): Filter by protocol name
- `hours` (int): Get logs from last N hours

**Example Requests:**

Get latest 50 logs:
```bash
curl "http://localhost:5000/api/logs?limit=50"
```

Get logs from specific protocol:
```bash
curl "http://localhost:5000/api/logs?protocol=Acurite-Tower&limit=100"
```

Get logs from specific device:
```bash
curl "http://localhost:5000/api/logs?device_id=12345"
```

Get logs from last 24 hours:
```bash
curl "http://localhost:5000/api/logs?hours=24"
```

Pagination:
```bash
# Page 1
curl "http://localhost:5000/api/logs?limit=50&offset=0"

# Page 2
curl "http://localhost:5000/api/logs?limit=50&offset=50"
```

**Example Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00",
      "gps_timestamp": "2024-01-15T10:29:58",
      "latitude": 48.8566,
      "longitude": 2.3522,
      "altitude": 35.0,
      "protocol": "Acurite-Tower",
      "device_id": "12345",
      "rssi": -45,
      "data_json": "{...}",
      "data": {
        "time": "2024-01-15 10:30:00",
        "model": "Acurite-Tower",
        "id": 12345,
        "temperature_C": 20.5,
        "humidity": 65,
        "rssi": -45
      },
      "created_at": "2024-01-15T10:30:01"
    }
  ],
  "count": 1
}
```

**Python Example:**
```python
import requests

# Get all Acurite sensors
response = requests.get(
    'http://localhost:5000/api/logs',
    params={
        'protocol': 'Acurite-Tower',
        'limit': 100
    }
)

logs = response.json()['logs']
for log in logs:
    print(f"{log['timestamp']}: Temp={log['data']['temperature_C']}°C")
```

### 3. Get Logs with Location

**Endpoint:** `GET /api/logs/location`

**Description:** Retrieve only logs that have GPS coordinates (for mapping).

**Query Parameters:**
- `limit` (int): Maximum records to return (default: 1000)
- `hours` (int): Get logs from last N hours

**Example Requests:**

Get all logs with GPS:
```bash
curl "http://localhost:5000/api/logs/location?limit=1000"
```

Get GPS logs from last hour:
```bash
curl "http://localhost:5000/api/logs/location?hours=1"
```

**Example Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00",
      "gps_timestamp": "2024-01-15T10:29:58",
      "latitude": 48.8566,
      "longitude": 2.3522,
      "altitude": 35.0,
      "protocol": "Acurite-Tower",
      "device_id": "12345",
      "rssi": -45,
      "data_json": "{...}",
      "data": {...},
      "created_at": "2024-01-15T10:30:01"
    }
  ],
  "count": 1
}
```

**JavaScript Example (for custom map):**
```javascript
fetch('http://localhost:5000/api/logs/location?limit=500')
  .then(response => response.json())
  .then(data => {
    data.logs.forEach(log => {
      // Add marker to map
      L.marker([log.latitude, log.longitude])
        .bindPopup(`${log.protocol} - ${log.device_id}<br>RSSI: ${log.rssi}`)
        .addTo(map);
    });
  });
```

## Advanced Usage Examples

### 1. Real-time Monitoring Dashboard

**Python script to monitor latest readings:**

```python
import requests
import time
from datetime import datetime, timedelta

def get_recent_logs(minutes=5):
    """Get logs from last N minutes"""
    hours = minutes / 60
    response = requests.get(
        'http://localhost:5000/api/logs',
        params={'hours': hours, 'limit': 100}
    )
    return response.json()['logs']

def display_dashboard():
    """Display real-time dashboard"""
    while True:
        logs = get_recent_logs(5)
        
        print("\n" + "="*60)
        print(f"RTL433 Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Group by protocol
        protocols = {}
        for log in logs:
            proto = log['protocol']
            protocols[proto] = protocols.get(proto, 0) + 1
        
        print(f"\nRecent activity (last 5 minutes): {len(logs)} events")
        print("\nBy protocol:")
        for proto, count in sorted(protocols.items()):
            print(f"  {proto}: {count}")
        
        time.sleep(30)  # Update every 30 seconds

if __name__ == '__main__':
    display_dashboard()
```

### 2. Export to CSV

**Python script to export data:**

```python
import requests
import csv

def export_to_csv(output_file='rtl433_export.csv', protocol=None):
    """Export logs to CSV"""
    
    params = {'limit': 10000}
    if protocol:
        params['protocol'] = protocol
    
    response = requests.get('http://localhost:5000/api/logs', params=params)
    logs = response.json()['logs']
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'protocol', 'device_id', 'rssi', 
                      'latitude', 'longitude', 'altitude']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for log in logs:
            writer.writerow({
                'timestamp': log['timestamp'],
                'protocol': log['protocol'],
                'device_id': log['device_id'],
                'rssi': log['rssi'],
                'latitude': log['latitude'],
                'longitude': log['longitude'],
                'altitude': log['altitude']
            })
    
    print(f"Exported {len(logs)} logs to {output_file}")

export_to_csv('sensors.csv', protocol='Acurite-Tower')
```

### 3. Device Tracker

**Track specific device movements:**

```python
import requests
from datetime import datetime

def track_device(device_id, hours=24):
    """Track a device's location over time"""
    
    response = requests.get(
        'http://localhost:5000/api/logs',
        params={
            'device_id': device_id,
            'hours': hours,
            'limit': 1000
        }
    )
    
    logs = response.json()['logs']
    locations = []
    
    for log in logs:
        if log['latitude'] and log['longitude']:
            locations.append({
                'timestamp': log['timestamp'],
                'lat': log['latitude'],
                'lon': log['longitude'],
                'rssi': log['rssi']
            })
    
    return locations

# Get device path
device_path = track_device('12345', hours=24)

print(f"Device 12345 was detected at {len(device_path)} locations:")
for loc in device_path:
    print(f"  {loc['timestamp']}: ({loc['lat']:.6f}, {loc['lon']:.6f}) RSSI:{loc['rssi']}")
```

### 4. RSSI Heatmap Data Generator

**Generate data for external heatmap tools:**

```python
import requests
import json

def generate_heatmap_data(protocol=None):
    """Generate heatmap data in GeoJSON format"""
    
    params = {'limit': 5000}
    if protocol:
        params['protocol'] = protocol
    
    response = requests.get('http://localhost:5000/api/logs/location', params=params)
    logs = response.json()['logs']
    
    features = []
    for log in logs:
        if log['latitude'] and log['longitude']:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [log['longitude'], log['latitude']]
                },
                'properties': {
                    'rssi': log['rssi'],
                    'protocol': log['protocol'],
                    'device_id': log['device_id'],
                    'timestamp': log['timestamp']
                }
            })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    with open('heatmap.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"Generated GeoJSON with {len(features)} points")

generate_heatmap_data()
```

### 5. Alert System

**Notify when device is detected:**

```python
import requests
import time
from datetime import datetime, timedelta

def check_for_device(device_id, check_interval=60):
    """Alert when specific device is detected"""
    
    last_seen = None
    
    while True:
        response = requests.get(
            'http://localhost:5000/api/logs',
            params={
                'device_id': device_id,
                'hours': 1,
                'limit': 1
            }
        )
        
        logs = response.json()['logs']
        
        if logs:
            latest = logs[0]
            timestamp = datetime.fromisoformat(latest['timestamp'])
            
            if last_seen is None or timestamp > last_seen:
                print(f"⚠️  Device {device_id} detected!")
                print(f"   Time: {latest['timestamp']}")
                print(f"   Protocol: {latest['protocol']}")
                print(f"   RSSI: {latest['rssi']} dBm")
                
                if latest['latitude']:
                    print(f"   Location: {latest['latitude']:.6f}, {latest['longitude']:.6f}")
                
                last_seen = timestamp
        
        time.sleep(check_interval)

# Monitor for specific device
check_for_device('12345', check_interval=30)
```

### 6. Statistics Report

**Generate summary report:**

```python
import requests
from collections import defaultdict

def generate_report():
    """Generate comprehensive statistics report"""
    
    # Get all data
    stats = requests.get('http://localhost:5000/api/statistics').json()
    logs = requests.get('http://localhost:5000/api/logs?limit=10000').json()['logs']
    
    # Calculate statistics
    rssi_by_protocol = defaultdict(list)
    devices_by_protocol = defaultdict(set)
    
    for log in logs:
        proto = log['protocol']
        if log['rssi']:
            rssi_by_protocol[proto].append(log['rssi'])
        if log['device_id']:
            devices_by_protocol[proto].add(log['device_id'])
    
    print("="*60)
    print("RTL433 Geo-Logger Statistics Report")
    print("="*60)
    print(f"\nOverall Statistics:")
    print(f"  Total logs: {stats['total_logs']}")
    print(f"  Logs with GPS: {stats['logs_with_gps']}")
    print(f"  Unique protocols: {stats['unique_protocols']}")
    print(f"  Unique devices: {stats['unique_devices']}")
    
    print(f"\nBy Protocol:")
    for proto in sorted(rssi_by_protocol.keys()):
        rssi_values = rssi_by_protocol[proto]
        avg_rssi = sum(rssi_values) / len(rssi_values)
        device_count = len(devices_by_protocol[proto])
        
        print(f"  {proto}:")
        print(f"    Samples: {len(rssi_values)}")
        print(f"    Devices: {device_count}")
        print(f"    Avg RSSI: {avg_rssi:.1f} dBm")

generate_report()
```

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider:
- Adding rate limiting middleware
- Implementing API keys
- Using caching for frequently accessed data

## CORS

CORS is enabled by default for all origins. For production:
- Restrict origins to specific domains
- Configure CORS in `web.py` create_app() function

## Error Handling

All endpoints return JSON error messages:

```json
{
  "error": "Error message description"
}
```

HTTP status codes:
- 200: Success
- 400: Bad request
- 404: Not found
- 500: Internal server error
