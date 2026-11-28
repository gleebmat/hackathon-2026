// Smart campus room sensor - Seeed XIAO ESP32S3 Sense (runs in the Velxio simulator and on the real board).
//
// Once per camera frame it publishes one JSON reading over MQTT to aau-hack26/rooms/<room>/readings on a public
// broker; the backend (app/mqtt_feed.py) subscribes to it:
//   {"room_id":"Z.1.04","noise_db":47.0,"presence":true,"person_score":0.91,"people":2,"left_items":0}
//
// Two models, both TensorFlow Lite Micro int8, both on the board, working together:
//  - fast (every frame, ~1 s in Velxio): Arshia's 96x96 person model (models/vww_96_int8.tflite in
//    person_model.h) on the whole frame. It only reports ARRIVALS quickly ("someone just came in").
//  - accurate (in a loop on the second core, ~1 min per run in Velxio, a few seconds on a real board): Seeed's
//    Swift-YOLO COCO detector, 320x320, 80 classes (models/coco_320_int8.tflite in items_model.h), on the sharp
//    320x240 camera frame (letterboxed, not upscaled). One run gives the people count (class "person") and the
//    forgettable things in view (bags, phones, bottles, laptops, books, ...).
// Presence: the accurate detector decides. Once it has seen people, the room stays occupied until one of its runs
// sees nobody; the fast model can add an arrival in between but can never declare the room empty. So a person
// standing still doesn't flicker to "nobody".
// Left items: items counted while the room was empty (and nobody came since) are the room's own baseline; after
// people were there, a run without people that sees MORE of these things than the baseline reports the extra ones.
// Noise: PDM microphone level (approximate: silence ~30 dB, full scale ~90 dB).
// Serial commands (Velxio serial monitor, type and press Send): status, items, snapshot (what is visible now belongs
// to the room), bgr (flip the camera's red/blue order if colours look wrong).
// In Velxio: Camera button = your webcam, Mic button = your microphone (off = test pattern / 440 Hz tone).
// Libraries: Chirale_TensorFlowLite, PubSubClient. Files: sketch.ino + person_model.h + items_model.h.
#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP_I2S.h>
#include <math.h>
#include "esp_camera.h"
#include "img_converters.h"
#include <Chirale_TensorFlowLite.h>
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "person_model.h"
#include "items_model.h"
#if __has_include("miniz.h")                 // the ROM decompressor's header moved between ESP-IDF versions
#include "miniz.h"
#elif __has_include("rom/miniz.h")
#include "rom/miniz.h"
#else
#include "esp32s3/rom/miniz.h"
#endif

const char* ROOM_ID = "Z.1.04";
const char* MQTT_HOST = "broker.hivemq.com";   // public broker: fine for a demo, use your own for real data
const int MQTT_PORT = 1883;
const float ARRIVAL_SCORE = 0.70;            // fast model: one frame this sure = someone arrived
const float ARRIVAL_VOTE = 0.60;             // ... or 2 of the last 3 frames at least this sure
const float DETECT_SCORE = 0.30;             // accurate detector: objectness x class score that counts
const uint32_t RESULT_FRESH_MS = 300000;     // older detector results are not used

// COCO classes the detector counts: person first, then things people forget (index in the model's 80 classes).
struct DetClass { int id; const char* name; };
const DetClass CLASSES[] = {{0, "person"}, {24, "backpack"}, {25, "umbrella"}, {26, "handbag"}, {28, "suitcase"},
                            {39, "bottle"}, {41, "cup"}, {63, "laptop"}, {67, "cell phone"}, {73, "book"}};
const int N_CLASSES = sizeof(CLASSES) / sizeof(CLASSES[0]);

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

const int FW = 320, FH = 240;                // camera frame (QVGA)
const int IMG = 96;                          // fast model input
const int DET = 320;                         // detector input (the 320x240 frame letterboxed into 320x320)

I2SClass mic;
bool camOk = false, micOk = false, modelOk = false;
bool bgrOrder = true;                        // esp32-camera's RGB888 output is blue-green-red

uint8_t* frame = nullptr;                    // current frame, 320x240x3 (PSRAM)
uint8_t* jobFrame = nullptr;                 // copy handed to the detector (PSRAM)

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
  c.pixel_format = PIXFORMAT_JPEG;        // 320x240 JPEG (small) decoded into PSRAM: real detail for the detector
  c.frame_size = FRAMESIZE_QVGA;
  c.jpeg_quality = 12;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_DRAM;      // the simulator can't put frame buffers in PSRAM yet
  c.grab_mode = CAMERA_GRAB_LATEST;
  frame = (uint8_t*)heap_caps_malloc(FW * FH * 3, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  jobFrame = (uint8_t*)heap_caps_malloc(FW * FH * 3, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  return frame && jobFrame && esp_camera_init(&c) == ESP_OK;
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
  Serial.printf("fast model arena used: %u bytes\n", (unsigned)interp.arena_used_bytes());
  return true;
}

// Red, green, blue of frame pixel (x, y), whatever order the decoder wrote.
inline void px(const uint8_t* f, int x, int y, int& r, int& g, int& b) {
  const uint8_t* p = f + 3 * (y * FW + x);
  if (bgrOrder) { b = p[0]; g = p[1]; r = p[2]; } else { r = p[0]; g = p[1]; b = p[2]; }
}

// Fast model input: the whole 320x240 frame averaged down to 96x96 (int8 RGB, pixel - 128).
void prepareFast() {
  int8_t* in = interpreter->input(0)->data.int8;
  for (int y = 0; y < IMG; y++) {
    const int y0 = y * FH / IMG, y1 = max(y0 + 1, (y + 1) * FH / IMG);
    for (int x = 0; x < IMG; x++) {
      const int x0 = x * FW / IMG, x1 = max(x0 + 1, (x + 1) * FW / IMG);
      int sr = 0, sg = 0, sb = 0, n = 0;
      for (int yy = y0; yy < y1; yy++)
        for (int xx = x0; xx < x1; xx++) {
          int r, g, b;
          px(frame, xx, yy, r, g, b);
          sr += r; sg += g; sb += b; n++;
        }
      int8_t* o = in + 3 * (y * IMG + x);
      o[0] = (int8_t)(sr / n - 128);
      o[1] = (int8_t)(sg / n - 128);
      o[2] = (int8_t)(sb / n - 128);
    }
  }
}

float personScore() {
  if (interpreter->Invoke() != kTfLiteOk) return -1;
  TfLiteTensor* out = interpreter->output(0);
  return (out->data.int8[1] - out->params.zero_point) * out->params.scale;   // index 1 = person
}

// ---- accurate detector on the second core ----
volatile bool jobBusy = false;               // the worker owns jobFrame while true
uint32_t jobFrameAt = 0;
volatile int detPeople = -1, detItems = -1;  // latest detector result (-1 = none yet)
volatile uint32_t detAt = 0;                 // when the frame of that result was taken
volatile uint32_t detMs = 0;                 // how long the last run took
char itemList[200] = "";                     // what the detector saw last, for the serial command 'items'
tflite::MicroInterpreter* detector = nullptr;

// Unpacks a zlib-compressed model from flash into 16-byte aligned PSRAM.
uint8_t* unpack(const unsigned char* z, size_t zBytes, size_t bytes) {
  uint8_t* buf = (uint8_t*)heap_caps_aligned_alloc(16, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  tinfl_decompressor* d = (tinfl_decompressor*)malloc(sizeof(tinfl_decompressor));   // ~11 KB: too big for the stack
  if (!buf || !d) return nullptr;
  tinfl_init(d);
  size_t in = zBytes, out = bytes;
  tinfl_status st = tinfl_decompress(d, z, &in, buf, buf, &out,
                                     TINFL_FLAG_PARSE_ZLIB_HEADER | TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF);
  free(d);
  if (st == TINFL_STATUS_DONE && out == bytes) return buf;
  free(buf);
  return nullptr;
}

tflite::MicroInterpreter* startDetector() {
  uint8_t* model = unpack(g_items_model_z, ITEMS_MODEL_Z_BYTES, ITEMS_MODEL_BYTES);
  const size_t arenaBytes = 3 * 1024 * 1024;
  uint8_t* mem = (uint8_t*)heap_caps_aligned_alloc(16, arenaBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!model || !mem) {
    Serial.println("detector: out of memory or unpack failed");
    return nullptr;
  }
  static tflite::MicroMutableOpResolver<16> ops;
  ops.AddConv2D();
  ops.AddDepthwiseConv2D();
  ops.AddPad();
  ops.AddPadV2();
  ops.AddAdd();
  ops.AddMul();
  ops.AddConcatenation();
  ops.AddMaxPool2D();
  ops.AddResizeNearestNeighbor();
  ops.AddLogistic();
  ops.AddTranspose();
  ops.AddReshape();
  ops.AddSplitV();
  ops.AddGather();
  ops.AddQuantize();
  auto* m = new tflite::MicroInterpreter(tflite::GetModel(model), ops, mem, arenaBytes);
  if (m->AllocateTensors() != kTfLiteOk) {
    Serial.println("detector: AllocateTensors failed");
    return nullptr;
  }
  Serial.printf("detector arena used: %u bytes\n", (unsigned)m->arena_used_bytes());
  return m;
}

// Detector input: the 320x240 frame copied 1:1 into the middle of a 320x320 square (grey bars top and bottom, as
// the model was trained), quantised with the input's scale.
void fillDetector() {
  TfLiteTensor* in = detector->input(0);
  const float s = in->params.scale;
  const int zp = in->params.zero_point;
  static int8_t lut[256];
  for (int v = 0; v < 256; v++) lut[v] = (int8_t)constrain((int)lroundf(v / 255.0f / s) + zp, -128, 127);
  const int top = (DET - FH) / 2;
  int8_t* d = in->data.int8;
  for (int y = 0; y < DET; y++)
    for (int x = 0; x < DET; x++, d += 3) {
      const int fy = y - top;
      if (fy < 0 || fy >= FH) { d[0] = d[1] = d[2] = lut[114]; continue; }
      int r, g, b;
      px(jobFrame, x, fy, r, g, b);
      d[0] = lut[r]; d[1] = lut[g]; d[2] = lut[b];
    }
}

// Overlap of two boxes given as centre x, centre y, width, height.
float iou(const float* a, const float* b) {
  float w = min(a[0] + a[2] / 2, b[0] + b[2] / 2) - max(a[0] - a[2] / 2, b[0] - b[2] / 2);
  float h = min(a[1] + a[3] / 2, b[1] + b[3] / 2) - max(a[1] - a[3] / 2, b[1] - b[3] / 2);
  if (w <= 0 || h <= 0) return 0;
  return w * h / (a[2] * a[3] + b[2] * b[3] - w * h);
}

// Runs the detector on jobFrame and counts boxes per class in CLASSES after non-maximum suppression.
// Rows are [x, y, w, h, objectness, 80 class scores], scores 0..100. Returns false if inference failed.
bool detect(int* perClass) {
  fillDetector();
  if (detector->Invoke() != kTfLiteOk) return false;
  TfLiteTensor* out = detector->output(0);
  const int rows = out->dims->data[1], cols = out->dims->data[2];
  const float s = out->params.scale / 100.0f;    // scores 0..1
  const int zp = out->params.zero_point;
  const int MAX_BOXES = 64;
  static float boxes[MAX_BOXES][6];              // x, y, w, h, score, class slot
  int nb = 0;
  for (int r = 0; r < rows; r++) {
    const int8_t* d = out->data.int8 + r * cols;
    const float obj = (d[4] - zp) * s;
    if (obj < DETECT_SCORE) continue;
    for (int k = 0; k < N_CLASSES; k++) {
      const float score = obj * (d[5 + CLASSES[k].id] - zp) * s;
      if (score < DETECT_SCORE) continue;
      int at = nb < MAX_BOXES ? nb++ : -1;
      if (at < 0) {                              // full: replace the weakest box if this one is stronger
        int weakest = 0;
        for (int i = 1; i < MAX_BOXES; i++) if (boxes[i][4] < boxes[weakest][4]) weakest = i;
        if (boxes[weakest][4] >= score) continue;
        at = weakest;
      }
      for (int c = 0; c < 4; c++) boxes[at][c] = (d[c] - zp) * out->params.scale;
      boxes[at][4] = score;
      boxes[at][5] = k;
    }
  }
  memset(perClass, 0, sizeof(int) * N_CLASSES);
  static bool used[MAX_BOXES];
  memset(used, 0, sizeof used);
  for (;;) {                                     // greedy NMS per class
    int best = -1;
    for (int i = 0; i < nb; i++) if (!used[i] && (best < 0 || boxes[i][4] > boxes[best][4])) best = i;
    if (best < 0) break;
    used[best] = true;
    perClass[(int)boxes[best][5]]++;
    for (int i = 0; i < nb; i++)
      if (!used[i] && boxes[i][5] == boxes[best][5] && iou(boxes[i], boxes[best]) > 0.45f) used[i] = true;
  }
  return true;
}

void workerTask(void*) {
  for (;;) {
    if (jobBusy) {
      const uint32_t t0 = millis();
      int perClass[N_CLASSES];
      if (detect(perClass)) {
        int items = 0, len = 0;
        itemList[0] = 0;
        for (int k = 0; k < N_CLASSES; k++) {
          if (k > 0) items += perClass[k];
          if (perClass[k] && len < (int)sizeof itemList - 24)
            len += snprintf(itemList + len, sizeof itemList - len, "%s%d %s", len ? ", " : "", perClass[k],
                            CLASSES[k].name);
        }
        detPeople = perClass[0];
        detItems = items;
        detMs = millis() - t0;
        detAt = jobFrameAt;
        Serial.printf("DETECTOR people %d, items %d [%s] (%lums)\n", detPeople, detItems, itemList,
                      (unsigned long)detMs);
      } else {
        Serial.println("DETECTOR inference failed");
      }
      jobBusy = false;
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
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
  Serial.setTimeout(20);
  delay(300);
  camOk = startCamera();
  Serial.println(camOk ? "CAM OK (320x240)" : "CAM FAILED");
  modelOk = startModel();
  Serial.println(modelOk ? "MODEL OK" : "MODEL FAILED");
  mic.setPinsPdmRx(42, 41);
  micOk = mic.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  Serial.println(micOk ? "MIC OK" : "MIC FAILED");
  detector = startDetector();
  Serial.println(detector ? "DETECTOR OK" : "DETECTOR FAILED (fast model only, no count, no left items)");
  if (detector) xTaskCreatePinnedToCore(workerTask, "detect", 16384, nullptr, 1, nullptr, 0);   // loop(): core 1
  WiFi.mode(WIFI_STA);
  WiFi.begin("Velxio-GUEST");   // Velxio's built-in open network; use your own SSID on the real board
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  Serial.println(WiFi.status() == WL_CONNECTED ? "WIFI OK" : "WIFI FAILED");
  topic = String("aau-hack26/rooms/") + ROOM_ID + "/readings";
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

// ---- room state ----
bool present = false;                        // what we report
bool confirmed = false;                      // present because the detector saw people (not just the fast model)
int people = 0;                              // detector's count while present
uint32_t usedDetAt = 0;                      // detector result already applied
uint32_t arrivalAt = 0;                      // frame time of the fast model's last arrival
bool lastArrival = false;
int itemsBefore = -1, leftItems = 0;         // room's own items (baseline) and extra items left behind
bool occupiedSinceBaseline = false;

void applyDetector() {
  if (detPeople < 0 || detAt == usedDetAt || millis() - detAt > RESULT_FRESH_MS) return;
  usedDetAt = detAt;
  if (detPeople > 0) {
    present = confirmed = true;
    people = detPeople;
    occupiedSinceBaseline = true;
    leftItems = 0;                           // whoever is here may still pick their things up
    return;
  }
  // the detector saw nobody: the room is empty, unless the fast model reported an arrival after that frame
  if (present && !confirmed && (int32_t)(arrivalAt - detAt) > 0) return;
  present = confirmed = false;
  people = 0;
  if (itemsBefore < 0 || !occupiedSinceBaseline) {
    itemsBefore = detItems;                  // empty and nobody came: these things belong to the room
  } else {
    leftItems = max(0, (int)detItems - itemsBefore);
    if (leftItems == 0) {                    // clean again: this is the new baseline
      itemsBefore = detItems;
      occupiedSinceBaseline = false;
    }
  }
}

void handleSerial() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd == "items" || cmd == "status") {
    Serial.printf("present=%d confirmed=%d people=%d | detector: %d people, %d items [%s], %lus ago, run %lums | "
                  "room baseline %d items, left %d\n", present, confirmed, people, detPeople, detItems, itemList,
                  (unsigned long)((millis() - detAt) / 1000), (unsigned long)detMs, itemsBefore, leftItems);
  } else if (cmd == "snapshot") {
    itemsBefore = max((int)detItems, 0);
    occupiedSinceBaseline = false;
    leftItems = 0;
    Serial.printf("The %d item(s) visible now belong to the room; left items back to 0.\n", itemsBefore);
  } else if (cmd == "bgr") {
    bgrOrder = !bgrOrder;
    Serial.printf("Camera colour order is now %s\n", bgrOrder ? "BGR" : "RGB");
  } else if (cmd.length()) {
    Serial.println("Commands: status, items, snapshot, bgr");
  }
}

void loop() {
  handleSerial();
  String json = String("{\"room_id\":\"") + ROOM_ID + "\"";
  float db = micOk ? noiseDb() : -1;
  if (db >= 0) json += ",\"noise_db\":" + String(db, 1);

  camera_fb_t* fb = camOk ? esp_camera_fb_get() : nullptr;
  bool decoded = fb && fmt2rgb888(fb->buf, fb->len, fb->format, frame);
  const uint32_t frameAt = millis();
  if (fb) esp_camera_fb_return(fb);

  if (decoded && modelOk) {
    if (detector && !jobBusy) {              // hand the newest frame to the idle detector
      memcpy(jobFrame, frame, FW * FH * 3);
      jobFrameAt = frameAt;
      jobBusy = true;
    }
    prepareFast();
    const uint32_t t0 = millis();
    const float score = personScore();
    const uint32_t ms = millis() - t0;
    applyDetector();
    if (score >= 0) {
      votes[voteIdx++ % 3] = score >= ARRIVAL_VOTE;
      const bool arrival = score >= ARRIVAL_SCORE || (votes[0] + votes[1] + votes[2]) >= 2;
      if (detector == nullptr) {
        present = arrival;                   // no detector: the fast model alone
      } else if (!present && arrival && !lastArrival) {
        // an arrival is a change from "no" to "yes": a false "yes" that never goes away can't keep re-opening
        // the room after the detector closed it
        present = true;
        people = 1;                          // the detector's next run gives the real count
        arrivalAt = frameAt;
        occupiedSinceBaseline = true;
        leftItems = 0;
      }
      lastArrival = arrival;
      json += ",\"person_score\":" + String(score, 2);
    }
    json += ",\"presence\":" + String(present ? "true" : "false");
    if (confirmed || !present) json += ",\"people\":" + String(present ? people : 0);   // real count or empty
    if (detector) json += ",\"left_items\":" + String(present ? 0 : leftItems);
    Serial.printf("person=%.2f (%lums) present=%d confirmed=%d people=%d left=%d\n", score, (unsigned long)ms,
                  present, confirmed, people, leftItems);
  } else if (camOk) {
    Serial.println("no camera frame (is the Camera button on?)");
  }
  json += "}";
  Serial.println(json);
  publish(json);
  mqtt.loop();
}
