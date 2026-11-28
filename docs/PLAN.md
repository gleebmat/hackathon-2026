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
  real sensor data from the XIAO ESP32S3 Sense board (simulated in Velxio); it shows a LIVE badge while the board is sending. Every other room is
  simulated. Change it with `BOARD_ROOM` in the backend and `ROOM_ID` in `firmware/xiao_sense/sketch.ino`.
- **Booking options:**
  - Time: 30-minute slots from 00:00 to midnight, 0.5–4 h per booking, and **at most 4 h per student per day**.
    Picking a room shows every slot of the day as free, shared, full, closed or past.
  - **Full** (the whole room) or **partial** (sharing is fine, with a number of seats).
  - **Purpose:** quiet study, group study, gaming, meeting, board games, event, or custom text.
  - **Sharing:** a partial booking means "others may join". Another student joins by booking the same room as
    partial with their number of people; all seats together never exceed the room's capacity.
- **Ghost bookings:** the board (or the simulator) reports the people count. When a booked room is empty, a
  10-minute timer starts: at the start of the booking, or when everyone leaves. If nobody is back when it runs
  out, the booking is released and its time slots are free again. Meanwhile the room shows as `ghost` with the
  release time. Z.1.04 readings expire after 10 seconds. Release requires an empty reading at or after the deadline.
- **Search:** typing a room number or name shows suggestions as you type (`z104`, `Z.1.04`, `107a` and `atrium`
  all work; the building letter may be left out), like campusplan.aau.at.
- **Noise detector for partial bookings:** every room shows a live noise level, so someone who wants silence can
  choose another room.
  - **Z.1.04 is measured by the board's PDM microphone** (your real microphone in Velxio).
  - The other rooms are simulated by the backend: random but the same for everyone, changing every minute.
- **People** per room. Z.1.04 gets presence (0 or 1 person) from the board's person detection; a real count comes
  later from Arshia's model. The other rooms are simulated from their bookings, plus a few walk-ins.
- **Lost & found:** after a booking ends and the board reports 0 persons, the system detects items left behind
  (e.g. "backpack at seat area 3") and tells the student who booked the room. Details are under "Lost items" below.
- **Room assistant** (`app/assistant.py`, `GET /api/assistant?q=`): a request in plain English or German
  ("quiet room for 3 tomorrow at 14:00 for 2 hours", "Besprechung jetzt zu viert, nur wir") is read for day, time,
  length, people, purpose, private/shared and building, rule-based (no AI service, works offline). It answers with
  what it understood and the 3 best rooms (right-sized, quiet first for quiet study); "Book this" opens the room
  with everything filled in.
- **Smart alerts** (in the website, while it is open): your quiet-study room got loud (board microphone), your
  running booking is about to be released as a ghost, or something was left behind in a room you just used.
- **Board room on the map:** a board badge (LIVE / OFFLINE) and, in the room panel, a live card with the people
  count, the noise in dB on a meter and the last minute of noise.
- **3D view:** the campus map (`web/map3d/`) is on the main page: rotate, zoom, click a room to book it; searching
  flies the camera to the room and highlights it.

All numbers are made up. This is a prototype.

## Roles
| Agent | Owns (only edit these, plus your section of `docs/LOG.md`) | Delivers |
|---|---|---|
| **gleb-claude** (Gleb's Claude Code): Backend | `app/` (except `app/lost_items.py`), `tests/`, `requirements.txt`, `.env.example` | FastAPI + SQLite: login, sign-up, rooms (from the map), search, availability, bookings, the booking rules, ghost release, board readings for Z.1.04 and the simulation of every other room (**done**, see API below). Integrates UI + map + board. |
| **tom-claude** (Tom's Claude Code): Board | `firmware/` | XIAO ESP32S3 Sense firmware (`firmware/xiao_sense/`, first version by gleb-claude, tested in Velxio): presence, noise, left items over MQTT. See "Board: XIAO ESP32S3 Sense on Velxio". (The Infineon path `bridge/` was removed on 28 Nov.) |
| **tom-claude**: 3D map (claude-2's role) | `web/map3d/`, `tools/campus3d/` | **Done:** a Three.js campus map of buildings V, N, Z, L and S with search, glow highlight, building and floor isolation, 3D room numbers and status colours. See "3D campus map" below. Standalone until the team decides how to combine it with the UI. |
| **claude-3**: Website UI | `web/index.html`, `web/login.html`, `web/js/app.js`, `web/js/api.js`, `web/js/picker.js`, `web/js/plan2d.js`, `web/css/style.css` | **Done** and wired to the 3D map. The login page, the search bar (calls `focusRoom`), the room panel (live noise, people, today's bookings, a LIVE badge on the room with `board: true`), the booking form (hours, full or partial, seats, purpose, and suggestions on a 409), and "my bookings"., and the **Lost & found** page: item cards, a "That's mine" button, and a "maybe yours" banner. |
| **gemini** (Arshia, Gemini Pro): Models, demo | `models/` (new), `README.md` | **Two models, added later:** (1) counting people in the board room, (2) finding lost items. They plug into `POST /api/readings` (`people` as a number) and the "Lost items" endpoints below. Also the demo script and the pitch. Room data and simulation are no longer gemini's: rooms come from the map, and the backend simulates the other rooms. |

## Architecture
```
XIAO ESP32S3 Sense (Velxio simulator or real board), room Z.1.04
  camera (your webcam in Velxio) -> person model ON the board (TensorFlow Lite Micro) -> presence
  camera -> empty-room snapshot diff -> left items        PDM mic -> noise_db
  -> MQTT publish  aau-hack26/rooms/Z.1.04/readings  (public broker broker.hivemq.com:1883, JSON)
       -> backend subscribes (app/mqtt_feed.py) -> same storage as POST /api/readings
web/ (UI + map3d/, Three.js from CDN) <-- JSON --> FastAPI + SQLite (app/)
                                                   (simulates every other room; rooms from web/map3d/campus.json)
```
- **Why MQTT:** the board can reach the internet but not the laptop, and the simulated board's HTTPS handshake
  with a Cloudflare tunnel was rejected. With MQTT the laptop never has to be reachable from outside. The broker
  is public (anyone could publish fake readings): fine for the demo, use a private broker with a password later.
- **Stack:** Python 3.12, FastAPI, the standard-library `sqlite3`, `paho-mqtt`, and static HTML/JS with Three.js
  from a CDN (pin an exact version, e.g. `three@0.160.0`), so there is no build step.
- **Run:** `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`, then open http://localhost:8000.
  The backend serves `web/` at `/`. Board runbook: `README.md`.

## Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used)
**Why this board.** Velxio (velxio.dev) simulates it for free, with no reservation: the camera (OV3660) and the PDM
microphone are emulated with real data, the camera can use your real webcam and the mic your real microphone,
and WiFi reaches the internet ("Velxio-GUEST", open). The same sketch runs on the physical board.

**Firmware:** `firmware/xiao_sense/sketch.ino` + `person_model.h` (Arshia's `models/vww_96_int8.tflite` as a C
array, generated). Libraries in Velxio: `Chirale_TensorFlowLite` (builds TFLM from source; `tflm_esp32` does
not work on arduino-esp32 3.x) and `PubSubClient`. The sketch publishes one reading per camera frame (no pause; ~1-2 s in Velxio):
`{"room_id": "Z.1.04", "noise_db": 37.2, "presence": true, "person_score": 0.91, "left_items": 0}`.

**Tested in Velxio with a webcam (28 Nov):**
| Feature | How | Result |
|---|---|---|
| Presence + people count + left items | the board sends encrypted 320x240 JPEG frames (~0.6 s apart in Velxio) over MQTT; the backend runs YOLO11s at 640 (`app/vision.py`, ~150 ms) and smooths over 3 frames | steady count, ~1 s to the website; left items = forgettable things in view while nobody is there |

**Left items (on the board).** No photo comparison any more (that version is the git tag `board-v1`). The COCO
detector counts forgettable objects while the room is empty; the count before people came is the baseline, and after
they leave every extra object is a left item. Details, placement tips and the model comparison: `README.md`.

**Next steps (board owner):** test on a physical XIAO ESP32S3 Sense with your own WiFi SSID (detectors are ~10-20x faster
there); a trained FOMO model for faster item checks.

**Demo notes**
- In Velxio: click **Camera** and **Mic** under the board (allow them in Chrome), then Run. Use the team project
  TODAREISTODO (`README.md`).
- Start the backend with `GHOST_GRACE_SECONDS=5` and `GHOST_RELEASE_SECONDS=15` for a fast ghost release.
- Keep the view empty after Run until serial prints `Empty-room baseline ready`.
- Pitch wording: presence, noise and left items are computed on the board; only small JSON readings leave it.
  The people count is slow in the simulator (~45 s); say so if you show it.

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
| GET | `/api/calendar?date=YYYY-MM-DD` | **The picker's calendar, one call for all rooms:** `{date, open, close, rooms: {room_id: {free_hours, slots:[same as availability]}}}`. `free_hours` = bookable hours left that day |
| POST | `/api/rooms/{id}/rating` | `{stars: 1-5}` → `{room_id, rating, votes, my_rating}`. Only after the user had an active booking there that has started (403 otherwise); rating again replaces the old vote |
| GET | `/api/favorites` | the logged-in user's liked rooms, newest like first: `[room + {favorite: true, liked_at}]` (401 when logged out) |
| PUT / DELETE | `/api/favorites/{id}` | like / unlike a room → `{room_id, favorite, likes}`; both idempotent, 404 for an unknown room |
| POST | `/api/bookings` | `{room_id, start:"YYYY-MM-DDTHH:MM", hours, mode:"full"|"partial", seats, purpose, custom_purpose}` returns 201 with the booking, or `409 {error, suggestions:[room_id,...]}` |
| GET | `/api/bookings/mine` | the user's bookings, newest first |
| DELETE | `/api/bookings/{id}` | cancels one of the user's bookings |
| GET | `/api/suggest?hours=&mode=&seats=&purpose=&start=` | room objects ranked by fit, the quietest first for quiet study |
| POST | `/api/readings` | `{room_id, noise_db?, people?, presence?}` from the board (or a model); `presence` true/false counts as 1/0 people; header `X-Token` if `READINGS_TOKEN` is set |

- Every room object also has `label` (map name such as `HS 1`, or null; search accepts it), `rating` (average,
  null without votes) and `votes`. `GET /api/rooms` and `/api/rooms/{id}` carry `favorite` (this account liked it; false when logged out); `GET /api/rooms/{id}` adds `my_rating`, `can_rate` and `likes` (how many accounts liked it); bookings carry
  `my_rating` for their room. Files under `web/` are served with `Cache-Control: no-cache`.

- A booking is `{id, room_id, start, end, hours, mode, seats, purpose, custom_purpose, status, checked_in,
  ghost_release_at, mine}`. Its `status` is `active`, `cancelled` or `released` (ghost: slot freed).
  `ghost_release_at` is set while the room is empty during the booking: show a countdown ("released at 10:15
  unless someone shows up").
- `seats` is the number of people coming. `mode: "full"` is private (nobody else can join); `mode: "partial"`
  means "open to share": others join by booking the same room as partial, until the capacity is reached.
- Bookings: start on :00 or :30, 0.5–4 h, around the clock within a calendar day, up to 14 days ahead. `custom_purpose` is
  required when `purpose` is `custom`.
- Purpose values: `quiet_study`, `group_study`, `meeting`, `custom`, `gaming`, `board_games`, `event`.
- Room `status` is `free`, `partial` (people there, seats left), `full`, `ghost` (booked, sensor sees 0 people) or
  `closed`. Rooms also carry `building` (`"Z"`), `board: true` on the board room, `live: true` while the board
  is sending, and `sensor: true` when a people count arrived in the last 2 min. Without a sensor, `noise_db` and
  `people` are simulated (`SIMULATE=0` turns that off: then `people` is the booked seats): noise drifts every few
  seconds, walk-ins come and go every 5 minutes, and `app/campus_sim.py` books rooms as "Other students" every 2
  minutes (about 45% of rooms in use during the day, 25% in the evening, 8% at night; never the board room;
  `CAMPUS_SIM=0` turns only that off).
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

### Room display + speaker (gleb-claude backend `app/display.py`, page `web/display.html` by Arshia)
The XIAO has no display or speaker, so a small window on the laptop pretends to be the Infineon E84 kit's 4.3" touch
display (800x480). The board sends `"display": true` in its readings (`HAS_DISPLAY` in the sketch); while it does, the
backend opens a chromeless Edge/Chrome window (800x520) on `/display.html?room=Z.1.04&token=<token>` and closes it ~10 s after the
board stops (`DISPLAY_WINDOW=0` turns this off, `DISPLAY_BROWSER` = browser path, `DISPLAY_TOKEN` fixes the token;
the log prints the URL to open it by hand). Sound plays in that window (laptop speakers). Actions send the token from
the page URL as header `X-Display-Token` (403 without it). QR codes use the public address (`tools/tunnel.py`).

| Method | Path | What it does |
|---|---|---|
| GET | `/api/display/{room}` | `{room_id, label, name, status, people, noise_db, board_online, bookings_now, break_until, sound:{kind, volume}, sounds:[...], emergency:{id, room_id, created_at, resolved_at}\|null, booking_url}`; poll it every 1-2 s; no token needed |
| GET | `/api/display/{room}/qr` | SVG QR code of `booking_url` (1. book a room) |
| POST | `/api/display/{room}/sound` | `{kind: off\|rain\|ocean\|forest\|cafe\|white\|pink\|brown, volume: 0-100}` (2. soundscapes): the backend only stores it, the page plays it (WebAudio or files) |
| POST | `/api/display/{room}/selfie` | (3. selfie) optional `{image: base64 JPEG}` = the photo the display took with its webcam; without it, the board camera's newest frame → `{url, qr_svg, expires_at}`; the photo lives in memory for 10 min, never on disk; 409 when there's no image and the board camera isn't live; 400 when the image isn't a JPEG |
| GET | `/api/selfies/{token}` | the selfie JPEG (what the QR opens); 404 once expired |
| POST | `/api/display/{room}/emergency` | `{confirm: true}` (4. SOS, after the page's "Are you sure?") → the open emergency; pressing again returns the same one. Simulated police call (133): logged, nobody is really called |
| DELETE | `/api/display/{room}/emergency` | "End emergency" on the display: closes it |
| POST / DELETE | `/api/display/{room}/break` | `{minutes: 5-30}` (5. take a break) → `{break_until}` on every running booking in the room; 409 when nobody booked. While it runs the booking is never released as a ghost; afterwards the empty timer starts again. DELETE ends it early |

These features are for the room display only; the website shows none of them (rooms and bookings carry
`break_until`, used by the ghost release).
- **Own soundscape:** the board mic also hears the sound the display plays. While a soundscape is on, readings from
  the display board keep the noise measured before it started, so the room never turns "loud" from its own sound.

**The page (`web/display.html`).** Laid out for 800x480 and scaled to any window. Home: one row of big buttons that
scrolls sideways like a list (finger, mouse drag, wheel, the arrows or the arrow keys; it moves as one row, nothing
wraps around or jumps). First the room card (300 px wide: status in words, people, booked until, minutes to the next
break reminder), then Book, Sounds, Selfie and Break (236x338 px each, about 28x40 mm on the 4.3" panel; the third
one peeks in at the edge so it's clear the row scrolls). It goes back to the start after 90 s untouched. Top bar: university logo (`web/img/aau-logo.svg`, the University
of Klagenfurt's logo as on Wikipedia, `Universitaet_klagenfurt_logo.svg`; a protected trademark of the university,
used here for the AAU challenge; without the file the name is written out), room, time with the date, a small ear
while the fire-alarm listener runs, language, SOS. Plain campus-system look on purpose: Arial, square boxes, grey
lines, AAU blue (`#497284`, from the logo), no decoration; red only for SOS and the fire alarm. Text contrast at least
4.5:1, touch targets at least 44 px (home buttons 236x338), text at least 15 px, nothing overflows at 800x480 in
English or German (checked on every screen and state, overlays included), English/German (same `roomv-lang` choice as
the website), screen-reader labels, reduced motion respected. SOS is always top right, asks "Call the police?" first,
shows "Calling the police (133)…" for a few seconds, then "Police called" until someone presses "End emergency".
Selfie: this computer's webcam (preview mirrored, photo not), else the board camera's frame. Sounds are synthesised
in the page (Web Audio), no files; the café is murmuring voices, cups and spoons and the coffee machine.

Shown without a button:
- **Break reminder** ("Time for a break": stand up, stretch, drink some water) every 45 minutes while people study in
  the room (people seen or a booking running, not during a break): full screen for 60 s, tap anywhere to close early.
  `?water=<minutes>` changes the interval.
- **Fire alarm for deaf students:** the page listens to the microphone and looks for a smoke alarm's beeps (a narrow
  tone at 2.5-4 kHz, 25 dB above the rest; three beeps of 0.2-1.2 s within 6 s, as in EN 14604 / ISO 8201, or one
  tone longer than 3 s). Then a full-screen bilingual "FIRE ALARM / FEUERALARM: leave the room" alert pulses at 1 Hz
  (well under the 3 flashes/s seizure limit) until no beep for 20 s. Nothing is recorded or sent; only the band
  energy is looked at in the page. The display window gets camera and microphone without a prompt
  (`--use-fake-ui-for-media-stream` in `app/display.py`; it's its own browser profile on this page only). On a real
  board the same check is a Goertzel filter at ~3.1 kHz on the PDM microphone.
- Demo: `?demo=1` then key **W** = break reminder, **F** = fire alarm for 15 s.

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
6. **My bookings:** `GET /api/bookings/mine`, with a cancel button (`DELETE /api/bookings/{id}`) on active ones,
   the ghost countdown when `ghost_release_at` is set, and 1–5 stars on bookings that have started
   (`POST /api/rooms/{id}/rating`).
7. **Room picker / calendar (`picker.js`, done):** one `GET /api/calendar?date=` per day gives every room's
   slots; the cards show free hours (any time) or the exact status for the picked range, plus `rating`.

### Lost items
Done on the board (see "Left items (on the board)" above): the board sends `left_items` (a count; the UI shows
"🎒 Something left behind" when it's above 0). There is no laptop-side detector, no stored photos and no lost &
found endpoints: nothing leaves the board except the number. Arshia's laptop reference (`models/webcam.py` with
EfficientDet-Lite2, which also names the object) is too big for the board (7.6 MB, ~10 MB working memory).

### 3D campus map (tom-claude; built and working, standalone for now)
The map is in **`web/map3d/`**: `index.html` (the demo page), `building3d.js` (the module) and `campus.json` (the data).
The backend already serves it at **http://localhost:8000/map3d/**. It isn't wired into the UI yet, on purpose.
- **Buildings:** V, N, Z, L (library), S and O (Nexus), built from campusplan.aau.at's floor-plan data
  (`tools/campus3d/fetch_plan.py` downloads it from the public GeoServer into `aau_plan.json`; `gen_campus.py` builds
  `campus.json`). Real outlines and room numbers on every floor; pieces that exist only on some floors (the floor-1
  bridges Z-S) carry their floors; courtyards are left out; no overlaps (rooms clipped to their building and each
  other). Rooms drawn: teaching rooms, offices, toilets; bookable: seminar / computer / group-work rooms and lecture
  halls with their real seats (55+ seats show as not bookable); Omansaal (Z.1.29) left out. `doors`: doors to the
  outside at ground level (from the plan's door-swing drawings, layer `cartolines`); `pillars`: legs under Nexus's
  overhang; `machines`: coffee (green) and vending (red) machines on floor 1, snapped to a free spot by a wall. `link: true`
  blocks are bridges and corridors to another building (narrower than 8 m, or underground beyond the building's body);
  the map hides them when one building is selected. Pieces under 40 m² or thinner than 1.6 m join their neighbour; holes under 80 m² are filled. Z.1.04 is the sensor-board room (an office in reality,
  a 51-seat seminar room here). Main entrance: Z, east, floor 1 (`entrances`). `north` = true north in the model.
- **Data:** `campus.json` = `{north: [x, z], buildings: [{id, name, floors, floor_height, blocks: [{poly, holes?, floors, link?}], rooms: [{id, label?, floor, storeys?, x, z, w, d, poly, holes?, capacity, type, bookable, name}], entrances?: [{x, z, floor, dir, main}], doors?: [{x, z, floor, dir}], pillars?: [{poly, to_floor}], machines?: [{kind, x, z, floor, dir}]}]}`. `label` is the main name shown on the map (HS 1-4, HS A-C; search accepts it, e.g. "HS1"), `storeys: 2` = a tall hall with the floor above cut open.
  Units are metres; the origin is the centre of V; x runs along N (roughly east), z across (roughly south).
- **Regenerate:** `uv run --with shapely python tools/campus3d/fetch_plan.py` (only to refresh the data), then
  `uv run --with shapely python tools/campus3d/gen_campus.py` and
  `uv run --with shapely --with scipy python tools/campus3d/gen_routes.py`; restart the backend afterwards.
- **Routes** (`campus.json` `routes`, `gen_routes.py`): `{room id: {from: "main" | "door", start: [x, z, floor],
  points: [[x, z, floor, y], ...], length}}` for every lecture hall and seminar room (no offices). Walkable = the
  plan's corridors, halls, entrances, bridges, stairwells, lifts and the library reading rooms, on a 0.5 m grid;
  floors connect only where a stair flight (found in the drawing lines by `fetch_plan.py`, `aau_plan.json` `stairs`)
  is on both floors; a floor change costs 8 m extra. Start: the main entrance, or the nearest outside door if the
  walk is over 150 m. End: the room's door (`room_doors`, from door swings), else the wall it shares with a corridor.
  Map: `showRoute(route, {startLabel})`, `clearRoute()`.

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
