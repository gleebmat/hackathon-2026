"""SQLite storage: schema, connection and seed data (floor 1 rooms of building V, demo accounts)."""

import json
import os
import sqlite3
from pathlib import Path

from app.auth import hash_password

ROOT = Path(__file__).resolve().parent.parent
BUILDING_JSON = ROOT / "web" / "data" / "building_v.json"
FLOOR = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, pw_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY, floor INTEGER NOT NULL, name TEXT NOT NULL, capacity INTEGER NOT NULL,
    closed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), room_id TEXT NOT NULL REFERENCES rooms(id),
    start TEXT NOT NULL, end TEXT NOT NULL, mode TEXT NOT NULL, seats INTEGER NOT NULL, purpose TEXT NOT NULL,
    custom_purpose TEXT, status TEXT NOT NULL DEFAULT 'active', checked_in_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS readings (
    room_id TEXT PRIMARY KEY REFERENCES rooms(id), noise_db REAL, people INTEGER, at TEXT NOT NULL);
"""

# Used until web/data/building_v.json exists. All numbers are made up.
DEFAULT_ROOMS = [
    {"id": "V.1.01", "name": "Lecture hall", "capacity": 60},
    {"id": "V.1.02", "name": "Seminar room", "capacity": 30},
    {"id": "V.1.03", "name": "Group room", "capacity": 8},
    {"id": "V.1.04", "name": "Group room", "capacity": 8},
    {"id": "V.1.05", "name": "Computer lab", "capacity": 24},
    {"id": "V.1.06", "name": "Seminar room", "capacity": 20},
    {"id": "V.1.07a", "name": "Seminar room", "capacity": 12},
    {"id": "V.1.07b", "name": "Study room", "capacity": 6},
    {"id": "V.1.08", "name": "Meeting room", "capacity": 10},
    {"id": "V.1.09", "name": "Project room", "capacity": 16},
    {"id": "V.1.10", "name": "Quiet study room", "capacity": 14},
    {"id": "V.1.11", "name": "Group room", "capacity": 6, "closed": True},
]
DEMO_USERS = [(f"student{i}@edu.aau.at", f"Student {i}") for i in range(1, 5)]
DEMO_PASSWORD = "demo"


def db_path() -> str:
    return os.environ.get("DB_PATH", str(ROOT / "campus.db"))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_rooms() -> list[dict]:
    if BUILDING_JSON.exists():
        rooms = json.loads(BUILDING_JSON.read_text(encoding="utf-8"))["rooms"]
        return [r for r in rooms if r.get("floor") == FLOOR]
    return [{**r, "floor": FLOOR} for r in DEFAULT_ROOMS]


def init() -> None:
    conn = connect()
    with conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO rooms (id, floor, name, capacity, closed) VALUES (:id, :floor, :name, :capacity, :closed) "
            "ON CONFLICT(id) DO UPDATE SET floor=excluded.floor, name=excluded.name, "
            "capacity=excluded.capacity, closed=excluded.closed",
            [{**r, "closed": int(bool(r.get("closed")))} for r in load_rooms()],
        )
        for email, name in DEMO_USERS:
            if not conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                conn.execute("INSERT INTO users (email, name, pw_hash) VALUES (?, ?, ?)",
                             (email, name, hash_password(DEMO_PASSWORD)))
    conn.close()
