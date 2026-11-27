# Graph Report - hackathon-2026  (2026-11-27)

## Corpus Check
- 30 files · ~42,364 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .example 1, .css 1)

## Summary
- 406 nodes · 920 edges · 19 communities (14 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `62cb0223`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- bridge.py
- test_ntfy_feed.py
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- booking.py
- LOG: one section per agent
- bridge.py
- test_api.py
- db.py
- main.py
- inference_task.c
- setup_person.ps1
- gen_campus.py

## God Nodes (most connected - your core abstractions)
1. `user()` - 24 edges
2. `book()` - 21 edges
3. `room_state()` - 16 edges
4. `loadSheetData()` - 16 edges
5. `ApiError` - 15 edges
6. `renderForm()` - 14 edges
7. `submitBooking()` - 14 edges
8. `now()` - 14 edges
9. `request()` - 13 edges
10. `suggest()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --calls--> `LiveNoiseFeed`  [EXTRACTED]
  app/main.py → bridge/ntfy_feed.py
- `api_error()` --uses--> `ApiError`  [INFERRED]
  app/main.py → app/booking.py
- `create_booking()` --uses--> `ApiError`  [INFERRED]
  app/main.py → app/booking.py
- `register()` --calls--> `valid_email()`  [EXTRACTED]
  app/main.py → app/auth.py
- `cancel_booking()` --calls--> `ApiError`  [EXTRACTED]
  app/main.py → app/booking.py

## Import Cycles
- None detected.

## Communities (19 total, 5 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.33
Nodes (5): Demo with the real board (runbook), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "bridge.py"
Cohesion: 0.10
Nodes (60): boardRoom(), bookingCard(), busySlot(), canBook(), cancelBooking(), closeSheet(), closeSuggestions(), confetti() (+52 more)

### Community 4 - "test_ntfy_feed.py"
Cohesion: 0.12
Nodes (12): LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet(), test_classes(), test_floor_ignores_noise_bursts(), test_loud_is_loud() (+4 more)

### Community 5 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.14
Nodes (13): 3D campus map (tom-claude; built and working, standalone for now), API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`), Architecture, Board (Live Lab): decisions and next steps for tom-claude, Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items (tom-claude, in `detector/` and `app/lost_items.py`), PLAN: Smart Campus Room Booking (Infineon challenge), building V (+5 more)

### Community 6 - "booking.py"
Cohesion: 0.12
Nodes (31): ApiError, availability(), booking_out(), create_booking(), current_bookings(), fmt(), get_room(), ghost_deadline() (+23 more)

### Community 7 - "LOG: one section per agent"
Cohesion: 0.29
Nodes (6): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map)

### Community 8 - "bridge.py"
Cohesion: 0.16
Nodes (11): Calibrator, main(), open_port(), parse(), reading(), send(), fresh(), test_factory_firmware_sends_nothing() (+3 more)

### Community 11 - "test_api.py"
Cohesion: 0.11
Nodes (33): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_room_presence_and_live() (+25 more)

### Community 12 - "db.py"
Cohesion: 0.14
Nodes (10): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+2 more)

### Community 13 - "main.py"
Cohesion: 0.07
Nodes (22): now(), to_local(), api_error(), BookingRequest, cancel_booking(), create_booking(), Credentials, current_user() (+14 more)

### Community 14 - "inference_task.c"
Cohesion: 0.24
Nodes (14): ApiError, availability(), book(), cancel(), login(), logout(), me(), myBookings() (+6 more)

### Community 15 - "setup_person.ps1"
Cohesion: 0.15
Nodes (13): building(), createView(), createPlan(), render(), roomSvg(), schedule(), esc(), layoutBuilding() (+5 more)

### Community 18 - "gen_campus.py"
Cohesion: 0.09
Nodes (20): bars_to_db(), build_l(), build_n(), build_s(), build_v(), build_wing(), build_z(), snap_connectors() (+12 more)

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LiveNoiseFeed` connect `test_ntfy_feed.py` to `main.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Should `bridge.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09994711792702274 - nodes in this community are weakly interconnected._
- **Why does `ApiError` connect `booking.py` to `main.py`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Should `test_ntfy_feed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1164021164021164 - nodes in this community are weakly interconnected._
- **Should `PLAN: Smart Campus Room Booking (Infineon challenge), building V` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Should `booking.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `test_api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10707070707070707 - nodes in this community are weakly interconnected._