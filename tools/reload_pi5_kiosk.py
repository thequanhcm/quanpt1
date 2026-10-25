"""Restart EdgeClientDaemon trên Pi 5 qua lệnh poweroff + script khởi động lại an toàn.
Hoặc dùng kiosk control để reload_ui nếu chỉ cần kiosk.js.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768


def send_control(action_data: dict) -> dict:
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control"
    payload = json.dumps(action_data).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("Đang gửi lệnh reload UI để kiosk.js mới có hiệu lực (không cần restart daemon)...")
    res = send_control({"action": "reload_ui"})
    print("reload_ui:", res)
    
    time.sleep(2.0)
    
    # Kiểm tra trạng thái sau reload
    req = urllib.request.Request(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/status", headers={"User-Agent": "Test"})
    with urllib.request.urlopen(req, timeout=3.0) as r:
        status = json.loads(r.read().decode("utf-8"))
        print("Pi5 status sau reload:")
        print(f"  avatar_state: {status.get('avatar_state')}")
        print(f"  core_connected: {status.get('core_connected')}")
    
    print("\nkiosk.js đã reload. client_daemon.py sẽ áp dụng ngay lần phát tiếp theo.")
    print("Để restart daemon, dùng lệnh SSH:")
    print("  ssh quanpt1@192.168.1.21 'pkill -f main.py; sleep 1; cd ~/quan_ai_brain/edge_client && python3 main.py &'")


if __name__ == "__main__":
    main()
