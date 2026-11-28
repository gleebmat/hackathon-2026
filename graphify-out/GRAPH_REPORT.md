# Graph Report - hackathon-2026  (2026-11-28)

## Corpus Check
- 42 files · ~109,201 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .tflite 4, (none) 2, .example 1)

## Summary
- 714 nodes · 1879 edges · 38 communities (24 shown, 14 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 33 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a39232aa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- os
- gen_campus.py
- BaseModel
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- re
- test_api.py
- now
- main.py
- api.js
- plan2d.js
- createPicker
- booking.py
- json
- ApiError
- db.py
- Conn
- create_booking
- display.py
- Launcher
- vision.py
- display_state
- LOG: one section per agent
- Room
- NoCacheStatic
- mqtt_feed.py

## God Nodes (most connected - your core abstractions)
1. `t()` - 52 edges
2. `user()` - 45 edges
3. `book()` - 38 edges
4. `room()` - 31 edges
5. `now()` - 28 edges
6. `main()` - 26 edges
7. `ApiError` - 22 edges
8. `esc()` - 22 edges
9. `createPicker()` - 21 edges
10. `request()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `building()`  [INFERRED]
  docs/PLAN.md → web/js/api.js
- `Roles` --references--> `people()`  [INFERRED]
  docs/PLAN.md → web/js/i18n.js
- `3D campus map (tom-claude; built and working, standalone for now)` --references--> `room_doors()`  [INFERRED]
  docs/PLAN.md → tools/campus3d/fetch_plan.py
- `3D campus map (tom-claude; built and working, standalone for now)` --references--> `pillars()`  [INFERRED]
  docs/PLAN.md → tools/campus3d/gen_campus.py
- `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` --references--> `q()`  [INFERRED]
  docs/PLAN.md → web/js/api.js

## Import Cycles
- None detected.

## Communities (38 total, 14 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.29
Nodes (6): Board limits (the brief for choosing models), Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Run locally, Setup, The board: XIAO ESP32S3 Sense in Velxio

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.06
Nodes (113): agoText(), applyMapRoute(), applyRoute(), ask(), boardCard(), bookingCard(), buildView(), busySlot() (+105 more)

### Community 5 - "os"
Cohesion: 0.31
Nodes (4): check_password(), hash_password(), new_token(), valid_email()

### Community 6 - "gen_campus.py"
Cohesion: 0.07
Nodes (27): fetch(), main(), frame(), outside_doors(), room_doors(), stair_flights(), block_union(), coords() (+19 more)

### Community 7 - "BaseModel"
Cohesion: 0.40
Nodes (4): BookingRequest, rate_room(), RatingRequest, SoundRequest

### Community 8 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.08
Nodes (22): 3D campus map (tom-claude; built and working, standalone for now), Architecture, Board: XIAO ESP32S3 Sense on Velxio (the Infineon PSOC Edge E84 is no longer used), Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items, PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+14 more)

### Community 11 - "test_api.py"
Cohesion: 0.06
Nodes (66): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_board_disconnect_and_recovery_during_demo() (+58 more)

### Community 12 - "now"
Cohesion: 0.13
Nodes (12): now(), to_local(), add_favorite(), ask_assistant(), calendar(), create_booking(), me(), my_bookings() (+4 more)

### Community 13 - "main.py"
Cohesion: 0.13
Nodes (8): get_conn(), in_transaction(), lifespan(), mqtt_reading(), post_reading(), Reading, save_reading(), vision_reading()

### Community 14 - "api.js"
Cohesion: 0.17
Nodes (24): ApiError, ask(), availability(), book(), building(), calendar(), cancel(), favorites() (+16 more)

### Community 15 - "plan2d.js"
Cohesion: 0.36
Nodes (7): createPlan(), render(), roomSvg(), schedule(), esc(), OUTER, YARD

### Community 18 - "createPicker"
Cohesion: 0.17
Nodes (26): locale, createPicker(), cardHtml(), cardState(), choose(), defaultStart(), drawCalendar(), drawKinds() (+18 more)

### Community 19 - "booking.py"
Cohesion: 0.08
Nodes (44): answer(), number(), parse(), availability(), booking_out(), calendar(), can_rate(), create_booking() (+36 more)

### Community 20 - "json"
Cohesion: 0.13
Nodes (12): heard(), check_left_item(), main(), prep_96(), run_person_detect(), detect_left_items(), is_valid_new_object(), load_labels() (+4 more)

### Community 24 - "ApiError"
Cohesion: 0.15
Nodes (10): public_url(), api_error(), booking_link(), current_user(), display_booking_qr(), display_selfie(), rooms(), SelfieRequest (+2 more)

### Community 25 - "db.py"
Cohesion: 0.21
Nodes (7): columns(), connect(), db_path(), init(), load_rooms(), upgrade(), test_search_finds_map_labels()

### Community 26 - "Conn"
Cohesion: 0.24
Nodes (8): BreakRequest, cancel_booking(), display_break(), display_break_end(), display_emergency_end(), display_room(), display_sound(), remove_favorite()

### Community 27 - "create_booking"
Cohesion: 0.26
Nodes (8): ApiError, Credentials, get_selfie(), login(), logout(), register(), Registration, start_session()

### Community 28 - "display.py"
Cohesion: 0.19
Nodes (6): qr_svg(), room_noise(), selfie(), set_sound(), sound(), take_selfie()

### Community 29 - "Launcher"
Cohesion: 0.25
Nodes (4): find_browser(), Launcher, online(), start()

### Community 30 - "vision.py"
Cohesion: 0.10
Nodes (11): camera_frame(), count(), decrypt(), frame_key(), letterbox(), nms(), start(), Vision (+3 more)

### Community 32 - "display_state"
Cohesion: 0.28
Nodes (5): display_emergency(), display_state(), emergency_out(), EmergencyRequest, open_emergency()

### Community 33 - "LOG: one section per agent"
Cohesion: 0.25
Nodes (7): arshia (Room display page), claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend + integration), LOG: one section per agent, tom-claude (Board + 3D map)

## Knowledge Gaps
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `people()` connect `app.js` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`, `LOG: one section per agent`, `createPicker`, `booking.py`?**
  _High betweenness centrality (0.309) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.06039025779803447 - nodes in this community are weakly interconnected._
- **Why does `API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`)` connect `booking.py` to `PLAN: Smart Campus Room Booking (Infineon challenge), building V`, `app.js`, `api.js`?**
  _High betweenness centrality (0.305) - this node is a cross-community bridge._
- **Should `gen_campus.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._
- **Why does `likes()` connect `booking.py` to `LOG: one section per agent`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Should `PLAN: Smart Campus Room Booking (Infineon challenge), building V` be split into smaller, more focused modules?**
  _Cohesion score 0.08262108262108261 - nodes in this community are weakly interconnected._
- **Should `test_api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06460674157303371 - nodes in this community are weakly interconnected._