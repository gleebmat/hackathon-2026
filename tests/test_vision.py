import os

import numpy as np
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fastapi.testclient import TestClient

from app import main, vision
from tests.test_api import app_env, room, time_now  # noqa: F401  (fixtures)


def test_frame_decrypts_like_the_board_encrypts():
    key, nonce, jpeg = os.urandom(16), os.urandom(16), b"\xff\xd8 a jpeg \xff\xd9" * 50
    enc = Cipher(algorithms.AES(key), modes.CTR(nonce)).encryptor()
    assert vision.decrypt(key, nonce + enc.update(jpeg) + enc.finalize()) == jpeg


def test_key_is_read_from_the_firmware_header(tmp_path, monkeypatch):
    header = tmp_path / "frame_key.h"
    header.write_text("const uint8_t FRAME_KEY[16] = {" + ", ".join(f"0x{b:02x}" for b in range(16)) + "};")
    monkeypatch.delenv("FRAME_KEY", raising=False)
    monkeypatch.setattr(vision, "KEY_HEADER", header)
    assert vision.frame_key() == bytes(range(16))
    monkeypatch.setenv("FRAME_KEY", "ff" * 16)
    assert vision.frame_key() == b"\xff" * 16


def test_count_keeps_one_box_per_object_and_only_near_items():
    out = np.zeros((1, 84, 5), dtype=np.float32)
    out[0, :4, 0] = out[0, :4, 1] = [100, 100, 50, 120]   # the same person found twice
    out[0, :4, 2] = [250, 100, 50, 120]                    # a second person
    out[0, :4, 3] = [200, 200, 40, 40]                     # a backpack about 3 m away
    out[0, :4, 4] = [300, 200, 10, 10]                     # a backpack-sized blob ~11 m away: not in the room
    out[0, 4, :3] = [0.9, 0.8, 0.7]
    out[0, 4 + 24, 3:] = 0.6
    people, items = vision.count(out, 320)
    assert people == 2 and [i[0] for i in items] == ["backpack"] and items[0][2] <= 3.5


def test_smoothing_does_not_flicker():
    r = vision.Room()
    assert r.add(1, 0) == (1, 0)
    assert r.add(0, 0) == (1, 0)          # one missed frame: still there
    assert r.add(2, 0) == (1, 0)
    assert r.add(2, 1) == (2, 0)          # items don't count while people are inside
    r.add(0, 1)
    assert r.add(0, 1) == (1, 0)          # just left: a person was seen in the last 3 frames
    assert r.add(0, 1) == (0, 1)          # nobody for 3 frames, the bag stayed
    assert r.add(0, 0) == (0, 1)          # one frame without it is not enough to clear it
    assert r.add(0, 0) == (0, 0)


def test_camera_count_overrules_board_presence(app_env):
    c = TestClient(main.app)
    assert main.vision_reading("V.1.07a", 2, 0)
    c.post("/api/readings", json={"room_id": "V.1.07a", "presence": False, "noise_db": 44})
    state = room(c, "V.1.07a")
    assert state["people"] == 2 and state["noise_db"] == 44
    main.vision_at.clear()
