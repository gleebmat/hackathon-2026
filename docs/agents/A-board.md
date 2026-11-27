# A Board: Tom + Claude Code
_Last update: 17:35_

## Status
LIVE and tested. The board microphone sends real noise readings for V.1.07a. `bridge/ntfy_feed.py` turns them into
quiet/moderate/loud and was validated on real data (quiet, talking, loud).

## What I did (chronological)
1. Wrote `docs/PLAN.md` v1, then v2 (building V booking site, 3D view, noise detector, roles A to D).
2. Explored the Infineon Live Lab: demos, the Developer Workspace remote PC, board controls, mic streaming
   (findings in `docs/board.md`).
3. Found that Infineon's `mtb-example-psoc-edge-pdm-pcm` already prints a volume bar over UART, so we need **no
   firmware changes**.
4. `bridge/setup.ps1`: creates the project, builds it and flashes the board on the lab PC. The first run failed
   on `CY_TOOLS_PATHS`; I fixed it, then built and flashed successfully (74,872 bytes verified).
5. `bridge/bridge.py`: UART volume bars become a dB reading, published every 5 s to
   https://ntfy.sh/aau-hack26-roomv-v107a. This needs no tunnel and no open ports. Verified end to end from my
   laptop.
6. Noise test with the Live Lab microphone stream: raw readings rise clearly with sound (table in
   `docs/board.md`).
7. `bridge/ntfy_feed.py` and its tests: the consumer for the backend. It learns the lab's ambient floor, rescales
   to a 35–90 dB display range, and detects when the feed goes stale. 8 offline tests replay the real recordings,
   and I checked it live. I fixed a clock-skew bug along the way: ntfy's timestamps differ from local time by
   about 2 minutes.

## How to run or test it
- Tests: `python -m pytest bridge/`
- Live check: `python -m bridge.ntfy_feed` prints the latest calibrated reading every 5 s.
- Re-running on the lab PC: see "Next lab session" in `docs/board.md`.

## Decisions
- The board is the live sensor for V.1.07a, and the noise level from its microphone is the core of the demo.
  Other rooms are simulated.
- Transport is ntfy.sh, a public topic with no account. The readings aren't sensitive, and it works behind any
  NAT. The limit is about 1 message per 5 s.
- Calibration happens on the consumer side (`ntfy_feed.py`), so the lab PC never needs re-typing. Typing there
  is unreliable.
- Cross-LLM communication happens only on GitHub.

## Open / needs from others
- -> B: at startup, `from bridge.ntfy_feed import LiveNoiseFeed`, then `feed.start()`. Use `feed.latest()` for
  V.1.07a and fall back to the simulator when `live` is False.
- -> D: show a "LIVE · PSOC Edge E84" badge on V.1.07a when `live` is true.
- -> Tom: book the next board slot for the final end-to-end run and the demo recording.
