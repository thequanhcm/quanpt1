"""Edge Pi5 Reconcile — Cherry tự phục hồi "tai mắt" khi Pi5 sống lại.

(11/11/2026, yêu cầu owner: "để cherry tự chủ động liên hệ qua lại điều chỉnh
tốt nhất cho hoạt động qua lại giữa core và pi5")

Vai trò trong watchdog 24/7 (check_edge_pi5_reconcile):
1. Phát hiện Pi5 sống lại: edge_monitor có heartbeat mới sau khi từng
   DISCONNECTED (transition DISCONNECTED/RECOVERING → CONNECTED/READY).
2. Khi phát hiện: SSH quanpt1@<edge_ip> (key-based, timeout ngắn) kiểm tra:
   a. Wake word service (quan_ai_wake.service) — deploy bản CHERRY-only
      (commit 0019c6c chưa kịp deploy lúc Pi5 offline) + ensure enable.
   b. quan_ai_edge.service — alive? (telemetry cuối 22:51 báo
      edge_daemon_alive=false ngay trước lúc sập — nghi service chết).
   c. DHCP IP mới? → cập nhật data/edge_runtime.json (auto-discovery phía
      client đã tự tìm lại core; đây chỉ để owner + server biết IP mới).
3. Tất cả kết quả ghi vào data/edge_reconcile_log.jsonl (audit + owner đọc).
4. Rate-limit: 1 lần/giờ + chỉ khi trạng thái chuyển từ DEAD → ALIVE (không
   đạp SSH liên tục khi Pi5 đang sống khỏe).

Quyền: R3-whitelist (SSH key có sẵn, chỉ status/restart service của dự án,
scp file edge_client/wake_word_service.py — không đụng OS/secret/DB).
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "edge_reconcile_log.jsonl"
STATE_PATH = BASE_DIR / "data" / "edge_runtime.json"

CONFIG = {
    "edge_user": "quanpt1",
    "edge_host": "192.168.1.21",      # DHCP — sẽ tự cập nhật khi phát hiện IP mới
    "ssh_timeout": 8,
    "reconcile_min_interval_sec": 3600,
    "wake_service": "quan_ai_wake.service",
    "edge_service": "quan_ai_edge.service",
    "wake_word_file": "edge_client/wake_word_service.py",
    "pi5_wake_path": "/home/quanpt1/QUAN_AI_BRAIN/edge_client/wake_word_service.py",
}

_lock = threading.Lock()
_last_reconcile_ts = 0.0


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_event(event: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ssh(host: str, cmd: str, timeout: int | None = None) -> tuple[int, str]:
    """SSH batch-mode (key-based) — trả (rc, output). Không bao giờ raise."""
    try:
        proc = subprocess.run(
            [
                "ssh", "-o", "BatchMode=yes",
                "-o", f"ConnectTimeout={timeout or CONFIG['ssh_timeout']}",
                "-o", "StrictHostKeyChecking=accept-new",
                f"{CONFIG['edge_user']}@{host}",
                cmd,
            ],
            capture_output=True, text=True, timeout=(timeout or CONFIG["ssh_timeout"]) + 5,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except Exception as exc:
        return 255, f"SSH error: {exc}"


def _scp_wake_service(host: str) -> tuple[bool, str]:
    """Deploy wake_word_service.py (bản CHERRY-only 0019c6c) lên Pi5."""
    src = BASE_DIR / CONFIG["wake_word_file"]
    if not src.exists():
        return False, f"missing local file: {src}"
    try:
        proc = subprocess.run(
            [
                "scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=accept-new",
                str(src), f"{CONFIG['edge_user']}@{host}:{CONFIG['pi5_wake_path']}",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return False, f"scp fail: {(proc.stderr or proc.stdout)[:200]}"
        return True, "wake_word_service.py deployed (CHERRY-only wake 0019c6c)"
    except Exception as exc:
        return False, f"scp error: {exc}"


def _probe_core_reachable_via_edge(host: str) -> bool:
    """Pi5 phản hồi SSH = mạng 2 chiều sống (heartbeat đã xác nhận từ server)."""
    rc, out = _ssh(host, "echo ok", timeout=6)
    return rc == 0 and "ok" in out


def reconcile_once(force: bool = False) -> dict:
    """1 chu kỳ reconcile. Trả dict kết quả; gọi từ watchdog."""
    global _last_reconcile_ts
    with _lock:
        now = time.time()
        if not force and (now - _last_reconcile_ts) < CONFIG["reconcile_min_interval_sec"]:
            return {"skipped": True, "reason": "rate-limited"}

        result: dict = {
            "ts_utc": _now_utc(),
            "host": CONFIG["edge_host"],
            "trigger": "pi5_recovered",
            "steps": [],
        }

        # B1: SSH sống không?
        rc, out = _ssh(CONFIG["edge_host"], "hostname; uptime -p", timeout=8)
        result["steps"].append({"step": "ssh_probe", "ok": rc == 0, "detail": out[:200]})
        if rc != 0:
            result["verdict"] = "PI5_UNREACHABLE_VIA_SSH"
            _log_event(result)
            _last_reconcile_ts = now
            return result

        # B2: deploy wake word (CHERRY-only) nếu chưa có bản CHERRY
        rc_chk, out_chk = _ssh(
            CONFIG["edge_host"],
            "grep -c 'CHERRY' /home/quanpt1/QUAN_AI_BRAIN/edge_client/wake_word_service.py 2>/dev/null || echo 0",
        )
        if out_chk.strip() == "0" or rc_chk != 0:
            ok, msg = _scp_wake_service(CONFIG["edge_host"])
            result["steps"].append({"step": "deploy_wake_cherry", "ok": ok, "detail": msg})
        else:
            result["steps"].append({"step": "deploy_wake_cherry", "ok": True, "detail": f"already CHERRY ({out_chk.strip()} refs)"})

        # B3: ensure wake + edge service enabled + active
        for svc in (CONFIG["wake_service"], CONFIG["edge_service"]):
            rc_s, out_s = _ssh(
                CONFIG["edge_host"],
                f"systemctl is-enabled {svc} 2>/dev/null; systemctl is-active {svc} 2>/dev/null",
            )
            lines = out_s.split()
            enabled = lines[0] if lines else "?"
            active = lines[1] if len(lines) > 1 else "?"
            if enabled != "enabled":
                _ssh(CONFIG["edge_host"], f"systemctl --user enable {svc} 2>/dev/null || sudo -n systemctl enable {svc} 2>/dev/null")
            if active != "active":
                _ssh(CONFIG["edge_host"], f"systemctl --user restart {svc} 2>/dev/null || sudo -n systemctl restart {svc} 2>/dev/null")
                # kiểm tra lại sau 5s
                time.sleep(5)
                rc_v, out_v = _ssh(CONFIG["edge_host"], f"systemctl is-active {svc} 2>/dev/null")
                result["steps"].append({
                    "step": f"service_{svc}", "ok": out_v.strip() == "active",
                    "detail": f"was enabled={enabled}/active={active}, after restart={out_v.strip()}",
                })
            else:
                result["steps"].append({"step": f"service_{svc}", "ok": True, "detail": f"enabled={enabled}/active={active}"})

        # B4: IP thật của Pi5 (nếu đổi, cập nhật state cho owner/server)
        rc_ip, out_ip = _ssh(CONFIG["edge_host"], "ip -4 addr show wlan0 | grep -oP '(?<=inet )([\\d.]+)'")
        pi_ip = out_ip.strip().splitlines()[-1].strip() if rc_ip == 0 and out_ip.strip() else CONFIG["edge_host"]
        if pi_ip != CONFIG["edge_host"]:
            CONFIG["edge_host"] = pi_ip
        result["pi_ip"] = pi_ip
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps({
                "pi_ip": pi_ip, "last_reconcile_utc": _now_utc(),
                "wake_deployed": any(s.get("ok") and s["step"] == "deploy_wake_cherry" for s in result["steps"]),
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass

        result["verdict"] = "RECONCILED"
        _log_event(result)
        _last_reconcile_ts = time.time()
        return result


def check_reconcile_from_core_api() -> None:
    """Bọc cho watchdog: tự lấy edge status từ core API (localhost 8766) rồi
    gọi check_edge_pi5_reconcile. Fail-honest tuyệt đối — không raise."""
    try:
        import urllib.request

        with urllib.request.urlopen(
            "http://127.0.0.1:8766/api/executive/edge/status", timeout=4
        ) as resp:
            payload = json.load(resp)
        check_edge_pi5_reconcile(payload.get("edge") or {})
    except Exception:
        pass


def check_edge_pi5_reconcile(edge_status: dict | None = None) -> None:
    """Hook cho watchdog: phát hiện DISCONNECTED → CONNECTED/READY transition.

    edge_status: dict từ edge_monitor.get_status() (state, last_heartbeat_epoch...).
    Đọc file data/edge_runtime.json ghi lại state lần trước để so transition.
    """
    try:
        if not isinstance(edge_status, dict) or not edge_status.get("paired"):
            return
        state = str(edge_status.get("state", ""))
        hb_epoch = float(edge_status.get("last_heartbeat_epoch") or 0)
        last_hb_age = time.time() - hb_epoch if hb_epoch else 1e9

        state_path = STATE_PATH
        prev_state = ""
        prev: dict = {}  # (fix 11/11) phải init trước — file chưa có → except →
        # trước đây prev unbound → NameError bị nuốt → state không bao giờ được ghi
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                prev = loaded
                prev_state = str(loaded.get("conn_state", ""))
        except (OSError, ValueError):
            pass

        # Ghi state hiện tại (cho chu kỳ sau)
        try:
            merged = prev if isinstance(prev, dict) else {}
            merged.update({"conn_state": state, "conn_state_utc": _now_utc()})
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass

        # Transition DEAD → ALIVE: trước DISCONNECTED/AUTH_FAILED, giờ READY/CONNECTED + hb mới (<60s)
        was_dead = prev_state in ("DISCONNECTED", "AUTH_FAILED", "RECOVERING", "")
        is_alive = state in ("READY", "CONNECTED") and last_hb_age < 60
        if was_dead and is_alive:
            reconcile_once()
    except Exception:
        # fail-honest: reconcile lỗi không được giết watchdog
        pass
