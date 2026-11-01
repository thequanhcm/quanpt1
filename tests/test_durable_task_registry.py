"""Unit tests for DurableTaskRegistry in QUAN AI BRAIN."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.orchestration.models import AutonomyLevel, TaskRecord, TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


def test_init_memory_schema() -> None:
    registry = DurableTaskRegistry(":memory:")
    tasks = registry.list_tasks()
    assert tasks == []


def test_register_task_defaults_and_fields(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"
    registry = DurableTaskRegistry(db_file, workspace=tmp_path)

    record = registry.register_task(
        goal="Tra cứu thông tin kiến trúc hệ thống",
        risk_level="R0",
        autonomy_level=AutonomyLevel.LEVEL_A,
        acceptance_criteria=["Tìm thấy file ARCHITECTURE.md"],
    )

    assert record.task_id.startswith("task_")
    assert record.goal == "Tra cứu thông tin kiến trúc hệ thống"
    assert record.risk_level == "R0"
    assert record.autonomy_level == AutonomyLevel.LEVEL_A
    assert record.status == TaskStatus.PENDING
    assert record.acceptance_criteria == ["Tìm thấy file ARCHITECTURE.md"]
    assert record.completed_at_utc is None

    # Fetch from db
    fetched = registry.get_task(record.task_id)
    assert fetched is not None
    assert fetched.task_id == record.task_id
    assert fetched.goal == record.goal


def test_idempotency_key_prevents_duplicate_registration(tmp_path: Path) -> None:
    registry = DurableTaskRegistry(":memory:")
    key = "idem_test_unique_123"

    first = registry.register_task("Mục tiêu lần đầu", idempotency_key=key)
    second = registry.register_task("Mục tiêu lần hai (trùng key)", idempotency_key=key)

    assert first.task_id == second.task_id
    assert second.goal == "Mục tiêu lần đầu"
    all_tasks = registry.list_tasks()
    assert len(all_tasks) == 1


def test_update_task_status_atomic_transitions(tmp_path: Path) -> None:
    registry = DurableTaskRegistry(":memory:")
    task = registry.register_task("Xác minh chỉ mục SQLite", risk_level="R1")

    # Update to IN_PROGRESS
    running = registry.update_task_status(
        task.task_id,
        TaskStatus.IN_PROGRESS,
        checkpoint_data={"step": 1, "note": "Scanning database"},
    )
    assert running.status == TaskStatus.IN_PROGRESS
    assert running.checkpoint_data["step"] == 1

    # Update to COMPLETED
    completed = registry.update_task_status(
        task.task_id,
        TaskStatus.COMPLETED,
        result_payload={"found": True, "latency_ms": 5.2},
        evidence_ref="evidence:sqlite_index_check",
    )
    assert completed.status == TaskStatus.COMPLETED
    assert completed.completed_at_utc is not None
    assert completed.result_payload["latency_ms"] == 5.2
    assert "evidence:sqlite_index_check" in completed.evidence_refs


def test_list_tasks_by_status(tmp_path: Path) -> None:
    registry = DurableTaskRegistry(":memory:")
    t1 = registry.register_task("Task 1")
    t2 = registry.register_task("Task 2")
    registry.update_task_status(t2.task_id, TaskStatus.COMPLETED)

    pending_list = registry.list_tasks(status=TaskStatus.PENDING)
    assert len(pending_list) == 1
    assert pending_list[0].task_id == t1.task_id

    completed_list = registry.list_tasks(status=TaskStatus.COMPLETED)
    assert len(completed_list) == 1
    assert completed_list[0].task_id == t2.task_id


def test_recover_in_flight_tasks_transitions_to_outcome_unknown() -> None:
    registry = DurableTaskRegistry(":memory:")
    t1 = registry.register_task("Task đang dở 1")
    t2 = registry.register_task("Task đã xong")
    t3 = registry.register_task("Task đang dở 2")

    registry.update_task_status(t1.task_id, TaskStatus.IN_PROGRESS)
    registry.update_task_status(t2.task_id, TaskStatus.COMPLETED)
    registry.update_task_status(t3.task_id, TaskStatus.IN_PROGRESS)

    recovered = registry.recover_in_flight_tasks()
    assert len(recovered) == 2
    recovered_ids = {r.task_id for r in recovered}
    assert recovered_ids == {t1.task_id, t3.task_id}

    for r in recovered:
        assert r.status == TaskStatus.OUTCOME_UNKNOWN
        assert "recovery_note" in r.checkpoint_data

    # Verify that in-progress tasks are now 0
    assert len(registry.list_tasks(status=TaskStatus.IN_PROGRESS)) == 0


def test_redaction_in_task_goal() -> None:
    registry = DurableTaskRegistry(":memory:")
    secret_text = "Kiểm tra kết nối với api_key: secret_xyz_123456"
    record = registry.register_task(secret_text)
    assert "secret_xyz_123456" not in record.goal
    assert "[REDACTED]" in record.goal


def test_non_existent_task_update_raises_key_error() -> None:
    registry = DurableTaskRegistry(":memory:")
    with pytest.raises(KeyError, match="not found"):
        registry.update_task_status("task_non_existent_999", TaskStatus.COMPLETED)
