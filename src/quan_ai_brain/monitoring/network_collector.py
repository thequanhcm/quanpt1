"""Network Health Collector — đo RTT thật PC→Pi5 qua Tailscale (M1.6).

Đọc-only: chỉ đo, không tạo traffic lớn (1 ICMP 2 giây / lần đo), không
thay đổi cấu hình mạng. Ghi result vào _last_result để reconnection check
dùng lại mà không đo lại.

Fail-honest: không ping được → UNKNOWN kèm lý do, không đoán NORMAL.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Any

PI5_IP = "100.100.83.59"
PC_IP = "100.102.120.6"

_last_result: dict[str, Any] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mk(check_id: str, value: Any, reason: str, status: str | None = None) -> dict[str, Any]:
    return {"value": value, "status": status or ("ok" if value is not None else "unknown"),
            "reason": reason, "measured_at": _now_iso()}


def collect_network_health() -> dict[str, Any]:
    """1 ICMP tới Pi5 + phân tích output Windows ping (tiếng Việt/Tiếng Anh)."""
    global _last_result
    checks: dict[str, Any] = {}

    code = None
    out = ""
    try:
        proc = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", PI5_IP],
            capture_output=True, text=True, timeout=8, errors="replace")
        code = proc.returncode
        out = proc.stdout or ""
    except Exception as exc:
        checks["pc_to_pi5_rtt_ms"] = _mk(
            "pc_to_pi5_rtt_ms", None, f"ping_error:{type(exc).__name__}", "unknown")

    rtt = None
    lost = None
    if code == 0:
        # Windows ping trả 'time=30ms'/'time<1ms' — hỗ trợ output đa ngôn ngữ:
        for token in out.replace("<", "=<").split():
            if token.lower().startswith("time"):
                digits = "".join(ch for ch in token if ch.isdigit())
                if digits:
                    rtt = float(digits)
                break
        lost = 0.0
    elif code is not None:
        lost = 100.0
    if rtt is not None or lost is not None:
        checks["pc_to_pi5_rtt_ms"] = _mk(
            "pc_to_pi5_rtt_ms", rtt,
            "measured" if rtt is not None else "ping_lost",
            "ok" if rtt is not None else "warn")
        checks["pc_to_pi5_loss_pct"] = _mk(
            "pc_to_pi5_loss_pct", lost, "measured",
            "ok" if lost == 0.0 else "warn")
    checks.setdefault("pc_to_pi5_rtt_ms", _mk(
        "pc_to_pi5_rtt_ms", None, "no_measurement", "unknown"))

    # Tailscale interface có mặt không (đọc-only):
    try:
        import psutil  # optional
        addrs = psutil.net_if_addrs()
        ts_up = any("Tailscale" in name or "ts" == name.lower()[:2] for name in addrs)
        checks["tailscale_interface"] = _mk(
            "tailscale_interface", "up" if ts_up else "down", "measured",
            "ok" if ts_up else "warn")
    except Exception as exc:
        checks["tailscale_interface"] = _mk(
            "tailscale_interface", None, f"probe_error:{type(exc).__name__}", "unknown")

    snap = {
        "component_id": "network",
        "measured_at": _now_iso(),
        "reachable": checks["pc_to_pi5_rtt_ms"]["status"] == "ok",
        "checks": checks,
    }
    _last_result = snap
    return snap


def was_connected() -> bool | None:
    """Kết quả đo gần nhất (không đo lại). None nếu chưa từng đo."""
    if _last_result is None:
        return None
    return bool(_last_result.get("reachable"))
