"""Unit tests for Windows Process Containment Contract and Inert Runner."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.execution.process_containment import (
    JOB_OBJECT_LIMIT_JOB_MEMORY,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    ContainmentConfigurationError,
    ContainedExecutionRunner,
    InertProcessBackend,
    ProcessBackendInterface,
    ProcessContainmentConfig,
)
from quan_ai_brain.execution.resource_budget import NetworkPolicy, ResourceBudget
from quan_ai_brain.execution.staging import ProductionExecutionProhibitedError
from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate


class FakeProcessBackend:
    """Mock backend tracking calls without invoking OS subprocesses."""

    def __init__(self, should_fail_config: bool = False) -> None:
        self.should_fail_config = should_fail_config
        self.configured_jobs: list[ProcessContainmentConfig] = []
        self.spawn_calls: list[dict] = []

    def is_available(self) -> bool:
        return True

    def configure_containment(self, config: ProcessContainmentConfig) -> dict[str, str]:
        if self.should_fail_config:
            raise RuntimeError("OS kernel rejected Job Object creation")
        self.configured_jobs.append(config)
        return {"handle": f"fake_handle_{config.job_name}"}

    def spawn_process(self, command: list[str], containment_handle: str, cwd: Path, env: dict) -> None:
        self.spawn_calls.append({"cmd": command, "handle": containment_handle})


def test_containment_config_mapping_from_budget():
    """Verify accurate translation of ResourceBudget into ProcessContainmentConfig."""
    budget = ResourceBudget(
        max_runtime_seconds=45.0,
        max_memory_mb=1024,
        max_cpu_time_seconds=15.0,
        max_child_processes=0,
        network_policy=NetworkPolicy.BLOCKED,
    )
    cfg = ProcessContainmentConfig.from_budget(budget, job_id_prefix="test_job")

    assert cfg.job_name.startswith("test_job_")
    assert cfg.max_memory_bytes == 1024 * 1024 * 1024
    assert cfg.max_cpu_time_ms == 15000
    assert cfg.max_active_processes == 1
    assert cfg.kill_on_job_close is True
    assert cfg.breakaway_prohibited is True
    assert cfg.network_isolated is True
    assert cfg.is_os_enforced is False
    assert cfg.limit_flags_bitmask & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE != 0
    assert cfg.limit_flags_bitmask & JOB_OBJECT_LIMIT_JOB_MEMORY != 0


def test_inert_backend_zero_process_spawning():
    """Verify InertProcessBackend strictly refuses OS process spawning."""
    backend = InertProcessBackend()
    assert backend.is_inert is True
    assert backend.supports_production is False

    config = ProcessContainmentConfig(
        job_name="inert_test",
        max_memory_bytes=512 * 1024 * 1024,
        max_cpu_time_ms=5000,
        max_active_processes=1,
    )
    handle = backend.configure_containment(config)
    assert handle["status"] == "CONFIGURED_INERT"

    with pytest.raises(ProductionExecutionProhibitedError) as exc_info:
        backend.spawn_process(["whoami"], handle, Path("."), {})
    assert "InertProcessBackend cannot launch OS processes" in str(exc_info.value)


def test_runner_refuses_r5_unconditionally(tmp_path: Path):
    """Verify ContainedExecutionRunner hard-blocks R5 actions."""
    runner = ContainedExecutionRunner(workspace=tmp_path)
    res = runner.prepare_and_stage(
        command=["rm", "-rf", "/"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R5,
    )
    assert res["status"] == "BLOCKED"
    assert res["success"] is False
    assert "R5 is prohibited" in res["reason"]


def test_runner_requires_owner_approval_for_r4(tmp_path: Path):
    """Verify ContainedExecutionRunner denies unapproved R4 actions when approval_id is missing."""
    runner = ContainedExecutionRunner(workspace=tmp_path)
    res = runner.prepare_and_stage(
        command=["reconfigure_system"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R4,
        approval_id=None,
    )
    assert res["status"] == "DENIED"
    assert res["success"] is False
    assert "no approval_id provided" in res["reason"]


def test_runner_verifies_valid_approval_for_r4(tmp_path: Path):
    """Verify runner permits R4 staging when a valid ApprovalGate approval is provided."""
    gate = ApprovalGate()
    req = gate.create_request("sys_admin", "execute", {"command": ["sys_admin"]}, "workspace", RiskLevel.R4)
    appr = gate.grant_approval(req, "owner")

    runner = ContainedExecutionRunner(workspace=tmp_path, approval_gate=gate)
    res = runner.prepare_and_stage(
        command=["sys_admin"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R4,
        approval_id=appr.approval_id,
    )
    assert res["status"] == "STAGED_INERT"
    assert res["success"] is True


def test_runner_fails_on_invalid_approval_for_r4(tmp_path: Path):
    """Verify runner fails closed when an invalid or mismatched approval_id is supplied."""
    gate = ApprovalGate()
    runner = ContainedExecutionRunner(workspace=tmp_path, approval_gate=gate)
    res = runner.prepare_and_stage(
        command=["sys_admin"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R4,
        approval_id="non_existent_approval_id",
    )
    assert res["status"] == "DENIED"
    assert res["success"] is False
    assert "owner approval invalid" in res["reason"]


def test_runner_emergency_stop_halts_execution(tmp_path: Path):
    """Verify persistent emergency STOP blocks execution runner."""
    db_path = tmp_path / "gov.db"
    store = GovernanceStateStore(db_path, workspace=tmp_path)
    store.set_emergency_state("stop", reason="Security incident active")

    runner = ContainedExecutionRunner(workspace=tmp_path, store=store)
    res = runner.prepare_and_stage(
        command=["dir"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R0,
    )
    assert res["status"] == "BLOCKED"
    assert "STOP" in res["reason"]

    store.close()


def test_runner_fails_closed_on_budget_violation(tmp_path: Path):
    """Verify invalid resource budgets are rejected before configuring containment."""
    fake_backend = FakeProcessBackend()
    runner = ContainedExecutionRunner(workspace=tmp_path, backend=fake_backend)

    invalid_budget = ResourceBudget(max_runtime_seconds=-10.0)
    res = runner.prepare_and_stage(
        command=["dir"],
        budget=invalid_budget,
        risk_level=RiskLevel.R0,
    )
    assert res["status"] == "DENIED"
    assert "budget validation failed" in res["reason"]
    # Backend must NEVER have been called
    assert len(fake_backend.configured_jobs) == 0


def test_runner_fails_closed_on_containment_configuration_error(tmp_path: Path):
    """Verify runner raises ContainmentConfigurationError when OS containment fails."""
    failing_backend = FakeProcessBackend(should_fail_config=True)
    runner = ContainedExecutionRunner(workspace=tmp_path, backend=failing_backend)

    with pytest.raises(ContainmentConfigurationError) as exc_info:
        runner.prepare_and_stage(
            command=["dir"],
            budget=ResourceBudget(),
            risk_level=RiskLevel.R0,
        )
    assert "OS kernel rejected" in str(exc_info.value)


def test_runner_inert_staging_success(tmp_path: Path):
    """Verify successful inert staging with valid budget and mock backend."""
    fake_backend = FakeProcessBackend()
    runner = ContainedExecutionRunner(workspace=tmp_path, backend=fake_backend)

    budget = ResourceBudget(max_runtime_seconds=20.0, max_memory_mb=256)
    res = runner.prepare_and_stage(
        command=["dir_list"],
        budget=budget,
        risk_level=RiskLevel.R0,
    )
    assert res["status"] == "STAGED_INERT"
    assert res["success"] is True
    assert len(fake_backend.configured_jobs) == 1
    # Zero real processes spawned
    assert len(fake_backend.spawn_calls) == 0
    assert "[INERT STAGING - ZERO PROCESS SPAWNED]" in res["notice"]


def test_runner_is_inert_property_invariant(tmp_path: Path):
    """Verify runner maintains immutable is_inert=True property."""
    runner = ContainedExecutionRunner(workspace=tmp_path)
    assert runner.is_inert is True
