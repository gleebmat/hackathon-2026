import json
import sqlite3
import threading
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import booking, campus_sim, clock, db, main

NOW = datetime(2026, 11, 27, 10, 5)


@pytest.fixture
def time_now(monkeypatch):
    current = {"t": NOW}
    monkeypatch.setattr(clock, "now", lambda: current["t"])
    return current


@pytest.fixture
def app_env(tmp_path, monkeypatch, time_now):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MQTT_FEED", "0")
    monkeypatch.delenv("READINGS_TOKEN", raising=False)
    monkeypatch.setenv("SIMULATE", "0")
    monkeypatch.setenv("CAMPUS_SIM", "0")
    monkeypatch.setattr(db, "CAMPUS_JSON", tmp_path / "missing.json")  # use the built-in V floor 1 rooms
    monkeypatch.setattr(booking, "BOARD_ROOM", "V.1.07a")
    with TestClient(main.app):
        yield


def user(n: int) -> TestClient:
    c = TestClient(main.app)
    assert c.post("/api/login", json={"email": f"student{n}@edu.aau.at", "password": "demo"}).status_code == 200
    return c


def book(c, room="V.1.07a", start="2026-11-27T12:00", hours=2, mode="partial", seats=2, purpose="group_study",
         **extra):
    return c.post("/api/bookings", json={"room_id": room, "start": start, "hours": hours, "mode": mode,
                                         "seats": seats, "purpose": purpose, **extra})


def reading(c, room, people=None, noise_db=None):
    body = {"room_id": room, "people": people, "noise_db": noise_db}
    assert c.post("/api/readings", json=body).status_code == 200


def room(c, room_id):
    return c.get(f"/api/rooms/{room_id}").json()


def sensor_until(c, time_now, room_id, people, until):
    """Post a reading every minute up to `until`, like a running sensor."""
    while time_now["t"] < until:
        time_now["t"] = min(time_now["t"] + timedelta(minutes=1), until)
        reading(c, room_id, people=people)


# --- accounts ---

def test_login_and_me(app_env):
    anon = TestClient(main.app)
    assert anon.get("/api/me").status_code == 401
    assert anon.post("/api/login", json={"email": "student1@edu.aau.at", "password": "nope"}).status_code == 401
    assert user(1).get("/api/me").json() == {"email": "student1@edu.aau.at", "name": "Student 1"}


def test_register(app_env):
    c = TestClient(main.app)
    assert c.post("/api/register", json={"email": "a@gmail.com", "password": "pass"}).status_code == 400
    assert c.post("/api/register", json={"email": "@edu.aau.at", "password": "pass"}).status_code == 400
    assert c.post("/api/register", json={"email": "anna@edu.aau.at", "password": "pw"}).status_code == 400
    r = c.post("/api/register", json={"email": " Anna@EDU.aau.at ", "password": "pass", "name": "Anna"})
    assert r.status_code == 201 and c.get("/api/me").json() == {"email": "anna@edu.aau.at", "name": "Anna"}
    assert c.post("/api/register", json={"email": "anna@edu.aau.at", "password": "pass"}).status_code == 409
    c.post("/api/logout")
    assert c.get("/api/me").status_code == 401
    assert c.post("/api/login", json={"email": "anna@edu.aau.at", "password": "pass"}).status_code == 200


def test_session_expires(app_env, time_now):
    c = user(1)
    time_now["t"] = NOW + timedelta(days=8)
    assert c.get("/api/me").status_code == 401


# --- rooms and search ---

def test_rooms_are_floor_one_with_real_numbers(app_env):
    rooms = TestClient(main.app).get("/api/rooms").json()
    assert {r["floor"] for r in rooms} == {1}
    assert room(TestClient(main.app), "V.1.07a")["name"] == "Atrium"
    assert next(r for r in rooms if r["id"] == "V.1.24")["status"] == "closed"
    assert TestClient(main.app).get("/api/rooms/V.9.99").status_code == 404


def test_search_suggestions(app_env):
    c = TestClient(main.app)
    ids = lambda q: [r["id"] for r in c.get("/api/search", params={"q": q}).json()]
    assert ids("V.1.07a") == ["V.1.07a"]
    assert ids("107")[:2] == ["V.1.07", "V.1.07a"]
    assert ids("v 1 07a") == ["V.1.07a"]
    assert ids("atri") == ["V.1.07a"]
    assert "V.1.01" in ids("seminar") and ids("") == [] and ids("zzz") == []
    assert len(ids("V.1")) == 8
    assert set(c.get("/api/search", params={"q": "V.1.0"}).json()[0]) == {"id", "label", "name", "floor", "status",
                                                                          "seats_free"}
    assert [r["id"] for r in c.get("/api/rooms", params={"q": "mediathek"}).json()] == ["V.1.29"]


# --- booking rules ---

def test_full_booking_blocks_others_and_suggests(app_env):
    a, b = user(1), user(2)
    assert book(a, mode="full", seats=5).status_code == 201
    r = book(b, start="2026-11-27T13:00", hours=1)
    assert r.status_code == 409 and r.json()["error"] == "Room is booked exclusively for that time"
    assert 0 < len(r.json()["suggestions"]) <= 3 and "V.1.07a" not in r.json()["suggestions"]
    assert "V.1.24" not in r.json()["suggestions"]  # closed


def test_sharing_respects_capacity(app_env):
    a, b, c = user(1), user(2), user(3)
    assert book(a, seats=8).status_code == 201
    assert book(b, seats=4).status_code == 201  # capacity 12
    r = book(c, seats=1)
    assert r.status_code == 409 and r.json()["error"].startswith("Only 0 seats free")
    assert book(c, mode="full").status_code == 409
    assert book(c, seats=13, start="2026-11-27T16:00").json()["error"] == "Room holds at most 12 people"


def test_daily_limit_and_own_overlap(app_env):
    a = user(1)
    assert book(a, hours=3).status_code == 201
    r = book(a, room="V.1.02", start="2026-11-27T16:00", hours=1.5)
    assert r.status_code == 400 and "1 h left" in r.json()["error"]
    assert book(a, room="V.1.02", start="2026-11-27T13:00", hours=1).status_code == 400
    assert book(a, room="V.1.02", start="2026-11-27T16:00", hours=1).status_code == 201
    assert book(a, room="V.1.02", start="2026-11-28T12:00", hours=4).status_code == 201  # another day


def test_cancelled_hours_are_given_back(app_env):
    a = user(1)
    booking_id = book(a, hours=4).json()["id"]
    assert book(a, room="V.1.02", start="2026-11-27T17:00", hours=1).status_code == 400
    assert a.delete(f"/api/bookings/{booking_id}").status_code == 200
    assert book(a, room="V.1.02", start="2026-11-27T17:00", hours=1).status_code == 201


def test_time_rules(app_env):
    a = user(1)
    assert book(a, start="2026-11-27T12:15").status_code == 400
    assert book(a, start="2026-11-27T23:30", hours=0.5).status_code == 201
    assert book(a, start="2026-11-27T07:30", hours=1).status_code == 400
    assert book(a, start="2026-11-27T09:00", hours=1).status_code == 400  # past
    assert book(a, start="2026-12-31T12:00", hours=1).status_code == 400  # too far ahead
    assert book(a, hours=4.5).status_code == 400
    assert book(a, hours=1.25).status_code == 400
    assert book(a, start="2026-11-27T10:00", hours=1).status_code == 201  # the current slot is fine


def test_time_with_zone_is_converted(app_env):
    r = book(user(1), start="2026-11-27T11:00:00Z", hours=1)  # 12:00 in Klagenfurt
    assert r.status_code == 201 and r.json()["start"] == "2026-11-27T12:00"


def test_purpose_rules(app_env):
    a, b = user(1), user(2)
    assert book(a, purpose="event", mode="partial").status_code == 400
    assert book(a, purpose="custom").json()["error"] == "Describe the purpose"
    assert book(a, purpose="custom", custom_purpose="Chess club").json()["custom_purpose"] == "Chess club"
    assert book(b, purpose="party").status_code == 400


def test_quiet_and_loud_dont_mix(app_env):
    a, b = user(1), user(2)
    assert book(a, purpose="quiet_study").status_code == 201
    r = book(b, purpose="gaming")
    assert r.status_code == 409 and "Quiet and loud" in r.json()["error"]
    assert book(b, purpose="group_study").status_code == 201


def test_quiet_study_refused_in_noisy_room(app_env):
    a, b = user(1), user(2)
    book(a, room="V.1.02", start="2026-11-27T10:00", purpose="meeting")
    reading(a, "V.1.02", people=3, noise_db=55)
    r = book(b, room="V.1.02", start="2026-11-27T10:00", purpose="quiet_study")
    assert r.status_code == 409 and "too noisy" in r.json()["error"]


def test_bad_input_gives_400_with_error(app_env):
    a = user(1)
    r = a.post("/api/bookings", json={"room_id": "V.1.07a"})
    assert r.status_code == 400 and r.json()["error"].startswith("start")
    assert book(a, seats=0).status_code == 400
    assert book(a, room="V.9.99").status_code == 404
    assert TestClient(main.app).post("/api/bookings", json={}).status_code in (400, 401)


def test_availability_slots(app_env):
    a = user(1)
    book(a, start="2026-11-27T12:00", hours=1, seats=3)
    slots = a.get("/api/rooms/V.1.07a/availability").json()["slots"]
    assert len(slots) == 48 and slots[0]["status"] == "past"
    noon = next(s for s in slots if s["start"] == "12:00")
    assert noon == {"start": "12:00", "end": "12:30", "status": "partial", "seats_free": 9, "shareable": True,
                    "noise": "moderate"}
    assert next(s for s in slots if s["start"] == "13:00")["status"] == "free"
    closed = a.get("/api/rooms/V.1.24/availability", params={"date": "2026-11-28"}).json()["slots"]
    assert {s["status"] for s in closed} == {"closed"}


def test_cancel_only_own(app_env):
    a, b = user(1), user(2)
    booking_id = book(a).json()["id"]
    assert b.delete(f"/api/bookings/{booking_id}").status_code == 404
    assert a.delete(f"/api/bookings/{booking_id}").status_code == 200
    assert a.delete(f"/api/bookings/{booking_id}").status_code == 404
    assert a.get("/api/bookings/mine").json()[0]["status"] == "cancelled"


def test_suggest_endpoint(app_env):
    c = TestClient(main.app)
    quiet = c.get("/api/suggest", params={"hours": 1, "mode": "partial", "seats": 2, "purpose": "quiet_study",
                                          "start": "2026-11-27T12:00"}).json()
    assert quiet and all(r["status"] != "closed" for r in quiet)
    fit = c.get("/api/suggest", params={"hours": 1, "mode": "full", "seats": 7, "start": "2026-11-27T12:00"}).json()
    assert fit[0]["id"] == "V.1.12"  # capacity 8 is the tightest fit
    assert c.get("/api/suggest", params={"hours": 1, "mode": "full", "seats": 1,
                                         "start": "2026-11-27T09:00"}).status_code == 400


# --- ghost bookings ---

def test_ghost_booking_released_after_10_min(app_env, time_now):
    a = user(1)
    booking_id = book(a, room="V.1.03", start="2026-11-27T10:00", hours=2).json()["id"]
    reading(a, "V.1.03", people=0, noise_db=34)  # 10:05, booking started 10:00
    state = room(a, "V.1.03")
    assert state["ghost_release_at"] is None
    time_now["t"] += timedelta(minutes=1)
    reading(a, "V.1.03", people=0)
    assert room(a, "V.1.03")["status"] == "ghost"
    assert a.get("/api/bookings/mine").json()[0]["ghost_release_at"] == "2026-11-27T10:15:00"
    sensor_until(a, time_now, "V.1.03", 0, datetime(2026, 11, 27, 10, 14))
    assert room(a, "V.1.03")["status"] == "ghost"
    sensor_until(a, time_now, "V.1.03", 0, datetime(2026, 11, 27, 10, 15))
    state = room(a, "V.1.03")
    assert state["status"] == "free" and state["bookings_today"] == []
    mine = a.get("/api/bookings/mine").json()[0]
    assert mine["id"] == booking_id and mine["status"] == "released"
    assert book(user(2), room="V.1.03", start="2026-11-27T10:00", mode="full").status_code == 201  # slot is free


def test_present_booking_is_kept(app_env, time_now):
    a = user(1)
    book(a, room="V.1.03", start="2026-11-27T10:00", hours=2)
    reading(a, "V.1.03", people=2)
    sensor_until(a, time_now, "V.1.03", 2, NOW + timedelta(minutes=30))
    mine = a.get("/api/bookings/mine").json()[0]
    assert mine["status"] == "active" and mine["checked_in"] and mine["ghost_release_at"] is None


def test_room_empty_mid_booking_starts_timer(app_env, time_now):
    a = user(1)
    book(a, room="V.1.03", start="2026-11-27T10:00", hours=2)
    sensor_until(a, time_now, "V.1.03", 2, datetime(2026, 11, 27, 10, 29))
    sensor_until(a, time_now, "V.1.03", 0, datetime(2026, 11, 27, 10, 30))  # everyone left at 10:30
    assert room(a, "V.1.03")["ghost_release_at"] is None
    sensor_until(a, time_now, "V.1.03", 0, datetime(2026, 11, 27, 10, 35))
    sensor_until(a, time_now, "V.1.03", 1, datetime(2026, 11, 27, 10, 50))  # back in time: timer stops
    assert a.get("/api/bookings/mine").json()[0]["status"] == "active"
    sensor_until(a, time_now, "V.1.03", 0, datetime(2026, 11, 27, 11, 0))  # left again at 10:51, released 11:01
    assert a.get("/api/bookings/mine").json()[0]["status"] == "active"
    sensor_until(a, time_now, "V.1.03", 0, datetime(2026, 11, 27, 11, 1))
    assert a.get("/api/bookings/mine").json()[0]["status"] == "released"


def test_stale_sensor_never_releases(app_env, time_now):
    a = user(1)
    book(a, room="V.1.03", start="2026-11-27T10:00", hours=2)
    reading(a, "V.1.03", people=0)
    time_now["t"] = NOW + timedelta(minutes=20)  # no readings for 20 min: sensor offline
    assert a.get("/api/bookings/mine").json()[0]["status"] == "active"
    assert room(a, "V.1.03")["status"] == "partial"


def test_noise_only_reading_keeps_people(app_env):
    a = user(1)
    reading(a, "V.1.03", people=3)
    reading(a, "V.1.03", noise_db=52)
    state = room(a, "V.1.03")
    assert state["people"] == 3 and state["noise_class"] == "moderate" and state["status"] == "partial"
    assert a.post("/api/readings", json={"room_id": "V.1.03"}).status_code == 400


def test_readings_token(app_env, monkeypatch):
    monkeypatch.setenv("READINGS_TOKEN", "secret")
    c = TestClient(main.app)
    assert c.post("/api/readings", json={"room_id": "V.1.03", "people": 1}).status_code == 403
    assert c.post("/api/readings", json={"room_id": "V.1.03", "people": 1},
                  headers={"X-Token": "secret"}).status_code == 200


# --- calendar and ratings ---

def test_calendar_has_every_room_in_one_call(app_env):
    a = user(1)
    book(a, start="2026-11-27T12:00", hours=1, seats=3)
    cal = a.get("/api/calendar").json()
    assert cal["date"] == "2026-11-27" and set(cal["rooms"]) == {r["id"] for r in a.get("/api/rooms").json()}
    room_cal = cal["rooms"]["V.1.07a"]
    assert room_cal["slots"] == a.get("/api/rooms/V.1.07a/availability").json()["slots"]
    assert room_cal["free_hours"] == 14.0  # 10:00-24:00 still bookable (shared at 12:00 still counts)
    assert cal["rooms"]["V.1.24"]["free_hours"] == 0  # closed
    assert a.get("/api/calendar", params={"date": "2026-11-28"}).json()["rooms"]["V.1.07a"]["free_hours"] == 24.0
    assert a.get("/api/calendar", params={"date": "bad"}).status_code == 400


def test_ratings_only_after_using_the_room(app_env, time_now):
    a, b = user(1), user(2)
    assert a.post("/api/rooms/V.1.03/rating", json={"stars": 5}).status_code == 403  # never booked
    book(a, room="V.1.03", start="2026-11-27T11:00", hours=1)
    assert a.post("/api/rooms/V.1.03/rating", json={"stars": 5}).status_code == 403  # not started yet
    time_now["t"] = datetime(2026, 11, 27, 11, 0)
    assert a.post("/api/rooms/V.1.03/rating", json={"stars": 6}).status_code == 400
    r = a.post("/api/rooms/V.1.03/rating", json={"stars": 4})
    assert r.status_code == 200 and r.json() == {"room_id": "V.1.03", "rating": 4.0, "votes": 1, "my_rating": 4}
    assert a.post("/api/rooms/V.1.03/rating", json={"stars": 2}).json()["votes"] == 1  # changing it, not a 2nd vote
    book(b, room="V.1.03", start="2026-11-27T11:00", hours=1)
    b.post("/api/rooms/V.1.03/rating", json={"stars": 5})
    state = room(a, "V.1.03")
    assert state["rating"] == 3.5 and state["votes"] == 2 and state["my_rating"] == 2 and state["can_rate"]
    assert a.get("/api/bookings/mine").json()[0]["my_rating"] == 2
    assert room(a, "V.1.04")["rating"] is None and not room(a, "V.1.04")["can_rate"]
    assert TestClient(main.app).post("/api/rooms/V.1.03/rating", json={"stars": 3}).status_code == 401


def test_search_finds_map_labels(app_env):
    conn = db.connect()
    conn.execute("UPDATE rooms SET label = 'HS 1' WHERE id = 'V.1.01'")
    conn.close()
    ids = [r["id"] for r in TestClient(main.app).get("/api/search", params={"q": "hs1"}).json()]
    assert ids == ["V.1.01"]


def test_web_files_are_not_cached(app_env):
    r = TestClient(main.app).get("/login.html")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"


# --- board room, campus data, simulation ---

def test_board_room_presence_and_live(app_env):
    c = TestClient(main.app)
    board = room(c, "V.1.07a")
    assert board["board"] and not board["live"] and board["building"] == "V"
    assert not room(c, "V.1.03")["board"]
    r = c.post("/api/readings", json={"room_id": "V.1.07a", "presence": True, "person_ratio": 0.9,
                                      "noise_avg_db": 63.2, "noise_peak_db": 78.5, "noise_db": 47.0})
    assert r.status_code == 200
    board = room(c, "V.1.07a")
    assert board["live"] and board["people"] == 1 and board["sensor"] and board["noise_class"] == "moderate"
    reading(c, "V.1.03", people=2)
    assert not room(c, "V.1.03")["live"]  # only the board room is live
    c.post("/api/readings", json={"room_id": "V.1.07a", "presence": False})
    assert room(c, "V.1.07a")["people"] == 0


def test_board_left_items(app_env):
    c = TestClient(main.app)
    assert room(c, "V.1.07a")["left_items"] == 0
    c.post("/api/readings", json={"room_id": "V.1.07a", "people": 2, "left_items": 0})
    c.post("/api/readings", json={"room_id": "V.1.07a", "people": 0, "left_items": 1})   # people left, a bag stayed
    state = room(c, "V.1.07a")
    assert state["people"] == 0 and state["left_items"] == 1
    c.post("/api/readings", json={"room_id": "V.1.07a", "people": 1, "left_items": 0})   # someone came back for it
    assert room(c, "V.1.07a")["left_items"] == 0
    assert c.post("/api/readings", json={"room_id": "V.1.07a", "left_items": -1}).status_code == 400


def test_rooms_come_from_the_campus_map(tmp_path, monkeypatch, time_now):
    campus = {"buildings": [
        {"id": "Z", "rooms": [
            {"id": "Z.1.04", "floor": 1, "name": "Seminar room", "capacity": 51, "bookable": True},
            {"id": "Z.1.90", "floor": 1, "name": "Office", "capacity": 2, "bookable": False}]},
        {"id": "N", "rooms": [{"id": "N.2.05", "floor": 2, "name": "Seminar room", "capacity": 16,
                               "bookable": True}]}]}
    path = tmp_path / "campus.json"
    path.write_text(json.dumps(campus), encoding="utf-8")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MQTT_FEED", "0")
    monkeypatch.setattr(db, "CAMPUS_JSON", path)
    with TestClient(main.app) as c:
        rooms = {r["id"]: r for r in c.get("/api/rooms").json()}
        assert set(rooms) == {"Z.1.04", "N.2.05"}
        assert rooms["N.2.05"]["floor"] == 2 and rooms["Z.1.04"]["capacity"] == 51
        assert rooms["Z.1.04"]["board"]  # the default board room
        assert [r["id"] for r in c.get("/api/search", params={"q": "104"}).json()] == ["Z.1.04"]


def test_simulation_is_stable_and_safe(app_env, monkeypatch, time_now):
    monkeypatch.setenv("SIMULATE", "1")
    c = TestClient(main.app)
    first = {r["id"]: (r["noise_db"], r["people"]) for r in c.get("/api/rooms").json()}
    assert first == {r["id"]: (r["noise_db"], r["people"]) for r in c.get("/api/rooms").json()}  # same minute
    changed = False
    for minute in range(1, 30):
        time_now["t"] = NOW + timedelta(minutes=minute)
        for r in c.get("/api/rooms").json():
            changed |= (r["noise_db"], r["people"]) != first[r["id"]]
            assert r["status"] != "ghost" and not r["sensor"] and not r["live"]
            assert r["noise_class"] == "quiet" or r["bookings_now"]  # empty rooms never block quiet study
            assert r["people"] <= r["capacity"]
    assert changed
    a = user(1)
    book(a, room="V.1.03", start="2026-11-27T10:30", seats=5, purpose="group_study")
    r = room(a, "V.1.03")
    assert r["people"] in (4, 5) and r["seats_free"] == 24 - 5 and r["noise_class"] == "moderate"


# --- storage ---

def test_data_survives_restart(app_env):
    a = user(1)
    booking_id = book(a).json()["id"]
    with TestClient(main.app):  # runs startup again on the same database file
        assert user(1).get("/api/bookings/mine").json()[0]["id"] == booking_id


def test_old_database_is_upgraded(tmp_path, monkeypatch, time_now):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                            pw_hash TEXT NOT NULL);
        CREATE TABLE sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE rooms (id TEXT PRIMARY KEY, floor INTEGER NOT NULL, name TEXT NOT NULL,
                            capacity INTEGER NOT NULL, closed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE bookings (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, room_id TEXT NOT NULL,
            start TEXT NOT NULL, end TEXT NOT NULL, mode TEXT NOT NULL, seats INTEGER NOT NULL, purpose TEXT NOT NULL,
            custom_purpose TEXT, status TEXT NOT NULL DEFAULT 'active', checked_in_at TEXT, created_at TEXT NOT NULL);
        CREATE TABLE readings (room_id TEXT PRIMARY KEY, noise_db REAL, people INTEGER, at TEXT NOT NULL);
        INSERT INTO rooms VALUES ('V.1.99', 1, 'Old room', 5, 0);
        INSERT INTO readings VALUES ('V.1.99', 40, 1, '2026-11-27T09:00:00');
    """)
    old.close()
    monkeypatch.setenv("DB_PATH", str(path))
    monkeypatch.setenv("MQTT_FEED", "0")
    monkeypatch.setenv("SIMULATE", "0")
    monkeypatch.setattr(db, "CAMPUS_JSON", tmp_path / "missing.json")
    with TestClient(main.app):
        a = user(1)
        reading(a, "V.1.03", people=2)
        assert room(a, "V.1.03")["people"] == 2
        assert a.get("/api/rooms/V.1.99").status_code == 404  # no longer in the room list
        assert book(a).status_code == 201


def test_concurrent_bookings_never_overbook(app_env):
    clients = []
    for i in range(10):
        c = TestClient(main.app)
        c.post("/api/register", json={"email": f"race{i}@edu.aau.at", "password": "pass"})
        clients.append(c)
    codes = []
    barrier = threading.Barrier(len(clients))

    def go(c):
        barrier.wait()
        codes.append(book(c, room="V.1.12", start="2026-11-27T14:00", mode="partial", seats=3).status_code)

    threads = [threading.Thread(target=go, args=(c,)) for c in clients]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [201, 201] + [409] * 8  # capacity 8 fits two groups of 3
    slot = next(s for s in clients[0].get("/api/rooms/V.1.12/availability").json()["slots"] if s["start"] == "14:00")
    assert slot["seats_free"] == 2


def test_booked_vs_present(app_env):
    a = user(1)
    book(a, room="V.1.03", start="2026-11-27T10:00", hours=2, seats=5)
    assert {k: room(a, "V.1.03")[k] for k in ("booked", "present", "counted")} == \
        {"booked": 5, "present": None, "counted": None}        # no sensor yet
    a.post("/api/readings", json={"room_id": "V.1.03", "presence": True})
    r = room(a, "V.1.03")
    assert (r["booked"], r["present"], r["counted"], r["people"]) == (5, 1, False, 1)   # presence model: yes/no only
    a.post("/api/readings", json={"room_id": "V.1.03", "people": 3})
    r = room(a, "V.1.03")
    assert (r["present"], r["counted"]) == (3, True)                                    # a real head count
    a.post("/api/readings", json={"room_id": "V.1.03", "presence": False})
    r = room(a, "V.1.03")
    assert r["present"] == 0 and r["ghost_release_at"] is None


def test_mqtt_reading_is_stored_like_http(app_env):
    assert main.mqtt_reading({"room_id": "V.1.07a", "presence": True, "noise_db": 47.5, "person_score": 0.9,
                              "left_items": 1})
    r = room(TestClient(main.app), "V.1.07a")
    assert (r["present"], r["counted"], r["noise_db"], r["left_items"], r["live"]) == (1, False, 47.5, 1, True)
    assert not main.mqtt_reading({"room_id": "V.9.99", "presence": True})   # unknown room
    assert not main.mqtt_reading({"room_id": "V.1.07a", "people": -3})      # invalid
    assert not main.mqtt_reading({"room_id": "V.1.07a"})                    # nothing measured


def test_board_disconnect_and_recovery_during_demo(app_env, time_now, monkeypatch):
    monkeypatch.setattr(booking, "GHOST_AFTER", timedelta(seconds=30))
    c = user(1)
    rid = booking.BOARD_ROOM
    assert book(c, room=rid, start="2026-11-27T10:00").status_code == 201
    for seconds in (0, 8, 16, 24):
        time_now["t"] = NOW + timedelta(seconds=seconds)
        reading(c, rid, people=0)
    time_now["t"] = NOW + timedelta(seconds=30)
    assert room(c, rid)["status"] == "ghost"  # no camera sample confirmed the deadline
    time_now["t"] = NOW + timedelta(seconds=35)
    assert not room(c, rid)["live"]
    reading(c, rid, noise_db=51)
    assert room(c, rid)["live"] and room(c, rid)["present"] is None
    for seconds in range(36, 67, 2):
        time_now["t"] = NOW + timedelta(seconds=seconds)
        reading(c, rid, people=0)
    assert c.get("/api/bookings/mine").json()[0]["status"] == "released"


def test_last_and_first_overnight_slots(app_env):
    c = user(1)
    assert book(c, start="2026-11-27T23:30", hours=0.5).status_code == 201
    assert book(c, start="2026-11-28T00:00", hours=0.5).status_code == 201
    slots = c.get("/api/rooms/V.1.07a/availability").json()["slots"]
    assert slots[-1]["start"] == "23:30" and slots[-1]["end"] == "24:00"


@pytest.mark.parametrize("arrived_first", [False, True])
def test_recording_grace_and_release(app_env, time_now, monkeypatch, arrived_first):
    monkeypatch.setattr(booking, "GHOST_GRACE", timedelta(seconds=5))
    monkeypatch.setattr(booking, "GHOST_AFTER", timedelta(seconds=15))
    c = user(1)
    rid = booking.BOARD_ROOM
    assert book(c, room=rid, start="2026-11-27T10:00").status_code == 201
    if arrived_first:
        reading(c, rid, people=1)
    for seconds, people, status in [(0, 0, "partial"), (4, 0, "partial"), (5, 0, "ghost"),
                                    (7, 1, "partial"), (8, 0, "partial"), (13, 0, "ghost"),
                                    (22, 0, "ghost"), (23, 0, "free")]:
        time_now["t"] = NOW + timedelta(seconds=seconds)
        reading(c, rid, people=people)
        assert room(c, rid)["status"] == status


def test_whole_room_can_be_booked_while_unbooked_people_are_inside(app_env):
    a = user(1)
    reading(a, "V.1.03", people=2)                       # two people sit there without a booking
    r = book(a, room="V.1.03", start="2026-11-27T10:00", hours=1, mode="full", seats=3)
    assert r.status_code == 201                          # they have no claim: the room can be booked privately


def test_live_badge_follows_the_board_within_seconds(app_env, time_now):
    c = TestClient(main.app)
    rid = booking.BOARD_ROOM
    assert room(c, rid)["live"] is False
    reading(c, rid, noise_db=40)
    assert room(c, rid)["live"] is True
    time_now["t"] = NOW + timedelta(seconds=4)       # board stopped: offline after 3 s
    assert room(c, rid)["live"] is False
    reading(c, rid, noise_db=41)                     # and back at once
    assert room(c, rid)["live"] is True


def test_other_students_keep_the_campus_busy(app_env, monkeypatch, time_now):
    monkeypatch.setenv("SIMULATE", "1")
    monkeypatch.setenv("CAMPUS_SIM", "1")
    monkeypatch.setattr(campus_sim, "_last_tick", None)
    c = TestClient(main.app)
    rooms = c.get("/api/rooms").json()
    busy = [r for r in rooms if r["bookings_now"]]
    assert busy and not any(r["board"] for r in busy)         # the board room is only booked by real people
    assert all(r["people"] <= r["capacity"] for r in rooms)
    later = [s for r in c.get("/api/calendar").json()["rooms"].values() for s in r["slots"] if s["status"] != "free"]
    assert later                                               # and some rooms are taken later today
    assert c.post("/api/login", json={"email": campus_sim.EMAIL, "password": "!"}).status_code == 401


def test_walk_ins_dont_block_a_whole_room_booking(app_env):
    a = user(1)
    reading(a, "V.1.07a", people=3)   # three people sitting in the board room without a booking
    cap = room(a, "V.1.07a")["capacity"]
    slots = a.get("/api/rooms/V.1.07a/availability", params={"date": "2026-11-27"}).json()["slots"]
    now_slot = next(s for s in slots if s["start"] == "10:00")
    assert now_slot["status"] == "free" and now_slot["seats_free"] == cap - 3   # sharers see 3 seats taken
    assert book(a, start="2026-11-27T10:00", hours=1, mode="full", seats=2, purpose="meeting").status_code == 201


def test_only_rooms_under_55_seats_can_be_booked(app_env, monkeypatch):
    a = user(1)
    rooms = a.get("/api/rooms").json()
    big = max(rooms, key=lambda r: r["capacity"])
    small = min(rooms, key=lambda r: r["capacity"])
    assert booking.BOOKABLE_BELOW == 55
    monkeypatch.setattr(booking, "BOOKABLE_BELOW", big["capacity"])   # the biggest built-in room plays a lecture hall
    assert not room(a, big["id"])["bookable"] and room(a, small["id"])["bookable"]
    r = book(a, room=big["id"])
    assert r.status_code == 409 and "fewer than" in r.json()["error"]
    slots = a.get(f"/api/rooms/{big['id']}/availability", params={"date": "2026-11-28"}).json()["slots"]
    assert {s["status"] for s in slots} == {"closed"}
    suggested = a.get("/api/suggest", params={"hours": 1, "mode": "partial", "seats": 1, "purpose": "group_study",
                                              "start": "2026-11-28T10:00"}).json()
    assert big["id"] not in [r["id"] for r in suggested]
    assert book(a, room=small["id"], seats=1).status_code == 201
