"""People count and left items from the board's camera, detected on the laptop.

The board (firmware/xiao_sense) sends a 320x240 JPEG about once a second over MQTT to aau-hack26/rooms/<room>/frame,
encrypted with AES-128-CTR (payload = 16-byte counter block + ciphertext) because the broker is public. Here YOLO11n
(models/yolo11n_320.onnx, COCO classes, ~10-20 ms on a laptop CPU) counts people and forgettable things in it; only the
newest frame per room is processed, so results never queue up.
Smoothing over the last 3 frames: the count is their median (a missed frame doesn't flicker), a room is empty only
when none of them shows a person, and things count as left behind when the room is empty and they show up in at
least 2 of them.
Key: FRAME_KEY (32 hex characters) or firmware/xiao_sense/frame_key.h, made by tools/make_frame_key.py.
"""

import io
import logging
import os
import re
import threading
from collections import defaultdict, deque
from collections.abc import Callable

import numpy as np
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from PIL import Image

from app import db

log = logging.getLogger(__name__)

MODEL = db.ROOT / "models" / "yolo11n_320.onnx"
KEY_HEADER = db.ROOT / "firmware" / "xiao_sense" / "frame_key.h"
SIZE = 320
PERSON = 0
ITEMS = {24: "backpack", 25: "umbrella", 26: "handbag", 28: "suitcase", 39: "bottle", 41: "cup", 63: "laptop",
         67: "cell phone", 73: "book"}
PERSON_SCORE = 0.45
ITEM_SCORE = 0.35
WINDOW = 3


def frame_key() -> bytes | None:
    text = os.environ.get("FRAME_KEY") or (KEY_HEADER.read_text() if KEY_HEADER.exists() else "")
    hexes = re.findall(r"0x([0-9a-fA-F]{2})", text) if "0x" in text else re.findall(r"[0-9a-fA-F]{2}", text.strip())
    return bytes(int(h, 16) for h in hexes) if len(hexes) == 16 else None


def decrypt(key: bytes, payload: bytes) -> bytes:
    nonce, data = payload[:16], payload[16:]
    dec = Cipher(algorithms.AES(key), modes.CTR(nonce)).decryptor()
    return dec.update(data) + dec.finalize()


def letterbox(img: Image.Image) -> np.ndarray:
    """RGB image -> 1x3x320x320 float input, scaled to fit with grey bars (as YOLO was trained)."""
    scale = SIZE / max(img.size)
    w, h = round(img.width * scale), round(img.height * scale)
    canvas = Image.new("RGB", (SIZE, SIZE), (114, 114, 114))
    canvas.paste(img.resize((w, h)), ((SIZE - w) // 2, (SIZE - h) // 2))
    return (np.asarray(canvas, dtype=np.float32) / 255).transpose(2, 0, 1)[None]


def nms_count(boxes: np.ndarray, scores: np.ndarray, iou: float = 0.45) -> int:
    """Number of boxes left after non-maximum suppression (boxes as centre x, centre y, w, h)."""
    x1, y1 = boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2
    x2, y2 = boxes[:, 0] + boxes[:, 2] / 2, boxes[:, 1] + boxes[:, 3] / 2
    area = boxes[:, 2] * boxes[:, 3]
    order, kept = scores.argsort()[::-1], 0
    while order.size:
        i, rest = order[0], order[1:]
        kept += 1
        w = np.clip(np.minimum(x2[i], x2[rest]) - np.maximum(x1[i], x1[rest]), 0, None)
        h = np.clip(np.minimum(y2[i], y2[rest]) - np.maximum(y1[i], y1[rest]), 0, None)
        inter = w * h
        order = rest[inter / (area[i] + area[rest] - inter) <= iou]
    return kept


def count(output: np.ndarray) -> tuple[int, dict[str, int]]:
    """YOLO output 1x84xN (box + 80 class scores) -> people and {item name: count}."""
    rows = output[0].T
    cls, score = rows[:, 4:].argmax(1), rows[:, 4:].max(1)
    people = nms_count(rows[(cls == PERSON) & (score >= PERSON_SCORE), :4], score[(cls == PERSON) & (score >= PERSON_SCORE)])
    items = {}
    for c, name in ITEMS.items():
        sel = (cls == c) & (score >= ITEM_SCORE)
        if sel.any():
            items[name] = nms_count(rows[sel, :4], score[sel])
    return people, items


class Room:
    """Last frames of one room -> a steady reading."""

    def __init__(self):
        self.people = deque(maxlen=WINDOW)
        self.items = deque(maxlen=WINDOW)

    def add(self, people: int, items: int) -> tuple[int, int]:
        self.people.append(people)
        self.items.append(items)
        if not any(self.people):
            seen = sorted(n for n in self.items if n)
            return 0, (seen[0] if len(seen) >= 2 else 0)
        return max(1, sorted(self.people)[len(self.people) // 2]), 0


class Vision:
    """Background detector: submit() keeps the newest frame per room, a worker thread detects and calls record()."""

    def __init__(self, key: bytes, record: Callable[[str, int, int], None]):
        import onnxruntime   # imported here so the backend and tests run without it when vision is off
        self.session = onnxruntime.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name
        self.key, self.record = key, record
        self.latest: dict[str, bytes] = {}
        self.rooms: dict[str, Room] = defaultdict(Room)
        self.wake = threading.Event()
        self.lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True, name="vision").start()

    def submit(self, room_id: str, payload: bytes) -> None:
        with self.lock:
            self.latest[room_id] = payload
        self.wake.set()

    def detect(self, jpeg: bytes) -> tuple[int, dict[str, int]]:
        img = Image.open(io.BytesIO(jpeg)).convert("RGB")
        return count(self.session.run(None, {self.input: letterbox(img)})[0])

    def run(self) -> None:
        while True:
            self.wake.wait()
            self.wake.clear()
            with self.lock:
                frames, self.latest = self.latest, {}
            for room_id, payload in frames.items():
                try:
                    people, items = self.detect(decrypt(self.key, payload))
                except Exception:   # wrong key, cut-off frame: skip it
                    log.warning("Frame from %s could not be read", room_id)
                    continue
                shown_people, left = self.rooms[room_id].add(people, sum(items.values()))
                log.info("%s: %d people, items %s -> people %d, left %d", room_id, people, items, shown_people, left)
                try:
                    self.record(room_id, shown_people, left)
                except Exception:
                    log.exception("Vision result for %s not stored", room_id)


def start(record: Callable[[str, int, int], None]) -> Vision | None:
    key = frame_key()
    if key is None or not MODEL.exists():
        log.warning("Camera frames off: %s", "no FRAME_KEY / frame_key.h" if key is None else f"{MODEL} missing")
        return None
    return Vision(key, record)
