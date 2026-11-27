from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import clock, db, main

NOW = datetime(2026, 11, 27, 10, 5)


@pytest.fixture
def time_now(monkeypatch):
    current = {"t": NOW}
    monkeypatch.setattr(clock, "now", lambda: current["t"])
    return current


@pytest.fixture
def app_env(tmp_path, monkeypatch, time_now):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("NOISE_FEED", "0")
    monkeypatch.setattr(db, "BUILDING_JSON", tmp_path / "missing.json")  # use the built-in floor 1 rooms
    with TestClient(main.app):
        yield


def user(n: int) -> TestClient:
    c = TestClient(main.app)
    assert c.post("/api/login", json={"email": f"student{n}@edu.aau.at", "password": "demo"}).status_code == 200
    return c


def book(c, room="V.1.07a", start="2026-11-27T12:00", hours=2, mode="partial", seats=2, purpose="group_study"):
    return c.post("/api/bookings", json={"room_id": room, "start": start, "hours": hours, "mode": mode,
                                         "seats": seats, "purpose": purpose})


def test_login_and_me(app_env):
    anon = TestClient(main.app)
    assert anon.get("/api/me").status_code == 401
    assert anon.post("/api/login", json={"email": "student1@edu.aau.at", "password": "nope"}).status_code == 401
    assert user(1).get("/api/me").json() == {"email": "student1@edu.aau.at", "name": "Student 1"}


def test_register(app_env):
    c = TestClient(main.app)
    assert c.post("/api/register", json={"email": "a@gmail.com", "password": "pass"}).status_code == 400
    assert c.post("/api/register", json={"email": "anna@edu.aau.at", "password": "pw"}).status_code == 400
    r = c.post("/api/register", json={"email": "Anna@edu.aau.at", "password": "pass", "name": "Anna"})
    assert r.status_code == 201 and c.get("/api/me").json()["email"] == "anna@edu.aau.at"
    assert c.post("/api/register", json={"email": "anna@edu.aau.at", "password": "pass"}).status_code == 409
    c.post("/api/logout")
    assert c.get("/api/me").status_code == 401


def test_rooms_floor_one_and_search(app_env):
    c = TestClient(main.app)
    rooms = c.get("/api/rooms").json()
    assert {r["floor"] for r in rooms} == {1} and any(r["id"] == "V.1.07a" for r in rooms)
    assert [r["id"] for r in c.get("/api/rooms", params={"q": "107a"}).json()] == ["V.1.07a"]
    assert all("quiet" in r["name"].lower() for r in c.get("/api/rooms", params={"q": "quiet"}).json())
    assert next(r for r in rooms if r["id"] == "V.1.11")["status"] == "closed"
    assert c.get("/api/rooms/V.9.99").status_code == 404


def test_full_booking_blocks_others_and_suggests(app_env):
    a, b = user(1), user(2)
    assert book(a, mode="full", seats=5).status_code == 201
    r = book(b, start="2026-11-27T13:00", hours=1)
    assert r.status_code == 409 and r.json()["error"] == "Room is booked exclusively for that time"
    assert 0 < len(r.json()["suggestions"]) <= 3 and "V.1.07a" not in r.json()["suggestions"]


def test_sharing_respects_capacity(app_env):
    a, b, c = user(1), user(2), user(3)
    assert book(a, seats=8).status_code == 201
    assert book(b, seats=4).status_code == 201  # capacity 12
    r = book(c, seats=1)
    assert r.status_code == 409 and r.json()["error"].startswith("Only 0 seats free")
    assert book(c, mode="full").status_code == 409


def test_daily_limit_and_own_overlap(app_env):
    a = user(1)
    assert book(a, hours=3).status_code == 201
    r = book(a, room="V.1.02", start="2026-11-27T16:00", hours=1.5)
    assert r.status_code == 400 and "1 h left" in r.json()["error"]
    assert book(a, room="V.1.02", start="2026-11-27T13:00", hours=1).status_code == 400
    assert book(a, room="V.1.02", start="2026-11-27T16:00", hours=1).status_code == 201


def test_time_rules(app_env):
    a = user(1)
    assert book(a, start="2026-11-27T12:15").status_code == 400
    assert book(a, start="2026-11-27T21:00", hours=2).status_code == 400
    assert book(a, start="2026-11-27T09:00", hours=1).status_code == 400  # past
    assert book(a, start="2026-11-27T10:00", hours=1).status_code == 201  # current slot is fine
    assert book(a, purpose="event", mode="partial").status_code == 400


def test_quiet_and_loud_dont_mix(app_env):
    a, b = user(1), user(2)
    assert book(a, purpose="quiet_study").status_code == 201
    r = book(b, purpose="gaming")
    assert r.status_code == 409 and "Quiet and loud" in r.json()["error"]
    assert book(b, purpose="group_study").status_code == 201


def test_availability_slots(app_env):
    a = user(1)
    book(a, start="2026-11-27T12:00", hours=1, seats=3)
    slots = a.get("/api/rooms/V.1.07a/availability").json()["slots"]
    assert len(slots) == 28 and slots[0]["status"] == "past"
    noon = next(s for s in slots if s["start"] == "12:00")
    assert noon == {"start": "12:00", "end": "12:30", "status": "partial", "seats_free": 9, "shareable": True,
                    "noise": "moderate"}
    assert next(s for s in slots if s["start"] == "13:00")["status"] == "free"


def test_cancel_only_own(app_env):
    a, b = user(1), user(2)
    booking_id = book(a).json()["id"]
    assert b.delete(f"/api/bookings/{booking_id}").status_code == 404
    assert a.delete(f"/api/bookings/{booking_id}").status_code == 200
    assert a.get("/api/bookings/mine").json()[0]["status"] == "cancelled"


def test_ghost_booking_is_released(app_env, time_now):
    a = user(1)
    booking_id = book(a, room="V.1.03", start="2026-11-27T10:00", hours=2).json()["id"]
    a.post("/api/readings", json={"room_id": "V.1.03", "noise_db": 34, "people": 0})
    assert next(r for r in a.get("/api/rooms").json() if r["id"] == "V.1.03")["status"] == "ghost"
    time_now["t"] = NOW + timedelta(minutes=11)  # 10:16
    a.post("/api/readings", json={"room_id": "V.1.03", "noise_db": 34, "people": 0})
    room = a.get("/api/rooms/V.1.03").json()
    assert room["status"] == "free" and room["bookings_today"] == []
    mine = a.get("/api/bookings/mine").json()[0]
    assert mine["id"] == booking_id and mine["status"] == "released"


def test_present_booking_is_kept(app_env, time_now):
    a = user(1)
    book(a, room="V.1.03", start="2026-11-27T10:00", hours=2)
    a.post("/api/readings", json={"room_id": "V.1.03", "noise_db": 48, "people": 2})
    time_now["t"] = NOW + timedelta(minutes=30)
    a.post("/api/readings", json={"room_id": "V.1.03", "noise_db": 40, "people": 0})
    assert a.get("/api/bookings/mine").json()[0]["status"] == "active"


def test_quiet_study_refused_in_noisy_room(app_env):
    a, b = user(1), user(2)
    book(a, room="V.1.02", start="2026-11-27T10:00", purpose="meeting")
    a.post("/api/readings", json={"room_id": "V.1.02", "noise_db": 55, "people": 3})
    r = book(b, room="V.1.02", start="2026-11-27T10:00", purpose="quiet_study")
    assert r.status_code == 409 and "too noisy" in r.json()["error"]


def test_readings_token(app_env, monkeypatch):
    monkeypatch.setenv("READINGS_TOKEN", "secret")
    c = TestClient(main.app)
    assert c.post("/api/readings", json={"room_id": "V.1.03", "people": 1}).status_code == 403
    assert c.post("/api/readings", json={"room_id": "V.1.03", "people": 1},
                  headers={"X-Token": "secret"}).status_code == 200
