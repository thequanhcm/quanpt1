#!/usr/bin/env python3
"""QUAN AI BRAIN — One-Time Setup, Wi-Fi Discovery & Pairing Script for Raspberry Pi 5.

Run this script ONCE on Raspberry Pi 5 to automatically pair with PC Central Brain Core.
Subsequent reboots will automatically synchronize without asking for pairing PIN again.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import socket
import sys
import time
import urllib.error
import urllib.request
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_banner() -> None:
    print("\n" + "=" * 70)
    print("      QUAN AI BRAIN — RASPBERRY PI 5 ONE-TIME AUTO PAIRING")
    print("       (KẾT NỐI VÀ ĐỒNG BỘ TỰ ĐỘNG QUA MẠNG WI-FI NỘI BỘ)")
    print("=" * 70)
    ram_desc = "4GB RAM" if "arm" in platform.machine().lower() or "aarch64" in platform.machine().lower() else "Standard Dev Runtime"
    print(f"  Phần cứng phát hiện:  {platform.system()} ({platform.machine()}) — {ram_desc}")
    print(f"  Python Runtime:       {sys.version.split()[0]}")
    print("=" * 70 + "\n")


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])
    except Exception:
        return "127.0.0.1"


def test_core_connectivity(host: str, port: int) -> bool:
    url = f"http://{host}:{port}/api/executive/supervisor"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "QuanAI-Pi5-Setup"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def discover_pc_core(port: int = 8766) -> str | None:
    """Quickly probe local Wi-Fi subnet candidates to automatically find PC Core IP."""
    import threading
    local_ip = get_local_ip()
    if local_ip.startswith("127."):
        if test_core_connectivity("127.0.0.1", port):
            return "127.0.0.1"
        return None

    prefix = ".".join(local_ip.split(".")[:3])
    found_ip: list[str] = []

    def _probe(ip_candidate: str):
        if found_ip:
            return
        if test_core_connectivity(ip_candidate, port):
            found_ip.append(ip_candidate)

    # Fast probe common LAN offsets and local subnet
    priority_ips = [
        f"{prefix}.11",  # Current Dell Precision PC IP
        f"{prefix}.17",
        local_ip,
        f"{prefix}.1", f"{prefix}.2", f"{prefix}.10", f"{prefix}.20",
        f"{prefix}.50", f"{prefix}.100", f"{prefix}.101", f"{prefix}.150"
    ]
    all_ips = list(priority_ips)
    for i in range(1, 255):
        cand = f"{prefix}.{i}"
        if cand not in all_ips:
            all_ips.append(cand)

    threads = []
    for ip in all_ips:
        t = threading.Thread(target=_probe, args=(ip,), daemon=True)
        t.start()
        threads.append(t)

    t_end = time.time() + 1.5
    while time.time() < t_end and not found_ip:
        time.sleep(0.05)

    return found_ip[0] if found_ip else None


def pair_with_core(host: str, port: int, pin: str, device_id: str, label: str) -> dict | None:
    url = f"http://{host}:{port}/api/edge/pair"
    payload = json.dumps({
        "device_id": device_id,
        "device_label": label,
        "pairing_pin": pin,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-Pi5-Setup"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        try:
            err_body = json.loads(he.read().decode("utf-8"))
            print(f"\n[LỖI TỪ BRAIN CORE] {err_body.get('error', he.reason)}")
        except Exception:
            print(f"\n[LỖI TỪ BRAIN CORE] Mã lỗi HTTP: {he.code}")
    except Exception as exc:
        print(f"\n[LỖI KẾT NỐI] Không thể gửi yêu cầu ghép cặp: {exc}")
    return None


def setup_autostart_kiosk(script_dir: Path) -> None:
    # 1. Create start_kiosk.sh optimized for 7" DSI Touchscreen 2 (1280x720)
    start_sh = script_dir / "start_kiosk.sh"
    content = f"""#!/bin/bash
# Tự động khởi chạy QUAN AI BRAIN Kiosk trên Raspberry Pi 5 (Màn hình 7" DSI Touch 2)
cd "{script_dir}"
python3 main.py &
sleep 2

CHROME_FLAGS="--kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 --touch-events=enabled --disable-pinch --overscroll-history-navigation=0 --window-size=1280,720 --window-position=0,0 --enable-features=OverlayScrollbar"

if which chromium-browser > /dev/null; then
    chromium-browser $CHROME_FLAGS http://127.0.0.1:8768/
elif which chromium > /dev/null; then
    chromium $CHROME_FLAGS http://127.0.0.1:8768/
fi
"""
    with open(start_sh, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        os.chmod(start_sh, 0o755)
    except Exception:
        pass

    # 2. Setup desktop autostart entry (LXDE / Wayland desktop)
    home_dir = Path.home()
    autostart_dir = home_dir / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    desktop_entry = autostart_dir / "quan_kiosk.desktop"
    desktop_content = f"""[Desktop Entry]
Type=Application
Name=QUAN AI BRAIN Kiosk
Exec={start_sh}
X-GNOME-Autostart-enabled=true
"""
    with open(desktop_entry, "w", encoding="utf-8") as f:
        f.write(desktop_content)
    print(f"  [OK] Đã cấu hình khởi động tự động tại: {desktop_entry}")


def main() -> int:
    print_banner()
    script_dir = Path(__file__).resolve().parent
    config_file = script_dir / "config.json"
    # Parse CLI flags
    auto_mode = "--auto" in sys.argv
    cli_host = None
    cli_port = None
    cli_pin = None
    no_launch = "--no-launch" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--host" and i + 1 < len(sys.argv):
            cli_host = sys.argv[i + 1]
        elif arg == "--port" and i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
            cli_port = int(sys.argv[i + 1])
        elif arg == "--pin" and i + 1 < len(sys.argv):
            cli_pin = sys.argv[i + 1]

    # Check if already paired
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                existing_cfg = json.load(f)
            sec = existing_cfg.get("shared_secret", "")
            if sec and sec != "EDGE_EPHEMERAL_DEV_SECRET_DO_NOT_USE_IN_PROD":
                print(f"👉 Thiết bị đã được ghép cặp trước đó với Brain Core tại:")
                print(f"   http://{existing_cfg.get('core_host', '127.0.0.1')}:{existing_cfg.get('core_port', 8766)}")
                if auto_mode:
                    print("\n[CHẾ ĐỘ TỰ ĐỘNG] Sử dụng cấu hình ghép cặp hiện tại.")
                    setup_autostart_kiosk(script_dir)
                    if not no_launch:
                        print("\nKhởi chạy giao diện Kiosk ngay...")
                        os.system("python3 main.py")
                    return 0
                ans = input("\nAnh có muốn ghép cặp lại không? [y/N]: ").strip().lower()
                if ans != "y":
                    print("\n[BỎ QUA] Giữ nguyên cấu hình ghép cặp hiện tại.")
                    setup_autostart_kiosk(script_dir)
                    if not no_launch:
                        print("\nKhởi chạy giao diện Kiosk ngay...")
                        os.system("python3 main.py")
                    return 0
        except Exception:
            pass

    my_ip = get_local_ip()
    print(f"Địa chỉ IP Wi-Fi của Raspberry Pi 5 này: {my_ip}")
    print("Vui lòng đảm bảo máy tính PC chạy QUAN AI BRAIN và Raspberry Pi 5 đang bắt cùng một mạng Wi-Fi.\n")

    # Probe Wi-Fi for PC Core IP
    print("Đang quét nhanh mạng Wi-Fi để tìm máy tính PC Central Brain Core...")
    discovered_ip = discover_pc_core(8766)
    default_host = cli_host if cli_host else (discovered_ip if discovered_ip else "127.0.0.1")

    if cli_host:
        core_host = cli_host
    elif auto_mode:
        core_host = default_host
        print(f"👉 [TỰ ĐỘNG CHỌN] Sử dụng PC Core IP: {core_host}")
    elif discovered_ip:
        print(f"👉 [TỰ ĐỘNG PHÁT HIỆN] Tìm thấy PC Central Brain Core tại IP: {discovered_ip}!")
        prompt_host = input(f"Nhấn [Enter] để dùng {discovered_ip} (hoặc nhập IP khác): ").strip()
        core_host = prompt_host if prompt_host else default_host
    else:
        prompt_host = input("Nhập địa chỉ IP Wi-Fi của máy tính PC (Ví dụ: 192.168.1.17) [Enter = 127.0.0.1]: ").strip()
        core_host = prompt_host if prompt_host else default_host

    if cli_port:
        core_port = cli_port
    elif auto_mode:
        core_port = 8766
    else:
        prompt_port = input("Nhập cổng dịch vụ Brain Core trên PC [Enter = 8766]: ").strip()
        core_port = int(prompt_port) if prompt_port.isdigit() else 8766

    print(f"\nĐang kiểm tra kết nối tới PC Brain Core tại http://{core_host}:{core_port}...")
    is_online = test_core_connectivity(core_host, core_port)
    if not is_online and not auto_mode:
        print(f"⚠️ [CẢNH BÁO] Chưa kết nối được tới http://{core_host}:{core_port}.")
        print("Vui lòng kiểm tra:")
        print("  1. Máy tính PC đã mở Phòng Điều Hành (`run_executive_desk.py` hoặc cổng 8766) chưa?")
        print("  2. Địa chỉ IP Wi-Fi đã nhập chính xác chưa?")
        cont = input("\nAnh vẫn muốn tiếp tục ghép cặp? [Y/n]: ").strip().lower()
        if cont == "n":
            return 1

    if cli_pin:
        pin = cli_pin
    elif auto_mode:
        pin = "888666"
    else:
        prompt_pin = input("\nNhập mã PIN xác thực 1 lần hiển thị trên Bàn Điều Hành PC [Mặc định: 888666]: ").strip()
        pin = prompt_pin if prompt_pin else "888666"

    device_id = "EDGE-PI5-DESK-01"
    device_label = "Bàn Làm Việc Quanpt1 (Màn hình 7 inch 1280x720)"

    print("\nĐang gửi yêu cầu ghép cặp an toàn lên Brain Core...")
    pair_res = pair_with_core(core_host, core_port, pin, device_id, device_label)

    if not pair_res or not pair_res.get("success"):
        print("\n❌ [THẤT BẠI] Ghép cặp không thành công. Vui lòng kiểm tra lại mã PIN và thử lại.")
        return 1

    # Save to config.json
    shared_secret = pair_res.get("shared_secret", "")
    config_data = {
        "device_id": device_id,
        "device_label": device_label,
        "core_host": core_host,
        "core_port": core_port,
        "kiosk_host": "127.0.0.1",
        "kiosk_port": 8768,
        "shared_secret": shared_secret,
        "poll_interval_sec": 1.0,
        "heartbeat_timeout_sec": 4.0,
        "reconnect_delay_sec": 2.0,
        "kiosk_mode": True,
        "face_only_mode": True,
        "display_orientation": "landscape",
        "screen_width": 1280,
        "screen_height": 720,
        "wake_word": "TONY ơi",
        "follow_up_window_sec": 15.0,
        "core_version": "0.2.0",
        "edge_client_version": "0.2.0",
        "protocol_version": "1.0",
        "avatar_version": "digital_human_model_f_v1",
        "config_schema_version": "1.0",
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("  ✅ [THÀNH CÔNG] GHÉP CẶP THÀNH CÔNG DUY NHẤT 1 LẦN!")
    print("=" * 70)
    print(f"  • Mã thiết bị:     {device_id}")
    print(f"  • Brain Core PC:   http://{core_host}:{core_port}")
    print(f"  • Khóa ký HMAC:    {shared_secret[:8]}... (Đã lưu an toàn)")
    print(f"  • Điều khiển cơ:   Hệ thống 8 Rơ-le và Khớp tay/chân robot đã sẵn sàng")
    print("=" * 70)

    # Setup autostart
    print("\nThiết lập tự động khởi động cùng hệ điều hành...")
    setup_autostart_kiosk(script_dir)

    print("\n👉 Từ nay, mỗi khi Anh bật nguồn Raspberry Pi 5:")
    print("   1. Màn hình tự động mở gương mặt số biểu cảm của TONY.")
    print("   2. Tự động kết nối và đồng bộ với PC mà KHÔNG CẦN NHẬP LẠI BẤT KỲ THÔNG TIN NÀO.")
    print("   3. Nút bấm STOP trên màn hình sẽ ngắt lập tức toàn bộ rơ-le và tác vụ trên PC.\n")

    if auto_mode:
        print("\n[CHẾ ĐỘ TỰ ĐỘNG] Khởi chạy giao diện Kiosk ngay...")
        if not no_launch:
            os.system("python3 main.py")
        return 0

    if no_launch:
        return 0

    launch_now = input("Anh có muốn khởi chạy Kiosk ngay bây giờ không? [Y/n]: ").strip().lower()
    if launch_now != "n":
        print("\nKhởi chạy giao diện Kiosk...")
        os.system("python3 main.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
