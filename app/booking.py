"""Booking rules, live room state, availability, suggestions and ghost-booking release."""

import os
import sqlite3
from datetime import date, datetime, time, timedelta

OPEN, CLOSE = time(8, 0), time(22, 0)
SLOT = timedelta(minutes=30)
MAX_HOURS_PER_DAY = 4.0
GHOST_AFTER = timedelta(minutes=int(os.environ.get("GHOST_RELEASE_MIN", "15")))
SENSOR_STALE = timedelta(minutes=2)

PURPOSE_CLASS = {
    "quiet_study": "quiet",
    "group_study": "moderate", "meeting": "moderate", "custom": "moderate",
    "gaming": "loud", "board_games": "loud", "event": "loud",
}
NOISE_ORDER = ["quiet", "moderate", "loud"]
SIMULATED_DB = {None: 33.0, "quiet": 37.0, "moderate": 50.0, "loud": 68.0}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def noise_class(db: float) -> str:
    return "quiet" if db < 40 else "moderate" if db < 60 else "loud"


def fmt(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")


def slot_start(dt: datetime) -> datetime:
    return dt.replace(minute=dt.minute - dt.minute % 30, second=0, microsecond=0)


def get_room(conn: sqlite3.Connection, room_id: str) -> sqlite3.Row:
    room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room is None:
        raise ApiError(404, f"Unknown room {room_id}")
    return room


def overlapping(conn: sqlite3.Connection, room_id: str, start: datetime, end: datetime) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bookings WHERE room_id = ? AND status = 'active' AND start < ? AND end > ? ORDER BY start",
        (room_id, fmt(end), fmt(start)),
    ).fetchall()


def fresh_reading(conn: sqlite3.Connection, room_id: str, now: datetime) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM readings WHERE room_id = ?", (room_id,)).fetchone()
    if row and datetime.fromisoformat(row["at"]) >= now - SENSOR_STALE:
        return row
    return None


def loudest(bookings: list[sqlite3.Row]) -> str | None:
    classes = [PURPOSE_CLASS[b["purpose"]] for b in bookings]
    return max(classes, key=NOISE_ORDER.index) if classes else None


def booking_out(row: sqlite3.Row, user_id: int | None = None) -> dict:
    start, end = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
    return {"id": row["id"], "room_id": row["room_id"], "start": row["start"], "end": row["end"],
            "hours": (end - start).total_seconds() / 3600, "mode": row["mode"], "seats": row["seats"],
            "purpose": row["purpose"], "custom_purpose": row["custom_purpose"], "status": row["status"],
            "checked_in": row["checked_in_at"] is not None, "mine": row["user_id"] == user_id}


def room_state(conn: sqlite3.Connection, room: sqlite3.Row, now: datetime, live: dict) -> dict:
    """What the room looks like right now: status, noise, people, free seats and current bookings."""
    current = overlapping(conn, room["id"], now, now + timedelta(seconds=1))
    reading = fresh_reading(conn, room["id"], now)
    feed = live.get(room["id"])
    is_live = bool(feed and feed.get("live"))
    if is_live:
        noise_db = feed["noise_db"]
    elif reading and reading["noise_db"] is not None:
        noise_db = reading["noise_db"]
    else:
        noise_db = SIMULATED_DB[loudest(current)]
    sensed = reading is not None and reading["people"] is not None
    booked = sum(b["seats"] for b in current)
    people = reading["people"] if sensed else booked
    exclusive = any(b["mode"] == "full" for b in current)
    seats_free = 0 if exclusive or room["closed"] else max(0, room["capacity"] - max(booked, people))

    if room["closed"]:
        status = "closed"
    elif sensed and people == 0 and any(b["checked_in_at"] is None for b in current):
        status = "ghost"
    elif exclusive or (current and seats_free == 0):
        status = "full"
    elif current or people > 0:
        status = "partial"
    else:
        status = "free"

    return {"id": room["id"], "floor": room["floor"], "name": room["name"], "capacity": room["capacity"],
            "status": status, "noise_db": round(noise_db, 1), "noise_class": noise_class(noise_db),
            "people": people, "seats_free": seats_free, "live": is_live, "sensor": sensed,
            "bookings_now": [{"id": b["id"], "mode": b["mode"], "purpose": b["purpose"], "seats": b["seats"],
                              "end": b["end"], "shareable": b["mode"] == "partial"} for b in current]}


def room_problem(conn: sqlite3.Connection, room: sqlite3.Row, start: datetime, end: datetime, mode: str,
                 seats: int, purpose: str, now: datetime, live: dict) -> str | None:
    """Why this room can't take the booking, or None if it can."""
    if room["closed"]:
        return "Room is closed"
    if seats > room["capacity"]:
        return f"Room holds at most {room['capacity']} people"
    others = overlapping(conn, room["id"], start, end)
    if mode == "full" and others:
        return "Room is already booked for that time"
    if any(b["mode"] == "full" for b in others):
        return "Room is booked exclusively for that time"
    if {PURPOSE_CLASS[purpose], *(PURPOSE_CLASS[b["purpose"]] for b in others)} >= {"quiet", "loud"}:
        return "Quiet and loud bookings can't share a room"
    state = room_state(conn, room, now, live) if start <= now < end else None
    t = start
    while t < end:
        used = sum(b["seats"] for b in others if b["start"] < fmt(t + SLOT) and b["end"] > fmt(t))
        if state and t <= now < t + SLOT:
            used = max(used, state["people"])
        if used + seats > room["capacity"]:
            return f"Only {max(0, room['capacity'] - used)} seats free at {t:%H:%M}"
        t += SLOT
    if state and mode == "partial" and PURPOSE_CLASS[purpose] == "quiet" and state["noise_class"] != "quiet":
        return "Room is too noisy for quiet study right now"
    return None


def validate_times(start: datetime, hours: float, now: datetime) -> datetime:
    if start.minute % 30 or start.second:
        raise ApiError(400, "Bookings start on the full or half hour")
    if hours * 2 != int(hours * 2) or not 0.5 <= hours <= MAX_HOURS_PER_DAY:
        raise ApiError(400, "Book between 0.5 and 4 hours, in steps of 0.5")
    end = start + timedelta(hours=hours)
    if start.time() < OPEN or end > datetime.combine(start.date(), CLOSE):
        raise ApiError(400, f"Rooms can be booked from {OPEN:%H:%M} to {CLOSE:%H:%M}")
    if start < slot_start(now):
        raise ApiError(400, "That time is in the past")
    return end


def create_booking(conn: sqlite3.Connection, user_id: int, req: dict, now: datetime, live: dict) -> dict:
    room = get_room(conn, req["room_id"])
    start, hours, mode, seats, purpose = req["start"], req["hours"], req["mode"], req["seats"], req["purpose"]
    end = validate_times(start, hours, now)
    if purpose == "event" and mode != "full":
        raise ApiError(400, "Events need the whole room")
    own = conn.execute(
        "SELECT start, end FROM bookings WHERE user_id = ? AND status = 'active' AND substr(start, 1, 10) = ?",
        (user_id, start.date().isoformat()),
    ).fetchall()
    if any(b["start"] < fmt(end) and b["end"] > fmt(start) for b in own):
        raise ApiError(400, "You already have a booking at that time")
    used = sum((datetime.fromisoformat(b["end"]) - datetime.fromisoformat(b["start"])).total_seconds() / 3600
               for b in own)
    if used + hours > MAX_HOURS_PER_DAY:
        raise ApiError(400, f"Daily limit is {MAX_HOURS_PER_DAY:g} h; you have {MAX_HOURS_PER_DAY - used:g} h left "
                            f"on {start.date()}")
    problem = room_problem(conn, room, start, end, mode, seats, purpose, now, live)
    if problem:
        raise ApiError(409, problem)
    cur = conn.execute(
        "INSERT INTO bookings (user_id, room_id, start, end, mode, seats, purpose, custom_purpose, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, room["id"], fmt(start), fmt(end), mode, seats, purpose, req.get("custom_purpose"), fmt(now)),
    )
    return booking_out(conn.execute("SELECT * FROM bookings WHERE id = ?", (cur.lastrowid,)).fetchone(), user_id)


def suggest(conn: sqlite3.Connection, start: datetime, hours: float, mode: str, seats: int, purpose: str,
            now: datetime, live: dict, exclude: str | None = None) -> list[dict]:
    """Rooms that can take this booking: quietest first for quiet study, otherwise the tightest fit."""
    end = start + timedelta(hours=hours)
    fits = [room_state(conn, room, now, live) for room in conn.execute("SELECT * FROM rooms ORDER BY id")
            if room["id"] != exclude and room_problem(conn, room, start, end, mode, seats, purpose, now, live) is None]
    if PURPOSE_CLASS[purpose] == "quiet":
        return sorted(fits, key=lambda r: (r["noise_db"], r["capacity"]))
    return sorted(fits, key=lambda r: (r["capacity"] - seats, r["noise_db"]))


def availability(conn: sqlite3.Connection, room: sqlite3.Row, day: date, now: datetime, live: dict) -> list[dict]:
    t, close = datetime.combine(day, OPEN), datetime.combine(day, CLOSE)
    bookings = overlapping(conn, room["id"], t, close)
    people_now = room_state(conn, room, now, live)["people"]
    slots = []
    while t < close:
        end = t + SLOT
        here = [b for b in bookings if b["start"] < fmt(end) and b["end"] > fmt(t)]
        used = sum(b["seats"] for b in here)
        if t <= now < end:
            used = max(used, people_now)
        exclusive = any(b["mode"] == "full" for b in here)
        seats_free = 0 if exclusive or room["closed"] else max(0, room["capacity"] - used)
        if end <= now:
            status = "past"
        elif room["closed"]:
            status = "closed"
        elif exclusive or seats_free == 0:
            status = "full"
        elif here or used:
            status = "partial"
        else:
            status = "free"
        slots.append({"start": f"{t:%H:%M}", "end": f"{end:%H:%M}", "status": status, "seats_free": seats_free,
                      "shareable": bool(here) and not exclusive, "noise": loudest(here)})
        t = end
    return slots


def record_reading(conn: sqlite3.Connection, room_id: str, noise_db: float | None, people: int | None,
                   now: datetime) -> None:
    get_room(conn, room_id)
    conn.execute("INSERT INTO readings (room_id, noise_db, people, at) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(room_id) DO UPDATE SET noise_db=excluded.noise_db, people=excluded.people, at=excluded.at",
                 (room_id, noise_db, people, now.isoformat()))
    if people:
        conn.execute("UPDATE bookings SET checked_in_at = ? WHERE room_id = ? AND status = 'active' "
                     "AND checked_in_at IS NULL AND start <= ? AND end > ?",
                     (fmt(now), room_id, fmt(now), fmt(now)))


def release_ghosts(conn: sqlite3.Connection, now: datetime) -> None:
    """Free bookings where the room sensor saw nobody during the first GHOST_AFTER minutes."""
    rows = conn.execute("SELECT id, room_id FROM bookings WHERE status = 'active' AND checked_in_at IS NULL "
                        "AND start <= ? AND end > ?", (fmt(now - GHOST_AFTER), fmt(now))).fetchall()
    for b in rows:
        reading = fresh_reading(conn, b["room_id"], now)
        if reading is not None and reading["people"] == 0:
            conn.execute("UPDATE bookings SET status = 'released' WHERE id = ?", (b["id"],))
