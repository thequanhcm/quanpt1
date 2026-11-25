# -*- coding: utf-8 -*-
"""GHÉP 4 CỬA SỔ CHERRY THÀNH 1 (23/11/2026, owner yêu cầu).

Vấn đề: KHOI_DONG_CHERRY.bat mở 4 cửa sổ console riêng (BAT + DualServers +
NetChatBot + Learning) → rối màn hình.

Giải pháp: 1 cửa sổ duy nhất (window host) chạy 4 service bằng subprocess,
đọc log trực tiếp của từng service và in TRỘN về đúng 1 console, mỗi dòng
kèm nhãn [SERVERS]/[NETCHAT]/[LEARNING]. Vẫn ghi file log đầy đủ riêng
từng service (logs/cherry_*.log) để debug.

Dừng Cherry: chạy TAT_CHERRY.bat (giữ nguyên — nó kill theo tên script).
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

PY = str(ROOT / ".venv" / "Scripts" / "pythonw.exe")
if not os.path.exists(PY):
    PY = str(ROOT / ".venv" / "Scripts" / "python.exe")

# (23/11/2026) Màu ANSI — cmd Win10 bật VT qua chuỗi escape trong BAT chính.
C_RESET = "\x1b[0m"
COLORS = {
    "SERVERS": "\x1b[96m",   # cyan
    "NETCHAT": "\x1b[92m",   # xanh lá
    "LEARNING": "\x1b[93m",  # vàng
    "SYSTEM": "\x1b[95m",    # tím
}
LABEL_W = 9

# ---- 3 service (không tính cửa sổ BAT chủ) ----
SERVICES = [
    ("SERVERS", [PY, str(ROOT / "start_dual_servers.py")]),
    ("NETCHAT", [PY, str(ROOT / "tools" / "netchat_auto_responder.py")]),
    ("LEARNING", [PY, str(ROOT / "tools" / "learning_daemon.py")]),
]



LOCK_FILE = ROOT / "data" / "console_host.lock"


def _acquire_lock() -> bool:
    """Marker chống double-spawn (skill windows-daemon-ops): nếu lock còn FRESH
    (< 2 giờ) và process ghi trong lock còn sống → đã có host → False."""
    import os as _os
    try:
        if LOCK_FILE.exists():
            age = time.time() - LOCK_FILE.stat().st_mtime
            pid_txt = LOCK_FILE.read_text(encoding="ascii", errors="replace").strip()
            if age < 7200 and pid_txt.isdigit():
                # process còn sống không?
                out = subprocess.run(["tasklist", "/FI", f"PID eq {pid_txt}"],
                                     capture_output=True, text=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                if str(pid_txt) in (out.stdout or ""):
                    return False
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(str(_os.getpid()), encoding="ascii")
        return True
    except Exception:
        return True  # fail-open: tốt hơn là mở 2 cửa sổ giám sát than thiếu


def _release_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _pump(name: str, proc: subprocess.Popen, q: "queue.Queue[tuple[str, str]]") -> None:
    """Đọc stdout của 1 service, đẩy từng dòng vào queue chung."""
    tag = f"{name:<{LABEL_W}}"
    try:
        for raw in iter(proc.stdout.readline, ""):
            if not raw:
                break
            line = raw.rstrip("\r\n")
            if line.strip():
                q.put((name, f"{line}"))
            else:
                q.put((name, ""))
    except Exception as e:
        q.put((name, f"[pump lỗi] {e}"))
    finally:
        code = proc.poll()
        q.put((name, f"--- THOÁT (code {code}) — xem log chi tiết logs/cherry_{name.lower()}.log ---"))


def _start_services():
    """Khởi động 3 service. Mỗi service: log file riêng + pipe về host."""
    procs = []
    for name, cmd in SERVICES:
        logf = open(LOG_DIR / f"cherry_{name.lower()}.log", "ab", buffering=0)
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        p = subprocess.Popen(
            cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
            env=env, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        procs.append((name, p))
    return procs


def main() -> int:
    if not _acquire_lock():
        print("[SYSTEM] Đã có cửa sổ CHERRY đang chạy — thoát (không mở trùng).")
        return 0
    print("=" * 78)
    print("  CHERRY — BẢNG ĐIỀU KHIỂN GỘP (1 cửa sổ: Servers + NetChat + Learning)")
    print("  Log chi tiết từng service: logs/cherry_servers.log / _netchat.log / _learning.log")
    print("  Tắt Cherry: chạy TAT_CHERRY.bat (hoặc đóng cửa sổ này)")
    print("=" * 78)

    procs = _start_services()
    q: "queue.Queue[tuple[str, str]]" = queue.Queue()
    threads = []
    for name, p in procs:
        t = threading.Thread(target=_pump, args=(name, p, q), daemon=True)
        t.start()
        threads.append(t)
        print(f"  \x1b[92m[OK]\x1b[0m {name:<9} PID {p.pid}")

    print("-" * 78)
    print("Đang trộn log 3 service (Ctrl+C hoặc đóng cửa sổ để tắt)...")
    print()

    try:
        while True:
            # dồn log — tối đa 200 dòng/lượt, chờ tối đa 0.5s
            deadline = time.time() + 0.5
            shown = 0
            while time.time() < deadline and shown < 200:
                try:
                    name, line = q.get(timeout=0.1)
                except queue.Empty:
                    break
                color = COLORS.get(name, "")
                tag = f"{name:<9}"
                if line:
                    print(f"{color}{_stamp()} {tag}\x1b[0m {line}")
                else:
                    print()
                shown += 1
            # kiểm tra service nào đã chết
            for name, p in procs:
                if p.poll() is not None:
                    pass  # dòng thoát đã in bởi pump
            if all(p.poll() is not None for _, p in procs):
                print("\n[SYSTEM] Cả 3 service đã dừng.")
                break
    except KeyboardInterrupt:
        print("\n[SYSTEM] Nhận Ctrl+C — dừng toàn bộ service...")
    finally:
        for name, p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        time.sleep(1)
        for name, p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[SYSTEM] Đã dừng sạch. Đóng cửa sổ.")
        _release_lock()
    return 0




def _ports_alive() -> bool:
    """Kiểm tra nhanh stack đã chạy sẵn chưa (port 8765 listen?)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        return s.connect_ex(("127.0.0.1", 8765)) == 0
    finally:
        s.close()


def main_attach() -> int:
    """(24/11/2026, owner: 'chi 1 cua so') CHẾ ĐỘ GẮN VÀO stack đang sống:
    KHÔNG spawn service mới — chỉ đọc 3 log file hiện có và trộn in về cửa sổ.
    Đóng cửa sổ = ngắt giám sát (service vẫn sống, không bị tắt).
    """
    if not _acquire_lock():
        print("[SYSTEM] Đã có cửa sổ CHERRY đang chạy — thoát (không mở trùng).")
        return 0
    print("=" * 78)
    print("  CHERRY — BẢNG ĐIỀU KHIỂN (chế độ GẮN VÀO: service đã chạy sẵn)")
    print("  Đang xem log: servers + netchat + learning. Đóng cửa sổ này KHÔNG tắt Cherry.")
    print("  Tắt hẳn Cherry: chạy TAT_CHERRY.bat")
    print("=" * 78)
    logs = [
        ("SERVERS", LOG_DIR / "cherry_servers.log"),
        ("NETCHAT", LOG_DIR / "cherry_netchat.log"),
        ("LEARNING", LOG_DIR / "cherry_learning.log"),
    ]
    print("  [OK] Stack đang sống (port 8765) — bám log 3 service:")
    for name, f in logs:
        print(f"    - {name:<9} {f.name}")
    print("-" * 78)
    print("Đang theo dõi log (Ctrl+C hoặc đóng cửa sổ để ngắt xem)...")
    print()
    try:
        # đọc từ cuối file trở đi
        handles = []
        for name, f in logs:
            fh = open(f, "r", encoding="utf-8", errors="replace")
            fh.seek(0, 2)  # EOF
            handles.append((name, fh))
        import queue as _q
        q: "_q.Queue[tuple[str, str]]" = _q.Queue()
        def _pump_file(name: str, fh):
            for raw in iter(fh.readline, ""):
                line = raw.rstrip("\r\n")
                if line.strip():
                    q.put((name, line))
            # EOF — poll tiếp
            while True:
                line = fh.readline()
                if line:
                    line = line.rstrip("\r\n")
                    if line.strip():
                        q.put((name, line))
                else:
                    time.sleep(0.4)
        threads = []
        for name, fh in handles:
            t = threading.Thread(target=_pump_file, args=(name, fh), daemon=True)
            t.start()
            threads.append(t)
        while True:
            deadline = time.time() + 0.5
            shown = 0
            while time.time() < deadline and shown < 200:
                try:
                    name, line = q.get(timeout=0.1)
                except _q.Empty:
                    break
                color = COLORS.get(name, "")
                print(f"{color}{_stamp()} {name:<9}\x1b[0m {line}")
                shown += 1
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Ngắt xem — Cherry vẫn chạy nền.")
    finally:
        _release_lock()
    return 0


if __name__ == "__main__":
    if "--attach" in sys.argv:
        sys.exit(main_attach())
    sys.exit(main())
