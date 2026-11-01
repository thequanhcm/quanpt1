"""Kiểm tra chi tiết Micro và Loa trên Raspberry Pi 5.
"""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768

DEBUG_SCRIPT = """#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_OUT="$SCRIPT_DIR/assets/avatar/av_debug.txt"

echo "=== AV DEBUG ===" > "$LOG_OUT"
echo "--- 1. DAEMON LOG ---" >> "$LOG_OUT"
tail -n 30 /tmp/quan_kiosk_daemon.log >> "$LOG_OUT" 2>&1 || true

echo "--- 2. TEST ARECORD WITH PLUGHW:2,0 ---" >> "$LOG_OUT"
arecord -D plughw:2,0 -f S16_LE -r 16000 -c 1 -d 2 /tmp/test_rec.wav >> "$LOG_OUT" 2>&1 || true
if [ -f /tmp/test_rec.wav ]; then
    ls -la /tmp/test_rec.wav >> "$LOG_OUT"
    rm -f /tmp/test_rec.wav
fi

echo "--- 3. TEST ARECORD WITH DEFAULT ---" >> "$LOG_OUT"
arecord -d 2 -f S16_LE -r 16000 -c 1 /tmp/test_rec_def.wav >> "$LOG_OUT" 2>&1 || true
if [ -f /tmp/test_rec_def.wav ]; then
    ls -la /tmp/test_rec_def.wav >> "$LOG_OUT"
    rm -f /tmp/test_rec_def.wav
fi

echo "--- 4. PLAY TEST SOUND ON DEFAULT SINK ---" >> "$LOG_OUT"
if command -v pw-play >/dev/null 2>&1; then
    pw-play /usr/share/sounds/alsa/Front_Center.wav >> "$LOG_OUT" 2>&1 || true
fi
"""


def main():
    content_b64 = base64.b64encode(DEBUG_SCRIPT.encode("utf-8")).decode("ascii")
    url_upload = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload"
    req = urllib.request.Request(
        url_upload,
        data=json.dumps({"filename": "setup_pi5_audio.sh", "content_b64": content_b64}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        print("Upload:", resp.read().decode("utf-8"))

    url_ctl = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control"
    req = urllib.request.Request(
        url_ctl,
        data=json.dumps({"action": "auto_configure_audio"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        print("Trigger:", resp.read().decode("utf-8"))

    print("Đang đợi Pi 5 ghi âm và phát loa...")
    time.sleep(5.0)

    url_log = f"http://{PI5_IP}:{PI5_PORT}/assets/avatar/av_debug.txt"
    with urllib.request.urlopen(url_log, timeout=5.0) as resp:
        print("\n--- KẾT QUẢ TỪ PI 5 ---")
        print(resp.read().decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
