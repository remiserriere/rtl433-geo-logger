"""
Web service module for RTL433 Geo-Logger
Provides REST API and web interface with map visualization
"""
import argparse
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Optional

from .database import Database


def create_app(db_path: str = "rtl433_data.db"):
    """
    Create Flask application
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Flask application
    """
    app = Flask(__name__)
    CORS(app)
    
    db = Database(db_path)
    
    # HTML template for the map interface
    MAP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>RTL433 Geo-Logger Map</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.css" />
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        .info-panel {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            max-width: 300px;
        }
        .info-panel h3 { margin-top: 0; }
        .stats { font-size: 14px; }
        .stats div { margin: 5px 0; }
        .controls {
            position: absolute;
            top: 10px;
            left: 60px;
            z-index: 1000;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
        }
        .controls label { margin-right: 10px; }
        .filter-section {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
        }
        .filter-section label {
            display: block;
            margin: 5px 0;
            font-weight: bold;
        }
        .filter-section select {
            width: 200px;
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
            margin-bottom: 5px;
        }
        button { 
            padding: 5px 10px; 
            margin: 5px 5px 5px 0;
            cursor: pointer;
            border: 1px solid #ccc;
            background: white;
            border-radius: 3px;
        }
        button:hover { background: #f0f0f0; }
        button.active { background: #007bff; color: white; }
    </style>
</head>
<body>
    <div class="controls">
        <button id="refreshBtn" onclick="loadData()">Refresh</button>
        <button id="heatmapBtn" onclick="toggleHeatmap()">Toggle Heatmap</button>
        <label>
            <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
            Auto-refresh (10s)
        </label>
        <div class="filter-section">
            <label>Filter by Protocol:</label>
            <select id="protocolFilter" onchange="applyFilters()">
                <option value="">All Protocols</option>
            </select>
            <label>Filter by Device ID:</label>
            <select id="deviceFilter" onchange="applyFilters()">
                <option value="">All Devices</option>
            </select>
            <button onclick="clearFilters()">Clear Filters</button>
        </div>
    </div>
    
    <div class="info-panel">
        <h3>RTL433 Geo-Logger</h3>
        <div class="stats" id="stats">
            <div>Loading...</div>
        </div>
    </div>
    
    <div id="map"></div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <script>
        // Initialize map
        var map = L.map('map').setView([48.8566, 2.3522], 13);  // Default: Paris
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        var markers = [];
        var heatmapLayer = null;
        var showHeatmap = false;
        var autoRefreshInterval = null;
        var allLogs = [];  // Store all logs for filtering
        var availableProtocols = new Set();
        var availableDevices = new Set();
        
        function clearMarkers() {
            markers.forEach(marker => map.removeLayer(marker));
            markers = [];
            if (heatmapLayer) {
                map.removeLayer(heatmapLayer);
                heatmapLayer = null;
            }
        }
        
        function updateFilterDropdowns() {
            // Update protocol filter
            var protocolFilter = document.getElementById('protocolFilter');
            var currentProtocol = protocolFilter.value;
            protocolFilter.innerHTML = '<option value="">All Protocols</option>';
            Array.from(availableProtocols).sort().forEach(protocol => {
                var option = document.createElement('option');
                option.value = protocol;
                option.textContent = protocol;
                if (protocol === currentProtocol) {
                    option.selected = true;
                }
                protocolFilter.appendChild(option);
            });
            
            // Update device filter
            var deviceFilter = document.getElementById('deviceFilter');
            var currentDevice = deviceFilter.value;
            deviceFilter.innerHTML = '<option value="">All Devices</option>';
            Array.from(availableDevices).sort().forEach(device => {
                var option = document.createElement('option');
                option.value = device;
                option.textContent = device;
                if (device === currentDevice) {
                    option.selected = true;
                }
                deviceFilter.appendChild(option);
            });
        }
        
        function getFilteredLogs() {
            var protocolFilter = document.getElementById('protocolFilter').value;
            var deviceFilter = document.getElementById('deviceFilter').value;
            
            return allLogs.filter(log => {
                if (protocolFilter && log.protocol !== protocolFilter) {
                    return false;
                }
                if (deviceFilter && log.device_id !== deviceFilter) {
                    return false;
                }
                return true;
            });
        }
        
        function applyFilters() {
            displayLogs(getFilteredLogs());
        }
        
        function clearFilters() {
            document.getElementById('protocolFilter').value = '';
            document.getElementById('deviceFilter').value = '';
            applyFilters();
        }
        
        function displayLogs(logs) {
            clearMarkers();
            
            if (logs.length === 0) {
                var message = allLogs.length === 0 ? 
                    'No data with GPS location found' : 
                    'No data matches the current filters';
                document.getElementById('stats').innerHTML = '<div>' + message + '</div>';
                return;
            }
            
            // Prepare heatmap data
            var heatData = [];
            
            // Add markers and collect heatmap data
            logs.forEach(log => {
                var lat = log.latitude;
                var lon = log.longitude;
                
                // Create marker
                var marker = L.marker([lat, lon]);
                
                // Create popup content
                var popupContent = '<b>' + (log.protocol || 'Unknown') + '</b><br>';
                if (log.device_id) {
                    popupContent += 'Device ID: ' + log.device_id + '<br>';
                }
                if (log.rssi !== null) {
                    popupContent += 'RSSI: ' + log.rssi + ' dBm<br>';
                }
                popupContent += 'Time: ' + log.timestamp + '<br>';
                if (log.altitude !== null) {
                    popupContent += 'Altitude: ' + log.altitude.toFixed(1) + ' m<br>';
                }
                
                marker.bindPopup(popupContent);
                
                if (!showHeatmap) {
                    marker.addTo(map);
                }
                markers.push(marker);
                
                // Add to heatmap data (intensity based on RSSI)
                var intensity = 0.5;
                if (log.rssi !== null) {
                    // Normalize RSSI (-100 to 0) to intensity (0 to 1)
                    intensity = Math.max(0, Math.min(1, (log.rssi + 100) / 100));
                }
                heatData.push([lat, lon, intensity]);
            });
            
            // Create heatmap layer
            if (heatData.length > 0) {
                heatmapLayer = L.heatLayer(heatData, {
                    radius: 25,
                    blur: 15,
                    maxZoom: 17,
                    max: 1.0,
                    gradient: {
                        0.0: 'blue',
                        0.5: 'lime',
                        0.7: 'yellow',
                        1.0: 'red'
                    }
                });
                
                if (showHeatmap) {
                    heatmapLayer.addTo(map);
                }
            }
            
            // Auto-zoom to show all markers
            if (markers.length > 0) {
                var group = new L.featureGroup(markers);
                map.fitBounds(group.getBounds().pad(0.1));
            }
            
            // Update stats display
            updateStats(logs.length);
        }
        
        function loadData() {
            fetch('/api/logs/location')
                .then(response => response.json())
                .then(data => {
                    allLogs = data.logs;
                    
                    // Collect available protocols and devices
                    availableProtocols.clear();
                    availableDevices.clear();
                    
                    allLogs.forEach(log => {
                        if (log.protocol) {
                            availableProtocols.add(log.protocol);
                        }
                        if (log.device_id) {
                            availableDevices.add(log.device_id);
                        }
                    });
                    
                    // Update filter dropdowns
                    updateFilterDropdowns();
                    
                    // Display filtered logs
                    applyFilters();
                });
            
            // Load statistics
            fetch('/api/statistics')
                .then(response => response.json())
                .then(stats => {
                    updateStatsPanel(stats);
                });
        }
        
        function updateStats(displayedCount) {
            fetch('/api/statistics')
                .then(response => response.json())
                .then(stats => {
                    updateStatsPanel(stats, displayedCount);
                });
        }
        
        function updateStatsPanel(stats, displayedCount) {
            var html = '<div><strong>Total logs:</strong> ' + stats.total_logs + '</div>';
            html += '<div><strong>With GPS:</strong> ' + stats.logs_with_gps + '</div>';
            if (displayedCount !== undefined && displayedCount < stats.logs_with_gps) {
                html += '<div><strong>Displayed:</strong> ' + displayedCount + ' (filtered)</div>';
            }
            html += '<div><strong>Protocols:</strong> ' + stats.unique_protocols + '</div>';
            html += '<div><strong>Devices:</strong> ' + stats.unique_devices + '</div>';
            if (stats.latest_log) {
                html += '<div><strong>Latest:</strong> ' + stats.latest_log + '</div>';
            }
            document.getElementById('stats').innerHTML = html;
        }
        
        function toggleHeatmap() {
            showHeatmap = !showHeatmap;
            
            if (showHeatmap) {
                // Hide markers, show heatmap
                markers.forEach(marker => map.removeLayer(marker));
                if (heatmapLayer) {
                    heatmapLayer.addTo(map);
                }
                document.getElementById('heatmapBtn').classList.add('active');
            } else {
                // Show markers, hide heatmap
                if (heatmapLayer) {
                    map.removeLayer(heatmapLayer);
                }
                markers.forEach(marker => marker.addTo(map));
                document.getElementById('heatmapBtn').classList.remove('active');
            }
        }
        
        function toggleAutoRefresh() {
            var checkbox = document.getElementById('autoRefresh');
            if (checkbox.checked) {
                autoRefreshInterval = setInterval(loadData, 10000);
            } else {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
            }
        }
        
        // Initial load
        loadData();
    </script>
</body>
</html>
    """
    
    @app.route('/')
    def index():
        """Main map interface"""
        return render_template_string(MAP_TEMPLATE)
    
    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        """
        Get logs with optional filters
        Query parameters:
        - limit: Maximum number of records (default: 100)
        - offset: Offset for pagination (default: 0)
        - device_id: Filter by device ID
        - protocol: Filter by protocol
        - hours: Get logs from last N hours
        """
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        device_id = request.args.get('device_id')
        protocol = request.args.get('protocol')
        
        # Time filter
        start_time = None
        hours = request.args.get('hours')
        if hours:
            start_time = datetime.utcnow() - timedelta(hours=int(hours))
        
        logs = db.get_logs(
            limit=limit,
            offset=offset,
            device_id=device_id,
            protocol=protocol,
            start_time=start_time
        )
        
        return jsonify({
            'logs': logs,
            'count': len(logs)
        })
    
    @app.route('/api/logs/location', methods=['GET'])
    def get_logs_with_location():
        """
        Get logs that have GPS location data
        Query parameters:
        - limit: Maximum number of records (default: 1000)
        - hours: Get logs from last N hours
        """
        limit = int(request.args.get('limit', 1000))
        
        # Time filter
        start_time = None
        hours = request.args.get('hours')
        if hours:
            start_time = datetime.utcnow() - timedelta(hours=int(hours))
        
        logs = db.get_logs_with_location(
            limit=limit,
            start_time=start_time
        )
        
        return jsonify({
            'logs': logs,
            'count': len(logs)
        })
    
    @app.route('/api/statistics', methods=['GET'])
    def get_statistics():
        """Get database statistics"""
        stats = db.get_statistics()
        return jsonify(stats)
    
    return app


def main():
    """Main entry point for the web service"""
    parser = argparse.ArgumentParser(
        description="RTL433 Geo-Logger Web Service - View RTL433 data on a map"
    )
    parser.add_argument(
        '--db',
        default='rtl433_data.db',
        help='Path to SQLite database file (default: rtl433_data.db)'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    app = create_app(db_path=args.db)
    
    print(f"Starting RTL433 Geo-Logger web service on http://{args.host}:{args.port}")
    print(f"Database: {args.db}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
