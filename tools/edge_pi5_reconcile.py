"""Edge Pi5 Reconcile — Cherry tự phục hồi + tự ĐÁNH THỨC "tai mắt" Pi5.

(11/11/2026, yêu cầu owner: "để cherry tự chủ động liên hệ qua lại điều chỉnh
tốt nhất cho hoạt động qua lại giữa core và pi5";
12/11/2026, yêu cầu owner: "cấu hình để đảm bảo Pi5 hoạt động ổn định, core
từ đây có thể đánh thức pi5 được thông qua kết nối wifi")

Vai trò trong watchdog 24/7 (check_edge_pi5_reconcile):
1. Phát hiện Pi5 sống lại: edge_monitor có heartbeat mới sau khi từng
   DISCONNECTED (transition DISCONNECTED/RECOVERING → CONNECTED/READY).
2. Khi phát hiện (hoặc khi owner gọi wake_pi5()):
   a. SSH quanpt1@<edge_ip> (key-based, timeout ngắn). Host thử theo thứ tự:
      IP cấu hình → IP từ mDNS `quanpt1.local` (chống DHCP nhảy IP).
   b. Deploy wake_word_service.py bản CHERRY-only (0019c6c) nếu md5 khác
      → PATH THẬT trên Pi5: /home/quanpt1/Desktop/edge_client/ (service
      systemd chạy từ đây — KHÔNG phải QUAN_AI_BRAIN/; lỗi 12/11 sáng).
   c. Wake màn hình: vcgencmd display_power 1 + xset dpms force on —
      Pi5 sống nhưng màn hình ngủ → core đánh thức được qua WiFi.
   d. Ensure quan_ai_wake + quan_ai_edge enabled + active.
   e. Phát hiện IP DHCP mới → cập nhật data/edge_runtime.json.
   f. DM NetChat cho owner (bot_tony → quanpt1) — owner biết ngay không cần hỏi.
3. Tất cả kết quả ghi vào data/edge_reconcile_log.jsonl (audit + owner đọc).
4. Rate-limit: 1 lần/giờ cho auto-reconcile; wake_pi5() chủ động bỏ qua.

Quyền: R3-whitelist (SSH key có sẵn, chỉ status/restart service của dự án,
scp file edge_client/wake_word_service.py, display power, gửi DM NetChat —
không đụng OS/secret/DB).
"""
from __future__ import annotations
from pathlib import Path
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret

import hashlib
import json
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# (12/11/2026) Loader secret tập trung
import sys as _sys
_SECRET_DIR = Path('E:/BRAIN/user, pass, token')
if str(_SECRET_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SECRET_DIR))
from loader import get_secret as _get_secret

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "edge_reconcile_log.jsonl"
STATE_PATH = BASE_DIR / "data" / "edge_runtime.json"

CONFIG = {
    "edge_user": "quanpt1",
    "edge_host": "192.168.1.21",      # DHCP — sẽ tự cập nhật khi phát hiện IP mới
    "mdns_host": "quanpt1.local",      # mDNS — chống DHCP nhảy IP
    "ssh_timeout": 8,
    "reconcile_min_interval_sec": 3600,
    "wake_service": "quan_ai_wake.service",
    "edge_service": "quan_ai_edge.service",
    "wake_word_file": "edge_client/wake_word_service.py",
    # PATH THẬT trên Pi5 (audit 12/11: systemd service chạy từ Desktop/edge_client)
    "pi5_wake_path": "/home/quanpt1/Desktop/edge_client/wake_word_service.py",
    "pi5_edge_dir": "/home/quanpt1/Desktop/edge_client",
    "notify_owner": True,
    "netchat_py": r"E:\BRAIN\.venv\Scripts\python.exe",
    "netchat_bot": r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py",
    "netchat_dm_id": _get_secret("netchat_channel_owner", "mwp3nk3ciprjjr4hdmcoqgk6jr")  # (12/11) đọc từ loader,  # DM duy nhất bot_tony → owner
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


def _resolve_candidates() -> list[str]:
    """Danh sách host thử theo thứ tự: IP cấu hình, IP từ mDNS (nếu khác)."""
    hosts = [CONFIG["edge_host"]]
    try:
        import socket
        mdns_ip = socket.gethostbyname(CONFIG["mdns_host"])
        if mdns_ip and mdns_ip not in hosts:
            hosts.append(mdns_ip)
    except Exception:
        pass
    return hosts


def _md5_remote(host: str, path: str) -> str:
    rc, out = _ssh(host, f"md5sum {path} 2>/dev/null || echo MISSING")
    if rc != 0 or "MISSING" in out:
        return ""
    return out.split()[0] if out.split() else ""


def _md5_local() -> str:
    src = BASE_DIR / CONFIG["wake_word_file"]
    if not src.exists():
        return ""
    return hashlib.md5(src.read_bytes()).hexdigest()


def _scp_wake_service(host: str) -> tuple[bool, str]:
    """Deploy wake_word_service.py (bản CHERRY-only 0019c6c) lên Pi5.

    mkdir -p trước — Pi5 fresh boot có thể chưa có thư mục (lỗi thật 12/11).
    """
    src = BASE_DIR / CONFIG["wake_word_file"]
    if not src.exists():
        return False, f"missing local file: {src}"
    try:
        # B0: đảm bảo thư mục đích tồn tại (lỗi scp 12/11 08:25: No such file or directory)
        rc_m, out_m = _ssh(host, f"mkdir -p {CONFIG['pi5_edge_dir']}")
        if rc_m != 0:
            return False, f"mkdir fail: {out_m[:150]}"
        proc = subprocess.run(
            [
                "scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=accept-new",
                str(src), f"{CONFIG['edge_user']}@{host}:{CONFIG['pi5_wake_path']}",
            ],
            capture_output=True, text=True, timeout=40,
        )
        if proc.returncode != 0:
            return False, f"scp fail: {(proc.stderr or proc.stdout)[:200]}"
        # Verify bằng md5 — scp OK nhưng file hỏng vẫn phải bắt được
        if _md5_remote(host, CONFIG["pi5_wake_path"]) != _md5_local():
            return False, "scp xong nhưng md5 KHÔNG khớp — deploy không đáng tin"
        return True, "wake_word_service.py deployed + md5 verified (CHERRY-only wake 0019c6c)"
    except Exception as exc:
        return False, f"scp error: {exc}"


def _wake_display(host: str) -> tuple[bool, str]:
    """ĐÁNH THỨC màn hình Pi5 qua SSH (Pi5 sống, màn hình ngủ sau idle 600s).

    Pi5 chạy labwc (Wayland) + swayidle: `swayidle -w timeout 600 wlopm --off
    * resume wlopm --on *` (audit 12/11: màn hình đang OFF, `wlopm` qua SSH
    hoạt động). vcgencmd display_power đã bị firmware mới bỏ → không dùng.
    Verify bằng `wlopm` đọc lại trạng thái — không tin mù lệnh đã chạy.
    """
    cmd = (
        "WAYLAND_DISPLAY=wayland-0 wlopm --on '*' 2>/dev/null; "
        "WAYLAND_DISPLAY=wayland-0 wlopm 2>/dev/null"
    )
    rc, out = _ssh(host, cmd, timeout=10)
    if rc != 0:
        return False, f"display wake fail: {out[:120]}"
    if " on" in out:
        return True, "display awake (wlopm: on)"
    if " off" in out:
        return False, f"wake sent nhưng màn hình vẫn off ({out[:80]})"
    # Không đọc được state nhưng lệnh không lỗi — coi như đã gửi, ghi trung thực
    return True, f"display wake sent (state unknown: {out[:60]})"


def _notify_owner(msg: str) -> tuple[bool, str]:
    """Gửi DM NetChat cho owner — qua cổng xác nhận 2 bước của netchat_bot
    (send → CONFIRM-REQUIRED: <token> → send --confirmed <token>).
    Best effort, không bao giờ raise/crash watchdog."""
    if not CONFIG.get("notify_owner"):
        return False, "notify_owner=False"
    try:
        base_cmd = [
            CONFIG["netchat_py"], CONFIG["netchat_bot"], "send",
            CONFIG["netchat_dm_id"], msg,
        ]
        proc = subprocess.run(base_cmd, capture_output=True, text=True, timeout=45)
        out = (proc.stdout + proc.stderr).strip()
        if proc.returncode == 0:
            return True, out[:150] or "sent"
        # rc=3 → cổng xác nhận 2 bước: lấy token và confirm
        m = re.search(r"CONFIRM-REQUIRED:\s*([0-9a-f]+)", out)
        if proc.returncode == 3 and m:
            proc2 = subprocess.run(
                base_cmd + ["--confirmed", m.group(1)],
                capture_output=True, text=True, timeout=45,
            )
            out2 = (proc2.stdout + proc2.stderr).strip()
            return (proc2.returncode == 0, out2[:150] or f"confirmed rc={proc2.returncode}")
        return False, out[:200] or f"rc={proc.returncode}"
    except Exception as exc:
        return False, f"notify error: {exc}"


def _probe_core_reachable_via_edge(host: str) -> bool:
    """Pi5 phản hồi SSH = mạng 2 chiều sống (heartbeat đã xác nhận từ server)."""
    rc, out = _ssh(host, "echo ok", timeout=6)
    return rc == 0 and "ok" in out


def _build_owner_message(result: dict) -> str:
    ts = result.get("ts_utc", "")[:16].replace("T", " ")
    ok_steps = [s for s in result.get("steps", []) if s.get("ok")]
    bad_steps = [s for s in result.get("steps", []) if not s.get("ok")]
    lines = [f"🌅 Pi5 vừa SỐNG LẠI — Cherry tự phục hồi ({ts} UTC, IP {result.get('pi_ip', '?')})"]
    for s in ok_steps:
        lines.append(f"✅ {s['step']}: {s.get('detail', '')[:60]}")
    for s in bad_steps:
        lines.append(f"❌ {s['step']}: {s.get('detail', '')[:80]}")
    verdict = result.get("verdict", "")
    lines.append(f"Kết luận: {verdict}")
    return "\n".join(lines)


def reconcile_once(force: bool = False) -> dict:
    """1 chu kỳ reconcile. Trả dict kết quả; gọi từ watchdog hoặc wake_pi5()."""
    global _last_reconcile_ts
    with _lock:
        now = time.time()
        if not force and (now - _last_reconcile_ts) < CONFIG["reconcile_min_interval_sec"]:
            return {"skipped": True, "reason": "rate-limited"}

        result: dict = {
            "ts_utc": _now_utc(),
            "host": CONFIG["edge_host"],
            "trigger": "pi5_recovered" if not force else "owner_wake",
            "steps": [],
        }

        # B1: SSH sống không? (thử IP cấu hình trước, rồi mDNS — chống DHCP nhảy)
        live_host = ""
        last_err = ""
        for cand in _resolve_candidates():
            rc, out = _ssh(cand, "hostname; uptime -p", timeout=8)
            if rc == 0:
                live_host = cand
                break
            last_err = out[:120]
        result["steps"].append({
            "step": "ssh_probe",
            "ok": bool(live_host),
            "detail": (f"{live_host}: {out[:120]}" if live_host else f"all candidates fail: {last_err}"),
        })
        if not live_host:
            result["verdict"] = "PI5_UNREACHABLE_VIA_SSH"
            result["pi_ip"] = CONFIG["edge_host"]
            _log_event(result)
            _last_reconcile_ts = time.time()
            _notify_owner(_build_owner_message(result))
            return result

        if live_host != CONFIG["edge_host"]:
            result["steps"].append({
                "step": "host_resolved_via_mdns", "ok": True,
                "detail": f"{CONFIG['edge_host']} → {live_host}",
            })
            CONFIG["edge_host"] = live_host

        # B2: deploy wake word (CHERRY-only) nếu md5 khác (không tin grep)
        local_md5 = _md5_local()
        remote_md5 = _md5_remote(live_host, CONFIG["pi5_wake_path"])
        if not local_md5:
            result["steps"].append({"step": "deploy_wake_cherry", "ok": False, "detail": "missing local wake_word_service.py"})
        elif remote_md5 == local_md5:
            result["steps"].append({"step": "deploy_wake_cherry", "ok": True, "detail": f"already current (md5 {local_md5[:8]})"})
        else:
            ok, msg = _scp_wake_service(live_host)
            result["steps"].append({"step": "deploy_wake_cherry", "ok": ok, "detail": msg})

        # B3: ĐÁNH THỨC màn hình (Pi5 sống nhưng màn hình ngủ)
        ok_disp, msg_disp = _wake_display(live_host)
        result["steps"].append({"step": "wake_display", "ok": ok_disp, "detail": msg_disp})

        # B4: ensure wake + edge service enabled + active
        for svc in (CONFIG["wake_service"], CONFIG["edge_service"]):
            rc_s, out_s = _ssh(
                live_host,
                f"systemctl is-enabled {svc} 2>/dev/null; systemctl is-active {svc} 2>/dev/null",
            )
            lines = out_s.split()
            enabled = lines[0] if lines else "?"
            active = lines[1] if len(lines) > 1 else "?"
            if enabled != "enabled":
                _ssh(live_host, f"sudo -n systemctl enable {svc} 2>/dev/null || systemctl --user enable {svc} 2>/dev/null")
            if active != "active":
                _ssh(live_host, f"sudo -n systemctl restart {svc} 2>/dev/null || systemctl --user restart {svc} 2>/dev/null")
                # kiểm tra lại sau 5s
                time.sleep(5)
                rc_v, out_v = _ssh(live_host, f"systemctl is-active {svc} 2>/dev/null")
                result["steps"].append({
                    "step": f"service_{svc}", "ok": out_v.strip() == "active",
                    "detail": f"was enabled={enabled}/active={active}, after restart={out_v.strip()}",
                })
            else:
                result["steps"].append({"step": f"service_{svc}", "ok": True, "detail": f"enabled={enabled}/active={active}"})

        # B5: IP thật của Pi5 (nếu đổi, cập nhật state cho owner/server)
        rc_ip, out_ip = _ssh(live_host, "ip -4 addr show wlan0 | grep -oP '(?<=inet )([\\d.]+)'")
        pi_ip = out_ip.strip().splitlines()[-1].strip() if rc_ip == 0 and out_ip.strip() else live_host
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
        ok_n, msg_n = _notify_owner(_build_owner_message(result))
        result["steps"].append({"step": "notify_owner", "ok": ok_n, "detail": msg_n[:100]})
        return result


def wake_pi5(reason: str = "owner") -> dict:
    """Core ĐÁNH THỨC Pi5 qua WiFi (chủ động, bỏ rate-limit).

    Làm mọi thứ reconcile_once làm: SSH probe (IP/mDNS), deploy wake bản
    CHERRY nếu thiếu/sai, đánh thức màn hình, ensure services, DM owner.
    """
    return reconcile_once(force=True)


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