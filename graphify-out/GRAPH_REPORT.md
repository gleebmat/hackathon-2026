# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 37 files · ~85,254 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .tflite 4, (none) 2, .example 1)

## Summary
- 571 nodes · 1445 edges · 21 communities (14 shown, 7 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 34 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `25ec2db7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- vision.py
- gen_campus.py
- building3d.js
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- test_api.py
- main.py
- api.js
- plan2d.js
- createPicker
- booking.py
- webcam.py

## God Nodes (most connected - your core abstractions)
1. `t()` - 46 edges
2. `user()` - 35 edges
3. `book()` - 32 edges
4. `main()` - 22 edges
5. `ApiError` - 21 edges
6. `createPicker()` - 21 edges
7. `room()` - 20 edges
8. `now()` - 18 edges
9. `esc()` - 18 edges
10. `request()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `3D campus map (tom-claude; built and working, standalone for now)` --references--> `pillars()`  [INFERRED]
  docs/PLAN.md → tools/campus3d/gen_campus.py
- `Roles` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `building()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `q()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js

## Import Cycles
- None detected.

## Communities (21 total, 7 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.29
Nodes (6): Board limits (the brief for choosing models), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup, The board: XIAO ESP32S3 Sense in Velxio

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.07
Nodes (92): agoText(), ask(), boardCard(), bookingCard(), busySlot(), canBook(), cancelBooking(), checkAlerts() (+84 more)

### Community 5 - "vision.py"
Cohesion: 0.07
Nodes (13): start(), count(), decrypt(), frame_key(), letterbox(), nms(), Room, start() (+5 more)

### Community 6 - "gen_campus.py"
Cohesion: 0.10
Nodes (20): fetch(), main(), frame(), outside_doors(), block_union(), coords(), final_clip(), floor_outlines() (+12 more)

### Community 7 - "building3d.js"
Cohesion: 0.25
Nodes (6): createBuilding(), HIDDEN_BY_DEFAULT, HOVER_COLOR, mountControls(), STATUS_COLOR, TYPE_COLOR

### Community 8 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.15
Nodes (12): 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used), Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items, PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+4 more)

### Community 11 - "test_api.py"
Cohesion: 0.08
Nodes (48): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_disconnect_and_recovery_during_demo() (+40 more)

### Community 13 - "main.py"
Cohesion: 0.05
Nodes (32): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+24 more)

### Community 14 - "api.js"
Cohesion: 0.13
Nodes (26): ApiError, ask(), availability(), book(), building(), calendar(), cancel(), login() (+18 more)

### Community 15 - "plan2d.js"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.12
Nodes (32): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map), people(), createPicker() (+24 more)

### Community 19 - "booking.py"
Cohesion: 0.06
Nodes (54): answer(), number(), parse(), ApiError, availability(), booking_out(), calendar(), can_rate() (+46 more)

### Community 20 - "webcam.py"
Cohesion: 0.11
Nodes (11): check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels(), main() (+3 more)

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` connect `booking.py` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`, `createPicker`, `api.js`?**
  _High betweenness centrality (0.414) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `ApiError` (e.g. with `answer()` and `add_booking()`) actually correct?**
  _`ApiError` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.07280701754385965 - nodes in this community are weakly interconnected._
- **Why does `people()` connect `createPicker` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`, `app.js`, `booking.py`, `api.js`?**
  _High betweenness centrality (0.361) - this node is a cross-community bridge._
- **Should `vision.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06533776301218161 - nodes in this community are weakly interconnected._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10121951219512196 - nodes in this community are weakly interconnected._
- **Should `test_api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0818452380952381 - nodes in this community are weakly interconnected._