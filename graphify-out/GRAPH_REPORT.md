# Graph Report - hackathon-2026  (2026-11-27)

## Corpus Check
- 14 files · ~6,809 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .css 1)

## Summary
- 124 nodes · 190 edges · 14 communities (10 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `76cd8298`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- hackathon-2026
- AGENTS.md
- test_ntfy_feed.py
- app.js
- bridge.py
- mock-data.js
- PLAN: Smart Campus Room Booking (Infineon challenge), building V
- main
- createPlaceholder
- LOG: one section per agent

## God Nodes (most connected - your core abstractions)
1. `LiveNoiseFeed` - 10 edges
2. `replay()` - 10 edges
3. `renderPanel()` - 9 edges
4. `main()` - 9 edges
5. `renderList()` - 7 edges
6. `selectRoom()` - 7 edges
7. `PLAN: Smart Campus Room Booking (Infineon challenge), building V` - 7 edges
8. `esc()` - 6 edges
9. `wireEvents()` - 6 edges
10. `getJson()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `claude-3 (Website UI)` --references--> `purpose()`  [INFERRED]
  docs/LOG.md → web/js/app.js
- `claude-3 (Website UI)` --references--> `setFloor()`  [INFERRED]
  docs/LOG.md → web/js/app.js
- `getRooms()` --calls--> `getRooms()`  [EXTRACTED]
  web/js/api.js → web/js/mock-data.js
- `getRoom()` --calls--> `getRoom()`  [EXTRACTED]
  web/js/api.js → web/js/mock-data.js
- `selectRoom()` --calls--> `getRoom()`  [EXTRACTED]
  web/js/app.js → web/js/api.js

## Import Cycles
- None detected.

## Communities (14 total, 4 thin omitted)

### Community 1 - "hackathon-2026"
Cohesion: 0.50
Nodes (3): Graphify (code knowledge graph, saves AI tokens), hackathon-2026, Setup

### Community 2 - "AGENTS.md"
Cohesion: 0.20
Nodes (8): Code, Docs, Git workflow (several people push to this repo at once), graphify (code knowledge graph in `graphify-out/`), Keep usage low, Project status (update when something important lands), Secrets, Stack

### Community 3 - "test_ntfy_feed.py"
Cohesion: 0.15
Nodes (12): LiveNoiseFeed, noise_class(), replay(), test_back_to_quiet_after_noise(), test_background_is_quiet(), test_classes(), test_floor_ignores_noise_bursts(), test_loud_is_loud() (+4 more)

### Community 4 - "app.js"
Cohesion: 0.25
Nodes (18): claude-3 (Website UI), clearSelection(), esc(), findRoom(), liveBadge(), purpose(), PURPOSE_LABEL, renderAll() (+10 more)

### Community 5 - "bridge.py"
Cohesion: 0.17
Nodes (3): main(), publish(), to_db()

### Community 6 - "mock-data.js"
Cohesion: 0.18
Nodes (14): at(), bookings, building, CAPACITIES, current(), getRoom(), getRooms(), NAMES (+6 more)

### Community 7 - "PLAN: Smart Campus Room Booking (Infineon challenge), building V"
Cohesion: 0.17
Nodes (11): 3D module API (claude-2; used by claude-3), API (tom-claude), Architecture, Contracts (code against these; whoever changes one updates this file in the same PR), Lost items (tom-claude), PLAN: Smart Campus Room Booking (Infineon challenge), building V, Product, Roles (+3 more)

### Community 8 - "main"
Cohesion: 0.36
Nodes (9): detectSource(), forced, getBuilding(), getJson(), getRoom(), getRooms(), main(), refresh() (+1 more)

### Community 9 - "createPlaceholder"
Cohesion: 0.47
Nodes (6): createPlaceholder(), plan(), render(), schedule(), createView(), ./building3d.js

### Community 10 - "LOG: one section per agent"
Cohesion: 0.40
Nodes (4): claude-2 (3D model), gemini (Data, simulation, demo), LOG: one section per agent, tom-claude (Backend + Board)

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LiveNoiseFeed` connect `test_ntfy_feed.py` to `bridge.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Should `test_ntfy_feed.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._
- **Why does `claude-3 (Website UI)` connect `app.js` to `LOG: one section per agent`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `LOG: one section per agent` connect `LOG: one section per agent` to `app.js`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._