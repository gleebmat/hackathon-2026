# PLAN: Smart Campus Room Booking (Infineon challenge), building V

**Every agent: read this file and `docs/LOG.md`, find your role below, and log your work in your section of
`docs/LOG.md`.** Don't create other Markdown files.

## Product
This is a website for AAU students. A student logs in, finds a room in a **3D model of building V**, and books it.
- **Login:** 4 demo accounts (`student1..4@edu.aau.at`, password `demo`), plus **sign-up** with any `@edu.aau.at`
  email and a password of 4+ characters. The repo is public, so never put real emails in it.
- **Only floor 1 of building V** is bookable and shown.
- **Booking options:**
  - Time: 30-minute slots from 08:00 to 22:00, 0.5–4 h per booking, and **at most 4 h per student per day**.
    Picking a room shows every slot of the day as free, shared, full, closed or past.
  - **Full** (the whole room) or **partial** (sharing is fine, with a number of seats).
  - **Purpose:** quiet study, group study, gaming, meeting, board games, event, or custom text.
  - **Sharing:** a partial booking means "others may join". Another student joins by booking the same room as
    partial with their number of people; all seats together never exceed the room's capacity.
- **Ghost bookings:** if a room's sensor reports 0 people for the first 15 min of a booking, the booking is
  released automatically. Until then the room shows as `ghost`.
- **Noise detector for partial bookings:** every room shows a live noise level, so someone who wants silence can
  choose another room.
  - **V.1.07a is measured by the real PSOC Edge E84 microphone.** This already works (see `docs/LOG.md`,
    tom-claude).
  - The other rooms are simulated.
- **People estimate** per room. V.1.07a gets a real count from the board's person-detection model (webcam feed
  into the board). The other rooms are simulated from their bookings.
- **Lost & found:** after a booking ends and the board reports 0 persons, the system detects items left behind
  (e.g. "backpack at seat area 3") and tells the student who booked the room. Details are under "Lost items" below.
- **3D view:** building V floats in empty space with no terrain. It is a rectangular ring with a courtyard hole,
  like Google Earth, and you can rotate and zoom it. Searching `V.1.07a` flies the camera to that room and hides
  everything else.

All numbers are made up. This is a prototype.

## Roles
| Agent | Owns (only edit these, plus your section of `docs/LOG.md`) | Delivers |
|---|---|---|
| **gleb-claude** (Gleb's Claude Code): Backend | `app/` (except `app/lost_items.py`), `tests/`, `requirements.txt`, `.env.example` | FastAPI + SQLite: login, sign-up, rooms, search, availability, bookings, the booking rules, ghost release, and the live noise feed for V.1.07a (**done**, see API below). |
| **tom-claude** (Tom's Claude Code): Board | `bridge/` | Board bridge (**done**). Forwards the board's noise and person count to the backend. |
| **claude-2**: 3D model | `web/js/building3d.js` | The Three.js building that floats in empty space, rotate and zoom, `focusRoom` with the others hidden, `showAll`, floor filter, status and noise colours. Use the module API below. |
| **claude-3**: Website UI | `web/index.html`, `web/login.html`, `web/js/app.js`, `web/css/style.css` | The login page, the search bar (calls `focusRoom`), the room panel (live noise, people, today's bookings, a LIVE badge on V.1.07a), the booking form (hours, full or partial, seats, purpose, and suggestions on a 409), and "my bookings"., and the **Lost & found** page: item cards, a "That's mine" button, and a "maybe yours" banner. |
| **tom-claude**, continued | `detector/`, `app/lost_items.py` (a FastAPI `APIRouter` that gleb-claude includes in `app/main.py`) | The lost-item service: snapshot vs reference diff, YOLOv8n labels, crops, and the endpoints below. Board: flash person detection and forward the person count through the bridge. |
| **gemini** (Gemini Pro): Data, simulation, demo | `web/data/building_v.json`, `sim/`, `README.md` | Building V room layout and data (schema below; take real room numbers from https://campusplan.aau.at/ if that's cheap, otherwise invent plausible ones). `sim/simulate.py`, which posts simulated readings for the other rooms. The demo script, the pitch and the README. End-to-end QA, with bugs reported in LOG. Lost-item demo setup: reference photo of the empty desk and the bag scenario. |

## Architecture
```
PSOC Edge E84 (Live Lab): mic -> UART -> bridge.py on the lab PC -> ntfy.sh topic
                                                                       |
web/ (static, Three.js from CDN) <-- JSON --> FastAPI + SQLite (app/) <-+ LiveNoiseFeed (bridge/ntfy_feed.py)
                                                     ^
                                    sim/simulate.py -+ POST /api/readings (the other rooms)
```
- **Stack:** Python 3.12, FastAPI, the standard-library `sqlite3`, and static HTML/JS with Three.js from a CDN
  (pin an exact version, e.g. `three@0.160.0`), so there is no build step.
- **Run:** `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`, then open http://localhost:8000.
  The backend serves `web/` at `/`.

## Contracts (code against these; whoever changes one updates this file in the same PR)

### `web/data/building_v.json` (gemini; read by the backend and by the 3D model)
```json
{"building": "V", "outer": {"w": 60, "d": 40}, "courtyard": {"w": 30, "d": 16}, "floor_height": 4,
 "rooms": [{"id": "V.1.07a", "floor": 1, "x": 12, "z": -18, "w": 8, "d": 6, "capacity": 12, "name": "Seminar room"}]}
```
- Units are metres. The origin is the building centre and `y` is up. `x`/`z` give the room centre on its floor.
- Only floor 1 is used: roughly 10–12 rooms arranged in the ring around the courtyard. The backend loads only rooms
  with `"floor": 1`. An optional `"closed": true` marks a room that can't be booked.
- `V.1.07a` must exist. Until this file exists, the backend uses built-in floor 1 rooms (`app/db.py`).

### API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)
Errors are `{error}` with 400 (bad input), 401 (not logged in), 404 or 409 (the room can't take it).
| Method | Path | Body / result |
|---|---|---|
| POST | `/api/register` | `{email, password, name?}` returns 201 `{email, name}` and logs in. 400 if the email isn't `@edu.aau.at` or the password is under 4 characters, 409 if the account exists |
| POST | `/api/login` | `{email, password}` sets a session cookie. `POST /api/logout`, `GET /api/me` returns `{email, name}` or 401 |
| GET | `/api/rooms?q=` | `[{id, floor, capacity, name, status, noise_db, noise_class, people, seats_free, live, sensor, bookings_now:[{id, mode, purpose, seats, end, shareable}]}]`. `q` searches room numbers (`107a` finds `V.1.07a`) and names |
| GET | `/api/rooms/{id}` | the room above plus `bookings_today:[booking]` |
| GET | `/api/rooms/{id}/availability?date=YYYY-MM-DD` | `{room_id, date, open, close, slots:[{start:"HH:MM", end, status, seats_free, shareable, noise}]}`; slot `status` is `free`, `partial`, `full`, `closed` or `past` |
| POST | `/api/bookings` | `{room_id, start:"YYYY-MM-DDTHH:MM", hours, mode:"full"|"partial", seats, purpose, custom_purpose}` returns 201 with the booking, or `409 {error, suggestions:[room_id,...]}` |
| GET | `/api/bookings/mine` | the user's bookings, newest first |
| DELETE | `/api/bookings/{id}` | cancels one of the user's bookings |
| GET | `/api/suggest?hours=&mode=&seats=&purpose=&start=` | room objects ranked by fit, the quietest first for quiet study |
| POST | `/api/readings` | `{room_id, noise_db?, people?}` from the simulator or the board; header `X-Token` if `READINGS_TOKEN` is set |

- A booking is `{id, room_id, start, end, hours, mode, seats, purpose, custom_purpose, status, checked_in, mine}`;
  its `status` is `active`, `cancelled` or `released` (ghost).
- Purpose values: `quiet_study`, `group_study`, `meeting`, `custom`, `gaming`, `board_games`, `event`.
- Room `status` is `free`, `partial` (people there, seats left), `full`, `ghost` (booked, sensor sees 0 people) or
  `closed`. `live: true` means real board noise (V.1.07a only); `sensor: true` means a people count arrived in the
  last 2 min. Without a sensor, `people` is the number of booked seats.
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

### Lost items (tom-claude, in `detector/` and `app/lost_items.py`)
**Pipeline**
1. The board's person-detection firmware sends a count for V.1.07a through the bridge and ntfy, just like noise.
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

### 3D module API (claude-2; used by claude-3)
```js
import { createBuilding } from "./building3d.js";
const b = createBuilding(containerEl, buildingJson);
b.setStatus(roomId, {status, noise_class, live});   // free=white, partial=amber, full=red, ghost=dashed outline, closed=grey; loud=red pulse; live=badge
b.focusRoom(roomId);   // animates the camera to the room, hides everything else; returns false if the room is unknown
b.showAll();           // restores the full building
b.setFloor(n | null);  // shows only floor n, or all floors
b.onRoomClick(cb);     // cb(roomId)
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
