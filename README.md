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
  (`web/img/login.jpg`). The 3D map opens on floor 1 (where the board room Z.1.04 is); "All floors" shows everything.
- **Notifications** (bell next to My bookings, unread counter, "Mark all as read"): booking starts in 10 min, ends in
  N min, time is over, ghost warning (nobody detected, released at HH:MM), booking released for inactivity, quiet room
  getting loud, something left behind, booked, cancelled. New ones also pop up as toasts; clicking one opens the room.
  Stored per account in the browser (`localStorage`), so each comes once, also across reloads; they follow the
  language switch.
- **Booking rules:** only rooms with **fewer than 55 seats** can be booked (`BOOKABLE_BELOW` in `app/booking.py`); lecture
  halls, the Aula and the atrium show live status only: status `unbookable`, "🔒 Not bookable" in the panel and the
  search, dark and see-through with a "🔒 55+" badge on the map, no room cards, closed slots, skipped by the assistant
  and suggestions, and the campus simulator doesn't book them. People sitting in a room without a booking take seats from
  sharers but **don't block booking the whole room** (a private booking just moves them out).
- **Room display (board room):** the board has no display or speaker, so when it runs the backend opens a small
  window (Edge or Chrome) that acts as its touch display: book-a-room QR, soundscapes, selfie QR (your webcam),
  take a break, quiet room, emergency; big swipeable cards sized for the E84 kit's 4.3" 800x480 screen
  (`web/display.html`, API in `docs/PLAN.md`, "Room display"). It closes when the board stops. Chrome somewhere else:
  set `DISPLAY_BROWSER`. Without the board: `$env:DISPLAY_TOKEN='dev-display'`, start the backend, open
  http://localhost:8000/display.html?room=Z.1.04&token=dev-display.
- **Public website:** `python tools/tunnel.py` (backend running) prints a public `https://...trycloudflare.com`
  address for phones and the jury; the display's QR codes use it. New address on every start. Needs `cloudflared`
  (`winget install --id Cloudflare.cloudflared`). Anyone with the link can use the site and the demo accounts.
- **Port:** any free port works (`uvicorn app.main:app --port 8011` is fine too). The board doesn't talk to the
  port: it publishes to an MQTT broker and the backend subscribes, so only the browser URL changes.
- **Database:** a local SQLite file (`campus.db`, or `DB_PATH`), gitignored. Accounts, sessions, bookings and
  ratings stay there across restarts, pulls and new commits; schema changes are migrated in place
  (`app/db.py: upgrade`). Only the board readings table is rebuilt when its columns change. Every machine has its own
  database, so an account made on Gleb's laptop doesn't exist on yours. The demo accounts are recreated if missing.
  Delete `campus.db` for a clean start.

## The board: XIAO ESP32S3 Sense in Velxio

**How it works** (`firmware/xiao_sense/sketch.ino` + `app/vision.py`). The board is the room's eyes and ears; the
heavy recognition runs on the laptop, so results reach the website in about **1 s**:
- **Camera:** the board grabs a raw 320x240 frame (RGB565), encodes it as JPEG (~6 KB) and sends it, encrypted with
  AES-128 (counter mode), over MQTT to `aau-hack26/rooms/Z.1.04/frame`, about every 0.6 s in Velxio. Encrypted
  because the broker is public. The key is `firmware/xiao_sense/frame_key.h`, made once with
  `python tools/make_frame_key.py`; the same file must be in the Velxio project, and the backend reads it too (or
  `FRAME_KEY`). Without the key file the board falls back to Arshia's 96x96 person model on the board (yes/no only).
- **Detection on the laptop:** `app/vision.py` runs **YOLO11s** (Ultralytics, COCO classes, exported to
  `models/yolo11s_640.onnx`, onnxruntime on the CPU, ~150 ms per frame) on the newest frame only, so nothing queues
  up. The 320x240 frame is upscaled to 640, so small and far people are still found (12 of 12 and 32 of 32 on
  crowd test pictures, where YOLO11n at 320 found none). It counts **people** (score 0.45+) and things people forget:
  **backpack, handbag, bottle, cup, laptop, mouse, cell phone** (0.50+; suitcase, umbrella and book are left out because a
  table was taken for a suitcase), but only **within about
  3 m**: the distance is estimated from the box size and the thing's typical size (`ITEM_MAX_M`, default 3.5;
  `CAMERA_FOV`, default 65 degrees). The backend console prints what the camera sees whenever it changes
  (`camera: Z.1.04: 0 people, left items 1 | this frame: 0 people, items backpack 0.81 at ~1.9 m`).
- **Steady results:** the count is the median of the last 3 frames, the room is empty only when none of them shows
  a person, and **left items** = such things seen in 3 of the last 4 frames after nobody was seen for 3 frames
  (about 3-4 s after the last person leaves). While the
  camera detector counts a room, the board's own presence is ignored and only its noise reading is used.
- **Noise:** the PDM microphone (RMS mapped to about 30-90 dB), sent as JSON to `aau-hack26/rooms/Z.1.04/readings`:
  `{"room_id":"Z.1.04","noise_db":37.2}`. The backend (`app/mqtt_feed.py`) subscribes to both topics.
  The LIVE badge goes off 3 s after the last reading (board stopped) and comes back with the next one.
- Earlier on-board versions (face detector, COCO detector on the board, ~1 min per result in Velxio) are in the git
  history and the tag `board-v1`.

**Velxio setup (team account).** Log in at https://velxio.dev with the team's (Gleb's) account and open the project
**TODAREISTODO** (https://velxio.dev/gleebmat/todareistodo). It has `sketch.ino`, `person_model.h`, `frame_key.h`
and the libraries `Chirale_TensorFlowLite` and `PubSubClient` (Library Manager). GitHub is the master copy for the
sketch: after changing it here, paste it into Velxio and save.

**The demo key is in the repo on purpose** (`firmware/xiao_sense/frame_key.h`, the same as in the Velxio project),
so the jury and anyone who clones the repo can run board + backend right away; it may be shared. Anyone with it can
decrypt the camera frames on the public broker, so for real use make a new key (`python tools/make_frame_key.py`),
put it in the Velxio project and keep it out of git.
1. Start the backend with short demo timers:
   ```powershell
   $env:GHOST_GRACE_SECONDS = '5'; $env:GHOST_RELEASE_SECONDS = '15'; uvicorn app.main:app
   ```
2. In Velxio, under the board, switch on **Camera** (your webcam) and **Mic** (your microphone; when it's off you
   get a 440 Hz test tone), allow both in Chrome, then **Run**. The serial monitor shows `CAM OK (320x240)`,
   `FRAMES ON`, `MIC OK`, `WIFI OK`, then one `frame N bytes -> sent` line per frame.
3. Open http://localhost:8000: Z.1.04 carries a board badge on the 3D map (red "LIVE" while the board sends, grey
   "OFFLINE" otherwise). Open the room (search `z104`): a live card shows the people count with person icons, the
   noise in dB on a meter and the last minute of noise as a line. Z.1.04 shows **LIVE**, the noise and "1 person here now". Book it
   and step out of the webcam: after 5 s the booking is marked ghost (violet on the map) and after 15 s it's
   released. Two people in view show as 2 about a second later. Leave a bag, phone or bottle within ~3 m and
   step out: a few seconds later the panel shows "🎒 Something left behind".

**Troubleshooting**
- *Count stays empty but frames are sent:* the backend has no key or a different one (it logs "Camera frames off" or
  "Frame from ... could not be read"); make sure `firmware/xiao_sense/frame_key.h` is the same as the one in the Velxio project and restart it.
- *Velxio's camera in JPEG mode returns cut-off frames* (only the top third), and the AES unit's bulk mode can't read
  PSRAM there; that's why the sketch captures RGB565, encodes JPEG itself and runs AES block by block.
- *Two boards:* only run the project in one browser tab. Every running tab publishes to the same topic.
- *HTTPS from the simulated board fails* (`ssl ... fatal alert`); plain MQTT/HTTP works.
- *Website shows the board offline:* the simulation is stopped or WiFi failed; the serial monitor says which.

**Placement: how to get reliable results**
- *People:* YOLO finds whole or partial people from any side, as long as they are not tiny in the 320x240 picture.
  Good light helps; a backlit person (window behind) is harder.
- *Left items:* only backpack, handbag, laptop, mouse, phone, bottle or cup, clearly visible,
  within ~3 m of the camera. Any of them in view while nobody is in the room counts as left behind; the backend
  console says what was seen and how far away it seemed.

## Board limits (the brief for choosing models)

Everything below was measured in Velxio on 28 Nov; any new model has to fit it.

| Limit | Value | What it means for a model |
|---|---|---|
| Chip | ESP32-S3, 2 cores at 240 MHz, 512 KB SRAM, **8 MB PSRAM**, 8 MB flash | weights and working memory (tensor arena) go in PSRAM; a few MB is fine |
| App flash in Velxio | **3 MB** (custom `partitions.csv` is ignored); the firmware itself is ~1.4 MB | **~1.6 MB left for models**, more if zlib-compressed (int8 weights shrink ~20-30%); today: firmware 0.92 MB in total (30%), only the 0.33 MB person model on board |
| Files in Velxio | max **4 million characters** per file | a model as a C array (~3 characters per byte) must stay under ~1.3 MB compressed, or be split |
| Network in Velxio | plain MQTT/HTTP only, **HTTPS fails** | models can't be downloaded at startup; they must be compiled in |
| Runtime | TensorFlow Lite Micro (`Chirale_TensorFlowLite`), **int8** `.tflite` | ops known to work: CONV_2D, DEPTHWISE_CONV_2D, FULLY_CONNECTED, AVERAGE/MAX_POOL_2D, ADD, MUL, CONCATENATION, PAD, PADV2, RESIZE_NEAREST_NEIGHBOR, LOGISTIC, SOFTMAX, RESHAPE, TRANSPOSE, SPLIT_V, GATHER, QUANTIZE; int8 CONCATENATION inputs must share one scale; no custom ops (e.g. `TFLite_Detection_PostProcess`) |
| Speed in Velxio | **~8 million multiply-adds per second** (reference kernels, no ESP-NN/SIMD): the 7.5 M MAC person model takes ~0.95 s, the 189 M MAC COCO detector ~70 s (sharing the CPU) | for a "live" feel (≤ ~1-2 s per frame) a model must stay **under ~10-15 M MACs** per frame; the real board is ~10-20x faster |
| Second core | usable (the detector runs there) | in Velxio both cores share the host's speed: a second model slows the first one down |
| Camera | 320x240 RGB565 frames fit in DRAM; JPEG mode returns cut-off frames in Velxio | encode JPEG on the board (`frame2jpg`, ~0.4 s); small objects (keys, pens) are only a few pixels |
| Espressif ESP-DL models | need ESP-IDF components and the S3 vector instructions | not usable in Velxio's Arduino build (fine on a real board) |

**Models we compared (28 Nov, on test photos and in Velxio):**

| Job | Model | Work per frame | Result |
|---|---|---|---|
| Presence | Arshia's VWW 96x96 (in use) | 7.5 M | fast; yes/no only |
| Count | Swift-YOLO Nano person 192 (tag `board-v1`) | 186 M | accurate (4/4, 2/2 on photos) but ~45 s |
| Count | Swift-YOLO person 192 | 89 M | found only 2 of 4 people |
| Count | Swift-YOLO face 96 (until 28 Nov) | 22 M | a few seconds, but needs faces towards the camera: missed people standing |
| Count + items | Swift-YOLO COCO 320 on the board (patched) | 189 M | 80 classes incl. person; ~95 s per result in Velxio: too slow |
| Count + items | YOLO11n 320 on the laptop | 3.3 G FLOPs | ~20 ms; fine for 1-2 people, but 0 of 12 on crowd pictures; few items |
| Count + items | **YOLO11s 640 on the laptop (in use)** | 21.5 G FLOPs | ~150 ms; 8/8, 12/12, 32/32 on crowd pictures; on coco128 at webcam size 2x the items of 11n at 320 |
| Count + items | YOLO11m 640 on the laptop | 68 G FLOPs | ~400 ms; a few more items, no better count |
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
