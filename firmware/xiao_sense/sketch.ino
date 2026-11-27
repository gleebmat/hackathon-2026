// Smart campus room sensor - Seeed XIAO ESP32S3 Sense (runs in the Velxio simulator and on the real board).
//
// Every 2 s it measures the room and prints one line on Serial; with BACKEND set it also POSTs it as JSON to
// <BACKEND>/api/readings, the same contract as the Infineon bridge:
//   {"room_id": "Z.1.04", "noise_db": 47.0, "presence": true, "left_items": 0}
//
// Step 1 (this file): camera frames (96x96 grayscale) and microphone level. Presence and left items come next.
// In Velxio: Camera button = your webcam, Mic button = your microphone (off = test pattern / 440 Hz tone).
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP_I2S.h>
#include <math.h>
#include "esp_camera.h"

const char* ROOM_ID = "Z.1.04";
const char* BACKEND = "";          // e.g. "https://<tunnel>.trycloudflare.com"; empty = Serial only
const uint32_t PERIOD_MS = 2000;

// Seeed's camera pin map for the Sense board (same as Velxio's camera example)
#define XCLK_GPIO_NUM 10
#define SIOD_GPIO_NUM 40
#define SIOC_GPIO_NUM 39
#define Y9_GPIO_NUM 48
#define Y8_GPIO_NUM 11
#define Y7_GPIO_NUM 12
#define Y6_GPIO_NUM 14
#define Y5_GPIO_NUM 16
#define Y4_GPIO_NUM 18
#define Y3_GPIO_NUM 17
#define Y2_GPIO_NUM 15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM 47
#define PCLK_GPIO_NUM 13

I2SClass mic;
bool camOk = false, micOk = false;

bool startCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM; c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_GRAYSCALE;   // the person model wants 96x96 pixels
  c.frame_size = FRAMESIZE_96X96;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_DRAM;      // the simulator can't put frame buffers in PSRAM yet
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  return esp_camera_init(&c) == ESP_OK;
}

// Approximate sound level: RMS of ~1/8 s of 16 kHz audio, mapped so silence ~30 dB and full scale ~90 dB.
float noiseDb() {
  double sum = 0;
  int n = 0;
  for (int i = 0; i < 2000; i++) {
    int s = mic.read();
    if (s == 0 || s == -1) continue;
    int16_t v = (int16_t)s;
    sum += (double)v * v;
    n++;
  }
  if (n == 0) return -1;
  double dbfs = 20.0 * log10(sqrt(sum / n) / 32768.0 + 1e-9);
  return constrain(90.0 + dbfs, 30.0, 95.0);
}

void post(const String& json) {
  if (!BACKEND[0] || WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String(BACKEND) + "/api/readings");
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(json);
  http.end();
  Serial.printf("POST -> %d\n", code);
}

void setup() {
  Serial.begin(115200);
  delay(300);
  camOk = startCamera();
  Serial.println(camOk ? "CAM OK" : "CAM FAILED");
  mic.setPinsPdmRx(42, 41);
  micOk = mic.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  Serial.println(micOk ? "MIC OK" : "MIC FAILED");
  if (BACKEND[0]) {
    WiFi.mode(WIFI_STA);
    WiFi.begin("Velxio-GUEST");   // Velxio's built-in open network; use your own SSID on the real board
    for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
    Serial.println(WiFi.status() == WL_CONNECTED ? "WIFI OK" : "WIFI FAILED");
  }
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last < PERIOD_MS) return;
  last = millis();

  float db = micOk ? noiseDb() : -1;
  int brightness = -1;
  uint32_t t0 = millis();
  camera_fb_t* fb = camOk ? esp_camera_fb_get() : nullptr;
  if (fb) {
    uint32_t sum = 0;
    for (size_t i = 0; i < fb->len; i++) sum += fb->buf[i];
    brightness = fb->len ? sum / fb->len : -1;
    Serial.printf("frame %ux%u fmt=%d len=%u grab=%lums\n", fb->width, fb->height, fb->format, (unsigned)fb->len,
                  (unsigned long)(millis() - t0));
    esp_camera_fb_return(fb);
  }

  String json = String("{\"room_id\":\"") + ROOM_ID + "\"";
  if (db >= 0) json += ",\"noise_db\":" + String(db, 1);
  json += "}";
  Serial.printf("READING %s brightness=%d\n", json.c_str(), brightness);
  post(json);
}
