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
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #map { position: absolute; top: 0; bottom: 0; left: 0; right: 350px; }
        .info-panel {
            position: absolute;
            top: 10px;
            right: 360px;
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
        
        /* Data panel styles */
        .data-panel {
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            width: 350px;
            background: white;
            box-shadow: -2px 0 15px rgba(0,0,0,0.2);
            overflow-y: auto;
            z-index: 900;
            padding: 15px;
        }
        .data-panel h3 {
            margin-top: 0;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .data-item {
            margin: 10px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .data-item:hover {
            background: #e9ecef;
        }
        .data-item.selected {
            background: #cfe2ff;
            border-left: 3px solid #007bff;
        }
        .data-item-header {
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
        }
        .data-item-time {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 5px;
        }
        .data-item-content {
            font-size: 13px;
            display: none;
        }
        .data-item.expanded .data-item-content {
            display: block;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #dee2e6;
        }
        .data-field {
            margin: 3px 0;
            display: flex;
            justify-content: space-between;
        }
        .data-field-name {
            font-weight: 500;
            color: #495057;
        }
        .data-field-value {
            color: #212529;
            font-family: 'Courier New', monospace;
        }
        .no-data-message {
            text-align: center;
            color: #6c757d;
            padding: 20px;
        }
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
    
    <div class="data-panel">
        <h3>Data Details</h3>
        <div id="dataList">
            <div class="no-data-message">Loading data...</div>
        </div>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <script>
        // Initialize map
        var map = L.map('map').setView([48.8566, 2.3522], 13);  // Default: Paris
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        var markerClusterGroup = null;
        var heatmapLayer = null;
        var showHeatmap = false;
        var autoRefreshInterval = null;
        var allLogs = [];  // Store all logs for filtering
        var availableProtocols = new Set();
        var protocolDeviceMap = {};  // Map of protocol -> Set of devices
        var selectedLogId = null;
        
        function clearMarkers() {
            if (markerClusterGroup) {
                map.removeLayer(markerClusterGroup);
                markerClusterGroup = null;
            }
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
            
            // Update device filter based on selected protocol
            updateDeviceFilter();
        }
        
        function updateDeviceFilter() {
            var protocolFilter = document.getElementById('protocolFilter');
            var deviceFilter = document.getElementById('deviceFilter');
            var currentDevice = deviceFilter.value;
            var selectedProtocol = protocolFilter.value;
            
            deviceFilter.innerHTML = '<option value="">All Devices</option>';
            
            // Get devices for the selected protocol or all devices if no protocol selected
            var devicesToShow = new Set();
            if (selectedProtocol) {
                // Only show devices from the selected protocol
                if (protocolDeviceMap[selectedProtocol]) {
                    devicesToShow = protocolDeviceMap[selectedProtocol];
                }
            } else {
                // Show all devices from all protocols
                Object.values(protocolDeviceMap).forEach(deviceSet => {
                    deviceSet.forEach(device => devicesToShow.add(device));
                });
            }
            
            Array.from(devicesToShow).sort().forEach(device => {
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
            // Update device filter dropdown when protocol changes
            updateDeviceFilter();
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
                updateDataPanel([]);
                return;
            }
            
            // Create marker cluster group
            markerClusterGroup = L.markerClusterGroup({
                chunkedLoading: true,
                spiderfyOnMaxZoom: true,
                showCoverageOnHover: false,
                zoomToBoundsOnClick: true
            });
            
            // Prepare heatmap data
            var heatData = [];
            
            // Add markers and collect heatmap data
            logs.forEach(log => {
                var lat = log.latitude;
                var lon = log.longitude;
                
                // Create marker
                var marker = L.marker([lat, lon]);
                
                // Store log data in marker for later use
                marker.logData = log;
                
                // Create popup content
                var popupContent = '<b>' + (log.protocol || 'Unknown') + '</b><br>';
                if (log.device_id) {
                    popupContent += 'Device ID: ' + log.device_id + '<br>';
                }
                if (log.rssi != null) {
                    popupContent += 'RSSI: ' + log.rssi + ' dBm<br>';
                }
                popupContent += 'Time: ' + log.timestamp + '<br>';
                if (log.altitude != null) {
                    popupContent += 'Altitude: ' + log.altitude.toFixed(1) + ' m<br>';
                }
                
                marker.bindPopup(popupContent);
                
                // Add click event to highlight in data panel
                marker.on('click', function() {
                    highlightDataItem(log.id);
                });
                
                markerClusterGroup.addLayer(marker);
                
                // Add to heatmap data (intensity based on RSSI)
                var intensity = 0.5;
                if (log.rssi != null) {
                    // Normalize RSSI (-100 to 0) to intensity (0 to 1)
                    intensity = Math.max(0, Math.min(1, (log.rssi + 100) / 100));
                }
                heatData.push([lat, lon, intensity]);
            });
            
            // Add marker cluster to map if not showing heatmap
            if (!showHeatmap) {
                map.addLayer(markerClusterGroup);
            }
            
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
            if (markerClusterGroup && markerClusterGroup.getLayers().length > 0) {
                map.fitBounds(markerClusterGroup.getBounds().pad(0.1));
            }
            
            // Update data panel with filtered logs
            updateDataPanel(logs);
            
            // Update stats display
            updateStats(logs.length);
        }
        
        function updateDataPanel(logs) {
            var dataList = document.getElementById('dataList');
            
            if (logs.length === 0) {
                dataList.innerHTML = '<div class="no-data-message">No data to display</div>';
                return;
            }
            
            // Sort logs by timestamp (most recent first)
            var sortedLogs = logs.slice().sort((a, b) => {
                return new Date(b.timestamp) - new Date(a.timestamp);
            });
            
            var html = '';
            sortedLogs.forEach(log => {
                var dataObj = log.data || {};
                var itemClass = 'data-item';
                if (selectedLogId === log.id) {
                    itemClass += ' expanded';
                }
                
                html += '<div class="' + itemClass + '" id="data-item-' + log.id + '" onclick="toggleDataItem(' + log.id + ')">';
                html += '<div class="data-item-header">' + (log.protocol || 'Unknown');
                if (log.device_id) {
                    html += ' - ID: ' + log.device_id;
                }
                html += '</div>';
                html += '<div class="data-item-time">' + log.timestamp + '</div>';
                html += '<div class="data-item-content">';
                
                // Display all data fields
                var displayedFields = new Set(['timestamp', 'model', 'protocol', 'type']);
                
                // Display key fields first
                if (log.rssi != null) {
                    html += '<div class="data-field"><span class="data-field-name">RSSI:</span><span class="data-field-value">' + log.rssi + ' dBm</span></div>';
                }
                if (log.latitude != null) {
                    html += '<div class="data-field"><span class="data-field-name">Latitude:</span><span class="data-field-value">' + log.latitude.toFixed(6) + '</span></div>';
                }
                if (log.longitude != null) {
                    html += '<div class="data-field"><span class="data-field-name">Longitude:</span><span class="data-field-value">' + log.longitude.toFixed(6) + '</span></div>';
                }
                if (log.altitude != null) {
                    html += '<div class="data-field"><span class="data-field-name">Altitude:</span><span class="data-field-value">' + log.altitude.toFixed(1) + ' m</span></div>';
                }
                
                // Display all other fields from JSON data
                Object.keys(dataObj).sort().forEach(key => {
                    if (!displayedFields.has(key) && key !== 'lat' && key !== 'lon' && key !== 'alt') {
                        var value = dataObj[key];
                        if (typeof value === 'object') {
                            value = JSON.stringify(value);
                        }
                        html += '<div class="data-field"><span class="data-field-name">' + key + ':</span><span class="data-field-value">' + value + '</span></div>';
                    }
                });
                
                html += '</div></div>';
            });
            
            dataList.innerHTML = html;
        }
        
        function toggleDataItem(logId) {
            var item = document.getElementById('data-item-' + logId);
            if (item.classList.contains('expanded')) {
                item.classList.remove('expanded');
                selectedLogId = null;
            } else {
                // Remove expanded class from all items
                document.querySelectorAll('.data-item').forEach(el => {
                    el.classList.remove('expanded');
                });
                item.classList.add('expanded');
                selectedLogId = logId;
            }
        }
        
        function highlightDataItem(logId) {
            selectedLogId = logId;
            var item = document.getElementById('data-item-' + logId);
            if (item) {
                // Remove expanded from all
                document.querySelectorAll('.data-item').forEach(el => {
                    el.classList.remove('expanded');
                });
                // Expand this one
                item.classList.add('expanded');
                // Scroll to item
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        function loadData() {
            fetch('/api/logs/location')
                .then(response => response.json())
                .then(data => {
                    allLogs = data.logs;
                    
                    // Collect available protocols and devices
                    availableProtocols.clear();
                    protocolDeviceMap = {};
                    
                    allLogs.forEach(log => {
                        if (log.protocol) {
                            availableProtocols.add(log.protocol);
                            
                            // Build protocol -> device mapping
                            if (!protocolDeviceMap[log.protocol]) {
                                protocolDeviceMap[log.protocol] = new Set();
                            }
                            if (log.device_id) {
                                protocolDeviceMap[log.protocol].add(log.device_id);
                            }
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
                // Hide marker clusters, show heatmap
                if (markerClusterGroup) {
                    map.removeLayer(markerClusterGroup);
                }
                if (heatmapLayer) {
                    heatmapLayer.addTo(map);
                }
                document.getElementById('heatmapBtn').classList.add('active');
            } else {
                // Show marker clusters, hide heatmap
                if (heatmapLayer) {
                    map.removeLayer(heatmapLayer);
                }
                if (markerClusterGroup) {
                    map.addLayer(markerClusterGroup);
                }
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
