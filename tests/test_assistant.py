from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import assistant, main
from tests.test_api import NOW, app_env, book, time_now, user  # noqa: F401  (fixtures and helpers)

FRIDAY = datetime(2026, 11, 27, 10, 5)


@pytest.mark.parametrize("text, start, hours, seats, purpose, mode", [
    ("quiet room for 3 people tomorrow at 14:00 for 2 hours", "2026-11-28 14:00", 2, 3, "quiet_study", "partial"),
    ("Gruppenraum für 5 heute um 15 Uhr, 90 Minuten", "2026-11-27 15:00", 1.5, 5, "group_study", "partial"),
    ("meeting now for 4, just us", "2026-11-27 10:00", 1, 4, "meeting", "full"),
    ("Brettspiele in Z heute Abend für 3 Std", "2026-11-27 18:00", 3, 1, "board_games", "partial"),
    ("I need to study alone", "2026-11-27 10:00", 1, 1, "quiet_study", "partial"),
    ("zu viert lernen morgen nachmittag", "2026-11-28 14:00", 1, 4, "group_study", "partial"),
    ("party for 20 on monday at 6pm for 3h", "2026-11-30 18:00", 3, 20, "event", "full"),
    ("room for 2 at 3", "2026-11-27 15:00", 1, 2, "group_study", "partial"),
    ("für uns allein, 4 personen, 2 std", "2026-11-27 10:00", 2, 4, "group_study", "full"),
    ("quiet room 14:45 for 6 hours", "2026-11-27 14:30", 4, 1, "quiet_study", "partial"),   # rounded, capped
])
def test_requests_are_understood(text, start, hours, seats, purpose, mode):
    want = assistant.parse(text, FRIDAY)
    assert f"{want['start']:%Y-%m-%d %H:%M}" == start
    assert (want["hours"], want["seats"], want["purpose"], want["mode"]) == (hours, seats, purpose, mode)


def test_building_filter_and_nonsense():
    assert assistant.parse("board games in Z", FRIDAY)["building"] == "Z"
    want = assistant.parse("hello?", FRIDAY)        # nothing recognised: a sensible default, nothing claimed as given
    assert want["given"] == [] and want["seats"] == 1


def test_assistant_api_suggests_bookable_rooms(app_env):
    c = TestClient(main.app)
    res = c.get("/api/assistant", params={"q": "group study for 4 tomorrow at 10:00 for 2h"}).json()
    assert res["problem"] is None and 1 <= len(res["rooms"]) <= 3
    assert res["understood"] == {**res["understood"], "date": "2026-11-28", "time": "10:00", "hours": 2.0, "seats": 4}
    s = user(1)                                      # the first suggestion can really be booked
    r = book(s, room=res["rooms"][0]["id"], start="2026-11-28T10:00", hours=2, mode="partial", seats=4)
    assert r.status_code == 201
    assert c.get("/api/assistant", params={"q": "room at 08:00"}).json()["problem"] == "past"
    assert c.get("/api/assistant", params={"q": "room in 3 weeks on friday"}).status_code == 200
    assert c.get("/api/assistant", params={"q": ""}).status_code == 400
