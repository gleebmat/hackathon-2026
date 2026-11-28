// Smart campus room sensor - Seeed XIAO ESP32S3 Sense (runs in the Velxio simulator and on the real board).
//
// At most twice per second it measures the room on the board itself and publishes one JSON reading over MQTT to the topic
// aau-hack26/rooms/<room>/readings on a public broker; the backend (app/mqtt_feed.py) subscribes to it:
//   {"room_id":"Z.1.04","noise_db":47.0,"presence":true,"person_score":0.91,"left_items":0}
//  - presence: Arshia's 96x96 person model (models/vww_96_int8.tflite, TensorFlow Lite Micro), majority of the
//    last 3 frames so one odd frame doesn't flip it
//  - noise_db: PDM microphone level (approximate: silence ~30 dB, full scale ~90 dB)
//  - left_items: while the room is empty and still, the board keeps a snapshot of it; after people leave, the frame
//    is compared with that snapshot (camera nudges and lighting changes compensated) and changes that stay in place
//    for a few seconds count as items, touching areas as one item
// In Velxio: Camera button = your webcam, Mic button = your microphone (off = test pattern / 440 Hz tone).
// Libraries: Chirale_TensorFlowLite (builds TFLM from source, works on arduino-esp32 3.x), PubSubClient.
// Files: sketch.ino + person_model.h.
#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP_I2S.h>
#include <math.h>
#include "esp_camera.h"
#include <Chirale_TensorFlowLite.h>
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "person_model.h"

const char* ROOM_ID = "Z.1.04";
const char* MQTT_HOST = "broker.hivemq.com";   // public broker: fine for a demo, use your own for real data
const int MQTT_PORT = 1883;
const uint32_t PERIOD_MS = 500;
const float PERSON_THRESHOLD = 0.60;

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

const int IMG = 96;                       // model input and camera frame: 96x96
const int CELL = 4, GRID = IMG / CELL;    // left-item check on a 24x24 grid of 4x4-pixel cells
const int EDGE_DIFF = 14;                 // a cell changed if its contrast to its neighbours moved this much
const int CELL_DIFF = 45;                 // ... or its brightness moved this much (after the global exposure shift)
const int MIN_ITEM_CELLS = 3;             // smaller blobs are webcam noise (JPEG artefacts)
const float MAX_CHANGED = 0.30;           // more than 30% changed = view or lights changed, not items: new snapshot
const int MAX_SHIFT = 3;                  // camera nudged by up to 3 px: compensated
const int STEADY_CHECKS = 3;              // a change must stay in place this many checks in a row to be an item
const int STILL_DIFF = 8;                 // scene counts as still if no cell's contrast moved more than this
const float EMPTY_SCORE = 0.45;           // the snapshot is only taken from frames that clearly show nobody
const int CALM_FOR_SNAPSHOT = 3;          // empty, calm checks in a row before the snapshot is refreshed
const int CLEAN_TO_RESET = 5;             // after people left: clean checks in a row before snapshots resume

I2SClass mic;
bool camOk = false, micOk = false, modelOk = false;

const int ARENA_SIZE = 160 * 1024;
uint8_t* arena = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;

uint8_t gray[IMG * IMG];                  // current frame, grayscale
uint8_t baseGray[IMG * IMG];              // empty-room snapshot
bool haveBaseline = false;
bool occupiedSinceSnapshot = false;       // people were seen after the snapshot: compare, don't refresh
int16_t edges[GRID * GRID], prevEdges[GRID * GRID];
uint8_t steady[GRID * GRID];              // checks in a row each cell has been changed
int emptyStreak = 0, calmStreak = 0, cleanStreak = 0, leftItems = 0;
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
  c.pixel_format = PIXFORMAT_RGB565;      // colour: the person model takes 96x96x3
  c.frame_size = FRAMESIZE_96X96;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_DRAM;      // the simulator can't put frame buffers in PSRAM yet
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  return esp_camera_init(&c) == ESP_OK;
}

bool startModel() {
  const tflite::Model* model = tflite::GetModel(g_person_model);
  arena = (uint8_t*)heap_caps_malloc(ARENA_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!arena) arena = (uint8_t*)heap_caps_malloc(ARENA_SIZE, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
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
  Serial.printf("model arena used: %u bytes\n", (unsigned)interp.arena_used_bytes());
  return true;
}

// Fills the model input (int8 RGB, pixel - 128) and the grayscale copy from one RGB565 frame.
void prepare(const camera_fb_t* fb) {
  int8_t* in = interpreter ? interpreter->input(0)->data.int8 : nullptr;
  for (int i = 0; i < IMG * IMG; i++) {
    uint16_t p = (fb->buf[2 * i] << 8) | fb->buf[2 * i + 1];
    uint8_t r = (p >> 11) << 3, g = ((p >> 5) & 0x3F) << 2, b = (p & 0x1F) << 3;
    gray[i] = (r * 77 + g * 150 + b * 29) >> 8;
    if (in) {
      in[3 * i] = (int8_t)(r - 128);
      in[3 * i + 1] = (int8_t)(g - 128);
      in[3 * i + 2] = (int8_t)(b - 128);
    }
  }
}

float personScore() {
  if (interpreter->Invoke() != kTfLiteOk) return -1;
  TfLiteTensor* out = interpreter->output(0);
  return (out->data.int8[1] - out->params.zero_point) * out->params.scale;   // index 1 = person
}

// Mean brightness of each 4x4 cell, read from img moved by (dx, dy) pixels (edges clamped).
void cellMeans(const uint8_t* img, int dx, int dy, uint8_t* dst) {
  for (int gy = 0; gy < GRID; gy++)
    for (int gx = 0; gx < GRID; gx++) {
      int sum = 0;
      for (int y = 0; y < CELL; y++)
        for (int x = 0; x < CELL; x++) {
          int sx = constrain(gx * CELL + x + dx, 0, IMG - 1), sy = constrain(gy * CELL + y + dy, 0, IMG - 1);
          sum += img[sy * IMG + sx];
        }
      dst[gy * GRID + gx] = sum / (CELL * CELL);
    }
}

// Contrast of each cell to its 3x3 neighbourhood. Smooth lighting changes (exposure, daylight, soft shadows)
// barely move it; an object's outline does.
void cellEdges(const uint8_t* cells, int16_t* dst) {
  for (int y = 0; y < GRID; y++)
    for (int x = 0; x < GRID; x++) {
      int sum = 0, n = 0;
      for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++) {
          int nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= GRID || ny >= GRID) continue;
          sum += cells[ny * GRID + nx];
          n++;
        }
      dst[y * GRID + x] = cells[y * GRID + x] - sum / n;
    }
}

// Camera offset (pixels) that best lines the frame up with the snapshot, so a nudged camera is not an item.
// Compares brightness steps between neighbouring pixels, which exposure changes don't affect.
void bestShift(int& bx, int& by) {
  long best = -1;
  for (int dy = -MAX_SHIFT; dy <= MAX_SHIFT; dy++)
    for (int dx = -MAX_SHIFT; dx <= MAX_SHIFT; dx++) {
      long cost = 0;
      for (int y = MAX_SHIFT; y < IMG - MAX_SHIFT - 1; y += 2)
        for (int x = MAX_SHIFT; x < IMG - MAX_SHIFT - 1; x += 2) {
          int c = y * IMG + x, b = (y + dy) * IMG + x + dx;
          cost += abs((gray[c + 1] - gray[c]) - (baseGray[b + 1] - baseGray[b])) +
                  abs((gray[c + IMG] - gray[c]) - (baseGray[b + IMG] - baseGray[b]));
        }
      if (best < 0 || cost < best) { best = cost; bx = dx; by = dy; }
    }
}

void takeSnapshot() {
  memcpy(baseGray, gray, sizeof baseGray);
  memset(steady, 0, sizeof steady);
  if (!haveBaseline) Serial.println("Empty-room baseline ready");
  haveBaseline = true;
}

// Items left behind: cells that differ from the empty-room snapshot and have stayed that way for STEADY_CHECKS
// checks (a person walking out or flickering light moves), grouped into blobs. One object usually shows up as
// several fragments, so every changed cell is grown by one cell first and fragments that then touch count as one
// item. Returns -1 when a large part of the picture changed (camera moved, lights switched): take a new snapshot.
int countLeftItems() {
  static uint8_t cur[GRID * GRID], base[GRID * GRID], mask[GRID * GRID], grown[GRID * GRID];
  static int16_t baseEdges[GRID * GRID];
  static uint16_t stack_[GRID * GRID];
  int sx = 0, sy = 0;
  bestShift(sx, sy);
  cellMeans(gray, 0, 0, cur);
  cellMeans(baseGray, sx, sy, base);
  cellEdges(base, baseEdges);
  long shift = 0;                          // auto-exposure brightens or darkens the whole frame: ignore that
  for (int i = 0; i < GRID * GRID; i++) shift += (int)cur[i] - (int)base[i];
  shift /= GRID * GRID;
  int changed = 0;
  for (int i = 0; i < GRID * GRID; i++) {
    bool diff = abs(edges[i] - baseEdges[i]) > EDGE_DIFF || abs((int)cur[i] - (int)base[i] - (int)shift) > CELL_DIFF;
    changed += diff;
    steady[i] = diff ? min(steady[i] + 1, 255) : 0;
    mask[i] = steady[i] >= STEADY_CHECKS;
  }
  if (changed > MAX_CHANGED * GRID * GRID) return -1;
  for (int y = 0; y < GRID; y++)
    for (int x = 0; x < GRID; x++) {
      uint8_t g = 0;
      for (int dy = -1; dy <= 1 && !g; dy++)
        for (int dx = -1; dx <= 1 && !g; dx++) {
          int nx = x + dx, ny = y + dy;
          g = nx >= 0 && ny >= 0 && nx < GRID && ny < GRID && mask[ny * GRID + nx];
        }
      grown[y * GRID + x] = g;
    }
  int items = 0;
  for (int i = 0; i < GRID * GRID; i++) {
    if (!grown[i]) continue;
    int top = 0, size = 0;                 // size = really changed cells inside the blob
    stack_[top++] = i;
    grown[i] = 0;
    while (top) {
      int p = stack_[--top], px = p % GRID, py = p / GRID;
      size += mask[p];
      for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++) {
          int nx = px + dx, ny = py + dy;
          if (nx < 0 || ny < 0 || nx >= GRID || ny >= GRID || !grown[ny * GRID + nx]) continue;
          grown[ny * GRID + nx] = 0;
          stack_[top++] = ny * GRID + nx;
        }
    }
    if (size >= MIN_ITEM_CELLS) items++;
  }
  if (items) Serial.printf("left-item check: %d item(s), %d cells changed, camera shift %d,%d px\n", items, changed, sx, sy);
  return items;
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
String topic;

void publish(const String& json) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (!mqtt.connected()) {
    String id = String("xiao-") + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (!mqtt.connect(id.c_str())) {
      Serial.printf("MQTT connect failed (%d)\n", mqtt.state());
      return;
    }
  }
  bool ok = mqtt.publish(topic.c_str(), json.c_str());
  Serial.printf("MQTT %s -> %s\n", topic.c_str(), ok ? "sent" : "FAILED");
}

void setup() {
  Serial.begin(115200);
  delay(300);
  camOk = startCamera();
  Serial.println(camOk ? "CAM OK" : "CAM FAILED");
  modelOk = startModel();
  Serial.println(modelOk ? "MODEL OK" : "MODEL FAILED");
  mic.setPinsPdmRx(42, 41);
  micOk = mic.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  Serial.println(micOk ? "MIC OK" : "MIC FAILED");
  WiFi.mode(WIFI_STA);
  WiFi.begin("Velxio-GUEST");   // Velxio's built-in open network; use your own SSID on the real board
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  Serial.println(WiFi.status() == WL_CONNECTED ? "WIFI OK" : "WIFI FAILED");
  topic = String("aau-hack26/rooms/") + ROOM_ID + "/readings";
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last < PERIOD_MS) return;
  last = millis();

  String json = String("{\"room_id\":\"") + ROOM_ID + "\"";
  float db = micOk ? noiseDb() : -1;
  if (db >= 0) json += ",\"noise_db\":" + String(db, 1);

  camera_fb_t* fb = camOk ? esp_camera_fb_get() : nullptr;
  if (fb && modelOk) {
    prepare(fb);
    esp_camera_fb_return(fb);
    uint32_t t0 = millis();
    float score = personScore();
    uint32_t ms = millis() - t0;
    if (score < 0) {
      Serial.println("Inference failed; occupancy unknown");
      json += "}";
      publish(json);
      mqtt.loop();
      return;
    }
    votes[voteIdx++ % 3] = score >= PERSON_THRESHOLD;
    bool present = score >= 0.85f || (votes[0] + votes[1] + votes[2]) >= 2;

    static uint8_t cells[GRID * GRID];
    memcpy(prevEdges, edges, sizeof edges);
    cellMeans(gray, 0, 0, cells);
    cellEdges(cells, edges);
    int motion = 0;                        // largest contrast change since the last check
    for (int i = 0; i < GRID * GRID; i++) motion = max(motion, abs(edges[i] - prevEdges[i]));

    if (present) {
      if (haveBaseline) occupiedSinceSnapshot = true;
      emptyStreak = calmStreak = cleanStreak = 0;
      leftItems = 0;
      memset(steady, 0, sizeof steady);
    } else {
      emptyStreak++;
      calmStreak = (score < EMPTY_SCORE && motion <= STILL_DIFF) ? calmStreak + 1 : 0;
      if (!occupiedSinceSnapshot) {
        // nobody has been here since the snapshot: keep it fresh (daylight, moved chairs) while the room is calm
        if (calmStreak >= CALM_FOR_SNAPSHOT) takeSnapshot();
      } else if (emptyStreak >= 2) {
        int k = countLeftItems();
        if (k < 0) {                       // view or lighting changed: new snapshot
          takeSnapshot();
          k = 0;
        }
        leftItems = k;
        cleanStreak = k == 0 ? cleanStreak + 1 : 0;
        if (cleanStreak >= CLEAN_TO_RESET) occupiedSinceSnapshot = false;
      }
    }
    json += ",\"presence\":" + String(present ? "true" : "false");
    json += ",\"person_score\":" + String(score, 2);
    json += ",\"left_items\":" + String(leftItems);
    Serial.printf("person=%.2f (%lums) present=%d left=%d\n", score, (unsigned long)ms, present, leftItems);
  } else if (fb) {
    esp_camera_fb_return(fb);
  }
  json += "}";
  Serial.println(json);
  publish(json);
  mqtt.loop();
}
