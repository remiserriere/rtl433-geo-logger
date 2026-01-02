"""
Database module for RTL433 Geo-Logger
Handles SQLite database operations for storing RTL433 data with GPS information
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import os


class Database:
    """SQLite database handler for RTL433 geo-logger"""
    
    def __init__(self, db_path: str = "rtl433_data.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Create main table for RTL433 data with GPS information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rtl433_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                gps_timestamp DATETIME,
                latitude REAL,
                longitude REAL,
                altitude REAL,
                protocol TEXT,
                device_id TEXT,
                rssi INTEGER,
                data_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON rtl433_logs(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_id 
            ON rtl433_logs(device_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_protocol 
            ON rtl433_logs(protocol)
        """)
        
        self.conn.commit()
    
    def insert_log(
        self,
        timestamp: datetime,
        data: Dict[str, Any],
        gps_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Insert a new RTL433 log entry
        
        Args:
            timestamp: Timestamp of the reading
            data: RTL433 data dictionary
            gps_data: GPS data dictionary extracted from rtl_433 JSON (optional)
                     Expected keys: 'lat', 'lon', 'altitude' (all optional)
            
        Returns:
            ID of inserted row
        """
        cursor = self.conn.cursor()
        
        # Extract common fields from RTL433 data
        # Support various protocol/model naming conventions including custom protocols
        protocol = data.get("model") or data.get("protocol") or data.get("type") or "Unknown"
        device_id = self._extract_device_id(data)
        # RSSI can be in different cases or missing for some protocols
        rssi = data.get("rssi") or data.get("RSSI") or data.get("snr")
        
        # Extract GPS data if available (from rtl_433 native GPSd support)
        latitude = None
        longitude = None
        altitude = None
        
        if gps_data:
            latitude = gps_data.get("lat")
            longitude = gps_data.get("lon")
            altitude = gps_data.get("altitude")
        
        # Store complete data as JSON
        data_json = json.dumps(data)
        
        cursor.execute("""
            INSERT INTO rtl433_logs 
            (timestamp, gps_timestamp, latitude, longitude, altitude, 
             protocol, device_id, rssi, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp.isoformat(),
            timestamp.isoformat() if (latitude and longitude) else None,  # Use rtl_433 timestamp for GPS
            latitude,
            longitude,
            altitude,
            protocol,
            device_id,
            rssi,
            data_json
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def _extract_device_id(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract device ID from RTL433 data
        Different devices use different field names for ID
        Handles standard protocols and custom protocols
        
        Args:
            data: RTL433 data dictionary
            
        Returns:
            Device ID as string or None
        """
        # Common device ID field names used by various RTL433 protocols
        # Including custom protocol possibilities
        id_fields = [
            "id", "device_id", "device", "sensor_id", "address", 
            "code", "transmitter_id", "node_id", "unit", "channel",
            "house_code", "rolling_code", "serial"
        ]
        
        for field in id_fields:
            if field in data and data[field] is not None:
                # Convert to string and handle various types
                value = data[field]
                if isinstance(value, (int, float, str)):
                    return str(value)
        
        return None
    
    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        device_id: Optional[str] = None,
        protocol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Query RTL433 logs with filters
        
        Args:
            limit: Maximum number of records to return
            offset: Offset for pagination
            device_id: Filter by device ID
            protocol: Filter by protocol
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of log dictionaries
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM rtl433_logs WHERE 1=1"
        params = []
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if protocol:
            query += " AND protocol = ?"
            params.append(protocol)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        results = []
        for row in rows:
            log_dict = dict(row)
            # Parse JSON data
            log_dict['data'] = json.loads(log_dict['data_json'])
            results.append(log_dict)
        
        return results
    
    def get_logs_with_location(
        self,
        limit: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get logs that have GPS location data for mapping
        
        Args:
            limit: Maximum number of records to return
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of log dictionaries with location data
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM rtl433_logs 
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL
        """
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            log_dict = dict(row)
            log_dict['data'] = json.loads(log_dict['data_json'])
            results.append(log_dict)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()
        
        # Total logs
        cursor.execute("SELECT COUNT(*) as count FROM rtl433_logs")
        total_logs = cursor.fetchone()['count']
        
        # Logs with GPS
        cursor.execute("""
            SELECT COUNT(*) as count FROM rtl433_logs 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        logs_with_gps = cursor.fetchone()['count']
        
        # Unique protocols
        cursor.execute("SELECT COUNT(DISTINCT protocol) as count FROM rtl433_logs")
        unique_protocols = cursor.fetchone()['count']
        
        # Unique devices
        cursor.execute("""
            SELECT COUNT(DISTINCT device_id) as count FROM rtl433_logs 
            WHERE device_id IS NOT NULL
        """)
        unique_devices = cursor.fetchone()['count']
        
        # Date range
        cursor.execute("""
            SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time 
            FROM rtl433_logs
        """)
        date_range = cursor.fetchone()
        
        return {
            'total_logs': total_logs,
            'logs_with_gps': logs_with_gps,
            'unique_protocols': unique_protocols,
            'unique_devices': unique_devices,
            'earliest_log': date_range['min_time'],
            'latest_log': date_range['max_time']
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
