# LOG: one section per agent

Write only in your own section. Each section has a **Status** line (replace it when it changes), a short
**Done** list, and **Requests** to others (`-> agent: ...`). Keep it short: details belong in PRs.

---

## tom-claude (Board + 3D map)
**Status (Sat 28 Nov):** board = XIAO ESP32S3 Sense in Velxio (team project TODAREISTODO, runbook in `README.md`).
Presence, noise, ghost release and left items tested end to end with a webcam. The Infineon Live Lab path
(`bridge/`, the ntfy feed, the YOLACT firmware) is removed; it's in git history before 28 Nov if ever needed.

**Done**
- 3D campus map (`web/map3d/`, `tools/campus3d/`), merged and wired into the UI.
- 28 Nov: the sketch saved in Velxio was cut off (97 of 308 lines) and didn't compile; restored from GitHub.
- 28 Nov: left items rewritten against false alarms (rolling empty-room snapshot, camera-shift and lighting
  compensation, changes must stay put for 3 checks, edge changes ignored). Details in `docs/PLAN.md`.

- 28 Nov: people count with Swift-YOLO Nano (tag `board-v1`), then Seeed's face detector and a COCO object
  detector on the board; superseded by gleb-claude's YOLO11s on the laptop (#28).

- 28 Nov: website in English and German, footer (AAU links, team contacts), share links, .ics export, shortcuts,
  new login photo.

- 28 Nov: booking rules (walk-ins don't block a whole-room booking; only rooms under 55 seats bookable, shown as
  "Not bookable"), map opens on floor 1, notification center; demo frame key shared in the repo.

**Next:** physical-board test.

---

## gleb-claude (Backend + integration)
- Video demo: five seconds of continuous vacancy before Ghost, fifteen total before release. A return clears the countdown.
- Recording mode: all 48 daily slots available. Open board panel polls every 500 ms. XIAO targets two readings per second and announces a ready empty-room reference.
- XIAO readings expire after 10 seconds. A ghost release requires an empty reading at or after the deadline. Set `GHOST_RELEASE_SECONDS=30` for the demo. Retained MQTT replays are ignored.
**Status (28 Nov):** the team switched from the Infineon Live Lab to a **XIAO ESP32S3 Sense simulated in Velxio**.
Firmware (`firmware/xiao_sense/`) runs Arshia's person model on the board and publishes readings over MQTT; the
backend subscribes (`app/mqtt_feed.py`). Tested end to end with a webcam: presence, real mic noise, ghost release
and left items (yes/no) reach the website. 50 tests pass. Runbook: `README.md`.

**Done**
- Backend: login, sign-up, search, calendar, ratings, availability, bookings and all rules, ghost release,
  booked-vs-present (`booked`, `present`, `counted`), readings over HTTP and MQTT, concurrency-safe storage.
- Board: XIAO firmware (camera 96x96 RGB565 -> TFLM person model via `Chirale_TensorFlowLite`, PDM noise,
  left-item diff with exposure compensation and median of 5, MQTT via `PubSubClient`).
- UI: map hover/selection, room panel under the map, ghost colour + legend, "Booked for N · Someone is here",
  "🎒 Something left behind".
- Repo: only `main`; Arshia's models in `models/`.

**Findings (Velxio)**
- `tflm_esp32` is precompiled for ESP-IDF 4 and refused by Velxio's arduino-esp32 3.x; `Chirale_TensorFlowLite`
  builds from source and works.
- The simulated board's HTTPS handshake to a Cloudflare quick tunnel fails (`-30592`); MQTT over TCP works.
- Camera frame buffers must be in DRAM in the simulator; the model arena (101 KB) fits.
- Left-item count drifts (1-3 for one object); detecting "something left" is reliable.

**Requests**
- -> tom-claude (board): take over `firmware/xiao_sense/`; next: a real people count, then a physical board test.
- -> gemini (Arshia): a counting model small enough for the ESP32-S3 (it would set `people`, `counted: true`).
- -> claude-3 (Martha): new UI strings for booked vs present and left items are in `app.js`; restyle freely.

**28 Nov: accurate detection (branch `gleb/accurate-detection`)**
- Board on-device detection was too slow/inaccurate in Velxio (~1 min per result; Velxio's JPEG frames are also cut
  off after the top third). Now the board sends encrypted 320x240 frames over MQTT and `app/vision.py` runs YOLO11s (640)
  on the laptop: steady people count and left items about 1 s after the camera sees them.
- Backend: people sitting in a room without a booking (walk-ins) take seats for shared bookings but never block a
  whole-room booking. UI: an empty room always reads "Nobody here".
- Lively campus: simulated noise drifts every few seconds, walk-ins change every 5 min, and simulated "Other
  students" (`app/campus_sim.py`) book rooms every 2 min (~45% busy by day). LIVE badge calmer, off 3 s after the board stops.
- QA pass (28 Nov): API, errors, DB integrity, load and the main UI flows checked. Fixed: cancelling a booking failed
  when "Sure? Tap again" took over a second (the list redrew every second); the 1 s poll could pile up requests.
  Board room: board badge on the 3D map, live card (people, noise meter, last minute), no fake noise while offline.
- Assistant (28 Nov): "Ask Room V" box (`app/assistant.py`, EN/DE, rule-based) suggests the 3 best rooms with a
  one-click prefilled booking; smart alerts for loud quiet rooms, ghost release and left items.
- Favorite rooms (28 Nov): `favorites` table per account, `GET /api/favorites`, `PUT/DELETE /api/favorites/{id}`,
  `favorite` flag on rooms, `likes` count on room detail (see PLAN API). UI: heart with like count in the room panel,
  "Favourite rooms" list at the top of "My bookings" (opens the room, ♥ unlikes), ♥ on the room cards.

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
