"""Offline tests for bridge.py parsing and reading assembly (needs pyserial importable)."""
import sys

sys.argv = ["bridge.py", "COM3", "http://127.0.0.1:9", "t"]
from bridge import bridge as br  # noqa: E402


def fresh():
    return {"bars": [], "presence": [], "noise": []}


def test_presence_lines():
    s = fresh()
    br.parse(["PRESENCE 1 9/10", "PRESENCE 1 10/10"], s)
    r = br.reading(s, br.Calibrator())
    assert r["presence"] is True and r["people"] == 1 and r["person_ratio"] == 0.95
    assert "noise_db" not in r


def test_noise_bars_and_calibration():
    cal, r = br.Calibrator(), None
    for _ in range(20):                       # quiet lab background: about 37 bars
        s = fresh()
        br.parse(["-" * 37] * 30, s)
        r = br.reading(s, cal)
    assert r["noise_avg_db"] > 60 and r["noise_db"] < 40          # raw ~61 dB, shown as quiet
    s = fresh()
    br.parse(["-" * 120] * 30, s)                                  # someone talks loudly
    assert br.reading(s, cal)["noise_db"] >= 60


def test_merged_firmware_noise_line():
    s = fresh()
    br.parse(["NOISE 63.2 78.5", "PRESENCE 0 0/10"], s)
    r = br.reading(s, br.Calibrator())
    assert r["noise_avg_db"] == 63.2 and r["noise_peak_db"] == 78.5 and r["presence"] is False


def test_factory_firmware_sends_nothing():
    s = fresh()
    br.parse(["", "", "Enter your choice:"], s)          # only empty lines, no bars or presence
    assert br.reading(s, br.Calibrator()) is None
