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

## gleb-claude (Backend)
**Status:** backend done on `gleb/backend` (PR), 14 API tests pass (`python -m pytest tests bridge`).

**Done**
- `app/`: FastAPI + SQLite. Login, sign-up, rooms with search, per-room availability, bookings with every rule
  in PLAN (4 h/day cap, sharing up to capacity, quiet vs loud, events full), cancel, suggestions on 409,
  sensor readings, ghost-booking release, live board noise for V.1.07a from `bridge/ntfy_feed.py`.
- Run: `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`. Serves `web/` at `/` once it exists.

**Requests**
- -> tom-claude: the backend is ours now (PLAN roles updated), so please don't build `app/`. Lost items go in
  `app/lost_items.py` as an `APIRouter`; tell me and I'll include it. Send the board's person count for V.1.07a
  to `POST /api/readings` (`{room_id, people}`); that drives presence and ghost release.
- -> gemini: `sim/simulate.py` should post `{room_id, noise_db, people}` to `POST /api/readings`; leave some
  booked rooms at `people: 0` to demo ghost bookings. Only floor 1 rooms are used.
- -> claude-3: use `GET /api/rooms/{id}/availability` for the slot picker and the `ghost`/`closed` statuses.

---

## claude-2 (3D model)
**Status:** not started.

---

## claude-3 (Website UI)
**Status:** not started.

---

## gemini (Data, simulation, demo)
**Status:** not started.
