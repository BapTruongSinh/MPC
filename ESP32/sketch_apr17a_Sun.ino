#include <Arduino.h>
#include <WiFi.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "esp_system.h"
#include <LiquidCrystal_I2C.h>

// Pins
const int SOIL_PIN = 36;
const int DHT_PIN = 4;

const int FAN_PIN = 26;
const int PUMP_PIN = 27;
const int LIGHT_PIN = 14;
const int MIST_PIN = 25;

const int SUN_LDR_LT_PIN = 34;
const int SUN_LDR_RT_PIN = 35;
const int SUN_LDR_LD_PIN = 32;
const int SUN_LDR_RD_PIN = 33;

const int SUN_SERVO_VERTICAL_PIN = 18;
const int SUN_SERVO_HORIZONTAL_PIN = 19;

#define DHTTYPE DHT22

//WiFi / WebSocket
const char* WIFI_SSID = "Khu H";
const char* WIFI_PASS = "khuh1234";

const char* WS_HOST = "10.85.155.132";
const uint16_t WS_PORT = 8000;
const char* WS_PATH = "/ws/esp/";

// Intervals
const unsigned long SENSOR_INTERVAL = 2500;
const unsigned long TELEMETRY_INTERVAL = 5000;
const unsigned long STATUS_INTERVAL = 5000;
const unsigned long WIFI_RETRY_INTERVAL = 5000;

const unsigned long SUN_TRACK_INTERVAL = 250;

//Sun tracker config
const int SUN_TRACK_THRESHOLD = 150;
const int SUN_SERVO_STEP = 3;
const int SUN_LDR_SAMPLES = 3;

const int SUN_SERVO_HORIZONTAL_MIN = 10;
const int SUN_SERVO_HORIZONTAL_MAX = 170;

const int SUN_SERVO_VERTICAL_MIN = 10;
const int SUN_SERVO_VERTICAL_MAX = 80;

//DHT config
const int DHT_FAIL_LIMIT = 5;

DHT dht(DHT_PIN, DHTTYPE);
Servo sunServoV;
Servo sunServoH;
WebSocketsClient webSocket;

// LCD
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ===== States =====
bool wsConnected = false;

bool fanOn = false;
bool pumpOn = false;
bool lightOn = false;
bool mistOn = false;

// Boot mặc định AUTO
bool isAutoMode = true;
bool isSunAutoMode = true;

int soilRaw = 0;
float soilMoisture = 0.0f;

float humidity = NAN;
float temperature = NAN;

int dhtFailCount = 0;
bool dhtErrorState = false;

int sunLdrLT = 0;
int sunLdrRT = 0;
int sunLdrLD = 0;
int sunLdrRD = 0;

int sunServoVertical = 45;
int sunServoHorizontal = 90;

//Timers
unsigned long fanStartMs = 0, fanDurationMs = 0;
unsigned long pumpStartMs = 0, pumpDurationMs = 0;
unsigned long lightStartMs = 0, lightDurationMs = 0;
unsigned long mistStartMs = 0, mistDurationMs = 0;

unsigned long lastSensorMs = 0;
unsigned long lastTelemetryMs = 0;
unsigned long lastStatusMs = 0;
unsigned long lastWifiRetryMs = 0;
unsigned long lastSunTrackMs = 0;

//Helper
int clampHorizontalAngle(int angle) {
  if (angle < SUN_SERVO_HORIZONTAL_MIN) return SUN_SERVO_HORIZONTAL_MIN;
  if (angle > SUN_SERVO_HORIZONTAL_MAX) return SUN_SERVO_HORIZONTAL_MAX;
  return angle;
}

int clampVerticalAngle(int angle) {
  if (angle < SUN_SERVO_VERTICAL_MIN) return SUN_SERVO_VERTICAL_MIN;
  if (angle > SUN_SERVO_VERTICAL_MAX) return SUN_SERVO_VERTICAL_MAX;
  return angle;
}

float readSoilPercent() {
  soilRaw = analogRead(SOIL_PIN);

  float pct = 100.0f - ((float)soilRaw * 100.0f / 4095.0f);

  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;

  return pct;
}

int readSunLDR(int pin) {
  long total = 0;

  for (int i = 0; i < SUN_LDR_SAMPLES; i++) {
    total += analogRead(pin);
  }

  int value = total / SUN_LDR_SAMPLES;
  return map(value, 0, 4095, 0, 1000);
}

void readSunSensors() {
  sunLdrLT = readSunLDR(SUN_LDR_LT_PIN);
  sunLdrRT = readSunLDR(SUN_LDR_RT_PIN);
  sunLdrLD = readSunLDR(SUN_LDR_LD_PIN);
  sunLdrRD = readSunLDR(SUN_LDR_RD_PIN);
}

void readSensors() {
  soilMoisture = readSoilPercent();

  float newHumidity = dht.readHumidity();
  float newTemperature = dht.readTemperature();

  if (isnan(newHumidity) || isnan(newTemperature)) {
    dhtFailCount++;

    if (dhtFailCount >= DHT_FAIL_LIMIT) {
      dhtErrorState = true;

      Serial.print("[DHT22] ERROR NaN liên tục ");
      Serial.print(dhtFailCount);
      Serial.println(" lần");
    }
  } else {
    humidity = newHumidity;
    temperature = newTemperature;
    dhtFailCount = 0;
    dhtErrorState = false;
  }

  readSunSensors();
}

void printDhtAndSoil() {
  Serial.print("[SENSOR] SoilRaw=");
  Serial.print(soilRaw);
  Serial.print(" Soil=");
  Serial.print(soilMoisture, 1);
  Serial.print("% | ");

  if (dhtErrorState || isnan(temperature) || isnan(humidity)) {
    Serial.println("DHT22=ERROR NaN");
    return;
  }

  Serial.print("Temp=");
  Serial.print(temperature, 1);
  Serial.print("C Humidity=");
  Serial.print(humidity, 1);
  Serial.println("%");
}

void updateOutputs() {
  digitalWrite(FAN_PIN, fanOn ? HIGH : LOW);
  digitalWrite(PUMP_PIN, pumpOn ? HIGH : LOW);
  digitalWrite(LIGHT_PIN, lightOn ? HIGH : LOW);
  digitalWrite(MIST_PIN, mistOn ? HIGH : LOW);
}

void checkTimers() {
  unsigned long now = millis();
  bool changed = false;

  if (fanDurationMs > 0 && (now - fanStartMs >= fanDurationMs)) {
    fanOn = false;
    fanDurationMs = 0;
    changed = true;
    Serial.println("[HẸN GIỜ] Đã tự động tắt QUẠT (FAN)");
  }

  if (pumpDurationMs > 0 && (now - pumpStartMs >= pumpDurationMs)) {
    pumpOn = false;
    pumpDurationMs = 0;
    changed = true;
    Serial.println("[HẸN GIỜ] Đã tự động tắt BƠM (PUMP)");
  }

  if (lightDurationMs > 0 && (now - lightStartMs >= lightDurationMs)) {
    lightOn = false;
    lightDurationMs = 0;
    changed = true;
    Serial.println("[HẸN GIỜ] Đã tự động tắt ĐÈN (LIGHT)");
  }

  if (mistDurationMs > 0 && (now - mistStartMs >= mistDurationMs)) {
    mistOn = false;
    mistDurationMs = 0;
    changed = true;
    Serial.println("[HẸN GIỜ] Đã tự động tắt PHUN SƯƠNG (MIST)");
  }

  if (changed) {
    updateOutputs();
  }
}

void writeSunServos() {
  sunServoVertical = clampVerticalAngle(sunServoVertical);
  sunServoHorizontal = clampHorizontalAngle(sunServoHorizontal);

  sunServoV.write(sunServoVertical);
  sunServoH.write(sunServoHorizontal);
}

void setSunMode(bool autoMode) {
  isSunAutoMode = autoMode;
}

void setSunServoVertical(int angle) {
  isSunAutoMode = false;
  sunServoVertical = clampVerticalAngle(angle);
  writeSunServos();
}

void setSunServoHorizontal(int angle) {
  isSunAutoMode = false;
  sunServoHorizontal = clampHorizontalAngle(angle);
  writeSunServos();
}

//Solar tracker logic
void updateSunTracker() {
  if (!isSunAutoMode) return;

  readSunSensors();

  int avt = (sunLdrLT + sunLdrRT) / 2;
  int avd = (sunLdrLD + sunLdrRD) / 2;
  int avl = (sunLdrLT + sunLdrLD) / 2;
  int avr = (sunLdrRT + sunLdrRD) / 2;

  int dvert = avt - avd;
  int dhoriz = avl - avr;

  if (abs(dvert) > SUN_TRACK_THRESHOLD) {
    int nextVertical = sunServoVertical + (avt > avd ? SUN_SERVO_STEP : -SUN_SERVO_STEP);
    nextVertical = constrain(nextVertical, SUN_SERVO_VERTICAL_MIN, SUN_SERVO_VERTICAL_MAX);

    if (nextVertical != sunServoVertical) {
      sunServoVertical = nextVertical;
      sunServoV.write(sunServoVertical);
    }
  }

  if (abs(dhoriz) > SUN_TRACK_THRESHOLD) {
    int nextHorizontal = sunServoHorizontal + (avl > avr ? -SUN_SERVO_STEP : SUN_SERVO_STEP);
    nextHorizontal = constrain(nextHorizontal, SUN_SERVO_HORIZONTAL_MIN, SUN_SERVO_HORIZONTAL_MAX);

    if (nextHorizontal != sunServoHorizontal) {
      sunServoHorizontal = nextHorizontal;
      sunServoH.write(sunServoHorizontal);
    }
  }
}

//WebSocket send
void sendAck(int commandId, const char* status) {
  if (!wsConnected) return;

  JsonDocument doc;
  doc["type"] = "ack";

  JsonObject data = doc["data"].to<JsonObject>();
  data["id"] = commandId;
  data["command_id"] = String(commandId);
  data["status"] = status;

  String out;
  serializeJson(doc, out);
  webSocket.sendTXT(out);
}

void sendTelemetry() {
  if (!wsConnected) return;

  bool dhtError = dhtErrorState || isnan(temperature) || isnan(humidity);
  bool soilError = false;

  JsonDocument doc;
  doc["type"] = "telemetry";

  JsonObject data = doc["data"].to<JsonObject>();
  data["soil_moisture"] = soilMoisture;
  data["temperature"] = dhtError ? 0 : temperature;
  data["humidity"] = dhtError ? 0 : humidity;
  data["fan"] = fanOn;
  data["pump"] = pumpOn;
  data["light_device"] = lightOn;
  data["mist"] = mistOn;
  data["mode"] = isAutoMode ? "auto" : "manual";
  data["auto_mode"] = isAutoMode;

  JsonObject payload = data["payload"].to<JsonObject>();

  JsonObject sunTracker = payload["sun_tracker"].to<JsonObject>();
  sunTracker["mode"] = isSunAutoMode ? "sun_auto" : "sun_manual";
  sunTracker["ldr_lt"] = sunLdrLT;
  sunTracker["ldr_rt"] = sunLdrRT;
  sunTracker["ldr_ld"] = sunLdrLD;
  sunTracker["ldr_rd"] = sunLdrRD;
  sunTracker["servo_horizontal"] = sunServoHorizontal;
  sunTracker["servo_vertical"] = sunServoVertical;

  JsonObject deviceStates = data["device_states"].to<JsonObject>();
  deviceStates["fan_on"] = fanOn;
  deviceStates["pump_on"] = pumpOn;
  deviceStates["light_on"] = lightOn;
  deviceStates["mist_on"] = mistOn;

  JsonObject sensorErrors = data["sensor_errors"].to<JsonObject>();
  sensorErrors["dht"] = dhtError;
  sensorErrors["soil"] = soilError;

  String out;
  serializeJson(doc, out);
  webSocket.sendTXT(out);
}

//WebSocket receive

bool setDevicePower(const String& device, const String& value, float durationSeconds = 0.0f) {
  bool turnOn;

  if (value == "on") {
    turnOn = true;
  } else if (value == "off") {
    turnOn = false;
  } else {
    return false;
  }

  unsigned long durationMs = (turnOn && durationSeconds > 0) ? (unsigned long)(durationSeconds * 1000.0) : 0;

  if (device.startsWith("fan")) {
    fanOn = turnOn;
    fanStartMs = millis();
    fanDurationMs = durationMs;
    return true;
  }

  if (device.startsWith("pump")) {
    pumpOn = turnOn;
    pumpStartMs = millis();
    pumpDurationMs = durationMs;
    return true;
  }

  if (device.startsWith("light")) {
    lightOn = turnOn;
    lightStartMs = millis();
    lightDurationMs = durationMs;
    return true;
  }

  if (device.startsWith("mist")) {
    mistOn = turnOn;
    mistStartMs = millis();
    mistDurationMs = durationMs;
    return true;
  }

  return false;
}

void applyDesiredState(JsonObject data) {
  if (data["mode"].is<const char*>()) {
    String mode = data["mode"] | "";
    mode.toLowerCase();

    if (mode == "auto") {
      isAutoMode = true;
    } else if (mode == "manual") {
      isAutoMode = false;
    }
  }

  if (data["fan"].is<bool>() || data["fan"].is<int>()) {
    fanOn = data["fan"] | fanOn;
  }

  if (data["pump"].is<bool>() || data["pump"].is<int>()) {
    pumpOn = data["pump"] | pumpOn;
  }

  if (data["light"].is<bool>() || data["light"].is<int>()) {
    lightOn = data["light"] | lightOn;
  }

  if (data["mist"].is<bool>() || data["mist"].is<int>()) {
    mistOn = data["mist"] | mistOn;
  }

  updateOutputs();
}

void handleCommand(JsonObject cmd) {
  int commandId = cmd["id"] | 0;
  const char* deviceCode = cmd["device_code"] | "";
  const char* command = cmd["command"] | "";
  const char* value = cmd["value"] | "";

  float durationSeconds = 0.0f;
  if (cmd.containsKey("payload") && cmd["payload"].is<JsonObject>()) {
    durationSeconds = cmd["payload"]["duration"] | 0.0f;
  }

  String device = String(deviceCode);
  device.toLowerCase();

  String commandStr = String(command);
  commandStr.toLowerCase();

  String valueStr = String(value);
  valueStr.toLowerCase();

  if (commandId == 0) return;

  if (commandStr == "set_mode") {
    if (valueStr == "auto") {
      isAutoMode = true;
      sendAck(commandId, "ack");
      return;
    }

    if (valueStr == "manual") {
      isAutoMode = false;
      sendAck(commandId, "ack");
      return;
    }

    sendAck(commandId, "failed");
    return;
  }

  if (commandStr == "set_power") {
    if (setDevicePower(device, valueStr, durationSeconds)) {
      updateOutputs();
      sendAck(commandId, "ack");

      if (valueStr == "on" && durationSeconds > 0) {
        Serial.print("   => [ACTUATOR] Đã bật ");
        Serial.print(device);
        Serial.print(", tự tắt sau: ");
        Serial.print(durationSeconds, 3);
        Serial.println(" s");
      }
      return;
    }
  }

  sendAck(commandId, "ignored");
}

void processWsMessage(const String& message) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, message);
  if (err) return;

  String type = doc["type"] | "";

  if (type == "mode") {
    String value = doc["data"]["value"] | "";
    value.toLowerCase();

    if (value == "auto") {
      isAutoMode = true;
      Serial.println("[MODE] AUTO from server");
      return;
    }

    if (value == "manual") {
      isAutoMode = false;
      Serial.println("[MODE] MANUAL from server");
      return;
    }

    return;
  }

  if (type == "desired_state") {
    JsonObject data = doc["data"].as<JsonObject>();
    if (data.isNull()) return;

    Serial.println("[WS] desired_state");
    applyDesiredState(data);
    return;
  }

  if (type == "pending_commands") {
    JsonArray commands = doc["data"]["commands"].as<JsonArray>();
    if (commands.isNull() || commands.size() == 0) return;

    bool handledAny = false;

    for (JsonObject cmd : commands) {
      handleCommand(cmd);
      handledAny = true;
      delay(1);
    }

    if (handledAny) {
      updateOutputs();
    }

    return;
  }

  if (type == "sun_control") {
    JsonObject data = doc["data"].as<JsonObject>();
    if (data.isNull()) return;

    String command = data["command"] | "";

    if (command == "set_mode") {
      String mode = data["mode"] | "";

      if (mode == "sun_auto") {
        setSunMode(true);
        Serial.println("[SUN] auto");
      } else if (mode == "sun_manual") {
        setSunMode(false);
        Serial.println("[SUN] manual");
      }

      return;
    }

    if (command == "set_servo") {
      String servo = data["servo"] | "";
      int angle = data["angle"] | 90;

      if (servo == "vertical") {
        setSunServoVertical(angle);
      } else if (servo == "horizontal") {
        setSunServoHorizontal(angle);
      }

      Serial.print("[SUN] set_servo ");
      Serial.print(servo);
      Serial.print(" = ");
      Serial.println(angle);

      return;
    }

    return;
  }

  if (type == "error") {
    const char* msg = doc["message"] | doc["reason"] | "error";
    Serial.print("[WS] ");
    Serial.println(msg);
  }
}

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  (void)length;

  switch (type) {
    case WStype_DISCONNECTED:
      wsConnected = false;
      Serial.println("[WS] Disconnected");
      break;

    case WStype_CONNECTED:
      wsConnected = true;
      Serial.println("[WS] Connected");
      break;

    case WStype_TEXT:
      processWsMessage(String((char*)payload));
      break;

    case WStype_ERROR:
      wsConnected = false;
      Serial.println("[WS] Error");
      break;

    default:
      break;
  }
}

void initWebSocket() {
  webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
}

//WiFi / Status
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("[WiFi] Connecting");

  unsigned long startMs = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startMs < 15000) {
    Serial.print(".");
    delay(500);
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WiFi] Connected: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("[WiFi] Failed, continue offline");
  }
}

void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) return;

  unsigned long now = millis();
  if (now - lastWifiRetryMs < WIFI_RETRY_INTERVAL) return;

  lastWifiRetryMs = now;
  wsConnected = false;

  Serial.println("[WiFi] Reconnecting...");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void printStatus() {
  Serial.print("Mode=");
  Serial.print(isAutoMode ? "AUTO" : "MANUAL");

  Serial.print(" Fan=");
  Serial.print(fanOn ? "ON" : "OFF");

  Serial.print(" Pump=");
  Serial.print(pumpOn ? "ON" : "OFF");

  Serial.print(" Light=");
  Serial.print(lightOn ? "ON" : "OFF");

  Serial.print(" Mist=");
  Serial.print(mistOn ? "ON" : "OFF");

  Serial.print(" Soil=");
  Serial.print(soilMoisture);
  Serial.print("%");

  Serial.print(" SunMode=");
  Serial.print(isSunAutoMode ? "sun_auto" : "sun_manual");

  Serial.print(" LDR=");
  Serial.print(sunLdrLT);
  Serial.print(",");
  Serial.print(sunLdrRT);
  Serial.print(",");
  Serial.print(sunLdrLD);
  Serial.print(",");
  Serial.print(sunLdrRD);

  Serial.print(" ServoV=");
  Serial.print(sunServoVertical);

  Serial.print(" ServoH=");
  Serial.print(sunServoHorizontal);

  if (dhtErrorState || isnan(temperature) || isnan(humidity)) {
    Serial.println(" DHT=fail");
  } else {
    Serial.print(" T=");
    Serial.print(temperature, 1);
    Serial.print("C H=");
    Serial.print(humidity, 1);
    Serial.println("%");
  }
}

//LCD
void updateLcd() {
  lcd.setCursor(0, 0);
  if (dhtErrorState || isnan(temperature) || isnan(humidity)) {
    lcd.print("T:--.-C H:--.-% ");
  } else {
    char buf[17];
    snprintf(buf, sizeof(buf), "T:%4.1fC H:%4.1f%%", temperature, humidity);
    lcd.print(buf);
  }

  lcd.setCursor(0, 1);
  char buf2[17];
  snprintf(buf2, sizeof(buf2), "Soil:%5.1f%%       ", soilMoisture);
  lcd.print(buf2);
}

//Setup / Loop
void setup() {
  Serial.begin(9600);
  delay(1000);

  lcd.init();
  lcd.backlight();

  Serial.println();
  Serial.println("=== GREENHOUSE FULL CODE V2 - SOLAR TRACKER SAME SAMPLE ===");

  Serial.print("[BOOT] Reset reason: ");
  Serial.println(esp_reset_reason());

  Serial.print("[BOOT] Mode default: ");
  Serial.println(isAutoMode ? "AUTO" : "MANUAL");

  Serial.print("[BOOT] SunMode default: ");
  Serial.println(isSunAutoMode ? "sun_auto" : "sun_manual");

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);

  pinMode(SUN_LDR_LT_PIN, INPUT);
  pinMode(SUN_LDR_RT_PIN, INPUT);
  pinMode(SUN_LDR_LD_PIN, INPUT);
  pinMode(SUN_LDR_RD_PIN, INPUT);

  dht.begin();

  pinMode(FAN_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(MIST_PIN, OUTPUT);

  sunServoV.setPeriodHertz(50);
  sunServoH.setPeriodHertz(50);

  sunServoV.attach(SUN_SERVO_VERTICAL_PIN);
  sunServoH.attach(SUN_SERVO_HORIZONTAL_PIN);

  writeSunServos();

  updateOutputs();

  connectWiFi();
  initWebSocket();

  readSensors();
  printDhtAndSoil();
  updateLcd();

  Serial.println("[BOOT] Setup done");
}

void loop() {
  ensureWiFiConnected();

  webSocket.loop();

  checkTimers();

  unsigned long now = millis();

  if (now - lastSensorMs >= SENSOR_INTERVAL) {
    lastSensorMs = now;
    readSensors();
    updateLcd();
  }

  if (now - lastSunTrackMs >= SUN_TRACK_INTERVAL) {
    lastSunTrackMs = now;
    updateSunTracker();
  }

  if (now - lastStatusMs >= STATUS_INTERVAL) {
    lastStatusMs = now;
    printStatus();
  }

  if (wsConnected && now - lastTelemetryMs >= TELEMETRY_INTERVAL) {
    lastTelemetryMs = now;
    sendTelemetry();
  }

  delay(1);
}