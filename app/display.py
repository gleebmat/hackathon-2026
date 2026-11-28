"""The board room's touch display and speaker, which the board doesn't have: a small window on the laptop stands in.

The board says it "has" them (`"display": true` in its readings, firmware/xiao_sense/sketch.ino). While such a board is
online the backend opens a chromeless Edge/Chrome window (~480x320, like the Infineon kit's display) on web/display.html and
closes it again when the board goes offline. The page (frontend) calls /api/display/<room>/... with the token from its
URL: book-a-room QR, soundscapes, selfie QR, emergency and take-a-break.

State kept here, in memory: the playing soundscape per room, selfies (10 minutes, never written to disk), and when
each display board was last heard. Breaks and emergencies are in the database (app/db.py).
"""

import logging
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import segno

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
TUNNEL_FILE = ROOT / "tunnel_url.txt"   # written by tools/tunnel.py while the public tunnel runs

SOUNDS = ("off", "rain", "ocean", "forest", "cafe", "white", "pink", "brown")
SELFIE_TTL = timedelta(minutes=10)
CAMERA_FRESH = 3.0          # seconds: a selfie needs a camera frame at most this old
OFFLINE_AFTER = 10.0        # seconds without a reading before the display window closes
WINDOW_SIZE = (800, 520)    # the E84 kit's 4.3" 800x480 screen plus the title bar (the page scales to any size)

TOKEN = os.environ.get("DISPLAY_TOKEN") or secrets.token_urlsafe(16)

sounds: dict[str, dict] = {}                         # room -> {"kind", "volume"}
selfies: dict[str, tuple[bytes, datetime]] = {}      # token -> (jpeg, expires)
frames: dict[str, tuple[bytes, float]] = {}          # room -> (latest decrypted camera jpeg, time.monotonic())
board_seen: dict[str, float] = {}                    # room -> time.monotonic() of the last reading with "display"
lock = threading.Lock()


def public_url(request_base: str) -> str:
    """Base address for QR codes: PUBLIC_URL, else the running tunnel, else the address this request came in on."""
    url = os.environ.get("PUBLIC_URL", "").strip()
    if not url and TUNNEL_FILE.exists():
        url = TUNNEL_FILE.read_text(encoding="utf-8").strip()
    return (url or request_base).rstrip("/")


def qr_svg(data: str) -> str:
    """SVG with a viewBox and no fixed size: the page sizes it with CSS. With the SVG namespace, so it also works on
    its own (an <img> of /api/display/{room}/qr), not only pasted into a page."""
    svg = segno.make(data, error="m").svg_inline(border=2, dark="#111", light="#fff", omitsize=True)
    return svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)


def sound(room_id: str) -> dict:
    return sounds.get(room_id, {"kind": "off", "volume": 50})


def set_sound(room_id: str, kind: str, volume: int) -> dict:
    sounds[room_id] = {"kind": kind, "volume": volume}
    return sounds[room_id]


# --- camera frames and selfies ---

def camera_frame(room_id: str, jpeg: bytes) -> None:
    """Called by app/vision.py with every decrypted frame; only the newest one per room is kept."""
    with lock:
        frames[room_id] = (jpeg, time.monotonic())


def take_selfie(room_id: str, now: datetime, photo: bytes | None = None) -> tuple[str, datetime] | None:
    """Keep a selfie: the photo the display took with its own webcam, else the board camera's newest frame.
    None when there's no photo and the board camera isn't live."""
    with lock:
        if photo is None:
            frame = frames.get(room_id)
            if frame is None or time.monotonic() - frame[1] > CAMERA_FRESH:
                return None
            photo = frame[0]
        for token in [t for t, (_, until) in selfies.items() if until <= now]:
            del selfies[token]
        token = secrets.token_urlsafe(16)
        selfies[token] = (photo, now + SELFIE_TTL)
        return token, now + SELFIE_TTL


def selfie(token: str, now: datetime) -> bytes | None:
    with lock:
        found = selfies.get(token)
        if found and found[1] <= now:
            del selfies[token]
            found = None
    return found[0] if found else None


# --- the window that pretends to be the display ---

def heard(room_id: str) -> None:
    """A reading from a board that has the display arrived."""
    board_seen[room_id] = time.monotonic()


def online(room_id: str) -> bool:
    seen = board_seen.get(room_id)
    return seen is not None and time.monotonic() - seen <= OFFLINE_AFTER


def find_browser() -> str | None:
    """DISPLAY_BROWSER, else Edge or Chrome (both have the chromeless --app window)."""
    if os.environ.get("DISPLAY_BROWSER"):
        return os.environ["DISPLAY_BROWSER"]
    for name in ("msedge", "chrome"):
        if found := shutil.which(name):
            return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        for exe in (Path("Microsoft/Edge/Application/msedge.exe"), Path("Google/Chrome/Application/chrome.exe")):
            if base and (Path(base) / exe).exists():
                return str(Path(base) / exe)
    return None


class Launcher:
    """Opens the display window when a display board comes online and closes it when the board goes offline."""

    def __init__(self, port: int):
        self.port = port
        self.windows: dict[str, subprocess.Popen] = {}
        self.browser = find_browser()
        if self.browser is None:
            log.warning("display: no Edge or Chrome found (set DISPLAY_BROWSER), the display window can't open")
        threading.Thread(target=self.run, daemon=True, name="display").start()

    def url(self, room_id: str) -> str:
        return f"http://localhost:{self.port}/display.html?room={room_id}&token={TOKEN}"

    def open(self, room_id: str) -> None:
        profile = Path(tempfile.gettempdir()) / f"room-display-{room_id}"
        self.windows[room_id] = subprocess.Popen([
            self.browser, f"--app={self.url(room_id)}", f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}",
            f"--user-data-dir={profile}", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
            # the window's own profile, only ever on this page: allow webcam (selfie) and microphone (fire-alarm
            # detection) without a prompt nobody is there to click
            "--use-fake-ui-for-media-stream"])
        log.warning("display: board %s online, display window opened", room_id)

    def close(self, room_id: str) -> None:
        self.windows.pop(room_id).terminate()
        log.warning("display: board %s offline, display window closed", room_id)

    def run(self) -> None:
        while True:
            for room_id in list(board_seen):
                if online(room_id) and room_id not in self.windows and self.browser:
                    self.open(room_id)
                elif not online(room_id) and room_id in self.windows:
                    self.close(room_id)
            for room_id, proc in list(self.windows.items()):
                if proc.poll() is not None and not online(room_id):
                    self.windows.pop(room_id)
            time.sleep(1)


def start(port: int) -> Launcher | None:
    if os.environ.get("DISPLAY_WINDOW", "1") == "0":
        return None
    if not log.handlers:   # uvicorn doesn't show app loggers
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
        log.addHandler(handler)
    launcher = Launcher(port)
    log.warning("display: opens with the board; by hand: %s", launcher.url("Z.1.04"))
    return launcher
