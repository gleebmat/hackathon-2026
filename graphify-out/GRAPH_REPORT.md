# Graph Report - hackathon-2026  (2026-11-27)

## Corpus Check
- 18 files · ~8,193 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .example 1)

## Summary
- 198 nodes · 384 edges · 19 communities (14 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `76cd8298`
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
- suggest
- ApiError
- main.py
- now
- register
- create_booking

## God Nodes (most connected - your core abstractions)
1. `ApiError` - 14 edges
2. `room_state()` - 14 edges
3. `user()` - 13 edges
4. `LiveNoiseFeed` - 12 edges
5. `suggest()` - 11 edges
6. `book()` - 11 edges
7. `room_problem()` - 10 edges
8. `create_booking()` - 10 edges
9. `availability()` - 10 edges
10. `now()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --calls--> `LiveNoiseFeed`  [EXTRACTED]
  app/main.py → bridge/ntfy_feed.py
- `register()` --calls--> `valid_email()`  [EXTRACTED]
  app/main.py → app/auth.py
- `create_booking()` --uses--> `ApiError`  [INFERRED]
  app/main.py → app/booking.py
- `register()` --calls--> `hash_password()`  [EXTRACTED]
  app/main.py → app/auth.py
- `login()` --calls--> `check_password()`  [EXTRACTED]
  app/main.py → app/auth.py

## Import Cycles
- None detected.

## Communities (19 total, 5 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.50
Nodes (3): Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "bridge.py"
Cohesion: 0.27
Nodes (3): main(), publish(), to_db()

### Community 4 - "test_ntfy_feed.py"
Cohesion: 0.12
Nodes (12): LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet(), test_classes(), test_floor_ignores_noise_bursts(), test_loud_is_loud() (+4 more)

### Community 5 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.17
Nodes (11): 3D module API (claude-2; used by claude-3), API (gleb-claude; implemented in `app/`, tested in `tests/test_api.py`), Architecture, Contracts (code against these; whoever changes one updates this file in the same PR), Lost items (tom-claude, in `detector/` and `app/lost_items.py`), PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product, Roles (+3 more)

### Community 6 - "booking.py"
Cohesion: 0.23
Nodes (17): availability(), booking_out(), create_booking(), fmt(), fresh_reading(), get_room(), loudest(), noise_class() (+9 more)

### Community 7 - "LOG: one section per agent"
Cohesion: 0.29
Nodes (6): claude-2 (3D model), claude-3 (Website UI), gemini (Data, simulation, demo), gleb-claude (Backend), LOG: one section per agent, tom-claude (Backend + Board)

### Community 11 - "test_api.py"
Cohesion: 0.15
Nodes (15): app_env(), book(), test_availability_slots(), test_cancel_only_own(), test_daily_limit_and_own_overlap(), test_full_booking_blocks_others_and_suggests(), test_ghost_booking_is_released(), test_login_and_me() (+7 more)

### Community 12 - "db.py"
Cohesion: 0.17
Nodes (8): check_password(), hash_password(), new_token(), valid_email(), connect(), db_path(), init(), load_rooms()

### Community 13 - "suggest"
Cohesion: 0.18
Nodes (8): live_data(), local_naive(), matches(), me(), my_bookings(), room_availability(), rooms(), suggest()

### Community 14 - "ApiError"
Cohesion: 0.22
Nodes (4): ApiError, api_error(), cancel_booking(), current_user()

### Community 16 - "now"
Cohesion: 0.33
Nodes (4): now(), get_conn(), post_reading(), Reading

### Community 17 - "register"
Cohesion: 0.60
Nodes (4): login(), logout(), register(), start_session()

### Community 18 - "create_booking"
Cohesion: 0.40
Nodes (4): BookingRequest, create_booking(), Credentials, Registration

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LiveNoiseFeed` connect `test_ntfy_feed.py` to `main.py`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ApiError` (e.g. with `api_error()` and `create_booking()`) actually correct?**
  _`ApiError` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_ntfy_feed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1164021164021164 - nodes in this community are weakly interconnected._
- **Why does `ApiError` connect `ApiError` to `booking.py`, `main.py`, `now`, `register`, `create_booking`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `suggest()` connect `suggest` to `now`, `booking.py`, `main.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._