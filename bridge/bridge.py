"""PSOC Edge E84 -> backend readings. Runs on the Live Lab PC that the board's KitProg3 UART is attached to.

Usage:
    python bridge.py COM3 https://<tunnel>.trycloudflare.com <token>   # direct to the backend (preferred)
    python bridge.py COM3                                               # fallback: publish to ntfy.sh

Understands every firmware we use (it just parses whatever lines arrive):
- noise firmware (mtb-example-psoc-edge-pdm-pcm): one bar of '-' per audio frame, length ~ volume
- presence firmware (bridge/firmware/inference_task.c): "PRESENCE <0|1> <person_frames>/<frames>" once per second
- a future merged firmware: "NOISE <avg_db> <peak_db>" lines (taken as-is)

Every INTERVAL seconds it sends one reading for ROOM (the board room, default Z.1.04; optional 4th argument):
    {"room_id", "presence", "person_ratio", "noise_avg_db", "noise_peak_db"}   raw board values (PLAN contract)
    + "people" (0/1) and "noise_db" (calibrated, quiet ~35 dB)                   fields the backend reads today
Network errors are retried on the next interval; the serial port is reopened if it drops.
"""

import json
import math
import sys
import time
import urllib.request
from collections import deque

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
URL = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else None
TOKEN = sys.argv[3] if len(sys.argv) > 3 else ""
ROOM = sys.argv[4] if len(sys.argv) > 4 else "Z.1.04"  # must match BOARD_ROOM in the backend
INTERVAL = 2 if URL else 5          # ntfy.sh allows ~250 messages/day, so the fallback is slower
NTFY_TOPIC = "aau-hack26-roomv-v107a"


def bars_to_db(dashes: float) -> float:
    """Made-up calibration of the volume bar: silence ~30 dB, speech ~50-60 dB, shouting 70 dB and above."""
    return round(min(95.0, 30.0 + 20.0 * math.log10(1.0 + dashes)), 1)


class Calibrator:
    """The lab is noisy (~61 dB raw), so the shown level is relative to the floor learned over 3 minutes:
    35 + max(4 x (avg - avg_floor), 2 x (peak - peak_floor)). Same rule as bridge/ntfy_feed.py."""

    def __init__(self, window_s=180):
        self.hist, self.window = deque(), window_s

    def __call__(self, avg, peak):
        now = time.monotonic()
        self.hist.append((now, avg, peak))
        while self.hist[0][0] < now - self.window:
            self.hist.popleft()
        floor = lambda i: sorted(h[i] for h in self.hist)[len(self.hist) // 10]
        return round(min(95.0, max(30.0, 35 + max(4 * (avg - floor(1)), 2 * (peak - floor(2))))), 1)


def parse(lines, state):
    for line in lines:
        s = line.strip()
        parts = s.split()
        if s == "" or set(s) <= {"-"}:
            state["bars"].append(s.count("-"))
        elif len(parts) == 3 and parts[0] == "PRESENCE" and "/" in parts[2]:
            hit, total = (int(x) for x in parts[2].split("/"))
            state["presence"].append((hit, total))
        elif len(parts) == 3 and parts[0] == "NOISE":
            state["noise"].append((float(parts[1]), float(parts[2])))


def reading(state, calibrate):
    r = {"room_id": ROOM}
    if state["presence"]:
        hits, total = sum(h for h, _ in state["presence"]), sum(t for _, t in state["presence"])
        ratio = hits / max(total, 1)
        r.update(presence=ratio >= 0.5, person_ratio=round(ratio, 2), people=int(ratio >= 0.5))
    if state["noise"]:
        avg = sum(a for a, _ in state["noise"]) / len(state["noise"])
        peak = max(p for _, p in state["noise"])
    elif state["bars"] and max(state["bars"]) > 0:        # all-zero bars = mic firmware not running
        avg, peak = bars_to_db(sum(state["bars"]) / len(state["bars"])), bars_to_db(max(state["bars"]))
    else:
        avg = None
    if avg is not None:
        r.update(noise_avg_db=round(avg, 1), noise_peak_db=round(peak, 1), noise_db=calibrate(avg, peak))
    return r if len(r) > 1 else None


def send(r):
    if URL:
        req = urllib.request.Request(f"{URL}/api/readings", data=json.dumps(r).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Token": TOKEN})
    else:
        req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=json.dumps(r).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError as e:
        return f"network error: {e}"


def open_port():
    while True:
        try:
            return serial.Serial(PORT, 115200, timeout=0.2)
        except serial.SerialException as e:
            print(f"cannot open {PORT} ({e}); retrying in 3 s")
            time.sleep(3)


def main():
    print(f"Reading {PORT}; sending to {URL + '/api/readings' if URL else 'https://ntfy.sh/' + NTFY_TOPIC} "
          f"every {INTERVAL}s")
    ser, buf, calibrate = open_port(), "", Calibrator()
    state, last = {"bars": [], "presence": [], "noise": []}, time.monotonic()
    while True:
        try:
            buf += ser.read(4096).decode(errors="ignore")
        except serial.SerialException as e:
            print(f"serial error ({e}); reopening")
            ser.close()
            ser = open_port()
            continue
        *lines, buf = buf.replace("\r", "\n").split("\n")
        parse(lines, state)
        if time.monotonic() - last >= INTERVAL:
            last = time.monotonic()
            r = reading(state, calibrate)
            state = {"bars": [], "presence": [], "noise": []}
            if r:
                print(r, "->", send(r))


if __name__ == "__main__":
    main()
