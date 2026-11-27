"""Live noise feed for room V.1.07a, consumed by the backend.

    from bridge.ntfy_feed import LiveNoiseFeed
    feed = LiveNoiseFeed()
    feed.start()        # background thread; reconnects on its own
    feed.latest()       # -> dict (see below), or None before the first reading

The PSOC Edge E84 sits in a noisy lab, so raw readings have a high, constant floor (about 61.5 dB). This class
learns the floor of both the average and the peak level, as the 10th percentile over the last WINDOW_S seconds.
It reports `noise_db = QUIET_DB + max(AVG_GAIN * (avg - avg_floor), PEAK_GAIN * (peak - peak_floor))`.
Calibrated on real readings from 2026-11-27: lab background reads as quiet (35-39 dB), talking reads as
moderate (about 45-59 dB), and music or shouting near the mic reads as loud (60 dB and up).
When no reading has arrived for STALE_S seconds, `live` is False and the backend should fall back to simulation.
Standard library only.
"""

import json
import threading
import time
import urllib.request
from collections import deque

TOPIC = "aau-hack26-roomv-v107a"
ROOM_ID = "V.1.07a"
WINDOW_S = 180   # ambient floor is learned over this window
STALE_S = 20     # the bridge publishes every 5 s
AVG_GAIN = 4.0   # the average rises 1-6 dB with sound; the peak rises 5-17 dB
PEAK_GAIN = 2.0
QUIET_DB = 35.0


def noise_class(db: float) -> str:
    return "quiet" if db < 40 else "moderate" if db < 60 else "loud"


class LiveNoiseFeed:
    def __init__(self, topic: str = TOPIC, room_id: str = ROOM_ID):
        self.topic, self.room_id = topic, room_id
        self._history: deque[tuple[float, float, float]] = deque()  # (received_at, avg raw dB, peak raw dB)
        self._last: dict | None = None
        self._lock = threading.Lock()

    # --- input ---
    def ingest(self, reading: dict, received_at: float | None = None) -> None:
        if reading.get("room_id") != self.room_id or "noise_db" not in reading:
            return
        now = time.time() if received_at is None else received_at
        with self._lock:
            avg = float(reading["noise_db"])
            self._history.append((now, avg, float(reading.get("peak_db", avg))))
            while self._history and self._history[0][0] < now - WINDOW_S:
                self._history.popleft()
            self._last = {**reading, "received_at": now}

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self._run, daemon=True, name="ntfy-noise-feed")
        t.start()
        return t

    def _run(self) -> None:
        since = "3m"  # replay recent readings so the floor is known right after a restart
        while True:
            try:
                url = f"https://ntfy.sh/{self.topic}/json?since={since}"
                with urllib.request.urlopen(url, timeout=60) as resp:  # ntfy sends keepalives every 45 s
                    for line in resp:
                        event = json.loads(line)
                        if event.get("event") == "message":
                            # Local receive time, not ntfy's timestamp: the two clocks can differ by minutes.
                            self.ingest(json.loads(event["message"]))
                            since = event["id"]
            except (OSError, ValueError):
                time.sleep(3)

    # --- output ---
    def floor(self, which: int = 1) -> float | None:
        """10th percentile of the recent average (which=1) or peak (which=2) levels."""
        with self._lock:
            values = sorted(h[which] for h in self._history)
        return values[len(values) // 10] if values else None

    def latest(self, now: float | None = None) -> dict | None:
        now = time.time() if now is None else now
        with self._lock:
            last = self._last
        if last is None:
            return None
        avg_floor, peak_floor = self.floor(1), self.floor(2)
        peak = float(last.get("peak_db", last["noise_db"]))
        excess = max(AVG_GAIN * (last["noise_db"] - avg_floor), PEAK_GAIN * (peak - peak_floor))
        db = round(min(95.0, max(30.0, QUIET_DB + excess)), 1)
        age = now - last["received_at"]
        return {"room_id": self.room_id, "noise_db": db, "noise_class": noise_class(db),
                "raw_db": last["noise_db"], "peak_db": peak, "floor_db": avg_floor, "peak_floor_db": peak_floor,
                "source": "psoc-e84", "live": age <= STALE_S, "age_s": round(age, 1)}


if __name__ == "__main__":  # quick manual check: python -m bridge.ntfy_feed
    feed = LiveNoiseFeed()
    feed.start()
    while True:
        time.sleep(5)
        print(feed.latest())
