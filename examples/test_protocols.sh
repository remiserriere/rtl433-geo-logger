#!/bin/bash
# Test script to demonstrate RTL433 Geo-Logger with various protocol types

echo "RTL433 Geo-Logger - Protocol Testing"
echo "====================================="
echo ""

# Clean up any previous test database
rm -f test_rtl433.db

echo "1. Testing data collection with various protocols..."
echo "   (Using example data without GPS)"
echo ""

# Feed test data to logger
cat examples/test_data.json | python3 -m rtl433_geo_logger.logger --db test_rtl433.db --no-gps

echo ""
echo "2. Database statistics:"
python3 -c "
import sqlite3
import json

conn = sqlite3.connect('test_rtl433.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Total logs
cursor.execute('SELECT COUNT(*) as count FROM rtl433_logs')
print(f'   Total logs: {cursor.fetchone()[\"count\"]}')

# Protocols
cursor.execute('SELECT protocol, COUNT(*) as count FROM rtl433_logs GROUP BY protocol')
print('   Protocols found:')
for row in cursor.fetchall():
    print(f'     - {row[\"protocol\"]}: {row[\"count\"]} entries')

# Device IDs
cursor.execute('SELECT device_id, COUNT(*) as count FROM rtl433_logs WHERE device_id IS NOT NULL GROUP BY device_id')
print('   Device IDs extracted:')
for row in cursor.fetchall():
    print(f'     - {row[\"device_id\"]}')

# RSSI stats
cursor.execute('SELECT AVG(rssi) as avg_rssi, MIN(rssi) as min_rssi, MAX(rssi) as max_rssi FROM rtl433_logs WHERE rssi IS NOT NULL')
row = cursor.fetchone()
if row['avg_rssi']:
    print(f'   RSSI range: {row[\"min_rssi\"]} to {row[\"max_rssi\"]} dBm (avg: {row[\"avg_rssi\"]:.1f})')

conn.close()
"

echo ""
echo "3. Sample log entries:"
python3 -c "
import sqlite3
import json

conn = sqlite3.connect('test_rtl433.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute('SELECT protocol, device_id, rssi, data_json FROM rtl433_logs LIMIT 5')
for row in cursor.fetchall():
    data = json.loads(row['data_json'])
    print(f'   Protocol: {row[\"protocol\"]:20s} Device: {str(row[\"device_id\"]):10s} RSSI: {str(row[\"rssi\"]):5s}')
    
conn.close()
"

echo ""
echo "4. To view in web interface:"
echo "   python3 -m rtl433_geo_logger.web --db test_rtl433.db"
echo "   Then open http://localhost:5000"
echo ""
echo "Test completed! Database: test_rtl433.db"
