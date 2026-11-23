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
    return 0


if __name__ == "__main__":
    sys.exit(main())
