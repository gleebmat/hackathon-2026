"""Public address for the website: a Cloudflare quick tunnel to the backend on this laptop.

Run the backend first, then:  python tools/tunnel.py   (Ctrl+C stops it)
Prints the https://...trycloudflare.com address and writes it to tunnel_url.txt, so the room display's QR codes
(app/display.py) point there. The address is new on every start. Needs cloudflared:
winget install --id Cloudflare.cloudflared
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL_FILE = ROOT / "tunnel_url.txt"
PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"


def main() -> None:
    exe = shutil.which("cloudflared") or next(
        (str(p) for p in (Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe"),
                          Path(r"C:\Program Files\cloudflared\cloudflared.exe")) if p.exists()), None)
    if exe is None:
        sys.exit("cloudflared not found: winget install --id Cloudflare.cloudflared (then open a new terminal)")
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{PORT}"],
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    try:
        for line in proc.stderr:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m and not URL_FILE.exists():
                URL_FILE.write_text(m.group(0), encoding="utf-8")
                print(f"\nPublic website: {m.group(0)}\n(QR codes on the room display use it; Ctrl+C stops)\n")
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    finally:
        URL_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
