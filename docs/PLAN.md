# PLAN: Smart Campus Room Booking (Infineon challenge), building V

**Every agent: read this file and `docs/LOG.md`, find your role below, and log your work in your section of
`docs/LOG.md`.** Don't create other Markdown files.

## Product
This is a website for AAU students. A student logs in, finds a room on a **3D map of the campus** (buildings V,
N, Z, L and S), and books it.
- **Login:** 4 demo accounts (`student1..4@edu.aau.at`, password `demo`), plus **sign-up** with any `@edu.aau.at`
  email and a password of 4+ characters. The repo is public, so never put real emails in it.
- **Rooms:** every room the map marks `bookable` (71 seminar rooms, lecture halls and the atrium, all floors).
- **The board room is `Z.1.04`** (seminar room, 51 seats, in the central building Z). It is the only room with
  real sensor data from the PSOC Edge E84; it shows a LIVE badge while the board is sending. Every other room is
  simulated. Change it with `BOARD_ROOM` in the backend and the 4th argument of `bridge.py`.
- **Booking options:**
  - Time: 30-minute slots from 08:00 to 22:00, 0.5–4 h per booking, and **at most 4 h per student per day**.
    Picking a room shows every slot of the day as free, shared, full, closed or past.
  - **Full** (the whole room) or **partial** (sharing is fine, with a number of seats).
  - **Purpose:** quiet study, group study, gaming, meeting, board games, event, or custom text.
  - **Sharing:** a partial booking means "others may join". Another student joins by booking the same room as
    partial with their number of people; all seats together never exceed the room's capacity.
- **Ghost bookings:** the board (or the simulator) reports the people count. When a booked room is empty, a
  10-minute timer starts: at the start of the booking, or when everyone leaves. If nobody is back when it runs
  out, the booking is released and its time slots are free again. Meanwhile the room shows as `ghost` with the
  release time. A sensor that goes silent for over 2 minutes never releases anything.
- **Search:** typing a room number or name shows suggestions as you type (`z104`, `Z.1.04`, `107a` and `atrium`
  all work; the building letter may be left out), like campusplan.aau.at.
- **Noise detector for partial bookings:** every room shows a live noise level, so someone who wants silence can
  choose another room.
  - **Z.1.04 is measured by the PSOC Edge E84 microphone** (our laptop mic, played into the Live Lab).
  - The other rooms are simulated by the backend: random but the same for everyone, changing every minute.
- **People** per room. Z.1.04 gets presence (0 or 1 person) from the board's person detection; a real count comes
  later from Arshia's model. The other rooms are simulated from their bookings, plus a few walk-ins.
- **Lost & found:** after a booking ends and the board reports 0 persons, the system detects items left behind
  (e.g. "backpack at seat area 3") and tells the student who booked the room. Details are under "Lost items" below.
- **3D view:** the campus map (`web/map3d/`) is on the main page: rotate, zoom, click a room to book it; searching
  flies the camera to the room and highlights it.

All numbers are made up. This is a prototype.

## Roles
| Agent | Owns (only edit these, plus your section of `docs/LOG.md`) | Delivers |
|---|---|---|
| **gleb-claude** (Gleb's Claude Code): Backend | `app/` (except `app/lost_items.py`), `tests/`, `requirements.txt`, `.env.example` | FastAPI + SQLite: login, sign-up, rooms (from the map), search, availability, bookings, the booking rules, ghost release, board readings for Z.1.04 and the simulation of every other room (**done**, see API below). Integrates UI + map + board. |
| **tom-claude** (Tom's Claude Code): Board | `bridge/` | Board bridge (noise and presence work, as separate firmwares). Next: see "Board (Live Lab): decisions and next steps". |
| **tom-claude**: 3D map (claude-2's role) | `web/map3d/`, `tools/campus3d/` | **Done:** a Three.js campus map of buildings V, N, Z, L and S with search, glow highlight, building and floor isolation, 3D room numbers and status colours. See "3D campus map" below. Standalone until the team decides how to combine it with the UI. |
| **claude-3**: Website UI | `web/index.html`, `web/login.html`, `web/js/app.js`, `web/js/api.js`, `web/js/plan2d.js`, `web/css/style.css` | **Done** and wired to the 3D map. The login page, the search bar (calls `focusRoom`), the room panel (live noise, people, today's bookings, a LIVE badge on the room with `board: true`), the booking form (hours, full or partial, seats, purpose, and suggestions on a 409), and "my bookings"., and the **Lost & found** page: item cards, a "That's mine" button, and a "maybe yours" banner. |
| **tom-claude**, continued | `detector/`, `app/lost_items.py` (a FastAPI `APIRouter` that gleb-claude includes in `app/main.py`) | The lost-item service: snapshot vs reference diff, YOLOv8n labels, crops, and the endpoints below. Board: flash person detection and forward the person count through the bridge. |
| **gemini** (Arshia, Gemini Pro): Models, demo | `models/` (new), `README.md` | **Two models, added later:** (1) counting people in the board room, (2) finding lost items. They plug into `POST /api/readings` (`people` as a number) and the "Lost items" endpoints below. Also the demo script and the pitch. Room data and simulation are no longer gemini's: rooms come from the map, and the backend simulates the other rooms. |

## Architecture
```
PSOC Edge E84 (Live Lab) -> UART -> bridge.py on the lab PC -> HTTPS (cloudflared tunnel, X-Token)
                                                                       |  POST /api/readings, room Z.1.04
web/ (UI + map3d/, Three.js from CDN) <-- JSON --> FastAPI + SQLite (app/) <-+
                                                   (simulates every other room; rooms from web/map3d/campus.json)
```
Fallback without a tunnel: `bridge.py` publishes to ntfy.sh and `bridge/ntfy_feed.py` in the backend reads it
(noise only, and ntfy's daily limit applies).
- **Stack:** Python 3.12, FastAPI, the standard-library `sqlite3`, and static HTML/JS with Three.js from a CDN
  (pin an exact version, e.g. `three@0.160.0`), so there is no build step.
- **Run:** `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`, then open http://localhost:8000.
  The backend serves `web/` at `/`.

## Board (Live Lab): decisions and next steps for tom-claude
**How it works.** The PSOC Edge E84 is a microcontroller (Cortex-M33 + Cortex-M55 + Ethos-U55 NPU), not an
FPGA; call it "the board" or "PSOC Edge E84" in the pitch. It sits in Infineon's remote Live Lab and represents
one room, **Z.1.04** (seminar room in the central building). Our laptop's microphone plays through a speaker next to the board, and our
webcam is shown on the lab's simulation display that the board's USB camera films. **The board measures noise
and detects people itself**; only its results leave it.

**Target data path (decided):**
```
laptop mic/webcam -> Live Lab speaker/display -> board (mic + camera, NPU) -> UART -> bridge.py on the lab PC
  -> HTTPS POST <tunnel URL>/api/readings (header X-Token) -> backend on the demo laptop (cloudflared tunnel)
```
- **Why not ntfy:** ntfy.sh allows 250 messages per day per IP. At one reading every 5 s that is used up in
  about 20 minutes, and the lab PC may share its IP with other teams. Keep ntfy only until the direct path works.
- **Why noise and presence aren't both live yet:** the chip runs one firmware at a time, and we use two separate
  Infineon examples. The hardware can do both; it needs **one merged firmware**.

**Tasks for tom-claude, in this order**
1. **Test the positive presence case first** (never tested): with the current presence firmware, put a person
   on the simulation display (Webcam Access → Enable) and confirm `PRESENCE 1`. Also confirm the USER LED is not
   lit for any other reason (a blinking heartbeat would give false positives). Record the result in LOG.
2. **Merged firmware:** start from `mtb-example-psoc-edge-ml-aihub-deploy-vision` (our `inference_task.c`) and
   add the PDM microphone capture from `mtb-example-psoc-edge-pdm-pcm` as a second FreeRTOS task. Print once per
   second, next to the presence line:
   `PRESENCE <0|1> <person_frames>/<frames>` and `NOISE <avg_db> <peak_db>`.
   Check first whether the PDM pins and clocks must be enabled in the vision project's Device Configurator
   (`design.modus`). Keep `setup_person.ps1` as the fallback if the merge doesn't work within one session.
3. **Done:** `python bridge.py COM3 <tunnel URL> <token>` posts one reading every 2 s to
   `POST <tunnel URL>/api/readings` with header `X-Token: <token>`:
   `{"room_id": "Z.1.04", "presence": true, "person_ratio": 0.9, "people": 1, "noise_avg_db": 63.2,
   "noise_peak_db": 78.5, "noise_db": 47.0}`. The bridge calibrates `noise_db`; the backend uses `people`
   (or `presence`) and `noise_db`, and ignores the raw fields. Tested end to end against the backend.
4. **Done:** LOG role fixed; the 3D map is tom-claude's (`web/map3d/`).
5. **Next live session:** run the demo runbook in `README.md` end to end with the real board.

**Demo notes**
- Use headphones or mute the laptop speakers: the lab sends its room audio back, which can echo.
- Keep loud phases short (under about a minute): the noise floor is learned from the last 3 minutes.
- Start the backend with `GHOST_RELEASE_MIN=1` for the demo, so a ghost booking is released within the pitch.
- Pitch wording: presence and noise are computed on the board, and only a yes/no and a level leave it. Don't
  claim a people count or on-board lost-item detection until those exist.
- **People count and lost items:** Arshia (gemini) is looking for a model that counts people and finds items;
  that comes later. The backend already accepts `people` as a number.

## Contracts (code against these; whoever changes one updates this file in the same PR)

### Rooms: `web/map3d/campus.json` is the single source (tom-claude; read by the backend, the map and the UI)
- The backend books exactly the rooms with `"bookable": true`, using their `id`, `floor`, `name` and `capacity`
  (an optional `"closed": true` makes a room unbookable today). Change rooms there, never in the backend; the
  backend picks them up on restart. Room ids must stay unique, and `Z.1.04` (the board room) must exist.
- `web/data/building_v.json` is no longer used. `DEFAULT_ROOMS` in `app/db.py` is only a fallback for the tests.

### API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)
Every error is `{error: "message to show"}` with 400 (bad input), 401 (not logged in), 403, 404 or 409 (the room
can't take it). Times are campus time (Europe/Vienna) without a zone: `"2026-11-27T14:00"`.
| Method | Path | Body / result |
|---|---|---|
| GET | `/api/search?q=&limit=8` | search-as-you-type: `[{id, name, floor, status, seats_free}]`, best match first; `[]` for an empty `q` |
| POST | `/api/register` | `{email, password, name?}` returns 201 `{email, name}` and logs in. 400 if the email isn't `@edu.aau.at` or the password is under 4 characters, 409 if the account exists |
| POST | `/api/login` | `{email, password}` sets a session cookie. `POST /api/logout`, `GET /api/me` returns `{email, name}` or 401 |
| GET | `/api/rooms?q=` | `[{id, floor, capacity, name, status, noise_db, noise_class, people, seats_free, live, sensor, ghost_release_at, bookings_now:[{id, mode, purpose, seats, end, shareable}]}]`; poll it every few seconds to colour the 3D model. `q` filters like `/api/search` |
| GET | `/api/rooms/{id}` | the room above plus `bookings_today:[booking]` |
| GET | `/api/rooms/{id}/availability?date=YYYY-MM-DD` | `{room_id, date, open, close, slots:[{start:"HH:MM", end, status, seats_free, shareable, noise}]}`; slot `status` is `free`, `partial`, `full`, `closed` or `past` |
| POST | `/api/bookings` | `{room_id, start:"YYYY-MM-DDTHH:MM", hours, mode:"full"|"partial", seats, purpose, custom_purpose}` returns 201 with the booking, or `409 {error, suggestions:[room_id,...]}` |
| GET | `/api/bookings/mine` | the user's bookings, newest first |
| DELETE | `/api/bookings/{id}` | cancels one of the user's bookings |
| GET | `/api/suggest?hours=&mode=&seats=&purpose=&start=` | room objects ranked by fit, the quietest first for quiet study |
| POST | `/api/readings` | `{room_id, noise_db?, people?}` from the simulator or the board; header `X-Token` if `READINGS_TOKEN` is set |

- A booking is `{id, room_id, start, end, hours, mode, seats, purpose, custom_purpose, status, checked_in,
  ghost_release_at, mine}`. Its `status` is `active`, `cancelled` or `released` (ghost: slot freed).
  `ghost_release_at` is set while the room is empty during the booking: show a countdown ("released at 10:15
  unless someone shows up").
- `seats` is the number of people coming. `mode: "full"` is private (nobody else can join); `mode: "partial"`
  means "open to share": others join by booking the same room as partial, until the capacity is reached.
- Bookings: start on :00 or :30, 0.5–4 h, between 08:00 and 22:00, up to 14 days ahead. `custom_purpose` is
  required when `purpose` is `custom`.
- Purpose values: `quiet_study`, `group_study`, `meeting`, `custom`, `gaming`, `board_games`, `event`.
- Room `status` is `free`, `partial` (people there, seats left), `full`, `ghost` (booked, sensor sees 0 people) or
  `closed`. Rooms also carry `building` (`"Z"`), `board: true` on the board room, `live: true` while the board
  is sending, and `sensor: true` when a people count arrived in the last 2 min. Without a sensor, `noise_db` and
  `people` are simulated (`SIMULATE=0` turns that off: then `people` is the booked seats).
- **Noise classes:** quiet below 40 dB, moderate from 40 to 60 dB, loud above 60 dB.
- **Purpose → class:** quiet study is quiet; group study, meeting and custom are moderate; gaming, board games and
  event are loud.
- **Booking rules:**
  - Full needs no overlapping booking.
  - Partial needs no overlapping full booking, and booked seats plus estimated people must fit within capacity.
  - Quiet and loud purposes can't share a room, and the room's current noise must fit the purpose. Otherwise the
    API returns 409 with 3 suggestions.
  - Events must be full bookings.
  - A student can't hold two bookings at the same time, and their active bookings on one day total at most 4 h.

### Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`)
1. **Login page:** `POST /api/login` or `POST /api/register`, then the main page. On load, `GET /api/me`; 401 →
   login page. The session is a cookie, so the frontend never stores a token (serve `web/` from the backend).
2. **3D view (done):** `app.js` loads `map3d/campus.json` into `map3d/building3d.js` (`index.html` has the import
   map for three.js), polls `GET /api/rooms` every 5 s and calls `b.setStatus(id, room)`. Clicking a bookable
   room opens its panel; non-bookable rooms are ignored. If WebGL fails it falls back to `plan2d.js`.
3. **Search bar:** on each keystroke (debounce ~150 ms) call `GET /api/search?q=` and show the list; picking one
   calls `b.focusRoom(id)` and opens the panel.
4. **Room panel:** `GET /api/rooms/{id}` (status, live noise, people, who is in now, today's bookings) and
   `GET /api/rooms/{id}/availability?date=` for the slot picker: `free` and `partial` slots with enough
   `seats_free` are selectable; `shareable` marks slots where people are open to sharing.
5. **Booking form:** start slot, hours (0.5–4), "Private room" (`full`) or "Open to share" (`partial`), number of
   people (`seats`, max = capacity), purpose. `POST /api/bookings`; on 409 show `error` and offer
   `suggestions` as buttons that open those rooms; on 400 show `error`.
6. **My bookings:** `GET /api/bookings/mine`, with a cancel button (`DELETE /api/bookings/{id}`) on active ones and
   the ghost countdown when `ghost_release_at` is set.

### Lost items (tom-claude, in `detector/` and `app/lost_items.py`)
**Pipeline**
1. The board sends presence for the board room (Z.1.04) through the bridge, just like noise; a count comes from Arshia's model later.
2. When a booking ends, or `people == 0` for 30 s after people were present, the backend takes **one snapshot**
   from the room camera. In the demo this is our webcam, the same feed that goes into the board.
3. `detector/` diffs the snapshot against `reference/<room>.jpg` (the empty room). Changed regions are labelled
   with YOLOv8n (COCO: backpack, handbag, suitcase, laptop, cell phone, bottle, umbrella, book, …). Regions it
   can't label become "unidentified item".
4. Only the item crop is stored. The full snapshot is deleted immediately, and crops are deleted after 7 days.
   No snapshot is ever taken while persons are present.

**Endpoints**
| Method | Path | Body / result |
|---|---|---|
| GET | `/api/lost-items` | `[{id, room_id, label, area, found_at, image_url, status: "found"|"claimed", maybe_yours: bool}]` |
| POST | `/api/lost-items/{id}/claim` | marks the item claimed by the current user and returns where to pick it up |
| POST | `/api/rooms/{id}/snapshot` | demo trigger: take a snapshot now (still refused while people > 0) |

`maybe_yours` is true when the current user had a booking in that room which ended within 2 h before `found_at`.
YOLO (`ultralytics`, which pulls in PyTorch) lives only in `detector/requirements.txt`, so the main app stays
light.

### 3D campus map (tom-claude; built and working, standalone for now)
The map is in **`web/map3d/`**: `index.html` (the demo page), `building3d.js` (the module) and `campus.json` (the data).
The backend already serves it at **http://localhost:8000/map3d/**. It isn't wired into the UI yet, on purpose.
- **Buildings:** V, N, Z, L and S, from campusplan.aau.at, simplified, with overlaps removed. V's room numbers are
  real; N, Z, L and S numbers are generated (`N.1.44` …). Bookable rooms are seminar rooms, lecture halls, the
  Aula and the atrium. Offices are hidden by default.
- **Data:** `campus.json` = `{buildings: [{id, name, floors, floor_height, blocks: [{x,z,w,d} | {poly, holes?, floors?, open?}], rooms: [{id, label?, floor, storeys?, x, z, w, d, poly?, angle?, capacity, type, bookable, name}], connectors?}]}`. `label` is the main name shown on the map (HS 1-4, HS A-C; search accepts it, e.g. "HS1"), `storeys: 2` = a tall hall with the floor above cut open.
  Units are metres; the origin is the centre of V; x points east and z points south.
- **Regenerate:** `uv run --with shapely python tools/campus3d/gen_campus.py`. It reads `building_v_rooms.json`
  and writes `web/map3d/campus.json`, which the backend also reads (restart it after regenerating).

```js
import { createBuilding } from "./building3d.js";      // path relative to web/map3d/
const b = createBuilding(containerEl, await (await fetch("campus.json")).json());   // 3rd arg {controls: false} hides the built-in building/floor selector
b.setStatus(roomId, {status, noise_class, live});   // free=white, partial=amber, full=red, ghost=light violet, closed=grey; loud=red pulse; live=LIVE badge; label colour follows
b.focusRoom(roomId);     // flies to the room, which glows and pulses while the rest dims; floors above it are hidden; returns the id or false
b.showAll();             // clears the highlight; back to the current building, all floors
b.setBuilding(id|null);  // isolate one building ("V", "N", "Z", "L", "S") or show all
b.setFloor(n | null);    // floors 0..n of the visible building(s), or all floors (the glass case always stays)
b.setOfficesVisible(bool);
b.onRoomClick(cb);       // cb(roomId)
b.onRoomHover(cb);       // cb(roomId | null, pointerEvent)
b.buildings(); b.rooms();
```

## Timeline (today, Fri 27 Nov)
- **By 18:30:** gleb-claude merges the backend with seed data. gemini merges `building_v.json`. claude-2 and
  claude-3 can start right away against the contracts above.
- **By 20:00:** real booking rules, the 3D model with search, and the UI flows each work on their own.
- **By 21:00:** integration on `main`: log in → search → book → noise conflict → suggestion.
- **Next board slot:** re-flash the mic firmware (noise), then test person detection with the webcam (prebuilt
  `.hex` from the DEEPCRAFT Model Zoo, e.g. YoloX), then do an end-to-end run and record the demo video.
- **By Saturday noon:** the lost-item pipeline works with the webcam: person leaves → bag detected → notice.
- **Sunday morning:** demo script rehearsed and the README finished.

## Rules for every agent
- **All cross-agent communication happens on GitHub**: `docs/LOG.md`, PR descriptions and PR comments.
  Start each work chunk with `git pull` and read what changed in `docs/`.
- **Docs: only `docs/PLAN.md`, `docs/LOG.md` and `README.md`.** Don't add other Markdown files. Write only in
  your own LOG section. Keep it short and replace outdated lines instead of appending forever.
- Follow `AGENTS.md`: work on a branch `<agent>/<task>`, open small PRs, never push to `main`, and add no AI
  attribution.
- Run the code or tests before you say something works.
