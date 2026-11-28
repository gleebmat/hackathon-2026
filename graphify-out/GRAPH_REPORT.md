# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 33 files · ~95,587 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .tflite 4, (none) 2, .example 1)

## Summary
- 487 nodes · 1170 edges · 22 communities (13 shown, 9 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 33 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `27ba5171`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- gen_campus.py
- building3d.js
- test_api.py
- db.py
- main.py
- api.js
- plan2d.js
- createPicker
- booking.py
- webcam.py

## God Nodes (most connected - your core abstractions)
1. `t()` - 37 edges
2. `user()` - 30 edges
3. `book()` - 27 edges
4. `main()` - 19 edges
5. `createPicker()` - 19 edges
6. `ApiError` - 17 edges
7. `now()` - 16 edges
8. `room_state()` - 16 edges
9. `request()` - 15 edges
10. `renderForm()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `building()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `q()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `claude-3 (Website UI)` --references--> `people()`  [INFERRED]
  docs/LOG.md → web/js/i18n.js
- `gleb-claude (Backend + integration)` --references--> `people()`  [INFERRED]
  docs/LOG.md → web/js/i18n.js
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js

## Import Cycles
- None detected.

## Communities (22 total, 9 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.29
Nodes (6): Board limits (the brief for choosing models), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup, The board: XIAO ESP32S3 Sense in Velxio

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.09
Nodes (75): bookingCard(), busySlot(), canBook(), cancelBooking(), closeSheet(), closeSuggestions(), confetti(), copyRoomLink() (+67 more)

### Community 6 - "gen_campus.py"
Cohesion: 0.08
Nodes (23): build_l(), build_n(), build_s(), build_v(), build_wing(), build_z(), name_real_rooms(), snap_connectors() (+15 more)

### Community 7 - "building3d.js"
Cohesion: 0.29
Nodes (6): createBuilding(), HIDDEN_BY_DEFAULT, HOVER_COLOR, mountControls(), STATUS_COLOR, TYPE_COLOR

### Community 11 - "test_api.py"
Cohesion: 0.09
Nodes (41): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_disconnect_and_recovery_during_demo() (+33 more)

### Community 12 - "db.py"
Cohesion: 0.09
Nodes (12): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+4 more)

### Community 13 - "main.py"
Cohesion: 0.06
Nodes (29): now(), to_local(), api_error(), BookingRequest, calendar(), cancel_booking(), create_booking(), Credentials (+21 more)

### Community 14 - "api.js"
Cohesion: 0.13
Nodes (25): ApiError, availability(), book(), building(), calendar(), cancel(), login(), logout() (+17 more)

### Community 15 - "plan2d.js"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.08
Nodes (41): claude-2 (3D model), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map), 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used) (+33 more)

### Community 19 - "booking.py"
Cohesion: 0.11
Nodes (36): ApiError, availability(), booking_out(), calendar(), can_rate(), create_booking(), current_bookings(), fmt() (+28 more)

### Community 20 - "webcam.py"
Cohesion: 0.18
Nodes (11): check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels(), main() (+3 more)

## Knowledge Gaps
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `people()` connect `createPicker` to `app.js`, `booking.py`, `api.js`?**
  _High betweenness centrality (0.327) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08591408591408592 - nodes in this community are weakly interconnected._
- **Why does `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` connect `booking.py` to `createPicker`, `api.js`?**
  _High betweenness centrality (0.285) - this node is a cross-community bridge._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07777777777777778 - nodes in this community are weakly interconnected._
- **Should `test_api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08896103896103896 - nodes in this community are weakly interconnected._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0928030303030303 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06293706293706294 - nodes in this community are weakly interconnected._