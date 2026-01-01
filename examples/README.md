# Example RTL433 Data

This file contains examples of various RTL433 protocol outputs, demonstrating the logger's ability to handle diverse data formats.

## Standard Acurite-Tower Sensor
```json
{"time":"2024-01-15 10:30:00","model":"Acurite-Tower","id":12345,"channel":"A","battery_ok":1,"temperature_C":20.5,"humidity":65,"rssi":-45,"snr":12.3,"noise":-57.3}
```
- Protocol extracted: `Acurite-Tower` (from `model`)
- Device ID extracted: `12345` (from `id`)
- RSSI extracted: `-45` (from `rssi`)

## Oregon Scientific Sensor
```json
{"time":"2024-01-15 10:30:15","model":"Oregon-THGR122N","id":234,"channel":1,"battery_ok":1,"temperature_C":18.2,"humidity":70,"rssi":-50}
```
- Protocol: `Oregon-THGR122N`
- Device ID: `234`
- RSSI: `-50`

## Custom Flex Decoder Output
```json
{"time":"2024-01-15 10:30:30","protocol":"custom_sensor","type":"flex","transmitter_id":"ABC123","payload":"deadbeef","data":[10,20,30,40],"rssi":-52}
```
- Protocol extracted: `custom_sensor` (from `protocol`)
- Device ID extracted: `ABC123` (from `transmitter_id`)
- RSSI extracted: `-52` (from `rssi`)
- **Note**: Custom payload and data array are preserved in `data_json`

## Custom Protocol with Non-Standard Fields
```json
{"time":"2024-01-15 10:30:45","type":"my_device","node_id":42,"value1":100,"value2":200,"snr":15.2}
```
- Protocol extracted: `my_device` (from `type`)
- Device ID extracted: `42` (from `node_id`)
- RSSI extracted: `15.2` (from `snr` - signal-to-noise ratio)

## LaCrosse TX Sensor
```json
{"time":"2024-01-15 10:31:00","model":"LaCrosse-TX","id":55,"temperature_C":22.1,"humidity":58,"rssi":-48}
```
- Protocol: `LaCrosse-TX`
- Device ID: `55`
- RSSI: `-48`

## Custom Door Sensor
```json
{"time":"2024-01-15 10:31:15","protocol":"door_sensor","address":"0xABCD","state":"open","battery":95,"rssi":-40}
```
- Protocol extracted: `door_sensor` (from `protocol`)
- Device ID extracted: `0xABCD` (from `address`)
- RSSI extracted: `-40`
- **Note**: Custom fields like `state` and `battery` are preserved

## Unknown Device (Minimal Data)
```json
{"time":"2024-01-15 10:31:30","raw":"101010101010","freq":433920000}
```
- Protocol: `Unknown` (no standard protocol field)
- Device ID: `None` (no ID field found)
- RSSI: `None` (no signal strength field)
- **Note**: Still logged successfully with all data in `data_json`

## Tire Pressure Monitoring System (TPMS)
```json
{"time":"2024-01-15 10:31:45","model":"Schrader-TPMS","type":"TPMS","id":"12AB34CD","pressure_kPa":220,"temperature_C":25,"rssi":-55}
```
- Protocol: `Schrader-TPMS`
- Device ID: `12AB34CD`
- RSSI: `-55`

## Custom Weather Station
```json
{"time":"2024-01-15 10:32:00","protocol":"my_weather","sensor_id":"WX001","temp":19.8,"humidity":72,"wind_speed":5.2,"wind_dir":180,"rain":0.5,"rssi":-47}
```
- Protocol extracted: `my_weather` (from `protocol`)
- Device ID extracted: `WX001` (from `sensor_id`)
- RSSI extracted: `-47`
- **Note**: All weather measurements preserved in JSON

## Home Automation Remote
```json
{"time":"2024-01-15 10:32:15","model":"Generic-Remote","code":"0x123456","house_code":"A","unit":3,"command":"on","rolling_code":"7F8E9D","rssi":-38}
```
- Protocol: `Generic-Remote`
- Device ID extracted: `0x123456` (from `code`)
- RSSI: `-38`
- **Note**: Multiple ID fields (`code`, `house_code`, `rolling_code`) - first match used

## Usage

To test with these examples:
```bash
cat examples/test_data.json | rtl433-logger --no-gps --db test.db
```

All protocols are stored successfully and can be filtered in the web interface!
