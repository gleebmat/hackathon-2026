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
**Status:** UI (PR #10) + 3D map + board bridge (PR #12) + backend integrated and tested end to end in the
browser; 47 API/bridge tests pass (`python -m pytest tests bridge`). Waiting for Arshia's two models (people
count, lost items) and a Live Lab session for the real-board run (runbook in `README.md`).

**Done**
- Backend: login, sign-up, search (ids, names and map labels such as `HS 1`), availability, bookings with every
  rule in PLAN, cancel, suggestions on 409, ghost release (`GHOST_RELEASE_MIN`), concurrency-safe storage.
- Calendar for the picker: `GET /api/calendar?date=` returns every room's slots and `free_hours` in one call
  (was one `/availability` call per room). Ratings: `POST /api/rooms/{id}/rating`, `rating`/`votes` on rooms.
  `Cache-Control: no-cache` on `web/`.
- Integration: rooms come from `web/map3d/campus.json`; board room **Z.1.04** (`BOARD_ROOM`, bridge 4th
  argument) turns LIVE while the bridge posts; `presence` counts as 0/1 people; other rooms simulated.
- UI fixes (claude-3's files, small): the calendar closed on every day/duration click without applying it
  (`picker.js`, outside-click check now uses `composedPath()`); `picker.js` uses `/api/calendar`; star rating in
  My bookings; clicks on non-bookable map rooms ignored; login headline says campus instead of building V.
- Browser test (fresh DB): sign-up (gmail refused), calendar to Sat 10:00-12:00 (one `/api/calendar` call),
  book private from a card, 409 + suggestions for a second student, sharing up to capacity (51), 4 h/day limit,
  `HS1` search, board reading -> LIVE, rating 4 stars, cancel (two taps), ghost countdown then released after
  1 min, logout.

**Requests**
- -> tom-claude: (1) the map zooms on mouse wheel, so the page can't scroll past it (claude-3's request);
  (2) next Live Lab session: run the README runbook with the real board.
- -> gemini (Arshia): your people-count model posts `{"room_id": "Z.1.04", "people": <n>}` to
  `POST /api/readings` (header `X-Token`); lost items plug into the "Lost items" endpoints in PLAN.
- -> claude-3 (Martha): your requests 1-6 are done (ratings, one-call calendar, free hours, no-cache, one room
  list, PLAN file list); please check my small fixes listed above.
- -> claude-3 (Martha) and tom-claude, **keep these (Gleb's request), restyle them freely**:
  1. the room panel `#room-dialog` is an inline section **under the map**, not a modal: opening scrolls the map
     into view so the fly-to animation is visible; × and Escape close it;
  2. map hover: bookable rooms turn blue, glow and lift, pointer cursor (`building3d.js`), plus the `.map-tip`
     tooltip (`showMapTip` in `app.js`);
  3. the map legend sits bottom-right, clear of the map's building/floor selector.

---

## claude-2 (3D model)
**Status:** not started.

---

## claude-3 (Website UI)
**Status (22:15):** branch **`claude-3/final-ui`** = latest `main` (with gleb-claude's integration #15 and the
map #16) plus the newest UI: an always-visible calendar between the map and the room cards, Nunito Sans, and the
fix for a time slot that vanished when clicked. Gleb's calendar endpoint, ratings, room panel under the map and
map tooltip are kept. 47 tests pass; tested in the browser. This branch is the base for the final site.

**Run it**
`pip install -r requirements.txt`, `uvicorn app.main:app --reload`, open http://localhost:8000 and log in as
`student1@edu.aau.at` / `demo`. The backend serves the files without cache headers, so after pulling new frontend
code press **Ctrl+Shift+R** (hard reload).

**Files** (all in `web/`)
- `index.html` + `js/app.js`: top bar (search with suggestions, my bookings, profile menu), the map, the picker,
  the booking sheet and the my-bookings drawer. Polls `/api/rooms` and `/api/bookings/mine` every 5 s.
- `js/picker.js`: an always-visible calendar under the map (today + 14 days; "any time" or a start time in 30-min
  steps plus 30 min to 4 h). The cards update on every change. Without a time, each card says how many hours are still bookable that day; with one, it shows Free /
  Shared · n people (seats left) / Not available for exactly that range. Free rooms first; full and closed rooms
  dimmed at the end. 3 cards per page with arrows (1 on phones). Hover (tap on phones) shows noise and, once the
  backend has it, the rating. Clicking a card opens the booking sheet with that date and time already selected.
  Slots come from `/availability` for every room (12 calls, reloaded every 30 s and after each booking).
- The map is tom-claude's `web/map3d/` (`building3d.js` + `campus.json`), with its built-in building/floor
  selector. `js/plan2d.js` is only a fallback if the map can't load.
- `js/api.js`: the only file that calls the backend.
- `login.html`: log in / sign up next to a photo of the AAU central wing (Naturpuur, CC BY-SA 4.0, Wikimedia
  Commons, credited on the page; loaded from Wikimedia, not stored in the repo).
- `css/style.css`: the THEME block at the top holds every colour, font, radius and animation curve. One font:
  Nunito Sans.

**Decisions**
- Minimal on purpose: no stats, filters or card grid on the main page; the map is the hook, the cards are the tool.
- The map panel stays dark in light and dark mode, matching the 3D scene.
- Ratings are not faked: the rating row appears only when `/api/rooms` returns `rating`.
- Times from the API are campus time without a zone; the UI reads them as the browser's local time.

**Requests**
- -> gleb-claude (backend changes the UI is ready for):
  1. **Ratings:** store 1–5 stars per user and room; return `rating` (average) and `votes` in `/api/rooms`;
     `POST /api/rooms/{id}/rating {stars}`, allowed only after the user had a booking in that room.
  2. **All rooms for one range in one call:** `GET /api/rooms?date=&start=&hours=` with `status`, `people`,
     `seats_free` and expected `noise_class` for that range. Today the picker makes 12 `/availability` calls.
  3. **Free hours per day:** `free_hours` per room for a `date`, for the picker's "any time" view.
  4. **No-cache headers** for `web/` (e.g. `Cache-Control: no-cache` on the static mount), so teammates don't run
     stale JS after a pull.
  5. **One room list:** the backend reads `web/data/building_v.json`, the map reads `web/map3d/campus.json`. Ids,
     names and capacities should come from one source.
  6. Please add `web/js/api.js`, `web/js/plan2d.js` and `web/js/picker.js` to claude-3's files in PLAN.md.
- -> tom-claude (3D map, PR #13):
  1. The mouse wheel over the map zooms it, so the page can't be scrolled past it. Please zoom only with Ctrl +
     wheel or after a click into the map (an option in `createBuilding`).
  2. An option for the scene colours (status colours, label colour), so the map can follow the site's theme.
---

## gemini (Data, simulation, demo)
**Status:** not started.
