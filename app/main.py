"""Campus room booking API. Run: uvicorn app.main:app --reload"""

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from app import auth, booking, clock, db, mqtt_feed
from app.booking import ApiError

WEB_DIR = db.ROOT / "web"
SESSION_DAYS = 7


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    mqtt_client = mqtt_feed.start(mqtt_reading) if os.environ.get("MQTT_FEED", "1") != "0" else None
    yield
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


app = FastAPI(title="Campus room booking", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse({"error": exc.message}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p not in ("body", "query", "path"))
    return JSONResponse({"error": f"{field}: {first['msg']}" if field else first["msg"]}, status_code=400)


def get_conn():
    """One write-locked transaction per request, committed before the response is sent.

    BEGIN IMMEDIATE serialises writers, so two people can't book the last seat at the same moment.
    """
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            booking.release_ghosts(conn, clock.now())
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn, scope="function")]


def session_user(conn: sqlite3.Connection, request: Request) -> dict | None:
    token = request.cookies.get(auth.COOKIE)
    if not token:
        return None
    cutoff = (clock.now() - timedelta(days=SESSION_DAYS)).isoformat()
    row = conn.execute("SELECT u.id, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id "
                       "WHERE s.token = ? AND s.created_at >= ?", (token, cutoff)).fetchone()
    return dict(row) if row else None


def current_user(request: Request, conn: Conn) -> dict:
    user = session_user(conn, request)
    if user is None:
        raise ApiError(401, "Not logged in")
    return user


User = Annotated[dict, Depends(current_user)]


def start_session(conn: sqlite3.Connection, response: Response, user: dict) -> dict:
    token = auth.new_token()
    conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                 (token, user["id"], clock.now().isoformat()))
    response.set_cookie(auth.COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax")
    return {"email": user["email"], "name": user["name"]}


# --- accounts ---

class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class Registration(Credentials):
    name: str | None = Field(None, max_length=60)


@app.post("/api/register", status_code=201)
def register(body: Registration, response: Response, conn: Conn):
    email = body.email.strip().lower()
    if not auth.valid_email(email):
        raise ApiError(400, f"Use your student email ({auth.EMAIL_DOMAIN})")
    if len(body.password) < auth.MIN_PASSWORD:
        raise ApiError(400, f"Password needs at least {auth.MIN_PASSWORD} characters")
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise ApiError(409, "An account with this email already exists")
    name = (body.name or "").strip() or email.split("@")[0]
    cur = conn.execute("INSERT INTO users (email, name, pw_hash) VALUES (?, ?, ?)",
                       (email, name, auth.hash_password(body.password)))
    return start_session(conn, response, {"id": cur.lastrowid, "email": email, "name": name})


@app.post("/api/login")
def login(body: Credentials, response: Response, conn: Conn):
    row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),)).fetchone()
    if not row or not auth.check_password(body.password, row["pw_hash"]):
        raise ApiError(401, "Wrong email or password")
    return start_session(conn, response, dict(row))


@app.post("/api/logout")
def logout(request: Request, response: Response, conn: Conn):
    conn.execute("DELETE FROM sessions WHERE token = ?", (request.cookies.get(auth.COOKIE),))
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(user: User):
    return {"email": user["email"], "name": user["name"]}


# --- rooms ---

@app.get("/api/rooms")
def rooms(conn: Conn, q: str | None = Query(None, max_length=50)):
    now = clock.now()
    found = booking.search(conn, q) if q and q.strip() else booking.listed_rooms(conn)
    return [booking.room_state(conn, r, now) for r in found]


@app.get("/api/search")
def search(conn: Conn, q: str = Query("", max_length=50), limit: int = Query(8, ge=1, le=50)):
    now = clock.now()
    return [{key: state[key] for key in ("id", "label", "name", "floor", "status", "seats_free")}
            for state in (booking.room_state(conn, r, now) for r in booking.search(conn, q)[:limit])]


@app.get("/api/rooms/{room_id}")
def room_detail(room_id: str, request: Request, conn: Conn):
    now = clock.now()
    room = booking.get_room(conn, room_id)
    user = session_user(conn, request)
    today = conn.execute("SELECT * FROM bookings WHERE room_id = ? AND status = 'active' AND substr(start, 1, 10) = ? "
                         "ORDER BY start", (room_id, now.date().isoformat())).fetchall()
    return {**booking.room_state(conn, room, now),
            "bookings_today": [booking.booking_out(conn, b, now, user and user["id"]) for b in today],
            "my_rating": booking.my_rating(conn, user["id"], room_id) if user else None,
            "can_rate": bool(user) and booking.can_rate(conn, user["id"], room_id, now)}


@app.get("/api/rooms/{room_id}/availability")
def room_availability(room_id: str, conn: Conn, day: date | None = Query(None, alias="date")):
    now = clock.now()
    room = booking.get_room(conn, room_id)
    day = day or now.date()
    return {"room_id": room_id, "date": day.isoformat(), "open": f"{booking.OPEN:%H:%M}",
            "close": "24:00", "slots": booking.availability(conn, room, day, now)}


@app.get("/api/calendar")
def calendar(conn: Conn, day: date | None = Query(None, alias="date")):
    now = clock.now()
    return booking.calendar(conn, day or now.date(), now)


class RatingRequest(BaseModel):
    stars: int = Field(ge=1, le=5)


@app.post("/api/rooms/{room_id}/rating")
def rate_room(room_id: str, body: RatingRequest, user: User, conn: Conn):
    return booking.rate_room(conn, user["id"], room_id, body.stars, clock.now())


# --- bookings ---

Mode = Literal["full", "partial"]
Purpose = Literal[tuple(booking.PURPOSE_CLASS)]


class BookingRequest(BaseModel):
    room_id: str = Field(max_length=20)
    start: datetime
    hours: float = Field(ge=0.5, le=booking.MAX_HOURS_PER_DAY, multiple_of=0.5, allow_inf_nan=False)
    mode: Mode
    seats: int = Field(ge=1, le=1000)
    purpose: Purpose
    custom_purpose: str | None = Field(None, max_length=80)


@app.post("/api/bookings", status_code=201)
def create_booking(body: BookingRequest, user: User, conn: Conn):
    now = clock.now()
    req = {**body.model_dump(), "start": clock.to_local(body.start)}
    try:
        return booking.create_booking(conn, user["id"], req, now)
    except ApiError as exc:
        if exc.status != 409:
            raise
        alternatives = booking.suggest(conn, req["start"], body.hours, body.mode, body.seats, body.purpose,
                                       now, exclude=body.room_id)
        return JSONResponse({"error": exc.message, "suggestions": [r["id"] for r in alternatives[:3]]},
                            status_code=409)


@app.get("/api/bookings/mine")
def my_bookings(user: User, conn: Conn):
    now = clock.now()
    rows = conn.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY start DESC, id DESC",
                        (user["id"],)).fetchall()
    return [booking.booking_out(conn, b, now, user["id"]) for b in rows]


@app.delete("/api/bookings/{booking_id}")
def cancel_booking(booking_id: int, user: User, conn: Conn):
    row = conn.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ? AND status = 'active'",
                       (booking_id, user["id"])).fetchone()
    if row is None:
        raise ApiError(404, "No active booking with that id")
    if booking.parse(row["end"]) <= clock.now():
        raise ApiError(400, "This booking is already over")
    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    return {"ok": True}


@app.get("/api/suggest")
def suggest(conn: Conn, mode: Mode, hours: float = Query(ge=0.5, le=booking.MAX_HOURS_PER_DAY, allow_inf_nan=False),
            seats: int = Query(ge=1, le=1000), purpose: Purpose = "group_study", start: datetime | None = None):
    now = clock.now()
    start = clock.to_local(start) if start else booking.slot_start(now)
    booking.validate_times(start, hours, now)
    return booking.suggest(conn, start, hours, mode, seats, purpose, now)


# --- sensors ---

class Reading(BaseModel):
    """From the board (over MQTT, app/mqtt_feed.py) or a simulator. Extra fields (person_score, ...) are ignored."""
    room_id: str = Field(max_length=20)
    noise_db: float | None = Field(None, ge=0, le=150, allow_inf_nan=False)
    people: int | None = Field(None, ge=0, le=1000)
    presence: bool | None = None
    left_items: int | None = Field(None, ge=0, le=100)   # items left behind, counted on the board


def save_reading(conn: sqlite3.Connection, body: Reading) -> None:
    people = body.people if body.people is not None else (None if body.presence is None else int(body.presence))
    booking.record_reading(conn, body.room_id, body.noise_db, people, clock.now(), body.left_items,
                           counted=body.people is not None)


@app.post("/api/readings")
def post_reading(body: Reading, conn: Conn, x_token: str | None = Header(None)):
    expected = os.environ.get("READINGS_TOKEN")
    if expected and x_token != expected:
        raise ApiError(403, "Bad sensor token")
    save_reading(conn, body)
    return {"ok": True}


def mqtt_reading(payload: dict) -> bool:
    """A reading that arrived over MQTT (app/mqtt_feed.py): same validation and storage as POST /api/readings.
    Returns False when it was rejected (bad fields, unknown room)."""
    try:
        body = Reading(**payload)
    except ValidationError:
        return False
    conn = db.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            save_reading(conn, body)
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        return True
    except ApiError:
        return False
    finally:
        conn.close()


class NoCacheStatic(StaticFiles):
    """Browsers revalidate every file, so nobody runs stale JS after a pull (unchanged files still get a 304)."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


if WEB_DIR.is_dir():
    app.mount("/", NoCacheStatic(directory=WEB_DIR, html=True), name="web")
