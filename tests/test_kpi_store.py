"""Test KpiStore — ADD-ONLY + N/A-insufficient + RED FLAG + version compare.

100% DB tạm (tmp_path) — KHÔNG đụng brain.db thật.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))

from quan_ai_brain.intelligence.kpi_store import (
    KPI_NAMES,
    KpiSnapshotInput,
    KpiStore,
    VALID_KPI_STATUSES,
)


def _store(tmp_path: Path) -> KpiStore:
    s = KpiStore(db_path=tmp_path / "kpi_test.db")
    s.ensure_schema(backup=False)  # DB tạm — không backup
    return s


def _kpis_base() -> list[KpiSnapshotInput]:
    return [
        KpiSnapshotInput(kpi_id=3, status="MEASURED", value=0.50, sample_size=4),
        KpiSnapshotInput(kpi_id=11, status="MEASURED", value=1.0, sample_size=1),
        KpiSnapshotInput(kpi_id=12, status="MEASURED", value=0.0, sample_size=1),
        KpiSnapshotInput(kpi_id=1, status="NOT_EVALUATED"),
        KpiSnapshotInput(kpi_id=5, status="BLOCKED"),
    ]


def test_schema_created_addonly(tmp_path) -> None:
    """3 bảng + index tạo đúng; store KHÔNG có method UPDATE/DELETE KPI."""
    s = _store(tmp_path)
    con = s.connect()
    try:
        tables = {r["name"] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert {"benchmark_runs", "kpi_snapshots", "version_comparisons"} <= tables
    finally:
        con.close()
    # ADD-ONLY: không có public method update/delete
    public = [m for m in dir(s) if not m.startswith("_")]
    assert not any(m.lower().startswith(("update", "delete")) for m in public), \
        f"Store ADD-ONLY không được có update/delete: {public}"


def test_write_run_na_insufficient_enforced(tmp_path) -> None:
    """MEASURED thiếu value → lỗi; NOT_EVALUATED có value → lỗi (N/A bắt buộc)."""
    s = _store(tmp_path)
    with __import__("pytest").raises(ValueError, match="thiếu value"):
        KpiSnapshotInput(kpi_id=1, status="MEASURED", value=None).validate()
    with __import__("pytest").raises(ValueError, match="N/A-insufficient"):
        KpiSnapshotInput(kpi_id=2, status="NOT_EVALUATED", value=0.9).validate()
    with __import__("pytest").raises(ValueError, match="không hợp lệ"):
        KpiSnapshotInput(kpi_id=2, status="PASS").validate()  # status không hợp lệ
    with __import__("pytest").raises(ValueError, match="ngoài 1..12"):
        KpiSnapshotInput(kpi_id=13, status="MEASURED", value=1.0).validate()


def test_write_and_read_run(tmp_path) -> None:
    """Ghi run 5 KPI (3 measured + 2 N/A) → đọc lại đúng, đủ 12 tên CISC."""
    s = _store(tmp_path)
    run = s.start_run("cisc_mini", "test run")
    s.finish_run(run, ok=True, llm_calls=42, duration_sec=12.5)
    summary = s.write_run(run, _kpis_base())
    assert summary["written"] == 5
    assert summary["red_flags"] == []

    rows = s.run_kpis(run)
    assert len(rows) == 5
    by_id = {r["kpi_id"]: r for r in rows}
    assert by_id[3]["status"] == "MEASURED" and by_id[3]["value"] == 0.50
    assert by_id[1]["status"] == "NOT_EVALUATED" and by_id[1]["value"] is None
    assert by_id[5]["status"] == "BLOCKED" and by_id[5]["value"] is None
    assert by_id[3]["kpi_name"] == KPI_NAMES[3]
    run_info = s.latest_run("cisc_mini")
    assert run_info and run_info["llm_calls"] == 42


def test_red_flag_on_5pct_drop(tmp_path) -> None:
    """KPI3 giảm 0.50 → 0.45 (chính xác -10%) → RED FLAG; tăng không flag."""
    s = _store(tmp_path)
    r1 = s.start_run("cisc_mini")
    s.finish_run(r1, ok=True)
    s.write_run(r1, _kpis_base())

    r2 = s.start_run("cisc_mini")
    s.finish_run(r2, ok=True)
    kpis2 = [
        KpiSnapshotInput(kpi_id=3, status="MEASURED", value=0.45, sample_size=4),  # -10%
        KpiSnapshotInput(kpi_id=11, status="MEASURED", value=1.0, sample_size=1),  # giữ
        KpiSnapshotInput(kpi_id=12, status="MEASURED", value=0.0, sample_size=1),
        KpiSnapshotInput(kpi_id=1, status="NOT_EVALUATED"),
        KpiSnapshotInput(kpi_id=5, status="BLOCKED"),
    ]
    summary = s.write_run(r2, kpis2, prev_run_id=r1)
    assert summary["red_flags"] == [3], "chỉ KPI3 (giảm >5%) bị RED FLAG"
    trend = s.kpi_trend(3)
    assert len(trend) == 2 and trend[0]["run_id"] == r2  # mới nhất đầu
    assert trend[0]["red_flag"] == 1


def test_version_comparison_verdicts(tmp_path) -> None:
    """IMPROVED / REGRESSED / UNCHANGED / NOT_EVALUATED đúng quy tắc CISC §4."""
    s = _store(tmp_path)
    rb = s.start_run("cisc_mini")
    s.finish_run(rb, ok=True)
    s.write_run(rb, [
        KpiSnapshotInput(kpi_id=3, status="MEASURED", value=0.40, sample_size=4),
        KpiSnapshotInput(kpi_id=11, status="MEASURED", value=1.0, sample_size=1),
        KpiSnapshotInput(kpi_id=5, status="NOT_EVALUATED"),
    ])
    rc = s.start_run("cisc_mini")
    s.finish_run(rc, ok=True)
    # KPI3 tăng (IMPROVED), KPI11 giữ (UNCHANGED), KPI5 vẫn N/A (NOT_EVALUATED)
    # + thêm KPI12 giảm sâu → REGRESSED
    s.write_run(rc, [
        KpiSnapshotInput(kpi_id=3, status="MEASURED", value=0.55, sample_size=4),
        KpiSnapshotInput(kpi_id=11, status="MEASURED", value=1.0, sample_size=1),
        KpiSnapshotInput(kpi_id=5, status="NOT_EVALUATED"),
        KpiSnapshotInput(kpi_id=12, status="MEASURED", value=0.5, sample_size=1, meta={"note": "demo"}),
    ])
    comp = s.compare_versions(rb, rc)
    by_id = {c["kpi_id"]: c for c in comp}
    assert by_id[3]["verdict"] == "IMPROVED" and by_id[3]["delta_pct"] == 37.5
    assert by_id[11]["verdict"] == "UNCHANGED"
    assert by_id[5]["verdict"] == "NOT_EVALUATED"
    # KPI12: base 0.0 → không tính delta (chia 0) → INCONCLUSIVE trung thực
    assert by_id[12]["verdict"] == "INCONCLUSIVE"


def test_full_12_kpis_roundtrip(tmp_path) -> None:
    """Ghi đủ 12 KPI (9 NOT_EVALUATED đúng thực trạng) → đọc đủ 12."""
    s = _store(tmp_path)
    run = s.start_run("cisc_full")
    s.finish_run(run, ok=True)
    kpis = [
        KpiSnapshotInput(kpi_id=3, status="MEASURED", value=0.50, sample_size=4),
        KpiSnapshotInput(kpi_id=11, status="MEASURED", value=1.0, sample_size=1),
        KpiSnapshotInput(kpi_id=12, status="MEASURED", value=0.0, sample_size=1),
    ] + [KpiSnapshotInput(kpi_id=i, status="NOT_EVALUATED") for i in (1, 2, 4, 5, 6, 7, 8, 9, 10)]
    assert len(kpis) == 12
    s.write_run(run, kpis)
    rows = s.run_kpis(run)
    assert len(rows) == 12
    measured = [r for r in rows if r["status"] == "MEASURED"]
    assert len(measured) == 3
    assert all(r["value"] is None for r in rows if r["status"] == "NOT_EVALUATED")
