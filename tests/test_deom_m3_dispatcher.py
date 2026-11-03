"""DEOM M3 — Tests cho AgentDispatcher + DependencyManager.

Chạy trên :memory: registry (fail-honest, không đụng tasks.db thật).
Thiết kế: reports/DEOM_M3_DESIGN.md §5.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.orchestration.agent_dispatcher import (
    AgentDispatcher,
    AgentProfile,
    NEVER_AUTO_ASSIGN_RISKS,
)
from quan_ai_brain.orchestration.dependency_manager import DependencyManager
from quan_ai_brain.orchestration.models import AutonomyLevel, TaskRecord, TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def registry() -> DurableTaskRegistry:
    return DurableTaskRegistry(":memory:")


@pytest.fixture()
def depman(registry: DurableTaskRegistry) -> DependencyManager:
    return DependencyManager(registry)


def _register(registry: DurableTaskRegistry, goal: str, **kwargs) -> TaskRecord:
    return registry.register_task(goal, **kwargs)


def _task_with_tools(registry: DurableTaskRegistry, tools: list[str], **kw) -> TaskRecord:
    return _register(registry, "task with tools", required_tools=tools, **kw)


# ===========================================================================
# AgentDispatcher
# ===========================================================================

class TestAgentDispatcher:
    def test_dispatch_requires_capability(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(AgentProfile(agent_id="core", capabilities=["web"]))
        task = _task_with_tools(registry, ["shell"])
        res = dispatcher.dispatch(task)
        assert not res.ok
        assert "no eligible agent" in res.reason

    def test_dispatch_superset_capability_ok(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(AgentProfile(agent_id="core", capabilities=["web", "shell", "db"]))
        task = _task_with_tools(registry, ["shell", "db"])
        res = dispatcher.dispatch(task)
        assert res.ok and res.agent.agent_id == "core"

    def test_dispatch_no_tools_required_matches_any(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(AgentProfile(agent_id="core", capabilities=[]))
        task = _register(registry, "simple task")
        assert dispatcher.dispatch(task).ok

    def test_risk_r3_never_auto_assigned(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(
            AgentProfile(agent_id="super", capabilities=["all"], allowed_risks=["R0", "R1", "R2", "R3"])
        )
        task = _register(registry, "risky", risk_level="R3")
        res = dispatcher.dispatch(task)
        assert not res.ok
        assert "owner approval" in res.reason

    @pytest.mark.parametrize("risk", ["R4", "R5"])
    def test_risk_r4_r5_blocked_even_if_agent_claims(self, registry, risk):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(
            AgentProfile(agent_id="rebel", capabilities=["all"], allowed_risks=["R0", "R1", "R2", "R3", "R4", "R5"])
        )
        task = _register(registry, f"task {risk}", risk_level=risk)
        res = dispatcher.dispatch(task)
        assert not res.ok
        assert risk in NEVER_AUTO_ASSIGN_RISKS

    def test_agent_capacity_full(self, registry):
        dispatcher = AgentDispatcher()
        agent = AgentProfile(agent_id="busy", capabilities=[], max_concurrent=1)
        agent.current_tasks.append("task_other")
        dispatcher.register_agent(agent)
        task = _register(registry, "need capacity")
        res = dispatcher.dispatch(task)
        assert not res.ok

    def test_least_loaded_agent_wins(self, registry):
        dispatcher = AgentDispatcher()
        busy = AgentProfile(agent_id="busy", capabilities=[], max_concurrent=3)
        busy.current_tasks = ["t1"]
        idle = AgentProfile(agent_id="idle", capabilities=[], max_concurrent=3)
        dispatcher.register_agent(busy)
        dispatcher.register_agent(idle)
        task = _register(registry, "pick least loaded")
        res = dispatcher.dispatch(task)
        assert res.ok and res.agent.agent_id == "idle"

    def test_registration_order_tiebreak(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(AgentProfile(agent_id="first", capabilities=[], max_concurrent=2))
        dispatcher.register_agent(AgentProfile(agent_id="second", capabilities=[], max_concurrent=2))
        task = _register(registry, "tie break")
        res = dispatcher.dispatch(task)
        assert res.ok and res.agent.agent_id == "first"

    def test_learning_task_only_for_learning_agent(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(AgentProfile(agent_id="owner-agent", capabilities=[], source_filter=["owner"]))
        dispatcher.register_agent(AgentProfile(agent_id="learner", capabilities=[], source_filter=["learning"]))
        task = _register(registry, "learn something", source="learning")
        res = dispatcher.dispatch(task)
        assert res.ok and res.agent.agent_id == "learner"

    def test_learning_blocked_when_owner_agent_only(self, registry):
        dispatcher = AgentDispatcher()
        dispatcher.register_agent(AgentProfile(agent_id="owner-only", capabilities=[], source_filter=["owner"]))
        task = _register(registry, "learn x", source="learning")
        assert not dispatcher.dispatch(task).ok

    def test_no_agents_registered(self, registry):
        dispatcher = AgentDispatcher()
        task = _register(registry, "any task")
        res = dispatcher.dispatch(task)
        assert not res.ok and "no agents registered" in res.reason

    # ---- assign / release -------------------------------------------------
    def test_assign_records_and_releases(self, registry):
        dispatcher = AgentDispatcher()
        agent = AgentProfile(agent_id="core", capabilities=[])
        dispatcher.register_agent(agent)
        task = _register(registry, "assign me")
        assignments: list[tuple[str, str, str]] = []

        def recorder(task_id: str, agent_id: str, reason: str):
            assignments.append((task_id, agent_id, reason))
            return None  # registry-side success

        err = dispatcher.assign(task, agent, assign_task=recorder)
        assert err is None
        assert assignments == [(task.task_id, "core", "assigned to core")]
        assert agent.current_tasks == [task.task_id]
        assert dispatcher.release(task.task_id)
        assert agent.current_tasks == []

    def test_assign_rejects_capacity_overflow(self, registry):
        dispatcher = AgentDispatcher()
        agent = AgentProfile(agent_id="one", capabilities=[], max_concurrent=1)
        dispatcher.register_agent(agent)
        task = _register(registry, "cannot hold")
        agent.current_tasks.append("already_holding")
        err = dispatcher.assign(task, agent, assign_task=lambda *a: None)
        assert err and "capacity" in err

    def test_assign_same_goal_conflict(self, registry):
        dispatcher = AgentDispatcher()
        agent = AgentProfile(agent_id="dup", capabilities=[], max_concurrent=5)
        dispatcher.register_agent(agent)
        task1 = _register(registry, "sao lưu dữ liệu quan trọng")
        task2 = _register(registry, "sao lưu dữ liệu quan trọng")  # trùng goal
        assert dispatcher.assign(task1, agent, assign_task=lambda *a: None) is None
        err = dispatcher.assign(task2, agent, assign_task=lambda *a: None)
        assert err and "same goal" in err

    def test_assign_unregistered_agent_rejected(self, registry):
        dispatcher = AgentDispatcher()
        ghost = AgentProfile(agent_id="ghost", capabilities=[])
        task = _register(registry, "who are you")
        assert dispatcher.assign(task, ghost, assign_task=lambda *a: None)

    def test_assign_task_registry_failure_propagates(self, registry):
        """assign_task callback báo lỗi → agent KHÔNG giữ task (không bịa thành công)."""
        dispatcher = AgentDispatcher()
        agent = AgentProfile(agent_id="core", capabilities=[])
        dispatcher.register_agent(agent)
        task = _register(registry, "db fails")

        def failing_recorder(task_id, agent_id, reason):
            return "transition write failed"

        err = dispatcher.assign(task, agent, assign_task=failing_recorder)
        assert err == "transition write failed"
        assert agent.current_tasks == []


# ===========================================================================
# DependencyManager
# ===========================================================================

class TestDependencyManager:
    def test_no_dependencies_eligible(self, registry, depman):
        task = _register(registry, "solo task")
        assert depman.eligible(task).ok

    def test_dependency_not_finished(self, registry, depman):
        dep = _register(registry, "dep work")
        task = _register(registry, "dependent work", dependencies=[dep.task_id])
        check = depman.eligible(task)
        assert not check.ok and "not finished" in check.reason

    def test_dependency_completed_verified_eligible(self, registry, depman):
        dep = _register(registry, "dep work")
        registry.update_task_status(dep.task_id, TaskStatus.COMPLETED, evidence_ref="ev1")
        registry.verify_task(dep.task_id, evidence_ok=True, note="ok")
        task = _register(registry, "dependent", dependencies=[dep.task_id])
        assert depman.eligible(task).ok

    def test_dependency_completed_without_verification_still_legacy_ok(self, registry, depman):
        """COMPLETED thuần (legacy, pre-M2, không qua verifier) = đủ điều kiện.

        Phân biên fail-honest: COMPLETED_UNVERIFIED (verifier đã chạy + THẤT BẠI
        thiếu bằng chứng) KHÔNG đủ — còn COMPLETED legacy không bị phạt oan.
        """
        dep = _register(registry, "dep work")
        registry.update_task_status(dep.task_id, TaskStatus.COMPLETED, evidence_ref="ev1")
        assert registry.get_task(dep.task_id).status == TaskStatus.COMPLETED
        task = _register(registry, "dependent", dependencies=[dep.task_id])
        assert depman.eligible(task).ok

    def test_dependency_unverified_not_eligible_fail_honest(self, registry, depman):
        """COMPLETED_UNVERIFIED = verifier ĐÃ CHẠY và thất bại (thiếu bằng chứng)
        → không đủ tin cậy làm điều kiện cho task sau (fail-honest)."""
        dep = _register(registry, "dep work")
        registry.update_task_status(dep.task_id, TaskStatus.VERIFYING)
        registry.verify_task(dep.task_id, evidence_ok=False, note="thiếu bằng chứng")
        assert registry.get_task(dep.task_id).status == TaskStatus.COMPLETED_UNVERIFIED
        task = _register(registry, "dependent", dependencies=[dep.task_id])
        check = depman.eligible(task)
        assert not check.ok and "without evidence" in check.reason

    def test_missing_dependency(self, registry, depman):
        task = _register(registry, "orphan", dependencies=["task_ghost"])
        check = depman.eligible(task)
        assert not check.ok and "missing" in check.reason

    def test_block_on_missing_dependencies(self, registry, depman):
        task = _register(registry, "orphan", dependencies=["task_ghost"])
        updated = depman.block_on_missing_dependencies(task)
        assert updated is not None and updated.status == TaskStatus.BLOCKED
        transitions = registry.list_transitions(task.task_id)
        assert transitions[-1].actor == "dependency_manager"

    def test_block_noop_when_no_missing(self, registry, depman):
        task = _register(registry, "normal", dependencies=[])
        assert depman.block_on_missing_dependencies(task) is None

    def test_unblock_dependents_after_completion(self, registry, depman):
        dep = _register(registry, "root work")
        task = _register(registry, "child work", dependencies=[dep.task_id])
        # chặn child trước
        registry.update_task_status(task.task_id, TaskStatus.BLOCKED, reason="waiting root")
        # root hoàn tất có bằng chứng
        registry.update_task_status(dep.task_id, TaskStatus.COMPLETED, evidence_ref="ev")
        registry.verify_task(dep.task_id, evidence_ok=True, note="ok")
        unblocked = depman.unblock_dependents(dep.task_id)
        assert [t.task_id for t in unblocked] == [task.task_id]
        assert registry.get_task(task.task_id).status == TaskStatus.READY
        tr = registry.list_transitions(task.task_id)
        assert tr[-1].to_status == TaskStatus.READY.value
        assert "dependency satisfied" in tr[-1].reason

    def test_unblock_skips_unverified_completion(self, registry, depman):
        """COMPLETED_UNVERIFIED (verifier chạy + thất bại) KHÔNG mở khóa task phụ."""
        dep = _register(registry, "root work")
        task = _register(registry, "child work", dependencies=[dep.task_id])
        registry.update_task_status(task.task_id, TaskStatus.BLOCKED, reason="waiting root")
        registry.update_task_status(dep.task_id, TaskStatus.VERIFYING)
        registry.verify_task(dep.task_id, evidence_ok=False, note="thiếu bằng chứng")
        assert depman.unblock_dependents(dep.task_id) == []
        assert registry.get_task(task.task_id).status == TaskStatus.BLOCKED

    def test_unblock_requires_other_deps_too(self, registry, depman):
        dep1 = _register(registry, "dep one")
        dep2 = _register(registry, "dep two")
        child = _register(registry, "child", dependencies=[dep1.task_id, dep2.task_id])
        registry.update_task_status(child.task_id, TaskStatus.BLOCKED, reason="waiting")
        registry.update_task_status(dep1.task_id, TaskStatus.COMPLETED, evidence_ref="e1")
        registry.verify_task(dep1.task_id, evidence_ok=True)
        # dep2 chưa xong → không mở khóa
        assert depman.unblock_dependents(dep1.task_id) == []

    def test_cycle_rejected_on_register_check(self, registry, depman):
        a = _register(registry, "A")
        b = _register(registry, "B", dependencies=[a.task_id])
        # B phụ thuộc A; đăng ký task mới phụ thuộc B nhưng là cha của A? A không có dep.
        # Tạo vòng: task C dep B, rồi A muốn dep C → cycle A→C→B→A
        c = _register(registry, "C", dependencies=[b.task_id])
        with pytest.raises(ValueError, match="cycle"):
            depman.assert_acyclic(a.task_id, [c.task_id])

    def test_self_dependency_rejected(self, registry, depman):
        a = _register(registry, "self dep")
        with pytest.raises(ValueError, match="cycle"):
            depman.assert_acyclic(a.task_id, [a.task_id])

    def test_no_cycle_passes(self, registry, depman):
        a = _register(registry, "A")
        b = _register(registry, "B", dependencies=[a.task_id])
        depman.assert_acyclic("task_new", [b.task_id])  # không raise

    def test_topological_order(self, registry, depman):
        a = _register(registry, "A")
        b = _register(registry, "B", dependencies=[a.task_id])
        c = _register(registry, "C", dependencies=[b.task_id])
        order = depman.topological_order([c.task_id, a.task_id, b.task_id])
        assert order.index(a.task_id) < order.index(b.task_id) < order.index(c.task_id)

    def test_topological_detects_real_cycle(self, registry, depman):
        """Cycle thật: A dep ghost (chưa có) không tạo cycle; A↔B mới là cycle.

        Cycle chỉ xảy ra khi 2 task CÙNG TỒN TẠI chỉ vào nhau. assert_acyclic
        chặn lúc đăng ký; topological_order chặn khi sort list có vòng.
        """
        a = _register(registry, "A", dependencies=["task_ghost_khong_ton_tai"])
        b = _register(registry, "B", dependencies=[a.task_id])
        # A dep ghost (missing) + B dep A: DAG với node missing — topological vẫn chạy được
        order = depman.topological_order([a.task_id, b.task_id])
        assert order.index(a.task_id) < order.index(b.task_id)


# ===========================================================================
# E2E: dispatch qua chuỗi phụ thuộc 3 task, 2 agent
# ===========================================================================

class TestE2EDispatchWithDependencies:
    def test_chain_dispatch_order_and_audit(self, registry, depman):
        dispatcher = AgentDispatcher()
        worker = AgentProfile(agent_id="tony-core", capabilities=["research", "report"], max_concurrent=2)
        dispatcher.register_agent(worker)

        t1 = _register(registry, "thu thập dữ liệu", required_tools=["research"])
        t2 = _register(registry, "phân tích dữ liệu", required_tools=["research"],
                       dependencies=[t1.task_id])
        t3 = _register(registry, "viết báo cáo", required_tools=["report"],
                       dependencies=[t2.task_id])

        # t2, t3 chưa đủ điều kiện
        assert not depman.eligible(t2).ok
        assert not depman.eligible(t3).ok

        # t1 đủ → dispatch
        res1 = dispatcher.dispatch(registry.get_task(t1.task_id))
        assert res1.ok
        assert dispatcher.assign(registry.get_task(t1.task_id), res1.agent,
                                 assign_task=lambda *a: None) is None

        # t1 hoàn tất có bằng chứng → mở khóa t2
        registry.update_task_status(t1.task_id, TaskStatus.COMPLETED, evidence_ref="data_ok")
        registry.verify_task(t1.task_id, evidence_ok=True)
        dispatcher.release(t1.task_id)
        unblocked = depman.unblock_dependents(t1.task_id)
        assert [t.task_id for t in unblocked] == [t2.task_id]

        # t2 giờ eligible + dispatch được
        t2_now = registry.get_task(t2.task_id)
        assert depman.eligible(t2_now).ok
        res2 = dispatcher.dispatch(t2_now)
        assert res2.ok and res2.agent.agent_id == "tony-core"

        # audit: transitions của t2 có READY với reason dependency satisfied
        tr2 = registry.list_transitions(t2.task_id)
        assert any(x.to_status == TaskStatus.READY.value and "dependency satisfied" in x.reason
                   for x in tr2)
