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

---

## claude-2 (3D model)
**Status:** not started.

---

## claude-3 (Website UI)
**Status (28 Nov):** **final redesign, ready for review in PR #33** (branch `claude-3/redesign`, on top of `main`,
not merged). The site is now **Campus Booking System**, the assistant is **Roomie**. Blue accents (logo, avatar,
badges, frames while you use the map or the calendar block, a soft cursor glow), taller map, ghost bookings in
`#8b5cf6`. Includes a **map proposal for tom-claude** (centred framing, colours matched to the site). 63 tests pass;
tested in the browser.

**Run it**
`pip install -r requirements.txt`, `uvicorn app.main:app --reload`, open http://localhost:8000 and log in as
`student1@edu.aau.at` / `demo`. After pulling frontend changes press **Ctrl+Shift+R**.

**What the redesign changes** (all in `web/`, plus the map proposal in `web/map3d/building3d.js`)
- Name and logo: "Campus Booking System", a black monogram tile `cb.` (no mascot).
- Palette (chosen by Martha, THEME block at the top of `css/style.css`): `--bg #f3f5f8`, `--surface #f9fbff`,
  `--surface-2 #eef1f5`, `--border #e1e5ec`, `--text #2a2420`, `--muted #6d685d`, `--brand`/`--accent #2f5be0`;
  status `--free #23865a`, `--shared #c98512`, `--full #b42318`, `--ghost #8b5cf6`, `--closed #94a3b8`;
  `--star #c98512`. No gradients; radii 7–14 px.
- Fonts: Bricolage Grotesque (headings, room ids), Instrument Sans (text), IBM Plex Mono (times).
- Our own line icons (SVG sprite in `index.html`) instead of every emoji.
- Roomie, the assistant: a small `r.` tile bottom right that opens a compact panel (no section on the page).
- Rooms that can't be booked (55+ seats) open a small info card on the map, not the booking panel.
- Filter on the room cards: All / Seminar rooms / Lecture halls (from the room's name or label).
- Ratings fold away: shown on card hover and in a collapsed "Ratings" box in the booking panel.
- Profile menu: the colour-theme picker is gone (light/dark/auto and language stay).

**Requests**
- -> tom-claude (map): please look at the separate commit "Map proposal for Tom" on `claude-3/redesign` and take
  it or redo it your way. The goal is that the map matches the site:
  1. **Centred:** the camera fits the campus to the canvas using the field of view and aspect, so it is whole and
     centred at any size, and re-frames on resize until the user moves the map (the old fixed formula cut the
     campus off in wide, short boxes).
  2. **Colours:** light blue-grey scene (`#eef2f8` → `#e2e8f1` panel), light cool room greys, statuses in the site
     colours above, hover in `#2f5be0`, and the built-in building/floor selector light with a blue active button.
  3. Still open from before: the mouse wheel over the map zooms it, so the page can't scroll past it (Ctrl + wheel
     or click-to-zoom would fix it).
- -> gleb-claude: no backend changes needed; please don't merge until Tom has looked at the map part.
---

## gemini (Data, simulation, demo)
**Status:** not started.
