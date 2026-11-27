# PLAN: Smart Campus Room Booking (Infineon challenge), building V

## Product
This is a website for AAU students. A student logs in, finds a room in a **3D model of building V**, and books it.
- **Login:** a tiny database with 4 demo accounts (`student1..4@edu.aau.at`, password `demo`). The repo is public,
  so never put real emails in it. Later this can be replaced by AAU single sign-on (@edu.aau.at).
- **Booking options:**
  - Duration: 1–8 hours.
  - **Full** (the whole room) or **partial** (sharing is fine, with a number of seats).
  - **Purpose:** quiet study, group study, gaming, meeting, board games, event, or custom text.
- **Noise detector for partial bookings:** every room shows a live noise level, so someone who wants silence can
  choose another room. One room is measured by the real PSOC Edge E84 microphone. The others are simulated.
- **People estimate** per room. The board's room uses the board's sensor; the others are estimated from bookings
  plus simulated noise.
- **3D view:** building V floats in empty space with no terrain. It is a rectangular ring with a courtyard hole,
  like Google Earth, and you can rotate and zoom it. Searching `V.1.07a` flies the camera to that room and hides
  everything else.

All numbers are made up. This is a prototype.

## Architecture
```
PSOC Edge E84 (Live Lab): mic -> noise dB, radar -> presence, display = door panel
      | serial / lab console
   bridge/ --POST /api/readings-->  FastAPI + SQLite (app/)  <--POST /api/readings-- sim/ (other rooms)
                                          |  serves web/ at /
   web/: login page, 3D building (Three.js), room panel + booking form, search
```
- **Stack:** Python 3.12, FastAPI, SQLite (one file through the standard-library `sqlite3`), and static HTML/JS
  with **Three.js from a CDN**, so there is no build step.
- **Run:** `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`, then open http://localhost:8000.

## Data model (SQLite, seeded at startup)
- `users(id, email, name, password_hash)`, with the 4 demo accounts
- `rooms(id "V.1.07a", floor, capacity, has_sensor)`. Geometry comes from `web/data/building_v.json`.
- `bookings(id, room_id, user_id, start, end, mode "full"|"partial", seats, purpose, custom_purpose)`
- `readings(room_id, ts, noise_db, people, presence, source "psoc-e84"|"sim")`. Only the latest reading per room
  is needed.

**Noise classes** (made up): quiet below 40 dB, moderate from 40 to 60 dB, loud above 60 dB.
**Purpose → noise class:** quiet study is quiet. Group study, meeting and custom are moderate. Gaming, board games
and events are loud.

**Booking rules:**
- **Full** needs no overlapping booking at all.
- **Partial** needs:
  - no overlapping full booking;
  - booked seats plus the estimated people to fit within capacity;
  - purposes that don't clash. A quiet booking can't share with a loud one, and the API returns this as a warning
    together with 3 suggested rooms.
- **Events** must be full bookings.

## API contract (code against this; don't wait for each other)
| Method | Path | Body / result |
|---|---|---|
| POST | `/api/login` | `{email, password}` sets a session cookie. `/api/logout`, `GET /api/me` |
| GET | `/api/rooms` | `[{id, floor, capacity, status, noise_db, noise_class, people, live, bookings_now:[...]}]` |
| GET | `/api/rooms/{id}` | the room above plus today's bookings |
| POST | `/api/bookings` | `{room_id, start, hours, mode, seats, purpose, custom_purpose}` returns the booking, or `409 {error, suggestions:[room_id]}` |
| GET / DELETE | `/api/bookings/mine`, `/api/bookings/{id}` | the user's bookings and cancelling one |
| GET | `/api/suggest?hours=&mode=&seats=&purpose=` | rooms ranked by fit, with the quietest first for quiet study |
| POST | `/api/readings` | `{room_id, noise_db, people, presence, source}` from the bridge or sim (CORS open) |

`status` is one of `free`, `partial`, `full` or `ghost`. `ghost` means booked but nobody present; this is a bonus
and only exists for the board's room. `live: true` marks the board's room.

## 3D model (`web/data/building_v.json` + `web/js/building3d.js`)
- The data file lists 3 floors, 0 to 2. Each room is `{id, floor, x, z, w, d, capacity}` in metres, in a ring:
  an outer rectangle of 60×40 m around a 30×16 m courtyard, with roughly 10 rooms per floor and IDs like
  `V.0.03` or `V.1.07a`.
  Real room numbers from https://campusplan.aau.at/ are only needed if they're cheap to get. Otherwise make them up.
- Building module API, used by the UI:
  `createBuilding(el, rooms) -> {setStatus(id, status, noiseClass), focusRoom(id), showAll(), setFloor(n|null), onRoomClick(cb)}`
- `focusRoom` animates the camera to the room and hides or fades all other meshes. `showAll` restores the view.
  Colours: free is white, partial is amber, full is red, loud gets a red pulse, and the live room gets a badge.

## Roles: each agent owns its files
| Agent | Owns | Delivers |
|---|---|---|
| **A: Board** (Tom + Claude Code) | `bridge/`, `docs/board.md` | Live Lab: noise in dB from the board microphone (must have), presence or people from radar (nice to have), and the display as a door panel (wow factor) for the live room `V.1.07a`. Bridge to `/api/readings`, plus a screen recording of the board. |
| **B: Backend** | `app/`, `sim/`, `tests/`, `requirements.txt` | Database, login, the booking rules, every endpoint above, and `sim/simulate.py` (noise and people for the other rooms, correlated with booking purposes). **Push stub endpoints with seed data first.** |
| **C: 3D** | `web/js/building3d.js`, `web/data/building_v.json` | The floating building model, rotate and zoom, `focusRoom` and isolate, floor filter, status colours. |
| **D: UI** | `web/index.html`, `web/login.html`, `web/js/app.js`, `web/css/`, `docs/DEMO.md` | The login page, search bar (calls `focusRoom`), room panel with live noise and people, booking form with suggestions on conflict, "my bookings", the demo script and the pitch. |

## Using the board wisely (impress the jury, spend few tokens)
1. **Real noise from the real microphone** feeds the partial-booking decision. This is the core of the demo.
2. **Presence** from radar, if the lab exposes it. A booked room with nobody present is shown as a ghost.
3. **Door panel on the board's display**, if we can flash firmware. It shows
   "V.1.07a · partial · quiet study · 38 dB", turns red when it's too loud, and the button checks you in.

If something isn't reachable in the Live Lab, simulate it and say so. The challenge allows simulated signals.

## Rules for every agent
- **All cross-LLM communication happens on GitHub**: this file, `docs/agents/*.md`, and PR descriptions and comments.
  Start each work chunk with `git pull` and read what changed in `docs/`.
- Follow `AGENTS.md`: work on a branch `<name>/<task>`, open small PRs, never push to `main`, and add no AI
  attribution.
- **Document as you go** in `docs/agents/<letter>-<role>.md` (template: `docs/agents/_TEMPLATE.md`). Cover what you
  built, how to run it, decisions, and anything that's open. Keep it short.
- When you change a contract above, update this file in the same PR.
