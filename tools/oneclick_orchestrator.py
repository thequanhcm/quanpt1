"""QUAN AI BRAIN — 1-Click Master System Orchestrator.

Kích hoạt toàn diện hệ thống bằng 1 click:
1. Kích hoạt Ollama LLM Engine (phục vụ suy nghĩ & lập kế hoạch nhận thức).
2. Khởi động PC Core Executive Cockpit Daemon (Port 8766).
3. Kiểm tra kết nối, thiết lập âm thanh và đồng bộ hình thể sang Raspberry Pi 5.
4. Tự động mở giao diện điều hành Web Cockpit trên trình duyệt của Anh Quân.
5. Duy trì bàn điều khiển giám sát thời gian thực.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

OLLAMA_HOST = "127.0.0.1:11434"
CORE_PORT = 8766
PI5_IP = "192.168.1.21"
PI5_PORT = 8768


def print_banner() -> None:
    print("=" * 76)
    print("      QUAN AI BRAIN — TRỢ LÝ ĐIỀU HÀNH SỐ (QUANPT1 DIGITAL REPLICA)")
    print("          KÍCH HOẠT HỆ THỐNG TOÀN DIỆN BẰNG 1-CLICK (ONE-CLICK LAUNCHER)")
    print("=" * 76)
    print(f"  Thư mục gốc: {ROOT}")
    print(f"  Thời gian:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 76)
    print()


def check_url(url: str, timeout: float = 1.5) -> tuple[bool, dict | None]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "QuanAI-Orchestrator/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                try:
                    return True, json.loads(raw.decode("utf-8", errors="replace"))
                except Exception:
                    return True, None
            return True, None
    except Exception:
        return False, None


def ensure_ollama() -> bool:
    print("[1/4] Kiểm tra lõi suy luận Ollama LLM (Port 11434)...")
    ok, data = check_url(f"http://{OLLAMA_HOST}/api/tags", timeout=1.5)
    if ok:
        models = [m.get("name") for m in (data.get("models", []) if data else [])]
        print(f"  ✅ Ollama đang hoạt động sẵn sàng. Số models khả dụng: {len(models)}")
        if models:
            print(f"     Mô hình tiêu biểu: {', '.join(models[:3])}")
        return True

    print("  [i] Ollama chưa chạy, đang tự động kích hoạt dịch vụ...")
    ollama_app = Path(r"E:\AI\Ollama\ollama app.exe")
    ollama_cli = Path(r"E:\AI\Ollama\ollama.exe")

    if ollama_app.exists():
        subprocess.Popen([str(ollama_app)], cwd=str(ollama_app.parent), close_fds=True)
    elif ollama_cli.exists():
        subprocess.Popen([str(ollama_cli), "serve"], cwd=str(ollama_cli.parent), close_fds=True)
    else:
        # Try system path
        try:
            subprocess.Popen(["ollama", "serve"], close_fds=True)
        except Exception:
            print("  ⚠️ Không tìm thấy đường dẫn Ollama tại E:\\AI\\Ollama. Tiếp tục chế độ CPU Fallback.")
            return False

    # Wait for Ollama to become ready
    for _ in range(12):
        time.sleep(1.0)
        ok, data = check_url(f"http://{OLLAMA_HOST}/api/tags", timeout=1.0)
        if ok:
            models = [m.get("name") for m in (data.get("models", []) if data else [])]
            print(f"  ✅ Đã kích hoạt Ollama thành công! Models: {len(models)}")
            return True

    print("  ⚠️ Ollama khởi động chậm hơn dự kiến, hệ thống sẽ tự động dùng mô hình dự phòng.")
    return False


def ensure_core_daemon() -> bool:
    print("\n[2/4] Kiểm tra máy chủ điều hành PC Core Desk (Port 8766)...")
    ok, _ = check_url(f"http://127.0.0.1:{CORE_PORT}/api/status", timeout=1.2)
    if ok:
        print(f"  ✅ PC Core Daemon đang trực tuyến tại http://127.0.0.1:{CORE_PORT}/")
        return True

    print(f"  [i] Đang khởi động PC Core Executive Daemon trên cổng {CORE_PORT}...")
    run_script = ROOT / "run_executive_desk.py"
    
    # Launch detached in background with creationflags
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(
        [PYTHON, str(run_script)],
        cwd=str(ROOT),
        creationflags=creationflags,
        close_fds=True,
    )

    for _ in range(15):
        time.sleep(0.5)
        ok, _ = check_url(f"http://127.0.0.1:{CORE_PORT}/api/status", timeout=1.0)
        if ok:
            print(f"  ✅ PC Core Daemon đã khởi động thành công tại http://127.0.0.1:{CORE_PORT}/")
            return True

    print("  ❌ Không thể xác nhận PC Core Daemon sau 7.5 giây.")
    return False


def ensure_pi5_link() -> bool:
    print(f"\n[3/4] Kiểm tra kết nối & giao tiếp hình thể Raspberry Pi 5 (http://{PI5_IP}:{PI5_PORT}/)...")
    ok, data = check_url(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/status", timeout=2.5)
    if not ok:
        print(f"  ⚠️ Raspberry Pi 5 chưa bật nguồn hoặc chưa vào cùng mạng Wi-Fi ({PI5_IP}).")
        print("     Tiến trình nền đang giám sát... Ngay khi Pi 5 bật nguồn, hệ thống sẽ tự động chào và kiểm tra loa/mic/camera!")
        start_pi5_background_watcher()
        return False

    dev_id = data.get("device_id", "N/A") if data else "EDGE-PI5-DESK-01"
    cur_state = data.get("avatar_state", "IDLE") if data else "IDLE"
    print(f"  ✅ ĐÃ KẾT NỐI RASPBERRY PI 5 THÀNH CÔNG!")
    print(f"     Thiết bị:    {dev_id}")
    print(f"     Trạng thái:  {cur_state}")

    # Đồng bộ tài sản mới nhất & thiết lập âm thanh
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{CORE_PORT}/api/executive/edge/files/sync-all",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            sync_res = json.loads(resp.read().decode("utf-8"))
            if sync_res.get("success"):
                print(f"  ✅ Đã đồng bộ {sync_res.get('synced_count', 0)} tài sản hình thể Digital Human V2 sang Pi 5.")
    except Exception as e:
        print(f"  [i] Tự động đồng bộ tài sản: {e}")

    # Đặt trạng thái về IDLE chuẩn nụ cười tự nhiên (loại bỏ hoàn toàn chồng hình)
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{CORE_PORT}/api/executive/edge/control",
            data=json.dumps({"action": "set_expression", "state": "IDLE"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3.0)
        print("  ✅ Đã thiết lập hình thể Pi 5 về trạng thái chuẩn IDLE (nụ cười tự nhiên).")
    except Exception:
        pass

    # Kích hoạt chu trình phản hồi chào & tự kiểm tra mic/camera qua loa Pi 5
    run_pi5_greeting_and_selftest()
    return True


def run_pi5_greeting_and_selftest() -> bool:
    print("\n  📢 [Chu Trình Khởi Động Pi 5] Đang kích hoạt loa phát lời chào & tự kiểm tra phần cứng...")
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{CORE_PORT}/api/executive/edge/startup-sequence",
            data=json.dumps({"greeting": "Chào anh ạ, rất vui được gặp anh."}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            st_res = json.loads(resp.read().decode("utf-8"))
            if st_res.get("success"):
                print("  🔊 [Loa Pi 5]: 'Chào anh ạ, rất vui được gặp anh.'")
                mic_tag = "✅ TỐT" if st_res.get("mic_ok") else "⚠️ CẦN KIỂM TRA"
                cam_tag = "✅ TỐT" if st_res.get("camera_ok") else "⚠️ CHƯA NHẬN"
                print(f"     • Kết quả kiểm tra Micro:  {mic_tag}")
                print(f"     • Kết quả kiểm tra Camera: {cam_tag}")
                print(f"  📢 [Loa Pi 5 Báo Cáo]: \"{st_res.get('report_text')}\"")
                return True
            else:
                print(f"  ℹ️ Pi 5 phản hồi: {st_res.get('message', 'Chưa sẵn sàng')}")
                return False
    except Exception as exc:
        print(f"  [i] Gửi chu trình chào Pi 5: {exc}")
        return False


def start_pi5_background_watcher():
    """Giám sát nền: Nếu Pi 5 khởi động sau PC, tự động bắt tay chào & test mic/camera ngay khi online."""
    import threading
    def _watcher():
        for _ in range(60):
            time.sleep(2.0)
            ok, _ = check_url(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/status", timeout=1.5)
            if ok:
                run_pi5_greeting_and_selftest()
                break
    t = threading.Thread(target=_watcher, daemon=True)
    t.start()


def open_cockpit_ui() -> None:
    url = f"http://127.0.0.1:{CORE_PORT}/"
    print(f"\n[4/4] Mở giao diện điều hành PC Executive Cockpit: {url}...")
    try:
        webbrowser.open(url)
        print("  ✅ Đã mở phòng điều hành trực quan trên trình duyệt mặc định.")
    except Exception as exc:
        print(f"  ⚠️ Không thể tự mở trình duyệt ({exc}). Anh vui lòng mở thủ công: {url}")


def interactive_dashboard() -> None:
    print()
    print("=" * 76)
    print("         QUAN AI BRAIN — BÀN GIÁM SÁT ĐIỀU HÀNH TRỰC TUYẾN")
    print("=" * 76)
    print("  [O] Mở lại Giao diện Điều hành Web (Cockpit Browser)")
    print("  [G] Phát loa 'Chào Anh Quân' & Tự kiểm tra Mic/Camera Loa Pi 5")
    print("  [S] Đồng bộ toàn bộ Hình thể Avatar V2 sang Pi 5")
    print("  [T] Thử nghiệm giọng nói 'Hi TONY' sang Loa Pi 5")
    print("  [R] Đặt lại biểu cảm Pi 5 về IDLE tự nhiên")
    print("  [Q] Thoát bảng điều khiển (Server tiếp tục chạy nền)")
    print("=" * 76)

    while True:
        try:
            cmd = input("\nNhập phím tắt (O / G / S / T / R / Q): ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            break

        if cmd == "O":
            webbrowser.open(f"http://127.0.0.1:{CORE_PORT}/")
            print("  -> Đã mở Cockpit trên trình duyệt.")
        elif cmd == "G":
            run_pi5_greeting_and_selftest()
        elif cmd == "S":
            print("  -> Đang phát lệnh đồng bộ hình thể sang Pi 5...")
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{CORE_PORT}/api/executive/edge/files/sync-all",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    print("  -> Kết quả:", resp.read().decode("utf-8", errors="replace"))
            except Exception as exc:
                print(f"  -> Lỗi: {exc}")
        elif cmd == "T":
            print("  -> Đang gửi lệnh chào giọng nữ tiếng Việt sang Loa Pi 5...")
            try:
                sync_tool = ROOT / "tools" / "sync_pi5_complete.py"
                subprocess.run([PYTHON, str(sync_tool)], check=False)
            except Exception as exc:
                print(f"  -> Lỗi phát âm thanh: {exc}")
        elif cmd == "R":
            print("  -> Đang đặt lại trạng thái Pi 5 về IDLE...")
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{CORE_PORT}/api/executive/edge/control",
                    data=json.dumps({"action": "set_expression", "state": "IDLE"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    print("  -> Đã đưa avatar về nụ cười tự nhiên IDLE.")
            except Exception as exc:
                print(f"  -> Lỗi: {exc}")
        elif cmd == "Q":
            print("\n  Cảm ơn Anh Quân! Toàn bộ dịch vụ lõi vẫn tiếp tục hoạt động phục vụ Anh.")
            break


def main() -> int:
    print_banner()
    ensure_ollama()
    ensure_core_daemon()
    ensure_pi5_link()
    open_cockpit_ui()
    interactive_dashboard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
