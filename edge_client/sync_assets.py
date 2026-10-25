"""QUAN AI BRAIN — 1-Click Asset & Model F Synchronizer for Raspberry Pi 5.

Synchronizes all 20 Model F CGI Avatar portraits, lip-sync mouth frames, eye expressions,
and sound effects from Central Brain PC Core (192.168.1.11:8766) to Raspberry Pi 5.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_assets_dir() -> Path:
    script_dir = Path(__file__).resolve().parent
    target_dir = script_dir / "assets" / "avatar"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def get_core_url() -> str:
    # 1. Environment variable
    env_url = os.environ.get("QUAN_CORE_URL")
    if env_url:
        return env_url.rstrip("/")

    # 2. Check config.json in edge_client directory
    config_file = Path(__file__).resolve().parent / "config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            host = data.get("core_host", "192.168.1.11")
            port = data.get("core_port", 8766)
            return f"http://{host}:{port}"
        except Exception:
            pass

    # 3. Default LAN IP of Central Brain PC
    return "http://192.168.1.11:8766"


def sync_all_assets() -> int:
    target_dir = find_assets_dir()
    core_url = get_core_url()

    print(f"\n======================================================================")
    print(f"   QUAN AI BRAIN — ĐỒNG BỘ TÀI SẢN HÌNH THỂ SỐ MODEL F SANG PI 5")
    print(f"======================================================================")
    print(f"  PC Core URL:       {core_url}")
    print(f"  Thư mục lưu trữ:   {target_dir}")
    print(f"----------------------------------------------------------------------")

    # Step 1: Query PC Core for file list
    api_url = f"{core_url}/api/executive/edge/files"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "QuanAI-Pi5-SyncClient/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[LỖI] Không thể kết nối tới PC Core tại {api_url}: {exc}")
        print("  -> Vui lòng kiểm tra PC và Pi 5 đã kết nối cùng mạng Wi-Fi.")
        return 1

    files = data.get("local_files", [])
    if not files:
        print("[CẢNH BÁO] Không tìm thấy danh sách tệp tài sản trên PC Core.")
        return 1

    print(f"  -> Đã tìm thấy {len(files)} tệp tài sản trên PC Core. Bắt đầu tải...")

    synced_count = 0
    total_bytes = 0

    for idx, f in enumerate(files, 1):
        name = f.get("name")
        expected_size = f.get("size", 0)
        local_path = target_dir / name
        download_url = f"{core_url}/edge_client/assets/avatar/{name}"

        # Check if already exists with same size
        if local_path.exists() and local_path.stat().st_size == expected_size and expected_size > 0:
            print(f"  [{idx:02d}/{len(files):02d}] ✓ Đã có sẵn: {name:<26} ({expected_size/1024:.1f} KB)")
            synced_count += 1
            total_bytes += expected_size
            continue

        try:
            print(f"  [{idx:02d}/{len(files):02d}] ⬇ Đang tải:  {name:<26} ...", end="", flush=True)
            d_req = urllib.request.Request(download_url, headers={"User-Agent": "QuanAI-Pi5-SyncClient/1.0"})
            with urllib.request.urlopen(d_req, timeout=15.0) as d_resp:
                content = d_resp.read()
                local_path.write_bytes(content)
                print(f" Xong ({len(content)/1024:.1f} KB)")
                synced_count += 1
                total_bytes += len(content)
        except Exception as e:
            print(f" Thất bại ({e})")

    print(f"----------------------------------------------------------------------")
    print(f"  ✅ ĐÃ ĐỒNG BỘ HOÀN TẤT {synced_count}/{len(files)} TỆP ({total_bytes/1024/1024:.2f} MB)")

    # Step 2: Synchronize core client scripts
    script_dir = Path(__file__).resolve().parent
    core_scripts = [
        "avatar_engine.js",
        "wake_engine.js",
        "kiosk.html",
        "kiosk.js",
        "kiosk.css",
        "client_daemon.py",
        "setup_pi5_audio.sh",
        "start_kiosk.sh",
    ]
    print(f"\n  Đang đồng bộ các tệp mã nguồn giao diện cốt lõi...")
    for s_name in core_scripts:
        s_local = script_dir / s_name
        s_url = f"{core_url}/edge_client/{s_name}"
        try:
            s_req = urllib.request.Request(s_url, headers={"User-Agent": "QuanAI-Pi5-SyncClient/1.0"})
            with urllib.request.urlopen(s_req, timeout=10.0) as s_resp:
                s_content = s_resp.read()
                if not s_local.exists() or s_local.stat().st_size != len(s_content):
                    s_local.write_bytes(s_content)
                    if s_name.endswith(".sh"):
                        try:
                            os.chmod(s_local, 0o755)
                        except Exception:
                            pass
                    print(f"  ✓ Đã cập nhật mã nguồn: {s_name} ({len(s_content)/1024:.1f} KB)")
                else:
                    print(f"  ✓ Đã đúng phiên bản:   {s_name}")
        except Exception as e:
            print(f"  ! Không thể tải {s_name}: {e}")


    # Step 3: Trigger Kiosk UI reload if local daemon is running
    try:
        reload_req = urllib.request.Request(
            "http://127.0.0.1:8768/api/kiosk/control",
            data=json.dumps({"action": "reload_ui"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(reload_req, timeout=1.0) as r_resp:
            print("  ✓ Đã gửi lệnh làm mới giao diện Kiosk Pi 5 thành công!")
    except Exception:
        pass

    print(f"  Gương mặt Cô Trợ Lý Mẫu F đã sẵn sàng hiển thị toàn màn hình trên Pi 5!")
    print(f"======================================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(sync_all_assets())
