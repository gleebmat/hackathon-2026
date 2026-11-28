# hackathon-2026

Smart campus room booking for AAU (Infineon challenge): a 3D campus map, live room status, booking with
sharing rules, and one room (`Z.1.04`) wired to a XIAO ESP32S3 Sense board (camera + microphone, person
model on the board), simulated in Velxio.
Spec and API: `docs/PLAN.md`. Status per teammate: `docs/LOG.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 and log in as `student1@edu.aau.at` / `demo` (also `student2..4`).
API docs: http://localhost:8000/docs. The map alone: http://localhost:8000/map3d/. Tests: `python -m pytest tests`.

- **Website:** English and German (switch top right, in the profile menu, the footer, or press `L`; strings live in
  `web/js/i18n.js`, backend errors and room types are translated there too). Footer with AAU links (website,
  CAMPUSonline, Moodle, campus map, IT Service Desk), how booking works and the team's contacts (`web/js/footer.js`).
  Rooms can be shared as links (`/?room=Z.1.04`, "Copy link" in the room panel), bookings exported to a calendar
  (`.ics`, "Calendar" in My bookings), and `?` shows the keyboard shortcuts. Login photo: carinthia.com
  (`web/img/login.jpg`).
- **Port:** any free port works (`uvicorn app.main:app --port 8011` is fine too). The board doesn't talk to the
  port: it publishes to an MQTT broker and the backend subscribes, so only the browser URL changes.
- **Database:** a local SQLite file (`campus.db`, or `DB_PATH`), gitignored. Accounts, sessions, bookings and
  ratings stay there across restarts, pulls and new commits; schema changes are migrated in place
  (`app/db.py: upgrade`). Only the board readings table is rebuilt when its columns change. Every machine has its own
  database, so an account made on Gleb's laptop doesn't exist on yours. The demo accounts are recreated if missing.
  Delete `campus.db` for a clean start.

## The board: XIAO ESP32S3 Sense in Velxio

**What runs on the board** (`firmware/xiao_sense/sketch.ino`; one reading per camera frame, ~1-2 s in the simulator;
the website polls every 1 s and the open room panel every 0.5 s). Three models, all TensorFlow Lite Micro int8:
- **Presence, every frame:** Arshia's 96x96 person model (`models/vww_96_int8.tflite` in `person_model.h`). Yes/no
  (score 0..1): present at once when one frame scores 0.70+, or when 2 of the last 3 frames reach 0.60; gone when 2 of
  3 drop below 0.60.
- **People count, while someone is present (second CPU core):** Seeed's Swift-YOLO **face** detector, 96x96, 22 M
  multiply-adds (`models/face_96_int8.tflite` in `face_model.h`). People = number of faces (at least 1 while present),
  so people facing away aren't counted. Faces need to be reasonably big (a webcam a metre or two away is fine).
- **Left items, after people leave (second CPU core):** Seeed's Swift-YOLO **COCO** detector, 320x320, 80 classes,
  189 M multiply-adds (`models/coco_320_int8.tflite` in `items_model.h`; its last three layers were re-quantised by
  `tools/patch_coco_concat.py` so standard TFLite runs it). It counts **backpack, umbrella, handbag, suitcase, bottle,
  cup, laptop, cell phone and book** (score 0.30+; list in `ITEMS` in the sketch). No photo comparison: items already
  there before people came are the room's baseline; **left items = how many more there are after they left**.
  In Velxio one item check takes **~70 s** (0.2 s on a real board), so it only runs after people leave and every
  5 minutes in an empty room; a face count waits while an item check is running.
- **Noise:** the PDM microphone (RMS mapped to about 30-90 dB).
- **Switches** at the top of the sketch: `COUNT_PEOPLE 0` / `FIND_ITEMS 0` turn a detector off (its model file is
  then not needed). The previous version (Swift-YOLO Nano count, photo-comparison left items) is the git tag
  `board-v1`. Both detectors are zlib-compressed in flash and unpacked into PSRAM at startup; regenerate a header with
  `python tools/make_model_header.py models/face_96_int8.tflite firmware/xiao_sense/face_model.h face_model`.
- One JSON reading per frame goes over MQTT to `broker.hivemq.com:1883`, topic `aau-hack26/rooms/Z.1.04/readings`:
  `{"room_id":"Z.1.04","noise_db":37.2,"presence":true,"person_score":0.91,"people":2,"left_items":0}`.
  The backend (`app/mqtt_feed.py`) subscribes and stores it like `POST /api/readings`. Readings older than 10 s
  count as "board offline".
- **Serial commands** (Velxio serial monitor, type and press Send): `items` lists what the item detector saw last and
  the baseline; `snapshot` makes the items visible now part of the room (left items back to 0).

**Velxio setup (team account).** Log in at https://velxio.dev with the team's (Gleb's) account and open the project
**TODAREISTODO** (https://velxio.dev/gleebmat/todareistodo). It already has `sketch.ino`, `person_model.h`,
`face_model.h`, `items_model.h` and the
libraries `Chirale_TensorFlowLite` and `PubSubClient` (Library Manager). GitHub is the master copy: after changing
the sketch here, paste it into Velxio (or the other way round) and save (File > Save project).
1. Start the backend with short demo timers:
   ```powershell
   $env:GHOST_GRACE_SECONDS = '5'; $env:GHOST_RELEASE_SECONDS = '15'; uvicorn app.main:app
   ```
2. In Velxio, under the board, switch on **Camera** (your webcam) and **Mic** (your microphone; when it's off you
   get a 440 Hz test tone), allow both in Chrome, then **Run**. The first compile takes a few minutes; after that
   the build cache makes it fast. The serial monitor shows `CAM OK`, `MODEL OK`, `MIC OK`, `FACES OK`, `ITEMS OK`,
   `WIFI OK`, then one `person=... present=...` line and one `MQTT ... -> sent` line per frame, plus `faces N` and
   `items N [...]` lines when a detector finishes.
3. Open http://localhost:8000 and search `z104`. Z.1.04 shows **LIVE**, the noise and "Someone is here". Book it
   and step out of the webcam: after 5 s the booking is marked ghost (violet on the map) and after 15 s it's
   released. With two people in view the panel shows 2 a few seconds later. Leave a bag, phone or bottle and step
   out: about a minute later (one item check) the panel shows "🎒 Something left behind".

**Troubleshooting**
- *Compile error "control reaches end of non-void function" or a cut-off sketch:* the paste was truncated (the
  editor is slow with long pastes). Check that `sketch.ino` ends with `loop()`'s closing brace, then paste again.
- *Two boards:* only run the project in one browser tab. Every running tab publishes to the same topic.
- *"Smallest app partition is 0x300000" / "app partition is too small":* the firmware is over 3 MB. Velxio ignores a
  custom `partitions.csv`, so models must be compressed (as the detectors are) or smaller.
- *HTTPS from the simulated board fails* (`ssl ... fatal alert`); plain MQTT/HTTP works. So models can't be downloaded
  at startup from GitHub.
- *A file "larger than 4 million characters":* Velxio won't build it; split the model or use a smaller one.
- *Website shows the board offline:* the simulation is stopped or WiFi failed; the serial monitor says which.

**Placement: how to get reliable results**
- *Presence:* the presence model sees a 96x96 picture of the whole view: upper body and face, roughly in the middle,
  not just a shoulder at the edge. Good light helps; a backlit person (window behind) scores low.
- *People count:* faces must face the camera and be reasonably big; sit a metre or two from the webcam.
- *Left items:* use things the detector knows (bag, backpack, umbrella, phone, bottle, cup, laptop, book), clearly
  visible and not tiny in the picture (a phone held up close works, a phone far away on a desk may not). Things that
  were already there before you came count as the room's own; check with `items` in the serial monitor, and use
  `snapshot` to accept what is there now. After you leave, the result comes with the next item check (~70 s in Velxio).

## Board limits (the brief for choosing models)

Everything below was measured in Velxio on 28 Nov; any new model has to fit it.

| Limit | Value | What it means for a model |
|---|---|---|
| Chip | ESP32-S3, 2 cores at 240 MHz, 512 KB SRAM, **8 MB PSRAM**, 8 MB flash | weights and working memory (tensor arena) go in PSRAM; a few MB is fine |
| App flash in Velxio | **3 MB** (custom `partitions.csv` is ignored); the firmware itself is ~1.4 MB | **~1.6 MB left for models**, more if zlib-compressed (int8 weights shrink ~20-30%); today: face 0.67 + COCO 0.60 MB compressed, firmware ~2.8 MB in total |
| Files in Velxio | max **4 million characters** per file | a model as a C array (~3 characters per byte) must stay under ~1.3 MB compressed, or be split |
| Network in Velxio | plain MQTT/HTTP only, **HTTPS fails** | models can't be downloaded at startup; they must be compiled in |
| Runtime | TensorFlow Lite Micro (`Chirale_TensorFlowLite`), **int8** `.tflite` | ops known to work: CONV_2D, DEPTHWISE_CONV_2D, FULLY_CONNECTED, AVERAGE/MAX_POOL_2D, ADD, MUL, CONCATENATION, PAD, PADV2, RESIZE_NEAREST_NEIGHBOR, LOGISTIC, SOFTMAX, RESHAPE, TRANSPOSE, SPLIT_V, GATHER, QUANTIZE; int8 CONCATENATION inputs must share one scale; no custom ops (e.g. `TFLite_Detection_PostProcess`) |
| Speed in Velxio | **~8 million multiply-adds per second** (reference kernels, no ESP-NN/SIMD): the 7.5 M MAC person model takes ~0.95 s, the 22 M MAC face detector a few seconds, the 189 M MAC COCO detector ~70 s (sharing the CPU) | for a "live" feel (≤ ~1-2 s per frame) a model must stay **under ~10-15 M MACs** per frame; the real board is ~10-20x faster |
| Second core | usable (the people counter runs there) | in Velxio both cores share the host's speed: a second model slows the first one down |
| Camera | 96x96 RGB565 frames (your webcam, scaled) | models get a 96x96 picture (bigger input = upscaled, no extra detail); small objects (keys, pens) are only a few pixels |
| Espressif ESP-DL models | need ESP-IDF components and the S3 vector instructions | not usable in Velxio's Arduino build (fine on a real board) |

**Models we compared (28 Nov, on test photos and in Velxio):**

| Job | Model | Work per frame | Result |
|---|---|---|---|
| Presence | Arshia's VWW 96x96 (in use) | 7.5 M | fast; yes/no only |
| Count | Swift-YOLO Nano person 192 (tag `board-v1`) | 186 M | accurate (4/4, 2/2 on photos) but ~45 s |
| Count | Swift-YOLO person 192 | 89 M | found only 2 of 4 people |
| Count | **Swift-YOLO face 96 (in use)** | 22 M | 97.9 mAP on its dataset; a few seconds; needs visible faces |
| Items | **Swift-YOLO COCO 320 (in use, patched)** | 189 M | 80 classes; found tv, chairs, bed, plant, book, clock, people on COCO photos; ~70 s |
| Items | EfficientDet-Lite0/2, SSD MobileNet | 400 M+ | too big; custom post-processing op |
| Items | FOMO 96x96 (Edge Impulse) | ~5 M | fastest, but no pretrained one for these classes: needs training |

## Graphify (code knowledge graph, saves AI tokens)

Install once on your machine, then run the setup inside this repo:

```bash
pip install graphifyy          # or: uv tool install graphifyy
graphify install --platform claude
graphify claude install        # adds Claude hooks to your local .claude/settings.json
graphify hook install          # keeps the graph updated after each commit
```

Restart Claude Code afterwards. The graph lives in `graphify-out/`.
