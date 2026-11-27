# AGENTS.md

Shared instructions for every AI coding tool and teammate working in this repo.
Hackathon project: speed matters, but don't break `main`.

## Project status (update when something important lands)
- Project: Smart Campus Room Booking on a 3D AAU campus map (Infineon challenge). **Read `docs/PLAN.md` (spec + your role) and `docs/LOG.md` (status per agent) first; run steps are in `README.md`.**
- Team: Gleb = backend + integration (`app/`), Thomas = board + 3D map (`bridge/`, `web/map3d/`), Martha = frontend (`web/`), Arshia = models (people count, lost items).
- Done and integrated on `main`: final UI (map, always-visible calendar, booking panel under the map, my bookings,
  ratings) + 3D map + backend +
  board bridge. Rooms come from `web/map3d/campus.json`; the board room is **Z.1.04**, every other room is
  simulated.
- Open: Arshia's two models (people count, lost items), the merged noise + presence firmware, and a real-board
  run in the Live Lab (PLAN, "Board (Live Lab)").

## Docs
- Only `docs/PLAN.md`, `docs/LOG.md` and `README.md`. No other Markdown files; log in your own section of `docs/LOG.md`.

## Stack
- Python 3, virtual env in `.venv/` (never commit it).
- Dependencies go in `requirements.txt`. Add a package only when it's really needed, and mention it in the PR.

## Git workflow (several people push to this repo at once)
- Never commit directly to `main`. Start each task with `git pull` on `main`, then `git checkout -b <name>/<short-task>`.
- Make small, focused commits with clear messages.
- Push the branch and open a pull request with `gh pr create`. Keep PRs small so they merge fast.
- Before starting work, `git pull` to get teammates' changes. Resolve conflicts carefully; never force-push to `main`.
- No AI attribution anywhere: no `Co-Authored-By` trailers, no "Generated with ..." lines in commits, PRs or code.

## Code
- Keep it simple and readable. Working demo over perfect architecture.
- Run the code (or its tests, if any) before saying something works.
- Don't leave dead code, debug prints, or commented-out blocks in PRs.

## Secrets
- API keys and tokens go in `.env` (already gitignored), never in code or commits.
- When a new env var is needed, add it with a placeholder value to `.env.example`.

## Keep usage low
- Read only the files you need; don't scan the whole repo for small tasks.
- Keep answers short. No long summaries of what was just done.
- Update "Project status" above only for real milestones, in one or two lines.

## graphify (code knowledge graph in `graphify-out/`)
- If `graphify` is installed, run `graphify query "<question>"` before grepping or reading source files. Use `graphify path "<A>" "<B>"` for relationships, `graphify explain "<concept>"` for a concept, `graphify section "<heading>"` for a Markdown section.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review.
- After modifying code, run `graphify update .` (AST-only, no API cost).
- `graphify-out/graph.json` is rewritten whole on every build; a large diff to it is expected.
