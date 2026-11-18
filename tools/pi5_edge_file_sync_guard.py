# -*- coding: utf-8 -*-
"""Pi5 EDGE FILE SYNC GUARD — đảm bảo kiosk/engine/protocol trên Pi5 luôn khớp PC.

Mục đích (17/11/2026, owner: "đảm bảo Pi5 luôn hoạt động đồng bộ và ổn định với máy tính"):
- Kiểm tra md5 3 file edge (kiosk.html, avatar_engine.js, avatar_protocol.js) PC vs Pi5
- Lệch → scp tự động → verify md5 lại → restart quan_ai_edge.service nếu có file đổi
- SSH chết → ghi log + DM owner (tối đa 1 lần/30 phút — chống spam), KHÔNG retry mù quáng
- Chạy idempotent, gọi bằng Task Scheduler 15 phút/lần (không cần process nền)
- Fail-honest: mọi bước ghi log; không tự tuyên bố thành công nếu verify fail

Dùng:
  python tools/pi5_edge_file_sync_guard.py --once             # 1 vòng kiểm tra + sync
  python tools/pi5_edge_file_sync_guard.py --once --quiet     # không DM (chỉ log)
  python tools/pi5_edge_file_sync_guard.py --install-task     # cài Task Scheduler 15'
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
LOG_PATH = WORKSPACE / "reports" / "pi5_edge_file_sync.log"
DM_STATE_PATH = WORKSPACE / "data" / "pi5_edge_file_sync_state.json"

PI5_HOST = "192.168.1.21"
PI5_USER = "quanpt1"
PI5_DIR = "/home/quanpt1/Desktop/edge_client"
PC_DIR = WORKSPACE / "edge_client"
SERVICE = "quan_ai_edge.service"

# 3 file phải đồng bộ (PC path name == Pi5 path name)
SYNC_FILES = ["kiosk.html", "avatar_engine.js", "avatar_protocol.js"]

SSH_BASE = [
    "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
    "-o", "StrictHostKeyChecking=accept-new",
    "-i", r"C:/Users/DELL/.ssh/tony_pi5_ed25519",
    "-o", "UserKnownHostsFile=C:/Users/DELL/.ssh/known_hosts",
    f"{PI5_USER}@{PI5_HOST}",
]

DM_COOLDOWN_S = 30 * 60  # 30 phút


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} | {msg}"
    print(line)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _secret_dir_on_path() -> None:
    d = WORKSPACE / "user, pass, token"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))


def dm_owner(msg: str) -> bool:
    """Gửi DM cho owner qua netchat_bot.py (2 bước confirm). True nếu gửi OK."""
    try:
        _secret_dir_on_path()
        bot = Path(r"C:/Users/DELL/AppData/Local/netmind_desktop/skills/bot-netchat/netchat_bot.py")
        py = WORKSPACE / ".venv" / "Scripts" / "python.exe"
        if not py.exists():
            py = Path(sys.executable)
        r1 = subprocess.run(
            [str(py), str(bot), "dm", "quanpt1", msg],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
        import re
        m = re.search(r"CONFIRM-REQUIRED: (\w+)", r1.stdout or "")
        if not m:
            log(f"DM step1 rc={r1.returncode} (không có confirm token?)")
            return False
        r2 = subprocess.run(
            [str(py), str(bot), "dm", "quanpt1", msg, "--confirmed", m.group(1)],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
        ok = r2.returncode == 0
        log(f"DM gửi: {'OK' if ok else f'FAIL rc={r2.returncode}'}")
        return ok
    except Exception as e:
        log(f"DM lỗi: {e}")
        return False


def dm_owner_rate_limited(key: str, msg: str) -> bool:
    """DM với cooldown 30 phút cho cùng key."""
    try:
        state = json.loads(DM_STATE_PATH.read_text(encoding="utf-8")) if DM_STATE_PATH.exists() else {}
    except Exception:
        state = {}
    now = time.time()
    last = state.get(key, 0)
    if now - last < DM_COOLDOWN_S:
        log(f"DM '{key}' cooldown ({int((DM_COOLDOWN_S - (now - last)) / 60)}' nữa) — bỏ qua")
        return False
    ok = dm_owner(msg)
    if ok:
        state[key] = now
        try:
            DM_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            DM_STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")
        except Exception:
            pass
    return ok


def ssh_ok() -> bool:
    try:
        r = subprocess.run(SSH_BASE + ["true"], capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def pi5_md5() -> dict[str, str]:
    """md5 3 file trên Pi5. Trả dict name→md5 (file thiếu → 'MISSING')."""
    names = " ".join(SYNC_FILES)
    try:
        r = subprocess.run(
            SSH_BASE + [f"cd {PI5_DIR} && md5sum {names} 2>/dev/null"],
            capture_output=True, text=True, timeout=25,
        )
        out = {}
        for line in (r.stdout or "").splitlines():
            parts = line.strip().split()
            if len(parts) == 2:
                out[parts[1]] = parts[0]
        for n in SYNC_FILES:
            out.setdefault(n, "MISSING")
        return out
    except Exception as e:
        log(f"md5sum Pi5 lỗi: {e}")
        return {}


def pc_md5() -> dict[str, str]:
    out = {}
    for n in SYNC_FILES:
        p = PC_DIR / n
        out[n] = md5_file(p) if p.exists() else "MISSING"
    return out


def scp_files(names: list[str]) -> bool:
    """scp file từ PC lên Pi5 (scp đích trực tiếp + mv nếu tmp còn sót từ lần trước)."""
    ok_all = True
    for n in names:
        src = PC_DIR / n
        try:
            r = subprocess.run(
                ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                 str(src), f"{PI5_USER}@{PI5_HOST}:{PI5_DIR}/{n}"],
                capture_output=True, text=True, timeout=40,
            )
            if r.returncode != 0:
                log(f"scp {n} FAIL rc={r.returncode} {r.stderr[:120]}")
                ok_all = False
                continue
            log(f"scp {n} OK")
            # dọn tmp sót (nếu có) — best effort, không fail guard
            subprocess.run(
                SSH_BASE + [f"cd {PI5_DIR} && rm -f {n}.tmp_sync"],
                capture_output=True, text=True, timeout=45,
            )
        except Exception as e:
            log(f"scp {n} lỗi: {e}")
            ok_all = False
    return ok_all


def restart_service() -> bool:
    try:
        r = subprocess.run(
            SSH_BASE + [f"sudo systemctl restart {SERVICE} && sleep 2 && systemctl is-active {SERVICE}"],
            capture_output=True, text=True, timeout=30,
        )
        active = (r.stdout or "").strip()
        log(f"restart {SERVICE}: {active}")
        return active == "active"
    except Exception as e:
        log(f"restart service lỗi: {e}")
        return False


def run_once(quiet: bool = False) -> int:
    log("=== pi5_edge_file_sync_guard START ===")

    # Bước 0: PC md5 phải có
    pcm = pc_md5()
    missing_pc = [n for n, v in pcm.items() if v == "MISSING"]
    if missing_pc:
        log(f"❌ File PC thiếu: {missing_pc} — DỪNG (không sync file rác lên Pi5)")
        if not quiet:
            dm_owner_rate_limited("pc_missing", f"⚠️ File PC thiếu {missing_pc} — guard dừng, không sync.")
        return 2

    # Bước 1: SSH reachable?
    if not ssh_ok():
        log("❌ SSH Pi5 không tới — không sync lần này (watchdog riêng sẽ alert)")
        if not quiet:
            dm_owner_rate_limited(
                "ssh_down",
                f"⚠️ Pi5 {PI5_HOST}: SSH không tới (guard file-sync). WiFi Pi5 có thể yếu — sẽ thử lại 15 phút sau.",
            )
        return 1

    # Bước 2: so md5
    pim = pi5_md5()
    if not pim:
        log("❌ Không lấy được md5 Pi5")
        return 1
    diff = [n for n in SYNC_FILES if pcm[n] != pim[n]]
    if not diff:
        log(f"✅ Đồng bộ {len(SYNC_FILES)}/{len(SYNC_FILES)} file (md5 khớp) — không cần làm gì")
        return 0

    # Bước 3: sync file lệch
    log(f"🔁 Lệch md5: {diff} — scp...")
    if not scp_files(diff):
        log("❌ scp fail — không restart service, thử lại lần sau")
        if not quiet:
            dm_owner_rate_limited("scp_fail", f"⚠️ Guard không scp được {diff} lên Pi5. Cần kiểm tra SSH/smart card.")
        return 1

    # Bước 4: verify sau scp
    pim2 = pi5_md5()
    still = [n for n in diff if pcm[n] != pim2.get(n)]
    if still:
        log(f"❌ Verify sau scp VẪN lệch: {still} — FAIL-HONEST, không restart")
        if not quiet:
            dm_owner_rate_limited("verify_fail", f"⚠️ Guard scp xong nhưng md5 vẫn lệch: {still}. Cần audit tay.")
        return 1
    log(f"✅ Verify sau scp: {len(diff)}/{len(diff)} khớp PC")

    # Bước 5: restart service (file kiosk/engine/protocol đổi → kiosk cần serve bản mới)
    if restart_service():
        log(f"✅ {SERVICE} restarted + active — sync hoàn tất")
        if not quiet:
            dm_owner_rate_limited(
                "sync_done",
                f"🔄 Guard tự đồng bộ {len(diff)} file ({', '.join(diff)}) PC→Pi5 + restart service OK. md5 khớp.",
            )
        return 0
    log("❌ Restart service FAIL")
    if not quiet:
        dm_owner_rate_limited("restart_fail", f"⚠️ Guard scp OK nhưng restart {SERVICE} fail trên Pi5.")
    return 1


def install_task() -> None:
    """Cài Task Scheduler: chạy guard 15 phút/lần (idempotent, không process nền)."""
    py = WORKSPACE / ".venv" / "Scripts" / "python.exe"
    script = Path(__file__).resolve()
    cmd = (
        f"schtasks /Create /F /TN QUAN_AI_BRAIN_PI5_FILE_SYNC_15MIN "
        f"/TR \"\\\"{py}\\\" \\\"{script}\\\" --once --quiet\" "
        f"/SC MINUTE /MO 15"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=30)
    print(r.stdout or r.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="không DM (chỉ log)")
    ap.add_argument("--install-task", action="store_true")
    args = ap.parse_args()

    if args.install_task:
        install_task()
        return
    if args.once or True:  # mặc định --once (idempotent, Task Scheduler)
        raise SystemExit(run_once(quiet=args.quiet))


if __name__ == "__main__":
    main()
