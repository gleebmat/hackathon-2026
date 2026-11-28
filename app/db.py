"""SQLite storage: schema, connection and seed data (the bookable rooms of the 3D campus map, demo accounts)."""

import json
import os
import sqlite3
from pathlib import Path

from app.auth import hash_password

ROOT = Path(__file__).resolve().parent.parent
CAMPUS_JSON = ROOT / "web" / "map3d" / "campus.json"
DEFAULT_CAPACITY = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, pw_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY, floor INTEGER NOT NULL, name TEXT NOT NULL, capacity INTEGER NOT NULL,
    closed INTEGER NOT NULL DEFAULT 0, listed INTEGER NOT NULL DEFAULT 1, label TEXT);
CREATE TABLE IF NOT EXISTS ratings (
    user_id INTEGER NOT NULL REFERENCES users(id), room_id TEXT NOT NULL REFERENCES rooms(id),
    stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5), updated_at TEXT NOT NULL, PRIMARY KEY (user_id, room_id));
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL REFERENCES users(id), room_id TEXT NOT NULL REFERENCES rooms(id),
    created_at TEXT NOT NULL, PRIMARY KEY (user_id, room_id));
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), room_id TEXT NOT NULL REFERENCES rooms(id),
    start TEXT NOT NULL, end TEXT NOT NULL, mode TEXT NOT NULL, seats INTEGER NOT NULL, purpose TEXT NOT NULL,
    custom_purpose TEXT, status TEXT NOT NULL DEFAULT 'active', checked_in_at TEXT, created_at TEXT NOT NULL,
    break_until TEXT);
CREATE TABLE IF NOT EXISTS emergencies (
    id INTEGER PRIMARY KEY, room_id TEXT NOT NULL REFERENCES rooms(id), created_at TEXT NOT NULL,
    resolved_at TEXT, resolved_by INTEGER REFERENCES users(id));
CREATE INDEX IF NOT EXISTS bookings_room_time ON bookings (room_id, status, start);
CREATE INDEX IF NOT EXISTS bookings_user_time ON bookings (user_id, status, start);
"""
# Latest sensor values per room. It is only a cache, so it is rebuilt whenever its columns change.
READINGS = """
CREATE TABLE IF NOT EXISTS readings (
    room_id TEXT PRIMARY KEY REFERENCES rooms(id), noise_db REAL, noise_at TEXT, people INTEGER, people_at TEXT,
    empty_since TEXT, left_items INTEGER, counted INTEGER)
"""
READINGS_COLUMNS = {"room_id", "noise_db", "noise_at", "people", "people_at", "empty_since", "left_items",
                    "counted"}

# Fallback when the map data is missing (the tests use it): building V floor 1, real numbers and names from
# campusplan.aau.at, made-up capacities.
DEFAULT_ROOMS = [
    {"id": "V.1.01", "name": "Seminarraum", "capacity": 30},
    {"id": "V.1.02", "name": "Arbeits- und Aufenthaltsraum", "capacity": 20},
    {"id": "V.1.03", "name": "Seminarraum", "capacity": 24},
    {"id": "V.1.04", "name": "Seminarraum", "capacity": 24},
    {"id": "V.1.07", "name": "Seminarraum", "capacity": 30},
    {"id": "V.1.07a", "name": "Atrium", "capacity": 12},
    {"id": "V.1.08", "name": "Seminarraum", "capacity": 20},
    {"id": "V.1.12", "name": "Sozialraum", "capacity": 8},
    {"id": "V.1.24", "name": "Reflektorium", "capacity": 16, "closed": True},
    {"id": "V.1.27", "name": "Seminarraum", "capacity": 30},
    {"id": "V.1.29", "name": "Mediathek", "capacity": 10},
    {"id": "V.1.34", "name": "Seminarraum", "capacity": 24},
]
DEMO_USERS = [(f"student{i}@edu.aau.at", f"Student {i}") for i in range(1, 5)]
DEMO_PASSWORD = "demo"


def db_path() -> str:
    return os.environ.get("DB_PATH", str(ROOT / "campus.db"))


def connect() -> sqlite3.Connection:
    """Autocommit connection; callers open transactions explicitly (BEGIN IMMEDIATE)."""
    conn = sqlite3.connect(db_path(), timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_rooms() -> list[dict]:
    """Every bookable room of the 3D map (web/map3d/campus.json), so the map, search and bookings always match."""
    if CAMPUS_JSON.exists():
        campus = json.loads(CAMPUS_JSON.read_text(encoding="utf-8"))
        rooms = [r for b in campus["buildings"] for r in b["rooms"] if r.get("bookable")]
    else:
        rooms = [{**r, "floor": 1} for r in DEFAULT_ROOMS]
    return [{"id": r["id"], "floor": int(r["floor"]), "name": r.get("name") or r["id"],
             "capacity": int(r.get("capacity") or DEFAULT_CAPACITY), "closed": int(bool(r.get("closed"))),
             "label": r.get("label")}
            for r in rooms]


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def upgrade(conn: sqlite3.Connection) -> None:
    """Bring a database created by an older version up to date, keeping users, sessions and bookings."""
    if "listed" not in columns(conn, "rooms"):
        conn.execute("ALTER TABLE rooms ADD COLUMN listed INTEGER NOT NULL DEFAULT 1")
    if "label" not in columns(conn, "rooms"):
        conn.execute("ALTER TABLE rooms ADD COLUMN label TEXT")
    if "break_until" not in columns(conn, "bookings"):
        conn.execute("ALTER TABLE bookings ADD COLUMN break_until TEXT")
    if columns(conn, "readings") not in (set(), READINGS_COLUMNS):
        conn.execute("DROP TABLE readings")
    conn.execute(READINGS)


def init() -> None:
    conn = connect()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        upgrade(conn)
        rooms = load_rooms()
        # Rooms that left the data file stay in the database (their bookings keep a valid room) but are hidden.
        conn.execute("UPDATE rooms SET listed = 0")
        conn.executemany(
            "INSERT INTO rooms (id, floor, name, capacity, closed, listed, label) "
            "VALUES (:id, :floor, :name, :capacity, :closed, 1, :label) "
            "ON CONFLICT(id) DO UPDATE SET floor=excluded.floor, name=excluded.name, capacity=excluded.capacity, "
            "closed=excluded.closed, listed=1, label=excluded.label",
            rooms,
        )
        for email, name in DEMO_USERS:
            if not conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                conn.execute("INSERT INTO users (email, name, pw_hash) VALUES (?, ?, ?)",
                             (email, name, hash_password(DEMO_PASSWORD)))
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
