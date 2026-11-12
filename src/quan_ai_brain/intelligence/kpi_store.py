"""KPI Store — lưu trữ ADD-ONLY cho benchmark runs + KPI snapshots (Phase 2).

(12/11/2026, Dashboard Phase 2 — owner duyệt "duyệt")

Nguyên tắc bất biến (spec + design doc):
- ADD-ONLY: KHÔNG UPDATE/KHÔNG DELETE trên bảng kpi — lịch sử benchmark là
  bằng chứng, sửa được thì không còn là bằng chứng (Goodhart guard).
- Benchmark chạy trên DB copy snapshot — bảng này chỉ GHI kết quả, không
  benchmark trực tiếp trên brain.db live.
- Schema migration có backup bắt buộc trước khi CREATE TABLE.
- 0 POST từ dashboard — store chỉ dùng bởi benchmark_runner (Phase 4).

Bảng (ADD-ONLY, trong brain.db):
- benchmark_runs     : 1 lần chạy suite (id, started_at, suite, status, cost)
- kpi_snapshots      : 12 KPI CISC của 1 run (kpi_id, value, status, ci, meta)
- version_comparisons: so sánh 2 runs (V_base → V_new) + RED FLAG >5%

Trạng thái KPI hợp lệ: MEASURED | NOT_EVALUATED | BLOCKED | AUDIT_REQUIRED
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

def _find_workspace_root() -> Path:
    """Tìm workspace root (thư mục chứa data/brain.db) đi LÊN từ file này.

    (12/11) Fix: parent đếm cứng sai bậc khi package lồng sâu
    (src/quan_ai_brain/intelligence/ cần 4 mức, không phải 3) — từng làm
    migrate schema vào src/data/brain.db (SAI DB). Anchor: data/brain.db.
    """
    here = Path(__file__).resolve()
    for cand in (here.parents[3], here.parents[2], here.parents[4]):
        if (cand / "data" / "brain.db").exists():
            return cand
    # fallback: cwd có data/brain.db không (khi chạy từ workspace)
    cwd = Path.cwd()
    if (cwd / "data" / "brain.db").exists():
        return cwd
    return here.parents[3]


BASE_DIR = _find_workspace_root()
DB_PATH = BASE_DIR / "data" / "brain.db"
BACKUP_DIR = BASE_DIR / "backups"

VALID_KPI_STATUSES = ("MEASURED", "NOT_EVALUATED", "BLOCKED", "AUDIT_REQUIRED")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id TEXT PRIMARY KEY,
    started_at_utc TEXT NOT NULL,
    finished_at_utc TEXT,
    suite_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'RUNNING',   -- RUNNING|COMPLETED|FAILED
    llm_calls INTEGER NOT NULL DEFAULT 0,
    duration_sec REAL NOT NULL DEFAULT 0.0,
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES benchmark_runs(run_id),
    kpi_id INTEGER NOT NULL,                  -- 1..12 (CISC)
    kpi_name TEXT NOT NULL,
    status TEXT NOT NULL,                     -- VALID_KPI_STATUSES
    value REAL,                               -- NULL khi NOT_EVALUATED/BLOCKED
    unit TEXT NOT NULL DEFAULT 'ratio',
    sample_size INTEGER,
    confidence_low REAL,
    confidence_high REAL,
    red_flag INTEGER NOT NULL DEFAULT 0,      -- giảm >5% so run trước
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS version_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_run_id TEXT NOT NULL,
    candidate_run_id TEXT NOT NULL,
    kpi_id INTEGER NOT NULL,
    value_base REAL,
    value_new REAL,
    delta_pct REAL,
    red_flag INTEGER NOT NULL DEFAULT 0,
    cost_ratio REAL,                          -- chi phí mới / chi phí base
    verdict TEXT NOT NULL DEFAULT 'INCONCLUSIVE',  -- IMPROVED|REGRESSED|INCONCLUSIVE
    created_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_run ON kpi_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_kpi ON kpi_snapshots(kpi_id);
CREATE INDEX IF NOT EXISTS idx_vcomp ON version_comparisons(baseline_run_id, candidate_run_id);
"""

KPI_NAMES: dict[int, str] = {
    1: "Problem Solving Accuracy",
    2: "Reasoning Validity",
    3: "Evidence Coverage",
    4: "False Confidence Rate",
    5: "Appropriate Abstention",
    6: "Contradiction Detection",
    7: "Causal Reasoning Accuracy",
    8: "Self-Correction Success",
    9: "Transfer Learning",
    10: "Regression Stability",
    11: "Decision Safety",
    12: "Governance Compliance",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class KpiSnapshotInput:
    """1 KPI của 1 run — bắt buộc trung thực: value=None khi NOT_EVALUATED."""
    kpi_id: int
    status: str
    value: float | None = None
    unit: str = "ratio"
    sample_size: int | None = None
    confidence_low: float | None = None
    confidence_high: float | None = None
    meta: dict = field(default_factory=dict)

    def validate(self) -> None:
        if self.kpi_id not in KPI_NAMES:
            raise ValueError(f"kpi_id {self.kpi_id} ngoài 1..12 (CISC)")
        if self.status not in VALID_KPI_STATUSES:
            raise ValueError(f"status '{self.status}' không hợp lệ: {VALID_KPI_STATUSES}")
        if self.status in ("NOT_EVALUATED", "BLOCKED") and self.value is not None:
            raise ValueError(f"KPI {self.kpi_id} status={self.status} nhưng có value — vi phạm N/A-insufficient")
        if self.status == "MEASURED" and self.value is None:
            raise ValueError(f"KPI {self.kpi_id} status=MEASURED nhưng thiếu value")


class KpiStore:
    """Store ADD-ONLY — chỉ INSERT/SELECT, không UPDATE/DELETE."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DB_PATH

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path), timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def ensure_schema(self, backup: bool = True) -> Path | None:
        """CREATE TABLE IF NOT EXISTS — backup brain.db trước khi migrate."""
        bak: Path | None = None
        if backup:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            bak = BACKUP_DIR / f"pre_kpi_schema_{ts}.db"
            src = sqlite3.connect(str(self.db_path), timeout=30)
            try:
                dst = sqlite3.connect(str(bak))
                try:
                    with dst:
                        src.backup(dst)
                finally:
                    dst.close()
            finally:
                src.close()
            check = sqlite3.connect(str(bak))
            try:
                ok = check.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                check.close()
            if ok != "ok":
                raise SystemExit(f"Backup pre-schema FAIL integrity ({ok}) — DỪNG.")
        con = self.connect()
        try:
            with con:
                con.executescript(SCHEMA_SQL)
        finally:
            con.close()
        return bak

    # ------------------------------------------------------------- runs
    def start_run(self, suite_name: str, notes: str = "") -> str:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT INTO benchmark_runs (run_id, started_at_utc, suite_name, status, notes) "
                    "VALUES (?, ?, ?, 'RUNNING', ?)",
                    (run_id, _now_utc(), suite_name, notes),
                )
        finally:
            con.close()
        return run_id

    def finish_run(self, run_id: str, ok: bool, llm_calls: int = 0, duration_sec: float = 0.0) -> None:
        con = self.connect()
        try:
            with con:
                con.execute(
                    "UPDATE benchmark_runs SET status=?, finished_at_utc=?, llm_calls=?, duration_sec=? "
                    "WHERE run_id=?",
                    ("COMPLETED" if ok else "FAILED", _now_utc(), llm_calls, duration_sec, run_id),
                )
        finally:
            con.close()

    # --------------------------------------------------------- snapshots
    def write_kpi(self, run_id: str, kpi: KpiSnapshotInput,
                  red_flag: bool = False) -> None:
        """INSERT 1 KPI. Validate trước — MEASURED phải có value,
        NOT_EVALUATED/BLOCKED phải KHÔNG có value (N/A-insufficient bắt buộc)."""
        kpi.validate()
        con = self.connect()
        try:
            with con:
                con.execute(
                    "INSERT INTO kpi_snapshots (run_id, kpi_id, kpi_name, status, value, unit, "
                    "sample_size, confidence_low, confidence_high, red_flag, meta_json, created_at_utc) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, kpi.kpi_id, KPI_NAMES[kpi.kpi_id], kpi.status, kpi.value, kpi.unit,
                     kpi.sample_size, kpi.confidence_low, kpi.confidence_high,
                     1 if red_flag else 0, json.dumps(kpi.meta, ensure_ascii=False), _now_utc()),
                )
        finally:
            con.close()

    def write_run(self, run_id: str, kpis: list[KpiSnapshotInput],
                  prev_run_id: str | None = None) -> dict:
        """Ghi 12 KPI của 1 run + tự tính RED FLAG (>5% giảm so prev run).

        Trả summary: {written, red_flags: [kpi_id...]}.
        Red flag: value_new < value_prev * 0.95 (giảm >5%).
        """
        prev_values: dict[int, float] = {}
        if prev_run_id:
            con = self.connect()
            try:
                for row in con.execute(
                    "SELECT kpi_id, value FROM kpi_snapshots "
                    "WHERE run_id=? AND status='MEASURED' AND value IS NOT NULL",
                    (prev_run_id,),
                ):
                    prev_values[row["kpi_id"]] = float(row["value"])
            finally:
                con.close()

        red_flags: list[int] = []
        for kpi in kpis:
            rf = False
            if prev_run_id and kpi.kpi_id in prev_values and kpi.value is not None:
                rf = kpi.value < prev_values[kpi.kpi_id] * 0.95
            if rf:
                red_flags.append(kpi.kpi_id)
            self.write_kpi(run_id, kpi, red_flag=rf)
        return {"written": len(kpis), "red_flags": red_flags}

    # ----------------------------------------------------------- SELECT
    def latest_run(self, suite_name: str | None = None) -> dict | None:
        con = self.connect()
        try:
            q = "SELECT * FROM benchmark_runs WHERE status='COMPLETED'"
            args: tuple = ()
            if suite_name:
                q += " AND suite_name=?"
                args = (suite_name,)
            q += " ORDER BY started_at_utc DESC LIMIT 1"
            row = con.execute(q, args).fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def run_kpis(self, run_id: str) -> list[dict]:
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT * FROM kpi_snapshots WHERE run_id=? ORDER BY kpi_id",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    def kpi_trend(self, kpi_id: int, limit: int = 7) -> list[dict]:
        """Trend 1 KPI qua các run (mới nhất đầu) — cho sparkline dashboard."""
        con = self.connect()
        try:
            rows = con.execute(
                "SELECT ks.run_id, ks.value, ks.red_flag, br.started_at_utc "
                "FROM kpi_snapshots ks JOIN benchmark_runs br ON br.run_id = ks.run_id "
                "WHERE ks.kpi_id=? AND ks.status='MEASURED' AND br.status='COMPLETED' "
                "ORDER BY br.started_at_utc DESC LIMIT ?",
                (kpi_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    def compare_versions(self, baseline_run_id: str, candidate_run_id: str) -> list[dict]:
        """So 2 runs theo 12 KPI + verdict theo quy tắc CISC §4:
        IMPROVED chỉ khi tăng và không red-flag; chi phí do caller kiểm."""
        con = self.connect()
        try:
            base = {r["kpi_id"]: r for r in con.execute(
                "SELECT * FROM kpi_snapshots WHERE run_id=?", (baseline_run_id,)).fetchall()}
            cand = {r["kpi_id"]: r for r in con.execute(
                "SELECT * FROM kpi_snapshots WHERE run_id=?", (candidate_run_id,)).fetchall()}
        finally:
            con.close()

        out: list[dict] = []
        for kid in range(1, 13):
            b, c = base.get(kid), cand.get(kid)
            row = {
                "kpi_id": kid, "kpi_name": KPI_NAMES[kid],
                "value_base": b["value"] if b else None,
                "value_new": c["value"] if c else None,
                "red_flag": bool(c["red_flag"]) if c else False,
                "verdict": "INCONCLUSIVE",
            }
            if b and c and b["value"] is not None and c["value"] is not None:
                row["delta_pct"] = round((c["value"] - b["value"]) / b["value"] * 100, 2)
                if row["red_flag"]:
                    row["verdict"] = "REGRESSED"
                elif c["value"] > b["value"]:
                    row["verdict"] = "IMPROVED"
                elif c["value"] == b["value"]:
                    row["verdict"] = "UNCHANGED"
                else:
                    row["verdict"] = "MIXED"
            elif c is None or c["value"] is None:
                row["verdict"] = "NOT_EVALUATED"
            elif b is None or b["value"] is None:
                # candidate đo được nhưng baseline thiếu → không so sánh được
                row["verdict"] = "INCONCLUSIVE"
            out.append(row)
        return out
