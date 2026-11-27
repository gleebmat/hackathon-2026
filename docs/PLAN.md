# PLAN: Smart Campus Room Assistant (Infineon challenge)

## Scenario (one story, end to end)
**Ghost booking → find a room.** A student needs a room for 3 people right now. The assistant finds that
**Z.1.09 is booked but the PSOC Edge E84 has sensed 0 people for N minutes**, so it is a ghost booking.
It explains what it found ("booked 16:00–18:00, nobody there for 22 min"), offers the room, and releases or flags
the booking. When the student walks in, the board senses presence and the floor map turns Z.1.09 red (occupied).

The board's role: **sensor plus door panel** for Z.1.09. Other rooms are simulated, which the challenge allows.
Stretch goal: lost-item reports per room. Only if the main story is fully done.

## Architecture
```
PSOC Edge E84 (Live Lab) --serial/console--> bridge/ --POST /api/signal--> FastAPI (app/)
                                                         sim/ (fake signals) --^        |
                         web/ (floor map + chat) <-- poll GET /api/rooms ---------------+
                                                 --> POST /api/chat --> assistant (Claude + tools)
```
Stack: Python 3.12, FastAPI, static HTML/JS (no build step), and the Anthropic SDK for the assistant.
Dependencies go in `requirements.txt`. Run with `uvicorn app.main:app --reload`, then open http://localhost:8000.

## Contracts (code against these now; don't wait for each other)
**Signal**, sent from the board bridge or the simulator: `POST /api/signal`
```json
{"room": "Z.1.09", "source": "psoc-e84", "presence": false, "people": 0, "ts": "2026-11-27T17:05:00Z"}
```
`people` is optional (null when the sensor only gives presence). `source` is `"psoc-e84"` or `"sim"`.

**Room**: `GET /api/rooms` returns a list of these:
```json
{"id": "Z.1.09", "capacity": 6, "status": "ghost",
 "booking": {"by": "Group 7", "start": "16:00", "end": "18:00"} ,
 "presence": false, "people": 0, "empty_since": "2026-11-27T16:43:00Z", "source": "psoc-e84"}
```
`status` is one of `free`, `occupied`, `booked` (booked and people present) or `ghost` (booked, but nobody present
for `GHOST_AFTER_S` seconds; use 30 for the demo and 900 in real life).

**Actions**: `POST /api/rooms/{id}/release` releases a ghost booking. `POST /api/rooms/{id}/book` takes
`{"by": "...", "minutes": 60}`.

**Chat**: `POST /api/chat` takes `{"messages": [{"role": "user", "content": "..."}]}` and returns `{"reply": "..."}`.
The assistant calls tools that use the same state: `list_rooms`, `find_free_room(capacity)`,
`explain_room(id)` (why the room has its status, with evidence), and `release_ghost_booking(id)`.

The floor (from the challenge slide): Z.1.08 occupied (24 people), Z.1.09 booked with 0 people (**the board room**),
Z.1.10 free, Z.1.11 occupied, Z.1.12 free. Seed data lives in `app/data/rooms.json`.

## Roles: 4 agents, each owns its files (no merge conflicts)
| Agent | Owns | Delivers |
|---|---|---|
| **A: Board** (Tom + Claude Code, at the Live Lab 17:00–18:00) | `bridge/`, `docs/board.md` | Find out what the Live Lab exposes, get a presence signal off the board, and send it to `/api/signal`. **Screen-record the board session** in case the board is unavailable at demo time. |
| **B: Backend** | `app/main.py`, `app/rooms.py`, `app/data/`, `sim/`, `tests/` | Room state, ghost logic, the endpoints above, `sim/simulate.py` (plays the scenario with fake signals), tests. Push a stub with all endpoints **first** (about 15 min). |
| **C: Assistant** | `app/assistant.py` | A Claude tool-use loop over the room functions, the system prompt, and 3 scripted demo questions that work reliably. Without an API key, use simple rule-based replies. |
| **D: Frontend + demo** | `web/`, `docs/DEMO.md` | A floor map in the slide's style (red = occupied, dashed = ghost, white = free) with a "LIVE from PSOC Edge" badge on Z.1.09, a chat panel, and an event timeline. Also the demo script and the pitch. |

`app/main.py` (owned by B) includes `app/assistant.py`'s router from the start, so C never edits `main.py`.

## Board (agent A) decision tree for the 17:00 slot
1. **First 10 minutes:** list what the Live Lab offers (preloaded demos, terminal, flashing, camera feed,
   virtual buttons or sliders) and write it in `docs/board.md`.
2. Pick the best presence signal, from best to worst:
   1. radar presence or people counting
   2. camera person detection
   3. microphone sound level
   4. a **button press as "check-in"**, or a virtual signal from the lab
3. Get it out of the lab, from best to worst:
   1. Serial lines read by `bridge/serial_bridge.py`
   2. A small JavaScript snippet pasted into the Live Lab page's browser console that forwards new terminal lines
      to `http://localhost:8000/api/signal` (the backend allows CORS)
   3. As a last resort, the operator mirrors the board state with a toggle in our UI while the board video plays
      alongside it ("simulated signals OK").
4. If the lab allows flashing custom firmware, use the board's display as the **door panel**: show
   "Z.1.09 · booked · 0 people for 22 min · press to check in". The button then checks in, which cancels the
   ghost status.
5. Before 18:00, book the **next slot**, so the final end-to-end run and the demo recording happen with the
   board live.

## Timeline (today)
- **16:30–17:00:** B pushes stub endpoints and seed data. C and D build against the contract. A logs in to the
  Live Lab and reads its docs.
- **17:00–18:00:** A works on the board; the others build. B's simulator lets C and D test without the board.
- **18:00–19:00:** Integration: bridge → backend → map and chat. The whole scenario works with the simulator.
- **Next board slot:** end-to-end run with the real board, then record the demo video.
- **Evening and Sunday morning:** polish, README, pitch (problem → assistant → resolved), rehearse.

## Rules for every agent
- **All cross-LLM communication happens on GitHub**: this file, `docs/agents/*.md`, and PR descriptions and comments.
  Start each work chunk with `git pull` and read what changed in `docs/`.
- Follow `AGENTS.md`: work on a branch `<name>/<task>`, open small PRs, never push to `main`, and add no AI
  attribution.
- **Document as you go** in `docs/agents/<agent>.md` (template: `docs/agents/_TEMPLATE.md`). Cover what you
  built, how to run it, decisions, and anything that's open. Keep it short and current.
- When you change a contract above, update this file in the same PR and say so in your doc.
