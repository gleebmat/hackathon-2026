# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 36 files · ~66,071 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .tflite 2, .example 1)

## Summary
- 513 nodes · 1167 edges · 23 communities (17 shown, 6 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 20 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b5e9ba3d`
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
- plan2d.js
- createPicker
- webcam.py
- webcam.py
- Live Lab test: real PSOC Edge E84 -> website (27 Nov, 23:10-23:36)

## God Nodes (most connected - your core abstractions)
1. `user()` - 27 edges
2. `book()` - 24 edges
3. `ApiError` - 17 edges
4. `createPicker()` - 17 edges
5. `room_state()` - 16 edges
6. `now()` - 16 edges
7. `request()` - 15 edges
8. `loadSheetData()` - 14 edges
9. `renderForm()` - 14 edges
10. `room()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `claude-3 (Website UI)` --references--> `free_hours()`  [INFERRED]
  docs/LOG.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `my_rating()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `free_hours()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `can_rate()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `claude-3 (Website UI)` --references--> `createBuilding()`  [INFERRED]
  docs/LOG.md → web/map3d/building3d.js

## Import Cycles
- None detected.

## Communities (23 total, 6 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.33
Nodes (5): Demo with the board (XIAO ESP32S3 Sense in Velxio), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "gen_campus.py"
Cohesion: 0.09
Nodes (65): bookingCard(), busySlot(), canBook(), cancelBooking(), closeSheet(), closeSuggestions(), confetti(), createView() (+57 more)

### Community 4 - "test_ntfy_feed.py"
Cohesion: 0.12
Nodes (12): LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet(), test_classes(), test_floor_ignores_noise_bursts(), test_loud_is_loud() (+4 more)

### Community 5 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.15
Nodes (12): 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used), Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items (tom-claude, in `detector/` and `app/lost_items.py`), PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+4 more)

### Community 6 - "gen_campus.py"
Cohesion: 0.08
Nodes (23): build_l(), build_n(), build_s(), build_v(), build_wing(), build_z(), name_real_rooms(), snap_connectors() (+15 more)

### Community 7 - "building3d.js"
Cohesion: 0.14
Nodes (12): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map), createBuilding(), HIDDEN_BY_DEFAULT (+4 more)

### Community 8 - "bridge.py"
Cohesion: 0.14
Nodes (12): bars_to_db(), Calibrator, main(), open_port(), parse(), reading(), send(), fresh() (+4 more)

### Community 11 - "test_api.py"
Cohesion: 0.09
Nodes (39): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_left_items() (+31 more)

### Community 12 - "db.py"
Cohesion: 0.10
Nodes (11): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+3 more)

### Community 13 - "main.py"
Cohesion: 0.07
Nodes (32): now(), to_local(), api_error(), BookingRequest, calendar(), cancel_booking(), create_booking(), Credentials (+24 more)

### Community 14 - "inference_task.c"
Cohesion: 0.20
Nodes (16): ApiError, availability(), book(), calendar(), cancel(), login(), logout(), me() (+8 more)

### Community 15 - "plan2d.js"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.19
Nodes (24): capital(), createPicker(), cardHtml(), cardState(), choose(), defaultStart(), drawCalendar(), expected() (+16 more)

### Community 19 - "webcam.py"
Cohesion: 0.11
Nodes (33): ApiError, availability(), booking_out(), calendar(), can_rate(), create_booking(), current_bookings(), fmt() (+25 more)

### Community 20 - "webcam.py"
Cohesion: 0.18
Nodes (11): check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels(), main() (+3 more)

### Community 21 - "Live Lab test: real PSOC Edge E84 -> website (27 Nov, 23:10-23:36)"
Cohesion: 0.33
Nodes (5): Live Lab test: real PSOC Edge E84 -> website (27 Nov, 23:10-23:36), Still to do, Verdict, Website log, What happened, step by step

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `free_hours()` connect `webcam.py` to `building3d.js`?**
  _High betweenness centrality (0.364) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ApiError` (e.g. with `api_error()` and `create_booking()`) actually correct?**
  _`ApiError` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09317051108095885 - nodes in this community are weakly interconnected._
- **Why does `claude-3 (Website UI)` connect `building3d.js` to `webcam.py`?**
  _High betweenness centrality (0.357) - this node is a cross-community bridge._
- **Should `test_ntfy_feed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1164021164021164 - nodes in this community are weakly interconnected._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07751937984496124 - nodes in this community are weakly interconnected._
- **Should `building3d.js` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._