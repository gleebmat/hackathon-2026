# hackathon-2026

Smart campus room booking for AAU (Infineon challenge): a 3D campus map, live room status, booking with
sharing rules, and one room (`Z.1.04`) wired to a real PSOC Edge E84 board in Infineon's Live Lab.
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

## Demo with the real board (runbook)

1. **Demo laptop, terminal 1** (PowerShell): start the backend with a sensor token and a 1-minute ghost timer.
   ```powershell
   $env:READINGS_TOKEN = 'pick-a-token'; $env:GHOST_RELEASE_MIN = '1'; uvicorn app.main:app
   ```
2. **Demo laptop, terminal 2:** open a public tunnel (install once: `winget install Cloudflare.cloudflared`).
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
   It prints an `https://….trycloudflare.com` URL.
3. **Live Lab:** in Application Demos, enable Webcam Access and unmute the microphone (our laptop's camera and mic
   feed the board). Then in the Developer Workspace, flash the firmware and start the bridge (details: `docs/LOG.md`,
   tom-claude, "Runbook"):
   ```powershell
   iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/main/bridge/setup_person.ps1 | iex
   python $HOME\bridge.py COM3 <tunnel URL> <token>
   ```
4. **Show it:** search `z104` on the site. Z.1.04 shows LIVE, its noise and whether someone is there. Book it,
   then step out of the webcam: the room turns into a ghost booking and is released after 1 minute.

Tips: use headphones (the lab sends its audio back), keep loud moments short, and every other room is simulated.

## Graphify (code knowledge graph, saves AI tokens)

Install once on your machine, then run the setup inside this repo:

```bash
pip install graphifyy          # or: uv tool install graphifyy
graphify install --platform claude
graphify claude install        # adds Claude hooks to your local .claude/settings.json
graphify hook install          # keeps the graph updated after each commit
```

Restart Claude Code afterwards. The graph lives in `graphify-out/`.
