# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 38 files · ~75,610 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .tflite 4, (none) 2, .example 1)

## Summary
- 577 nodes · 1437 edges · 23 communities (16 shown, 7 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8adc532b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- bridge.py
- mock-data.js
- building3d.js
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- createPlaceholder
- __init__.py
- setup.ps1
- main.py
- api.js
- createView
- createPicker
- gen_campus.py
- webcam.py

## God Nodes (most connected - your core abstractions)
1. `t()` - 46 edges
2. `user()` - 35 edges
3. `book()` - 32 edges
4. `main()` - 23 edges
5. `ApiError` - 21 edges
6. `createPicker()` - 21 edges
7. `room()` - 20 edges
8. `now()` - 18 edges
9. `esc()` - 18 edges
10. `request()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `building()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `Roles` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `q()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `can_rate()`  [INFERRED]
  docs/PLAN.md → app/booking.py

## Import Cycles
- None detected.

## Communities (23 total, 7 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.29
Nodes (6): Board limits (the brief for choosing models), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup, The board: XIAO ESP32S3 Sense in Velxio

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.06
Nodes (99): agoText(), ask(), boardCard(), bookingCard(), busySlot(), canBook(), cancelBooking(), checkAlerts() (+91 more)

### Community 5 - "bridge.py"
Cohesion: 0.07
Nodes (13): start(), count(), decrypt(), frame_key(), letterbox(), nms(), Room, start() (+5 more)

### Community 6 - "mock-data.js"
Cohesion: 0.08
Nodes (22): build_l(), build_n(), build_s(), build_wing(), build_z(), name_real_rooms(), snap_connectors(), teal_spans_m() (+14 more)

### Community 7 - "building3d.js"
Cohesion: 0.29
Nodes (6): createBuilding(), HIDDEN_BY_DEFAULT, HOVER_COLOR, mountControls(), STATUS_COLOR, TYPE_COLOR

### Community 8 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.15
Nodes (12): 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used), Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items, PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+4 more)

### Community 9 - "createPlaceholder"
Cohesion: 0.29
Nodes (6): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map)

### Community 11 - "__init__.py"
Cohesion: 0.08
Nodes (48): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_disconnect_and_recovery_during_demo() (+40 more)

### Community 12 - "setup.ps1"
Cohesion: 0.12
Nodes (11): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+3 more)

### Community 13 - "main.py"
Cohesion: 0.06
Nodes (35): now(), to_local(), api_error(), ask_assistant(), BookingRequest, calendar(), cancel_booking(), create_booking() (+27 more)

### Community 14 - "api.js"
Cohesion: 0.19
Nodes (21): ApiError, ask(), availability(), book(), building(), calendar(), cancel(), login() (+13 more)

### Community 15 - "createView"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.18
Nodes (25): createPicker(), cardHtml(), cardState(), choose(), defaultStart(), drawCalendar(), drawKinds(), expected() (+17 more)

### Community 19 - "gen_campus.py"
Cohesion: 0.08
Nodes (40): answer(), number(), parse(), ApiError, availability(), booking_out(), calendar(), can_rate() (+32 more)

### Community 20 - "webcam.py"
Cohesion: 0.10
Nodes (12): check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels(), main() (+4 more)

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` connect `gen_campus.py` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`, `app.js`, `api.js`?**
  _High betweenness centrality (0.406) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `ApiError` (e.g. with `answer()` and `add_booking()`) actually correct?**
  _`ApiError` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.06483516483516484 - nodes in this community are weakly interconnected._
- **Why does `people()` connect `app.js` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`, `createPicker`, `gen_campus.py`?**
  _High betweenness centrality (0.337) - this node is a cross-community bridge._
- **Should `bridge.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06538461538461539 - nodes in this community are weakly interconnected._
- **Should `mock-data.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08478513356562137 - nodes in this community are weakly interconnected._
- **Should `__init__.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07726075504828797 - nodes in this community are weakly interconnected._