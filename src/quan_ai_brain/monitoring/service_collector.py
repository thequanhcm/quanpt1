"""Service Health Collector — kiểm tra trạng thái service TONY bằng đo thật
(M1.4 mở rộng). Đọc-only: TCP probe + health endpoint + heartbeat file mtime.

Service kiểm tra (đều là service TONY, không đụng hệ thống):
- executive_server (8766) — GET /api/health
- dashboard (8765) — GET /api/health
- netchat_responder — heartbeat file do responder ghi (nếu có)
- learning_daemon — heartbeat file
"""
from __future__ import annotations

import glob
import json
import socket
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEARTBEAT_STALE_SEC = 150.0  # đồng bộ với watchdog hiện hành (stale 150s)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mk(check_id: str, value: Any, reason: str, status: str | None = None) -> dict[str, Any]:
    return {"value": value, "status": status or ("ok" if value is not None else "unknown"),
            "reason": reason, "measured_at": _now_iso()}


def _probe_http(port: int, path: str = "/api/health", timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            body = r.read(300).decode("utf-8", errors="replace")
        return True, body[:120]
    except Exception as exc:
        return False, f"probe_error:{type(exc).__name__}"


def _latest_mtime(pattern: str) -> float | None:
    hits = glob.glob(pattern)
    if not hits:
        return None
    return max((Path(h).stat().st_mtime for h in hits), default=None)


def collect_service_health() -> dict[str, Any]:
    checks: dict[str, Any] = {}

    # Executive server 8766 (nếu collector chạy TRONG server này, HTTP vẫn OK).
    ok, detail = _probe_http(8766)
    checks["executive_server"] = _mk(
        "executive_server", "up" if ok else "down", detail,
        "ok" if ok else "crit")

    # Dashboard 8765.
    ok, detail = _probe_http(8765)
    checks["dashboard"] = _mk(
        "dashboard", "up" if ok else "down", detail,
        "ok" if ok else "warn")

    # Heartbeat files (responder ghi heartbeat log; learning daemon chỉ có
    # activity log — dùng mtime log mới nhất của mỗi service làm bằng chứng
    # "còn sống", stale > 150s = cảnh báo).
    ws = Path(__file__).resolve().parents[3]
    hb_specs = {
        "netchat_responder_heartbeat": str(ws / "logs" / "*responder*heartbeat*"),
        "learning_daemon_heartbeat": str(ws / "logs" / "learning_daemon.py.log"),
    }
    for check_id, pattern in hb_specs.items():
        mtime = _latest_mtime(pattern)
        if mtime is None:
            checks[check_id] = _mk(check_id, None, "no_heartbeat_file", "unknown")
            continue
        age = datetime.now(timezone.utc).timestamp() - mtime
        status = "ok" if age <= HEARTBEAT_STALE_SEC else "warn"
        checks[check_id] = _mk(check_id, round(age, 1),
                               f"heartbeat_age_sec(stale_if>{HEARTBEAT_STALE_SEC})", status)

    return {
        "component_id": "services",
        "measured_at": _now_iso(),
        "reachable": all(
            c["status"] != "unknown" for c in checks.values()),
        "checks": checks,
    }
