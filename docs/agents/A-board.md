# A Board: Tom + Claude Code
_Last update: 16:30_

## Status
Plan v2 (building V, booking, noise). Working on the Live Lab now (17:00–18:00).

## What I built
- `docs/PLAN.md`: scenario, architecture, contracts, roles, timeline

## How to run or test it
Not yet.

## Decisions
- The board is the live sensor and door panel for room V.1.07a: noise in dB from the microphone (must have), presence (nice to have), the display as a door panel (wow factor).
- Cross-LLM communication happens only on GitHub, through these docs and PRs. No Telegram.

## Open / needs from others
- -> B, C, D: claim your role by adding `docs/agents/<letter>-<role>.md` in your first PR.
- -> B: please make `POST /api/readings` accept CORS from any origin, so the browser bridge can post to it.
