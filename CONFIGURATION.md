# RTL433 Geo-Logger Configuration Examples

## RTL433 Native GPSd Support

RTL433 has **built-in GPSd support** that includes GPS coordinates directly in JSON output. This is the recommended approach for GPS integration.

### Quick Start with GPS

```bash
# 1. Start GPSD
sudo gpsd -N /dev/ttyUSB0

# 2. Run rtl_433 (it will auto-detect GPSd on localhost:2947)
# GPS data (lat, lon, alt) will be included in JSON output
rtl_433 -F json -M time:iso:utc -M protocol -M level | rtl433-logger

# 3. Or use a configuration file (see examples/rtl_433.conf)
rtl_433 -c examples/rtl_433.conf -F json | rtl433-logger
```

### RTL433 Configuration File with GPS

Create `rtl_433.conf`:
```
output json
output_tag gpsd,lat,lon,alt
frequency 433.92M
```

Then run:
```bash
rtl_433 -c rtl_433.conf | rtl433-logger
```

### Verify GPS Data in Output

When GPSd is running and rtl_433 is configured properly, you'll see GPS fields in the JSON:
```json
{
  "time": "2026-01-02 16:51:20",
  "model": "inFactory-TH",
  "id": 159,
  "temperature_C": 22.56,
  "humidity": 29,
  "rssi": 0.7,
  "lat": 44.704776200,
  "lon": 2.661084933,
  "alt": 695.3
}
```

## Basic RTL433 Commands

### Capture Everything on 433MHz
```bash
rtl_433 -f 433.92M -F json | rtl433-logger
```

### Capture with Specific Protocol
```bash
# Only Acurite sensors
rtl_433 -R 40 -F json | rtl433-logger

# Multiple protocols
rtl_433 -R 40 -R 41 -R 42 -F json | rtl433-logger
```

### Increase Sensitivity
```bash
# Increase gain
rtl_433 -g 40 -F json | rtl433-logger

# Auto gain
rtl_433 -g 0 -F json | rtl433-logger
```

## Custom Protocol (Flex Decoder) Examples

### Simple OOK Device
```bash
rtl_433 -X 'n=my_sensor,m=OOK_PWM,s=400,l=800,r=8000,g=1000,t=200,y=0' -F json | rtl433-logger
```

### FSK Device
```bash
rtl_433 -X 'n=my_fsk,m=FSK_PCM,s=100,l=100,r=5000' -F json | rtl433-logger
```

### Multiple Custom Protocols
```bash
rtl_433 \
  -X 'n=sensor1,m=OOK_PWM,s=400,l=800,r=8000' \
  -X 'n=sensor2,m=OOK_PPM,s=200,l=400,r=5000' \
  -F json | rtl433-logger
```

## GPS Configuration

### Basic GPS Setup

RTL433 includes native GPSd support. Simply ensure GPSd is running:

```bash
# Start GPSD with USB GPS device
sudo gpsd -N /dev/ttyUSB0

# RTL433 will automatically detect GPSd and include lat, lon, alt in JSON
rtl_433 -F json | rtl433-logger
```

### GPSD with Different GPS Devices

```bash
# USB GPS device
sudo gpsd -N /dev/ttyUSB0

# Serial GPS device
sudo gpsd -N /dev/ttyS0

# Bluetooth GPS (after pairing)
sudo gpsd -N /dev/rfcomm0

# Multiple GPS devices
sudo gpsd -N /dev/ttyUSB0 /dev/ttyUSB1
```

### Advanced GPSD Configuration

```bash
# Specify GPSD host and port in rtl_433.conf
# report_meta gpsd localhost:2947

# Or connect to remote GPSD
# report_meta gpsd 192.168.1.100:2947
```

### Test GPSD Connection

```bash
# Check if GPSD is receiving data
cgps

# Or use gpsmon for detailed view
gpsmon

# Test with gpspipe
gpspipe -w | head -n 5
```
```

## Database Configuration

### Custom Database Location
```bash
rtl_433 -F json | rtl433-logger --db /data/rtl433/sensors.db
```

### Separate Databases by Frequency
```bash
# Terminal 1: 433MHz
rtl_433 -d 0 -f 433.92M -F json | rtl433-logger --db 433mhz.db

# Terminal 2: 315MHz (with second dongle)
rtl_433 -d 1 -f 315M -F json | rtl433-logger --db 315mhz.db
```

## Web Service Configuration

### Basic Web Service
```bash
rtl433-web --db sensors.db
```

### Custom Port
```bash
rtl433-web --db sensors.db --port 8080
```

### Listen on All Interfaces
```bash
rtl433-web --db sensors.db --host 0.0.0.0 --port 80
```

### Debug Mode
```bash
rtl433-web --db sensors.db --debug
```

## Advanced Usage

### Log to File and Database Simultaneously
```bash
rtl_433 -F json | tee rtl433.log | rtl433-logger
```

### Filter by Signal Strength
```bash
# Only log strong signals (RSSI > -50)
rtl_433 -F json | grep -v '"rssi":[[:space:]]*-[5-9][0-9]' | rtl433-logger
```

### Rotate Databases Daily
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
rtl_433 -F json | rtl433-logger --db "rtl433_${DATE}.db"
```

### Mobile Wardriving Setup
```bash
#!/bin/bash
# Start GPS
sudo gpsd -N /dev/ttyUSB0

# Wait for GPS fix
sleep 10

# Start logging with timestamp in filename
DATE=$(date +%Y%m%d_%H%M%S)
rtl_433 -F json | rtl433-logger --db "wardriving_${DATE}.db"
```

## Systemd Service Example

Create `/etc/systemd/system/rtl433-logger.service`:

```ini
[Unit]
Description=RTL433 Geo-Logger
After=network.target gpsd.service

[Service]
Type=simple
User=rtl433
WorkingDirectory=/home/rtl433
ExecStart=/bin/bash -c 'rtl_433 -F json | /usr/local/bin/rtl433-logger --db /var/lib/rtl433/sensors.db'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable rtl433-logger
sudo systemctl start rtl433-logger
```

## Docker Example

`Dockerfile`:
```dockerfile
FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    rtl-sdr \
    librtlsdr-dev \
    gpsd \
    gpsd-clients \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY rtl433_geo_logger /app/rtl433_geo_logger

VOLUME /data

ENTRYPOINT ["python", "-m", "rtl433_geo_logger.logger"]
CMD ["--db", "/data/rtl433.db"]
```

Run:
```bash
docker build -t rtl433-logger .
docker run --device=/dev/bus/usb -v /data:/data rtl433-logger
```

## Performance Tuning

### High-Volume Collection
```bash
# Increase buffer size, reduce frequency hopping
rtl_433 -f 433.92M -F json | rtl433-logger --db high_volume.db
```

### Low-Power Mode (Raspberry Pi)
```bash
# Reduce sample rate
rtl_433 -s 250k -F json | rtl433-logger --db low_power.db
```

## Backup Strategy

### Daily Backup
```bash
#!/bin/bash
# backup_rtl433.sh
DATE=$(date +%Y%m%d)
sqlite3 /var/lib/rtl433/sensors.db ".backup /backup/sensors_${DATE}.db"
```

### Cloud Sync
```bash
# Sync to cloud storage
rclone sync /var/lib/rtl433/ remote:rtl433-backups/
```

## Troubleshooting

### RTL-SDR Not Found
```bash
# Check device
rtl_test

# If not found, check permissions
sudo usermod -a -G plugdev $USER
```

### GPS Not Working

```bash
# Check if GPSD is receiving data
cgps
gpsmon

# Check rtl_433 GPSd connection
# rtl_433 should show "Getting GPSd JSON data from localhost port 2947"
rtl_433 -F json

# Restart GPSD if needed
sudo systemctl restart gpsd

# Verify GPS data in rtl_433 output
# Look for lat, lon, alt fields in JSON output
rtl_433 -F json | grep -E '"(lat|lon|alt)"'
```

### Database Locked
```bash
# Check for other processes
lsof /path/to/rtl433.db

# Or use Write-Ahead Logging
sqlite3 rtl433.db "PRAGMA journal_mode=WAL;"
```

## Production Recommendations

1. **Use systemd service** for automatic restart
2. **Enable GPS via rtl_433 native GPSd support** for mobile/fixed location logging
3. **Set up regular backups** of database
4. **Monitor disk space** - database can grow quickly
5. **Use WAL mode** for better concurrent access
6. **Run web service separately** from logger
7. **Set appropriate permissions** on database file
8. **Consider log rotation** for long-term operation
9. **Use rtl_433.conf file** for consistent configuration

## Example Complete Setup

```bash
# 1. Install
git clone https://github.com/remiserriere/rtl433-geo-logger.git
cd rtl433-geo-logger
pip install -e .

# 2. Start GPSD (for GPS support)
sudo gpsd -N /dev/ttyUSB0

# 3. Start logger with rtl_433 native GPSd support
rtl_433 -c examples/rtl_433.conf -F json | rtl433-logger --db /data/rtl433.db

# 4. Start web service (separate terminal)
rtl433-web --db /data/rtl433.db --host 0.0.0.0 --port 5000

# 5. Access web interface
# Open browser to http://your-server:5000
```
