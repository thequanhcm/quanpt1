"""DEOM V4 P5 — Learning Metrics & Reward-Hacking Guards (Phần 10, G1–G6).

Đọc số liệu TỪ DỮ LIỆU THẬT (task_feedback.db + tasks.db), không nhận declaration:
- measure_improvement: so sánh cùng nhóm nhiệm vụ trước/sau (verified rate, retry, p50 duration).
- detect_reward_hacking: 5 tín hiệu từ dữ liệu — chỉ BÁO CÁO, không tự sửa (Phần 21).
- lessons luôn candidate; promote chỉ qua API owner (Q-4) — module này không có đường promote.

Không thay thế Learning Engine/Q-4 — chỉ lớp đo lường độc lập phục vụ nghiệm thu.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.orchestration.models import TaskStatus

_SUCCESS_STATES = (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED, TaskStatus.COMPLETED_PARTIALLY)
_VERIFIED_STATES = (TaskStatus.COMPLETED_VERIFIED,)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _percent(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


@dataclass
class ImprovementReport:
    """Kết quả so sánh trước/sau cùng nhóm nhiệm vụ (G3)."""

    task_pattern: str
    before_tasks: int
    after_tasks: int
    before_success_rate: float
    after_success_rate: float
    before_verified_rate: float
    after_verified_rate: float
    before_avg_retries: float
    after_avg_retries: float
    before_p50_duration: float | None
    after_p50_duration: float | None
    improved: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_pattern": self.task_pattern,
            "before": {"tasks": self.before_tasks, "success_rate": self.before_success_rate,
                       "verified_rate": self.before_verified_rate, "avg_retries": self.before_avg_retries,
                       "p50_duration_sec": self.before_p50_duration},
            "after": {"tasks": self.after_tasks, "success_rate": self.after_success_rate,
                      "verified_rate": self.after_verified_rate, "avg_retries": self.after_avg_retries,
                      "p50_duration_sec": self.after_p50_duration},
            "improved": self.improved,
            "notes": self.notes,
        }


@dataclass
class RewardHackingSignal:
    """Phát hiện kiểu 'làm đẹp số liệu' — báo owner, không tự xử (G6)."""

    signal_type: str
    severity: str  # P2 | P3
    evidence: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "severity": self.severity,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


class LearningMetrics:
    """Lớp đo lường học tập độc lập — số liệu từ registry + feedback DB."""

    def __init__(self, tasks_db: str | Path, feedback_db: str | Path | None = None) -> None:
        self._tasks_path = Path(tasks_db)
        self._feedback_path = Path(feedback_db) if feedback_db else None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Đọc dữ liệu
    # ------------------------------------------------------------------
    def _fetch_tasks(self, since_utc: str | None = None, until_utc: str | None = None,
                     pattern: str | None = None) -> list[sqlite3.Row]:
        if not self._tasks_path.exists():
            return []
        conn = sqlite3.connect(str(self._tasks_path))
        conn.row_factory = sqlite3.Row
        try:
            sql = "SELECT * FROM durable_tasks WHERE 1=1"
            params: list[Any] = []
            if since_utc:
                sql += " AND created_at_utc >= ?"
                params.append(since_utc)
            if until_utc:
                sql += " AND created_at_utc < ?"
                params.append(until_utc)
            if pattern:
                sql += " AND goal LIKE ?"
                params.append(f"%{pattern}%")
            rows = conn.execute(sql + " ORDER BY created_at_utc", params).fetchall()
            return rows
        finally:
            conn.close()

    @staticmethod
    def _stats(rows: list[sqlite3.Row]) -> dict[str, Any]:
        total = len(rows)
        success = sum(1 for r in rows if r["status"] in tuple(s.value for s in _SUCCESS_STATES))
        verified = sum(1 for r in rows if r["status"] in tuple(s.value for s in _VERIFIED_STATES))
        unverified_success = sum(
            1 for r in rows if r["status"] == TaskStatus.COMPLETED.value
        )
        retries = [r["retry_count"] or 0 for r in rows]
        durations = sorted(
            (datetime.fromisoformat(r["completed_at_utc"]) - datetime.fromisoformat(r["created_at_utc"])).total_seconds()
            for r in rows
            if r["completed_at_utc"] and r["created_at_utc"]
        )
        p50 = durations[len(durations) // 2] if durations else None
        return {
            "total": total,
            "success": success,
            "verified": verified,
            "unverified_success": unverified_success,
            "success_rate": _percent(success, total),
            "verified_rate": _percent(verified, total),
            "avg_retries": round(sum(retries) / total, 2) if total else 0.0,
            "p50_duration_sec": p50,
        }

    # ------------------------------------------------------------------
    # G3 — đo cải thiện bằng so sánh trước/sau (cùng pattern)
    # ------------------------------------------------------------------
    def measure_improvement(
        self,
        *,
        task_pattern: str,
        before_start: str,
        split_at: str,
        after_end: str | None = None,
    ) -> ImprovementReport:
        before_rows = self._fetch_tasks(since_utc=before_start, until_utc=split_at, pattern=task_pattern)
        after_rows = self._fetch_tasks(since_utc=split_at, until_utc=after_end, pattern=task_pattern)
        sb = self._stats(before_rows)
        sa = self._stats(after_rows)
        notes: list[str] = []
        improved = (
            sa["verified_rate"] >= sb["verified_rate"]
            and sa["success_rate"] >= sb["success_rate"]
            and (sb["total"] == 0 or sa["avg_retries"] <= sb["avg_retries"])
        )
        if sb["total"] == 0:
            notes.append("kỳ trước không có task cùng nhóm — không kết luận cải thiện")
            improved = False
        if sa["total"] == 0:
            notes.append("kỳ sau không có task cùng nhóm — không kết luận")
        return ImprovementReport(
            task_pattern=task_pattern,
            before_tasks=sb["total"], after_tasks=sa["total"],
            before_success_rate=sb["success_rate"], after_success_rate=sa["success_rate"],
            before_verified_rate=sb["verified_rate"], after_verified_rate=sa["verified_rate"],
            before_avg_retries=sb["avg_retries"], after_avg_retries=sa["avg_retries"],
            before_p50_duration=sb["p50_duration_sec"], after_p50_duration=sa["p50_duration_sec"],
            improved=improved, notes=notes,
        )

    # ------------------------------------------------------------------
    # G6 — reward hacking detectors (từ dữ liệu, chỉ báo cáo)
    # ------------------------------------------------------------------
    def detect_reward_hacking(self, *, window_hours: int = 24) -> list[RewardHackingSignal]:
        now = _now()
        window_start = (now - timedelta(hours=window_hours)).isoformat()
        prev_start = (now - timedelta(hours=window_hours * 2)).isoformat()
        cur = self._stats(self._fetch_tasks(since_utc=window_start))
        prev = self._stats(self._fetch_tasks(since_utc=prev_start, until_utc=window_start))
        signals: list[RewardHackingSignal] = []

        # 1. Task fragmentation — chia nhỏ vô nghĩa
        rows = self._fetch_tasks(since_utc=window_start)
        prefixes: dict[str, int] = {}
        for r in rows:
            prefix = " ".join((r["goal"] or "").split()[:4]).lower()
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
        hot = {p: c for p, c in prefixes.items() if c > 6 and cur["total"] > 6}
        if hot:
            worst = max(hot.items(), key=lambda kv: kv[1])
            signals.append(RewardHackingSignal(
                "task_fragmentation", "P2",
                f"{worst[1]} task cùng mẫu '{worst[0]}…' trong {window_hours}h — nghi chia nhỏ vô nghĩa",
                "rà soát: gộp task cha, chấm KPI theo outcome thay vì số task",
            ))

        # 2. Quality erosion — verified rate giảm ≥20 điểm % khi volume tăng
        if prev["total"] >= 5 and cur["total"] > prev["total"]:
            drop = prev["verified_rate"] - cur["verified_rate"]
            if drop >= 20.0:
                signals.append(RewardHackingSignal(
                    "quality_erosion", "P2",
                    f"verified rate giảm {drop:.1f} điểm % ({prev['verified_rate']}% → {cur['verified_rate']}%) trong khi volume tăng ({prev['total']} → {cur['total']})",
                    "rà soát tiêu chí verify; KHÔNG hạ chuẩn verify để tăng số lượng",
                ))

        # 3. Unverified success rush — COMPLETED (không verify) tăng đột biến
        if cur["unverified_success"] > 0 and cur["unverified_success"] >= max(5, prev["unverified_success"] * 1.5):
            signals.append(RewardHackingSignal(
                "unverified_success_rush", "P2",
                f"{cur['unverified_success']} task COMPLETED chưa verify (kỳ trước: {prev['unverified_success']}) — có thể 'báo thành công' khi chưa có bằng chứng",
                "chạy verifier cho lo task này trước khi tính vào KPI",
            ))

        # 4. Evidence gap — success nhưng 0 evidence
        no_evidence = 0
        for r in self._fetch_tasks(since_utc=window_start):
            if r["status"] in tuple(s.value for s in _SUCCESS_STATES):
                refs = r["evidence_refs_json"] or "[]"
                if refs in ("[]", "", "null"):
                    no_evidence += 1
        if no_evidence >= 3:
            signals.append(RewardHackingSignal(
                "evidence_gap", "P3",
                f"{no_evidence} task thành công không có evidence_ref nào",
                "bật yêu cầu evidence bắt buộc trước khiverify",
            ))

        # 5. Cherry picking — có task R2+ nhận vào nhưng toàn bộ completed là R0/R1
        risk_completed = [
            (r["risk_level"] or "R1") for r in self._fetch_tasks(since_utc=window_start)
            if r["status"] in tuple(s.value for s in _SUCCESS_STATES)
        ]
        risk_created = [(r["risk_level"] or "R1") for r in self._fetch_tasks(since_utc=window_start)]
        has_higher = any(x in ("R2", "R3", "R4") for x in risk_created)
        done_higher = any(x in ("R2", "R3", "R4") for x in risk_completed)
        if has_higher and len(risk_completed) >= 3 and not done_higher:
            signals.append(RewardHackingSignal(
                "cherry_picking", "P3",
                f"có nhiệm vụ R2+ trong hàng đợi nhưng {len(risk_completed)} task hoàn thành đều R0/R1",
                "kiểm tra thứ tự ưu tiên — không chỉ chọn việc dễ",
            ))
        return signals

    # ------------------------------------------------------------------
    # Tổng hợp lessons (candidate vs promoted) — G4/G5 read-only
    # ------------------------------------------------------------------
    def learning_report(self) -> dict[str, Any]:
        out: dict[str, Any] = {"lessons": {"candidate": 0, "promoted": 0, "by_kind": {}}, "feedback": 0}
        if not self._feedback_path or not self._feedback_path.exists():
            out["error"] = "feedback DB không tồn tại"
            return out
        conn = sqlite3.connect(str(self._feedback_path))
        conn.row_factory = sqlite3.Row
        try:
            for r in conn.execute("SELECT verification_status, COUNT(*) n FROM task_lessons GROUP BY verification_status"):
                out["lessons"][r["verification_status"]] = r["n"]
            for r in conn.execute("SELECT kind, COUNT(*) n FROM task_lessons GROUP BY kind"):
                out["lessons"]["by_kind"][r["kind"]] = r["n"]
            out["feedback"] = conn.execute("SELECT COUNT(*) n FROM task_feedback").fetchone()["n"]
        finally:
            conn.close()
        return out
