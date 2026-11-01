import base64
import json
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768

restart_script = """#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Start a detached subshell that waits 0.5s (so this HTTP request completes), then restarts main.py
(
  sleep 0.5
  pkill -f "main.py" 2>/dev/null || true
  pkill -f "client_daemon" 2>/dev/null || true
  sleep 1.0
  nohup python3 "$SCRIPT_DIR/main.py" > "$SCRIPT_DIR/daemon.log" 2>&1 &
  echo "RESTARTED $(date)" > "$SCRIPT_DIR/assets/avatar/restart_ok.txt"
) &
"""

print("[1/3] Đang tải lên script restart_pi5_proper...")
b64 = base64.b64encode(restart_script.encode("utf-8")).decode("ascii")
req = urllib.request.Request(
    f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload",
    data=json.dumps({"filename": "setup_pi5_audio.sh", "content_b64": b64}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=5) as r:
    print("  Upload result:", r.read().decode())

print("[2/3] Kích hoạt auto_configure_audio...")
req2 = urllib.request.Request(
    f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control",
    data=json.dumps({"action": "auto_configure_audio"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req2, timeout=5) as r:
        print("  Trigger result:", r.read().decode())
except Exception as e:
    print("  Trigger sent (conn dropped as expected):", e)

print("[3/3] Đang chờ 3.5s để daemon mới khởi động và bind port 8768...")
time.sleep(3.5)

for i in range(1, 10):
    try:
        with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/audio/status", timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"🎉 THÀNH CÔNG! Audio status: {data}")
            break
    except Exception as e:
        print(f"  Thử {i}/9: {e}")
        time.sleep(1.2)
