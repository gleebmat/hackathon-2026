"""Campus room booking API. Run: uvicorn app.main:app --reload"""

import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Literal

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import auth, booking, clock, db
from app.booking import ApiError
from bridge.ntfy_feed import LiveNoiseFeed

WEB_DIR = db.ROOT / "web"
SESSION_DAYS = 7
feed: LiveNoiseFeed | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global feed
    db.init()
    if os.environ.get("NOISE_FEED", "1") != "0":
        feed = LiveNoiseFeed()
        feed.start()
    yield


app = FastAPI(title="Campus room booking", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse({"error": exc.message}, status_code=exc.status)


def get_conn():
    conn = db.connect()
    try:
        with conn:
            booking.release_ghosts(conn, clock.now())
            yield conn
    finally:
        conn.close()


def live_data() -> dict:
    latest = feed.latest() if feed else None
    return {latest["room_id"]: latest} if latest else {}


def current_user(request: Request, conn=Depends(get_conn)) -> dict:
    token = request.cookies.get(auth.COOKIE)
    row = token and conn.execute("SELECT u.id, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id "
                                 "WHERE s.token = ?", (token,)).fetchone()
    if not row:
        raise ApiError(401, "Not logged in")
    return dict(row)


def start_session(conn, response: Response, user: dict) -> dict:
    token = auth.new_token()
    conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                 (token, user["id"], clock.now().isoformat()))
    response.set_cookie(auth.COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax")
    return {"email": user["email"], "name": user["name"]}


def local_naive(dt: datetime) -> datetime:
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


# --- accounts ---

class Credentials(BaseModel):
    email: str
    password: str


class Registration(Credentials):
    name: str | None = None


@app.post("/api/register", status_code=201)
def register(body: Registration, response: Response, conn=Depends(get_conn)):
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
def login(body: Credentials, response: Response, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),)).fetchone()
    if not row or not auth.check_password(body.password, row["pw_hash"]):
        raise ApiError(401, "Wrong email or password")
    return start_session(conn, response, dict(row))


@app.post("/api/logout")
def logout(request: Request, response: Response, conn=Depends(get_conn)):
    conn.execute("DELETE FROM sessions WHERE token = ?", (request.cookies.get(auth.COOKIE),))
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"email": user["email"], "name": user["name"]}


# --- rooms ---

def matches(room, q: str) -> bool:
    def norm(s: str) -> str:
        return s.lower().replace(".", "").replace(" ", "")
    return norm(q) in norm(room["id"]) or q.lower() in room["name"].lower()


@app.get("/api/rooms")
def rooms(q: str | None = None, conn=Depends(get_conn)):
    live, now = live_data(), clock.now()
    return [booking.room_state(conn, r, now, live) for r in conn.execute("SELECT * FROM rooms ORDER BY id")
            if not q or matches(r, q)]


@app.get("/api/rooms/{room_id}")
def room_detail(room_id: str, request: Request, conn=Depends(get_conn)):
    now = clock.now()
    room = booking.get_room(conn, room_id)
    user = conn.execute("SELECT user_id FROM sessions WHERE token = ?",
                        (request.cookies.get(auth.COOKIE),)).fetchone()
    today = conn.execute("SELECT * FROM bookings WHERE room_id = ? AND status = 'active' AND substr(start, 1, 10) = ? "
                         "ORDER BY start", (room_id, now.date().isoformat())).fetchall()
    return {**booking.room_state(conn, room, now, live_data()),
            "bookings_today": [booking.booking_out(b, user and user["user_id"]) for b in today]}


@app.get("/api/rooms/{room_id}/availability")
def room_availability(room_id: str, day: date | None = Query(None, alias="date"), conn=Depends(get_conn)):
    now = clock.now()
    room = booking.get_room(conn, room_id)
    day = day or now.date()
    return {"room_id": room_id, "date": day.isoformat(), "open": f"{booking.OPEN:%H:%M}",
            "close": f"{booking.CLOSE:%H:%M}", "slots": booking.availability(conn, room, day, now, live_data())}


# --- bookings ---

Mode = Literal["full", "partial"]
Purpose = Literal[tuple(booking.PURPOSE_CLASS)]


class BookingRequest(BaseModel):
    room_id: str
    start: datetime
    hours: float
    mode: Mode
    seats: int = Field(ge=1)
    purpose: Purpose
    custom_purpose: str | None = Field(None, max_length=80)


@app.post("/api/bookings", status_code=201)
def create_booking(body: BookingRequest, user=Depends(current_user), conn=Depends(get_conn)):
    now, live = clock.now(), live_data()
    req = {**body.model_dump(), "start": local_naive(body.start)}
    try:
        return booking.create_booking(conn, user["id"], req, now, live)
    except ApiError as exc:
        if exc.status != 409:
            raise
        alternatives = booking.suggest(conn, req["start"], body.hours, body.mode, body.seats, body.purpose,
                                       now, live, exclude=body.room_id)
        return JSONResponse({"error": exc.message, "suggestions": [r["id"] for r in alternatives[:3]]},
                            status_code=409)


@app.get("/api/bookings/mine")
def my_bookings(user=Depends(current_user), conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY start DESC", (user["id"],)).fetchall()
    return [booking.booking_out(b, user["id"]) for b in rows]


@app.delete("/api/bookings/{booking_id}")
def cancel_booking(booking_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    cur = conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ? AND user_id = ? AND status = 'active'",
                       (booking_id, user["id"]))
    if cur.rowcount == 0:
        raise ApiError(404, "No active booking with that id")
    return {"ok": True}


@app.get("/api/suggest")
def suggest(hours: float, mode: Mode, seats: int = Query(ge=1), purpose: Purpose = "group_study",
            start: datetime | None = None, conn=Depends(get_conn)):
    now = clock.now()
    start = local_naive(start) if start else booking.slot_start(now)
    booking.validate_times(start, hours, now)
    return booking.suggest(conn, start, hours, mode, seats, purpose, now, live_data())


# --- sensors ---

class Reading(BaseModel):
    room_id: str
    noise_db: float | None = None
    people: int | None = Field(None, ge=0)


@app.post("/api/readings")
def post_reading(body: Reading, x_token: str | None = Header(None), conn=Depends(get_conn)):
    expected = os.environ.get("READINGS_TOKEN")
    if expected and x_token != expected:
        raise ApiError(403, "Bad sensor token")
    booking.record_reading(conn, body.room_id, body.noise_db, body.people, clock.now())
    return {"ok": True}


if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
