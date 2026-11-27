"""PSOC Edge E84 -> room noise readings.

Runs on the Live Lab PC that the board's KitProg3 UART is attached to.
Firmware: Infineon's unmodified `mtb-example-psoc-edge-pdm-pcm`, which prints one bar of '-' per audio frame,
with a length proportional to the microphone volume.

Every INTERVAL seconds this script publishes one JSON reading to the public ntfy.sh topic below.
The backend subscribes to https://ntfy.sh/<TOPIC>/json, so no tunnel or open port is needed on either side.

Usage: python bridge.py [COM3]
"""

import json
import math
import sys
import time
import urllib.request

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
TOPIC = "aau-hack26-roomv-v107a"
ROOM = "V.1.07a"
INTERVAL = 5  # ntfy.sh allows roughly one message per 5 s per client on the free tier


def to_db(dashes: float) -> float:
    """Made-up calibration: silence is about 30 dB, normal speech about 55 dB, shouting 70 dB and above."""
    return round(min(95.0, 30.0 + 20.0 * math.log10(1.0 + dashes)), 1)


def publish(reading: dict) -> None:
    req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=json.dumps(reading).encode(), method="POST")
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except OSError as e:
        print("publish failed:", e)


def main() -> None:
    ser = serial.Serial(PORT, 115200, timeout=0.2)
    print(f"Reading {PORT}, publishing to https://ntfy.sh/{TOPIC} every {INTERVAL}s")
    buf, bars, presence, last = "", [], [], time.monotonic()
    while True:
        buf += ser.read(4096).decode(errors="ignore")
        *lines, buf = buf.replace("\r", "\n").split("\n")
        bars += [line.count("-") for line in lines if line.strip() == "" or set(line.strip()) <= {"-"}]
        # Person firmware (bridge/firmware/inference_task.c) prints "PRESENCE <0|1> <person_frames>/<frames>"
        for line in lines:
            parts = line.split()
            if len(parts) == 3 and parts[0] == "PRESENCE" and "/" in parts[2]:
                hit, total = (int(x) for x in parts[2].split("/"))
                presence.append((hit, total))
        if time.monotonic() - last >= INTERVAL:
            last = time.monotonic()
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if presence:
                hits, total = sum(h for h, _ in presence), sum(t for _, t in presence)
                reading = {"room_id": ROOM, "presence": hits * 2 >= total, "person_ratio": round(hits / max(total, 1), 2),
                           "fps": round(total / INTERVAL, 1), "source": "psoc-e84-vision", "ts": ts}
                print(reading)
                publish(reading)
                presence = []
            if not bars or max(bars) == 0:
                # No volume bars: the board isn't running the mic firmware (e.g. the lab switched to its
                # factory demos). Publish nothing, so the backend marks the feed as not live.
                bars = []
                continue
            avg, peak = sum(bars) / len(bars), max(bars)
            reading = {"room_id": ROOM, "noise_db": to_db(avg), "peak_db": to_db(peak), "frames": len(bars),
                       "source": "psoc-e84", "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            print(reading)
            publish(reading)
            bars = []


if __name__ == "__main__":
    main()
