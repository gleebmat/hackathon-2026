// Smart campus room sensor - Seeed XIAO ESP32S3 Sense (runs in the Velxio simulator and on the real board).
//
// Camera: raw RGB565 frames (the simulator's own JPEG output is cut off after the top third), encoded to JPEG here.
// With frame_key.h in the project (tools/make_frame_key.py), every JPEG frame (~5-10 KB) goes
// encrypted (AES-128-CTR) over MQTT to aau-hack26/rooms/<room>/frame, a few per second. The backend
// (app/vision.py) runs YOLO11n on it: people count and left items, on the website about a second later.
// Without frame_key.h the board decides presence itself with Arshia's 96x96 person model (person_model.h),
// yes/no only, ~1 s per frame in Velxio.
// Noise: PDM microphone level (approximate: silence ~30 dB, full scale ~90 dB), every loop, as JSON on
// aau-hack26/rooms/<room>/readings: {"room_id":"Z.1.04","noise_db":47.0} (+ "presence","person_score" in fallback).
// In Velxio: Camera button = your webcam, Mic button = your microphone (off = test pattern / 440 Hz tone).
// Libraries: Chirale_TensorFlowLite, PubSubClient. Files: sketch.ino + person_model.h (+ frame_key.h).
#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP_I2S.h>
#include <math.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "mbedtls/aes.h"
#include <Chirale_TensorFlowLite.h>
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "person_model.h"
#if __has_include("frame_key.h")
#include "frame_key.h"
#define SEND_FRAMES 1
#else
#define SEND_FRAMES 0
#endif

const char* ROOM_ID = "Z.1.04";
const char* MQTT_HOST = "broker.hivemq.com";   // public broker: frames are encrypted, readings are not secret
const int MQTT_PORT = 1883;
const uint32_t FRAME_EVERY_MS = 250;         // at most ~4 frames per second
const float ARRIVAL_SCORE = 0.70;            // fallback model: one frame this sure = present
const float VOTE_SCORE = 0.60;               // ... or 2 of the last 3 frames at least this sure

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

int FW = 0, FH = 0;                          // camera frame size, the biggest that fits (see startCamera)
const int IMG = 96;                          // fallback model input

I2SClass mic;
bool camOk = false, micOk = false, modelOk = false;
uint8_t* rgb = nullptr;                      // frame as 3 bytes per pixel (BGR) for the fallback model (PSRAM)
uint8_t* sealed = nullptr;                   // encrypted frame: 16-byte counter block + JPEG (PSRAM)
const size_t SEALED_MAX = 64 * 1024;

const int ARENA_SIZE = 160 * 1024;
uint8_t* arena = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
bool votes[3] = {false, false, false};
int voteIdx = 0;

bool startCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM; c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_RGB565;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_DRAM;      // the simulator can't put frame buffers in PSRAM yet
  c.grab_mode = CAMERA_GRAB_LATEST;
  rgb = (uint8_t*)heap_caps_malloc(320 * 240 * 3, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  sealed = (uint8_t*)heap_caps_malloc(SEALED_MAX, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!rgb || !sealed) return false;
  // the raw frame must fit in internal RAM: take the biggest size that does
  const framesize_t sizes[] = {FRAMESIZE_QVGA, FRAMESIZE_HQVGA, FRAMESIZE_QQVGA};
  const int widths[] = {320, 240, 160}, heights[] = {240, 176, 120};
  for (int i = 0; i < 3; i++) {
    c.frame_size = sizes[i];
    if (esp_camera_init(&c) == ESP_OK) {
      FW = widths[i];
      FH = heights[i];
      return true;
    }
    esp_camera_deinit();
  }
  return false;
}

bool startModel() {
  const tflite::Model* model = tflite::GetModel(g_person_model);
  arena = (uint8_t*)heap_caps_malloc(ARENA_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!arena) return false;
  static tflite::MicroMutableOpResolver<6> ops;
  ops.AddAveragePool2D();
  ops.AddConv2D();
  ops.AddDepthwiseConv2D();
  ops.AddFullyConnected();
  ops.AddReshape();
  ops.AddSoftmax();
  static tflite::MicroInterpreter interp(model, ops, arena, ARENA_SIZE);
  if (interp.AllocateTensors() != kTfLiteOk) return false;
  interpreter = &interp;
  return true;
}

// Fallback model score for a frame: centre 240x240 square averaged down to 96x96 (int8 RGB, pixel - 128).
float personScore(camera_fb_t* fb) {
  if (!fmt2rgb888(fb->buf, fb->len, fb->format, rgb)) return -1;
  int8_t* in = interpreter->input(0)->data.int8;
  const int left = (FW - FH) / 2;
  for (int y = 0; y < IMG; y++) {
    const int y0 = y * FH / IMG, y1 = (y + 1) * FH / IMG;
    for (int x = 0; x < IMG; x++) {
      const int x0 = left + x * FH / IMG, x1 = left + (x + 1) * FH / IMG;
      int s[3] = {0, 0, 0}, n = 0;
      for (int yy = y0; yy < y1; yy++)
        for (int xx = x0; xx < x1; xx++, n++) {
          const uint8_t* p = rgb + 3 * (yy * FW + xx);   // decoder writes blue, green, red
          s[0] += p[2]; s[1] += p[1]; s[2] += p[0];
        }
      for (int c = 0; c < 3; c++) in[3 * (y * IMG + x) + c] = (int8_t)(s[c] / n - 128);
    }
  }
  if (interpreter->Invoke() != kTfLiteOk) return -1;
  TfLiteTensor* out = interpreter->output(0);
  return (out->data.int8[1] - out->params.zero_point) * out->params.scale;   // index 1 = person
}

// Approximate sound level: RMS of ~32 ms of 16 kHz audio.
float noiseDb() {
  double sum = 0;
  int n = 0;
  for (int i = 0; i < 512; i++) {
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

WiFiClient net;
PubSubClient mqtt(net);
String readingsTopic, frameTopic;

bool mqttReady() {
  if (WiFi.status() != WL_CONNECTED) return false;
  if (mqtt.connected()) return true;
  String id = String("xiao-") + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (mqtt.connect(id.c_str())) return true;
  Serial.printf("MQTT connect failed (%d)\n", mqtt.state());
  return false;
}

#if SEND_FRAMES
// Encodes the frame as JPEG, encrypts it (AES-128-CTR, fresh random counter block) and streams it to the frame topic.
bool sendFrame(camera_fb_t* fb, size_t& jpgLen) {
  uint8_t* jpg = nullptr;
  jpgLen = 0;
  if (!mqttReady() || !frame2jpg(fb, 80, &jpg, &jpgLen)) return false;
  if (jpgLen + 16 > SEALED_MAX) {
    free(jpg);
    return false;
  }
  uint8_t nonce[16], block[16];
  esp_fill_random(nonce, 16);
  memcpy(sealed, nonce, 16);
  mbedtls_aes_context aes;
  mbedtls_aes_init(&aes);
  mbedtls_aes_setkey_enc(&aes, FRAME_KEY, 128);
  size_t off = 0;
  mbedtls_aes_crypt_ctr(&aes, jpgLen, &off, nonce, block, jpg, sealed + 16);
  mbedtls_aes_free(&aes);
  free(jpg);
  const size_t n = jpgLen + 16;
  return mqtt.beginPublish(frameTopic.c_str(), n, false) && mqtt.write(sealed, n) == n && mqtt.endPublish();
}
#endif

void setup() {
  Serial.begin(115200);
  delay(300);
  camOk = startCamera();
  if (camOk) Serial.printf("CAM OK (%dx%d)\n", FW, FH);
  else Serial.println("CAM FAILED");
  if (!SEND_FRAMES) {
    modelOk = startModel();
    Serial.println(modelOk ? "MODEL OK (on-board presence)" : "MODEL FAILED");
  } else {
    Serial.println("FRAMES ON: people and items are detected by the backend");
  }
  mic.setPinsPdmRx(42, 41);
  micOk = mic.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  Serial.println(micOk ? "MIC OK" : "MIC FAILED");
  WiFi.mode(WIFI_STA);
  WiFi.begin("Velxio-GUEST");   // Velxio's built-in open network; use your own SSID on the real board
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  Serial.println(WiFi.status() == WL_CONNECTED ? "WIFI OK" : "WIFI FAILED");
  readingsTopic = String("aau-hack26/rooms/") + ROOM_ID + "/readings";
  frameTopic = String("aau-hack26/rooms/") + ROOM_ID + "/frame";
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

uint32_t lastFrame = 0, sent = 0, failed = 0;

void loop() {
  if (millis() - lastFrame < FRAME_EVERY_MS) delay(FRAME_EVERY_MS - (millis() - lastFrame));
  lastFrame = millis();
  String json = String("{\"room_id\":\"") + ROOM_ID + "\"";
  float db = micOk ? noiseDb() : -1;
  if (db >= 0) json += ",\"noise_db\":" + String(db, 1);

  camera_fb_t* fb = camOk ? esp_camera_fb_get() : nullptr;
  if (fb) {
#if SEND_FRAMES
    const uint32_t t0 = millis();
    size_t jpgLen;
    const bool ok = sendFrame(fb, jpgLen);
    ok ? sent++ : failed++;
    Serial.printf("frame %u bytes -> %s (%lums, %lu sent, %lu failed)\n", (unsigned)jpgLen, ok ? "sent" : "FAILED",
                  (unsigned long)(millis() - t0), (unsigned long)sent, (unsigned long)failed);
#else
    if (modelOk) {
      const float score = personScore(fb);
      if (score >= 0) {
        votes[voteIdx++ % 3] = score >= VOTE_SCORE;
        const bool present = score >= ARRIVAL_SCORE || (votes[0] + votes[1] + votes[2]) >= 2;
        json += ",\"person_score\":" + String(score, 2) + ",\"presence\":" + (present ? "true" : "false");
      }
    }
#endif
    esp_camera_fb_return(fb);
  } else if (camOk) {
    Serial.println("no camera frame (is the Camera button on?)");
  }
  json += "}";
  if (mqttReady()) mqtt.publish(readingsTopic.c_str(), json.c_str());
  Serial.println(json);
  mqtt.loop();
}
