"""Offline tests for LiveNoiseFeed, replaying real (avg dB, peak dB) readings recorded from the board on 2026-11-27.
Run: python -m pytest bridge/"""

from bridge.ntfy_feed import LiveNoiseFeed, noise_class

# Lab background with nobody making noise.
QUIET = [(61.5, 74.3), (61.8, 74.1), (61.4, 74.1), (61.7, 74.0), (61.6, 74.5), (61.3, 74.3), (61.1, 74.4),
         (61.2, 73.8), (61.4, 73.9), (61.6, 76.1), (61.4, 74.0), (61.2, 74.1)]
# Talking into the Live Lab microphone stream.
TALKING = [(63.7, 81.2), (63.5, 86.1), (64.0, 84.8), (62.8, 78.6), (64.3, 82.5), (62.7, 81.0)]
# Loud: music or shouting.
LOUD = [(67.7, 90.9), (67.3, 87.3), (67.5, 89.0), (66.7, 88.6)]


def replay(seq, start=1000.0):
    """Feed readings 5 s apart; return the feed and the class after each reading."""
    feed, classes = LiveNoiseFeed(), []
    for i, (avg, peak) in enumerate(seq):
        t = start + 5 * i
        feed.ingest({"room_id": "V.1.07a", "noise_db": avg, "peak_db": peak}, received_at=t)
        classes.append(feed.latest(now=t)["noise_class"])
    return feed, classes


def test_background_is_quiet():
    _, classes = replay(QUIET)
    assert set(classes) == {"quiet"}


def test_talking_is_moderate_or_loud():
    _, classes = replay(QUIET + TALKING)
    assert all(c in ("moderate", "loud") for c in classes[len(QUIET):])


def test_loud_is_loud():
    _, classes = replay(QUIET + TALKING + LOUD)
    assert set(classes[-len(LOUD):]) == {"loud"}


def test_back_to_quiet_after_noise():
    _, classes = replay(QUIET + LOUD + QUIET[:3])
    assert classes[-3:] == ["quiet"] * 3


def test_floor_ignores_noise_bursts():
    feed, _ = replay(QUIET + TALKING + LOUD)
    assert 61.0 <= feed.floor(1) <= 61.6 and 73.5 <= feed.floor(2) <= 74.5


def test_stale_when_bridge_stops():
    feed, _ = replay(QUIET)
    t = 1000.0 + 5 * (len(QUIET) - 1)
    assert feed.latest(now=t + 5)["live"] is True
    assert feed.latest(now=t + 60)["live"] is False


def test_other_rooms_ignored():
    feed = LiveNoiseFeed()
    feed.ingest({"room_id": "V.0.01", "noise_db": 80})
    assert feed.latest() is None


def test_classes():
    assert [noise_class(x) for x in (35, 45, 70)] == ["quiet", "moderate", "loud"]
