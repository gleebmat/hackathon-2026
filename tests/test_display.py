import base64
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import display, main
from tests.test_api import NOW, app_env, book, reading, room, sensor_until, time_now, user  # noqa: F401

ROOM = "V.1.03"
TOKEN = {"X-Display-Token": display.TOKEN}


@pytest.fixture(autouse=True)
def clean_display():
    for state in (display.sounds, display.selfies, display.frames, display.board_seen):
        state.clear()


def act(path, method="post", token=TOKEN, **body):
    return getattr(TestClient(main.app), method)(f"/api/display/{ROOM}/{path}", headers=token,
                                                 **({"json": body} if body else {}))


def test_display_state_and_booking_qr(app_env, monkeypatch):
    c = TestClient(main.app)
    state = c.get(f"/api/display/{ROOM}").json()
    assert state["booking_url"] == f"http://testserver/?room={ROOM}" and state["board_online"] is False
    assert state["sound"] == {"kind": "off", "volume": 50} and "rain" in state["sounds"] and state["emergency"] is None
    monkeypatch.setenv("PUBLIC_URL", "https://demo.trycloudflare.com/")
    assert c.get(f"/api/display/{ROOM}").json()["booking_url"] == f"https://demo.trycloudflare.com/?room={ROOM}"
    qr = c.get(f"/api/display/{ROOM}/qr")
    assert qr.headers["content-type"].startswith("image/svg+xml") and qr.text.startswith("<svg")
    assert 'xmlns="http://www.w3.org/2000/svg"' in qr.text                 # loads as an <img> too
    assert c.get("/api/display/X.9.99").status_code == 404


def test_actions_need_the_display_token(app_env):
    for path, body in [("sound", {"kind": "rain"}), ("break", {"minutes": 10}), ("selfie", {}),
                       ("emergency", {"confirm": True})]:
        assert act(path, token={}, **body).status_code == 403
        assert act(path, token={"X-Display-Token": "guess"}, **body).status_code == 403
    assert act("break", method="delete", token={}).status_code == 403


def test_soundscape(app_env):
    assert act("sound", kind="rain", volume=30).json() == {"kind": "rain", "volume": 30}
    assert room(TestClient(main.app), ROOM)["sound"] == "rain"
    assert act("sound", kind="disco").status_code == 400
    assert act("sound", kind="ocean", volume=101).status_code == 400
    act("sound", kind="off")
    assert room(TestClient(main.app), ROOM)["sound"] == "off"


def test_break_keeps_the_booking_while_the_room_is_empty(app_env, time_now):
    assert act("break", minutes=10).status_code == 409                  # nobody booked right now
    a = user(1)
    book(a, room=ROOM, start="2026-11-27T10:00", hours=2)
    assert act("break", minutes=3).status_code == 400 and act("break", minutes=31).status_code == 400
    assert act("break", minutes=20).json()["break_until"] == "2026-11-27T10:25:00"
    assert room(a, ROOM)["break_until"] == "2026-11-27T10:25:00"
    assert a.get("/api/bookings/mine").json()[0]["break_until"] == "2026-11-27T10:25:00"
    # empty for 20 minutes: without the break this booking would be released at 10:15
    sensor_until(a, time_now, ROOM, 0, datetime(2026, 11, 27, 10, 25))
    state = room(a, ROOM)
    assert state["status"] != "ghost" and len(state["bookings_today"]) == 1
    sensor_until(a, time_now, ROOM, 0, datetime(2026, 11, 27, 10, 26))
    assert room(a, ROOM)["break_until"] is None and room(a, ROOM)["status"] == "ghost"   # the timer starts again
    sensor_until(a, time_now, ROOM, 0, datetime(2026, 11, 27, 10, 35))
    assert a.get("/api/bookings/mine").json()[0]["status"] == "released"


def test_break_can_end_early(app_env, time_now):
    a = user(1)
    book(a, room=ROOM, start="2026-11-27T10:00", hours=2)
    act("break", minutes=30)
    time_now["t"] += timedelta(minutes=5)
    assert act("break", method="delete").json()["break_until"] is None
    assert room(a, ROOM)["break_until"] is None


def test_selfie_from_the_board_camera(app_env, time_now):
    assert act("selfie").status_code == 409                             # camera not live
    display.camera_frame(ROOM, b"\xff\xd8jpeg")
    r = act("selfie").json()
    assert r["url"].startswith("http://testserver/api/selfies/") and r["qr_svg"].startswith("<svg")
    assert r["expires_at"] == "2026-11-27T10:15:00"
    c = TestClient(main.app)
    path = r["url"].removeprefix("http://testserver")
    got = c.get(path)
    assert got.content == b"\xff\xd8jpeg" and got.headers["content-type"] == "image/jpeg"
    time_now["t"] += timedelta(minutes=10)
    assert c.get(path).status_code == 404                               # gone after 10 minutes
    assert c.get("/api/selfies/nope").status_code == 404


def test_selfie_from_the_display_webcam(app_env):
    photo = b"\xff\xd8webcam"
    r = act("selfie", image=base64.b64encode(photo).decode()).json()   # works without a live board camera
    got = TestClient(main.app).get(r["url"].removeprefix("http://testserver"))
    assert got.content == photo
    assert act("selfie", image="not base64!").status_code == 400
    assert act("selfie", image=base64.b64encode(b"GIF89a").decode()).status_code == 400


def test_emergency(app_env):
    assert act("emergency").status_code == 400                          # "Are you sure?" not confirmed
    assert act("emergency", confirm=False).status_code == 400
    first = act("emergency", confirm=True).json()
    assert first["room_id"] == ROOM and first["resolved_at"] is None
    assert act("emergency", confirm=True).json()["id"] == first["id"]  # pressing again: same alarm
    anon = TestClient(main.app)
    assert room(anon, ROOM)["emergency"] is True
    assert anon.get(f"/api/display/{ROOM}").json()["emergency"]["id"] == first["id"]
    assert anon.get("/api/emergencies").status_code == 401
    staff = user(2)
    assert [e["id"] for e in staff.get("/api/emergencies").json()] == [first["id"]]
    assert staff.post(f"/api/emergencies/{first['id']}/resolve").json()["resolved_at"]
    assert staff.post(f"/api/emergencies/{first['id']}/resolve").status_code == 404
    assert room(anon, ROOM)["emergency"] is False and staff.get("/api/emergencies").json() == []


def test_board_with_display_is_online(app_env):
    c = TestClient(main.app)
    reading(c, ROOM, noise_db=40)
    assert c.get(f"/api/display/{ROOM}").json()["board_online"] is False
    assert c.post("/api/readings", json={"room_id": ROOM, "noise_db": 40, "display": True}).status_code == 200
    assert c.get(f"/api/display/{ROOM}").json()["board_online"] is True
