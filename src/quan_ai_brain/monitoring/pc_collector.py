"""PC Health Collector — thu số liệu máy chủ thật bằng psutil (M1.1).

Đọc-only tuyệt đối: không ghi file, không đổi cấu hình, không giết process.
psutil là optional: môi trường thiếu psutil → trả UNKNOWN (fail-honest),
không crash server.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:  # optional dependency — kiểm tra tại import, không hard-require
    import psutil  # type: ignore
except Exception:  # pragma: no cover - môi trường không có psutil
    psutil = None  # type: ignore

from quan_ai_brain.monitoring.health_state import CheckResult, UNKNOWN


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unknown(check_id: str, why: str) -> CheckResult:
    return CheckResult(check_id=check_id, value=None, status="unknown",
                       reason=why, measured_at=_now_iso())


def collect_pc_health() -> dict[str, Any]:
    """Thu thập snapshot sức khỏe PC. Trả dict có schema ổn định:

    {component_id, measured_at, available, checks: {check_id: CheckResult-dict}}
    """
    checks: dict[str, Any] = {}

    if psutil is None:
        return {
            "component_id": "pc_host",
            "measured_at": _now_iso(),
            "available": False,
            "reason": "psutil_not_installed",
            "checks": {},
        }

    # --- CPU (interval ngắn, non-blocking tổng thể) ---
    try:
        cpu_pct = psutil.cpu_percent(interval=0.25)
        checks["cpu_percent"] = CheckResult(
            "cpu_percent", round(cpu_pct, 1), "ok", "measured", _now_iso())
    except Exception as exc:
        checks["cpu_percent"] = _unknown("cpu_percent", f"probe_error:{type(exc).__name__}")

    # --- RAM ---
    try:
        mem = psutil.virtual_memory()
        used_pct = round(mem.percent, 1)
        checks["ram_percent"] = CheckResult(
            "ram_percent", used_pct, "ok", "measured", _now_iso())
        checks["ram_available_mb"] = CheckResult(
            "ram_available_mb", round(mem.available / 1024 / 1024), "ok", "measured", _now_iso())
    except Exception as exc:
        checks["ram_percent"] = _unknown("ram_percent", f"probe_error:{type(exc).__name__}")

    # --- Disk (ổ chứa workspace) ---
    try:
        disk = psutil.disk_usage("D:\\")
        free_gb = round(disk.free / 1024**3, 1)
        total_gb = round(disk.total / 1024**3, 1)
        used_pct = round(disk.percent, 1)
        checks["disk_free_gb"] = CheckResult(
            "disk_free_gb", free_gb, "ok", "measured", _now_iso())
        checks["disk_total_gb"] = CheckResult(
            "disk_total_gb", total_gb, "ok", "measured", _now_iso())
        checks["disk_percent"] = CheckResult(
            "disk_percent", used_pct, "ok", "measured", _now_iso())
    except Exception as exc:
        checks["disk_free_gb"] = _unknown("disk_free_gb", f"probe_error:{type(exc).__name__}")

    # --- Load process chính (server python hiện tại) ---
    try:
        proc = psutil.Process()
        with proc.oneshot():
            pmem = proc.memory_info().rss / 1024**2
            pcpu = proc.cpu_percent(interval=None)
            threads = proc.num_threads()
        checks["server_rss_mb"] = CheckResult(
            "server_rss_mb", round(pmem, 1), "ok", "measured", _now_iso())
        checks["server_cpu_percent"] = CheckResult(
            "server_cpu_percent", round(pcpu, 1), "ok", "measured", _now_iso())
        checks["server_threads"] = CheckResult(
            "server_threads", threads, "ok", "measured", _now_iso())
    except Exception as exc:
        checks["server_rss_mb"] = _unknown("server_rss_mb", f"probe_error:{type(exc).__name__}")

    # --- Số process python đang chạy (phát hiện spawn chồng) ---
    try:
        py_count = 0
        for p in psutil.process_iter(["name"]):
            try:
                name = (p.info.get("name") or "").lower()
                if name.startswith("python"):
                    py_count += 1
            except Exception:
                continue
        checks["python_process_count"] = CheckResult(
            "python_process_count", py_count, "ok", "measured", _now_iso())
    except Exception as exc:
        checks["python_process_count"] = _unknown(
            "python_process_count", f"probe_error:{type(exc).__name__}")

    # --- Uptime hệ thống ---
    try:
        boot = psutil.boot_time()
        up_s = int(datetime.now(timezone.utc).timestamp() - boot)
        checks["uptime_hours"] = CheckResult(
            "uptime_hours", round(up_s / 3600, 1), "ok", "measured", _now_iso())
    except Exception as exc:
        checks["uptime_hours"] = _unknown("uptime_hours", f"probe_error:{type(exc).__name__}")

    return {
        "component_id": "pc_host",
        "measured_at": _now_iso(),
        "available": True,
        "checks": {k: {
            "value": v.value, "status": v.status, "reason": v.reason,
            "measured_at": v.measured_at,
        } for k, v in checks.items()},
    }
