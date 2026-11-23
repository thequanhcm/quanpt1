# -*- coding: utf-8 -*-
"""v6_m4b_watch_sync_pi5.py — Watch Pi5 rồi sync 3 file M4b khi SSH thông.

Pi5 WiFi đang yếu (ping 60% loss, SSH timeout). Script chạy NGẦM, thử SSH
định kỳ; ngay khi SSH chấp nhận kết nối thì:
  1. scp 3 file M4b (kiosk.html, avatar_engine.js, avatar_protocol.js)
  2. md5 verify Pi5 khớp PC
  3. restart quan_ai_edge.service
  4. Ghi log + gửi DM NetChat báo thành công (dùng skill bot-netchat)

Tự thoát khi sync xong hoặc sau MAX_ROUNDS vòng thử.
"""
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime

HOST = "quanpt1@192.168.1.21"
REMOTE_DIR = "~/Desktop/edge_client"
WORKSPACE = r"E:\BRAIN"
FILES = ["kiosk.html", "avatar_engine.js", "avatar_protocol.js"]
LOG = os.path.join(WORKSPACE, "reports", "m4b_pi5_sync.log")
INTERVAL = 60          # giây giữa 2 vòng thử
MAX_ROUNDS = 240       # 240 vòng x 60s = 4 giờ rồi tự thoát


def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def try_ssh(timeout=10):
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", f"-o", f"ConnectTimeout={timeout}",
         HOST, "echo SSH_OK"],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    return "SSH_OK" in (r.stdout or "")


def scp_files():
    ok = True
    for f in FILES:
        src = os.path.join(WORKSPACE, "edge_client", f)
        r = subprocess.run(
            ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
             src, f"{HOST}:{REMOTE_DIR}/{f}"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            log(f"SCP FAIL {f}: {(r.stderr or '').strip()[:120]}")
            ok = False
    return ok


def verify_md5():
    cmds = "; ".join([f"md5sum {REMOTE_DIR}/{f}" for f in FILES])
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, cmds],
        capture_output=True, text=True, timeout=60,
    )
    out = r.stdout or ""
    results = {}
    for f in FILES:
        local = md5(os.path.join(WORKSPACE, "edge_client", f))
        for line in out.splitlines():
            if f in line:
                remote = line.split()[0]
                results[f] = (remote == local, local, remote)
    return results


def restart_service():
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST,
         "sudo systemctl restart quan_ai_edge.service && sleep 6 && systemctl is-active quan_ai_edge.service"],
        capture_output=True, text=True, timeout=90,
    )
    return (r.stdout or "").strip()


def notify_dm(text):
    bot = r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
    p = subprocess.run([sys.executable, bot, "dm", "quanpt1", text],
                       capture_output=True, text=True, timeout=60)
    if p.returncode == 3:
        token = None
        out = (p.stdout or "") + (p.stderr or "")
        for line in out.splitlines():
            if line.startswith("CONFIRM-REQUIRED:"):
                token = line.split(":", 1)[1].strip()
        if token:
            p = subprocess.run([sys.executable, bot, "dm", "quanpt1", text,
                                "--confirmed", token],
                               capture_output=True, text=True, timeout=60)
    return p.returncode


def main():
    log("=== WATCHER START: chờ Pi5 SSH thông rồi sync M4b ===")
    for rnd in range(1, MAX_ROUNDS + 1):
        try:
            if try_ssh():
                log(f"ROUND {rnd}: SSH OK — bắt đầu scp 3 file M4b")
                if not scp_files():
                    log("scp lỗi — thử vòng sau")
                    time.sleep(INTERVAL)
                    continue
                ver = verify_md5()
                all_ok = all(ok for ok, _, _ in ver.values()) and len(ver) == 3
                for f, (ok, lo, re_) in ver.items():
                    log(f"MD5 {f}: {'OK' if ok else 'MISMATCH'} (PC={lo} Pi5={re_})")
                if all_ok:
                    svc = restart_service()
                    log(f"Service restart: {svc}")
                    log("SYNC HOÀN TẤT — gửi DM báo cáo")
                    lines = [f"🍓 CHERRY — Đã đồng bộ M4b lên Pi5 ({datetime.now().strftime('%H:%M %d/%m')})"]
                    for f, (ok, _, _) in ver.items():
                        lines.append(f"{'✅' if ok else '❌'} {f}: md5 {'khớp' if ok else 'LỆCH'}")
                    lines.append(f"🔁 quan_ai_edge.service: {svc}")
                    notify_dm("\n".join(lines))
                    log("=== WATCHER DONE ===")
                    return 0
                else:
                    log("md5 lệch — thử scp lại")
            else:
                if rnd % 10 == 0:
                    log(f"ROUND {rnd}: SSH chưa thông")
        except subprocess.TimeoutExpired:
            log(f"ROUND {rnd}: ssh timeout")
        time.sleep(INTERVAL)
    log("=== WATCHER MAX_ROUNDS — tự thoát (4h không kết nối được) ===")
    return 1


if __name__ == "__main__":
    sys.exit(main())
