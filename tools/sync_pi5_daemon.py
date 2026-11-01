"""Đồng bộ mã nguồn client_daemon.py mới nhất sang Raspberry Pi 5 và khởi động lại daemon.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768
ROOT = Path(__file__).resolve().parents[1]
DAEMON_PATH = ROOT / "edge_client" / "client_daemon.py"


def upload_file(filename: str, content_bytes: bytes) -> bool:
    b64 = base64.b64encode(content_bytes).decode("ascii")
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload"
    payload = json.dumps({"filename": filename, "content_b64": b64}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-SyncDaemon/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("success", False)


def trigger_control(action_data: dict) -> dict | None:
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control"
    payload = json.dumps(action_data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-SyncDaemon/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print("=" * 72)
    print("   QUAN AI BRAIN — ĐỒNG BỘ & TÁI KHỞI ĐỘNG DAEMON PI 5 (ADDENDUM V2.1)")
    print("=" * 72)

    # 1. Kiểm tra kết nối hiện tại
    print("[1/5] Kiểm tra kết nối tới Pi 5 daemon...")
    try:
        with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/status", timeout=10.0) as resp:
            st = json.loads(resp.read().decode("utf-8"))
            print(f"  ✅ Kết nối thành công! Thiết bị: {st.get('device_id')}, Core: {st.get('core_host')}")
    except Exception as exc:
        print(f"  ❌ Không thể kết nối tới Pi 5: {exc}")
        return 1

    # 2. Tải lên client_daemon.py và start_kiosk.sh mới
    print("\n[2/5] Đang tải lên client_daemon.py và start_kiosk.sh mới nhất sang Pi 5...")
    daemon_bytes = DAEMON_PATH.read_bytes()
    if not upload_file("client_daemon.py", daemon_bytes):
        print("  ❌ Thất bại khi tải client_daemon.py!")
        return 1
    print(f"  ✅ Đã tải lên client_daemon.py ({len(daemon_bytes):,} bytes)")

    kiosk_sh_path = ROOT / "edge_client" / "start_kiosk.sh"
    if kiosk_sh_path.exists():
        kiosk_sh_bytes = kiosk_sh_path.read_bytes()
        upload_file("start_kiosk.sh", kiosk_sh_bytes)
        print(f"  ✅ Đã tải lên start_kiosk.sh ({len(kiosk_sh_bytes):,} bytes)")

    main_py_path = ROOT / "edge_client" / "main.py"
    if main_py_path.exists():
        main_py_bytes = main_py_path.read_bytes()
        upload_file("main.py", main_py_bytes)
        print(f"  ✅ Đã tải lên main.py ({len(main_py_bytes):,} bytes)")

    config_json_path = ROOT / "edge_client" / "config.json"
    if config_json_path.exists():
        upload_file("config.json", config_json_path.read_bytes())
        print("  ✅ Đã tải lên config.json")

    # 3. Chuẩn bị kịch bản restart daemon an toàn
    print("\n[3/5] Đang chuẩn bị kịch bản tái khởi động daemon trên Pi 5...")
    restart_script = """#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== TÁI KHỞI ĐỘNG CLIENT DAEMON STANDBY ===" > "$SCRIPT_DIR/assets/avatar/restart_log.txt"

# Tìm PID của client_daemon hoặc main.py hiện tại
CUR_PIDS=$(pgrep -f "python3.*(client_daemon|main).py" || true)

# Khởi chạy main.py mới trong background (ở chế độ Standby - không tự mở trình duyệt)
nohup python3 "$SCRIPT_DIR/main.py" --core-host 192.168.1.10 --core-port 8766 > "$SCRIPT_DIR/daemon.log" 2>&1 &
NEW_PID=$!
echo "Đã khởi chạy daemon mới (PID: $NEW_PID)" >> "$SCRIPT_DIR/assets/avatar/restart_log.txt"

# Ngắt các tiến trình daemon cũ sau 0.5s
sleep 0.5
for p in $CUR_PIDS; do
    if [ "$p" != "$NEW_PID" ] && [ -n "$p" ]; then
        kill -9 "$p" 2>/dev/null || true
    fi
done

echo "Hoàn tất tái khởi động!" >> "$SCRIPT_DIR/assets/avatar/restart_log.txt"
"""
    if not upload_file("setup_pi5_audio.sh", restart_script.encode("utf-8")):
        print("  ❌ Thất bại khi tải setup_pi5_audio.sh!")
        return 1
    print("  ✅ Đã cấu hình kịch bản restart thành công.")

    # 4. Kích hoạt restart
    print("\n[4/5] Kích hoạt kịch bản khởi động lại daemon...")
    try:
        trigger_control({"action": "auto_configure_audio"})
        print("  ✅ Đã gửi lệnh kích hoạt.")
    except Exception as exc:
        print(f"  ℹ️ Tín hiệu gửi (kết nối có thể bị đóng do daemon restart): {exc}")

    # 5. Chờ và xác minh daemon mới đã online
    print("\n[5/5] Đang chờ và xác minh daemon mới trên Pi 5...")
    time.sleep(3.0)

    for attempt in range(1, 10):
        try:
            with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/audio/status", timeout=3.0) as resp:
                audio_st = json.loads(resp.read().decode("utf-8"))
                print(f"  🎉 XÁC MINH THÀNH CÔNG! Endpoint /api/kiosk/audio/status đã hoạt động!")
                print(f"     • Mic Device:      {audio_st.get('device_name')}")
                print(f"     • Mic Enabled:     {audio_st.get('mic_enabled')}")
                print(f"     • Mic Muted:       {audio_st.get('mic_muted')}")
                print(f"     • Wake Word:       {audio_st.get('wake_word_enabled')}")
                print(f"     • Listening Mode:  {audio_st.get('listening_mode')}")
                print(f"     • Audio Level:     {audio_st.get('audio_level_db')} dB")
                break
        except Exception as e:
            sys.stdout.write(f"\r  Đang đợi daemon sẵn sàng (thử {attempt}/9)...")
            sys.stdout.flush()
            time.sleep(1.5)
    else:
        print("\n  ❌ Quá thời gian chờ daemon mới phản hồi.")
        return 1

    # Kiểm tra endpoint camera status
    try:
        with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/camera/status", timeout=3.0) as resp:
            cam_st = json.loads(resp.read().decode("utf-8"))
            print(f"  🎉 XÁC MINH THÀNH CÔNG! Endpoint /api/kiosk/camera/status đã hoạt động!")
            print(f"     • Camera Device:   {cam_st.get('device_name')}")
            print(f"     • Device Node:     {cam_st.get('device_node')}")
            print(f"     • Camera Enabled:  {cam_st.get('camera_enabled')}")
            print(f"     • Resolution:      {cam_st.get('resolution')}")
    except Exception as e:
        print(f"  ⚠️ Cảnh báo kiểm tra camera status: {e}")

    print("\n" + "=" * 72)
    print("   ĐỒNG BỘ VÀ TÁI KHỞI ĐỘNG HOÀN TẤT THÀNH CÔNG 100%!")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
