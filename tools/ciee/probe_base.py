"""CIEE probe framework — cấu trúc chuẩn cho mọi probe.

Mỗi probe là một class con của `Probe` với:
  - probe_id : định danh ổn định, khớp baseline V0 (VD "B2_conflict_scan_runs")
  - group    : nhóm năng lực A-H (A_PROBLEM ... H_LEARNING)
  - title    : mô tả ngắn tiếng Việt
  - setup()  : chuẩn bị (mặc định không làm gì)
  - run(ctx) : chạy đo lường thật, trả `ProbeResult` (outcome + evidence)
  - teardown(): dọn dẹp (mặc định không làm gì)

Outcome hợp lệ: PASS / FAIL / PARTIAL / GAP_KNOWN / NOT_RUN / ERROR.
- FAIL     : năng lực đo được nhưng KHÔNG đạt (điểm yếu thật, phải sửa).
- PARTIAL  : khung có thật nhưng chưa hoàn chỉnh/chưa hữu dụng.
- GAP_KNOWN: năng lực chưa được xây, đã ghi nhận trong master plan.
- ERROR    : lỗi hạ tầng của runner (không phải điểm yếu của CHERRY).
- NOT_RUN  : cố tình bỏ qua, phải kèm lý do.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- nhóm A-H
GROUPS = {
    "A_PROBLEM": "A. Problem Solving",
    "B_REASONING": "B. Reasoning Accuracy",
    "C_EPISTEMIC": "C. Epistemic Intelligence",
    "D_CRITICAL": "D. Critical Thinking",
    "E_METACOG": "E. Metacognition",
    "F_ADAPTIVE": "F. Adaptive",
    "G_DECISION": "G. Decision",
    "H_LEARNING": "H. Learning Effectiveness",
}

OUTCOMES = ("PASS", "FAIL", "PARTIAL", "GAP_KNOWN", "NOT_RUN", "ERROR")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ProbeResult:
    """Kết quả của một probe — luôn có evidence, luôn serialize được."""

    probe_id: str
    group: str
    title: str
    outcome: str
    detail: str = ""
    evidence: str = ""
    duration_s: float = 0.0
    started_at_utc: str = field(default_factory=utc_now_iso)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "probe_id": self.probe_id,
            "group": self.group,
            "group_label": GROUPS.get(self.group, self.group),
            "title": self.title,
            "outcome": self.outcome,
            "detail": self.detail,
            "evidence": self.evidence,
            "duration_s": round(self.duration_s, 3),
            "started_at_utc": self.started_at_utc,
        }
        if self.extras:
            d["extras"] = self.extras
        return d


@dataclass
class ProbeContext:
    """Bối cảnh dùng chung cho cả run — probes KHÔNG tự mở DB production rw."""

    run_id: str
    run_dir: Path                 # reports/intelligence_maturity/ciee/runs/<ts>/
    tmp_dir: Path                 # thư mục tạm chứa snapshot (dọn sau run)
    src_root: Path                # E:/BRAIN/src
    workspace: Path               # E:/BRAIN
    brain_db: Path                # production (chỉ mở qua read-only URI)
    tasks_db: Path
    governance_db: Path
    knowledge_db: Path
    brain_copy: Path              # snapshot copy (để mở rw an toàn khi cần)
    tasks_copy: Path
    gov_copy: Path


class Probe(ABC):
    """Lớp cơ sở cho mọi probe CIEE."""

    probe_id: str = ""
    group: str = ""
    title: str = ""

    def setup(self, ctx: ProbeContext) -> None:  # noqa: B027 — hook tùy chọn
        return None

    @abstractmethod
    def run(self, ctx: ProbeContext) -> ProbeResult:
        raise NotImplementedError

    def teardown(self, ctx: ProbeContext) -> None:  # noqa: B027
        return None

    # -- helper cho subclass: chạy run() có đo giờ + bắt lỗi thành ERROR
    def execute(self, ctx: ProbeContext) -> ProbeResult:
        started = time.perf_counter()
        started_at = utc_now_iso()
        try:
            self.setup(ctx)
            result = self.run(ctx)
        except Exception as exc:  # noqa: BLE001 — lỗi probe phải trở thành kết quả
            import traceback

            tb = traceback.format_exc(limit=4)
            result = ProbeResult(
                probe_id=self.probe_id,
                group=self.group,
                title=self.title,
                outcome="ERROR",
                detail=f"{type(exc).__name__}: {exc}",
                evidence=tb[-800:],
            )
        finally:
            try:
                self.teardown(ctx)
            except Exception:  # noqa: BLE001 — teardown không được che kết quả
                pass
        result.duration_s = time.perf_counter() - started
        result.started_at_utc = started_at
        if result.probe_id != self.probe_id or result.group != self.group:
            # probe tự set sai định danh → chuẩn hóa lại
            result.probe_id = self.probe_id
            result.group = self.group
        return result


def build_result(probe: Probe, outcome: str, detail: str, evidence: str,
                 extras: dict[str, Any] | None = None) -> ProbeResult:
    """Helper ngắn để subclass tạo ProbeResult đúng định danh."""
    if outcome not in OUTCOMES:
        raise ValueError(f"Outcome không hợp lệ: {outcome}")
    return ProbeResult(
        probe_id=probe.probe_id,
        group=probe.group,
        title=probe.title,
        outcome=outcome,
        detail=detail,
        evidence=evidence,
        extras=extras or {},
    )
