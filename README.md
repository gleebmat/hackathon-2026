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

- **Port:** any free port works (`uvicorn app.main:app --port 8011` is fine too). The board doesn't talk to the
  port: it publishes to an MQTT broker and the backend subscribes, so only the browser URL changes.
- **Database:** a local SQLite file (`campus.db`, or `DB_PATH`), gitignored. Accounts, sessions, bookings and
  ratings stay there across restarts, pulls and new commits; schema changes are migrated in place
  (`app/db.py: upgrade`). Only the board readings table is rebuilt when its columns change. Every machine has its own
  database, so an account made on Gleb's laptop doesn't exist on yours. The demo accounts are recreated if missing.
  Delete `campus.db` for a clean start.

## The board: XIAO ESP32S3 Sense in Velxio

**What runs on the board** (`firmware/xiao_sense/sketch.ino`; one reading per camera frame, ~1-2 s in the simulator;
the website polls every 1 s and the open room panel every 0.5 s). The camera takes **320x240** JPEG frames, decoded
into PSRAM. Two models, both TensorFlow Lite Micro int8, working together:
- **Fast, every frame:** Arshia's 96x96 person model (`models/vww_96_int8.tflite` in `person_model.h`) on the whole
  frame scaled down. It only reports **arrivals** quickly: one frame at 0.70+, or 2 of the last 3 at 0.60+, after a
  "no". Until the accurate detector confirms, the reading has `presence` but no `people` ("Someone is here").
- **Accurate, in a loop on the second CPU core:** Seeed's Swift-YOLO **COCO** detector, 320x320, 80 classes,
  189 M multiply-adds (`models/coco_320_int8.tflite` in `items_model.h`; its last three layers were re-quantised by
  `tools/patch_coco_concat.py` so standard TFLite runs it). It sees the sharp 320x240 frame letterboxed (grey bars,
  not upscaled) and one run gives both the **people count** (class person) and the **things in view**: backpack,
  umbrella, handbag, suitcase, bottle, cup, laptop, cell phone, book (score 0.30+; list in `CLASSES` in the sketch).
  One run takes **~95 s in Velxio** (a few seconds at most on a real board); it always takes the newest frame.
- **Presence = the accurate detector.** Once it has seen people the room stays occupied until one of its runs sees
  nobody; the fast model can add an arrival in between but can never declare the room empty. So a person standing
  still doesn't flicker, and "empty" comes ~1-2 detector runs after the last person left.
- **Left items:** no photo comparison. Things counted while the room was empty are the room's own (baseline); after
  people were there, a run without people that sees more of them reports the extra ones as left items. When the
  room is clean again, that becomes the new baseline.
- **Noise:** the PDM microphone (RMS mapped to about 30-90 dB).
- The previous versions are the git tag `board-v1` (Nano count, photo comparison) and, before this change, a face
  detector for counting (needed faces towards the camera). The detector is zlib-compressed in flash and unpacked into
  PSRAM at startup; regenerate the header with
  `python tools/make_model_header.py models/coco_320_int8.tflite firmware/xiao_sense/items_model.h items_model`.
- One JSON reading per frame goes over MQTT to `broker.hivemq.com:1883`, topic `aau-hack26/rooms/Z.1.04/readings`:
  `{"room_id":"Z.1.04","noise_db":37.2,"presence":true,"person_score":0.91,"people":2,"left_items":0}`.
  The backend (`app/mqtt_feed.py`) subscribes and stores it like `POST /api/readings`. Readings older than 10 s
  count as "board offline".
- **Serial commands** (Velxio serial monitor, type and press Send): `status` (or `items`) shows the room state and
  what the detector saw last; `snapshot` makes the items visible now part of the room (left items back to 0); `bgr`
  flips the camera's red/blue order if colours look wrong.

**Velxio setup (team account).** Log in at https://velxio.dev with the team's (Gleb's) account and open the project
**TODAREISTODO** (https://velxio.dev/gleebmat/todareistodo). It already has `sketch.ino`, `person_model.h`,
`items_model.h` and the
libraries `Chirale_TensorFlowLite` and `PubSubClient` (Library Manager). GitHub is the master copy: after changing
the sketch here, paste it into Velxio (or the other way round) and save (File > Save project).
1. Start the backend with short demo timers:
   ```powershell
   $env:GHOST_GRACE_SECONDS = '5'; $env:GHOST_RELEASE_SECONDS = '15'; uvicorn app.main:app
   ```
2. In Velxio, under the board, switch on **Camera** (your webcam) and **Mic** (your microphone; when it's off you
   get a 440 Hz test tone), allow both in Chrome, then **Run**. The first compile takes a few minutes; after that
   the build cache makes it fast. The serial monitor shows `CAM OK`, `MODEL OK`, `MIC OK`, `DETECTOR OK`,
   `WIFI OK`, then one `person=... present=...` line and one `MQTT ... -> sent` line per frame, plus a
   `DETECTOR people N, items N [...]` line when a detector run finishes.
3. Open http://localhost:8000 and search `z104`. Z.1.04 shows **LIVE**, the noise and "Someone is here". Book it
   and step out of the webcam: after 5 s the booking is marked ghost (violet on the map) and after 15 s it's
   released. With two people in view the panel shows 2 after the next detector run (~1 min). Leave a bag, phone
   or bottle and step out: one or two detector runs later the panel shows "🎒 Something left behind".

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
- *Presence and count:* the detector finds whole or partial people (facing away is fine) as long as they are not
  tiny in the 320x240 picture; a metre or a few metres from the webcam works. Good light helps; a backlit person
  (window behind) is harder. Arrivals show at once ("Someone is here"); the count follows with the next detector run.
- *Left items:* use things the detector knows (bag, backpack, umbrella, phone, bottle, cup, laptop, book), clearly
  visible and not tiny in the picture (a phone held up close works, a phone far away on a desk may not). Things that
  were already there before you came count as the room's own; check with `status` in the serial monitor, and use
  `snapshot` to accept what is there now. After you leave, the result comes with the first detector run that sees
  nobody (one or two runs, ~1-2 min in Velxio).

## Board limits (the brief for choosing models)

Everything below was measured in Velxio on 28 Nov; any new model has to fit it.

| Limit | Value | What it means for a model |
|---|---|---|
| Chip | ESP32-S3, 2 cores at 240 MHz, 512 KB SRAM, **8 MB PSRAM**, 8 MB flash | weights and working memory (tensor arena) go in PSRAM; a few MB is fine |
| App flash in Velxio | **3 MB** (custom `partitions.csv` is ignored); the firmware itself is ~1.4 MB | **~1.6 MB left for models**, more if zlib-compressed (int8 weights shrink ~20-30%); today: person 0.33 + COCO 0.60 MB compressed, firmware 1.96 MB in total (58%) |
| Files in Velxio | max **4 million characters** per file | a model as a C array (~3 characters per byte) must stay under ~1.3 MB compressed, or be split |
| Network in Velxio | plain MQTT/HTTP only, **HTTPS fails** | models can't be downloaded at startup; they must be compiled in |
| Runtime | TensorFlow Lite Micro (`Chirale_TensorFlowLite`), **int8** `.tflite` | ops known to work: CONV_2D, DEPTHWISE_CONV_2D, FULLY_CONNECTED, AVERAGE/MAX_POOL_2D, ADD, MUL, CONCATENATION, PAD, PADV2, RESIZE_NEAREST_NEIGHBOR, LOGISTIC, SOFTMAX, RESHAPE, TRANSPOSE, SPLIT_V, GATHER, QUANTIZE; int8 CONCATENATION inputs must share one scale; no custom ops (e.g. `TFLite_Detection_PostProcess`) |
| Speed in Velxio | **~8 million multiply-adds per second** (reference kernels, no ESP-NN/SIMD): the 7.5 M MAC person model takes ~0.95 s, the 189 M MAC COCO detector ~70 s (sharing the CPU) | for a "live" feel (≤ ~1-2 s per frame) a model must stay **under ~10-15 M MACs** per frame; the real board is ~10-20x faster |
| Second core | usable (the detector runs there) | in Velxio both cores share the host's speed: a second model slows the first one down |
| Camera | 320x240 JPEG frames (your webcam, scaled); frame buffers must be in DRAM, so raw RGB frames that big don't fit | decoded into PSRAM; the detector gets real 320x240 detail; small objects (keys, pens) are still only a few pixels |
| Espressif ESP-DL models | need ESP-IDF components and the S3 vector instructions | not usable in Velxio's Arduino build (fine on a real board) |

**Models we compared (28 Nov, on test photos and in Velxio):**

| Job | Model | Work per frame | Result |
|---|---|---|---|
| Presence | Arshia's VWW 96x96 (in use) | 7.5 M | fast; yes/no only |
| Count | Swift-YOLO Nano person 192 (tag `board-v1`) | 186 M | accurate (4/4, 2/2 on photos) but ~45 s |
| Count | Swift-YOLO person 192 | 89 M | found only 2 of 4 people |
| Count | Swift-YOLO face 96 (until 28 Nov) | 22 M | a few seconds, but needs faces towards the camera: missed people standing |
| Count + items | **Swift-YOLO COCO 320 (in use, patched)** | 189 M | 80 classes incl. person; found tv, chairs, bed, plant, book, clock, people on COCO photos; ~95 s in Velxio; one run = count + items |
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
