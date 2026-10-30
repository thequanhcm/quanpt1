"""Tests — Master Prompt V6: Task-Driven Learning Pipeline (task_pipeline.py).

Phủ: thứ tự stage, skip có lý do, safety gate ADVISE/VERIFY, fail-honest,
persist round-trip, reuse.
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

import pytest

from quan_ai_brain.cognition.task_pipeline import (
    PipelineStage,
    PipelineViolation,
    TaskPipelineEngine,
)


@pytest.fixture()
def engine() -> TaskPipelineEngine:
    return TaskPipelineEngine()


@pytest.fixture()
def pipeline(engine: TaskPipelineEngine):
    return engine.create_pipeline(
        owner_request="Kiểm tra tiến độ các công việc trong hệ thống",
        task_goal="Đối chiếu trạng thái task giữa tasks.db và báo cáo",
        acceptance_criteria=[
            "Mọi task đều có trạng thái đối chiếu được",
            "Mâu thuẫn (nếu có) được giữ nguyên 2 phiên bản",
        ],
        risk_level="R1",
    )


class TestCreation:
    def test_create_pipeline_records_understand(self, engine):
        p = engine.create_pipeline(
            owner_request="Yêu cầu gốc của chủ nhân", task_goal="Mục tiêu"
        )
        assert p.current_stage() == PipelineStage.UNDERSTAND
        assert p.stage_history[0].evidence_refs == [f"owner_request:{p.pipeline_id}"]

    def test_empty_owner_request_rejected(self, engine):
        with pytest.raises(ValueError):
            engine.create_pipeline(owner_request="   ", task_goal="X")

    def test_empty_task_goal_rejected(self, engine):
        with pytest.raises(ValueError):
            engine.create_pipeline(owner_request="OK", task_goal="")


class TestStageOrdering:
    def test_forward_single_step(self, engine, pipeline):
        engine.advance(pipeline, PipelineStage.DECOMPOSE, notes="chia nhỏ")
        assert pipeline.current_stage() == PipelineStage.DECOMPOSE

    def test_backward_move_rejected(self, engine, pipeline):
        engine.advance(pipeline, PipelineStage.DECOMPOSE, notes="ok")
        with pytest.raises(PipelineViolation):
            engine.advance(pipeline, PipelineStage.UNDERSTAND, notes="quay lại")

    def test_same_stage_rejected(self, engine, pipeline):
        engine.advance(pipeline, PipelineStage.DECOMPOSE, notes="ok")
        with pytest.raises(PipelineViolation):
            engine.advance(pipeline, PipelineStage.DECOMPOSE, notes="giữ nguyên")

    def test_skip_requires_reason(self, engine, pipeline):
        with pytest.raises(PipelineViolation):
            engine.advance(pipeline, PipelineStage.DECOMPOSE, notes="", skipped_reason="  ")
        engine.advance(
            pipeline, PipelineStage.DECOMPOSE, notes="", skipped_reason="bài toán 1 bước"
        )
        rec = pipeline.stage_history[-1]
        assert rec.skipped_reason == "bài toán 1 bước"
        assert pipeline.current_stage() == PipelineStage.DECOMPOSE


class TestSafetyGates:
    def test_verify_requires_criteria(self, engine, pipeline):
        p = engine.create_pipeline(owner_request="r", task_goal="g")
        # đi tới ANALYZE rồi mới VERIFY
        stages = [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]
        for s in stages:
            engine.advance(p, s, notes="ok", skipped_reason="increment test" if s != PipelineStage.ANALYZE else None)
        with pytest.raises(PipelineViolation):
            engine.advance(p, PipelineStage.VERIFY, notes="thiếu validation")
        # criteria trống cũng chặn
        with pytest.raises(PipelineViolation):
            engine.advance(p, PipelineStage.VERIFY, notes="", validation={"criteria": {}})

    def test_verify_missing_criterion_rejected(self, engine, pipeline):
        # đi tới ANALYZE
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]:
            engine.advance(pipeline, s, notes="ok")
        with pytest.raises(PipelineViolation):
            engine.advance(
                pipeline,
                PipelineStage.VERIFY,
                notes="bỏ 1 tiêu chí",
                validation={"criteria": {pipeline.spec.acceptance_criteria[0]: {"passed": True}}},
            )

    def test_verify_fail_honest_allowed(self, engine, pipeline):
        """Thiếu bằng chứng → not_verified=True được chấp nhận (fail-honest)."""
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]:
            engine.advance(pipeline, s, notes="ok")
        crit1, crit2 = pipeline.spec.acceptance_criteria
        engine.advance(
            pipeline,
            PipelineStage.VERIFY,
            notes="1 tiêu chí thiếu bằng chứng",
            validation={
                "criteria": {
                    crit1: {"passed": True, "evidence": ["tasks.db"]},
                    crit2: {"passed": False, "not_verified": True, "reason": "nguồn chưa truy cập"},
                }
            },
            evidence_refs=["data/tasks.db"],
        )
        assert pipeline.has_completed(PipelineStage.VERIFY)
        assert pipeline.validation_results["criteria"][crit2]["not_verified"] is True

    def test_advise_before_verify_blocked(self, engine, pipeline):
        """Safety gate cốt lõi: chưa VERIFY thì không được tư vấn."""
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]:
            engine.advance(pipeline, s, notes="ok")
        with pytest.raises(PipelineViolation):
            engine.advance(pipeline, PipelineStage.ADVISE, notes="khuyến nghị vội")

    def test_advise_after_verify_allowed(self, engine, pipeline):
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]:
            engine.advance(pipeline, s, notes="ok")
        crit1, crit2 = pipeline.spec.acceptance_criteria
        engine.advance(
            pipeline,
            PipelineStage.VERIFY,
            notes="đủ bằng chứng",
            validation={
                "criteria": {
                    crit1: {"passed": True, "evidence": ["data/tasks.db"]},
                    crit2: {"passed": True, "evidence": ["data/tasks.db"]},
                }
            },
        )
        engine.advance(
            pipeline,
            PipelineStage.ADVISE,
            notes="Khuyến nghị: 2 task PENDING cần chủ nhân xác nhận trạng thái",
        )
        assert pipeline.final_recommendation == (
            "Khuyến nghị: 2 task PENDING cần chủ nhân xác nhận trạng thái"
        )

    def test_advise_requires_nonempty_recommendation(self, engine, pipeline):
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
            PipelineStage.VERIFY,
        ]:
            crit1, crit2 = pipeline.spec.acceptance_criteria
            if s == PipelineStage.VERIFY:
                engine.advance(
                    pipeline, s, notes="ok",
                    validation={"criteria": {
                        crit1: {"passed": True}, crit2: {"passed": True},
                    }},
                )
            else:
                engine.advance(pipeline, s, notes="ok")
        with pytest.raises(PipelineViolation):
            engine.advance(pipeline, PipelineStage.ADVISE, notes="")


class TestReuse:
    def test_reuse_records_assets(self, engine, pipeline):
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]:
            engine.advance(pipeline, s, notes="ok")
        crit1, crit2 = pipeline.spec.acceptance_criteria
        engine.advance(
            pipeline, PipelineStage.VERIFY, notes="ok",
            validation={"criteria": {crit1: {"passed": True}, crit2: {"passed": True}}},
        )
        engine.advance(pipeline, PipelineStage.ADVISE, notes="khuyến nghị X")
        engine.advance(
            pipeline,
            PipelineStage.REUSE,
            notes="lưu quy trình",
            evidence_refs=["tool:task_pipeline", "skill:progress_audit"],
        )
        assert pipeline.reusable_assets == ["tool:task_pipeline", "skill:progress_audit"]

    def test_reuse_requires_assets(self, engine, pipeline):
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
            PipelineStage.VERIFY,
        ]:
            crit1, crit2 = pipeline.spec.acceptance_criteria
            if s == PipelineStage.VERIFY:
                engine.advance(
                    pipeline, s, notes="ok",
                    validation={"criteria": {crit1: {"passed": True}, crit2: {"passed": True}}},
                )
            else:
                engine.advance(pipeline, s, notes="ok")
        engine.advance(pipeline, PipelineStage.ADVISE, notes="rec")
        with pytest.raises(PipelineViolation):
            engine.advance(pipeline, PipelineStage.REUSE, notes="", evidence_refs=[])


class TestPersistence:
    def test_round_trip(self, engine, pipeline):
        for s in [
            PipelineStage.DECOMPOSE,
            PipelineStage.DISCOVER,
            PipelineStage.PLAN,
            PipelineStage.LEARN,
            PipelineStage.BUILD,
            PipelineStage.TEST,
            PipelineStage.ANALYZE,
        ]:
            engine.advance(pipeline, s, notes="ok")
        crit1, crit2 = pipeline.spec.acceptance_criteria
        engine.advance(
            pipeline, PipelineStage.VERIFY, notes="ok",
            validation={"criteria": {crit1: {"passed": True}, crit2: {"passed": True}}},
            evidence_refs=["data/tasks.db"],
        )
        engine.advance(pipeline, PipelineStage.ADVISE, notes="rec")
        engine.advance(
            pipeline, PipelineStage.REUSE, notes="", evidence_refs=["tool:task_pipeline"]
        )

        data = pipeline.to_dict()
        restored = type(pipeline).from_dict(data)
        assert restored.pipeline_id == pipeline.pipeline_id
        assert restored.current_stage() == PipelineStage.REUSE
        assert restored.final_recommendation == pipeline.final_recommendation
        assert restored.validation_results == pipeline.validation_results
        assert restored.evidence_manifest["VERIFY"] == ["data/tasks.db"]
        assert restored.reusable_assets == ["tool:task_pipeline"]
