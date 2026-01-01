# RTL433 Protocol Support

## Overview

RTL433 Geo-Logger is designed to handle **all** RTL433 protocols, including:
- Standard built-in protocols (Acurite, Oregon Scientific, etc.)
- Custom protocols defined by users
- Flex decoder outputs

## How It Works

The logger uses a flexible parsing strategy that:
1. **Stores complete JSON**: All RTL433 data is preserved in the `data_json` field
2. **Extracts common fields**: Attempts to extract protocol, device ID, and RSSI
3. **Gracefully handles missing fields**: Continues logging even if fields are absent

## Field Extraction Logic

### Protocol/Model Detection

The logger tries multiple field names in order:
1. `model` - Most common field for built-in protocols
2. `protocol` - Alternative field name
3. `type` - Used by some custom protocols
4. Falls back to `"Unknown"` if none found

### Device ID Detection

The logger searches for device IDs in these fields:
- `id`, `device_id`, `device`
- `sensor_id`, `transmitter_id`, `node_id`
- `address`, `code`, `rolling_code`
- `house_code`, `serial`
- `unit`, `channel`

If no device ID is found, the log is still stored (device_id = NULL).

### RSSI/Signal Strength

Searches for signal strength in:
- `rssi` or `RSSI` - Most common
- `snr` - Signal-to-noise ratio (alternative)

## Examples

### Standard Protocol (Acurite-Tower)

```json
{
  "time": "2024-01-15 10:30:45",
  "model": "Acurite-Tower",
  "id": 12345,
  "channel": "A",
  "battery_ok": 1,
  "temperature_C": 20.5,
  "humidity": 65,
  "rssi": -45,
  "snr": 12.3,
  "noise": -57.3
}
```

**Extracted fields:**
- Protocol: `Acurite-Tower`
- Device ID: `12345`
- RSSI: `-45`

### Custom Protocol (Flex Decoder)

```json
{
  "time": "2024-01-15 10:31:00",
  "protocol": "custom_sensor",
  "type": "flex",
  "transmitter_id": "ABC123",
  "payload": "deadbeef",
  "data": [10, 20, 30, 40],
  "rssi": -52
}
```

**Extracted fields:**
- Protocol: `custom_sensor`
- Device ID: `ABC123`
- RSSI: `-52`

### Minimal Custom Data

```json
{
  "time": "2024-01-15 10:32:15",
  "raw": "101010101010",
  "freq": 433920000
}
```

**Extracted fields:**
- Protocol: `Unknown`
- Device ID: `None`
- RSSI: `None`

**Note:** This is still logged successfully with all data in `data_json`.

### Custom Protocol Without Standard Fields

```json
{
  "timestamp": "2024-01-15T10:33:00Z",
  "type": "my_device",
  "node_id": 42,
  "value1": 100,
  "value2": 200,
  "snr": 15.2
}
```

**Extracted fields:**
- Protocol: `my_device`
- Device ID: `42`
- RSSI: `15.2` (from SNR)

## RTL433 Configuration Tips

### Enabling Custom Protocols

RTL433 supports custom protocols via flex decoder:

```bash
# Example: Custom 433MHz device
rtl_433 -X 'n=custom_sensor,m=OOK_PWM,s=400,l=800,r=8000,g=1000,t=200,y=0' -F json
```

### Output Format

Always use JSON output for compatibility:

```bash
rtl_433 -F json | rtl433-logger
```

### Multiple Protocols

The logger handles mixed protocols automatically:

```bash
# Capture everything on 433MHz
rtl_433 -f 433.92M -F json | rtl433-logger

# Capture multiple frequencies (requires multiple dongles)
rtl_433 -d 0 -f 433.92M -F json | rtl433-logger --db data1.db &
rtl_433 -d 1 -f 315M -F json | rtl433-logger --db data2.db &
```

## Database Storage

All protocol data is preserved:

1. **Common fields**: Extracted into dedicated columns for easy querying
2. **Complete data**: Original JSON in `data_json` column
3. **No data loss**: Even unrecognized protocols are fully stored

### Querying Custom Data

```python
import sqlite3
import json

conn = sqlite3.connect('rtl433_data.db')
cursor = conn.cursor()

# Get all logs from a custom protocol
cursor.execute("SELECT data_json FROM rtl433_logs WHERE protocol = ?", ("custom_sensor",))

for row in cursor.fetchall():
    data = json.loads(row[0])
    # Access any custom field
    print(data.get('custom_field'))
```

## Web Interface

The web interface automatically:
- Lists all protocols in the filter dropdown (including custom ones)
- Displays device IDs from any field
- Shows RSSI/SNR in markers and heatmaps
- Handles missing fields gracefully

## Troubleshooting

### Protocol Not Detected

If your custom protocol shows as "Unknown":
- Check that JSON includes `model`, `protocol`, or `type` field
- All data is still logged in `data_json`
- You can query by other fields using the API

### Device ID Not Extracted

If device ID is not showing:
- Check field names in your RTL433 output
- Add field name to `_extract_device_id()` in `database.py`
- Data is still logged, just without device_id index

### RSSI Missing

If RSSI shows as N/A:
- Check if RTL433 is outputting signal strength
- Use `-M level` or `-M noise` flags with RTL433
- Some protocols don't provide RSSI

## Best Practices

1. **Always use JSON output** from RTL433
2. **Include time field** in RTL433 output (default)
3. **Use consistent field names** in custom protocols
4. **Test custom protocols** with small datasets first
5. **Monitor logs** for parsing warnings

## Contributing

If you use a custom protocol with different field names, consider contributing:
1. Add field name to extraction logic
2. Submit example JSON
3. Update documentation
