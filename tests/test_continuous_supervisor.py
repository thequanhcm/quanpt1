"""Unit tests for ContinuousAutonomySupervisor in QUAN AI BRAIN."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.learning.periodic_reporter import PeriodicLearningReporter
from quan_ai_brain.llm import FallbackMode, LLMProvider
from quan_ai_brain.orchestration.models import (
    AutonomyLevel,
    SupervisorState,
    TaskStatus,
)
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.coordinator import ExecutiveCoordinator


@pytest.fixture
def supervisor_env(tmp_path: Path):
    registry = DurableTaskRegistry(":memory:", workspace=tmp_path)
    gov_store = GovernanceStateStore(db_path=":memory:", workspace=tmp_path)
    llm = LLMProvider(fallback_mode=FallbackMode.ALWAYS_MOCK)
    coordinator = ExecutiveCoordinator(workspace=tmp_path, llm_provider=llm)
    reporter = PeriodicLearningReporter(workspace=tmp_path, db_path=":memory:")

    sup = ContinuousAutonomySupervisor(
        workspace=tmp_path,
        task_registry=registry,
        governance_store=gov_store,
        coordinator=coordinator,
        learning_reporter=reporter,
    )
    return sup, registry, gov_store


def test_supervisor_initialization_transitions_to_ready(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    assert sup.state == SupervisorState.STARTING

    sup.initialize()
    assert sup.state == SupervisorState.READY
    history = [h["to"] for h in sup.cycle_history]
    assert SupervisorState.HEALTH_CHECK.value in history
    assert SupervisorState.RECOVERING.value in history
    assert SupervisorState.READY.value in history


def test_supervisor_emergency_stop_halts_to_stopped(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    gov_store.set_emergency_state("stop", reason="Khẩn cấp: Tạm dừng toàn hệ thống", activated_by="owner")

    sup.step()
    assert sup.state == SupervisorState.STOPPED

    # Step again remains stopped
    sup.step()
    assert sup.state == SupervisorState.STOPPED


def test_supervisor_emergency_freeze_halts_to_safe_mode(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    gov_store.set_emergency_state("freeze", reason="Đóng băng kiểm tra an toàn", activated_by="owner")

    sup.step()
    assert sup.state == SupervisorState.SAFE_MODE


def test_supervisor_idle_when_no_pending_tasks(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    sup.initialize()

    state = sup.step()
    assert state == SupervisorState.IDLE
    assert sup.current_task is None


def test_supervisor_level_a_task_full_cycle_to_completed(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    sup.initialize()

    # Register safe read task
    task = registry.register_task(
        goal="Đọc cấu hình hệ thống và kiểm tra tài nguyên",
        risk_level="R0",
        autonomy_level=AutonomyLevel.LEVEL_A,
    )

    # 1. Step: SELECTING_TASK -> PLANNING
    sup.step(dry_run=True)
    assert sup.state == SupervisorState.PLANNING
    assert sup.current_task.task_id == task.task_id

    # 2. Step: PLANNING -> RUNNING_AUTHORIZED_TASK
    sup.step(dry_run=True)
    assert sup.state == SupervisorState.RUNNING_AUTHORIZED_TASK

    # 3. Step: RUNNING_AUTHORIZED_TASK -> VERIFYING_RESULT -> READY (Completed)
    sup.step(dry_run=True)
    assert sup.state == SupervisorState.READY

    # Verify task in registry is COMPLETED
    updated = registry.get_task(task.task_id)
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result_payload["mode"] == "dry_run"
    assert "evidence:verified_safe_run" in updated.evidence_refs


def test_supervisor_high_risk_task_stops_at_waiting_for_approval(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    sup.initialize()

    # Register high-risk deploy task (triggers R4 keyword)
    task = registry.register_task(
        goal="deploy new production version to cluster",
        risk_level="R4",
        autonomy_level=AutonomyLevel.LEVEL_D,
    )

    sup.step(dry_run=True)  # -> PLANNING
    assert sup.state == SupervisorState.PLANNING

    sup.step(dry_run=True)  # -> WAITING_FOR_APPROVAL
    assert sup.state == SupervisorState.WAITING_FOR_APPROVAL

    updated = registry.get_task(task.task_id)
    assert updated.status == TaskStatus.WAITING_APPROVAL


def test_supervisor_level_b_task_stops_at_waiting_for_approval(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    sup.initialize()

    # Level B requires explicit staging test authorization
    task = registry.register_task(
        goal="Chạy thử nghiệm kiểm thử cô lập",
        risk_level="R1",
        autonomy_level=AutonomyLevel.LEVEL_B,
    )

    sup.step(dry_run=True)
    sup.step(dry_run=True)
    assert sup.state == SupervisorState.WAITING_FOR_APPROVAL


def test_supervisor_recovers_in_flight_tasks_on_init(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    t1 = registry.register_task("Task bị treo")
    registry.update_task_status(t1.task_id, TaskStatus.IN_PROGRESS)

    sup.initialize()
    assert sup.state == SupervisorState.READY

    recovered = registry.get_task(t1.task_id)
    assert recovered.status == TaskStatus.OUTCOME_UNKNOWN


def test_supervisor_run_cycles_bounded(supervisor_env) -> None:
    sup, registry, gov_store = supervisor_env
    # Empty queue should initialize and quickly halt at IDLE
    history = sup.run_cycles(max_cycles=10, dry_run=True)
    assert sup.state == SupervisorState.IDLE
    assert len(history) >= 2
