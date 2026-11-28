# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 38 files · ~75,510 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .tflite 4, (none) 2, .example 1)

## Summary
- 576 nodes · 1435 edges · 27 communities (19 shown, 8 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3c56a13`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- bridge.py
- mock-data.js
- building3d.js
- now
- createPlaceholder
- __init__.py
- setup.ps1
- main.py
- api.js
- createView
- ApiError
- createPicker
- gen_campus.py
- webcam.py
- room_detail
- listed_rooms
- NoCacheStatic

## God Nodes (most connected - your core abstractions)
1. `t()` - 46 edges
2. `user()` - 35 edges
3. `book()` - 32 edges
4. `main()` - 22 edges
5. `ApiError` - 21 edges
6. `createPicker()` - 21 edges
7. `room()` - 20 edges
8. `esc()` - 18 edges
9. `now()` - 18 edges
10. `room_state()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Roles` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `my_rating()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `free_hours()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `can_rate()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js

## Import Cycles
- None detected.

## Communities (27 total, 8 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.29
Nodes (6): Board limits (the brief for choosing models), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup, The board: XIAO ESP32S3 Sense in Velxio

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (98): agoText(), ask(), boardCard(), bookingCard(), busySlot(), canBook(), cancelBooking(), checkAlerts() (+90 more)

### Community 5 - "bridge.py"
Cohesion: 0.05
Nodes (16): number(), parse(), start(), count(), decrypt(), frame_key(), letterbox(), nms() (+8 more)

### Community 6 - "mock-data.js"
Cohesion: 0.08
Nodes (22): build_l(), build_n(), build_s(), build_wing(), build_z(), name_real_rooms(), snap_connectors(), teal_spans_m() (+14 more)

### Community 7 - "building3d.js"
Cohesion: 0.29
Nodes (6): createBuilding(), HIDDEN_BY_DEFAULT, HOVER_COLOR, mountControls(), STATUS_COLOR, TYPE_COLOR

### Community 8 - "now"
Cohesion: 0.13
Nodes (10): now(), to_local(), ask_assistant(), calendar(), cancel_booking(), create_booking(), me(), my_bookings() (+2 more)

### Community 9 - "createPlaceholder"
Cohesion: 0.29
Nodes (6): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map)

### Community 11 - "__init__.py"
Cohesion: 0.08
Nodes (47): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_disconnect_and_recovery_during_demo() (+39 more)

### Community 12 - "setup.ps1"
Cohesion: 0.12
Nodes (11): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+3 more)

### Community 13 - "main.py"
Cohesion: 0.11
Nodes (17): BookingRequest, Credentials, in_transaction(), lifespan(), login(), logout(), mqtt_reading(), post_reading() (+9 more)

### Community 14 - "api.js"
Cohesion: 0.09
Nodes (34): 3D campus map (tom-claude; built and working, standalone for now), API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used), Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items, PLAN: Smart Campus Room Booking (Infineon challenge), building V (+26 more)

### Community 15 - "createView"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 17 - "ApiError"
Cohesion: 0.18
Nodes (9): answer(), ApiError, slot_start(), validate_times(), add_booking(), target(), tick(), user_id() (+1 more)

### Community 18 - "createPicker"
Cohesion: 0.18
Nodes (25): createPicker(), cardHtml(), cardState(), choose(), defaultStart(), drawCalendar(), drawKinds(), expected() (+17 more)

### Community 19 - "gen_campus.py"
Cohesion: 0.15
Nodes (24): availability(), booking_out(), calendar(), can_rate(), create_booking(), current_bookings(), fmt(), free_hours() (+16 more)

### Community 20 - "webcam.py"
Cohesion: 0.10
Nodes (12): check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels(), main() (+4 more)

### Community 23 - "room_detail"
Cohesion: 0.33
Nodes (5): api_error(), current_user(), room_detail(), session_user(), validation_error()

### Community 25 - "listed_rooms"
Cohesion: 0.33
Nodes (6): listed_rooms(), _norm(), search(), search_rank(), rooms(), search()

## Knowledge Gaps
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` connect `api.js` to `app.js`, `gen_campus.py`?**
  _High betweenness centrality (0.405) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `ApiError` (e.g. with `answer()` and `add_booking()`) actually correct?**
  _`ApiError` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.06572068707991038 - nodes in this community are weakly interconnected._
- **Why does `people()` connect `app.js` to `createPicker`, `api.js`?**
  _High betweenness centrality (0.336) - this node is a cross-community bridge._
- **Should `bridge.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05442176870748299 - nodes in this community are weakly interconnected._
- **Why does `can_rate()` connect `gen_campus.py` to `api.js`, `room_detail`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Should `mock-data.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08478513356562137 - nodes in this community are weakly interconnected._