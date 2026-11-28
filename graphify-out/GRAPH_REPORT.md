# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 41 files · ~99,930 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .tflite 4, (none) 2, .example 1)

## Summary
- 690 nodes · 1815 edges · 36 communities (24 shown, 12 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `96273ee0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- vision.py
- mock-data.js
- building3d.js
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- re
- __init__.py
- now
- main.py
- api.js
- createView
- createPicker
- gen_campus.py
- webcam.py
- LOG: one section per agent
- db.py
- display.py
- display_selfie
- display_room
- ApiError
- suggest
- Launcher
- count
- mqtt_feed.py
- camera_frame
- Room
- NoCacheStatic

## God Nodes (most connected - your core abstractions)
1. `t()` - 51 edges
2. `user()` - 44 edges
3. `book()` - 37 edges
4. `room()` - 30 edges
5. `now()` - 28 edges
6. `main()` - 26 edges
7. `ApiError` - 25 edges
8. `createPicker()` - 21 edges
9. `esc()` - 20 edges
10. `request()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `3D campus map (tom-claude; built and working, standalone for now)` --references--> `pillars()`  [INFERRED]
  docs/PLAN.md → tools/campus3d/gen_campus.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `can_rate()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `free_hours()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `likes()`  [INFERRED]
  docs/PLAN.md → app/booking.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `my_rating()`  [INFERRED]
  docs/PLAN.md → app/booking.py

## Import Cycles
- None detected.

## Communities (36 total, 12 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.29
Nodes (6): Board limits (the brief for choosing models), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup, The board: XIAO ESP32S3 Sense in Velxio

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.06
Nodes (115): agoText(), ask(), boardCard(), bookingCard(), busySlot(), canBook(), cancelBooking(), checkAlerts() (+107 more)

### Community 5 - "vision.py"
Cohesion: 0.16
Nodes (4): frame_key(), start(), Vision, test_key_is_read_from_the_firmware_header()

### Community 6 - "mock-data.js"
Cohesion: 0.10
Nodes (21): fetch(), main(), frame(), outside_doors(), block_union(), coords(), final_clip(), floor_outlines() (+13 more)

### Community 7 - "building3d.js"
Cohesion: 0.25
Nodes (6): createBuilding(), HIDDEN_BY_DEFAULT, HOVER_COLOR, mountControls(), STATUS_COLOR, TYPE_COLOR

### Community 8 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.14
Nodes (13): 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used), Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items, PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+5 more)

### Community 11 - "__init__.py"
Cohesion: 0.07
Nodes (65): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_disconnect_and_recovery_during_demo() (+57 more)

### Community 12 - "now"
Cohesion: 0.18
Nodes (14): now(), add_favorite(), ask_assistant(), calendar(), cancel_booking(), display_booking_qr(), get_selfie(), me() (+6 more)

### Community 13 - "main.py"
Cohesion: 0.10
Nodes (16): Credentials, display_sound(), EmergencyRequest, get_conn(), in_transaction(), lifespan(), mqtt_reading(), post_reading() (+8 more)

### Community 14 - "api.js"
Cohesion: 0.17
Nodes (23): ApiError, ask(), availability(), book(), calendar(), cancel(), favorites(), like() (+15 more)

### Community 15 - "createView"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.18
Nodes (25): createPicker(), cardHtml(), cardState(), choose(), defaultStart(), drawCalendar(), drawKinds(), expected() (+17 more)

### Community 19 - "gen_campus.py"
Cohesion: 0.08
Nodes (44): answer(), number(), parse(), availability(), booking_out(), calendar(), can_rate(), create_booking() (+36 more)

### Community 20 - "webcam.py"
Cohesion: 0.13
Nodes (12): heard(), check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels() (+4 more)

### Community 23 - "LOG: one section per agent"
Cohesion: 0.25
Nodes (7): arshia (Room display page), claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map)

### Community 24 - "db.py"
Cohesion: 0.16
Nodes (10): check_password(), hash_password(), valid_email(), columns(), connect(), db_path(), init(), load_rooms() (+2 more)

### Community 25 - "display.py"
Cohesion: 0.12
Nodes (8): new_token(), find_browser(), qr_svg(), room_noise(), selfie(), set_sound(), sound(), take_selfie()

### Community 26 - "display_selfie"
Cohesion: 0.18
Nodes (8): public_url(), api_error(), booking_link(), current_user(), display_selfie(), display_state(), session_user(), validation_error()

### Community 27 - "display_room"
Cohesion: 0.19
Nodes (8): BreakRequest, display_break(), display_break_end(), display_emergency(), display_emergency_end(), display_room(), emergency_out(), open_emergency()

### Community 28 - "ApiError"
Cohesion: 0.29
Nodes (7): ApiError, BookingRequest, create_booking(), login(), logout(), register(), start_session()

### Community 30 - "Launcher"
Cohesion: 0.29
Nodes (3): Launcher, online(), start()

### Community 31 - "count"
Cohesion: 0.24
Nodes (4): count(), letterbox(), nms(), test_count_keeps_one_box_per_object_and_only_near_items()

### Community 33 - "camera_frame"
Cohesion: 0.40
Nodes (3): camera_frame(), decrypt(), test_frame_decrypts_like_the_board_encrypts()

## Knowledge Gaps
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Contracts (code against these; whoever changes one updates this file in the same PR)` connect `PLAN: Smart Campus Room Booking (Infineon challenge), building V` to `gen_campus.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05716253443526171 - nodes in this community are weakly interconnected._
- **Why does `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` connect `gen_campus.py` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `mock-data.js` be split into smaller, more focused modules?**
  _Cohesion score 0.09745293466223699 - nodes in this community are weakly interconnected._
- **Should `PLAN: Smart Campus Room Booking (Infineon challenge), building V` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Should `__init__.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06504702194357367 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09879032258064516 - nodes in this community are weakly interconnected._