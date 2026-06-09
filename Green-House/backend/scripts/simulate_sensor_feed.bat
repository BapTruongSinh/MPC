@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Simulate an ESP32 by POSTing sensor readings every 5 seconds.
rem Soil moisture starts at 65% and decreases to 55%, then holds at 55%.
rem Required: Green-House backend running at http://127.0.0.1:8000.
rem Optional overrides before running:
rem   set API_URL=http://127.0.0.1:8000/api/ingest/readings/
rem   set DEVICE_TOKEN=esp32-local-token
rem   set INTERVAL_SECONDS=5
rem   set AUTO_MODE=true
rem   set GREENHOUSE_ID=4
rem   set START_SOIL_MOISTURE=65
rem   set END_SOIL_MOISTURE=55
rem   set SOIL_MOISTURE_STEP=1

if not defined API_URL set "API_URL=http://127.0.0.1:8000/api/ingest/readings/"
if not defined DEVICE_TOKEN set "DEVICE_TOKEN=esp32-local-token"
if not defined INTERVAL_SECONDS set "INTERVAL_SECONDS=5"
if not defined AUTO_MODE set "AUTO_MODE=true"
if not defined GREENHOUSE_ID set "GREENHOUSE_ID=4"
if not defined START_SOIL_MOISTURE set "START_SOIL_MOISTURE=65"
if not defined END_SOIL_MOISTURE set "END_SOIL_MOISTURE=55"
if not defined SOIL_MOISTURE_STEP set "SOIL_MOISTURE_STEP=1"

set /a SOIL_MOISTURE_CURRENT=%START_SOIL_MOISTURE%

set "TEMP_JSON=%TEMP%\green_house_sensor_payload.json"

echo Sensor simulator is running.
echo API_URL=!API_URL!
echo INTERVAL_SECONDS=!INTERVAL_SECONDS!
echo AUTO_MODE=!AUTO_MODE!
echo GREENHOUSE_ID=!GREENHOUSE_ID!
echo SOIL_MOISTURE=!START_SOIL_MOISTURE! -^> !END_SOIL_MOISTURE! step !SOIL_MOISTURE_STEP!
echo Press Ctrl+C to stop.
echo.

:loop
for /f %%I in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('o')"') do set "RECORDED_AT=%%I"

set /a TEMPERATURE=24 + !RANDOM! %% 10
set /a HUMIDITY=55 + !RANDOM! %% 31
set /a LIGHT=2500 + !RANDOM! %% 9500
set /a SOIL_MOISTURE=!SOIL_MOISTURE_CURRENT!
set /a MQ135=180 + !RANDOM! %% 260

set "FAN_ON=false"
if !TEMPERATURE! GEQ 31 set "FAN_ON=true"

set "LIGHT_ON=false"
if !LIGHT! LSS 3500 set "LIGHT_ON=true"

(
  echo {"greenhouse_id":!GREENHOUSE_ID!,"recorded_at":"!RECORDED_AT!","temperature":!TEMPERATURE!,"humidity":!HUMIDITY!,"light":!LIGHT!,"soil_moisture":!SOIL_MOISTURE!,"auto_mode":!AUTO_MODE!,"firmware_version":"sensor-simulator-bat","device_states":{"fan_on":!FAN_ON!,"pump_on":false,"light_on":!LIGHT_ON!},"sensor_errors":{},"payload":{"source":"simulate_sensor_feed.bat","mq135_ppm":!MQ135!}}
) > "!TEMP_JSON!"

echo [!date! !time!] temperature=!TEMPERATURE! humidity=!HUMIDITY! light=!LIGHT! soil=!SOIL_MOISTURE!
curl -s -X POST "!API_URL!" -H "Content-Type: application/json" -H "X-Device-Token: !DEVICE_TOKEN!" --data-binary "@!TEMP_JSON!"
echo.
echo Waiting !INTERVAL_SECONDS! seconds...

if !START_SOIL_MOISTURE! GTR !END_SOIL_MOISTURE! (
  if !SOIL_MOISTURE_CURRENT! GTR !END_SOIL_MOISTURE! (
    set /a SOIL_MOISTURE_CURRENT-=!SOIL_MOISTURE_STEP!
    if !SOIL_MOISTURE_CURRENT! LSS !END_SOIL_MOISTURE! set /a SOIL_MOISTURE_CURRENT=!END_SOIL_MOISTURE!
  )
) else (
  if !SOIL_MOISTURE_CURRENT! LSS !END_SOIL_MOISTURE! (
    set /a SOIL_MOISTURE_CURRENT+=!SOIL_MOISTURE_STEP!
    if !SOIL_MOISTURE_CURRENT! GTR !END_SOIL_MOISTURE! set /a SOIL_MOISTURE_CURRENT=!END_SOIL_MOISTURE!
  )
)

timeout /t !INTERVAL_SECONDS! /nobreak >nul
goto loop
