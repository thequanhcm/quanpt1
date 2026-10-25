import base64
import json
from pathlib import Path
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768

script = """#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo "=== PORT 8768 LISTENERS ==="
  ss -tlpn 'sport = :8768' 2>/dev/null || true
  lsof -i :8768 2>/dev/null || true
  fuser 8768/tcp 2>/dev/null || true
  echo "=== ALL PYTHON PROCESSES ==="
  ps aux | grep python || true
  echo "=== PWD AND LS ==="
  pwd
  ls -la
} > "$SCRIPT_DIR/assets/avatar/port_diag.txt" 2>&1
"""

b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
req = urllib.request.Request(
    f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload",
    data=json.dumps({"filename": "setup_pi5_audio.sh", "content_b64": b64}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
urllib.request.urlopen(req, timeout=5)

req2 = urllib.request.Request(
    f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control",
    data=json.dumps({"action": "auto_configure_audio"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
urllib.request.urlopen(req2, timeout=5)

time.sleep(2)
try:
    with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/assets/avatar/port_diag.txt") as r:
        print("=== PORT DIAG ===\n", r.read().decode("utf-8", errors="replace"))
except Exception as e:
    print("No port_diag:", e)
