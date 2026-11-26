# hackathon-2026

This project is being built for a hackathon.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

## Graphify (code knowledge graph, saves AI tokens)

Install once on your machine, then run the setup inside this repo:

```bash
pip install graphifyy          # or: uv tool install graphifyy
graphify install --platform claude
graphify claude install        # adds Claude hooks to your local .claude/settings.json
graphify hook install          # keeps the graph updated after each commit
```

Restart Claude Code afterwards. The graph lives in `graphify-out/`.
