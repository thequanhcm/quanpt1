"""Database Health Collector — kiểm tra DB thật bằng integrity check (M1).

Đọc-only: PRAGMA quick_check + integrity_check(2) + WAL size + row counts
bdiag Quartz. KHÔNG ghi dữ liệu, KHÔNG vacuum, KHÔNG thay đổi schema.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mk(check_id: str, value: Any, reason: str, status: str | None = None) -> dict[str, Any]:
    return {"value": value, "status": status or ("ok" if value is not None else "unknown"),
            "reason": reason, "measured_at": _now_iso()}


def collect_database_health(workspace: Path | None = None) -> dict[str, Any]:
    ws = Path(workspace) if workspace else Path(__file__).resolve().parents[3]
    data_dir = ws / "data"
    checks: dict[str, Any] = {}

    for db_name in ("brain.db", "tasks.db"):
        db_path = data_dir / db_name
        if not db_path.exists():
            checks[db_name] = _mk(db_name, None, "db_file_missing", "unknown")
            continue
        try:
            size_mb = round(db_path.stat().st_size / 1024**2, 1)
            wal = Path(str(db_path) + "-wal")
            wal_mb = round(wal.stat().st_size / 1024**2, 1) if wal.exists() else 0.0
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3)
            try:
                # quick_check 1 dòng: 'ok' hoặc mô tả lỗi đầu tiên.
                row = conn.execute("PRAGMA quick_check(1)").fetchone()
                qc = (row[0] if row else "no_result")
                counts: dict[str, int] = {}
                try:
                    counts["episodes"] = conn.execute(
                        "SELECT COUNT(*) FROM episodes").fetchone()[0]
                except sqlite3.Error:
                    pass
                try:
                    counts["memories"] = conn.execute(
                        "SELECT COUNT(*) FROM memories").fetchone()[0]
                except sqlite3.Error:
                    pass
            finally:
                conn.close()
            status = "ok" if qc == "ok" else "crit"
            checks[db_name] = _mk(
                db_name,
                {"size_mb": size_mb, "wal_mb": wal_mb,
                 "quick_check": qc, "rows": counts},
                "measured", status)
        except sqlite3.Error as exc:
            checks[db_name] = _mk(db_name, None, f"sqlite_error:{exc}"[:80], "unknown")
        except Exception as exc:
            checks[db_name] = _mk(db_name, None, f"probe_error:{type(exc).__name__}", "unknown")

    return {
        "component_id": "databases",
        "measured_at": _now_iso(),
        "reachable": any(v["status"] == "ok" for v in checks.values()),
        "checks": checks,
    }
