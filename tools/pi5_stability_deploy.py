#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deploy Pi5 stability config (wifi_watchdog + systemd timer) qua SSH.

Chạy khi Pi5 online. Idempotent: skip nếu md5 khớp.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PI5_HOST = "192.168.1.21"
PI5_USER = "quanpt1"
REMOTE_DIR = "/home/quanpt1/edge_client/pi5_stability"
SYSTEMD_DIR = "/etc/systemd/system"

FILES = [
    ("edge_client/pi5_stability/wifi_watchdog.sh", f"{REMOTE_DIR}/wifi_watchdog.sh", "0755"),
    ("edge_client/pi5_stability/pi5-wifi-watchdog.service", f"{SYSTEMD_DIR}/pi5-wifi-watchdog.service", "0644"),
    ("edge_client/pi5_stability/pi5-wifi-watchdog.timer", f"{SYSTEMD_DIR}/pi5-wifi-watchdog.timer", "0644"),
]


def md5_local(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def md5_remote(host: str, path: str) -> str | None:
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
         f"{PI5_USER}@{host}", f"sha256sum {path} 2>/dev/null | cut -c1-12"],
        capture_output=True, text=True, timeout=15)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None


def scp_file(local: Path, remote: str) -> None:
    subprocess.run(
        ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
         str(local), f"{PI5_USER}@{PI5_HOST}:{remote}"],
        check=True, timeout=30)


def deploy(dry: bool = False) -> dict:
    results = []
    for local_rel, remote, mode in FILES:
        local = WORKSPACE / local_rel
        if not local.exists():
            results.append({"file": local_rel, "status": "MISSING_LOCAL"})
            continue
        local_md5 = md5_local(local)
        remote_md5 = md5_remote(PI5_HOST, remote) if not dry else None
        if remote_md5 == local_md5:
            results.append({"file": local_rel, "status": "SKIP_MATCH", "md5": local_md5})
            continue
        if dry:
            results.append({"file": local_rel, "status": "WOULD_DEPLOY", "md5": local_md5})
            continue
        try:
            scp_file(local, remote)
            subprocess.run(
                ["ssh", "-o", "BatchMode=yes", f"{PI5_USER}@{PI5_HOST}",
                 f"chmod {mode} {remote}"],
                check=True, timeout=15)
            results.append({"file": local_rel, "status": "DEPLOYED", "md5": local_md5})
        except Exception as exc:
            results.append({"file": local_rel, "status": "FAILED", "error": str(exc)[:200]})

    if not dry:
        # Enable + start timer
        cmds = [
            "sudo systemctl daemon-reload",
            "sudo systemctl enable pi5-wifi-watchdog.timer",
            "sudo systemctl start pi5-wifi-watchdog.timer",
            "systemctl list-timers pi5-wifi-watchdog.timer --no-pager",
        ]
        for c in cmds:
            r = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", f"{PI5_USER}@{PI5_HOST}", c],
                capture_output=True, text=True, timeout=20)
            results.append({"cmd": c, "rc": r.returncode,
                            "out": (r.stdout + r.stderr).strip()[:200]})
    return {"results": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = deploy(dry=args.dry_run)
    import json
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
