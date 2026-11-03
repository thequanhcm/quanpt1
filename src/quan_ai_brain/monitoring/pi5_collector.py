"""Pi5 Health Collector — probe Raspberry Pi 5 qua SSH key sẵn có (M1.2).

Đọc-only: chỉ chạy lệnh đọc (vcgencmd, free, df, bluetoothctl info, systemctl
is-active). Không cài, không restart, không đổi cấu hình trên Pi5.

SSH dùng BatchMode (key auth, không bao giờ hỏi mật khẩu — không lưu key
trong code). Timeout chặt để không treo thread server.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Any

PI5_HOST = "quanpt1@100.100.83.59"
_SSH_TIMEOUT = 12.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ssh_run(remote_cmd: str, timeout: float = _SSH_TIMEOUT) -> tuple[int, str]:
    """Chạy 1 lệnh đọc trên Pi5. Trả (exit_code, stdout). Không raise ra ngoài."""
    try:
        proc = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
             PI5_HOST, remote_cmd],
            capture_output=True, text=True, timeout=timeout, errors="replace",
        )
        return proc.returncode, (proc.stdout or "").strip()
    except Exception as exc:
        return 255, f"probe_error:{type(exc).__name__}"


def collect_pi5_health() -> dict[str, Any]:
    """Snapshot sức khỏe Pi5 thật. Mỗi check độc lập — lỗi 1 check không
    ảnh hưởng check khác; thiếu dữ liệu → status 'unknown' (fail-honest)."""
    checks: dict[str, Any] = {}

    # --- Nhiệt độ SoC ---
    code, out = _ssh_run("vcgencmd measure_temp")
    temp_c = None
    if code == 0 and "temp=" in out:
        try:
            temp_c = float(out.split("temp=")[1].split("'")[0])
        except (ValueError, IndexError):
            temp_c = None
    checks["soc_temp_c"] = _mk("soc_temp_c", temp_c, "measured" if temp_c is not None
                               else f"parse_error:{out[:60]}")

    # --- Throttled flags (0x0 = ổn) ---
    code, out = _ssh_run("vcgencmd get_throttled")
    throttled_hex = None
    if code == 0 and "throttled=" in out:
        throttled_hex = out.split("throttled=")[1].strip()
    ok = throttled_hex in ("0x0", "0x0.")
    checks["throttled"] = _mk("throttled", throttled_hex,
                              "measured" if throttled_hex is not None else "parse_error",
                              status_override="ok" if ok else ("warn" if throttled_hex else "unknown"))

    # --- RAM ---
    code, out = _ssh_run("free -m | awk '/Mem:/ {print $2, $3, $7}'")
    ram = None
    if code == 0 and out:
        parts = out.split()
        if len(parts) == 3:
            try:
                total, used, avail = (int(x) for x in parts)
                ram = {"total_mb": total, "used_mb": used,
                       "available_mb": avail,
                       "used_pct": round(used * 100.0 / total, 1) if total else None}
            except ValueError:
                ram = None
    checks["ram_mb"] = _mk("ram_mb", ram, "measured" if ram else "parse_error")

    # --- Disk root ---
    code, out = _ssh_run("df -BM / | awk 'NR==2 {print $2, $3, $4, $5}'")
    disk = None
    if code == 0 and out:
        parts = out.split()
        if len(parts) == 4:
            try:
                disk = {"total_mb": int(parts[0].rstrip("M")),
                        "used_mb": int(parts[1].rstrip("M")),
                        "free_mb": int(parts[2].rstrip("M")),
                        "used_pct": parts[3]}
            except (ValueError, IndexError):
                disk = None
    checks["disk_root"] = _mk("disk_root", disk, "measured" if disk else "parse_error")

    # --- Bluetooth speaker (SRS-XB33) connected? ---
    code, out = _ssh_run(
        "bluetoothctl info 6C:47:60:58:EF:93 2>/dev/null | grep -i connected")
    bt = None
    if code == 0 and out:
        bt = "yes" if "yes" in out.lower() else "no"
    checks["bt_speaker_connected"] = _mk(
        "bt_speaker_connected", bt,
        "measured" if bt is not None else "parse_error",
        status_override=("ok" if bt == "yes" else "warn") if bt else "unknown")

    # --- Services TONY trên Pi5 ---
    code, out = _ssh_run(
        "for s in quan_ai_edge quan_ai_wake quan_ai_kiosk_guard; do "
        "printf '%s=%s ' \"$s\" \"$(systemctl is-active $s 2>/dev/null)\"; done")
    svc = {}
    if code == 0 and "quan_ai_edge=" in out:
        for pair in out.split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                svc[k] = v
    checks["services"] = _mk("services", svc or None,
                             "measured" if svc else "parse_error")

    # --- Uptime (phát hiện reboot mới) ---
    code, out = _ssh_run("uptime -s")
    # '2026-11-01 07:16:40' — có 'T' sau khi chuẩn ISO; check dấu '-' là đủ
    boot_iso = out if code == 0 and "-" in out and ":" in out else None
    checks["boot_time"] = _mk("boot_time", boot_iso,
                              "measured" if boot_iso else "parse_error")

    return {
        "component_id": "pi5_edge",
        "measured_at": _now_iso(),
        "reachable": any(v["status"] != "unknown" for v in checks.values()),
        "checks": checks,
    }


def _mk(check_id: str, value: Any, reason: str, status_override: str | None = None) -> dict[str, Any]:
    status = "unknown"
    if status_override is not None:
        status = status_override
    elif value is not None:
        status = "ok"
    return {
        "value": value,
        "status": status,
        "reason": reason,
        "measured_at": _now_iso(),
    }
