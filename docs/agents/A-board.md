# A Board: Tom + Claude Code
_Last update: 17:16_

## Status
LIVE: the board microphone sends real noise dB for V.1.07a to ntfy.sh every 5 s. Details are in docs/board.md.

## What I built
- `docs/PLAN.md`: scenario, architecture, contracts, roles, timeline
- `bridge/setup.ps1`: creates, builds and flashes the mic example on the Live Lab PC
- `bridge/bridge.py`: reads the UART volume bars, converts them to dB, and publishes to ntfy.sh every 5 s
- `docs/board.md`: what the Live Lab offers, and the reading format for the backend

## How to run or test it
Not yet.

## Decisions
- The board is the live sensor and door panel for room V.1.07a: noise in dB from the microphone (must have), presence (nice to have), the display as a door panel (wow factor).
- Cross-LLM communication happens only on GitHub, through these docs and PRs. No Telegram.

## Open / needs from others
- -> B, C, D: claim your role by adding `docs/agents/<letter>-<role>.md` in your first PR.
- -> B: readings for V.1.07a arrive on https://ntfy.sh/aau-hack26-roomv-v107a/json (format in docs/board.md). Subscribe to that feed instead of waiting for POSTs. Keep `POST /api/readings` for the simulator.
