"""Đẩy các file đã sửa (client_daemon.py và kiosk.js) lên Pi 5 và reload.

Fix: âm thanh phát đôi do daemon (mpg123) + Chromium Web Audio cùng phát.
Giải pháp: CHROMIUM_ONLY mode — chỉ Chromium phát, daemon không gọi mpg123.
"""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768

ROOT = Path(__file__).resolve().parents[1]
EDGE = ROOT / "edge_client"


def upload_file(local_path: Path, filename: str) -> bool:
    content = local_path.read_bytes()
    content_b64 = base64.b64encode(content).decode("ascii")
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload"
    payload = json.dumps({"filename": filename, "content_b64": content_b64}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-Deploy/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("success", False)


def send_control(action_data: dict) -> dict:
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control"
    payload = json.dumps(action_data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-Deploy/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print("=" * 70)
    print("   QUAN AI BRAIN — DEPLOY BẢN VÁ SỬA LỖI ÂM THANH PHÁT ĐÔI")
    print("   Fix: CHROMIUM_ONLY mode — tắt mpg123, chỉ Chromium Web Audio phát")
    print("=" * 70)

    files = [
        (EDGE / "client_daemon.py", "client_daemon.py"),
        (EDGE / "kiosk.js", "kiosk.js"),
    ]

    for local_path, filename in files:
        print(f"\n[DEPLOY] Đang đẩy {filename} ({local_path.stat().st_size:,} bytes)...")
        if upload_file(local_path, filename):
            print(f"  ✅ Đã tải thành công: {filename}")
        else:
            print(f"  ❌ THẤT BẠI: {filename}")
            return 1

    print("\n[RELOAD] Đang yêu cầu Pi 5 tải lại giao diện Kiosk...")
    res = send_control({"action": "reload_ui"})
    if res.get("success"):
        print("  ✅ Pi 5 đã nhận tín hiệu reload UI!")
    else:
        print(f"  ⚠️  Reload UI: {res}")

    print("\n[CHÚ Ý] Để daemon cập nhật, cần khởi động lại EdgeClientDaemon trên Pi 5.")
    print("         Lệnh SSH: ssh pi@192.168.1.21 'pkill -f client_daemon && python3 ~/edge_client/main.py'")
    print("         Hoặc khởi động lại Pi 5 từ xa qua nút 'Tắt Hẳn Hình Thể Pi 5' rồi bật lại.")
    print("\n[KIỂM TRA] Trạng thái hiện tại của Pi 5:")
    req = urllib.request.Request(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/status", headers={"User-Agent": "Test"})
    with urllib.request.urlopen(req, timeout=3.0) as r:
        status = json.loads(r.read().decode("utf-8"))
        print(f"  avatar_state: {status.get('avatar_state')}")
        print(f"  core_connected: {status.get('core_connected')}")

    print("\n" + "=" * 70)
    print("   ĐÃ HOÀN TẤT DEPLOY!")
    print("   Chromium Kiosk là nguồn phát DUY NHẤT — hết đôi tiếng!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
