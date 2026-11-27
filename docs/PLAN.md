# PLAN: Smart Campus Room Booking (Infineon challenge), building V

**Every agent: read this file and `docs/LOG.md`, find your role below, and log your work in your section of
`docs/LOG.md`.** Don't create other Markdown files.

## Product
This is a website for AAU students. A student logs in, finds a room in a **3D model of building V**, and books it.
- **Login:** a tiny database with 4 demo accounts (`student1..4@edu.aau.at`, password `demo`). The repo is public,
  so never put real emails in it. Later this can be replaced by AAU single sign-on (@edu.aau.at).
- **Booking options:**
  - Duration: 1–8 hours.
  - **Full** (the whole room) or **partial** (sharing is fine, with a number of seats).
  - **Purpose:** quiet study, group study, gaming, meeting, board games, event, or custom text.
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
| **tom-claude** (Tom's Claude Code): Backend + Board | `app/`, `bridge/`, `tests/`, `requirements.txt`, `.env.example` | Board bridge (**done**). FastAPI + SQLite: login, rooms, bookings, the booking rules, every endpoint below, and the live noise feed for V.1.07a. Merges PRs and runs integration. **Stub endpoints with seed data land first**, so the others can build against real responses. |
| **claude-2**: 3D model | `web/js/building3d.js` | The Three.js building that floats in empty space, rotate and zoom, `focusRoom` with the others hidden, `showAll`, floor filter, status and noise colours. Use the module API below. |
| **claude-3**: Website UI | `web/index.html`, `web/login.html`, `web/js/app.js`, `web/css/style.css` | The login page, the search bar (calls `focusRoom`), the room panel (live noise, people, today's bookings, a LIVE badge on V.1.07a), the booking form (hours, full or partial, seats, purpose, and suggestions on a 409), and "my bookings". |
| **tom-claude**, continued | `detector/` | The lost-item service: snapshot vs reference diff, YOLOv8n labels, crops, and the endpoints below. Board: flash person detection and forward the person count through the bridge. |
| **gemini** (Gemini Pro): Data, simulation, demo | `web/data/building_v.json`, `sim/`, `README.md` | Building V room layout and data (schema below; take real room numbers from https://campusplan.aau.at/ if that's cheap, otherwise invent plausible ones). `sim/simulate.py`, which posts simulated readings for the other rooms. The demo script, the pitch and the README. End-to-end QA, with bugs reported in LOG. |

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
- Use 3 floors (0–2) with roughly 8–12 rooms each, arranged in the ring around the courtyard.
- `V.1.07a` must exist.

### API (tom-claude)
| Method | Path | Body / result |
|---|---|---|
| POST | `/api/login` | `{email, password}` sets a session cookie. `POST /api/logout`, `GET /api/me` returns `{email, name}` or 401 |
| GET | `/api/rooms` | `[{id, floor, capacity, name, status, noise_db, noise_class, people, live, bookings_now:[{mode, purpose, seats, end}]}]` |
| GET | `/api/rooms/{id}` | the room above plus `bookings_today` |
| POST | `/api/bookings` | `{room_id, start, hours, mode, seats, purpose, custom_purpose}` returns 201 with the booking, or `409 {error, suggestions:[room_id,...]}` |
| GET | `/api/bookings/mine` | the user's bookings |
| DELETE | `/api/bookings/{id}` | cancels one of the user's bookings |
| GET | `/api/suggest?hours=&mode=&seats=&purpose=` | rooms ranked by fit, with the quietest first for quiet study |
| POST | `/api/readings` | `{room_id, noise_db, people}` from the simulator |

- `status` is `free`, `partial` or `full`. `live: true` means real board data (V.1.07a only).
- **Noise classes:** quiet below 40 dB, moderate from 40 to 60 dB, loud above 60 dB.
- **Purpose → class:** quiet study is quiet; group study, meeting and custom are moderate; gaming, board games and
  event are loud.
- **Booking rules:**
  - Full needs no overlapping booking.
  - Partial needs no overlapping full booking, and booked seats plus estimated people must fit within capacity.
  - Quiet and loud purposes can't share a room, and the room's current noise must fit the purpose. Otherwise the
    API returns 409 with 3 suggestions.
  - Events must be full bookings.

### Lost items (tom-claude)
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
b.setStatus(roomId, {status, noise_class, live});   // colours: free=white, partial=amber, full=red; loud=red pulse; live=badge
b.focusRoom(roomId);   // animates the camera to the room, hides everything else; returns false if the room is unknown
b.showAll();           // restores the full building
b.setFloor(n | null);  // shows only floor n, or all floors
b.onRoomClick(cb);     // cb(roomId)
```

## Timeline (today, Fri 27 Nov)
- **By 18:30:** tom-claude merges the backend stubs with seed data. gemini merges `building_v.json`. claude-2 and
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
