"""
Logger module for RTL433 Geo-Logger
Reads RTL433 JSON output with GPS data from rtl_433 native GPSd support
"""
import sys
import json
import argparse
from datetime import datetime
from typing import Optional, Dict, Any

from .database import Database


class RTL433Logger:
    """Main logger class for RTL433 data with GPS support via rtl_433 native GPSd integration"""
    
    def __init__(self, db_path: str = "rtl433_data.db", verbose: bool = True):
        """
        Initialize RTL433 logger
        
        Args:
            db_path: Path to SQLite database
            verbose: Enable verbose output with data recap for each entry
        """
        self.db = Database(db_path)
        self.verbose = verbose
    
    def process_rtl433_line(self, line: str) -> bool:
        """
        Process a single line of RTL433 JSON output
        Handles all RTL433 protocols including custom protocols
        Extracts GPS data from rtl_433 native GPSd support (lat, lon, alt fields)
        
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
            
            # Extract GPS data from rtl_433 JSON (native GPSd support)
            # rtl_433 includes lat, lon, alt fields when configured with GPSd
            gps_data = None
            if 'lat' in data and 'lon' in data:
                try:
                    # Convert to float to handle string values from rtl_433
                    lat = float(data.get('lat'))
                    lon = float(data.get('lon'))
                    alt = float(data.get('alt')) if data.get('alt') is not None else None
                    
                    gps_data = {
                        'lat': lat,
                        'lon': lon,
                        'altitude': alt,
                    }
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid GPS data format: {e}", file=sys.stderr)
                    gps_data = None
            
            # Insert into database (handles all protocol types)
            log_id = self.db.insert_log(timestamp, data, gps_data)
            
            # Print summary if verbose mode is enabled
            if self.verbose:
                protocol = data.get('model') or data.get('protocol') or data.get('type') or 'Unknown'
                device_id = self.db._extract_device_id(data)
                rssi = data.get('rssi') or data.get('RSSI') or data.get('snr') or 'N/A'
                
                summary = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {protocol}"
                if device_id:
                    summary += f" ID:{device_id}"
                summary += f" RSSI:{rssi}"
                
                if gps_data:
                    summary += f" GPS:{gps_data['lat']:.6f},{gps_data['lon']:.6f}"
                    if gps_data.get('altitude') is not None:
                        summary += f" Alt:{gps_data['altitude']:.1f}m"
                
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
        
        if self.verbose:
            print("RTL433 Geo-Logger started. Reading from input...")
            print("Expecting rtl_433 JSON output with optional GPS data (lat, lon, alt)")
            print("Configure rtl_433 with: output_tag gpsd,lat,lon,alt")
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
        description="RTL433 Geo-Logger - Log RTL433 data with GPS location (via rtl_433 native GPSd support)"
    )
    parser.add_argument(
        '--db',
        default='rtl433_data.db',
        help='Path to SQLite database file (default: rtl433_data.db)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Disable verbose output (only show errors)'
    )
    
    args = parser.parse_args()
    
    # Verbose is True by default, unless --quiet is specified
    verbose = not args.quiet
    
    logger = RTL433Logger(db_path=args.db, verbose=verbose)
    
    logger.run()


if __name__ == '__main__':
    main()
