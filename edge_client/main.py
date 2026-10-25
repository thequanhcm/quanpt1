"""Entrypoint CLI for QUAN AI BRAIN — Raspberry Pi 5 Edge Client.

Usage:
    python -m edge_client.main
    python -m edge_client.main --check-health
    python -m edge_client.main --core-host 192.168.1.50 --core-port 8766
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_PKG_PARENT = Path(__file__).resolve().parent.parent
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))
_PKG_SELF = Path(__file__).resolve().parent
if str(_PKG_SELF) not in sys.path:
    sys.path.insert(0, str(_PKG_SELF))

try:
    from edge_client.client_daemon import EdgeClientDaemon
    from edge_client.config import EdgeConfig
except ImportError:
    from client_daemon import EdgeClientDaemon  # type: ignore
    from config import EdgeConfig  # type: ignore


def launch_kiosk_browser(url: str = "http://127.0.0.1:8768/") -> None:
    """Tự động mở trình duyệt Chromium Kiosk toàn màn hình (1280x720) trên Raspberry Pi 5."""
    import os
    import shutil
    import subprocess
    import threading

    def _spawn() -> None:
        time.sleep(1.2)
        env = os.environ.copy()
        if "DISPLAY" not in env and "WAYLAND_DISPLAY" not in env:
            env["DISPLAY"] = ":0"

        flags = [
            "--kiosk",
            "--noerrdialogs",
            "--disable-infobars",
            "--check-for-update-interval=31536000",
            "--touch-events=enabled",
            "--disable-pinch",
            "--overscroll-history-navigation=0",
            "--window-size=1280,720",
            "--window-position=0,0",
            "--enable-features=OverlayScrollbar",
            "--autoplay-policy=no-user-gesture-required",
        ]

        for bin_name in ["chromium-browser", "chromium", "google-chrome", "firefox", "x-www-browser"]:
            bin_path = shutil.which(bin_name)
            if bin_path:
                try:
                    cmd = [bin_path] + flags + [url]
                    subprocess.Popen(
                        cmd,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    print(f"  [Giao Diện Kiosk] Đã tự động mở {bin_name} toàn màn hình trên màn 7\" DSI!")
                    return
                except Exception as e:
                    print(f"  [Giao Diện Kiosk] Cảnh báo khởi chạy {bin_name}: {e}")

    threading.Thread(target=_spawn, daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="QUAN AI BRAIN — Raspberry Pi 5 Edge Kiosk Client",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=str(Path(__file__).parent / "config.json"),
        help="Path to configuration JSON file",
    )
    parser.add_argument(
        "--core-host",
        type=str,
        default=None,
        help="Override Central Brain Core IP / Hostname",
    )
    parser.add_argument(
        "--core-port",
        type=int,
        default=None,
        help="Override Central Brain Core port (default 8766)",
    )
    parser.add_argument(
        "--kiosk-port",
        type=int,
        default=None,
        help="Override local kiosk UI port (default 8768)",
    )
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Probe connection to Central Brain Core once and exit",
    )
    parser.add_argument(
        "--launch-browser",
        action="store_true",
        default=False,
        help="Mở trình duyệt Chromium Kiosk ngay khi khởi động (Mặc định: TẮT để chạy chế độ chờ Standby)",
    )

    args = parser.parse_args()

    # Load configuration
    config = EdgeConfig.load_from_file(args.config)
    if args.core_host:
        config.core_host = args.core_host
    if args.core_port:
        config.core_port = args.core_port
    if args.kiosk_port:
        config.kiosk_port = args.kiosk_port

    daemon = EdgeClientDaemon(config)

    # Health check mode
    if args.check_health:
        print(f"Kiểm tra kết nối đến PC Brain Core ({config.core_base_url})...")
        ok = daemon.check_core_connection()
        if ok:
            print(f"[THÀNH CÔNG] Brain Core ONLINE! Model: {daemon.state.active_model}")
            return 0
        else:
            print(f"[THẤT BẠI] Không thể kết nối Brain Core tại {config.core_base_url}.")
            return 1

    print("\n" + "=" * 66)
    print("      QUAN AI BRAIN — RASPBERRY PI 5 EDGE KIOSK CLIENT")
    print("=" * 66)
    print(f"  Thiết bị ID:       {config.device_id}")
    print(f"  Nhãn hiển thị:     {config.device_label}")
    print(f"  Brain Core PC:     {config.core_base_url}")
    print(f"  Giao diện Kiosk:   {config.kiosk_url}")
    print(f"  Cơ chế xác thực:   Anti-Replay HMAC-SHA256")
    print("=" * 66 + "\n")

    daemon.start()
    print(f"[Kiosk Sẵn Sàng] Đang phục vụ giao diện tại {config.kiosk_url}")
    if args.launch_browser:
        launch_kiosk_browser(config.kiosk_url)
    else:
        print("[Embodiment Standby] Chế độ chờ (Standby) kích hoạt — Giao diện hình thể 7\" DSI sẽ chỉ bật khi Anh Quân thao tác từ Web Cockpit.")
    print("[Vận hành] Nhấn Ctrl+C để dừng Edge Client an toàn.\n")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[Đang dừng] Đóng Edge Client an toàn...")
        daemon.stop()
        print("[Hoàn tất] Edge Client đã tắt.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
