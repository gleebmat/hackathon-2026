# A Board: Tom + Claude Code
_Last update: 16:30_

## Status
Role claimed. I start on the Live Lab at 17:00 (the board is booked 17:00–18:00).

## What I built
- `docs/PLAN.md`: scenario, architecture, contracts, roles, timeline

## How to run or test it
Not yet.

## Decisions
- Scenario: ghost booking + "find me a room now". The E84 acts as presence sensor and door panel for Z.1.09.
- Cross-LLM communication happens only on GitHub, through these docs and PRs. No Telegram.

## Open / needs from others
- -> B, C, D: claim your role by adding `docs/agents/<letter>-<role>.md` in your first PR.
- -> B: please make `POST /api/signal` accept CORS from any origin, so the browser bridge can post to it.
