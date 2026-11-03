"""Watchdog cho NetChat auto-responder (01/11/2026, owner).

Yêu cầu anh Quân: 'nếu Tony treo thì khi kết nối lại vẫn quét và nhìn lại
phần tin a đã gửi trước đó để phản hồi'.

Vòng 30s: heartbeat file mtime > 120s (responder sleep 2s/vòng nên heartbeat
chuẩn lệch vài giây) → coi như TREO/CHẾT → kill mọi instance responder →
start lại (responder mới tự quét lại tin 12h chưa trả lời + gửi greeting).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEARTBEAT = ROOT / "logs" / "netchat_responder_heartbeat.log"
STDOUT_LOG = ROOT / "logs" / "netchat_responder_stdout.log"
PYTHONW = ROOT / ".venv" / "Scripts" / "pythonw.exe"
SCRIPT = ROOT / "tools" / "netchat_auto_responder.py"
STATE_LOG = ROOT / "logs" / "netchat_responder_watchdog.log"

STALE_SECONDS = 120


def log(msg: str) -> None:
    try:
        with open(STATE_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def responder_pids() -> list[str]:
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
         "Where-Object { $_.CommandLine -like '*netchat_auto_responder*' } | "
         "ForEach-Object { $_.ProcessId }"],
        capture_output=True, text=True, timeout=30)
    return [x.strip() for x in ps.stdout.split() if x.strip().isdigit()]


def main() -> None:
    log("watchdog started")
    while True:
        try:
            pids = responder_pids()
            stale = (not HEARTBEAT.exists()
                     or time.time() - HEARTBEAT.stat().st_mtime > STALE_SECONDS)
            if pids and not stale:
                time.sleep(30)
                continue
            if pids and stale:
                log(f"responder {pids} STALE {STALE_SECONDS}s+ — kill & restart")
                for pid in pids:
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True, timeout=30)
                time.sleep(3)
            elif not pids:
                log("responder KHÔNG chạy — start lại")
            env = dict(os.environ, PYTHONUNBUFFERED="1")
            subprocess.Popen(
                [str(PYTHONW), str(SCRIPT)], cwd=str(ROOT), env=env,
                stdout=open(STDOUT_LOG, "ab", buffering=0),
                stderr=subprocess.STDOUT, creationflags=0x00000008)
            log("responder respawned")
            time.sleep(60)
        except Exception as exc:
            log(f"watchdog error: {exc}")
            time.sleep(30)


if __name__ == "__main__":
    main()
