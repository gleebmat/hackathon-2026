# LOG: one section per agent

Write only in your own section. Each section has a **Status** line (replace it when it changes), a short
**Done** list, and **Requests** to others (`-> agent: ...`). Keep it short: details belong in PRs.

---

## tom-claude (Board + 3D map)
**Status (Sat):** the role is **Board** (the backend is gleb-claude's) plus the **3D campus map**, which is a
separate PR (`web/map3d/`, kept apart from the UI for now). Both board features work on the real hardware:
**noise** (microphone, session 1) and **person presence** (camera with YOLACT on the NPU, session 2), still as
two firmwares. `bridge.py` now posts **directly to the backend** (PLAN task 3). Not started on purpose: the
merged firmware and any people-count or lost-item model, since Arshia (gemini) is building those models.

**Direct path (PLAN task 3).** On the demo laptop:
1. Start the backend with a token: `READINGS_TOKEN=<token> uvicorn app.main:app`.
2. Run `cloudflared tunnel --url http://localhost:8000`. It needs no account; install it once with
   `winget install Cloudflare.cloudflared`. It prints an `https://….trycloudflare.com` URL.

On the lab PC, run `python $HOME\bridge.py COM3 <that URL> <token>`. Every 2 s it posts
`{room_id, presence, person_ratio, noise_avg_db, noise_peak_db}` (raw, the PLAN contract) plus `people` (0/1) and
`noise_db` (calibrated, quiet ≈ 35 dB), which the backend already understands. It retries on network errors and
reopens the serial port when it drops. Without a URL it falls back to ntfy. Tested against the real backend:
200 with the token, 403 without it, and V.1.07a showed the reading. There are 5 offline tests in
`bridge/test_bridge.py`.

**Done**
- `docs/PLAN.md`: product, contracts and roles.
- Board pipeline: the PSOC Edge E84 runs Infineon's unmodified `mtb-example-psoc-edge-pdm-pcm`, which prints a
  UART volume bar. `bridge/bridge.py` on the lab PC turns it into dB and publishes a reading every 5 s to
  https://ntfy.sh/aau-hack26-roomv-v107a.
- `bridge/ntfy_feed.py`: the backend consumer. It learns the lab's ambient floor, rescales to 35–90 dB, and sets
  `live` to False after 20 s without data. It has 8 tests that replay real board data (`python -m pytest bridge/`).
- Noise test with the Live Lab microphone streaming our voices to the board:

  | Phase | Raw avg / peak dB | Shown |
  |---|---|---|
  | Background | 61.1–61.8 / 73.8–76.1 | 35–39 dB, quiet |
  | Talking | 62.7–64.9 / 78.6–87.9 | about 45–59 dB, moderate |
  | Loud | 66.5–67.7 / 86.3–90.9 | 60 dB and up, loud |

  The reading reacts within one 5 s interval and drops back to quiet within one interval after the noise stops.

**Board reference (Live Lab)**
- **Developer Workspace:** a remote Windows PC with ModusToolbox 3.9, VS Code and Tera Term. It has internet and
  Python 3.12 + pyserial, but no git. The board's UART is COM3. The target is `APP_KIT_PSE84_EVAL_EPC2`.
- **Board Controls:** BTN1, BTN2, Reset, a potentiometer (0–1.8 V), and **Microphone → "Click here to Unmute"**,
  which streams our microphone to the board.
- **Every new session starts from a fresh lab PC** (no projects, empty `mtb_shared`), and the board is back on the
  factory firmware. Sessions end with a 4-minute warning, so plan about 10 min of setup per firmware.
- **Runbook for a session.** In the Developer Workspace, open VS Code from the taskbar, maximise it, click into the
  terminal, and type `cls` to check that the terminal has focus. Then type the command in 3 short chunks:
  - **Noise:** `iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/main/bridge/setup.ps1 | iex`.
    This takes about 5 min (create, build, flash).
  - **Presence:** `iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/main/bridge/setup_person.ps1 | iex`.
    This takes about 8 min: create about 3 min, build about 4 min (2,268 objects), flash about 1 min.
  - Then run `python $HOME\bridge.py COM3` and keep that terminal open. The bridge handles both firmwares: noise
    readings carry `noise_db`, presence readings carry `presence` and `person_ratio`.
- **Untested idea for a positive presence test.** First go to Application Demos → Vision Hand Gesture → Webcam
  Access → Enable, so the simulation display shows our webcam. Then switch to the Developer Workspace and run the
  presence runbook. If the simulation display keeps showing the webcam, the board will see us.
- **Gotchas:**
  - Typing into the remote PC drops characters and garbles long strings and double quotes. Type short chunks in
    single quotes.
  - Click in the terminal first: typing that lands in the editor has to be undone with File → Revert File.
  - Switching to "Application Demos" reflashes the factory firmware.

**Vision and presence on the board (tested 17:50–18:00)**
- **How the lab's vision works** (Live Lab User Manual v1.6): the board has a **USB camera** pointed at a second
  monitor, the "Vision Simulation Display". That monitor shows *our* browser webcam (Webcam Access → Enable). So
  any vision firmware sees whatever our webcam shows, and Chrome can pick any camera device, including a
  **virtual camera such as OBS playing a prepared video** (for example an empty classroom with a bag left
  behind). That gives a repeatable demo.
- Audio works the same way: a **speaker next to the board** plays our browser microphone, which is why the noise
  test worked. A lab microphone sends the room audio back to us.
- **On-board sensors** (kit user guide): PDM microphones, IMU (BMI270), magnetometer (BMM350), USB camera, and a
  4.3" display. There is **no radar** on this kit, and no radar examples are listed as Live Lab-supported.
- Supported in the Live Lab (official list): `ml-aihub-deploy-vision` (person segmentation and model-zoo
  detectors), `ml-deepcraft-deploy-vision`, `ml-face-id`, the sensor hub, and the IMU.
- Uploaded files land on the lab PC in `...\Imagimob Studio\USER_UPLOADED_FILE\`.
- Tom has the official docs pack offline (user guides, app notes, all supported code examples). Ask tom-claude
  for any detail from it.
- Factory demos tested with the webcam:
  - Hand Gesture runs at about 54 ms per frame.
  - **Face ID** runs at about 12 ms per frame, in inference mode, with 1 of 5 users already enrolled by someone
    else. Don't enrol faces: that stores biometric data.
- **Person presence on the board (session 2, tested).** I flashed Infineon's
  `mtb-example-psoc-edge-ml-aihub-deploy-vision` (YOLACT person segmentation, running on the NPU) with our
  `bridge/firmware/inference_task.c`.
  - The pipeline library has no API for its results, but it lights the USER LED while it sees a person. Our task
    samples that pin after each frame and prints `PRESENCE <0|1> <person_frames>/<frames>` once per second.
  - Result: about **10.6 inferences per second**. The EVK display shows "YOLACT PERSON SEGMENTATION" on the camera
    image (`docs/img/board-person-segmentation.png`). With only the static leaf picture on the simulation display
    the board correctly published `presence: false, person_ratio: 0.0` (`docs/img/bridge-presence-output.png`).
  - **Not yet tested:** the positive case with a person on the simulation display (we ran out of session time).
  - The DEEPCRAFT Model Zoo has many detectors (YoloX, SSDMobileNetV1/V2, TinyYolov2, SwiftYolo,
    Yolov8nPersonDetection), but **all of them are trained for persons only**, so they can't detect bags. Each
    comes with a prebuilt `.hex`.
  - **Lost items:** no ready model on the board. Options: (a) change detection: compare the empty room against a
    reference image and report "unknown object at seat X" without a label; (b) label the object off the board,
    using a COCO model in the backend, on a snapshot taken only when the board reports 0 persons;
    (c) train a backpack detector in DEEPCRAFT Studio, which is too slow for this weekend.
- Privacy design for the pitch: presence comes from people counts only. The camera checks for lost items only when
  the room is empty, everything runs on the board, and only labels leave it.

**Requests**
- -> Tom: book the next board slot for the final run and the demo recording.

---

## gleb-claude (Backend + integration)
**Status:** UI + 3D map + board bridge + backend are integrated on `main` and tested end to end in the browser;
43 API/bridge tests pass (`python -m pytest tests bridge`). Waiting for Arshia's two models (people count, lost
items) and a Live Lab session for the real-board run (runbook in `README.md`).

**Done**
- `app/`: FastAPI + SQLite. Login, sign-up, search-as-you-type, availability, bookings with every rule in PLAN
  (4 h/day cap, private or open to share, seats up to capacity, quiet vs loud, events private), cancel,
  suggestions on 409, ghost release after 10 min empty (`GHOST_RELEASE_MIN`), concurrency-safe storage.
- Integration: rooms come from `web/map3d/campus.json` (all 71 bookable rooms); the UI shows the 3D map
  (`app.js` loads `../map3d/building3d.js`); the board room is **Z.1.04** (`BOARD_ROOM`, bridge 4th argument),
  which turns LIVE while the bridge posts; `presence` maps to `people` 0/1; every other room is simulated
  (stable per minute, never ghost, empty rooms stay quiet; `SIMULATE=0` turns it off). `pyserial` added to
  requirements for the bridge tests.
- Browser test (fresh DB, token, 1-min ghost timer): login, map, search `z104`, book 21:00 shared, board reading
  with token (403 without) -> LIVE, then presence false -> ghost -> released after 1 min.

**Requests**
- -> tom-claude: `bridge.py` now defaults to room `Z.1.04` (4th argument to override). Next session: run the
  README runbook with the real board and confirm presence = 1 and the noise levels.
- -> gemini (Arshia): your people-count model posts `{"room_id": "Z.1.04", "people": <n>}` to
  `POST /api/readings` (header `X-Token`); lost items plug into the "Lost items" endpoints in PLAN.
- -> claude-3 (Martha): your UI is merged and wired to the 3D map; check the hero text and `.building` height I
  changed in `index.html` and `style.css`.

---

## claude-2 (3D model)
**Status:** not started.

---

## claude-3 (Website UI)
**Status (19:30):** the full frontend runs on the real backend (branch `claude-3/ui-layout`): login and sign-up,
search with suggestions, building view, booking sheet, my bookings. Tested in the browser. Next: lost & found
page (waits for `app/lost_items.py`), then the 3D model once claude-2 pushes it.

**Run it**
`pip install -r requirements.txt`, `uvicorn app.main:app --reload`, open http://localhost:8000 and log in as
`student1@edu.aau.at` / `demo`. The backend serves the files without cache headers, so after pulling new frontend
code press **Ctrl+Shift+R** (hard reload).

**Files** (all in `web/`; mock data is gone, everything is live from the API)
- `login.html`: log in and sign up (`/api/login`, `/api/register`), demo-account chips.
- `index.html` + `js/app.js`: building view on top, live room cards with filters (free, open to join, quiet),
  search with suggestions (`/api/search`, 150 ms debounce, arrow keys, `/` shortcut), booking sheet, my bookings
  drawer, profile menu, polling `/api/rooms` and `/api/bookings/mine` every 5 s.
- `js/api.js`: the only file that calls the backend; errors carry `{error, suggestions}`.
- `js/plan2d.js`: 2D floor plan with the 3D module API, used while `js/building3d.js` doesn't exist. Until
  `data/building_v.json` exists it lays the API rooms out in a ring around the courtyard.
- `css/style.css`: the **THEME block at the top** holds every colour, font, radius and animation speed. Presets
  violet / ocean / sunset / mint and light / dark / auto are switchable in the profile menu (saved per browser).

**Booking sheet** (clicking a room on the plan, a card, or a search result)
- 15 days (today + 14), 30-min slots 08:00–22:00 from `/availability`; past slots hidden. Tap a start, then an end.
- The form mirrors `app/booking.py`, so it only offers what the backend accepts: durations capped by free
  consecutive slots and by the 4 h/day limit (own bookings counted); "Private room" only when no one else booked
  that time; seats capped by capacity (private) or the lowest `seats_free` (shared); events force private; quiet
  vs loud purposes disabled when they would clash; own bookings shown as "yours", other rooms at that time as
  "booked". The backend still decides: 400/409 errors are shown, 409 suggestions open that room with the same
  time and settings.
- My bookings: grouped per day with hours used out of 4, "Now" tag, ghost countdown, "+ Add time" (opens the room
  at the booking's end time), two-tap cancel, history of past/cancelled/released.

**Tested (19:00–19:30, backend on a scratch DB with `NOISE_FEED=0`)**: login redirect, search `semi` / `107a`,
open from plan, card and search; book shared 3 people; join student2's shared room (max 4 seats, private
disabled); 409 "too noisy for quiet study" → suggestion → booked; add time up to exactly 4 h, then add disabled;
cancel; ghost countdown after `people: 0`; theme and dark mode; phone width. `pytest tests bridge`: 36 passed
(backend untouched).

**Decisions**
- Times from the API are campus time without a zone; the UI reads them as the browser's local time (fine in
  Klagenfurt).
- The UI is English, 24-hour clock. Fonts: Plus Jakarta Sans and Space Grotesk from Google Fonts.

**Requests**
- -> gleb-claude: please add `web/js/api.js` and `web/js/plan2d.js` to claude-3's files in PLAN.md.
- -> claude-2: `createBuilding(el, buildingJson)` gets `data/building_v.json`, or the generated ring layout until it
  exists; `setStatus(id, room)` receives the full room object from `/api/rooms` (uses `status`, `noise_class`,
  `live`); `onRoomClick` opens the booking sheet, `focusRoom`/`showAll` run when it opens and closes.
- -> gemini: once `building_v.json` lands, the plan uses its geometry automatically.
---

## gemini (Data, simulation, demo)
**Status:** not started.
