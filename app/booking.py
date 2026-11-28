"""Booking rules, live room state, availability, search, suggestions and ghost-booking release.

Booking times are campus-time strings 'YYYY-MM-DDTHH:MM' (fixed width, so they compare correctly as text).
Sensor times are compared as datetimes.
"""

import os
import random
import sqlite3
from datetime import date, datetime, time, timedelta

# The one room wired to the PSOC Edge E84 in the Live Lab; every other room is simulated.
BOARD_ROOM = os.environ.get("BOARD_ROOM", "Z.1.04")
OPEN = time.min
SLOT = timedelta(minutes=30)
MAX_HOURS_PER_DAY = 4.0
BOOKING_HORIZON_DAYS = 14
GHOST_AFTER = (timedelta(seconds=int(os.environ["GHOST_RELEASE_SECONDS"]))
               if "GHOST_RELEASE_SECONDS" in os.environ
               else timedelta(minutes=int(os.environ.get("GHOST_RELEASE_MIN", "10"))))
GHOST_GRACE = timedelta(seconds=int(os.environ.get("GHOST_GRACE_SECONDS", "60")))
BOARD_STALE = timedelta(seconds=10)   # board readings older than this are not used (ghost timers survive short gaps)
LIVE_STALE = timedelta(seconds=3)     # the board sends every ~0.6 s: 3 s without a reading = shown as offline
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


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def slot_start(dt: datetime) -> datetime:
    return dt.replace(minute=dt.minute - dt.minute % 30, second=0, microsecond=0)


def listed_rooms(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM rooms WHERE listed = 1 ORDER BY id").fetchall()


def get_room(conn: sqlite3.Connection, room_id: str) -> sqlite3.Row:
    room = conn.execute("SELECT * FROM rooms WHERE id = ? AND listed = 1", (room_id,)).fetchone()
    if room is None:
        raise ApiError(404, f"Unknown room {room_id}")
    return room


def overlapping(conn: sqlite3.Connection, room_id: str, start: datetime, end: datetime) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bookings WHERE room_id = ? AND status = 'active' AND start < ? AND end > ? ORDER BY start",
        (room_id, fmt(end), fmt(start)),
    ).fetchall()


def current_bookings(conn: sqlite3.Connection, room_id: str, now: datetime) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bookings WHERE room_id = ? AND status = 'active' AND start <= ? AND end > ? ORDER BY start",
        (room_id, fmt(now), fmt(now)),
    ).fetchall()


def sensor(conn: sqlite3.Connection, room_id: str, now: datetime) -> dict:
    """Fresh sensor values for a room: noise_db, people and empty_since are None when unknown or stale."""
    row = conn.execute("SELECT * FROM readings WHERE room_id = ?", (room_id,)).fetchone()
    cutoff = now - (BOARD_STALE if room_id == BOARD_ROOM else SENSOR_STALE)
    out = {"noise_db": None, "people": None, "empty_since": None, "left_items": None, "counted": None, "people_at": None,
           "heard_at": max((parse(row[k]) for k in ("noise_at", "people_at") if row and row[k]), default=None)}
    if row and row["noise_at"] and parse(row["noise_at"]) >= cutoff:
        out["noise_db"] = row["noise_db"]
    if row and row["people_at"] and parse(row["people_at"]) >= cutoff:
        out["people_at"] = parse(row["people_at"])
        out["people"] = row["people"]
        out["counted"] = bool(row["counted"])
        out["empty_since"] = parse(row["empty_since"]) if row["empty_since"] else None
        out["left_items"] = row["left_items"]
    return out


def ghost_deadline(booking: sqlite3.Row, seen: dict) -> datetime | None:
    """When a running booking is released if the room stays empty, or None while people are (or may be) there."""
    if seen["people"] != 0 or seen["empty_since"] is None:
        return None
    since = max(seen["empty_since"], parse(booking["start"]), parse(booking["created_at"]))
    if seen["people_at"] < since + min(GHOST_GRACE, GHOST_AFTER / 2):
        return None
    return since + GHOST_AFTER


def loudest(bookings: list[sqlite3.Row]) -> str | None:
    classes = [PURPOSE_CLASS[b["purpose"]] for b in bookings]
    return max(classes, key=NOISE_ORDER.index) if classes else None


def booking_out(conn: sqlite3.Connection, row: sqlite3.Row, now: datetime, user_id: int | None = None) -> dict:
    start, end = parse(row["start"]), parse(row["end"])
    deadline = None
    if row["status"] == "active" and start <= now < end:
        deadline = ghost_deadline(row, sensor(conn, row["room_id"], now))
    return {"id": row["id"], "room_id": row["room_id"], "start": row["start"], "end": row["end"],
            "hours": (end - start).total_seconds() / 3600, "mode": row["mode"], "seats": row["seats"],
            "purpose": row["purpose"], "custom_purpose": row["custom_purpose"], "status": row["status"],
            "checked_in": row["checked_in_at"] is not None,
            "ghost_release_at": deadline.isoformat() if deadline else None, "mine": row["user_id"] == user_id,
            "my_rating": my_rating(conn, user_id, row["room_id"]) if row["user_id"] == user_id else None}


def my_rating(conn: sqlite3.Connection, user_id: int, room_id: str) -> int | None:
    row = conn.execute("SELECT stars FROM ratings WHERE user_id = ? AND room_id = ?", (user_id, room_id)).fetchone()
    return row["stars"] if row else None


def simulating() -> bool:
    return os.environ.get("SIMULATE", "1") != "0"


def simulated(room: sqlite3.Row, current: list[sqlite3.Row], now: datetime) -> tuple[float, int]:
    """Noise and people for a room without a sensor. Random but the same for every viewer: noise changes every
    minute, walk-ins every 10 minutes. Booked rooms hold their booked people (or one fewer); about one free room
    in twelve has one or two walk-ins."""
    booked = sum(b["seats"] for b in current)
    cls = loudest(current)
    if not simulating():
        return SIMULATED_DB[cls], booked
    rnd = random.Random(f"{room['id']}|{now:%Y-%m-%dT%H:%M}")
    walk_ins = random.Random(f"{room['id']}|{now:%Y-%m-%dT%H}|{now.minute // 10}")
    if room["closed"]:
        people = 0
    elif current:
        people = max(1, booked - rnd.randint(0, 1))
    else:
        people = walk_ins.choice([1, 2]) if walk_ins.random() < 1 / 12 else 0
    base = SIMULATED_DB[cls] if cls else SIMULATED_DB[None] + 3 * people
    noise = base + rnd.uniform(-3, 3)
    if cls in (None, "quiet"):
        noise = min(noise, 39.0)  # stays "quiet", so quiet study is never refused by chance
    return round(noise, 1), people


def room_state(conn: sqlite3.Connection, room: sqlite3.Row, now: datetime) -> dict:
    """What the room looks like right now: status, noise, people, free seats and current bookings."""
    current = current_bookings(conn, room["id"], now)
    seen = sensor(conn, room["id"], now)
    sim_noise, sim_people = simulated(room, current, now)
    if seen["noise_db"] is not None:
        noise_db = seen["noise_db"]
    else:
        noise_db = sim_noise
    booked = sum(b["seats"] for b in current)
    people = seen["people"] if seen["people"] is not None else sim_people
    board = room["id"] == BOARD_ROOM
    is_live = board and seen["heard_at"] is not None and now - seen["heard_at"] <= LIVE_STALE
    exclusive = any(b["mode"] == "full" for b in current)
    seats_free = 0 if exclusive or room["closed"] else max(0, room["capacity"] - max(booked, people))
    deadlines = [d for d in (ghost_deadline(b, seen) for b in current) if d]

    if room["closed"]:
        status = "closed"
    elif deadlines:
        status = "ghost"
    elif exclusive or (current and seats_free == 0):
        status = "full"
    elif current or people > 0:
        status = "partial"
    else:
        status = "free"

    rating = conn.execute("SELECT AVG(stars) AS avg, COUNT(*) AS votes FROM ratings WHERE room_id = ?",
                          (room["id"],)).fetchone()
    return {"id": room["id"], "label": room["label"], "building": room["id"].split(".")[0], "floor": room["floor"],
            "name": room["name"], "capacity": room["capacity"],
            "rating": round(rating["avg"], 1) if rating["votes"] else None, "votes": rating["votes"],
            "status": status, "noise_db": round(noise_db, 1),
            "noise_class": noise_class(noise_db), "people": people, "seats_free": seats_free, "board": board,
            "live": is_live, "sensor": seen["people"] is not None, "left_items": seen["left_items"] or 0,
            # booked vs actually here: `present` is what the sensor sees (None without one); `counted` is False when
            # the board only knows yes/no (presence model), so the UI shows "someone is here" instead of a number.
            "booked": booked, "present": seen["people"], "counted": seen["counted"],
            "ghost_release_at": min(deadlines).isoformat() if deadlines else None,
            "bookings_now": [{"id": b["id"], "mode": b["mode"], "purpose": b["purpose"], "seats": b["seats"],
                              "end": b["end"], "shareable": b["mode"] == "partial"} for b in current]}


def room_problem(conn: sqlite3.Connection, room: sqlite3.Row, start: datetime, end: datetime, mode: str,
                 seats: int, purpose: str, now: datetime) -> str | None:
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
    state = room_state(conn, room, now) if start <= now < end else None
    if state and mode == "full" and state["people"] > 0:
        # people are in the room right now without a booking (seen by the sensor, or walk-ins): the room can't be
        # taken privately from under them, but sharing it is fine
        return "People are in the room right now, so it can't be booked privately; book it as shared"
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
    if start.minute % 30 or start.second or start.microsecond:
        raise ApiError(400, "Bookings start on the full or half hour")
    if hours * 2 != int(hours * 2) or not 0.5 <= hours <= MAX_HOURS_PER_DAY:
        raise ApiError(400, "Book between 0.5 and 4 hours, in steps of 0.5")
    end = start + timedelta(hours=hours)
    if end > datetime.combine(start.date() + timedelta(days=1), OPEN):
        raise ApiError(400, "Book each calendar day separately for overnight stays")
    if start < slot_start(now):
        raise ApiError(400, "That time is in the past")
    if start.date() > now.date() + timedelta(days=BOOKING_HORIZON_DAYS):
        raise ApiError(400, f"Bookings open at most {BOOKING_HORIZON_DAYS} days ahead")
    return end


def create_booking(conn: sqlite3.Connection, user_id: int, req: dict, now: datetime) -> dict:
    room = get_room(conn, req["room_id"])
    start, hours, mode, seats, purpose = req["start"], req["hours"], req["mode"], req["seats"], req["purpose"]
    custom = (req.get("custom_purpose") or "").strip() or None
    end = validate_times(start, hours, now)
    if purpose == "event" and mode != "full":
        raise ApiError(400, "Events need the whole room")
    if purpose == "custom" and not custom:
        raise ApiError(400, "Describe the purpose")
    own = conn.execute(
        "SELECT start, end FROM bookings WHERE user_id = ? AND status = 'active' AND substr(start, 1, 10) = ?",
        (user_id, start.date().isoformat()),
    ).fetchall()
    if any(b["start"] < fmt(end) and b["end"] > fmt(start) for b in own):
        raise ApiError(400, "You already have a booking at that time")
    used = sum((parse(b["end"]) - parse(b["start"])).total_seconds() / 3600 for b in own)
    if used + hours > MAX_HOURS_PER_DAY:
        raise ApiError(400, f"Daily limit is {MAX_HOURS_PER_DAY:g} h; you have {MAX_HOURS_PER_DAY - used:g} h left "
                            f"on {start.date()}")
    problem = room_problem(conn, room, start, end, mode, seats, purpose, now)
    if problem:
        raise ApiError(409, problem)
    cur = conn.execute(
        "INSERT INTO bookings (user_id, room_id, start, end, mode, seats, purpose, custom_purpose, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, room["id"], fmt(start), fmt(end), mode, seats, purpose, custom if purpose == "custom" else None,
         now.isoformat()),
    )
    row = conn.execute("SELECT * FROM bookings WHERE id = ?", (cur.lastrowid,)).fetchone()
    return booking_out(conn, row, now, user_id)


def suggest(conn: sqlite3.Connection, start: datetime, hours: float, mode: str, seats: int, purpose: str,
            now: datetime, exclude: str | None = None) -> list[dict]:
    """Rooms that can take this booking: quietest first for quiet study, otherwise the tightest fit."""
    end = start + timedelta(hours=hours)
    fits = [room_state(conn, room, now) for room in listed_rooms(conn)
            if room["id"] != exclude and room_problem(conn, room, start, end, mode, seats, purpose, now) is None]
    if PURPOSE_CLASS[purpose] == "quiet":
        return sorted(fits, key=lambda r: (r["noise_db"], r["capacity"], r["id"]))
    return sorted(fits, key=lambda r: (r["capacity"] - seats, r["noise_db"], r["id"]))


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def search_rank(room: sqlite3.Row, q: str) -> int | None:
    """Lower is better; None means no match. '107a', 'v.1.07a' and 'V 1 07a' all find V.1.07a; '104' finds
    Z.1.04 and V.1.04 (the building letter may be left out)."""
    nq, nid, name = _norm(q), _norm(room["id"]), room["name"].lower()
    label = _norm(room["label"] or "")
    if not nq:
        return None
    if nid == nq or label == nq:
        return 0
    if nid.startswith(nq) or nid[1:].startswith(nq) or (label and label.startswith(nq)):
        return 1
    if nq in nid:
        return 2
    if name.startswith(q.strip().lower()):
        return 3
    if q.strip().lower() in name:
        return 4
    return None


def search(conn: sqlite3.Connection, q: str) -> list[sqlite3.Row]:
    ranked = [(rank, room["id"], room) for room in listed_rooms(conn) if (rank := search_rank(room, q)) is not None]
    return [room for _, _, room in sorted(ranked, key=lambda x: (x[0], x[1]))]


def availability(conn: sqlite3.Connection, room: sqlite3.Row, day: date, now: datetime) -> list[dict]:
    t, close = datetime.combine(day, OPEN), datetime.combine(day + timedelta(days=1), OPEN)
    bookings = overlapping(conn, room["id"], t, close)
    people_now = room_state(conn, room, now)["people"]
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
        slots.append({"start": f"{t:%H:%M}", "end": "24:00" if end == close else f"{end:%H:%M}", "status": status, "seats_free": seats_free,
                      "shareable": bool(here) and not exclusive, "noise": loudest(here)})
        t = end
    return slots


def free_hours(slots: list[dict]) -> float:
    """Hours of a day that can still be booked (slots that are free or shared with seats left)."""
    return sum(1 for s in slots if s["status"] in ("free", "partial")) / 2


def calendar(conn: sqlite3.Connection, day: date, now: datetime) -> dict:
    """Every listed room's slots for one day, in one call (the picker's calendar)."""
    rooms = {}
    for room in listed_rooms(conn):
        slots = availability(conn, room, day, now)
        rooms[room["id"]] = {"free_hours": free_hours(slots), "slots": slots}
    return {"date": day.isoformat(), "open": f"{OPEN:%H:%M}", "close": "24:00", "rooms": rooms}


def can_rate(conn: sqlite3.Connection, user_id: int, room_id: str, now: datetime) -> bool:
    """Only students who actually had the room may rate it: an active booking there that has started."""
    return conn.execute("SELECT 1 FROM bookings WHERE user_id = ? AND room_id = ? AND status = 'active' "
                        "AND start <= ?", (user_id, room_id, fmt(now))).fetchone() is not None


def rate_room(conn: sqlite3.Connection, user_id: int, room_id: str, stars: int, now: datetime) -> dict:
    get_room(conn, room_id)
    if not can_rate(conn, user_id, room_id, now):
        raise ApiError(403, "You can rate a room after you have used it")
    conn.execute("INSERT INTO ratings (user_id, room_id, stars, updated_at) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(user_id, room_id) DO UPDATE SET stars = excluded.stars, updated_at = excluded.updated_at",
                 (user_id, room_id, stars, now.isoformat()))
    row = conn.execute("SELECT AVG(stars) AS avg, COUNT(*) AS votes FROM ratings WHERE room_id = ?",
                       (room_id,)).fetchone()
    return {"room_id": room_id, "rating": round(row["avg"], 1), "votes": row["votes"], "my_rating": stars}


def record_reading(conn: sqlite3.Connection, room_id: str, noise_db: float | None, people: int | None,
                   now: datetime, left_items: int | None = None, counted: bool = True) -> None:
    """`counted` is False when `people` only says yes/no (1 or 0) from a presence model, not a head count."""
    get_room(conn, room_id)
    if noise_db is None and people is None:
        raise ApiError(400, "Send noise_db, people or both")
    old = conn.execute("SELECT * FROM readings WHERE room_id = ?", (room_id,)).fetchone()
    stamp = now.isoformat()
    row = dict(old) if old else {"room_id": room_id, "noise_db": None, "noise_at": None, "people": None,
                                 "people_at": None, "empty_since": None, "left_items": None, "counted": None}
    if left_items is not None:                      # items left behind, counted on the board after people leave
        row["left_items"] = left_items
    if noise_db is not None:
        row.update(noise_db=noise_db, noise_at=stamp)
    if people is not None:
        before = sensor(conn, room_id, now)
        if people > 0:
            empty_since = None
        elif before["people"] == 0 and before["empty_since"] is not None:
            empty_since = row["empty_since"]  # still empty: the timer keeps running
        else:
            empty_since = stamp  # just became empty, or the sensor is back after a gap: the timer starts now
        row.update(people=people, people_at=stamp, empty_since=empty_since, counted=int(counted))
    conn.execute("INSERT OR REPLACE INTO readings (room_id, noise_db, noise_at, people, people_at, empty_since, "
                 "left_items, counted) VALUES (:room_id, :noise_db, :noise_at, :people, :people_at, :empty_since, "
                 ":left_items, :counted)", row)
    if people:
        conn.execute("UPDATE bookings SET checked_in_at = ? WHERE room_id = ? AND status = 'active' "
                     "AND checked_in_at IS NULL AND start <= ? AND end > ?", (stamp, room_id, fmt(now), fmt(now)))


def release_ghosts(conn: sqlite3.Connection, now: datetime) -> None:
    """Release running bookings whose room the sensor has seen empty for GHOST_AFTER."""
    rows = conn.execute("SELECT * FROM bookings WHERE status = 'active' AND start <= ? AND end > ?",
                        (fmt(now), fmt(now))).fetchall()
    for b in rows:
        seen = sensor(conn, b["room_id"], now)
        deadline = ghost_deadline(b, seen)
        if deadline and seen["people_at"] >= deadline:
            conn.execute("UPDATE bookings SET status = 'released' WHERE id = ?", (b["id"],))
