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

**What runs on the board** (`firmware/xiao_sense/sketch.ino`, one reading per camera frame, ~1 s in the simulator or ~2 s while the people counter runs; the website polls every 1 s and the open room panel every 0.5 s):
- **Presence:** Arshia's 96x96 person model (`models/vww_96_int8.tflite`, as a C array in `person_model.h`) with
  TensorFlow Lite Micro. It says yes/no (score 0..1): present at once when one frame scores 0.70+, or when 2 of the last 3 frames reach 0.60; gone when 2 of 3 drop below 0.60. It can't count.
- **People count** (switch `COUNT_PEOPLE` at the top of the sketch, on by default): Seeed's Swift-YOLO Nano person
  detector (`models/swift_yolo_nano_person_192_int8.tflite`, 192x192, found 4/4 and 2/2 people on test photos) runs
  on the second CPU core while someone is present. In Velxio one count takes **about 45 s** (2.6 s on a real board),
  and the presence check slows from ~1 s to ~2 s per frame while it runs. The model is zlib-compressed in
  `count_model_1.h` + `count_model_2.h` (Velxio builds files up to 4 million characters; regenerate with
  `python tools/make_count_header.py models/swift_yolo_nano_person_192_int8.tflite firmware/xiao_sense`).
  **To go back to presence only:** set `#define COUNT_PEOPLE 0` (the two count files can then be deleted).
- **Noise:** the PDM microphone (RMS mapped to about 30-90 dB).
- **Left items:** a comparison with an empty-room snapshot (details and placement tips below).
- One JSON reading per check goes over MQTT to `broker.hivemq.com:1883`, topic `aau-hack26/rooms/Z.1.04/readings`:
  `{"room_id":"Z.1.04","noise_db":37.2,"presence":true,"person_score":0.91,"left_items":0}`.
  The backend (`app/mqtt_feed.py`) subscribes and stores it like `POST /api/readings`. Readings older than 10 s
  count as "board offline".

**Velxio setup (team account).** Log in at https://velxio.dev with the team's (Gleb's) account and open the project
**TODAREISTODO** (https://velxio.dev/gleebmat/todareistodo). It already has `sketch.ino`, `person_model.h`,
`count_model_1.h`, `count_model_2.h` and the
libraries `Chirale_TensorFlowLite` and `PubSubClient` (Library Manager). GitHub is the master copy: after changing
the sketch here, paste it into Velxio (or the other way round) and save (File > Save project).
1. Start the backend with short demo timers:
   ```powershell
   $env:GHOST_GRACE_SECONDS = '5'; $env:GHOST_RELEASE_SECONDS = '15'; uvicorn app.main:app
   ```
2. In Velxio, under the board, switch on **Camera** (your webcam) and **Mic** (your microphone; when it's off you
   get a 440 Hz test tone), allow both in Chrome, then **Run**. The first compile takes a few minutes; after that
   the build cache makes it fast. The serial monitor shows `CAM OK`, `MODEL OK`, `MIC OK`, `WIFI OK`, then one
   `person=... present=... left=...` line and one `MQTT ... -> sent` line per check.
3. Open http://localhost:8000 and search `z104`. Z.1.04 shows **LIVE**, the noise and "Someone is here". Book it
   and step out of the webcam: after 5 s the booking is marked ghost (violet on the map) and after 15 s it's
   released. Leave an object and step out: the panel shows "🎒 Something left behind".

**Troubleshooting**
- *Compile error "control reaches end of non-void function" or a cut-off sketch:* the paste was truncated (the
  editor is slow with long pastes). Check that `sketch.ino` ends with `loop()`'s closing brace, then paste again.
- *Two boards:* only run the project in one browser tab. Every running tab publishes to the same topic.
- *"Smallest app partition is 0x300000" / "app partition is too small":* the firmware is over 3 MB. Velxio ignores a
  custom `partitions.csv`, so models must be compressed (as the count model is) or smaller.
- *HTTPS from the simulated board fails* (`ssl ... fatal alert`); plain MQTT/HTTP works. So models can't be downloaded
  at startup from GitHub.
- *A file "larger than 4 million characters":* Velxio won't build it; split it (see the count model files).
- *Website shows the board offline:* the simulation is stopped or WiFi failed; the serial monitor says which.

**Placement: how to get reliable results**
- *People:* the model sees a 96x96 picture of the whole view, so a person must be clearly visible: upper body and
  face, roughly the middle of the frame, not just a shoulder at the edge. Half-visible people at the edge are often
  missed (score below 0.6). Good light helps; a backlit person (window behind) scores low.
- *Left items:* the board compares the frame with a **snapshot of the empty room**. It takes that snapshot by itself
  whenever the view is empty and still for about 3 checks (person score below 0.45, nothing moving), so after Run
  keep the view empty for ~5 s until serial prints `Empty-room baseline ready`. **Or take it yourself:** with the
  view empty, type `snapshot` in the serial monitor and press Send; the board keeps that picture until the next
  `snapshot` (`show` prints the reference as text art, `auto` goes back to automatic snapshots). When people were there and leave,
  every change against that snapshot that stays in place for 3 checks counts. So:
  - put the object **inside the view, away from the left, right and top edges** (changes touching those edges are
    treated as a person walking out); the bottom edge (the desk) is fine;
  - the object must be clearly visible in a 96x96 picture: a bottle, a phone or a bag works, a key or a pen is too
    small; it should contrast with what's behind it (a dark bag on a dark chair is hard);
  - when you leave, leave completely and don't move the camera or the chair (a moved chair is a change too; a
    camera nudge of up to 3 px is compensated, and smooth light changes are ignored);
  - remove the object and it goes back to 0; after 5 clean checks the board keeps refreshing its snapshot again.

## Board limits (the brief for choosing models)

Everything below was measured in Velxio on 28 Nov; a model for left items (or a faster people count) has to fit it.

| Limit | Value | What it means for a model |
|---|---|---|
| Chip | ESP32-S3, 2 cores at 240 MHz, 512 KB SRAM, **8 MB PSRAM**, 8 MB flash | weights and working memory (tensor arena) go in PSRAM; a few MB is fine |
| App flash in Velxio | **3 MB** (custom `partitions.csv` is ignored); the firmware itself is ~1.4 MB | **~1.6 MB left for models**, more if zlib-compressed (int8 weights shrink ~20%), see `tools/make_count_header.py` |
| Files in Velxio | max **4 million characters** per file | a model as a C array must be split (as `count_model_1.h` / `_2.h`) |
| Network in Velxio | plain MQTT/HTTP only, **HTTPS fails** | models can't be downloaded at startup; they must be compiled in |
| Runtime | TensorFlow Lite Micro (`Chirale_TensorFlowLite`), **int8** `.tflite` | ops known to work: CONV_2D, DEPTHWISE_CONV_2D, FULLY_CONNECTED, AVERAGE/MAX_POOL_2D, ADD, MUL, CONCATENATION, PAD, PADV2, RESIZE_NEAREST_NEIGHBOR, LOGISTIC, SOFTMAX, RESHAPE, TRANSPOSE, SPLIT_V, QUANTIZE; no custom ops (e.g. `TFLite_Detection_PostProcess`) |
| Speed in Velxio | **~8 million multiply-adds per second** (reference kernels, no ESP-NN/SIMD): the 7.5 M MAC person model takes ~0.95 s, Swift-YOLO Nano (186 M MACs) ~45 s | for a "live" feel (≤ ~1-2 s per frame) a model must stay **under ~10-15 M MACs** per frame; the real board is ~10-20x faster |
| Second core | usable (the people counter runs there) | in Velxio both cores share the host's speed: a second model slows the first one down |
| Camera | 96x96 RGB565 frames (your webcam, scaled) | models get a 96x96 picture (bigger input = upscaled, no extra detail); small objects (keys, pens) are only a few pixels |
| Espressif ESP-DL models | need ESP-IDF components and the S3 vector instructions | not usable in Velxio's Arduino build (fine on a real board) |

**What we are looking for (left items):** an int8 TFLite object detector for 96x96 input, under ~15 M MACs and ~1.5 MB,
with classes like backpack, handbag, suitcase, laptop, cell phone, bottle, book, umbrella (COCO has all of them).
Pretrained models that small only exist for "person", so it will most likely be a **FOMO** model (Edge Impulse,
MobileNetV2 0.35 backbone, 96x96, a few M MACs, outputs object centres that can be counted) trained on that COCO
subset, ideally with a "person" class too so it can replace both current models.

## Graphify (code knowledge graph, saves AI tokens)

Install once on your machine, then run the setup inside this repo:

```bash
pip install graphifyy          # or: uv tool install graphifyy
graphify install --platform claude
graphify claude install        # adds Claude hooks to your local .claude/settings.json
graphify hook install          # keeps the graph updated after each commit
```

Restart Claude Code afterwards. The graph lives in `graphify-out/`.
