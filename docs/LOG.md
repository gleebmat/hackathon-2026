# LOG: one section per agent

Write only in your own section. Each section has a **Status** line (replace it when it changes), a short
**Done** list, and **Requests** to others (`-> agent: ...`). Keep it short: details belong in PRs.

---

## tom-claude (Backend + Board)
**Status (17:50):** the board is live and tested. Starting on the backend stubs next.

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
- **Next session** (the lab may be reset). In VS Code, click into the terminal, then:
  1. Run `iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/main/bridge/setup.ps1 | iex`.
     It creates, builds and flashes the firmware in about 5 min.
  2. Run `python $HOME\bridge.py COM3` and keep that terminal open.
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
- Infineon examples we could flash in a later slot (each about 5 min to build and flash):
  - `mtb-example-psoc-edge-ml-aihub-deploy-vision`: **real-time person segmentation** from a USB camera. This is
    the basis for human presence.
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

## claude-2 (3D model)
**Status:** not started.

---

## claude-3 (Website UI)
**Status (18:30):** the dashboard layout runs on its own with mock data (branch `claude-3/ui-layout`). Next:
booking form, login, my bookings, lost & found.

**Done**
- `web/index.html`, `web/css/style.css`, `web/js/app.js`: dashboard with search bar, overview stats, building
  view, room panel (noise, people, today's bookings, LIVE badge on V.1.07a) and room list. Polls every 5 s.
- `web/js/api.js`: the only place that calls the backend. `?data=mock` or `?data=api` forces a source;
  otherwise it uses the API when `GET /api/rooms` answers, else the mock. A badge in the top bar shows which.
- `web/js/mock-data.js`: 24 made-up rooms and bookings, shaped exactly like the PLAN contracts. Delete it once the
  backend and `building_v.json` are live.
- Building view: loads `web/js/building3d.js` if it exists; otherwise a clickable 2D floor-plan placeholder with
  the same module API (`setStatus`, `focusRoom`, `showAll`, `setFloor`, `onRoomClick`).
- Tested in the browser at desktop and phone width: search (`1.07a`, unknown id), room selection, floor filter,
  live updates.

**Run without the backend**
`python -m http.server 5500 --directory web`, then open http://localhost:5500. The 404s in the console for
`/api/rooms`, `data/building_v.json` and `js/building3d.js` are the fallbacks and are expected.

**Decisions**
- Status colours follow the 3D model (free white, partial amber, full red, loud pulses red); LIVE is purple.
- V.1.07a with `live: false` shows "SENSOR OFFLINE" instead of LIVE.
- Times use the 24-hour clock.

**Requests**
- -> tom-claude: please add `web/js/api.js` and `web/js/mock-data.js` to claude-3's files in PLAN.md.
- -> tom-claude: the UI assumes these `purpose` values: `quiet_study`, `group_study`, `gaming`, `meeting`,
  `board_games`, `event`, `custom`. Please confirm or put the exact list in PLAN.md.
- -> claude-2: `createBuilding(el, buildingJson)` is called with the container already sized (min 300 px high).
  `onRoomClick` and `focusRoom` drive the room panel.

---

## gemini (Data, simulation, demo)
**Status:** not started.
