# Testing RTL433 Geo-Logger

This guide provides instructions for testing the RTL433 Geo-Logger system.

## Quick Start Test

Test the logger with example data (no RTL433 or GPS hardware required):

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run test with example data
cat examples/test_data.json | python3 -m rtl433_geo_logger.logger --db test.db --no-gps

# 3. Start web interface
python3 -m rtl433_geo_logger.web --db test.db

# 4. Open browser to http://localhost:5000
```

## Testing Without GPS

If you don't have GPS hardware but have RTL433:

```bash
# Capture RTL433 data without GPS
rtl_433 -F json | python3 -m rtl433_geo_logger.logger --no-gps --db rtl433.db
```

The logger will work normally but won't include GPS coordinates in the database.

## Testing With Real RTL433 Hardware

### Prerequisites
- RTL-SDR dongle
- rtl_433 installed
- 433MHz sensors nearby

### Basic Test
```bash
# Test RTL433 reception
rtl_433 -F json

# If you see JSON output, start logging
rtl_433 -F json | python3 -m rtl433_geo_logger.logger --no-gps --db rtl433.db
```

### With GPS
If you have GPSD running:

```bash
# 1. Start GPSD (example with USB GPS)
sudo gpsd -N /dev/ttyUSB0

# 2. Verify GPS is working
cgps  # or gpsmon

# 3. Start logger with GPS
rtl_433 -F json | python3 -m rtl433_geo_logger.logger --db rtl433.db
```

## Testing Custom Protocols

### Flex Decoder Example

Create a custom protocol for a 433MHz device:

```bash
# Example: Capture unknown device
rtl_433 -X 'n=my_sensor,m=OOK_PWM,s=400,l=800,r=8000' -F json | \
  python3 -m rtl433_geo_logger.logger --no-gps --db custom.db
```

The logger will:
- Extract protocol name from `protocol` or `type` field
- Try to find device ID in various fields
- Store complete JSON data

### Verify Custom Protocol Storage

```bash
# Check database
sqlite3 custom.db "SELECT protocol, device_id, data_json FROM rtl433_logs LIMIT 5;"
```

## Web Interface Testing

### Test API Endpoints

```bash
# Start web server
python3 -m rtl433_geo_logger.web --db test.db --port 5000 &

# Test statistics endpoint
curl http://localhost:5000/api/statistics

# Test logs endpoint
curl http://localhost:5000/api/logs?limit=10

# Test location endpoint (requires GPS data)
curl http://localhost:5000/api/logs/location
```

### Test Filtering

1. Open web interface: http://localhost:5000
2. Load data with multiple protocols
3. Use protocol filter dropdown
4. Use device ID filter dropdown
5. Toggle heatmap view
6. Enable auto-refresh

### Expected Behavior

- **Protocol Filter**: Should show only entries matching selected protocol
- **Device ID Filter**: Should show only entries from selected device
- **Clear Filters**: Should reset to show all data
- **Heatmap**: Should color-code by RSSI (blue=weak, red=strong)
- **Markers**: Should show protocol, device ID, RSSI, timestamp
- **Statistics**: Should update to show filtered vs total counts

## Performance Testing

### Large Dataset Test

```bash
# Generate large test dataset
for i in {1..1000}; do
  echo '{"time":"2024-01-15 10:30:00","model":"Test-Sensor","id":'$i',"temp":20.5,"rssi":-45}'
done | python3 -m rtl433_geo_logger.logger --no-gps --db large.db

# Verify
sqlite3 large.db "SELECT COUNT(*) FROM rtl433_logs;"

# Test web interface responsiveness
python3 -m rtl433_geo_logger.web --db large.db
```

### Expected Performance

- **Database inserts**: ~1000-5000 entries/second
- **Web page load**: <2 seconds for 1000 markers
- **Filter application**: <500ms for 10000 entries
- **Heatmap rendering**: <1 second for 1000 points

## GPS Testing

### Static GPS Test

If GPS is not moving:

```bash
# Start logger with GPS
rtl_433 -F json | python3 -m rtl433_geo_logger.logger --db static.db

# All entries should have same GPS coordinates
sqlite3 static.db "SELECT DISTINCT latitude, longitude FROM rtl433_logs WHERE latitude IS NOT NULL;"
```

### Mobile GPS Test

For wardriving/mobile collection:

```bash
# Start logger in vehicle with GPS
rtl_433 -F json | python3 -m rtl433_geo_logger.logger --db mobile.db

# Entries should have different GPS coordinates
sqlite3 mobile.db "SELECT COUNT(DISTINCT latitude || ',' || longitude) as unique_locations FROM rtl433_logs WHERE latitude IS NOT NULL;"
```

### GPS Accuracy Check

```bash
# Check GPS fix quality in logs
python3 << EOF
import sqlite3
conn = sqlite3.connect('mobile.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) as with_gps FROM rtl433_logs WHERE latitude IS NOT NULL")
print(f"Entries with GPS: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) as total FROM rtl433_logs")
print(f"Total entries: {cursor.fetchone()[0]}")
EOF
```

## Troubleshooting Tests

### Logger Not Receiving Data

```bash
# Test rtl_433 is working
rtl_433 -F json

# Test with verbose output
rtl_433 -F json | python3 -m rtl433_geo_logger.logger --no-gps -v
```

### GPS Not Working

```bash
# Check GPSD status
gpspipe -w

# Check connection
python3 << EOF
try:
    import gpsd
    gpsd.connect()
    packet = gpsd.get_current()
    print(f"GPS mode: {packet.mode}")
    if packet.mode >= 2:
        print(f"Position: {packet.lat}, {packet.lon}")
except Exception as e:
    print(f"GPS error: {e}")
EOF
```

### Database Issues

```bash
# Check database schema
sqlite3 test.db ".schema"

# Check for corrupted database
sqlite3 test.db "PRAGMA integrity_check;"

# Repair if needed
sqlite3 test.db "VACUUM;"
```

### Web Interface Not Loading

```bash
# Check Flask is installed
python3 -c "import flask; print(flask.__version__)"

# Start with debug mode
python3 -m rtl433_geo_logger.web --debug --db test.db

# Check port is not in use
netstat -tlnp | grep 5000
```

## Automated Test Script

Run the comprehensive test:

```bash
cd examples
chmod +x test_protocols.sh
./test_protocols.sh
```

This will:
1. Create test database
2. Import example data
3. Show statistics
4. Display sample entries
5. Provide web server command

## CI/CD Testing

For automated testing in CI/CD pipelines:

```bash
# Install dependencies
pip install -r requirements.txt

# Run syntax check
python3 -m py_compile rtl433_geo_logger/*.py

# Run basic functionality test
cat examples/test_data.json | python3 -m rtl433_geo_logger.logger --no-gps --db ci_test.db

# Verify database
python3 << EOF
import sqlite3
conn = sqlite3.connect('ci_test.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM rtl433_logs")
count = cursor.fetchone()[0]
assert count == 10, f"Expected 10 entries, got {count}"
print("✓ Database test passed")
EOF
```

## Success Criteria

A successful test should show:

- ✅ Logger accepts RTL433 JSON data
- ✅ Database stores all fields correctly
- ✅ Protocol names extracted (or "Unknown")
- ✅ Device IDs extracted when available
- ✅ RSSI values stored when available
- ✅ Complete JSON preserved in data_json
- ✅ Web interface loads without errors
- ✅ Map displays markers (if GPS data present)
- ✅ Filters work correctly
- ✅ Heatmap toggles properly
- ✅ API endpoints return valid JSON

## Next Steps

After testing:

1. Review collected data in web interface
2. Adjust RTL433 parameters if needed
3. Configure GPS if doing mobile collection
4. Set up persistent database location
5. Consider backup strategy for important data
6. Monitor disk space for long-term collection

## Getting Help

If tests fail:

1. Check error messages in logger output
2. Verify RTL433 JSON format matches expectations
3. Review PROTOCOLS.md for custom protocol support
4. Check database with sqlite3 CLI
5. Open an issue with test results and error messages
