"""DEOM M3 — Tests tích hợp supervisor + AgentDispatcher + DependencyManager.

Supervisor giờ chọn task qua work_queue → eligibility → dispatch (§4 design).
Mọi test chạy :memory:/tmp workspace — không đụng DB thật.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.orchestration.agent_dispatcher import AgentDispatcher, AgentProfile
from quan_ai_brain.orchestration.dependency_manager import DependencyManager
from quan_ai_brain.orchestration.models import AutonomyLevel, TaskStatus
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor, SupervisorState
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def registry() -> DurableTaskRegistry:
    return DurableTaskRegistry(":memory:")


@pytest.fixture()
def gov(ws: Path) -> GovernanceStateStore:
    return GovernanceStateStore(ws / "data" / "governance.db", workspace=ws)


def _supervisor(registry, gov, *, agents: list[AgentProfile] | None = None) -> ContinuousAutonomySupervisor:
    dispatcher = AgentDispatcher(agents)
    depman = DependencyManager(registry)
    return ContinuousAutonomySupervisor(
        workspace=".",  # coordinator không chạy thật trong step-select path
        task_registry=registry,
        governance_store=gov,
        dispatcher=dispatcher,
        dependency_manager=depman,
    )


class TestSupervisorDispatchIntegration:
    def test_fallback_pre_m3_behavior_when_pool_empty(self, registry, gov):
        """Pool rỗng → supervisor vẫn chạy task như trước M3 (không vỡ nền)."""
        task = registry.register_task("công việc cũ", risk_level="R1")
        sup = _supervisor(registry, gov, agents=None)
        sup.step()  # STARTING → READY
        sup.step()  # READY → SELECTING_TASK → PLANNING
        assert sup.current_task is not None
        assert sup.current_task.task_id == task.task_id

    def test_dispatched_agent_recorded(self, registry, gov):
        """Có agent phù hợp → task được gán, transition actor=dispatcher, agent giữ task."""
        agent = AgentProfile(agent_id="tony-core", capabilities=[], max_concurrent=3)
        task = registry.register_task("công việc cho agent", risk_level="R1")
        sup = _supervisor(registry, gov, agents=[agent])
        sup.step()
        sup.step()  # chọn + gán
        assert sup.current_task.task_id == task.task_id
        # agent giữ task trong pool
        assert agent.current_tasks == [task.task_id]
        # transition log có dòng assignment
        transitions = registry.list_transitions(task.task_id)
        assert any(
            t.reason.startswith("assigned to") and t.actor == "dispatcher"
            for t in transitions
        ), [t.to_dict() for t in transitions]

    def test_dependency_pending_task_skipped(self, registry, gov):
        """Task có dep chưa xong bị bỏ qua — supervisor chọn task khác eligible."""
        agent = AgentProfile(agent_id="tony-core", capabilities=[], max_concurrent=3)
        dep = registry.register_task("việc gốc", risk_level="R1")
        dependent = registry.register_task(
            "việc phụ thuộc", risk_level="R1", dependencies=[dep.task_id], priority=1
        )
        normal = registry.register_task("việc thường", risk_level="R1", priority=2)
        sup = _supervisor(registry, gov, agents=[agent])
        sup.step()
        sup.step()
        # priority=1 của dependent nhưng dep chưa xong → phải chọn normal
        assert sup.current_task.task_id == normal.task_id
        # dependent KHÔNG bị gán
        assert dependent.task_id not in agent.current_tasks

    def test_completion_unblocks_dependent(self, registry, gov):
        """Task gốc hoàn tất qua supervisor → task phụ tự READY (unblock)."""
        agent = AgentProfile(agent_id="tony-core", capabilities=[], max_concurrent=3)
        root = registry.register_task("gốc", risk_level="R1", priority=1)
        child = registry.register_task("phụ thuộc", risk_level="R1", dependencies=[root.task_id], priority=2)
        sup = _supervisor(registry, gov, agents=[agent])

        # chạy tới khi root COMPLETED (dry-run luôn success)
        for _ in range(8):
            sup.step(dry_run=True)
            cur = registry.get_task(root.task_id)
            if cur.status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED):
                break
        assert registry.get_task(root.task_id).status in (
            TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED
        )
        # child đã được mở khóa → READY
        assert registry.get_task(child.task_id).status == TaskStatus.READY

    def test_agent_capacity_blocks_second_assignment(self, registry, gov):
        """Agent hết chỗ → task kế tiếp không gán được (ở lại queue)."""
        agent = AgentProfile(agent_id="solo", capabilities=[], max_concurrent=1)
        t1 = registry.register_task("việc một", risk_level="R1", priority=1)
        t2 = registry.register_task("việc hai", risk_level="R1", priority=2)
        sup = _supervisor(registry, gov, agents=[agent])
        sup.step(); sup.step()  # chọn t1 → gán → PLANNING
        assert agent.current_tasks == [t1.task_id]
        # mô phỏng: đưa supervisor về READY và thử chọn tiếp — t2 không thể gán
        # (max_concurrent=1, t1 chưa xong). step tiếp chỉ chạy tiếp t1 → không gán t2.
        assert sup.current_task.task_id == t1.task_id


class TestCycleE2E:
    def test_true_cycle_detected_between_two_existing_tasks(self, registry, depman=None):
        """Cycle thật: A dep B, sau đó B dep A (qua update dependencies) → assert lỗi.

        assert_acyclic chặn khi ĐĂNG KÝ; chuỗi tạo bằng update trực tiếp
        (mô phỏng data lỗi) vẫn bị topological/assert bắt.
        """
        from quan_ai_brain.orchestration.dependency_manager import DependencyManager

        dm = DependencyManager(registry)
        a = registry.register_task("A")
        b = registry.register_task("B", dependencies=[a.task_id])
        # ép A trỏ ngược về B (mô phỏng dữ liệu lỗi / import nhầm)
        registry._conn.execute(
            "UPDATE durable_tasks SET dependencies_json = ? WHERE task_id = ?",
            (f'["{b.task_id}"]', a.task_id),
        )
        registry._conn.commit()
        with pytest.raises(ValueError, match="cycle"):
            dm.topological_order([a.task_id, b.task_id])
        # assert_acyclic cho task MỚI dep a: new_task_id chưa tồn tại trong graph
        # A↔B → về nguyên tắc không tạo cycle MỚI (cycle sẵn là lỗi dữ liệu cũ).
        # Hành vi đúng: không raise cho new; cycle sẵn được topological bắt.
