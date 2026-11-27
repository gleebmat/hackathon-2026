# Graph Report - hackathon-2026  (2026-11-27)

## Corpus Check
- 31 files · ~46,729 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .example 1, .css 1)

## Summary
- 461 nodes · 1057 edges · 20 communities (15 shown, 5 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3069ae7c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- gen_campus.py
- test_ntfy_feed.py
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- gen_campus.py
- building3d.js
- bridge.py
- test_api.py
- db.py
- main.py
- inference_task.c
- setup_person.ps1
- createPicker
- booking.py

## God Nodes (most connected - your core abstractions)
1. `user()` - 26 edges
2. `book()` - 23 edges
3. `createPicker()` - 17 edges
4. `ApiError` - 16 edges
5. `now()` - 16 edges
6. `room_state()` - 16 edges
7. `request()` - 15 edges
8. `loadSheetData()` - 14 edges
9. `renderForm()` - 14 edges
10. `submitBooking()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `gleb-claude (Backend + integration)` --references--> `showMapTip()`  [INFERRED]
  docs/LOG.md → web/js/app.js
- `gleb-claude (Backend + integration)` --references--> `free_hours()`  [INFERRED]
  docs/LOG.md → app/booking.py
- `claude-3 (Website UI)` --references--> `free_hours()`  [INFERRED]
  docs/LOG.md → app/booking.py
- `claude-3 (Website UI)` --references--> `createBuilding()`  [INFERRED]
  docs/LOG.md → web/map3d/building3d.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `can_rate()`  [INFERRED]
  docs/PLAN.md → app/booking.py

## Import Cycles
- None detected.

## Communities (20 total, 5 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.33
Nodes (5): Demo with the real board (runbook), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "gen_campus.py"
Cohesion: 0.10
Nodes (61): bookingCard(), busySlot(), canBook(), cancelBooking(), closeSheet(), closeSuggestions(), confetti(), createView() (+53 more)

### Community 4 - "test_ntfy_feed.py"
Cohesion: 0.12
Nodes (12): LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet(), test_classes(), test_floor_ignores_noise_bursts(), test_loud_is_loud() (+4 more)

### Community 5 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.15
Nodes (12): 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board (Live Lab): decisions and next steps for tom-claude, Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items (tom-claude, in `detector/` and `app/lost_items.py`), PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+4 more)

### Community 6 - "gen_campus.py"
Cohesion: 0.09
Nodes (22): build_l(), build_n(), build_s(), build_wing(), build_z(), name_real_rooms(), snap_connectors(), teal_spans_m() (+14 more)

### Community 7 - "building3d.js"
Cohesion: 0.14
Nodes (12): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map), createBuilding(), HIDDEN_BY_DEFAULT (+4 more)

### Community 8 - "bridge.py"
Cohesion: 0.15
Nodes (12): bars_to_db(), Calibrator, main(), open_port(), parse(), reading(), send(), fresh() (+4 more)

### Community 11 - "test_api.py"
Cohesion: 0.10
Nodes (35): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_room_presence_and_live() (+27 more)

### Community 12 - "db.py"
Cohesion: 0.12
Nodes (12): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+4 more)

### Community 13 - "main.py"
Cohesion: 0.07
Nodes (31): now(), to_local(), api_error(), BookingRequest, calendar(), cancel_booking(), create_booking(), Credentials (+23 more)

### Community 14 - "inference_task.c"
Cohesion: 0.20
Nodes (16): ApiError, availability(), book(), calendar(), cancel(), login(), logout(), me() (+8 more)

### Community 15 - "setup_person.ps1"
Cohesion: 0.31
Nodes (8): createPlan(), render(), roomSvg(), schedule(), esc(), layoutBuilding(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.18
Nodes (23): capital(), createPicker(), cardHtml(), cardState(), choose(), defaultStart(), drawPop(), expected() (+15 more)

### Community 19 - "booking.py"
Cohesion: 0.12
Nodes (32): ApiError, availability(), booking_out(), calendar(), can_rate(), create_booking(), current_bookings(), fmt() (+24 more)

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `free_hours()` connect `booking.py` to `building3d.js`?**
  _High betweenness centrality (0.387) - this node is a cross-community bridge._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1003584229390681 - nodes in this community are weakly interconnected._
- **Why does `gleb-claude (Backend + integration)` connect `building3d.js` to `gen_campus.py`, `booking.py`?**
  _High betweenness centrality (0.346) - this node is a cross-community bridge._
- **Should `test_ntfy_feed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1164021164021164 - nodes in this community are weakly interconnected._
- **Why does `showMapTip()` connect `gen_campus.py` to `building3d.js`?**
  _High betweenness centrality (0.337) - this node is a cross-community bridge._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08902439024390243 - nodes in this community are weakly interconnected._
- **Should `building3d.js` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._