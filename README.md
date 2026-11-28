# hackathon-2026

Smart campus room booking for AAU (Infineon challenge): a 3D campus map, live room status, booking with
sharing rules, and one room (`Z.1.04`) wired to a XIAO ESP32S3 Sense board (camera + microphone, person
model on the board), simulated in Velxio.
Spec and API: `docs/PLAN.md`. Status per teammate: `docs/LOG.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 and log in as `student1@edu.aau.at` / `demo` (also `student2..4`).
API docs: http://localhost:8000/docs. The map alone: http://localhost:8000/map3d/. Tests: `python -m pytest tests`.

- **Port:** any free port works (`uvicorn app.main:app --port 8011` is fine too). The board doesn't talk to the
  port: it publishes to an MQTT broker and the backend subscribes, so only the browser URL changes.
- **Database:** a local SQLite file (`campus.db`, or `DB_PATH`), gitignored. Accounts, sessions, bookings and
  ratings stay there across restarts, pulls and new commits; schema changes are migrated in place
  (`app/db.py: upgrade`). Only the board readings table is rebuilt when its columns change. Every machine has its own
  database, so an account made on Gleb's laptop doesn't exist on yours. The demo accounts are recreated if missing.
  Delete `campus.db` for a clean start.

## The board: XIAO ESP32S3 Sense in Velxio

**What runs on the board** (`firmware/xiao_sense/sketch.ino`, about one reading per second in the simulator):
- **Presence:** Arshia's 96x96 person model (`models/vww_96_int8.tflite`, as a C array in `person_model.h`) with
  TensorFlow Lite Micro. It says yes/no (score 0..1, threshold 0.60, majority of the last 3 frames). It can't count.
- **Noise:** the PDM microphone (RMS mapped to about 30-90 dB).
- **Left items:** a comparison with an empty-room snapshot (details and placement tips below).
- One JSON reading per check goes over MQTT to `broker.hivemq.com:1883`, topic `aau-hack26/rooms/Z.1.04/readings`:
  `{"room_id":"Z.1.04","noise_db":37.2,"presence":true,"person_score":0.91,"left_items":0}`.
  The backend (`app/mqtt_feed.py`) subscribes and stores it like `POST /api/readings`. Readings older than 10 s
  count as "board offline".

**Velxio setup (team account).** Log in at https://velxio.dev with the team's (Gleb's) account and open the project
**TODAREISTODO** (https://velxio.dev/gleebmat/todareistodo). It already has `sketch.ino`, `person_model.h` and the
libraries `Chirale_TensorFlowLite` and `PubSubClient` (Library Manager). GitHub is the master copy: after changing
the sketch here, paste it into Velxio (or the other way round) and save (File > Save project).
1. Start the backend with short demo timers:
   ```powershell
   $env:GHOST_GRACE_SECONDS = '5'; $env:GHOST_RELEASE_SECONDS = '15'; uvicorn app.main:app
   ```
2. In Velxio, under the board, switch on **Camera** (your webcam) and **Mic** (your microphone; when it's off you
   get a 440 Hz test tone), allow both in Chrome, then **Run**. The first compile takes a few minutes; after that
   the build cache makes it fast. The serial monitor shows `CAM OK`, `MODEL OK`, `MIC OK`, `WIFI OK`, then one
   `person=... present=... left=...` line and one `MQTT ... -> sent` line per check.
3. Open http://localhost:8000 and search `z104`. Z.1.04 shows **LIVE**, the noise and "Someone is here". Book it
   and step out of the webcam: after 5 s the booking is marked ghost (violet on the map) and after 15 s it's
   released. Leave an object and step out: the panel shows "🎒 Something left behind".

**Troubleshooting**
- *Compile error "control reaches end of non-void function" or a cut-off sketch:* the paste was truncated (the
  editor is slow with long pastes). Check that `sketch.ino` ends with `loop()`'s closing brace, then paste again.
- *Two boards:* only run the project in one browser tab. Every running tab publishes to the same topic.
- *Website shows the board offline:* the simulation is stopped or WiFi failed; the serial monitor says which.

**Placement: how to get reliable results**
- *People:* the model sees a 96x96 picture of the whole view, so a person must be clearly visible: upper body and
  face, roughly the middle of the frame, not just a shoulder at the edge. Half-visible people at the edge are often
  missed (score below 0.6). Good light helps; a backlit person (window behind) scores low.
- *Left items:* the board compares the frame with a **snapshot of the empty room**. It takes that snapshot by itself
  whenever the view is empty and still for about 3 checks (person score below 0.45, nothing moving), so after Run
  keep the view empty for ~5 s until serial prints `Empty-room baseline ready`. When people were there and leave,
  every change against that snapshot that stays in place for 3 checks counts. So:
  - put the object **inside the view, away from the left, right and top edges** (changes touching those edges are
    treated as a person walking out); the bottom edge (the desk) is fine;
  - the object must be clearly visible in a 96x96 picture: a bottle, a phone or a bag works, a key or a pen is too
    small; it should contrast with what's behind it (a dark bag on a dark chair is hard);
  - when you leave, leave completely and don't move the camera or the chair (a moved chair is a change too; a
    camera nudge of up to 3 px is compensated, and smooth light changes are ignored);
  - remove the object and it goes back to 0; after 5 clean checks the board keeps refreshing its snapshot again.

## Graphify (code knowledge graph, saves AI tokens)

Install once on your machine, then run the setup inside this repo:

```bash
pip install graphifyy          # or: uv tool install graphifyy
graphify install --platform claude
graphify claude install        # adds Claude hooks to your local .claude/settings.json
graphify hook install          # keeps the graph updated after each commit
```

Restart Claude Code afterwards. The graph lives in `graphify-out/`.
