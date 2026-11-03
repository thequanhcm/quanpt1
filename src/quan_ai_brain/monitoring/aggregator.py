"""Health Snapshot Aggregator — hợp nhất PC + Pi5 + Network + Services +
Databases + Voice, kèm lịch sử telemetry (M1.3 mở rộng).

Một nơi duy nhất để server hỏi "hệ thống đang thế nào": gọi collectors,
tổng hợp theo Health State Machine, cache ngắn (TTL) để dashboard poll
liên tục không gây tải lặp, và ghi lịch sử vào data/health_history.db
(read-only đối với hệ thống: chỉ thêm bản ghi telemetry của riêng nó).

Đọc-only đối với hệ điều hành/cấu hình. Không khởi động thread khi import.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.monitoring import (
    database_collector,
    network_collector,
    pc_collector,
    pi5_collector,
    service_collector,
    voice_collector,
)
from quan_ai_brain.monitoring.health_state import (
    CRITICAL,
    MAINTENANCE,
    NORMAL,
    UNKNOWN,
    WARNING,
)

_CACHE_TTL_SEC = 45.0
_HISTORY_DB = "health_history.db"
_HISTORY_KEEP_ROWS = 2000

# Ngưỡng mặc định (tường minh, chỉnh được qua env sau này — KHÔNG hardcode
# trong collector). Format: {check_id: (warn_expr, crit_expr)}
PC_THRESHOLDS: dict[str, tuple[str, str]] = {
    "cpu_percent": (">=85", ">=97"),
    "ram_percent": (">=85", ">=95"),
    "disk_percent": (">=85", ">=95"),
    "server_rss_mb": (">=1200", ">=2000"),
}
PI5_THRESHOLDS: dict[str, tuple[str, str]] = {
    "soc_temp_c": (">=70", ">=80"),
    "ram_mb.used_pct": (">=85", ">=95"),
    "disk_root.used_pct": (">=85", ">=95"),
    # Loa BT tắt = ngoại vi thiếu (WARNING), không phải hệ thống hỏng.
    "bt_speaker_connected": ("==no", ""),
}
NETWORK_THRESHOLDS: dict[str, tuple[str, str]] = {
    "pc_to_pi5_rtt_ms": (">=150", ">=500"),
    "pc_to_pi5_loss_pct": (">1", ">=50"),
}
SERVICE_THRESHOLDS: dict[str, tuple[str, str]] = {
    "executive_server": ("==down", "==down"),
    "dashboard": ("==down", "==down"),
    "netchat_responder_heartbeat": (">=150", ">=600"),
    "learning_daemon_heartbeat": (">=150", ">=600"),
}
VOICE_THRESHOLDS: dict[str, tuple[str, str]] = {
    "stt_engine": ("==unavailable", "==unavailable"),
    "llm_netmind": ("==UNKNOWN", "==DOWN"),
    "tts_engine": ("==unavailable", "==unavailable"),
}

COMPONENT_THRESHOLDS = {
    "pc": PC_THRESHOLDS,
    "pi5": PI5_THRESHOLDS,
    "network": NETWORK_THRESHOLDS,
    "services": SERVICE_THRESHOLDS,
    "voice": VOICE_THRESHOLDS,
    # databases: quick_check==='ok' đã là status tầng đo; không ngưỡng thêm.
}


def _apply_thresholds(checks: dict[str, Any], thresholds: dict[str, tuple[str, str]]) -> dict[str, Any]:
    """Gắn status NORMAL/WARNING/CRITICAL/UNKNOWN cho từng check theo ngưỡng.

    checks: {check_id: {value, status, reason, measured_at}} — 'status' tầng
    đo ('ok'|'warn'|...) được nâng cấp thành phân loại mức hệ thống.
    """
    out: dict[str, Any] = {}
    for check_id, info in checks.items():
        value = info.get("value")
        severity = _classify_check(check_id, value, thresholds)
        entry = dict(info)
        entry["severity"] = severity
        out[check_id] = entry
    return out


def _classify_check(check_id: str, value: Any, thresholds: dict[str, tuple[str, str]]) -> str:
    rule = thresholds.get(check_id)
    if value is None:
        return UNKNOWN
    if rule is None:
        return NORMAL
    warn_expr, crit_expr = rule
    for expr, sev in ((crit_expr, CRITICAL), (warn_expr, WARNING)):
        if not expr:
            continue
        for op in (">=", "<=", "==", "!=", ">", "<"):
            if expr.startswith(op):
                rhs = expr[len(op):].strip()
                break
        else:
            continue
        try:
            left, right = float(value), float(rhs)
        except (TypeError, ValueError):
            left, right = str(value), rhs
        if op == ">=" and left >= right:
            return sev
        if op == "<=" and left <= right:
            return sev
        if op == ">" and left > right:
            return sev
        if op == "<" and left < right:
            return sev
        if op == "==" and left == right:
            return sev
        if op == "!=" and left != right:
            return sev
    return NORMAL


def classify_measured_status(measured: str | None) -> str:
    """Map status tầng đo ('ok'/'warn'/'crit'/'unknown') sang mức hệ thống."""
    return {
        "ok": NORMAL,
        "warn": WARNING,
        "crit": CRITICAL,
        "unknown": UNKNOWN,
    }.get(measured or "", UNKNOWN)


class HealthAggregator:
    """Cache snapshot hợp nhất + đánh giá theo ngưỡng + lịch sử telemetry."""

    def __init__(self, workspace: Any | None = None) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, Any] | None = None
        self._cache_ts = 0.0
        self._pi5_probe: Any | None = None  # inject để test
        self._workspace = Path(workspace) if workspace else None
        self._maintenance = False  # cờ MAINTENANCE (toggle qua API owner-gated)

    # ----- lịch sử telemetry -----
    def _history_db_path(self) -> Path | None:
        ws = self._workspace or Path(__file__).resolve().parents[3]
        data = ws / "data"
        try:
            data.mkdir(parents=True, exist_ok=True)
            return data / _HISTORY_DB
        except Exception:
            return None

    def _append_history(self, snap: dict[str, Any]) -> None:
        db = self._history_db_path()
        if db is None:
            return
        try:
            compact = {
                "overall_status": snap.get("overall_status"),
                "pc": snap.get("pc", {}).get("status"),
                "pi5": snap.get("pi5", {}).get("status"),
                "network": snap.get("network", {}).get("status"),
                "services": snap.get("services", {}).get("status"),
                "databases": snap.get("databases", {}).get("status"),
                "voice": snap.get("voice", {}).get("status"),
                "rtt_ms": (snap.get("network", {}).get("checks", {})
                           .get("pc_to_pi5_rtt_ms", {}).get("value")),
                "cpu_percent": (snap.get("pc", {}).get("checks", {})
                                .get("cpu_percent", {}).get("value")),
                "ram_percent": (snap.get("pc", {}).get("checks", {})
                                .get("ram_percent", {}).get("value")),
                "soc_temp_c": (snap.get("pi5", {}).get("checks", {})
                               .get("soc_temp_c", {}).get("value")),
            }
            with sqlite3.connect(db, timeout=5) as conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS health_history (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           ts_utc TEXT NOT NULL,
                           snapshot TEXT NOT NULL)""")
                conn.execute(
                    "INSERT INTO health_history (ts_utc, snapshot) VALUES (?,?)",
                    (datetime.now(timezone.utc).isoformat(),
                     json.dumps(compact, ensure_ascii=False)))
                # Giữ DB gọn: xoá bớt row cũ vượt ngưỡng KEEP.
                conn.execute(
                    """DELETE FROM health_history WHERE id NOT IN (
                           SELECT id FROM health_history
                           ORDER BY id DESC LIMIT ?)""",
                    (_HISTORY_KEEP_ROWS,))
        except Exception:
            # Telemetry không được giết server — fail-silent có chủ đích.
            pass

    def history(self, limit: int = 120) -> list[dict[str, Any]]:
        """Đọc lịch sử telemetry gần nhất (mới nhất đầu)."""
        db = self._history_db_path()
        if db is None or not db.exists():
            return []
        try:
            with sqlite3.connect(db, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT ts_utc, snapshot FROM health_history "
                    "ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
            return [{"ts_utc": r["ts_utc"], **json.loads(r["snapshot"])}
                    for r in rows]
        except Exception:
            return []

    # ----- MAINTENANCE (owner-gated) -----
    def set_maintenance(self, enabled: bool) -> None:
        with self._lock:
            self._maintenance = bool(enabled)

    def is_maintenance(self) -> bool:
        return self._maintenance

    # ----- đo + hợp nhất -----
    def snapshot(self, force: bool = False) -> dict[str, Any]:
        with self._lock:
            if (not force and self._cache is not None
                    and time.time() - self._cache_ts < _CACHE_TTL_SEC):
                return dict(self._cache)

        pc = pc_collector.collect_pc_health()
        pi5 = (self._pi5_probe or pi5_collector.collect_pi5_health)()
        network = network_collector.collect_network_health()
        services = service_collector.collect_service_health()
        databases = database_collector.collect_database_health(self._workspace)
        voice = voice_collector.collect_voice_health()

        pc_checks = _apply_thresholds(pc.get("checks", {}), PC_THRESHOLDS)
        pi5_checks = _apply_thresholds(pi5.get("checks", {}), PI5_THRESHOLDS)
        net_checks = _apply_thresholds(network.get("checks", {}), NETWORK_THRESHOLDS)
        svc_checks = _apply_thresholds(services.get("checks", {}), SERVICE_THRESHOLDS)
        # databases + voice: dùng status tầng đo ('ok'/'warn'/'crit'/'unknown')
        db_checks = {k: {**v, "severity": classify_measured_status(v.get("status"))}
                     for k, v in databases.get("checks", {}).items()}
        voice_checks = {k: {**v, "severity": classify_measured_status(v.get("status"))}
                        for k, v in voice.get("checks", {}).items()}

        def worst(sevs: list[str]) -> str:
            if CRITICAL in sevs:
                return CRITICAL
            if WARNING in sevs:
                return WARNING
            if UNKNOWN in sevs:
                return UNKNOWN
            return NORMAL

        comp_status = {
            "pc": worst([v["severity"] for v in pc_checks.values()]) if pc_checks else UNKNOWN,
            "pi5": worst([v["severity"] for v in pi5_checks.values()]) if pi5_checks else UNKNOWN,
            "network": worst([v["severity"] for v in net_checks.values()]) if net_checks else UNKNOWN,
            "services": worst([v["severity"] for v in svc_checks.values()]) if svc_checks else UNKNOWN,
            "databases": worst([v["severity"] for v in db_checks.values()]) if db_checks else UNKNOWN,
            "voice": worst([v["severity"] for v in voice_checks.values()]) if voice_checks else UNKNOWN,
        }

        if self._maintenance:
            overall = MAINTENANCE
        else:
            overall = worst(list(comp_status.values()))

        snap = {
            "measured_at": max(
                pc.get("measured_at", ""), pi5.get("measured_at", ""),
                network.get("measured_at", ""), services.get("measured_at", ""),
                databases.get("measured_at", ""), voice.get("measured_at", "")),
            "pc": {**pc, "checks": pc_checks, "status": comp_status["pc"]},
            "pi5": {**pi5, "checks": pi5_checks, "status": comp_status["pi5"]},
            "network": {**network, "checks": net_checks, "status": comp_status["network"]},
            "services": {**services, "checks": svc_checks, "status": comp_status["services"]},
            "databases": {**databases, "checks": db_checks, "status": comp_status["databases"]},
            "voice": {**voice, "checks": voice_checks, "status": comp_status["voice"]},
            "overall_status": overall,
        }
        with self._lock:
            self._cache = snap
            self._cache_ts = time.time()
        self._append_history(snap)
        return dict(snap)


_GLOBAL_AGGREGATOR: HealthAggregator | None = None
_AGG_LOCK = threading.Lock()


def get_global_aggregator() -> HealthAggregator:
    global _GLOBAL_AGGREGATOR
    with _AGG_LOCK:
        if _GLOBAL_AGGREGATOR is None:
            _GLOBAL_AGGREGATOR = HealthAggregator()
        return _GLOBAL_AGGREGATOR
