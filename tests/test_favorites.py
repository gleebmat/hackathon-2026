from datetime import timedelta

from fastapi.testclient import TestClient

from app import main
from tests.test_api import NOW, app_env, book, room, time_now, user  # noqa: F401  (fixtures and helpers)


def favorites(c):
    return [r["id"] for r in c.get("/api/favorites").json()]


def test_like_and_unlike_a_room(app_env, time_now):
    s = user(1)
    assert favorites(s) == []
    r = s.put("/api/favorites/V.1.03")
    assert r.status_code == 200 and r.json() == {"room_id": "V.1.03", "favorite": True, "likes": 1}
    time_now["t"] = NOW + timedelta(minutes=1)
    s.put("/api/favorites/V.1.08")
    assert s.put("/api/favorites/V.1.03").json()["likes"] == 1          # liking twice changes nothing
    assert favorites(s) == ["V.1.08", "V.1.03"]                          # newest like first, first date kept
    first = s.get("/api/favorites").json()[0]
    assert first["favorite"] is True and first["liked_at"] and first["status"] == "free" and "seats_free" in first
    assert s.delete("/api/favorites/V.1.03").json() == {"room_id": "V.1.03", "favorite": False, "likes": 0}
    assert s.delete("/api/favorites/V.1.03").status_code == 200          # unliking again is fine too
    assert favorites(s) == ["V.1.08"]


def test_favorites_are_per_account_and_kept_after_logout(app_env):
    a, b = user(1), user(2)
    a.put("/api/favorites/V.1.03")
    b.put("/api/favorites/V.1.03")
    b.put("/api/favorites/V.1.04")
    assert favorites(a) == ["V.1.03"] and sorted(favorites(b)) == ["V.1.03", "V.1.04"]
    assert room(a, "V.1.03")["likes"] == 2
    a.post("/api/logout")
    assert favorites(user(1)) == ["V.1.03"]                              # stored in the database, not the session


def test_favorite_flags_on_room_endpoints(app_env):
    s = user(1)
    s.put("/api/favorites/V.1.04")
    flags = {r["id"]: r["favorite"] for r in s.get("/api/rooms").json()}
    assert flags["V.1.04"] is True and not any(v for k, v in flags.items() if k != "V.1.04")
    assert room(s, "V.1.04")["favorite"] is True and room(s, "V.1.03")["favorite"] is False
    anon = TestClient(main.app)                                          # logged out: no flags, likes still public
    assert not any(r["favorite"] for r in anon.get("/api/rooms").json())
    assert room(anon, "V.1.04") | {"favorite": False, "likes": 1} == room(anon, "V.1.04")
    assert [r["id"] for r in s.get("/api/rooms", params={"q": "V.1.04"}).json() if r["favorite"]] == ["V.1.04"]


def test_favorites_need_login_and_a_real_room(app_env):
    anon = TestClient(main.app)
    assert anon.get("/api/favorites").status_code == 401
    assert anon.put("/api/favorites/V.1.03").status_code == 401
    assert anon.delete("/api/favorites/V.1.03").status_code == 401
    s = user(1)
    assert s.put("/api/favorites/X.9.99").status_code == 404
    assert s.delete("/api/favorites/X.9.99").status_code == 404
    assert favorites(s) == []


def test_favorites_dont_change_booking(app_env):
    s, other = user(1), user(2)
    s.put("/api/favorites/V.1.07a")
    assert book(s).status_code == 201                                    # liked rooms book like any other
    assert book(other, mode="full", seats=4, start="2026-11-27T15:00").status_code == 201
    assert room(other, "V.1.07a")["favorite"] is False                   # someone else's like is not mine
    s.delete("/api/favorites/V.1.07a")
    assert len(s.get("/api/bookings/mine").json()) == 1                  # unliking keeps the booking
