/*
  RobotEva - ESP32 servo controller via MQTT

  Subscribes:
    <TOPIC_BASE>/set
      payload: "<servo_id>,<angle>"
      example: "0,90"

  Publishes (optional):
    <TOPIC_BASE>/status  -> "online" / "offline"

  Notes:
  - ESP32 generates 50Hz servo PWM directly using LEDC (no PCA9685).
  - Power servos from external 5V/6V (do NOT power servos from ESP32 3.3V).
  - Common ground: ESP32 GND <-> servo PSU GND.
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <HardwareSerial.h>

// Arduino-ESP32 core version helpers (core 3.x changed LEDC API).
#if __has_include(<esp_arduino_version.h>)
  #include <esp_arduino_version.h>
#endif

#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  // Arduino-ESP32 v3+: LEDC is pin-based (ledcAttach/ledcWrite(pin,...))
  #define EVA_LEDC_PIN_API 1
#else
  // Arduino-ESP32 v2.x: LEDC is channel-based (ledcSetup/ledcAttachPin/ledcWrite(channel,...))
  #define EVA_LEDC_PIN_API 0
#endif

// ===== Logging =====
// Set to 0 to silence Serial logs.
#define ENABLE_SERIAL_LOGS 1

#if ENABLE_SERIAL_LOGS
  #define LOGI(msg) do { Serial.print("[I] "); Serial.println(msg); } while (0)
  #define LOGW(msg) do { Serial.print("[W] "); Serial.println(msg); } while (0)
  #define LOGE(msg) do { Serial.print("[E] "); Serial.println(msg); } while (0)
#else
  #define LOGI(msg) do {} while (0)
  #define LOGW(msg) do {} while (0)
  #define LOGE(msg) do {} while (0)
#endif

// ====== USER CONFIG ======
static const char* WIFI_SSID     = "YOUR_WIFI_SSID";
static const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

static const char* MQTT_HOST = "212.67.8.211"; // MQTT broker IP/host
static const uint16_t MQTT_PORT = 1883;
static const char* MQTT_USER = "";     // optional
static const char* MQTT_PASS = "";     // optional

static const char* TOPIC_BASE = "robot_eva/servos";

// Servo PWM (LEDC)
static const uint16_t SERVO_FREQ_HZ = 50;
static const uint8_t LEDC_RES_BITS = 16; // 0..65535 duty range

// Map servo_id (0..15) -> ESP32 GPIO pin.
// Set to -1 to disable a channel.
// IMPORTANT: pick pins that support output on your ESP32 board and are not strapping pins (avoid 0/2/4/5/12/15 unless you know what you're doing).
static const int SERVO_PINS[16] = {
  13, 14, 25, 26,      // 0..3 (4 servos)
  -1,                  // 4
  -1, -1, -1, -1, -1,  // 5..9
  -1, -1, -1, -1, -1,  // 10..14
  -1                   // 15
};

// Pulse width calibration (typical servos: 500..2500 us)
static const int SERVO_MIN_US = 500;
static const int SERVO_MAX_US = 2500;

// ====== END USER CONFIG ======

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

String topicSet;
String topicStatus;

static bool isServoEnabled(int id) {
  if (id < 0 || id >= 16) return false;
  return SERVO_PINS[id] >= 0;
}

static int angleToUs(float angle) {
  float a = angle;
  if (a < 0) a = 0;
  if (a > 180) a = 180;
  const float us = (SERVO_MIN_US + (a / 180.0f) * (SERVO_MAX_US - SERVO_MIN_US));
  return (int)(us + 0.5f);
}

static uint32_t usToDuty(int us) {
  // duty range depends on resolution; at 50Hz period = 20000us
  const uint32_t maxDuty = ((uint32_t)1 << LEDC_RES_BITS) - 1;
  uint32_t d = (uint32_t)((((uint64_t)us) * maxDuty) / 20000ULL);
  if (d > maxDuty) d = maxDuty;
  return d;
}

static bool servoWriteAngle(int id, float angle, uint32_t *outDuty, int *outUs) {
  if (!isServoEnabled(id)) return false;
  const int pin = SERVO_PINS[id];
  const int us = angleToUs(angle);
  const uint32_t duty = usToDuty(us);
#if EVA_LEDC_PIN_API
  ledcWrite((uint8_t)pin, duty);
#else
  ledcWrite((uint8_t)id, duty);
#endif
  if (outDuty) *outDuty = duty;
  if (outUs) *outUs = us;
  (void)pin;
  return true;
}

static void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  // Don't block forever; keep trying in loop()
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < 15000) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    LOGI(String("WiFi connected. SSID=") + WIFI_SSID + " IP=" + WiFi.localIP().toString());
  } else {
    LOGW(String("WiFi not connected yet. status=") + (int)WiFi.status());
  }
}

static void publishStatus(const char* status) {
  mqttClient.publish(topicStatus.c_str(), status, true /*retain*/);
  LOGI(String("MQTT TX status=") + status + " topic=" + topicStatus);
}

static void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Expect: "<id>,<angle>"
  // Minimal parsing without extra JSON libs.
  if (length == 0) return;

  // Copy to a null-terminated buffer
  static char buf[64];
  unsigned int n = (length < sizeof(buf) - 1) ? length : (sizeof(buf) - 1);
  memcpy(buf, payload, n);
  buf[n] = '\0';

  LOGI(String("MQTT RX topic=") + topic + " payload=" + buf);

  // Find comma
  char* comma = strchr(buf, ',');
  if (!comma) {
    LOGW("Bad payload (no comma). Expected: <id>,<angle>");
    return;
  }
  *comma = '\0';
  const int id = atoi(buf);
  const float angle = atof(comma + 1);

  if (id < 0 || id >= 16) {
    LOGW(String("Bad servo id: ") + id + " (expected 0..15)");
    return;
  }

  if (!isServoEnabled(id)) {
    LOGW(String("Servo id=") + id + " is disabled (SERVO_PINS[" + String(id) + "] = -1).");
    return;
  }

  uint32_t duty = 0;
  int us = 0;
  const bool ok = servoWriteAngle(id, angle, &duty, &us);
  if (ok) {
    LOGI(String("Servo id=") + id + " pin=" + SERVO_PINS[id] + " angle=" + String(angle, 1) + " us=" + us + " duty=" + duty + " (LEDC OK)");
  } else {
    LOGE(String("Servo id=") + id + " FAILED to write (LEDC)");
  }
}

static void connectMQTT() {
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  while (!mqttClient.connected()) {
    const String clientId = String("eva-esp32-servo-") + String((uint32_t)ESP.getEfuseMac(), HEX);
    bool ok;

    LOGI(String("MQTT connecting to ") + MQTT_HOST + ":" + MQTT_PORT + " clientId=" + clientId);

    if (strlen(MQTT_USER) > 0) {
      ok = mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS, topicStatus.c_str(), 1, true, "offline");
    } else {
      ok = mqttClient.connect(clientId.c_str(), nullptr, nullptr, topicStatus.c_str(), 1, true, "offline");
    }
    if (!ok) {
      LOGW(String("MQTT connect failed. state=") + mqttClient.state() + " retrying...");
      delay(1000);
    }
  }

  publishStatus("online");
  mqttClient.subscribe(topicSet.c_str(), 0);
  LOGI(String("MQTT connected. subscribed to ") + topicSet);
}

void setup() {
  #if ENABLE_SERIAL_LOGS
    Serial.begin(115200);
    delay(200);
    LOGI("Boot: ESP32 Servo MQTT Controller");
  #endif

  topicSet = String(TOPIC_BASE) + "/set";
  topicStatus = String(TOPIC_BASE) + "/status";

  connectWiFi();

  // Init LEDC channels for enabled servos
  LOGI(String("Init LEDC: freq=") + SERVO_FREQ_HZ + "Hz res=" + LEDC_RES_BITS + "bits");
  for (int id = 0; id < 16; id++) {
    const int pin = SERVO_PINS[id];
    if (pin < 0) continue;
#if EVA_LEDC_PIN_API
    const bool attached = ledcAttach((uint8_t)pin, SERVO_FREQ_HZ, LEDC_RES_BITS);
    if (!attached) {
      LOGE(String("LEDC attach FAILED for servo id=") + id + " pin=" + pin);
      continue;
    }
#else
    ledcSetup((uint8_t)id, SERVO_FREQ_HZ, LEDC_RES_BITS);
    ledcAttachPin((uint8_t)pin, (uint8_t)id);
#endif
    uint32_t duty = 0;
    int us = 0;
    const bool ok = servoWriteAngle(id, 90.0f, &duty, &us);
    if (ok) {
      LOGI(String("Init servo id=") + id + " pin=" + pin + " angle=90.0 us=" + us + " duty=" + duty);
    } else {
      LOGE(String("Init servo id=") + id + " pin=" + pin + " FAILED");
    }
  }

  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
}


