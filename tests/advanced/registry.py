"""DEOM Advanced Assurance — Test Governance Center (Phần 3).

Test Registry + Evidence store thống nhất cho toàn bộ suite A–N.
SQLite riêng (data/test_governance.db khi dùng thật, tmp_path khi test) —
KHÔNG đụng database production. Không thay thế cognitive core / DEOM:
đây là sổ cái bằng chứng kiểm thử.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 18 category — Phần 3.2
TEST_CATEGORIES = (
    "UNIT",
    "INTEGRATION",
    "CONTRACT",
    "END_TO_END",
    "PROPERTY_BASED",
    "FUZZ",
    "MUTATION",
    "SECURITY",
    "ADVERSARIAL",
    "CHAOS",
    "CONCURRENCY",
    "PERFORMANCE",
    "MEMORY",
    "RECOVERY",
    "LONG_HORIZON",
    "HUMAN_IN_THE_LOOP",
    "HARDWARE",
    "ACCEPTANCE",
)

# Trạng thái xác minh — Phần 1 (không tự nâng: LIVE/OWNER chỉ owner xác nhận)
VERIFICATION_LEVELS = (
    "DESIGNED",
    "IMPLEMENTED",
    "UNIT_TESTED",
    "INTEGRATION_TESTED",
    "END_TO_END_TESTED",
    "STRESS_TESTED",
    "ADVERSARIAL_TESTED",
    "LIVE_VERIFIED",
    "OWNER_ACCEPTED",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestGovernanceError(Exception):
    """Lỗi nghiệp vụ registry (fail-honest, không nuốt)."""


class TestRegistry:
    """Sổ cái test case + evidence — 17 trường/test case, 12 trường/evidence."""

    def __init__(self, db_path: str | Path = "data/test_governance.db") -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_cases (
                    test_id TEXT PRIMARY KEY,
                    test_name TEXT NOT NULL,
                    test_category TEXT NOT NULL,
                    test_objective TEXT NOT NULL DEFAULT '',
                    target_module TEXT NOT NULL DEFAULT '',
                    risk_level TEXT NOT NULL DEFAULT 'R0',
                    preconditions TEXT NOT NULL DEFAULT '',
                    input_dataset TEXT NOT NULL DEFAULT '',
                    execution_environment TEXT NOT NULL DEFAULT 'unit',
                    expected_result TEXT NOT NULL DEFAULT '',
                    verification_method TEXT NOT NULL DEFAULT '',
                    actual_result TEXT,
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'DESIGNED',
                    regression_status TEXT NOT NULL DEFAULT 'NOT_RUN',
                    created_at TEXT NOT NULL,
                    last_executed_at TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    git_commit TEXT NOT NULL DEFAULT '',
                    software_version TEXT NOT NULL DEFAULT '',
                    environment TEXT NOT NULL DEFAULT '',
                    dataset_version TEXT NOT NULL DEFAULT '',
                    config_fingerprint TEXT NOT NULL DEFAULT '',
                    random_seed TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    result TEXT NOT NULL,
                    error TEXT,
                    logs_redacted TEXT NOT NULL DEFAULT '',
                    refs TEXT NOT NULL DEFAULT '[]',
                    runner_version TEXT NOT NULL DEFAULT ''
                )
                """
            )

    # ---------------------------------------------------------------
    # Đăng ký test case
    # ---------------------------------------------------------------
    def register(
        self,
        *,
        test_name: str,
        test_category: str,
        test_objective: str = "",
        target_module: str = "",
        risk_level: str = "R0",
        preconditions: str = "",
        input_dataset: str = "",
        execution_environment: str = "unit",
        expected_result: str = "",
        verification_method: str = "",
        test_id: str | None = None,
    ) -> dict[str, Any]:
        if test_category not in TEST_CATEGORIES:
            raise TestGovernanceError(f"unknown category {test_category!r} — use one of {TEST_CATEGORIES}")
        if risk_level not in ("R0", "R1", "R2", "R3", "R4", "R5"):
            raise TestGovernanceError(f"invalid risk_level {risk_level!r}")
        if not test_name.strip():
            raise TestGovernanceError("test_name is required")
        tid = test_id or f"tc_{uuid.uuid4().hex[:10]}"
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO test_cases (
                    test_id, test_name, test_category, test_objective, target_module,
                    risk_level, preconditions, input_dataset, execution_environment,
                    expected_result, verification_method, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    test_name.strip(),
                    test_category,
                    test_objective,
                    target_module,
                    risk_level,
                    preconditions,
                    input_dataset,
                    execution_environment,
                    expected_result,
                    verification_method,
                    _now(),
                ),
            )
        return self.get_case(tid)  # type: ignore[return-value]

    def get_case(self, test_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM test_cases WHERE test_id = ?", (test_id,)).fetchone()
        return dict(row) if row else None

    def list_cases(self, category: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            if category:
                rows = self._conn.execute(
                    "SELECT * FROM test_cases WHERE test_category = ? ORDER BY created_at DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM test_cases ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------------
    # Kết quả chạy + evidence (12 trường Phần 3.3)
    # ---------------------------------------------------------------
    def record_run(
        self,
        *,
        test_id: str,
        result: str,
        git_commit: str = "",
        environment: str = "unit",
        random_seed: str | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
        error: str | None = None,
        logs_redacted: str = "",
        refs: list[str] | None = None,
        runner_version: str = "",
        software_version: str = "",
        dataset_version: str = "",
        config_fingerprint: str = "",
        verification_level: str | None = None,
    ) -> dict[str, Any]:
        if result not in ("PASS", "FAIL", "SKIP"):
            raise TestGovernanceError(f"result must be PASS/FAIL/SKIP, got {result!r}")
        case = self.get_case(test_id)
        if case is None:
            raise TestGovernanceError(f"test case {test_id} not registered")
        if verification_level is not None:
            if verification_level not in VERIFICATION_LEVELS:
                raise TestGovernanceError(f"invalid verification level {verification_level!r}")
            # Đơn vị được phép tự xác nhận tối đa ADVERSARIAL/STRESS (bằng máy);
            # LIVE_VERIFIED / OWNER_ACCEPTED chỉ owner gán khi nghiệm thu.
            if verification_level in ("LIVE_VERIFIED", "OWNER_ACCEPTED"):
                raise TestGovernanceError(
                    "LIVE_VERIFIED/OWNER_ACCEPTED chỉ được gán khi owner nghiệm thu — không tự nâng"
                )
        eid = f"ev_{uuid.uuid4().hex[:12]}"
        start = started_at or _now()
        end = ended_at or _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO test_evidence (
                    evidence_id, test_id, git_commit, software_version, environment,
                    dataset_version, config_fingerprint, random_seed, started_at, ended_at,
                    result, error, logs_redacted, refs, runner_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    test_id,
                    git_commit,
                    software_version,
                    environment,
                    dataset_version,
                    config_fingerprint,
                    random_seed,
                    start,
                    end,
                    result,
                    error,
                    logs_redacted,
                    json.dumps(refs or []),
                    runner_version,
                ),
            )
            new_status = "IMPLEMENTED" if case["status"] in ("DESIGNED",) else case["status"]
            if verification_level is not None:
                new_status = verification_level
            self._conn.execute(
                "UPDATE test_cases SET status = ?, regression_status = ?, last_executed_at = ?, actual_result = ? WHERE test_id = ?",
                (new_status, result, end, result, test_id),
            )
        return {"evidence_id": eid, "test_id": test_id, "result": result}

    def evidence_for(self, test_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM test_evidence WHERE test_id = ? ORDER BY started_at DESC LIMIT ?",
                (test_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
            by_status = self._conn.execute(
                "SELECT status, COUNT(*) FROM test_cases GROUP BY status"
            ).fetchall()
            latest = self._conn.execute(
                "SELECT test_id, result, ended_at FROM test_evidence ORDER BY ended_at DESC LIMIT 10"
            ).fetchall()
        return {
            "total_cases": total,
            "by_status": {r[0]: r[1] for r in by_status},
            "latest_runs": [dict(r) for r in latest],
        }

    def close(self) -> None:
        self._conn.close()
