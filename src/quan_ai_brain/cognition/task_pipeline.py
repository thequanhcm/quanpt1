"""Task-Driven Learning Pipeline — Master Prompt V6 (§III).

Pipeline chuẩn: UNDERSTAND → DECOMPOSE → DISCOVER → PLAN → LEARN → BUILD →
TEST → ANALYZE → VERIFY → ADVISE → REUSE

Thiết kế:
- Bọc ngoài TaskSpecification hiện có (information_gap_analyzer) — KHÔNG tạo model trùng.
- Stage chỉ đi tới trước; skip phải có lý do (audit trail).
- Safety gate: ADVISE bị chặn nếu VERIFY chưa hoàn tất (fail-closed).
- Fail-honest: VERIFY thiếu bằng chứng ghi not_verified=True, không bịa kết luận.
- to_dict() đủ để persist vào checkpoint_data_json (cơ chế S15, không tạo bảng mới).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from quan_ai_brain.cognition.information_gap_analyzer import TaskSpecification


class PipelineStage(str, Enum):
    """11 stage chuẩn của Task-Driven Learning (V6 §III)."""

    UNDERSTAND = "UNDERSTAND"
    DECOMPOSE = "DECOMPOSE"
    DISCOVER = "DISCOVER"
    PLAN = "PLAN"
    LEARN = "LEARN"
    BUILD = "BUILD"
    TEST = "TEST"
    ANALYZE = "ANALYZE"
    VERIFY = "VERIFY"
    ADVISE = "ADVISE"
    REUSE = "REUSE"


_STAGE_ORDER: dict[PipelineStage, int] = {s: i for i, s in enumerate(PipelineStage)}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StageRecord:
    """Một lần chuyển stage — giữ vết audit."""

    stage: PipelineStage
    at: str
    notes: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    skipped_reason: str | None = None  # khác None → stage bị bỏ qua

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "at": self.at,
            "notes": self.notes,
            "evidence_refs": list(self.evidence_refs),
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StageRecord:
        return cls(
            stage=PipelineStage(d["stage"]),
            at=d["at"],
            notes=d.get("notes", ""),
            evidence_refs=list(d.get("evidence_refs", [])),
            skipped_reason=d.get("skipped_reason"),
        )


@dataclass
class TaskPipeline:
    """Pipeline giải quyết 1 bài toán của chủ nhân, có bằng chứng đầy đủ."""

    pipeline_id: str
    spec: TaskSpecification
    stage_history: list[StageRecord] = field(default_factory=list)
    evidence_manifest: dict[str, list[str]] = field(default_factory=dict)
    validation_results: dict[str, Any] = field(default_factory=dict)
    reusable_assets: list[str] = field(default_factory=list)
    final_recommendation: str | None = None

    # ---------- helpers ----------

    def current_stage(self) -> PipelineStage | None:
        return self.stage_history[-1].stage if self.stage_history else None

    def _stage_index(self, stage: PipelineStage) -> int:
        """Index cao nhất stage đó xuất hiện trong history."""
        idx = -1
        for rec in self.stage_history:
            if rec.stage == stage and rec.skipped_reason is None:
                idx = max(idx, _STAGE_ORDER[stage])
        return idx

    def has_completed(self, stage: PipelineStage) -> bool:
        """Stage đã hoàn tất = có record không phải skip."""
        return any(
            rec.stage == stage and rec.skipped_reason is None
            for rec in self.stage_history
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "spec": self.spec.to_dict(),
            "stage_history": [r.to_dict() for r in self.stage_history],
            "evidence_manifest": {
                k: list(v) for k, v in self.evidence_manifest.items()
            },
            "validation_results": dict(self.validation_results),
            "reusable_assets": list(self.reusable_assets),
            "final_recommendation": self.final_recommendation,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskPipeline:
        return cls(
            pipeline_id=d["pipeline_id"],
            spec=TaskSpecification.from_dict(d["spec"]),
            stage_history=[StageRecord.from_dict(r) for r in d["stage_history"]],
            evidence_manifest={k: list(v) for k, v in d.get("evidence_manifest", {}).items()},
            validation_results=dict(d.get("validation_results", {})),
            reusable_assets=list(d.get("reusable_assets", [])),
            final_recommendation=d.get("final_recommendation"),
        )


class PipelineViolation(Exception):
    """Vi phạm quy tắc chuyển stage — fail-closed, caller phải xử lý."""


class TaskPipelineEngine:
    """Điều phối pipeline; mọi chuyển stage đều validate."""

    def create_pipeline(
        self,
        owner_request: str,
        task_goal: str,
        acceptance_criteria: list[str] | None = None,
        risk_level: str = "R1",
        constraints: list[str] | None = None,
    ) -> TaskPipeline:
        """Tạo pipeline mới; UNDERSTAND tự động ghi với owner_request làm bằng chứng gốc."""
        if not owner_request or not owner_request.strip():
            raise ValueError("owner_request is required (evidence origin)")
        if not task_goal or not task_goal.strip():
            raise ValueError("task_goal is required")

        spec = TaskSpecification(
            task_id=f"tp_{uuid.uuid4().hex[:12]}",
            task_goal=task_goal,
            acceptance_criteria=list(acceptance_criteria or []),
            constraints=list(constraints or []),
        )
        spec.risks = [f"risk_level={risk_level}"]
        spec.owner_decisions_required = []

        pipeline = TaskPipeline(pipeline_id=spec.task_id, spec=spec)
        # UNDERSTAND tự động — bằng chứng gốc là yêu cầu của chủ nhân
        pipeline.stage_history.append(
            StageRecord(
                stage=PipelineStage.UNDERSTAND,
                at=now_utc(),
                notes=f"Owner request recorded verbatim ({len(owner_request)} chars)",
                evidence_refs=[f"owner_request:{spec.task_id}"],
            )
        )
        pipeline.evidence_manifest["UNDERSTAND"] = [f"owner_request:{spec.task_id}"]
        return pipeline

    def advance(
        self,
        pipeline: TaskPipeline,
        stage: PipelineStage,
        notes: str = "",
        evidence_refs: list[str] | None = None,
        skipped_reason: str | None = None,
        validation: dict[str, Any] | None = None,
    ) -> TaskPipeline:
        """Chuyển tới stage mới với validate fail-closed."""
        refs = list(evidence_refs or [])

        # --- skip phải có lý do ---
        if skipped_reason is not None and not skipped_reason.strip():
            raise PipelineViolation("skipped_reason must be non-empty when skipping a stage")

        # --- thứ tự: chỉ tới trước ---
        if pipeline.stage_history:
            last = pipeline.stage_history[-1]
            last_idx = _STAGE_ORDER[last.stage]
            new_idx = _STAGE_ORDER[stage]
            if new_idx <= last_idx:
                raise PipelineViolation(
                    f"Cannot move from {last.stage.value} to {stage.value}: "
                    f"pipeline stages only move forward"
                )

        # --- VERIFY: fail-honest validation ---
        if stage == PipelineStage.VERIFY and skipped_reason is None:
            spec = pipeline.spec
            if not spec.acceptance_criteria:
                raise PipelineViolation(
                    "VERIFY requires at least one acceptance criterion to check"
                )
            if validation is None:
                raise PipelineViolation(
                    "VERIFY requires validation results (fail-honest: no silent pass)"
                )
            # Mọi tiêu chí phải có kết luận hoặc not_verified — không bỏ trống
            results = validation.get("criteria", {})
            for crit in spec.acceptance_criteria:
                if crit not in results:
                    raise PipelineViolation(
                        f"VERIFY missing conclusion for criterion: {crit!r} "
                        f"(use not_verified=true if evidence is insufficient)"
                    )
            pipeline.validation_results = {
                "criteria": results,
                "verified_at": now_utc(),
            }

        # --- ADVISE: safety gate — không tư vấn khi chưa đối chiếu bằng chứng ---
        if stage == PipelineStage.ADVISE and skipped_reason is None:
            if not pipeline.has_completed(PipelineStage.VERIFY):
                raise PipelineViolation(
                    "ADVISE blocked: VERIFY must complete first (fail-closed safety gate)"
                )
            if not notes.strip():
                raise PipelineViolation(
                    "ADVISE requires a recommendation grounded in verification results"
                )

        # --- REUSE: chỉ ghi asset đã kiểm chứng ---
        if stage == PipelineStage.REUSE and skipped_reason is None:
            if not refs and not notes.strip():
                raise PipelineViolation(
                    "REUSE requires reusable assets (tool/skill/procedure) as evidence"
                )

        record = StageRecord(
            stage=stage,
            at=now_utc(),
            notes=notes,
            evidence_refs=refs,
            skipped_reason=skipped_reason,
        )
        pipeline.stage_history.append(record)
        if refs:
            merged = pipeline.evidence_manifest.setdefault(stage.value, [])
            for r in refs:
                if r not in merged:
                    merged.append(r)
        if stage == PipelineStage.ADVISE and skipped_reason is None:
            pipeline.final_recommendation = notes
        if stage == PipelineStage.REUSE:
            pipeline.reusable_assets = list(dict.fromkeys(refs)) or pipeline.reusable_assets
        return pipeline
