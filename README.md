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
API docs: http://localhost:8000/docs. The map alone: http://localhost:8000/map3d/. Tests: `python -m pytest tests bridge`.

## Demo with the board (XIAO ESP32S3 Sense in Velxio)

1. **Backend** (PowerShell, in this repo): start it with a two-stage recording timer. It subscribes to the board's
   MQTT readings by itself (public broker `broker.hivemq.com`, topic `aau-hack26/rooms/+/readings`).
   ```powershell
   $env:GHOST_GRACE_SECONDS = '5'; $env:GHOST_RELEASE_SECONDS = '15'; uvicorn app.main:app
   ```
2. **Velxio** (https://velxio.dev/editor, Chrome): new project, board **XIAO ESP32S3 Sense**.
   - Files: paste `firmware/xiao_sense/sketch.ino` into `sketch.ino`; add a file `person_model.h` with the content of
     `firmware/xiao_sense/person_model.h`.
   - Libraries (Library Manager): `Chirale_TensorFlowLite` and `PubSubClient`.
   - Under the board click **Camera** and **Mic** (allow them in Chrome), then **Run**. The first compile takes a few
     minutes. The serial monitor shows `MODEL OK`, `WIFI OK` and one `MQTT ... -> sent` line per reading (500 ms target, plus simulator delays).
3. **Show it:** open http://localhost:8000, search `z104`. Z.1.04 shows LIVE, its noise, "Booked for N · Someone is
   here". Book it, then step out of the webcam: the room turns into a ghost booking (violet on the map) and is
   marked Ghost after 5 seconds and released after 15 seconds total of confirmed absence. Leave an object in view when you go: the panel shows "🎒 Something left behind".

Tips: keep the camera view empty after Run until serial prints `Empty-room baseline ready`. Every other
room is simulated. The old Infineon Live Lab path (`bridge/`) still works as a fallback, see `docs/LOG.md`.

## Graphify (code knowledge graph, saves AI tokens)

Install once on your machine, then run the setup inside this repo:

```bash
pip install graphifyy          # or: uv tool install graphifyy
graphify install --platform claude
graphify claude install        # adds Claude hooks to your local .claude/settings.json
graphify hook install          # keeps the graph updated after each commit
```

Restart Claude Code afterwards. The graph lives in `graphify-out/`.
