"""DEOM M2 tests — schema mở rộng, transition log, work queue, verifier, deadline.

Nguyên tắc: chạy trên :memory: (không đụng tasks.db thật); mọi hành vi mới
phải fail-honest (không tự phong COMPLETED_VERIFIED khi không có bằng chứng).
"""
from __future__ import annotations

import pytest

from quan_ai_brain.orchestration.models import (
    TaskStatus,
)
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def registry() -> DurableTaskRegistry:
    return DurableTaskRegistry(":memory:")


class TestDeomSchema:
    def test_new_columns_exist(self, registry: DurableTaskRegistry):
        cols = {row[1] for row in registry._conn.execute("PRAGMA table_info(durable_tasks)")}
        for col in (
            "priority", "deadline_utc", "parent_task_id", "dependencies_json",
            "required_tools_json", "assigned_agents_json", "permission_scope_json",
            "progress_weight_json", "source", "verified_at_utc", "verification_note",
        ):
            assert col in cols, f"missing DEOM column: {col}"

    def test_transitions_table_exists(self, registry: DurableTaskRegistry):
        tables = {
            r[0]
            for r in registry._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "task_transitions" in tables


class TestRegisterWithDeomFields:
    def test_register_with_priority_and_deadline(self, registry: DurableTaskRegistry):
        t = registry.register_task(
            "gấp: kiểm tra server chết",
            priority=1,
            deadline_utc="2026-11-02T08:00:00+00:00",
            source="owner",
            initial_status=TaskStatus.RECEIVED,
        )
        assert t.priority == 1
        assert t.deadline_utc == "2026-11-02T08:00:00+00:00"
        assert t.source == "owner"
        assert t.status == TaskStatus.RECEIVED

    def test_priority_clamped(self, registry: DurableTaskRegistry):
        t = registry.register_task("x", priority=99)
        assert t.priority == 5
        t2 = registry.register_task("y", priority=-3)
        assert t2.priority == 1

    def test_invalid_source_falls_back_owner(self, registry: DurableTaskRegistry):
        t = registry.register_task("z", source="hacker")
        assert t.source == "owner"

    def test_dependencies_roundtrip(self, registry: DurableTaskRegistry):
        parent = registry.register_task("task cha", source="owner")
        child = registry.register_task(
            "task con",
            parent_task_id=parent.task_id,
            dependencies=[parent.task_id],
            required_tools=["email_intake"],
            assigned_agents=["tony-bdi-1"],
            permission_scope=["memory:read", "task:execute"],
            progress_weight={"collect": 0.6, "report": 0.4},
        )
        loaded = registry.get_task(child.task_id)
        assert loaded.parent_task_id == parent.task_id
        assert loaded.dependencies == [parent.task_id]
        assert loaded.required_tools == ["email_intake"]
        assert loaded.assigned_agents == ["tony-bdi-1"]
        assert loaded.permission_scope == ["memory:read", "task:execute"]
        assert loaded.progress_weight == {"collect": 0.6, "report": 0.4}


class TestTransitionLog:
    def test_birth_transition_logged(self, registry: DurableTaskRegistry):
        t = registry.register_task("a", source="system")
        trs = registry.list_transitions(t.task_id)
        assert len(trs) == 1
        assert trs[0].from_status is None
        assert trs[0].to_status == "PENDING"
        assert trs[0].actor == "system"

    def test_status_change_logged_with_actor_reason(self, registry: DurableTaskRegistry):
        t = registry.register_task("b")
        registry.update_task_status(
            t.task_id, TaskStatus.IN_PROGRESS, actor="tony", reason="bắt đầu chạy"
        )
        trs = registry.list_transitions(t.task_id)
        assert len(trs) == 2
        assert trs[1].from_status == "PENDING"
        assert trs[1].to_status == "IN_PROGRESS"
        assert trs[1].actor == "tony"
        assert trs[1].reason == "bắt đầu chạy"

    def test_owner_direct_assign_records_owner_actor(self, registry: DurableTaskRegistry):
        t = registry.register_task("c")
        registry.update_task_status(t.task_id, TaskStatus.APPROVED, actor="owner", reason="owner giao trực tiếp")
        trs = registry.list_transitions(t.task_id)
        assert trs[-1].actor == "owner"
        assert trs[-1].to_status == "APPROVED"


class TestWorkQueue:
    def test_priority_order(self, registry: DurableTaskRegistry):
        low = registry.register_task("low", priority=5)
        crit = registry.register_task("crit", priority=1)
        high = registry.register_task("high", priority=2)
        q = registry.work_queue(limit=10)
        ids = [t.task_id for t in q]
        assert ids.index(crit.task_id) < ids.index(high.task_id) < ids.index(low.task_id)

    def test_deadline_before_undated(self, registry: DurableTaskRegistry):
        a = registry.register_task("không deadline", priority=2)
        b = registry.register_task("có deadline", priority=2, deadline_utc="2026-11-02T00:00:00+00:00")
        q = registry.work_queue(limit=10)
        ids = [t.task_id for t in q]
        assert ids.index(b.task_id) < ids.index(a.task_id)

    def test_learning_yields_to_owner(self, registry: DurableTaskRegistry):
        learn = registry.register_task("tự học", priority=1, source="learning")
        own = registry.register_task("việc anh giao", priority=5, source="owner")
        q = registry.work_queue(limit=10)
        ids = [t.task_id for t in q]
        assert own.task_id in ids
        assert learn.task_id not in ids  # learning bị dồn lại khi owner có việc

    def test_learning_runs_when_no_owner_tasks(self, registry: DurableTaskRegistry):
        learn = registry.register_task("tự học", priority=3, source="learning")
        q = registry.work_queue(limit=10)
        assert [t.task_id for t in q] == [learn.task_id]

    def test_completed_not_in_queue(self, registry: DurableTaskRegistry):
        t = registry.register_task("done")
        registry.update_task_status(t.task_id, TaskStatus.COMPLETED)
        q = registry.work_queue(limit=10)
        assert t.task_id not in [x.task_id for x in q]


class TestTaskVerifier:
    def test_completed_without_evidence_is_unverified(self, registry: DurableTaskRegistry):
        t = registry.register_task("x", acceptance_criteria=["bằng chứng A"])
        registry.update_task_status(t.task_id, TaskStatus.VERIFYING)
        v = registry.verify_task(t.task_id, evidence_ok=False, note="chưa có bằng chứng")
        assert v.status == TaskStatus.COMPLETED_UNVERIFIED

    def test_completed_with_evidence_is_verified(self, registry: DurableTaskRegistry):
        t = registry.register_task("x", acceptance_criteria=["bằng chứng A"])
        registry.update_task_status(t.task_id, TaskStatus.VERIFYING)
        v = registry.verify_task(t.task_id, evidence_ok=True, note="test pass", evidence_ref="reports/x.md")
        assert v.status == TaskStatus.COMPLETED_VERIFIED

    def test_verify_requires_verifying_state(self, registry: DurableTaskRegistry):
        t = registry.register_task("y")
        with pytest.raises(ValueError):
            registry.verify_task(t.task_id, evidence_ok=True)

    def test_verify_only_from_allowed_states(self, registry: DurableTaskRegistry):
        t = registry.register_task("z")
        registry.update_task_status(t.task_id, TaskStatus.IN_PROGRESS)
        with pytest.raises(ValueError):
            registry.verify_task(t.task_id, evidence_ok=True)


class TestDeadlineExpiry:
    def test_overdue_task_expires(self, registry: DurableTaskRegistry):
        t = registry.register_task("quá hạn", deadline_utc="2020-01-01T00:00:00+00:00")
        expired = registry.expire_overdue()
        assert t.task_id in [x.task_id for x in expired]
        loaded = registry.get_task(t.task_id)
        assert loaded.status == TaskStatus.EXPIRED

    def test_future_deadline_not_expired(self, registry: DurableTaskRegistry):
        t = registry.register_task("còn hạn", deadline_utc="2099-01-01T00:00:00+00:00")
        expired = registry.expire_overdue()
        assert t.task_id not in [x.task_id for x in expired]

    def test_completed_overdue_not_touched(self, registry: DurableTaskRegistry):
        t = registry.register_task("quá hạn nhưng xong", deadline_utc="2020-01-01T00:00:00+00:00")
        registry.update_task_status(t.task_id, TaskStatus.COMPLETED)
        expired = registry.expire_overdue()
        assert t.task_id not in [x.task_id for x in expired]
        assert registry.get_task(t.task_id).status == TaskStatus.COMPLETED


class TestBackwardCompat:
    def test_legacy_status_enum_values_unchanged(self):
        assert TaskStatus.PENDING.value == "PENDING"
        assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TaskStatus.WAITING_APPROVAL.value == "WAITING_APPROVAL"
        assert TaskStatus.APPROVED.value == "APPROVED"
        assert TaskStatus.COMPLETED.value == "COMPLETED"
        assert TaskStatus.FAILED.value == "FAILED"
        assert TaskStatus.CANCELLED.value == "CANCELLED"
        assert TaskStatus.OUTCOME_UNKNOWN.value == "OUTCOME_UNKNOWN"
        assert TaskStatus.BLOCKED.value == "BLOCKED"

    def test_old_record_defaults(self, registry: DurableTaskRegistry):
        t = registry.register_task("mặc định")
        assert t.priority == 3
        assert t.deadline_utc is None
        assert t.source == "owner"
        assert t.dependencies == []
        assert t.status == TaskStatus.PENDING
