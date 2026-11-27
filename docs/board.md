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

## Reading format (for B: Backend)
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
- The lab is constantly noisy (fans), so the **ambient level reads about 61.5 dB** (peak about 74) with the
  made-up formula. **B: subtract an ambient offset when displaying**, e.g. `shown_db = max(30, noise_db - 26)`, so
  that a quiet lab shows about 35 dB and extra sound pushes it up.
- To make noise during the demo, use the Live Lab's "Voice Command via Microphone" (it streams our microphone to
  the board).
- Typing into the remote VS Code sometimes lands in the editor, and Ctrl+Z gets dropped. Recover with
  File → Revert File. Keep the bridge's terminal open; closing it stops the feed.
