# Graph Report - hackathon-2026  (2026-11-27)

## Corpus Check
- 18 files · ~10,531 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .example 1)

## Summary
- 240 nodes · 527 edges · 14 communities (10 shown, 4 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `711d61f5`
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
- test_api.py
- db.py
- main.py

## God Nodes (most connected - your core abstractions)
1. `user()` - 23 edges
2. `book()` - 20 edges
3. `room_state()` - 16 edges
4. `ApiError` - 15 edges
5. `now()` - 14 edges
6. `suggest()` - 12 edges
7. `LiveNoiseFeed` - 12 edges
8. `create_booking()` - 11 edges
9. `create_booking()` - 11 edges
10. `booking_out()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --calls--> `LiveNoiseFeed`  [EXTRACTED]
  app/main.py → bridge/ntfy_feed.py
- `register()` --calls--> `valid_email()`  [EXTRACTED]
  app/main.py → app/auth.py
- `api_error()` --uses--> `ApiError`  [INFERRED]
  app/main.py → app/booking.py
- `create_booking()` --uses--> `ApiError`  [INFERRED]
  app/main.py → app/booking.py
- `cancel_booking()` --calls--> `parse()`  [EXTRACTED]
  app/main.py → app/booking.py

## Import Cycles
- None detected.

## Communities (14 total, 4 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.50
Nodes (3): Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "bridge.py"
Cohesion: 0.17
Nodes (3): main(), publish(), to_db()

### Community 4 - "test_ntfy_feed.py"
Cohesion: 0.15
Nodes (12): LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet(), test_classes(), test_floor_ignores_noise_bursts(), test_loud_is_loud() (+4 more)

### Community 5 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.15
Nodes (12): 3D module API (claude-2; used by claude-3), API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`), Architecture, Contracts (code against these; whoever changes one updates this file in the same PR), Frontend flow (claude-3 / Martha; every call above is live on `uvicorn app.main:app`), Lost items (tom-claude, in `detector/` and `app/lost_items.py`), PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product (+4 more)

### Community 6 - "booking.py"
Cohesion: 0.18
Nodes (23): availability(), booking_out(), create_booking(), current_bookings(), fmt(), get_room(), ghost_deadline(), listed_rooms() (+15 more)

### Community 7 - "LOG: one section per agent"
Cohesion: 0.29
Nodes (6): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend), LOG: one section per agent, tom-claude (Backend + Board)

### Community 11 - "test_api.py"
Cohesion: 0.11
Nodes (31): app_env(), book(), reading(), room(), sensor_until(), test_availability_slots(), test_bad_input_gives_400_with_error(), test_cancel_only_own() (+23 more)

### Community 12 - "db.py"
Cohesion: 0.12
Nodes (12): check_password(), hash_password(), new_token(), valid_email(), columns(), connect(), db_path(), init() (+4 more)

### Community 13 - "main.py"
Cohesion: 0.08
Nodes (26): ApiError, now(), to_local(), api_error(), BookingRequest, cancel_booking(), create_booking(), Credentials (+18 more)

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LiveNoiseFeed` connect `test_ntfy_feed.py` to `bridge.py`, `db.py`, `main.py`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ApiError` (e.g. with `api_error()` and `create_booking()`) actually correct?**
  _`ApiError` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_ntfy_feed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._
- **Why does `ApiError` connect `main.py` to `booking.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Should `test_api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10963455149501661 - nodes in this community are weakly interconnected._
- **Why does `suggest()` connect `main.py` to `booking.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11965811965811966 - nodes in this community are weakly interconnected._