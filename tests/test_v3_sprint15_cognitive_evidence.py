"""Tests — Sprint 15: Evidence Traceability + Cognitive State Reconciliation.

Tmp DB 100%; CognitiveState dựng qua module của nhánh song song (đã 12/12 test xanh);
không đụng DB production. Test both paths: persist + API + fail-open.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.cognitive_state import (
    BeliefKind,
    CognitiveState,
)
from quan_ai_brain.memory.models import VerificationStatus
from quan_ai_brain.orchestration.models import AutonomyLevel
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.models import TaskPlan, TaskStep


def _cog_state(with_contradiction: bool = False) -> CognitiveState:
    cs = CognitiveState(task_id="plan-cog-test", goal="g")
    cs.add_belief(
        statement="Server chạy trên PC core",
        kind=BeliefKind.FACT_RETRIEVED,
        source_ref="memory:m1",
        confidence=0.8,
        verification_status=VerificationStatus.VERIFIED.value,
    )
    cs.add_belief(
        statement="Tri thức ứng viên: chưa ai duyệt",
        kind=BeliefKind.HYPOTHESIS,
        source_ref="memory:m2",
        confidence=0.3,
        verification_status=VerificationStatus.CANDIDATE.value,
    )
    if with_contradiction:
        cs.record_contradiction(
            topic="backup_time",
            claim_a="backup chạy 2AM",
            source_a="memory:m1",
            status_a="VERIFIED",
            claim_b="backup chạy 3AM",
            source_b="memory:m9",
            status_b="UNVERIFIED",
            notes="test contradiction",
        )
    return cs


def _plan(cog: CognitiveState | None, warnings: list[str] | None = None) -> TaskPlan:
    return TaskPlan(
        goal="kiểm tra trạng thái",
        steps=[TaskStep(name="read_status", description="Đọc trạng thái", expected_output="ok")],
        summary="s",
        source="mock",
        warnings=warnings or [],
        memory_refs=["m1"],
        cognitive_state=cog,
    )


@pytest.fixture()
def orch(tmp_path: Path) -> PlanOrchestrator:
    reg = DurableTaskRegistry(tmp_path / "tasks.db", workspace=tmp_path)
    return PlanOrchestrator(task_registry=reg, workspace=tmp_path)


class TestPersistCognitiveState:
    def test_state_persisted_in_checkpoint(self, orch):
        rec = orch.submit_plan(_plan(_cog_state()))
        stored = orch.task_registry.get_task(rec.task_id)
        snap = (stored.checkpoint_data or {}).get("sprint15_cognitive_state")
        assert isinstance(snap, dict) and snap["has_cognitive_state"] is True
        beliefs = snap["cognitive_state"]["beliefs"]
        assert len(beliefs) == 2
        kinds = {b["kind"] for b in beliefs}
        assert "fact_retrieved" in kinds and "hypothesis" in kinds
        # provenance giữ nguyên
        assert any(b["source_ref"] == "memory:m1" for b in beliefs)
        assert snap["plan_id"] == rec.correlation_id or snap["plan_id"]

    def test_candidate_stays_hypothesis_low_confidence(self, orch):
        rec = orch.submit_plan(_plan(_cog_state()))
        snap = orch.task_registry.get_task(rec.task_id).checkpoint_data["sprint15_cognitive_state"]
        cand = [b for b in snap["cognitive_state"]["beliefs"] if b["verification_status"] == "CANDIDATE"]
        assert cand and cand[0]["kind"] == "hypothesis" and cand[0]["confidence"] <= 0.3

    def test_warnings_persisted_redacted(self, orch):
        rec = orch.submit_plan(_plan(_cog_state(), warnings=["CẢNH BÁO DỮ LIỆU CŨ: 1 bản ghi"]))
        snap = orch.task_registry.get_task(rec.task_id).checkpoint_data["sprint15_cognitive_state"]
        assert any("CẢNH BÁO DỮ LIỆU CŨ" in w for w in snap["plan_warnings"])

    def test_no_cog_state_still_persists_flag_false(self, orch):
        rec = orch.submit_plan(_plan(None))
        snap = orch.task_registry.get_task(rec.task_id).checkpoint_data["sprint15_cognitive_state"]
        assert snap["has_cognitive_state"] is False and snap["cognitive_state"] is None

    def test_idempotent_replay_does_not_overwrite_checkpoint(self, orch):
        """Task existing (replay theo idempotency_key) không bị ghi đè checkpoint."""
        plan1 = _plan(_cog_state())
        rec1 = orch.submit_plan(plan1, idempotency_key="idem_s15_x")
        first_ckpt = orch.task_registry.get_task(rec1.task_id).checkpoint_data
        # replay cùng key — task đã tồn tại → return sớm, checkpoint không đổi
        plan2 = _plan(None, warnings=["KHÁC"])
        rec2 = orch.submit_plan(plan2, idempotency_key="idem_s15_x")
        assert rec2.task_id == rec1.task_id
        second_ckpt = orch.task_registry.get_task(rec1.task_id).checkpoint_data
        assert second_ckpt == first_ckpt

    def test_status_unchanged_by_checkpoint_write(self, orch):
        rec = orch.submit_plan(_plan(_cog_state()))
        stored = orch.task_registry.get_task(rec.task_id)
        assert stored.status.value == "PENDING"  # ghi checkpoint không đổi status

    def test_fail_open_on_registry_error(self, orch, monkeypatch):
        """Registry lỗi khi ghi checkpoint → submit vẫn thành công (fail-open)."""
        def boom(*a, **k):
            raise RuntimeError("db locked")
        monkeypatch.setattr(orch.task_registry, "update_task_status", boom, raising=False)
        rec = orch.submit_plan(_plan(_cog_state()))
        assert rec.task_id  # đăng ký vẫn thành công


class TestAPI:
    def _handler(self, monkeypatch, tmp_path: Path):
        import quan_ai_brain.web.server as srv
        from quan_ai_brain.web.server import BrainAPIHandler

        _Fake._h = BrainAPIHandler._handle_api_task_cognitive_state
        _Fake.sent = None
        _Fake.error = None
        monkeypatch.setattr(srv, "_find_workspace_root", lambda: tmp_path, raising=False)

    def _registry(self, tmp_path: Path) -> DurableTaskRegistry:
        (tmp_path / "data").mkdir(exist_ok=True)
        reg = DurableTaskRegistry(tmp_path / "data" / "tasks.db", workspace=tmp_path)
        return reg

    def test_has_state_with_needs_review(self, monkeypatch, tmp_path):
        self._handler(monkeypatch, tmp_path)
        reg = self._registry(tmp_path)
        orch = PlanOrchestrator(task_registry=reg, workspace=tmp_path)
        rec = orch.submit_plan(_plan(_cog_state(with_contradiction=True)))
        _Fake().run(f"task_id={rec.task_id}")
        assert _Fake.sent["success"] is True
        assert _Fake.sent["has_cognitive_state"] is True
        assert _Fake.sent["needs_review"] is True
        assert _Fake.sent["unresolved_contradiction_count"] == 1
        # cả 2 nguồn contradiction vẫn được giữ
        conts = _Fake.sent["cognitive_state"]["contradictions"]
        assert conts and conts[0]["claim_a"] and conts[0]["claim_b"]
        assert conts[0]["resolution_status"] == "UNRESOLVED"

    def test_resolved_contradiction_not_needs_review(self, monkeypatch, tmp_path):
        self._handler(monkeypatch, tmp_path)
        reg = self._registry(tmp_path)
        orch = PlanOrchestrator(task_registry=reg, workspace=tmp_path)
        cs = _cog_state(with_contradiction=True)
        cs.contradictions[0].resolution_status = "CONTEXT_DIFFERENCE"
        rec = orch.submit_plan(_plan(cs))
        _Fake().run(f"task_id={rec.task_id}")
        assert _Fake.sent["needs_review"] is False

    def test_old_task_honest_false(self, monkeypatch, tmp_path):
        """Task cũ (không có sprint15 snapshot) → has_cognitive_state=false, không bịa."""
        self._handler(monkeypatch, tmp_path)
        reg = self._registry(tmp_path)
        rec = reg.register_task(goal="task cổ", risk_level="R1")
        _Fake().run(f"task_id={rec.task_id}")
        assert _Fake.sent["success"] is True
        assert _Fake.sent["has_cognitive_state"] is False
        assert "trước Sprint 15" in _Fake.sent["reason"]

    def test_missing_task_404(self, monkeypatch, tmp_path):
        self._handler(monkeypatch, tmp_path)
        self._registry(tmp_path)
        _Fake().run("task_id=task_khong_ton_tai")
        assert _Fake.error and _Fake.error["code"] == 404

    def test_missing_param_400(self, monkeypatch, tmp_path):
        self._handler(monkeypatch, tmp_path)
        self._registry(tmp_path)
        _Fake().run("")
        assert _Fake.error and _Fake.error["code"] == 400

    def test_remote_403(self, monkeypatch, tmp_path):
        self._handler(monkeypatch, tmp_path)
        self._registry(tmp_path)
        h = _Fake()
        h.client_address = ("10.1.2.3", 5)
        h.run("task_id=t1")
        assert _Fake.error and _Fake.error["code"] == 403


class _Fake:
    sent: Any = None
    error: Any = None
    client_address = ("127.0.0.1", 1)
    _h: Any = None

    def run(self, query: str) -> None:
        _Fake._h(self, query)

    @staticmethod
    def _send_json(payload, code=200):
        _Fake.sent = payload
        _Fake.error = None

    @staticmethod
    def _send_error_json(msg, code=400):
        _Fake.error = {"error": msg, "code": code}
        _Fake.sent = None
