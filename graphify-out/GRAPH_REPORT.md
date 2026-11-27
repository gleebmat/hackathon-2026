# Graph Report - hackathon-2026  (2026-11-27)

## Corpus Check
- 23 files · ~17,290 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .example 1, .css 1)

## Summary
- 337 nodes · 782 edges · 18 communities (12 shown, 6 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e98782f1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- app.js
- app.js
- bridge.py
- mock-data.js
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- __init__.py
- setup.ps1
- GEMINI.md
- api.js
- createView

## God Nodes (most connected - your core abstractions)
1. `user()` - 23 edges
2. `book()` - 20 edges
3. `room_state()` - 16 edges
4. `loadSheetData()` - 16 edges
5. `ApiError` - 15 edges
6. `now()` - 14 edges
7. `renderForm()` - 14 edges
8. `submitBooking()` - 14 edges
9. `request()` - 13 edges
10. `suggest()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --calls--> `LiveNoiseFeed`  [EXTRACTED]
  app/main.py → bridge/ntfy_feed.py
- `register()` --calls--> `valid_email()`  [EXTRACTED]
  app/main.py → app/auth.py
- `register()` --calls--> `hash_password()`  [EXTRACTED]
  app/main.py → app/auth.py
- `login()` --calls--> `check_password()`  [EXTRACTED]
  app/main.py → app/auth.py
- `start_session()` --calls--> `new_token()`  [EXTRACTED]
  app/main.py → app/auth.py

## Import Cycles
- None detected.

## Communities (18 total, 6 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.50
Nodes (3): Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "app.js"
Cohesion: 0.10
Nodes (59): bookingCard(), busySlot(), canBook(), cancelBooking(), closeSheet(), closeSuggestions(), confetti(), dateKey() (+51 more)

### Community 4 - "app.js"
Cohesion: 0.08
Nodes (15): main(), publish(), to_db(), LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet() (+7 more)

### Community 5 - "bridge.py"
Cohesion: 0.15
Nodes (12): 3D module API (claude-2; used by claude-3), API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`), Architecture, Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items (tom-claude, in `detector/` and `app/lost_items.py`), PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+4 more)

### Community 6 - "mock-data.js"
Cohesion: 0.18
Nodes (23): availability(), booking_out(), create_booking(), current_bookings(), fmt(), get_room(), ghost_deadline(), listed_rooms() (+15 more)

### Community 7 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.29
Nodes (6): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend), LOG: one section per agent, tom-claude (Backend + Board)

### Community 11 - "__init__.py"
Cohesion: 0.11
Nodes (31): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_cancel_only_own() (+23 more)

### Community 12 - "setup.ps1"
Cohesion: 0.15
Nodes (10): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+2 more)

### Community 13 - "GEMINI.md"
Cohesion: 0.08
Nodes (28): ApiError, now(), to_local(), api_error(), BookingRequest, cancel_booking(), create_booking(), Credentials (+20 more)

### Community 14 - "api.js"
Cohesion: 0.24
Nodes (14): ApiError, availability(), book(), cancel(), login(), logout(), me(), myBookings() (+6 more)

### Community 15 - "createView"
Cohesion: 0.23
Nodes (11): building(), createView(), ./building3d.js, createPlan(), render(), roomSvg(), schedule(), esc() (+3 more)

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LiveNoiseFeed` connect `app.js` to `GEMINI.md`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.10218579234972677 - nodes in this community are weakly interconnected._
- **Why does `ApiError` connect `GEMINI.md` to `mock-data.js`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08232118758434548 - nodes in this community are weakly interconnected._
- **Why does `suggest()` connect `GEMINI.md` to `mock-data.js`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Should `__init__.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10963455149501661 - nodes in this community are weakly interconnected._
- **Should `GEMINI.md` be split into smaller, more focused modules?**
  _Cohesion score 0.07540983606557378 - nodes in this community are weakly interconnected._