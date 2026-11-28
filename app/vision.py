"""People count and left items from the board's camera, detected on the laptop.

The board (firmware/xiao_sense) sends a 320x240 JPEG about every 0.6 s over MQTT to aau-hack26/rooms/<room>/frame,
encrypted with AES-128-CTR (payload = 16-byte counter block + ciphertext) because the broker is public. Here YOLO11s
(models/yolo11s_640.onnx, COCO classes, the frame upscaled to 640 so small and far people are found, ~150 ms on a
laptop CPU) counts people and forgettable things; only the newest frame per room is processed, so nothing queues up.
Items only count when they are within ITEM_MAX_M metres (default 3.5): the distance is estimated from the box size
and the object's typical real size, for a webcam with a CAMERA_FOV degrees (default 65) wide view.
Smoothing: the people count is the median of the last 3 frames and the room is empty only when none of them shows a
person; things count as left behind when nobody was seen in the last 3 frames and they show up in 3 of the last 4.
Key: FRAME_KEY (32 hex characters) or firmware/xiao_sense/frame_key.h, made by tools/make_frame_key.py.
"""

import io
import logging
import math
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

MODEL = db.ROOT / "models" / "yolo11s_640.onnx"
KEY_HEADER = db.ROOT / "firmware" / "xiao_sense" / "frame_key.h"
PERSON = 0
# The only things that count as left behind: COCO class -> (name, typical size of its longest side in metres).
# Not suitcase, umbrella or book: tables, chairs and papers get mistaken for them.
ITEMS = {24: ("backpack", 0.45), 26: ("handbag", 0.35), 39: ("bottle", 0.25), 41: ("cup", 0.10),
         63: ("laptop", 0.33), 64: ("mouse", 0.11), 67: ("cell phone", 0.15)}
PERSON_SCORE = 0.45
ITEM_SCORE = 0.50
ITEM_MAX_M = float(os.environ.get("ITEM_MAX_M", "3.5"))
CAMERA_FOV = float(os.environ.get("CAMERA_FOV", "65"))


def frame_key() -> bytes | None:
    text = os.environ.get("FRAME_KEY") or (KEY_HEADER.read_text() if KEY_HEADER.exists() else "")
    hexes = re.findall(r"0x([0-9a-fA-F]{2})", text) if "0x" in text else re.findall(r"[0-9a-fA-F]{2}", text.strip())
    return bytes(int(h, 16) for h in hexes) if len(hexes) == 16 else None


def decrypt(key: bytes, payload: bytes) -> bytes:
    nonce, data = payload[:16], payload[16:]
    dec = Cipher(algorithms.AES(key), modes.CTR(nonce)).decryptor()
    return dec.update(data) + dec.finalize()


def letterbox(img: Image.Image, size: int) -> tuple[np.ndarray, float]:
    """RGB image -> 1x3xSxS float input scaled to fit with grey bars (as YOLO was trained), and the scale used."""
    scale = size / max(img.size)
    w, h = round(img.width * scale), round(img.height * scale)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(img.resize((w, h), Image.BILINEAR), ((size - w) // 2, (size - h) // 2))
    return (np.asarray(canvas, dtype=np.float32) / 255).transpose(2, 0, 1)[None], scale


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float = 0.45) -> list[int]:
    """Indexes of the boxes kept by non-maximum suppression (boxes as centre x, centre y, w, h)."""
    x1, y1 = boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2
    x2, y2 = boxes[:, 0] + boxes[:, 2] / 2, boxes[:, 1] + boxes[:, 3] / 2
    area = boxes[:, 2] * boxes[:, 3]
    order, kept = scores.argsort()[::-1], []
    while order.size:
        i, rest = order[0], order[1:]
        kept.append(int(i))
        w = np.clip(np.minimum(x2[i], x2[rest]) - np.maximum(x1[i], x1[rest]), 0, None)
        h = np.clip(np.minimum(y2[i], y2[rest]) - np.maximum(y1[i], y1[rest]), 0, None)
        inter = w * h
        order = rest[inter / (area[i] + area[rest] - inter) <= iou]
    return kept


def count(output: np.ndarray, frame_width: float) -> tuple[int, list[tuple[str, float, float]]]:
    """YOLO output 1x84xN (box + 80 class scores), boxes in pixels of a frame frame_width wide ->
    people, and the items within ITEM_MAX_M as (name, score, metres away)."""
    rows = output[0].T
    cls, score = rows[:, 4:].argmax(1), rows[:, 4:].max(1)
    sel = (cls == PERSON) & (score >= PERSON_SCORE)
    people = len(nms(rows[sel, :4], score[sel])) if sel.any() else 0
    focal = frame_width / 2 / math.tan(math.radians(CAMERA_FOV) / 2)   # in pixels
    items = []
    for c, (name, metres) in ITEMS.items():
        sel = (cls == c) & (score >= ITEM_SCORE)
        if not sel.any():
            continue
        boxes, scores = rows[sel, :4], score[sel]
        for i in nms(boxes, scores):
            distance = metres * focal / max(boxes[i, 2], boxes[i, 3], 1)
            if distance <= ITEM_MAX_M:
                items.append((name, round(float(scores[i]), 2), round(float(distance), 1)))
    return people, items


class Room:
    """Last frames of one room -> a steady reading."""

    def __init__(self):
        self.people = deque(maxlen=3)
        self.items = deque(maxlen=4)

    def add(self, people: int, items: int) -> tuple[int, int]:
        self.people.append(people)
        self.items.append(items)
        if any(self.people):
            return max(1, sorted(self.people)[len(self.people) // 2]), 0
        seen = [n for n in self.items if n]
        return 0, (min(seen) if len(seen) >= 3 else 0)


class Vision:
    """Background detector: submit() keeps the newest frame per room, a worker thread detects and calls record()."""

    def __init__(self, key: bytes, record: Callable[[str, int, int], None]):
        import onnxruntime   # imported here so the backend and tests run without it when vision is off
        self.session = onnxruntime.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name
        self.size = self.session.get_inputs()[0].shape[2]
        self.key, self.record = key, record
        self.latest: dict[str, bytes] = {}
        self.rooms: dict[str, Room] = defaultdict(Room)
        self.shown: dict[str, tuple] = {}
        self.wake = threading.Event()
        self.lock = threading.Lock()
        if not log.handlers:   # uvicorn doesn't show app loggers: print what the camera sees to the console
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s camera: %(message)s", "%H:%M:%S"))
            log.addHandler(handler)
            log.setLevel(logging.INFO)
        threading.Thread(target=self.run, daemon=True, name="vision").start()

    def submit(self, room_id: str, payload: bytes) -> None:
        with self.lock:
            self.latest[room_id] = payload
        self.wake.set()

    def detect(self, jpeg: bytes) -> tuple[int, list[tuple[str, float, float]]]:
        img = Image.open(io.BytesIO(jpeg)).convert("RGB")
        x, scale = letterbox(img, self.size)
        out = self.session.run(None, {self.input: x})[0]
        return count(out, img.width * scale)

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
                    log.warning("frame from %s could not be read (wrong key?)", room_id)
                    continue
                shown = self.rooms[room_id].add(people, len(items))
                if (shown, [i[0] for i in items]) != self.shown.get(room_id):
                    self.shown[room_id] = (shown, [i[0] for i in items])
                    log.info("%s: %d people, left items %d | this frame: %d people, items %s", room_id, *shown,
                             people, ", ".join(f"{n} {s:.2f} at ~{d} m" for n, s, d in items) or "none")
                try:
                    self.record(room_id, *shown)
                except Exception:
                    log.exception("result for %s not stored", room_id)


def start(record: Callable[[str, int, int], None]) -> Vision | None:
    key = frame_key()
    if key is None or not MODEL.exists():
        log.warning("Camera frames off: %s", "no FRAME_KEY / frame_key.h" if key is None else f"{MODEL} missing")
        return None
    return Vision(key, record)
