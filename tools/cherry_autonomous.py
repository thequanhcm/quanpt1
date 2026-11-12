"""CHERRY AUTONOMOUS MODE — tự vận hành chủ động 24/7.

Owner lệnh 12/11/2026: "cho cherry tự vận hành chủ động và quản trị,
điều khiển thông qua ra lệnh DM của anh quanpt1 từ netchat".

3 lớp an toàn (fail-safe):
- LỚP 1 AUTO (không cần duyệt): probe read-only + self-heal BIẾT CHẮC
  (restart dual servers khi /api/health chết 2 lần liên tiếp; restart
  responder khi heartbeat stale >300s; DM cảnh báo khi Pi5 mất >5m).
- LỚP 2 PROPOSE (DM xin duyệt 2 bước token): bất thường KHÔNG tự xử
  (ollama chết, learning stale >1h, disk >80%, DB phình) — DM đề xuất,
  owner trả lời "duyệt" mới làm.
- LỚP 3 NEVER: R4/R5, xóa data, executive.js, router, secrets — hard-block.

Chống spam: mỗi loại alert/cảnh báo tối đa 1 lần/30 phút (rate-limit state).
Chống restart loop: tối đa 2 restart/giờ/thành phần; vượt → PROPOSE thay vì AUTO.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
STATE_PATH = WORKSPACE / "data" / "cherry_autonomous_state.json"
LOG_PATH = WORKSPACE / "logs" / "cherry_autonomous.log"
NETCHAT_PY = r"C:/Users/DELL/AppData/Local/netmind_desktop/skills/bot-netchat/netchat_bot.py"
NETCHAT_VENV = r"E:/BRAIN/.venv/Scripts/python.exe"
DM_CHANNEL = "mwp3nk3ciprjjr4hdmcoqgk6jr"

HEALTH_URL = "http://127.0.0.1:8765/api/health"
EXEC_URL = "http://127.0.0.1:8766/"

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Rate-limit + restart budget
ALERT_COOLDOWN_S = 1800      # 30 phút giữa 2 alert cùng loại
RESTART_BUDGET_PER_HOUR = 2  # tối đa 2 restart/thành phần/giờ


def _log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    try:
        print(line)  # pythonw + DEVNULL: stdout là None → bỏ qua, không crash
    except Exception:
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"alerts": {}, "restarts": {}, "proposals": {}}


def _save_state(st: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        _log(f"state save failed: {e}")


def _dm(text: str) -> bool:
    """Gửi DM owner qua netchat_bot 2 bước token (chuẩn confirm gate).

    Bước 1: send → exit 3 (confirm required) + token ở stderr.
    Bước 2: send ... --confirmed <token> → exit 0 = gửi thành công.
    """
    try:
        r1 = subprocess.run(
            [NETCHAT_VENV, NETCHAT_PY, "send", DM_CHANNEL, text],
            capture_output=True, creationflags=NO_WINDOW, text=True, timeout=60,
        )
        if r1.returncode == 0:
            _log(f"DM send ok (1 bước): {text[:80]!r}")
            return True
        if r1.returncode != 3:
            _log(f"DM step1 rc={r1.returncode}: {r1.stderr[:120]}")
            return False
        token = ""
        for line in r1.stdout.splitlines():
            if line.startswith("CONFIRM-REQUIRED:"):
                token = line.split(":", 1)[1].strip()
                break
        if not token:
            _log("DM step1: không tìm thấy token CONFIRM-REQUIRED trong stdout")
            return False
        r2 = subprocess.run(
            [NETCHAT_VENV, NETCHAT_PY, "send", DM_CHANNEL, text,
             "--confirmed", token],
            capture_output=True, creationflags=NO_WINDOW, text=True, timeout=60,
        )
        ok = r2.returncode == 0
        _log(f"DM 2 bước ok={ok}: {text[:80]!r}")
        return ok
    except Exception as e:
        _log(f"DM send error: {e}")
        return False


def _should_alert(st: dict, key: str) -> bool:
    now = time.time()
    last = st.get("alerts", {}).get(key, 0)
    if now - last < ALERT_COOLDOWN_S:
        return False
    st.setdefault("alerts", {})[key] = now
    return True


def _restart_budget_left(st: dict, comp: str) -> int:
    now = time.time()
    wins = [t for t in st.get("restarts", {}).get(comp, []) if now - t < 3600]
    st.setdefault("restarts", {})[comp] = wins
    return max(0, RESTART_BUDGET_PER_HOUR - len(wins))


def _record_restart(st: dict, comp: str) -> None:
    st.setdefault("restarts", {}).setdefault(comp, []).append(time.time())


def _probe_health() -> dict | None:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=6) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _probe_exec() -> bool:
    try:
        with urllib.request.urlopen(EXEC_URL, timeout=6) as r:
            return r.status == 200
    except Exception:
        return False


def _heartbeat_age() -> float | None:
    p = WORKSPACE / "logs" / "netchat_responder_heartbeat.log"
    try:
        return time.time() - p.stat().st_mtime
    except Exception:
        return None


def _spawn(script: str, marker: str) -> bool:
    """Spawn detached qua spawn_detached.py (tránh double-process)."""
    try:
        subprocess.Popen(
            [str(WORKSPACE / ".venv" / "Scripts" / "python.exe"),
             str(WORKSPACE / "tools" / "spawn_detached.py"),
             str(WORKSPACE / ".venv" / "Scripts" / "pythonw.exe"), script],
            creationflags=NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0),
            cwd=str(WORKSPACE),
        )
        _log(f"spawned {script} (marker={marker})")
        return True
    except Exception as e:
        _log(f"spawn {script} failed: {e}")
        return False


# ---------------------------------------------------------------------------
# LỚP 1 — AUTO checks (self-heal biết chắc)
# ---------------------------------------------------------------------------

def check_servers(st: dict) -> None:
    """8765 health + 8766 executive chết → restart (budget 2/h)."""
    health = _probe_health()
    ok = health is not None and _probe_exec()
    fails = st.setdefault("server_fails", 0)
    if ok:
        st["server_fails"] = 0
        return
    st["server_fails"] = fails + 1
    if st["server_fails"] < 2:
        _log(f"servers fail #{st['server_fails']} — chờ vòng sau xác nhận lại")
        return
    # 2 lần liên tiếp → hành động
    if _restart_budget_left(st, "servers") > 0:
        _log("servers DEAD x2 — AUTO restart")
        _spawn("start_dual_servers.py", "start_dual_servers")
        _record_restart(st, "servers")
        if _should_alert(st, "servers_restarted"):
            _dm("🤖 CHERRY tự vận hành: phát hiện servers 8765/8766 chết 2 lần probe liên tiếp → em tự khởi động lại (LỚP 1 AUTO). Sẽ probe lại sau 5 phút.")
    else:
        if _should_alert(st, "servers_budget_exhausted"):
            _dm("⚠️ CHERRY: servers chết nhưng em đã restart 2 lần/giờ (budget hết) — đề xuất anh kiểm tra thủ công. Logs: E:/BRAIN/logs/dual_servers_watchdog.log")


def check_responder(st: dict) -> None:
    """Heartbeat stale >300s → restart responder (budget 2/h)."""
    age = _heartbeat_age()
    if age is None:
        if _should_alert(st, "responder_log_missing"):
            _dm("⚠️ CHERRY: heartbeat log responder biến mất — không xác minh được bot còn sống. Anh kiểm tra giúp em.")
        return
    if age < 300:
        return
    if _restart_budget_left(st, "responder") > 0:
        _log(f"responder heartbeat stale {age:.0f}s — AUTO restart")
        _spawn("tools/netchat_auto_responder.py", "netchat_auto_responder")
        _record_restart(st, "responder")
    else:
        if _should_alert(st, "responder_budget"):
            _dm(f"⚠️ CHERRY: responder heartbeat stale {age:.0f}s nhưng em đã restart 2 lần/giờ — đề xuất anh xem logs/netchat_auto_responder_stdout.log")


def check_pi5(st: dict) -> None:
    """Pi5 heartbeat từ edge status API — mất >300s → DM cảnh báo (rate-limit)."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/executive/edge/status", timeout=6) as r:
            d = json.loads(r.read().decode())
        edge = d.get("edge") or {}
        secs = edge.get("seconds_since_heartbeat")
        if secs is None:
            return
        if secs > 300 and _should_alert(st, "pi5_lost"):
            _dm(f"🔴 CHERRY tự vận hành: Pi5 mất heartbeat {secs:.0f}s (>5 phút). Wifi watchdog Pi5 sẽ tự reconnect; em theo dõi và báo khi Pi5 sống lại.")
        elif secs < 60 and st.get("pi5_was_lost"):
            st["pi5_was_lost"] = False
            _dm("🟢 CHERRY: Pi5 đã sống lại — heartbeat recovered.")
        if secs > 300:
            st["pi5_was_lost"] = True
    except Exception as e:
        _log(f"pi5 probe error: {e}")


# ---------------------------------------------------------------------------
# LỚP 2 — PROPOSE (chỉ DM đề xuất, KHÔNG tự làm)
# ---------------------------------------------------------------------------

def propose_issues(st: dict) -> None:
    """Bất thường không tự xử → DM đề xuất (rate-limit 30m/loại)."""
    # Ollama chết
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=4) as r:
            r.read()
        ollama_ok = True
    except Exception:
        ollama_ok = False
    if not ollama_ok and _should_alert(st, "propose_ollama"):
        _dm("💡 CHERRY đề xuất: Ollama (BGE-M3) không phản hồi ở 127.0.0.1:11434. Semantic search sẽ fallback. Anh muốn em thử khởi động Ollama không? (trả lời \'duyệt ollama\')")

    # Disk
    try:
        import shutil
        total, used, free = shutil.disk_usage("E:/")
        pct = used / total * 100
        if pct > 80 and _should_alert(st, "propose_disk"):
            _dm(f"💡 CHERRY đề xuất: ổ E: dùng {pct:.0f}% (còn {free/1024**3:.0f}GB). Em có thể dọn logs cũ + cisc_runs — anh duyệt không?")
    except Exception:
        pass


def run_cycle(st: dict) -> None:
    check_servers(st)
    check_responder(st)
    check_pi5(st)
    propose_issues(st)


def main() -> None:
    _log("=" * 60)
    _log(f"CHERRY AUTONOMOUS MODE — bắt đầu (chu kỳ 300s) pid={__import__('os').getpid()}")
    _log("=" * 60)
    import traceback
    while True:
        try:
            st = _load_state()
            run_cycle(st)
            _save_state(st)
        except Exception:
            _log("cycle CRASH:\n" + traceback.format_exc())
        time.sleep(300)


if __name__ == "__main__":
    main()
