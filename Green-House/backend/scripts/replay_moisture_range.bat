@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Replay historical sensor readings for a selected clock-time range.
rem Required: Green-House backend running at http://127.0.0.1:8000.
rem Optional overrides before running:
rem   set API_URL=http://127.0.0.1:8000/api/ingest/readings/
rem   set DEVICE_TOKEN=esp32-local-token
rem   set GREENHOUSE_ID=4
rem   set RANGE_START=11:00
rem   set RANGE_END=12:19
rem   set STEP_SECONDS=5
rem   set START_MOISTURE=65
rem   set END_MOISTURE=55
rem   set MOISTURE_FIELD=soil_moisture
rem   set OVERWRITE=true
rem   set DRY_RUN=true

if not defined API_URL set "API_URL=http://127.0.0.1:8000/api/ingest/readings/"
if not defined DEVICE_TOKEN set "DEVICE_TOKEN=esp32-local-token"
if not defined GREENHOUSE_ID set "GREENHOUSE_ID=4"
if not defined AUTO_MODE set "AUTO_MODE=true"
if not defined RANGE_START_DEFAULT set "RANGE_START_DEFAULT=11:00"
if not defined RANGE_END_DEFAULT set "RANGE_END_DEFAULT=12:19"
if not defined STEP_SECONDS set "STEP_SECONDS=5"
if not defined START_MOISTURE set "START_MOISTURE=65"
if not defined END_MOISTURE set "END_MOISTURE=55"
if not defined MOISTURE_FIELD set "MOISTURE_FIELD=soil_moisture"
if not defined OVERWRITE set "OVERWRITE=true"
if not defined TEMPERATURE set "TEMPERATURE=28"
if not defined AIR_HUMIDITY set "AIR_HUMIDITY=70"
if not defined LIGHT set "LIGHT=5500"

echo Replay sensor readings into Green-House backend.
echo Time formats: 8h20, 08:20, 9h, 09:00
echo.

if not defined RANGE_START set /p "RANGE_START=Start time [!RANGE_START_DEFAULT!]: "
if not defined RANGE_START (
  set "RANGE_START=!RANGE_START_DEFAULT!"
)

if not defined RANGE_END set /p "RANGE_END=End time [!RANGE_END_DEFAULT!]: "
if not defined RANGE_END (
  set "RANGE_END=!RANGE_END_DEFAULT!"
)

set /p "START_MOISTURE_INPUT=Start moisture percent [!START_MOISTURE!]: "
if defined START_MOISTURE_INPUT set "START_MOISTURE=!START_MOISTURE_INPUT!"

set /p "END_MOISTURE_INPUT=End moisture percent [!END_MOISTURE!]: "
if defined END_MOISTURE_INPUT set "END_MOISTURE=!END_MOISTURE_INPUT!"

set /p "MOISTURE_FIELD_INPUT=Moisture field: soil_moisture, humidity, both [!MOISTURE_FIELD!]: "
if defined MOISTURE_FIELD_INPUT set "MOISTURE_FIELD=!MOISTURE_FIELD_INPUT!"

set "THIS_BAT=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$content = Get-Content -Raw -LiteralPath $env:THIS_BAT; $parts = [regex]::Split($content, '(?m)^# POWERSHELL_PAYLOAD\s*$'); if ($parts.Count -lt 2) { throw 'PowerShell payload marker not found.' }; Invoke-Expression $parts[1]"
exit /b %ERRORLEVEL%

# POWERSHELL_PAYLOAD
$ErrorActionPreference = 'Stop'

function Get-EnvValue {
    param([string]$Name, [string]$Default)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function Get-EnvDouble {
    param([string]$Name, [double]$Default)
    $raw = Get-EnvValue $Name ([string]$Default)
    $parsed = 0.0
    if (-not [double]::TryParse($raw, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
        throw "$Name must be a number. Current value: $raw"
    }
    return $parsed
}

function Get-EnvInt {
    param([string]$Name, [int]$Default)
    $raw = Get-EnvValue $Name ([string]$Default)
    $parsed = 0
    if (-not [int]::TryParse($raw, [ref]$parsed)) {
        throw "$Name must be an integer. Current value: $raw"
    }
    return $parsed
}

function Parse-ClockTime {
    param([string]$Value)

    $normalized = $Value.Trim().ToLowerInvariant() -replace '\s+', ''
    if ($normalized -match '^(?<hour>\d{1,2})h(?<minute>\d{1,2})?$') {
        $hour = [int]$Matches.hour
        $minute = if ($Matches.minute) { [int]$Matches.minute } else { 0 }
    }
    elseif ($normalized -match '^(?<hour>\d{1,2}):(?<minute>\d{1,2})$') {
        $hour = [int]$Matches.hour
        $minute = [int]$Matches.minute
    }
    elseif ($normalized -match '^(?<hour>\d{1,2})$') {
        $hour = [int]$Matches.hour
        $minute = 0
    }
    else {
        throw "Invalid time '$Value'. Use formats like 8h20, 08:20, 9h, or 09:00."
    }

    if ($hour -lt 0 -or $hour -gt 23 -or $minute -lt 0 -or $minute -gt 59) {
        throw "Invalid time '$Value'. Hour must be 0-23 and minute must be 0-59."
    }

    return [TimeSpan]::new($hour, $minute, 0)
}

$apiUrl = Get-EnvValue 'API_URL' 'http://127.0.0.1:8000/api/ingest/readings/'
$deviceToken = Get-EnvValue 'DEVICE_TOKEN' 'esp32-local-token'
$greenhouseId = Get-EnvInt 'GREENHOUSE_ID' 4
$autoModeRaw = (Get-EnvValue 'AUTO_MODE' 'true').Trim().ToLowerInvariant()
$autoMode = $autoModeRaw -in @('1', 'true', 'yes', 'y')
$overwriteRaw = (Get-EnvValue 'OVERWRITE' 'true').Trim().ToLowerInvariant()
$overwrite = $overwriteRaw -in @('1', 'true', 'yes', 'y')
$stepSeconds = Get-EnvInt 'STEP_SECONDS' 5
$startMoisture = Get-EnvDouble 'START_MOISTURE' 65
$endMoisture = Get-EnvDouble 'END_MOISTURE' 55
$moistureField = (Get-EnvValue 'MOISTURE_FIELD' 'soil_moisture').Trim().ToLowerInvariant()
$temperature = Get-EnvDouble 'TEMPERATURE' 28
$airHumidity = Get-EnvDouble 'AIR_HUMIDITY' 70
$light = Get-EnvDouble 'LIGHT' 5500
$dryRun = (Get-EnvValue 'DRY_RUN' 'false').Trim().ToLowerInvariant() -in @('1', 'true', 'yes', 'y')

if ($stepSeconds -le 0) {
    throw 'STEP_SECONDS must be greater than 0.'
}

if ($moistureField -notin @('soil_moisture', 'humidity', 'both')) {
    throw "MOISTURE_FIELD must be soil_moisture, humidity, or both. Current value: $moistureField"
}

$today = (Get-Date).Date
$startAt = $today.Add((Parse-ClockTime (Get-EnvValue 'RANGE_START' '')))
$endAt = $today.Add((Parse-ClockTime (Get-EnvValue 'RANGE_END' '')))
if ($endAt -lt $startAt) {
    $endAt = $endAt.AddDays(1)
}
if ($endAt -eq $startAt) {
    throw 'End time must be after start time.'
}

$points = [System.Collections.Generic.List[datetime]]::new()
for ($cursor = $startAt; $cursor -le $endAt; $cursor = $cursor.AddSeconds($stepSeconds)) {
    $points.Add($cursor)
}
if ($points.Count -eq 0 -or $points[$points.Count - 1] -ne $endAt) {
    $points.Add($endAt)
}

Write-Host "API_URL=$apiUrl"
Write-Host "GREENHOUSE_ID=$greenhouseId"
Write-Host "Range=$($startAt.ToString('yyyy-MM-dd HH:mm')) -> $($endAt.ToString('yyyy-MM-dd HH:mm'))"
Write-Host "Samples=$($points.Count), step=$stepSeconds second(s), $moistureField=$startMoisture -> $endMoisture"
Write-Host "OVERWRITE=$overwrite"
if ($dryRun) {
    Write-Host 'DRY_RUN=true, no POST requests will be sent.'
}
Write-Host ''

$headers = @{ 'X-Device-Token' = $deviceToken }

for ($index = 0; $index -lt $points.Count; $index++) {
    $ratio = if ($points.Count -eq 1) { 0.0 } else { [double]$index / [double]($points.Count - 1) }
    $moisture = [Math]::Round($startMoisture + (($endMoisture - $startMoisture) * $ratio), 2)
    $soilMoisture = if ($moistureField -in @('soil_moisture', 'both')) { $moisture } else { 60.0 }
    $humidity = if ($moistureField -in @('humidity', 'both')) { $moisture } else { $airHumidity }

    $payload = [ordered]@{
        greenhouse_id = $greenhouseId
        recorded_at = $points[$index].ToUniversalTime().ToString('o')
        temperature = $temperature
        humidity = $humidity
        light = $light
        soil_moisture = $soilMoisture
        auto_mode = $autoMode
        overwrite = $overwrite
        firmware_version = 'sensor-range-replay-bat'
        device_states = [ordered]@{
            fan_on = ($temperature -ge 31)
            pump_on = $false
            light_on = ($light -lt 3500)
        }
        sensor_errors = @{}
        payload = [ordered]@{
            source = 'replay_moisture_range.bat'
            moisture_field = $moistureField
            replay_index = $index
            replay_count = $points.Count
        }
    }

    $json = $payload | ConvertTo-Json -Depth 8 -Compress
    Write-Host "[$($points[$index].ToString('HH:mm'))] soil_moisture=$soilMoisture humidity=$humidity"

    if (-not $dryRun) {
        Invoke-RestMethod -Method Post -Uri $apiUrl -Headers $headers -ContentType 'application/json' -Body $json | Out-Null
    }
}

Write-Host ''
Write-Host 'Replay completed.'
