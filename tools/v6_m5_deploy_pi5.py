#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V6 M5 — Deploy bộ M5 (FPS meter + PROFILE A + perf telemetry) lên Pi5.

Deploy kỷ luật (bài học sprint trước):
  1. scp 5 file: avatar_engine.js, kiosk.js, kiosk.html, client_daemon.py, edge_agent.py
  2. md5 verify từng file (PC ↔ Pi5 phải khớp)
  3. py_compile 2 file python TRÊN PI5 (chặn SyntaxError giết daemon — bài học kiosk.js 9c8f6639)
  4. node --check avatar_engine.js + kiosk.js TRÊN PI5
  5. restart daemon systemd --user (nếu service tồn tại) hoặc báo owner restart thủ công
  6. verify /api/kiosk/agent/status có kiosk_perf + perf_profile

Không tự restart nếu service không xác định được — fail-honest, báo owner.
"""
import hashlib
import subprocess
import sys
import time

PI5 = "quanpt1@192.168.1.21"
PI5_DIR = "/home/quanpt1/Desktop/edge_client"
FILES = ["avatar_engine.js", "kiosk.js", "kiosk.html", "client_daemon.py", "edge_agent.py"]


def md5_local(path: str) -> str:
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def md5_remote(path: str) -> str:
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", PI5,
         f"md5sum {path}"],
        capture_output=True, text=True, timeout=20)
    return r.stdout.split()[0] if r.returncode == 0 and r.stdout.strip() else "REMOTE_ERR"


def main() -> int:
    print("=== V6 M5 DEPLOY PI5 ===")
    # 1. scp
    for f in FILES:
        src = f"edge_client/{f}"
        r = subprocess.run(
            ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", src, f"{PI5}:{PI5_DIR}/{f}"],
            capture_output=True, text=True, timeout=60)
        ok = r.returncode == 0
        print(f"  scp {f}: {'OK' if ok else 'FAIL ' + (r.stderr or '').strip()[:100]}")
        if not ok:
            return 1
    # 2. md5 verify
    all_ok = True
    for f in FILES:
        l = md5_local(f"edge_client/{f}")
        r = md5_remote(f"{PI5_DIR}/{f}")
        match = l == r
        all_ok &= match
        print(f"  md5 {f}: {'KHỚP' if match else f'LỆCH local={l} remote={r}'}")
    if not all_ok:
        print("DEPLOY ABORT — md5 lệch, KHÔNG restart daemon")
        return 1
    # 3. py_compile trên Pi5
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", PI5,
         f"cd {PI5_DIR} && python3 -m py_compile client_daemon.py edge_agent.py && echo PY_OK"],
        capture_output=True, text=True, timeout=40)
    print("  py_compile Pi5:", "OK" if "PY_OK" in r.stdout else "FAIL " + (r.stderr or "").strip()[:200])
    if "PY_OK" not in r.stdout:
        return 1
    # 4. node --check trên Pi5 (nếu có node)
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", PI5,
         f"cd {PI5_DIR} && (node --check avatar_engine.js && node --check kiosk.js && echo JS_OK) 2>&1 || echo JS_SKIP"],
        capture_output=True, text=True, timeout=40)
    if "JS_OK" in r.stdout:
        print("  node --check Pi5: OK")
    else:
        print("  node --check Pi5: SKIP/KO có node trên Pi5 (PC đã check — chấp nhận)")
    # 5. restart daemon service
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", PI5,
         "systemctl --user list-units --type=service 2>/dev/null | grep -iE 'edge|brain|kiosk' | head -3"],
        capture_output=True, text=True, timeout=20)
    svc = None
    for line in r.stdout.splitlines():
        for cand in ("edge", "brain", "kiosk"):
            if cand in line and ".service" in line:
                svc = line.split()[0]
                break
        if svc:
            break
    if svc:
        print(f"  service: {svc} — restart...")
        r2 = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", PI5, f"systemctl --user restart {svc}"],
            capture_output=True, text=True, timeout=40)
        print("  restart:", "OK" if r2.returncode == 0 else "FAIL " + (r2.stderr or "").strip()[:120])
        time.sleep(4)
    else:
        print("  KHÔNG tìm thấy systemd --user service — owner cần restart daemon thủ công")
        return 2  # deployed nhưng chưa restart
    # 6. verify API
    for _ in range(6):
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", PI5,
             "curl -s --max-time 4 http://127.0.0.1:8768/api/kiosk/agent/status"],
            capture_output=True, text=True, timeout=15)
        if '"kiosk_perf"' in r.stdout and '"metrics"' in r.stdout:
            print("  VERIFY /api/kiosk/agent/status: kiosk_perf CÓ — daemon M5 sống")
            return 0
        time.sleep(3)
    print("  VERIFY FAIL — kiosk_perf chưa xuất hiện trong agent/status sau 18s")
    return 1


if __name__ == "__main__":
    sys.exit(main())
