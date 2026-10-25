"""Thu thập danh sách tiến trình và kiểm tra phiên bản daemon trên Pi 5.
"""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768

SCRIPT = """#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/client_daemon.py" "$SCRIPT_DIR/assets/avatar/pi5_daemon.py" 2>/dev/null || true
ps aux | grep -E 'python|chromium' > "$SCRIPT_DIR/assets/avatar/pi5_ps.txt" 2>&1 || true
"""


def main():
    content_b64 = base64.b64encode(SCRIPT.encode("utf-8")).decode("ascii")
    url_upload = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload"
    req = urllib.request.Request(
        url_upload,
        data=json.dumps({"filename": "setup_pi5_audio.sh", "content_b64": content_b64}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=5.0)

    url_ctl = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control"
    req = urllib.request.Request(
        url_ctl,
        data=json.dumps({"action": "auto_configure_audio"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=5.0)

    time.sleep(2.0)

    with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/assets/avatar/pi5_ps.txt") as r:
        print("PROCESSES ON PI 5:\n", r.read().decode("utf-8", errors="replace"))

    with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/assets/avatar/pi5_daemon.py") as r:
        code = r.read().decode("utf-8", errors="replace")
        print(f"PI5 DAEMON CODE SIZE: {len(code)} bytes")
        for line in code.splitlines():
            if "content_length >" in line or "mpg123" in line or "play_audio_on_hardware_speaker" in line:
                print("  ->", line.strip())


if __name__ == "__main__":
    main()
