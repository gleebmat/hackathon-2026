"""Other students: simulated bookings so the campus map feels alive (only the board room has a real sensor).

Every SIM_EVERY (2 minutes) a few rooms get booked by "Other students", starting now or within the next hours,
until about TARGET of the open rooms are in use (busier during the day). Bookings end on their own after 0.5-3 h.
They are real bookings (same rules, they block seats and show in the calendar), never in the board room, and only
while SIMULATE and CAMPUS_SIM are on (the default; tests turn them off).
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

from app import booking
from app.booking import ApiError, fmt, slot_start

SIM_EVERY = timedelta(minutes=2)
EMAIL = "campus@edu.aau.at"
_last_tick: datetime | None = None


def target(now: datetime) -> float:
    """Share of open rooms in use at this hour."""
    return 0.45 if 8 <= now.hour < 18 else 0.25 if 18 <= now.hour < 22 else 0.08


def user_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM users WHERE email = ?", (EMAIL,)).fetchone()
    if row:
        return row["id"]
    # "!" is no valid password hash, so nobody can log in as this user
    return conn.execute("INSERT INTO users (email, name, pw_hash) VALUES (?, 'Other students', '!')",
                        (EMAIL,)).lastrowid


def add_booking(conn: sqlite3.Connection, uid: int, room: sqlite3.Row, start: datetime, now: datetime,
                rnd: random.Random) -> bool:
    hours = rnd.choice([0.5, 1, 1, 1.5, 2, 2, 3])
    full = rnd.random() < 0.3
    purpose = rnd.choice(["meeting", "group_study", "quiet_study", "event"] if full
                         else ["quiet_study", "group_study", "group_study", "meeting"])
    cap = room["capacity"]
    seats = rnd.randint(2, max(2, min(cap, 12))) if full else rnd.randint(1, max(1, min(6, cap // 3)))
    mode = "full" if full else "partial"
    try:
        end = booking.validate_times(start, hours, now)
    except ApiError:
        return False
    if booking.room_problem(conn, room, start, end, mode, seats, purpose, now):
        return False
    conn.execute("INSERT INTO bookings (user_id, room_id, start, end, mode, seats, purpose, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (uid, room["id"], fmt(start), fmt(end), mode, seats, purpose,
                                                     now.isoformat()))
    return True


def tick(conn: sqlite3.Connection, now: datetime) -> None:
    global _last_tick
    if not booking.simulating() or os.environ.get("CAMPUS_SIM", "1") == "0" or (_last_tick and now - _last_tick < SIM_EVERY and now >= _last_tick):
        return
    first = _last_tick is None
    _last_tick = now
    uid = user_id(conn)
    rooms = [r for r in booking.listed_rooms(conn) if not r["closed"] and r["id"] != booking.BOARD_ROOM]
    if not rooms:
        return
    in_use = {r["room_id"] for r in conn.execute(
        "SELECT room_id FROM bookings WHERE status = 'active' AND start <= ? AND end > ?", (fmt(now), fmt(now)))}
    missing = int(len(rooms) * target(now)) - len(in_use)
    rnd = random.Random()
    for _ in range(max(0, missing if first else min(3, missing))):   # the first tick fills the campus at once
        add_booking(conn, uid, rnd.choice(rooms), slot_start(now), now, rnd)
    for _ in range(10 if first else 1):                               # and some bookings later today
        add_booking(conn, uid, rnd.choice(rooms), slot_start(now) + booking.SLOT * rnd.randint(1, 8), now, rnd)
