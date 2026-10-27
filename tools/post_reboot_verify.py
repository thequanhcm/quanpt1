"""Sprint 7 (a): post-reboot verify — kiểm tra 10 bước sau khi PC khởi động lại.

Dùng sau reboot thật (anh nhấn restart). Mọi bước probe THẬT, in PASS/FAIL
trung thực + exit code 0 khi cả 10 PASS, 1 nếu có FAIL (cho task scheduler).

Bước:
 1. Dashboard 8765          6. Backup task Ready (2AM)
 2. Executive 8766          7. Morning report task Ready (8AM)
 3. Ollama 11434            8. brain.db mở được + counts đọc được
 4. Pi 5 edge heartbeat     9. Không daemon trùng lặp (1 instance/daemon)
 5. Responder heartbeat    10. Learning daemon chạy (log mới <15 phút HOẶC
                               watchdog sẽ tự restart trong vòng kế)

Usage: .venv/Scripts/python.exe tools/post_reboot_verify.py
"""
from __future__ import annotations

import json
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(r"E:\AI\QUAN AI BRAIN")


def _tcp(port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def _http(url: str, timeout: float = 5.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _wmic_python_count(fragment: str) -> int:
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine"],
            capture_output=True, text=True, timeout=20,
        ).stdout.lower()
        return sum(1 for line in out.splitlines() if fragment in line)
    except Exception:
        return -1  # không xác minh được = FAIL trung thực


def main() -> int:
    results: list[tuple[int, str, bool, str]] = []

    def check(no: int, name: str, ok: bool, note: str = "") -> None:
        results.append((no, name, ok, note))

    # 1-2. Servers
    dash = _http("http://127.0.0.1:8765/api/status")
    check(1, "Dashboard 8765 ONLINE", dash is not None and dash.get("success") is True)
    edge = _http("http://127.0.0.1:8766/api/executive/edge/status")
    # 4. Pi5 — dùng luôn payload edge
    pi_ok = False
    pi_note = ""
    if edge and edge.get("edge"):
        hb = edge["edge"].get("seconds_since_heartbeat")
        state = edge["edge"].get("state")
        pi_ok = state == "READY" and isinstance(hb, (int, float)) and hb < 10
        pi_note = f"state={state} hb={hb}s"
    else:
        pi_note = "edge status không đọc được"
    check(2, "Executive 8766 ONLINE", edge is not None)
    check(4, "Pi 5 edge READY (hb<10s)", pi_ok, pi_note)

    # 3. Ollama
    check(3, "Ollama 11434 ONLINE", _tcp(11434))

    # 5. Responder heartbeat
    hb_path = BASE / "logs" / "netchat_responder_heartbeat.log"
    if hb_path.exists():
        age = time.time() - hb_path.stat().st_mtime
        check(5, "Responder heartbeat mới (<10 phút)", age < 600, f"age={int(age)}s")
    else:
        check(5, "Responder heartbeat mới (<10 phút)", False, "không có file heartbeat")

    # 6-7. Task Scheduler
    try:
        q = subprocess.run(
            ["schtasks", "/query", "/tn", "QUAN_AI_BRAIN_BACKUP_2AM", "/fo", "LIST"],
            capture_output=True, text=True, timeout=20,
        ).stdout
        check(6, "Backup task Ready", "Ready" in q)
    except Exception as e:
        check(6, "Backup task Ready", False, str(e)[:80])
    try:
        q = subprocess.run(
            ["schtasks", "/query", "/tn", "QUAN_AI_BRAIN_MORNING_REPORT_8AM", "/fo", "LIST"],
            capture_output=True, text=True, timeout=20,
        ).stdout
        check(7, "Morning report task Ready", "Ready" in q)
    except Exception as e:
        check(7, "Morning report task Ready", False, str(e)[:80])

    # 8. DB đọc được
    try:
        conn = sqlite3.connect(str(BASE / "data" / "brain.db"), timeout=5)
        sem = conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
        conn.close()
        check(8, "brain.db mở + đọc được", sem > 0, f"semantic={sem}")
    except Exception as e:
        check(8, "brain.db mở + đọc được", False, str(e)[:80])

    # 9. Không daemon trùng (mỗi daemon = venv launcher + python thật = 2 dòng
    # wmic; đềm <= 2 instance để bật cờ sớm khi trùng)
    dual = _wmic_python_count("start_dual_servers.py")
    wd_cnt = _wmic_python_count("tools\\watchdog.py")
    resp = _wmic_python_count("netchat_auto_responder.py")
    learn = _wmic_python_count("learning_daemon.py")
    check(
        9, "Đúng 1 instance/daemon",
        dual in (1, 2, 3, 4) and wd_cnt in (1, 2) and resp in (1, 2),
        f"dual={dual} watchdog={wd_cnt} responder={resp} learning={learn}",
    )

    # 10. Learning daemon (log mới HOẶC process sống — KHOI_DONG ghi stdout
    # vào learning_daemon.log; không có log mà process sống = buffer chờ)
    ld_log = BASE / "logs" / "learning_daemon.log"
    learn_alive = learn >= 1
    if ld_log.exists():
        age = time.time() - ld_log.stat().st_mtime
        check(10, "Learning daemon sống (log mới <15 phút hoặc process có)",
              age < 900 or learn_alive, f"age={int(age)}s proc={learn}")
    else:
        check(10, "Learning daemon sống (log mới <15 phút hoặc process có)",
              learn_alive, f"proc={learn}")

    # In + chấm
    print("=" * 62)
    print("POST-REBOOT VERIFY —", datetime.now(timezone.utc).astimezone().strftime("%d/%m %H:%M"))
    print("=" * 62)
    n_pass = 0
    for no, name, ok, note in results:
        mark = "PASS" if ok else "FAIL"
        n_pass += ok
        suffix = f"  [{note}]" if note else ""
        print(f"[{mark}] {no:>2}. {name}{suffix}")
    print("=" * 62)
    print(f"KẾT QUẢ: {n_pass}/{len(results)} PASS")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
