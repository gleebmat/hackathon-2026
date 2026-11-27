# Board: PSOC Edge E84 in the Infineon Live Lab

## What the Live Lab offers (checked 2026-11-27, 17:00 slot)
- **Application Demos**: the factory firmware with Carousel, Music Player, Vision Hand Gesture, Vision Face ID,
  Video Player and Rock Paper Scissors. Includes a livestream of the board's display and a camera stream.
- **Developer Workspace**: a remote Windows PC with ModusToolbox 3.9, DEEPCRAFT Studio, VS Code, Tera Term and
  Audacity.
  - It has internet access, Python 3.12 and pyserial 3.5. Git is not installed.
  - The board's UART shows up as COM3 (COM1 is also present). The workspace folder is `~/mtw`.
  - The board target is `APP_KIT_PSE84_EVAL_EPC2`.
- **Remote board controls**: User Button 1 and 2 (single click, 3 s hold, continuous hold), Reset, Boot switch,
  a potentiometer (0–1.8 V), and power cycling.
- **"Voice Command via Microphone"**: the lab can stream *our* computer's microphone to the board, so we can make
  noise in the room remotely during the demo.
- Gotcha: typing into the remote desktop garbles long strings and double quotes. Type in short chunks and use
  single quotes.

## Our setup: real noise level for room V.1.07a
1. Firmware: Infineon's **unmodified** `mtb-example-psoc-edge-pdm-pcm`. It reads the PDM microphone and prints
   one bar of `-` per frame over UART, with the bar length proportional to the volume. The LED lights up above a
   noise threshold, and User Button 1 resets the threshold.
2. On the Live Lab PC, run `iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/tom/board/bridge/setup.ps1 | iex`.
   It creates the project, builds it and flashes the board, and downloads `bridge.py`.
3. Then run `python $HOME\bridge.py COM3`. It averages the bars every 5 s, converts them to made-up dB, and
   publishes to **https://ntfy.sh/aau-hack26-roomv-v107a**.

## For B (Backend): use `bridge/ntfy_feed.py`, not raw ntfy
```python
from bridge.ntfy_feed import LiveNoiseFeed
feed = LiveNoiseFeed(); feed.start()   # at app startup; a background thread that reconnects by itself
r = feed.latest()   # None until the first reading, otherwise:
# {"room_id": "V.1.07a", "noise_db": 52.4, "noise_class": "moderate", "live": True, "age_s": 2.1,
#  "raw_db": 63.5, "peak_db": 86.1, "floor_db": 61.4, "peak_floor_db": 74.3, "source": "psoc-e84"}
```
- Use `noise_db` and `noise_class` (quiet below 40, moderate 40–60, loud above 60) for room V.1.07a.
- If `live` is False (no reading for 20 s, i.e. the bridge or the lab session stopped), **fall back to the
  simulator** for V.1.07a and stop showing the "LIVE" badge.
- Standard library only, so there are no new dependencies. Tests: `python -m pytest bridge/` (8 tests,
  replaying real board data).

## Raw message format (what the bridge publishes)
One JSON message every 5 s, carried in the `message` field of each ntfy event:
```json
{"room_id": "V.1.07a", "noise_db": 41.3, "peak_db": 55.0, "frames": 120, "source": "psoc-e84", "ts": "2026-11-27T16:40:05Z"}
```
Subscribe with `GET https://ntfy.sh/aau-hack26-roomv-v107a/json`, a streaming response with one JSON event per
line. Use events where `event == "message"`, parse their `message` with `json.loads`, and store the result as the
latest reading for V.1.07a. Use `?since=10m` to replay recent readings when the backend starts.
Watch it live in a browser: https://ntfy.sh/aau-hack26-roomv-v107a

Calibration is made up: `dB = 30 + 20·log10(1 + bar_length)`. Silence is about 30 dB, speech is 50–60 dB.

## Status (17:16): live
- The board is flashed with `room_noise` (the pdm-pcm example). `bridge.py` runs on the Live Lab PC on COM3 and
  publishes every 5 s. I verified from outside that readings arrive at ntfy.sh.
- The lab is constantly noisy (fans), so the raw **ambient level is about 61.5 dB** (peak about 74).
  `ntfy_feed.py` learns that floor automatically and rescales it (see below).
- To make noise during the demo, use the Live Lab's "Voice Command via Microphone" (it streams our microphone to
  the board).
- Typing into the remote VS Code sometimes lands in the editor, and Ctrl+Z gets dropped. Recover with
  File → Revert File. Keep the bridge's terminal open; closing it stops the feed.

## Noise test (17:20–17:25, with the Live Lab microphone streaming our voices to the board)
| Phase | Raw avg dB | Raw peak dB | Calibrated by `ntfy_feed` |
|---|---|---|---|
| Lab background, nobody talking | 61.1–61.8 | 73.8–76.1 | 35–39 dB, **quiet** |
| Talking into the stream | 62.7–64.9 | 78.6–87.9 | about 45–59 dB, **moderate** |
| Loud (shouting or music) | 66.5–67.7 | 86.3–90.9 | 60 dB and up, **loud** |

The response follows the sound within one 5 s reading and drops back to quiet within one reading after the
noise stops. Calibration: `35 + max(4 × (avg − avg_floor), 2 × (peak − peak_floor))`, with both floors taken as
the 10th percentile over the last 3 minutes. The Microphone panel is in Developer Workspace → Board Controls
(scroll down): "Click here to Unmute".

## Next lab session (the board and the remote PC may be reset)
1. Developer Workspace → VS Code → click in the terminal → `iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/tom/board/bridge/setup.ps1 | iex`
   (this creates, builds and flashes the firmware in about 5 min; the `CY_TOOLS_PATHS` fix is included).
2. `python $HOMEridge.py COM3` and leave the terminal open.
3. Unmute the Microphone panel and check https://ntfy.sh/aau-hack26-roomv-v107a.
