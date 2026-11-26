# CLAUDE.md

Shared instructions for every teammate's Claude Code working in this repo.
Hackathon project: speed matters, but don't break `main`.

## Stack
- Python 3, virtual env in `.venv/` (never commit it).
- Dependencies go in `requirements.txt`. Add a package only when it's really needed, and mention it in the PR.

## Git workflow (several people push to this repo at once)
- Never commit directly to `main`. Start each task with `git pull` on `main`, then `git checkout -b <name>/<short-task>`.
- Make small, focused commits with clear messages.
- Push the branch and open a pull request with `gh pr create`. Keep PRs small so they merge fast.
- Before starting work, `git pull` to get teammates' changes. Resolve conflicts carefully; never force-push to `main`.

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
