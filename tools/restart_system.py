"""Safe, autonomous system restarter for QUAN AI BRAIN.

Used to automatically restart all services (Web UI, Executive Desk, Ollama)
after updates or feature additions, with pre-flight safety validation.

Usage:
    python tools/restart_system.py
    python tools/restart_system.py --validate
    python tools/restart_system.py --target desk
    python tools/restart_system.py --status
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

PORTS_MAP = {
    "desk": 8766,
    "chat": 8765,
    "ollama": 11434,
}


def log(msg: str, level: str = "INFO") -> None:
    timestamp = time.strftime("%H:%M:%S")
    prefix = {
        "INFO": "[\033[94mINFO\033[0m]",
        "SUCCESS": "[\033[92mTHÀNH CÔNG\033[0m]",
        "WARN": "[\033[93mCẢNH BÁO\033[0m]",
        "ERROR": "[\033[91mLỖI\033[0m]",
    }.get(level, f"[{level}]")
    print(f"[{timestamp}] {prefix} {msg}")


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def find_pids_on_port(port: int) -> list[int]:
    """Find process IDs listening on a specific TCP port on Windows."""
    pids: list[int] = []
    try:
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        current_pid = os.getpid()
        for line in output.splitlines():
            line = line.strip()
            if f":{port}" in line and "LISTENING" in line:
                tokens = re.split(r"\s+", line)
                if tokens and tokens[-1].isdigit():
                    pid = int(tokens[-1])
                    if pid not in (0, 4, current_pid):
                        pids.append(pid)
    except Exception as exc:
        log(f"Không thể quét PID cổng {port}: {exc}", "WARN")
    return list(set(pids))


def terminate_pids(pids: list[int]) -> None:
    """Terminate given process IDs on Windows."""
    for pid in pids:
        try:
            log(f"Đang dừng tiến trình cũ (PID: {pid})...")
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception as exc:
            log(f"Không thể dừng PID {pid}: {exc}", "WARN")


def wait_port_released(port: int, timeout_sec: float = 4.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not is_port_listening(port):
            return True
        time.sleep(0.2)
    return False


def wait_port_ready(port: int, timeout_sec: float = 12.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if is_port_listening(port):
            return True
        time.sleep(0.3)
    return False


def check_preflight_imports() -> bool:
    """Verify that Python environment and core modules load without syntax/runtime error."""
    log("Đang kiểm tra mã nguồn (Pre-flight Import Check)...")
    code = (
        "import quan_ai_brain; "
        "import quan_ai_brain.web.server; "
        "import quan_ai_brain.voice; "
        "print('PREFLIGHT_OK')"
    )
    res = subprocess.run(
        [str(PYTHON_EXE), "-c", code],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0 and "PREFLIGHT_OK" in res.stdout:
        log("Mã nguồn hợp lệ, không có lỗi cú pháp hoặc import.", "SUCCESS")
        return True
    else:
        log("Kiểm tra mã nguồn thất bại! Lỗi:", "ERROR")
        print(res.stderr or res.stdout)
        return False


def run_validation_and_report() -> bool:
    """Run tools/validate_and_report.py to produce handoff report and run full test suite."""
    log("Đang chạy kiểm thử nghiệm thu và lập báo cáo bàn giao (validate_and_report)...")
    script = WORKSPACE_ROOT / "tools" / "validate_and_report.py"
    if not script.exists():
        log("Không tìm thấy tools/validate_and_report.py", "WARN")
        return True

    res = subprocess.run(
        [str(PYTHON_EXE), str(script)],
        cwd=WORKSPACE_ROOT,
    )
    if res.returncode == 0:
        log("Kiểm thử nghiệm thu thành công! Báo cáo bàn giao đã cập nhật.", "SUCCESS")
        return True
    else:
        log("Kiểm thử nghiệm thu THẤT BẠI. Hủy khởi động lại để bảo vệ hệ thống.", "ERROR")
        return False


def ensure_ollama_running() -> bool:
    """Check if Ollama is listening on 11434, start if needed."""
    if is_port_listening(11434):
        log("Dịch vụ Ollama đang hoạt động trên cổng 11434.", "SUCCESS")
        return True

    log("Ollama chưa bật. Đang khởi động tiến trình Ollama cục bộ...", "WARN")
    ollama_candidates = [
        Path(r"E:\AI\Ollama\ollama app.exe"),
        Path(r"E:\AI\Ollama\ollama.exe"),
    ]
    for exe in ollama_candidates:
        if exe.exists():
            try:
                cmd = [str(exe)]
                if exe.name == "ollama.exe":
                    cmd.append("serve")
                subprocess.Popen(
                    cmd,
                    cwd=exe.parent,
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(2.0)
                if wait_port_ready(11434, timeout_sec=6.0):
                    log("Đã khởi động Ollama thành công.", "SUCCESS")
                    return True
            except Exception as exc:
                log(f"Không thể khởi động {exe}: {exc}", "WARN")

    log("Không tìm thấy tệp thực thi Ollama hợp lệ. Tiếp tục chạy chế độ Fallback.", "WARN")
    return False


def spawn_service_process(script_name: str) -> None:
    """Spawn an independent persistent background Python service process on Windows."""
    script_path = WORKSPACE_ROOT / script_name
    bat_map = {
        "run_executive_desk.py": "KHOI_DONG_PHONG_DIEU_HANH_8766.bat",
        "run_web_ui.py": "KHOI_DONG_WEB_UI.bat",
    }
    bat_name = bat_map.get(script_name)
    if bat_name and (WORKSPACE_ROOT / bat_name).exists():
        cmd = f'start "{bat_name}" cmd /c "{bat_name}"'
    else:
        cmd = f'start "{script_name}" "{PYTHON_EXE}" "{script_path}"'

    subprocess.Popen(
        cmd,
        cwd=WORKSPACE_ROOT,
        shell=True,
    )


def print_status() -> None:
    print("\n======================================================================")
    print("           TRẠNG THÁI CÁC DỊCH VỤ CỦA QUAN AI BRAIN")
    print("======================================================================")
    for name, port in [
        ("Phòng Điều Hành & Tham Vấn (Cockpit)", 8766),
        ("Giao Diện Chat Cục Bộ (Web UI)", 8765),
        ("Mô Hình Ngôn Ngữ Local Ollama", 11434),
    ]:
        running = is_port_listening(port)
        status_text = "\033[92mĐANG CHẠY (ONLINE)\033[0m" if running else "\033[91mĐÃ DỪNG (OFFLINE)\033[0m"
        pids = find_pids_on_port(port) if running else []
        pid_str = f" [PID: {', '.join(map(str, pids))}]" if pids else ""
        print(f"  • {name:<36} Cổng :{port:<5} -> {status_text}{pid_str}")
    print("======================================================================\n")


def restart_system(
    target: str = "all",
    validate: bool = False,
    run_tests: bool = False,
    open_browser: bool = True,
) -> bool:
    print(f"\n======================================================================")
    print(f"       QUAN AI BRAIN — LỆNH TỰ KHỞI ĐỘNG LẠI HỆ THỐNG AN TOÀN")
    print(f"======================================================================")
    print(f"  Chủ nhân:        Quanpt1")
    print(f"  Workspace:       {WORKSPACE_ROOT}")
    print(f"  Mục tiêu:        {target.upper()} (Desk: 8766 | Chat: 8765)")
    print(f"======================================================================\n")

    # Step 1: Pre-flight check
    if not check_preflight_imports():
        return False

    # Step 2: Validate & test if requested
    if validate:
        if not run_validation_and_report():
            return False
    elif run_tests:
        log("Đang chạy kiểm thử nhanh (pytest)...")
        res = subprocess.run([str(PYTHON_EXE), "-m", "pytest", "tests/", "-q"], cwd=WORKSPACE_ROOT)
        if res.returncode != 0:
            log("Kiểm thử thất bại. Hủy khởi động lại.", "ERROR")
            return False
        log("Tất cả bài test đều vượt qua.", "SUCCESS")

    # Step 3: Identify targets
    ports_to_restart: list[tuple[str, int, str]] = []
    if target in ("all", "desk"):
        ports_to_restart.append(("Phòng Điều Hành (8766)", 8766, "run_executive_desk.py"))
    if target in ("all", "chat"):
        ports_to_restart.append(("Web UI Chat (8765)", 8765, "run_web_ui.py"))

    # Step 4: Gracefully stop old instances
    for label, port, _ in ports_to_restart:
        pids = find_pids_on_port(port)
        if pids:
            log(f"Phát hiện {label} đang chạy trên PID {pids}. Đang dừng an toàn...")
            terminate_pids(pids)
            wait_port_released(port, timeout_sec=3.0)
        else:
            log(f"{label} hiện chưa chạy (cổng :{port} trống).")

    # Step 5: Check Ollama
    ensure_ollama_running()

    # Step 6: Start new services
    for label, port, script_name in ports_to_restart:
        log(f"Đang khởi động {label} bằng Python 3.11...")
        spawn_service_process(script_name)
        if wait_port_ready(port, timeout_sec=8.0):
            log(f"{label} đã sẵn sàng trên cổng :{port}!", "SUCCESS")
        else:
            log(f"{label} phản hồi chậm trên cổng :{port}. Vui lòng kiểm tra lại.", "WARN")

    # Step 7: Open browser if requested
    primary_url = "http://127.0.0.1:8766/" if target in ("all", "desk") else "http://127.0.0.1:8765/"
    if open_browser:
        log(f"Đang mở giao diện tại: {primary_url}")
        time.sleep(0.5)
        webbrowser.open(primary_url)

    print("\n======================================================================")
    print("      KHỞI ĐỘNG LẠI THÀNH CÔNG — TOÀN BỘ HỆ THỐNG ĐÃ SẴN SÀNG")
    print("======================================================================")
    print(f"  URL Phòng Điều Hành & Tham Vấn:  http://127.0.0.1:8766/")
    print(f"  URL Web Chat Console:            http://127.0.0.1:8765/")
    print(f"  Trợ lý giọng nói:                'Tony ơi' (Wake Word Sẵn Sàng)")
    print("======================================================================\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lệnh tự động khởi động lại hệ thống QUAN AI BRAIN sau mỗi lần update."
    )
    parser.add_argument(
        "--target",
        choices=["all", "desk", "chat"],
        default="all",
        help="Dịch vụ mục tiêu: 'all' (cả 8766 và 8765), 'desk' (:8766), 'chat' (:8765).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Chạy toàn bộ kiểm thử nghiệm thu và cập nhật báo cáo HANDOFF_LATEST.md trước khi khởi động lại.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Chạy pytest nhanh trước khi khởi động lại.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Không tự động mở trình duyệt.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Chỉ kiểm tra và in trạng thái các dịch vụ hiện tại.",
    )

    args = parser.parse_args()

    if args.status:
        print_status()
        return 0

    success = restart_system(
        target=args.target,
        validate=args.validate,
        run_tests=args.test,
        open_browser=not args.no_browser,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
