"""
Logger module for RTL433 Geo-Logger
Reads RTL433 JSON output and GPS data, stores in database
"""
import sys
import json
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import time

try:
    import gpsd
    GPSD_AVAILABLE = True
except ImportError:
    GPSD_AVAILABLE = False
    print("Warning: gpsd-py3 not installed. GPS features will be disabled.", file=sys.stderr)

from .database import Database


class GPSReader:
    """GPS data reader using GPSD"""
    
    def __init__(self, host: str = "localhost", port: int = 2947):
        """
        Initialize GPS reader
        
        Args:
            host: GPSD host
            port: GPSD port
        """
        self.host = host
        self.port = port
        self.connected = False
        
        if GPSD_AVAILABLE:
            try:
                gpsd.connect(host=host, port=port)
                self.connected = True
                print(f"Connected to GPSD at {host}:{port}")
            except Exception as e:
                print(f"Failed to connect to GPSD: {e}", file=sys.stderr)
                self.connected = False
        else:
            print("GPSD library not available", file=sys.stderr)
    
    def get_current_position(self) -> Optional[Dict[str, Any]]:
        """
        Get current GPS position
        
        Returns:
            Dictionary with GPS data or None if not available
        """
        if not self.connected or not GPSD_AVAILABLE:
            return None
        
        try:
            packet = gpsd.get_current()
            
            if packet.mode < 2:  # No fix
                return None
            
            gps_data = {
                'timestamp': datetime.utcnow(),
                'lat': packet.lat,
                'lon': packet.lon,
                'altitude': packet.alt if packet.mode >= 3 else None,
                'speed': packet.speed(),
                'track': packet.track(),
                'mode': packet.mode
            }
            
            return gps_data
        except Exception as e:
            print(f"Error reading GPS: {e}", file=sys.stderr)
            return None


class RTL433Logger:
    """Main logger class for RTL433 data with GPS"""
    
    def __init__(
        self,
        db_path: str = "rtl433_data.db",
        enable_gps: bool = True,
        gps_host: str = "localhost",
        gps_port: int = 2947
    ):
        """
        Initialize RTL433 logger
        
        Args:
            db_path: Path to SQLite database
            enable_gps: Whether to enable GPS logging
            gps_host: GPSD host
            gps_port: GPSD port
        """
        self.db = Database(db_path)
        self.gps_reader = None
        
        if enable_gps:
            self.gps_reader = GPSReader(host=gps_host, port=gps_port)
            if not self.gps_reader.connected:
                print("GPS not available, continuing without GPS data")
                self.gps_reader = None
    
    def process_rtl433_line(self, line: str) -> bool:
        """
        Process a single line of RTL433 JSON output
        Handles all RTL433 protocols including custom protocols
        
        Args:
            line: JSON string from RTL433
            
        Returns:
            True if successfully processed, False otherwise
        """
        try:
            # Skip empty lines
            line = line.strip()
            if not line:
                return True
            
            # Parse RTL433 JSON
            data = json.loads(line)
            
            # Validate that we have a dictionary
            if not isinstance(data, dict):
                print(f"Warning: Unexpected data type: {type(data)}", file=sys.stderr)
                return False
            
            # Get timestamp from data or use current time
            timestamp_str = data.get('time')
            if timestamp_str:
                try:
                    # Try parsing ISO format (common RTL433 format)
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    try:
                        # Try other common formats
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        # Fallback to current time
                        timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()
            
            # Get GPS data if available
            gps_data = None
            if self.gps_reader:
                gps_data = self.gps_reader.get_current_position()
            
            # Insert into database (handles all protocol types)
            log_id = self.db.insert_log(timestamp, data, gps_data)
            
            # Print summary - use robust field extraction
            protocol = data.get('model') or data.get('protocol') or data.get('type') or 'Unknown'
            device_id = self.db._extract_device_id(data)
            rssi = data.get('rssi') or data.get('RSSI') or data.get('snr') or 'N/A'
            
            summary = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {protocol}"
            if device_id:
                summary += f" ID:{device_id}"
            summary += f" RSSI:{rssi}"
            
            summary = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {protocol}"
            if device_id:
                summary += f" ID:{device_id}"
            summary += f" RSSI:{rssi}"
            
            if gps_data:
                summary += f" GPS:{gps_data['lat']:.6f},{gps_data['lon']:.6f}"
            
            print(summary)
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error processing line: {e}", file=sys.stderr)
            return False
    
    def run(self, input_source=None):
        """
        Run the logger, reading from stdin or provided source
        
        Args:
            input_source: Input source (default: stdin)
        """
        if input_source is None:
            input_source = sys.stdin
        
        print("RTL433 Geo-Logger started. Reading from input...")
        print(f"GPS: {'enabled' if self.gps_reader else 'disabled'}")
        print("=" * 60)
        
        try:
            for line in input_source:
                line = line.strip()
                if line:
                    self.process_rtl433_line(line)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.db.close()


def main():
    """Main entry point for the logger"""
    parser = argparse.ArgumentParser(
        description="RTL433 Geo-Logger - Log RTL433 data with GPS location"
    )
    parser.add_argument(
        '--db',
        default='rtl433_data.db',
        help='Path to SQLite database file (default: rtl433_data.db)'
    )
    parser.add_argument(
        '--no-gps',
        action='store_true',
        help='Disable GPS logging'
    )
    parser.add_argument(
        '--gps-host',
        default='localhost',
        help='GPSD host (default: localhost)'
    )
    parser.add_argument(
        '--gps-port',
        type=int,
        default=2947,
        help='GPSD port (default: 2947)'
    )
    
    args = parser.parse_args()
    
    logger = RTL433Logger(
        db_path=args.db,
        enable_gps=not args.no_gps,
        gps_host=args.gps_host,
        gps_port=args.gps_port
    )
    
    logger.run()


if __name__ == '__main__':
    main()
