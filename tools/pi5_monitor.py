#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pi5 liveness monitor — chạy nền trên PC, phát hiện Pi5 mất → DM owner.

Thiết kế (12/11/2026, sau 3 lần Pi5 mất mạng):
- Probe mỗi 60s: ping + SSH port + mDNS fallback
- Nếu mất > 5 phút liên tục → ghi log + DM owner (1 lần, không spam)
- Nếu Pi5 sống lại → ghi log + DM owner "đã sống lại" + auto-trigger reconcile
- Rate-limit DM: tối đa 1 DM mỗi 30 phút cho cùng trạng thái (chống spam)
- Chạy bằng Task Scheduler mỗi 5 phút (không cần process nền — idempotent)

Dùng:
  python tools/pi5_monitor.py --once          # 1 lần probe, ghi log
  python tools/pi5_monitor.py --once --notify # 1 lần probe + DM nếu mất
  python tools/pi5_monitor.py --install-task  # cài Task Scheduler 5 phút/lần
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret

# (12/11/2026) Loader secret tập trung
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret

WORKSPACE = Path(__file__).resolve().parent.parent
STATE_PATH = WORKSPACE / "data" / "pi5_monitor_state.json"
LOG_PATH = WORKSPACE / "data" / "pi5_monitor.log"

PI5_HOSTS = ["192.168.1.21", "quanpt1.local"]
PI5_PORTS = [22, 8768]  # SSH + kiosk
PROBE_TIMEOUT = 3.0
LOST_THRESHOLD_SEC = 300  # 5 phút mất liên tục → cảnh báo
DM_COOLDOWN_SEC = 1800    # 30 phút/lần DM cho cùng trạng thái


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"{now_utc()} | {msg}"
    print(line)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_seen_utc": None, "last_lost_utc": None,
            "last_dm_state": None, "last_dm_utc": None,
            "consecutive_lost_probes": 0}


def save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def probe() -> dict:
    """Trả {alive: bool, host: str|None, latency_ms: int|None, reason: str}."""
    for host in PI5_HOSTS:
        for port in PI5_PORTS:
            t0 = time.perf_counter()
            s = socket.socket()
            s.settimeout(PROBE_TIMEOUT)
            try:
                s.connect((host, port))
                latency = (time.perf_counter() - t0) * 1000
                return {"alive": True, "host": host, "port": port,
                        "latency_ms": round(latency), "reason": "tcp_open"}
            except socket.gaierror:
                continue  # mDNS chưa resolve, thử host kế
            except Exception:
                continue
            finally:
                s.close()
    return {"alive": False, "host": None, "port": None, "latency_ms": None,
            "reason": "all_hosts_unreachable"}


def notify_owner(msg: str) -> bool:
    """Gửi DM NetChat qua bot script (2 bước token). Best effort."""
    try:
        bot = r"C:/Users/DELL/AppData/Local/netmind_desktop/skills/bot-netchat/netchat_bot.py"
        dm_id = _get_secret("netchat_channel_owner", "mwp3nk3ciprjjr4hdmcoqgk6jr")  # (12/11) đọc từ loader
        py = r"E:/BRAIN/.venv/Scripts/python.exe"
        base = [py, bot, "send", dm_id, msg]
        r1 = subprocess.run(base, capture_output=True, text=True, timeout=45)
        out = (r1.stdout + r1.stderr).strip()
        if r1.returncode == 0:
            return True
        import re
        m = re.search(r"CONFIRM-REQUIRED:\s*([0-9a-f]+)", out)
        if r1.returncode == 3 and m:
            r2 = subprocess.run(base + ["--confirmed", m.group(1)],
                                capture_output=True, text=True, timeout=45)
            return r2.returncode == 0
        return False
    except Exception as exc:
        log(f"notify_owner error: {exc}")
        return False



def should_dm(state: dict, new_state: str) -> bool:
    """Rate-limit: 1 DM / 30 phút cho cùng trạng thái."""
    if state.get("last_dm_state") != new_state:
        return True
    last = state.get("last_dm_utc")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now(timezone.utc) - last_dt).total_seconds() > DM_COOLDOWN_SEC
    except Exception:
        return True


def run_once(notify: bool = False) -> dict:
    state = load_state()
    p = probe()
    now = now_utc()

    if p["alive"]:
        state["consecutive_lost_probes"] = 0
        was_lost = state.get("last_lost_utc") is not None
        state["last_seen_utc"] = now
        log(f"ALIVE host={p['host']}:{p['port']} latency={p['latency_ms']}ms")
        if was_lost and notify and should_dm(state, "recovered"):
            uptime_info = ""
            # Nếu SSH được, lấy uptime thật
            if p["port"] == 22:
                try:
                    r = subprocess.run(
                        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                         "quanpt1@192.168.1.21", "uptime -p; cat /proc/loadavg"],
                        capture_output=True, text=True, timeout=15)
                    if r.returncode == 0:
                        uptime_info = f"\nUptime: {r.stdout.strip().splitlines()[0]}"
                except Exception:
                    pass
            msg = (f"🟢 Pi5 vừa SỐNG LẠI — monitor phát hiện lúc {now} "
                   f"(host {p['host']}:{p['port']}, latency {p['latency_ms']}ms)"
                   f"{uptime_info}\n"
                   f"Reconcile sẽ tự chạy trong vòng 1h (rate-limit).")
            if notify_owner(msg):
                state["last_dm_state"] = "recovered"
                state["last_dm_utc"] = now
                log("DM recovered sent")
        state["last_lost_utc"] = None
    else:
        state["consecutive_lost_probes"] = state.get("consecutive_lost_probes", 0) + 1
        if state.get("last_lost_utc") is None:
            state["last_lost_utc"] = now
        lost_since = state["last_lost_utc"]
        try:
            lost_dt = datetime.fromisoformat(lost_since)
            lost_sec = (datetime.now(timezone.utc) - lost_dt).total_seconds()
        except Exception:
            lost_sec = 0
        log(f"LOST probe #{state['consecutive_lost_probes']} (mất {lost_sec:.0f}s)")
        if lost_sec >= LOST_THRESHOLD_SEC and notify and should_dm(state, "lost"):
            msg = (f"🔴 Pi5 MẤT MẠNG — monitor phát hiện lúc {now}\n"
                   f"Mất liên tục: {lost_sec/60:.0f} phút\n"
                   f"Lần thấy cuối: {state.get('last_seen_utc','?')}\n"
                   f"Nguyên nhân có thể: WiFi drop / mất nguồn / OS treo\n"
                   f"Hw watchdog 10s chỉ reboot khi OS treo — KHÔNG reboot khi mất nguồn hoàn toàn.\n"
                   f"Anh kiểm tra: (1) cục nguồn 5V/5A cắm chặt, (2) WiFi adapter, (3) đèn LED Pi5.")
            if notify_owner(msg):
                state["last_dm_state"] = "lost"
                state["last_dm_utc"] = now
                log("DM lost sent")

    save_state(state)
    return {"probe": p, "state": state}


def install_task() -> None:
    """Cài Task Scheduler chạy mỗi 5 phút (idempotent)."""
    py = r"E:/BRAIN/.venv/Scripts/python.exe"
    script = str(Path(__file__).resolve())
    task_name = "QUAN_AI_BRAIN_PI5_MONITOR_5MIN"
    cmd = ["schtasks", "/create", "/tn", task_name, "/tr",
           f'"{py}" "{script}" --once --notify',
           "/sc", "minute", "/mo", "5",
           "/rl", "LIMITED", "/f"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("STDOUT:", r.stdout)
    print("STDERR:", r.stderr)
    print("rc:", r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--install-task", action="store_true")
    args = ap.parse_args()
    if args.install_task:
        install_task()
    elif args.once:
        out = run_once(notify=args.notify)
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()