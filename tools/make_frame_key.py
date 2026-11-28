"""Makes the camera frame key shared by the board and the backend (app/vision.py).

Usage: python tools/make_frame_key.py
Writes firmware/xiao_sense/frame_key.h (the repo holds a public demo key; a new one is secret). Add that file to the Velxio project too; the backend reads the
same file (or FRAME_KEY). Keep an existing key: run it again only to change the key on both sides.
"""

import secrets
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "firmware" / "xiao_sense" / "frame_key.h"
key = secrets.token_bytes(16)
path.write_text("// AES-128 key for camera frames (tools/make_frame_key.py). Secret: never commit it.\n"
                "#pragma once\n"
                "const uint8_t FRAME_KEY[16] = {" + ", ".join(f"0x{b:02x}" for b in key) + "};\n")
print(f"Wrote {path}")
