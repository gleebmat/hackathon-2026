// Smart campus room sensor - Seeed XIAO ESP32S3 Sense (runs in the Velxio simulator and on the real board).
//
// Once per camera frame (about every 1-2 s in Velxio) it measures the room on the board itself and publishes one JSON
// reading over MQTT to the topic aau-hack26/rooms/<room>/readings on a public broker; the backend
// (app/mqtt_feed.py) subscribes to it:
//   {"room_id":"Z.1.04","noise_db":47.0,"presence":true,"person_score":0.91,"people":2,"left_items":0}
// Three models, all TensorFlow Lite Micro, int8, on the board:
//  - presence (every frame): Arshia's 96x96 person model (models/vww_96_int8.tflite in person_model.h)
//  - people count (while someone is present, on the second core): Seeed's Swift-YOLO face detector, 96x96
//    (models/face_96_int8.tflite in face_model.h); people = number of faces, at least 1 while present
//  - left items (while the room is empty, on the second core): Seeed's Swift-YOLO COCO detector, 320x320, 80 classes
//    (models/coco_320_int8.tflite in items_model.h); it counts forgettable things (bags, phones, umbrellas, books, ...).
//    Items already there before people came belong to the room; left items = how many more there are after they left.
//  - noise_db: PDM microphone level (approximate: silence ~30 dB, full scale ~90 dB)
// The two detectors are zlib-compressed in flash (firmware + models must fit Velxio's 3 MB app partition) and
// unpacked into PSRAM at startup with the ROM decompressor.
// Serial commands (Velxio: type into the serial monitor, press Send): items = list what the item detector sees;
// snapshot = the items visible now belong to the room (left items back to 0).
// In Velxio: Camera button = your webcam, Mic button = your microphone (off = test pattern / 440 Hz tone).
// Libraries: Chirale_TensorFlowLite (builds TFLM from source, works on arduino-esp32 3.x), PubSubClient.
// Files: sketch.ino + person_model.h + face_model.h + items_model.h.
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

// Switches: 0 turns a detector off (its model file is then not needed). Previous version (Swift-YOLO Nano count,
// snapshot-diff left items): git tag board-v1.
#define COUNT_PEOPLE 1
#define FIND_ITEMS 1
#if COUNT_PEOPLE
#include "face_model.h"
#endif
#if FIND_ITEMS
#include "items_model.h"
#endif
#if COUNT_PEOPLE || FIND_ITEMS
#if __has_include("miniz.h")                 // the ROM decompressor's header moved between ESP-IDF versions
#include "miniz.h"
#elif __has_include("rom/miniz.h")
#include "rom/miniz.h"
#else
#include "esp32s3/rom/miniz.h"
#endif
#endif

const char* ROOM_ID = "Z.1.04";
const char* MQTT_HOST = "broker.hivemq.com";   // public broker: fine for a demo, use your own for real data
const int MQTT_PORT = 1883;
const float PERSON_THRESHOLD = 0.60;
const float PRESENT_NOW = 0.70;              // a single frame this sure counts as present right away
const float FACE_SCORE = 0.40;               // face detector score that counts as a person
const float ITEM_SCORE = 0.30;               // objectness x class score that counts as an item
const uint32_t RESULT_FRESH_MS = 120000;     // older detector results are not used

// COCO classes people forget (index in the model's 80 classes).
struct ItemClass { int id; const char* name; };
const ItemClass ITEMS[] = {{24, "backpack"}, {25, "umbrella"}, {26, "handbag"}, {28, "suitcase"}, {39, "bottle"},
                           {41, "cup"}, {63, "laptop"}, {67, "cell phone"}, {73, "book"}};
const int N_ITEMS = sizeof(ITEMS) / sizeof(ITEMS[0]);

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

const int IMG = 96;                          // camera frame and presence model input: 96x96

I2SClass mic;
bool camOk = false, micOk = false, modelOk = false;

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
  c.pixel_format = PIXFORMAT_RGB565;      // colour: the models take RGB
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

// Fills the presence model input (int8 RGB, pixel - 128) from one RGB565 frame; rgb (optional) receives 8-bit RGB
// for the detectors.
void prepare(const camera_fb_t* fb, uint8_t* rgb) {
  int8_t* in = interpreter ? interpreter->input(0)->data.int8 : nullptr;
  for (int i = 0; i < IMG * IMG; i++) {
    uint16_t p = (fb->buf[2 * i] << 8) | fb->buf[2 * i + 1];
    uint8_t r = (p >> 11) << 3, g = ((p >> 5) & 0x3F) << 2, b = (p & 0x1F) << 3;
    if (rgb) {
      rgb[3 * i] = r;
      rgb[3 * i + 1] = g;
      rgb[3 * i + 2] = b;
    }
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

#if COUNT_PEOPLE || FIND_ITEMS
// ---- detectors on the second core ----
enum Job { JOB_NONE, JOB_FACES, JOB_ITEMS };
uint8_t jobRgb[IMG * IMG * 3];               // frame handed to the worker
volatile int job = JOB_NONE;                 // the worker owns jobRgb while this isn't JOB_NONE
volatile int faces = -1, items = -1;         // latest results (-1 = none yet)
volatile uint32_t facesAt = 0, itemsAt = 0;  // when the frame of that result was taken
uint32_t jobFrameAt = 0;
char itemList[160] = "";                     // what the item detector saw last, for the serial command 'items'

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

// Builds an interpreter with the ops both Swift-YOLO detectors use.
tflite::MicroInterpreter* startDetector(const unsigned char* z, size_t zBytes, size_t bytes, size_t arenaBytes,
                                        const char* name) {
  uint8_t* model = unpack(z, zBytes, bytes);
  uint8_t* mem = (uint8_t*)heap_caps_aligned_alloc(16, arenaBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!model || !mem) {
    Serial.printf("%s: out of memory or unpack failed\n", name);
    return nullptr;
  }
  static tflite::MicroMutableOpResolver<16> ops;
  static bool opsReady = false;
  if (!opsReady) {
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
    opsReady = true;
  }
  auto* m = new tflite::MicroInterpreter(tflite::GetModel(model), ops, mem, arenaBytes);
  if (m->AllocateTensors() != kTfLiteOk) {
    Serial.printf("%s: AllocateTensors failed\n", name);
    return nullptr;
  }
  Serial.printf("%s arena used: %u bytes\n", name, (unsigned)m->arena_used_bytes());
  return m;
}

// Copies jobRgb into a detector's input, scaled to its size (nearest pixel).
void fillInput(tflite::MicroInterpreter* m) {
  TfLiteTensor* in = m->input(0);
  const int size = in->dims->data[1];
  const float s = in->params.scale;
  const int zp = in->params.zero_point;
  for (int y = 0; y < size; y++)
    for (int x = 0; x < size; x++) {
      const uint8_t* px = jobRgb + 3 * ((y * IMG / size) * IMG + x * IMG / size);
      for (int c = 0; c < 3; c++)
        in->data.int8[3 * (y * size + x) + c] = (int8_t)constrain((int)lroundf(px[c] / 255.0f / s) + zp, -128, 127);
    }
}

// Overlap of two boxes given as centre x, centre y, width, height.
float iou(const float* a, const float* b) {
  float w = min(a[0] + a[2] / 2, b[0] + b[2] / 2) - max(a[0] - a[2] / 2, b[0] - b[2] / 2);
  float h = min(a[1] + a[3] / 2, b[1] + b[3] / 2) - max(a[1] - a[3] / 2, b[1] - b[3] / 2);
  if (w <= 0 || h <= 0) return 0;
  return w * h / (a[2] * a[3] + b[2] * b[3] - w * h);
}

// Runs a Swift-YOLO detector on jobRgb. Rows are [x, y, w, h, objectness, class scores...], scores 0..100.
// Counts boxes per class (perClass may be null) after non-maximum suppression; returns the total or -1.
int detect(tflite::MicroInterpreter* m, float minScore, const ItemClass* classes, int nClasses, int* perClass) {
  fillInput(m);
  if (m->Invoke() != kTfLiteOk) return -1;
  TfLiteTensor* out = m->output(0);
  const int rows = out->dims->data[1], cols = out->dims->data[2];
  const float s = out->params.scale / 100.0f;    // scores 0..1
  const int zp = out->params.zero_point;
  const int MAX_BOXES = 48;
  static float boxes[MAX_BOXES][6];              // x, y, w, h, score, class slot
  int nb = 0;
  for (int r = 0; r < rows; r++) {
    const int8_t* d = out->data.int8 + r * cols;
    float obj = (d[4] - zp) * s;
    if (obj < minScore) continue;
    for (int k = 0; k < (classes ? nClasses : 1); k++) {
      float score = classes ? obj * (d[5 + classes[k].id] - zp) * s : obj;
      if (score < minScore) continue;
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
  if (perClass) memset(perClass, 0, sizeof(int) * nClasses);
  int total = 0;
  static bool used[MAX_BOXES];
  memset(used, 0, sizeof used);
  for (;;) {                                     // greedy NMS per class
    int best = -1;
    for (int i = 0; i < nb; i++) if (!used[i] && (best < 0 || boxes[i][4] > boxes[best][4])) best = i;
    if (best < 0) break;
    used[best] = true;
    total++;
    if (perClass) perClass[(int)boxes[best][5]]++;
    for (int i = 0; i < nb; i++)
      if (!used[i] && boxes[i][5] == boxes[best][5] && iou(boxes[i], boxes[best]) > 0.45f) used[i] = true;
  }
  return total;
}

tflite::MicroInterpreter* faceModel = nullptr;
tflite::MicroInterpreter* itemsModel = nullptr;

void workerTask(void*) {
  for (;;) {
    int j = job;
    if (j != JOB_NONE) {
      uint32_t t0 = millis();
      if (j == JOB_FACES) {
        int n = detect(faceModel, FACE_SCORE, nullptr, 0, nullptr);
        if (n >= 0) {
          faces = n;
          facesAt = jobFrameAt;
        }
        Serial.printf("faces %d (%lums)\n", n, (unsigned long)(millis() - t0));
      } else {
        int perClass[N_ITEMS];
        int n = detect(itemsModel, ITEM_SCORE, ITEMS, N_ITEMS, perClass);
        if (n >= 0) {
          int len = 0;
          itemList[0] = 0;
          for (int k = 0; k < N_ITEMS; k++)
            if (perClass[k] && len < (int)sizeof itemList - 24)
              len += snprintf(itemList + len, sizeof itemList - len, "%s%d %s", len ? ", " : "", perClass[k],
                              ITEMS[k].name);
          items = n;
          itemsAt = jobFrameAt;
        }
        Serial.printf("items %d [%s] (%lums)\n", n, itemList, (unsigned long)(millis() - t0));
      }
      job = JOB_NONE;
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}
#endif

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
  Serial.println(camOk ? "CAM OK" : "CAM FAILED");
  modelOk = startModel();
  Serial.println(modelOk ? "MODEL OK" : "MODEL FAILED");
  mic.setPinsPdmRx(42, 41);
  micOk = mic.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  Serial.println(micOk ? "MIC OK" : "MIC FAILED");
#if COUNT_PEOPLE
  faceModel = startDetector(g_face_model_z, FACE_MODEL_Z_BYTES, FACE_MODEL_BYTES, 512 * 1024, "face model");
  Serial.println(faceModel ? "FACES OK" : "FACES FAILED (presence only)");
#endif
#if FIND_ITEMS
  itemsModel = startDetector(g_items_model_z, ITEMS_MODEL_Z_BYTES, ITEMS_MODEL_BYTES, 3 * 1024 * 1024, "items model");
  Serial.println(itemsModel ? "ITEMS OK" : "ITEMS FAILED (no left items)");
#endif
#if COUNT_PEOPLE || FIND_ITEMS
  if (faceModel || itemsModel)
    xTaskCreatePinnedToCore(workerTask, "detect", 16384, nullptr, 1, nullptr, 0);   // loop() runs on core 1
#endif
  WiFi.mode(WIFI_STA);
  WiFi.begin("Velxio-GUEST");   // Velxio's built-in open network; use your own SSID on the real board
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  Serial.println(WiFi.status() == WL_CONNECTED ? "WIFI OK" : "WIFI FAILED");
  topic = String("aau-hack26/rooms/") + ROOM_ID + "/readings";
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

// Left items from item counts: items seen while nobody has come yet belong to the room (baseline); after people
// were present and left, every extra item counts. When the extra items are gone the room is clean again.
int itemsBefore = 0, leftItems = 0;
bool occupied = false;                       // people were seen since the baseline
uint32_t leftAt = 0;                         // when presence last ended

void loop() {
  // no pause: one reading per frame, as fast as the presence model runs
  String json = String("{\"room_id\":\"") + ROOM_ID + "\"";
  float db = micOk ? noiseDb() : -1;
  if (db >= 0) json += ",\"noise_db\":" + String(db, 1);

  camera_fb_t* fb = camOk ? esp_camera_fb_get() : nullptr;
  if (fb && modelOk) {
    static bool wasPresent = false;
#if COUNT_PEOPLE || FIND_ITEMS
    // hand this frame to the idle worker: faces while someone is here, items while the room is empty
    int next = wasPresent ? (faceModel ? JOB_FACES : JOB_NONE) : (itemsModel ? JOB_ITEMS : JOB_NONE);
    bool feed = job == JOB_NONE && next != JOB_NONE;
    prepare(fb, feed ? jobRgb : nullptr);
    if (feed) {
      jobFrameAt = millis();
      job = next;
    }
#else
    prepare(fb, nullptr);
#endif
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
    // one clear frame is enough to say "someone is here"; leaving needs 2 of the last 3 frames below the threshold
    bool present = score >= PRESENT_NOW || (votes[0] + votes[1] + votes[2]) >= 2;
    if (wasPresent && !present) leftAt = millis();
    wasPresent = present;

#if FIND_ITEMS
    static uint32_t usedItemsAt = 0;
    if (Serial.available()) {
      String cmd = Serial.readStringUntil('\n');
      cmd.trim();
      if (cmd == "items") {
        Serial.printf("Item detector: %d item(s) [%s]; room baseline %d; left %d\n", items, itemList, itemsBefore,
                      leftItems);
      } else if (cmd == "snapshot") {
        itemsBefore = max((int)items, 0);
        occupied = false;
        leftItems = 0;
        Serial.printf("The %d item(s) visible now belong to the room; left items back to 0.\n", itemsBefore);
      } else if (cmd.length()) {
        Serial.println("Commands: items, snapshot");
      }
    }
    if (present) {
      occupied = true;
      leftItems = 0;                         // whoever is here may still pick their things up
    } else if (items >= 0 && itemsAt != usedItemsAt && millis() - itemsAt < RESULT_FRESH_MS) {
      usedItemsAt = itemsAt;                 // a new item count from a frame without people
      if (!occupied) {
        itemsBefore = items;
      } else if ((int32_t)(itemsAt - leftAt) >= 0) {
        leftItems = max(0, (int)items - itemsBefore);
        if (leftItems == 0) occupied = false;   // clean again: the next count is the new baseline
      }
    }
    json += ",\"left_items\":" + String(leftItems);
#endif
    json += ",\"presence\":" + String(present ? "true" : "false");
    json += ",\"person_score\":" + String(score, 2);
#if COUNT_PEOPLE
    // the face count lags a few seconds behind, so presence decides 0 vs. some and the faces say how many
    if (faces >= 0 && millis() - facesAt < RESULT_FRESH_MS)
      json += ",\"people\":" + String(present ? max((int)faces, 1) : 0);
#endif
    Serial.printf("person=%.2f (%lums) present=%d\n", score, (unsigned long)ms, present);
  } else if (fb) {
    esp_camera_fb_return(fb);
  }
  json += "}";
  Serial.println(json);
  publish(json);
  mqtt.loop();
}
