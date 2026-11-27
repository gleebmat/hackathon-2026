# LOG: one section per agent

Write only in your own section. Each section has a **Status** line (replace it when it changes), a short
**Done** list, and **Requests** to others (`-> agent: ...`). Keep it short: details belong in PRs.

---

## tom-claude (Backend + Board)
**Status (17:50):** the board is live and tested. Starting on the backend stubs next.

**Done**
- `docs/PLAN.md`: product, contracts and roles.
- Board pipeline: the PSOC Edge E84 runs Infineon's unmodified `mtb-example-psoc-edge-pdm-pcm`, which prints a
  UART volume bar. `bridge/bridge.py` on the lab PC turns it into dB and publishes a reading every 5 s to
  https://ntfy.sh/aau-hack26-roomv-v107a.
- `bridge/ntfy_feed.py`: the backend consumer. It learns the lab's ambient floor, rescales to 35–90 dB, and sets
  `live` to False after 20 s without data. It has 8 tests that replay real board data (`python -m pytest bridge/`).
- Noise test with the Live Lab microphone streaming our voices to the board:

  | Phase | Raw avg / peak dB | Shown |
  |---|---|---|
  | Background | 61.1–61.8 / 73.8–76.1 | 35–39 dB, quiet |
  | Talking | 62.7–64.9 / 78.6–87.9 | about 45–59 dB, moderate |
  | Loud | 66.5–67.7 / 86.3–90.9 | 60 dB and up, loud |

  The reading reacts within one 5 s interval and drops back to quiet within one interval after the noise stops.

**Board reference (Live Lab)**
- **Developer Workspace:** a remote Windows PC with ModusToolbox 3.9, VS Code and Tera Term. It has internet and
  Python 3.12 + pyserial, but no git. The board's UART is COM3. The target is `APP_KIT_PSE84_EVAL_EPC2`.
- **Board Controls:** BTN1, BTN2, Reset, a potentiometer (0–1.8 V), and **Microphone → "Click here to Unmute"**,
  which streams our microphone to the board.
- **Next session** (the lab may be reset). In VS Code, click into the terminal, then:
  1. Run `iwr -useb https://raw.githubusercontent.com/gleebmat/hackathon-2026/main/bridge/setup.ps1 | iex`.
     It creates, builds and flashes the firmware in about 5 min.
  2. Run `python $HOME\bridge.py COM3` and keep that terminal open.
- **Gotchas:**
  - Typing into the remote PC drops characters and garbles long strings and double quotes. Type short chunks in
    single quotes.
  - Click in the terminal first: typing that lands in the editor has to be undone with File → Revert File.
  - Switching to "Application Demos" reflashes the factory firmware.

**Requests**
- -> Tom: book the next board slot for the final run and the demo recording.

---

## claude-2 (3D model)
**Status:** not started.

---

## claude-3 (Website UI)
**Status:** not started.

---

## gemini (Data, simulation, demo)
**Status:** not started.
