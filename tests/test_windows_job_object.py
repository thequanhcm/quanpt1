"""Unit and Integration Tests for Windows Job Object Containment Backend.

Sprint 7B: Windows Job Object Kernel Integration & Subprocess Spawner.
Verifies kernel-level limits, accounting queries, PathGuard boundaries,
R5 command screening, fail-closed staging defaults, and runner integration.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import pytest

from quan_ai_brain.execution.process_containment import (
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS,
    JOB_OBJECT_LIMIT_JOB_MEMORY,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOB_OBJECT_LIMIT_PROCESS_TIME,
    ContainedExecutionRunner,
    ProcessContainmentConfig,
)
from quan_ai_brain.execution.resource_budget import NetworkPolicy, ResourceBudget
from quan_ai_brain.execution.staging import ProductionExecutionProhibitedError
from quan_ai_brain.execution.windows_job_object import (
    IS_WINDOWS,
    JobExecutionResult,
    ProcessAssignmentError,
    WindowsJobObjectBackend,
)
from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.path_guard import PathOutsideWorkspaceError


# ---------------------------------------------------------------------------
# Basic OS Availability & Handle Lifecycle
# ---------------------------------------------------------------------------
def test_windows_job_object_availability():
    """Verify backend accurately detects Windows host and kernel32 availability."""
    backend = WindowsJobObjectBackend()
    if IS_WINDOWS:
        assert backend.is_available() is True
    else:
        assert backend.is_available() is False


@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows NT host with Job Object support")
def test_configure_containment_creates_real_job_object():
    """Verify configure_containment creates a genuine Win32 Job Object with correct flags."""
    backend = WindowsJobObjectBackend()
    config = ProcessContainmentConfig(
        job_name="test_containment_job_1",
        max_memory_bytes=256 * 1024 * 1024,
        max_cpu_time_ms=5000,
        max_active_processes=2,
        kill_on_job_close=True,
    )

    handle_dict = backend.configure_containment(config)
    assert handle_dict["job_name"] == "test_containment_job_1"
    assert handle_dict["status"] == "CONFIGURED_OS"
    assert handle_dict["is_os_enforced"] is True
    assert handle_dict["handle"] is not None
    assert handle_dict["handle"] != 0

    applied = handle_dict["limits_applied"]
    assert applied["memory_bytes"] == 256 * 1024 * 1024
    assert applied["cpu_time_ms"] == 5000
    assert applied["active_processes"] == 2
    assert applied["kill_on_job_close"] is True
    assert applied["limit_flags"] & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE != 0
    assert applied["limit_flags"] & JOB_OBJECT_LIMIT_JOB_MEMORY != 0
    assert applied["limit_flags"] & JOB_OBJECT_LIMIT_PROCESS_TIME != 0
    assert applied["limit_flags"] & JOB_OBJECT_LIMIT_ACTIVE_PROCESS != 0

    # Cleanup
    assert backend.close_containment("test_containment_job_1") is True


# ---------------------------------------------------------------------------
# Fail-Closed Staging Gate
# ---------------------------------------------------------------------------
def test_default_fail_closed_inert_mode():
    """Verify WindowsJobObjectBackend defaults to fail-closed staging mode."""
    backend = WindowsJobObjectBackend()
    assert backend.allow_live_processes is False

    config = ProcessContainmentConfig(
        job_name="fail_closed_job",
        max_memory_bytes=128 * 1024 * 1024,
        max_cpu_time_ms=1000,
        max_active_processes=1,
    )
    if backend.is_available():
        h = backend.configure_containment(config)
    else:
        h = {"job_name": "fail_closed_job", "handle": 123}

    with pytest.raises(ProductionExecutionProhibitedError) as exc_info:
        backend.spawn_process([sys.executable, "-c", "print(1)"], h)

    assert "Fail-Closed Staging mode" in str(exc_info.value)
    if backend.is_available():
        backend.close_containment("fail_closed_job")


# ---------------------------------------------------------------------------
# Controlled Live Process Spawning & Accounting Telemetry
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows NT host with Job Object support")
def test_spawn_process_in_sandboxed_job(tmp_path: Path):
    """Verify safe process execution inside a Win32 Job Object with telemetry."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    config = ProcessContainmentConfig(
        job_name="live_sandbox_job_1",
        max_memory_bytes=256 * 1024 * 1024,
        max_cpu_time_ms=5000,
        max_active_processes=2,
    )

    handle_dict = backend.configure_containment(config)

    # Run safe python command printing deterministic token
    command = [sys.executable, "-c", "import sys; sys.stdout.write('job_sandbox_verified')"]
    result = backend.spawn_process(command, handle_dict, cwd=tmp_path)

    assert isinstance(result, JobExecutionResult)
    assert result.success is True
    assert result.returncode == 0
    assert "job_sandbox_verified" in result.stdout
    assert result.stderr == ""
    assert result.job_name == "live_sandbox_job_1"
    assert result.total_processes >= 1
    assert result.is_inert is False

    backend.close_containment("live_sandbox_job_1")


@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows NT host with Job Object support")
def test_accounting_query_telemetry(tmp_path: Path):
    """Verify kernel accounting telemetry tracks processes and CPU time."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    config = ProcessContainmentConfig(
        job_name="telemetry_job_1",
        max_memory_bytes=256 * 1024 * 1024,
        max_cpu_time_ms=5000,
        max_active_processes=1,
    )
    handle_dict = backend.configure_containment(config)

    # Spawn short computation to accumulate CPU time
    cmd = [sys.executable, "-c", "sum(i*i for i in range(100000))"]
    result = backend.spawn_process(cmd, handle_dict, cwd=tmp_path)

    assert result.success is True
    acct = backend.query_accounting(handle_dict)
    assert acct["total_processes"] >= 1
    assert "user_time_ms" in acct
    assert "kernel_time_ms" in acct
    assert acct["user_time_ms"] >= 0.0

    backend.close_containment("telemetry_job_1")


# ---------------------------------------------------------------------------
# Destructive R5 Command Screening & Boundary Validation
# ---------------------------------------------------------------------------
def test_prohibited_r5_commands_blocked(tmp_path: Path):
    """Verify destructive commands are rejected before any OS process is created."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    h = {"job_name": "r5_block_job", "handle": 999}

    forbidden_commands = [
        ["rm", "-rf", "/"],
        ["rm", "-r", "logs"],
        ["del", "/s", "data"],
        ["del", "/f", "config.json"],
        ["rmdir", "/s", "build"],
        ["format", "D:"],
        ["diskpart"],
        ["reg", "delete", "HKCU\\Software"],
    ]

    for cmd in forbidden_commands:
        with pytest.raises(ValueError) as exc_info:
            backend.spawn_process(cmd, h, cwd=tmp_path)
        assert "Prohibited destructive command pattern" in str(exc_info.value)


def test_empty_command_rejected(tmp_path: Path):
    """Verify empty command argument list is rejected."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    with pytest.raises(ValueError) as exc_info:
        backend.spawn_process([], {"job_name": "empty_cmd"}, cwd=tmp_path)
    assert "non-empty list" in str(exc_info.value)


def test_path_guard_enforcement(tmp_path: Path):
    """Verify PathGuard blocks cwd pointing outside designated workspace."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    outside_dir = tmp_path / "outside_forbidden"
    outside_dir.mkdir()

    backend = WindowsJobObjectBackend(workspace=workspace_dir, allow_live_processes=True)
    h = {"job_name": "path_guard_job", "handle": 123}

    with pytest.raises(PathOutsideWorkspaceError):
        backend.spawn_process([sys.executable, "-c", "pass"], h, cwd=outside_dir)


# ---------------------------------------------------------------------------
# Handle Cleanup & Context Manager
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows NT host with Job Object support")
def test_context_manager_auto_cleanup():
    """Verify context manager automatically closes active handles on exit."""
    with WindowsJobObjectBackend() as backend:
        cfg = ProcessContainmentConfig(
            job_name="cm_cleanup_job",
            max_memory_bytes=64 * 1024 * 1024,
            max_cpu_time_ms=1000,
            max_active_processes=1,
        )
        backend.configure_containment(cfg)
        assert "cm_cleanup_job" in backend._active_jobs

    assert len(backend._active_jobs) == 0


# ---------------------------------------------------------------------------
# ContainedExecutionRunner Integration
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows NT host with Job Object support")
def test_contained_runner_with_windows_job_backend(tmp_path: Path):
    """Verify ContainedExecutionRunner stages real Win32 Job Object in fail-closed mode."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=False)
    runner = ContainedExecutionRunner(workspace=tmp_path, backend=backend)

    budget = ResourceBudget(
        max_runtime_seconds=10.0,
        max_memory_mb=128,
        max_cpu_time_seconds=2.0,
        max_child_processes=0,
        network_policy=NetworkPolicy.BLOCKED,
    )

    staging_res = runner.prepare_and_stage(
        command=[sys.executable, "-c", "print('inert')"],
        budget=budget,
        risk_level=RiskLevel.R1,
    )

    assert staging_res["status"] == "STAGED_INERT"
    assert staging_res["success"] is True
    handle = staging_res["containment_handle"]
    assert handle["status"] == "CONFIGURED_OS"
    assert handle["is_os_enforced"] is True

    # Attempting execute_contained in fail-closed mode must raise ProductionExecutionProhibitedError
    with pytest.raises(ProductionExecutionProhibitedError):
        runner.execute_contained(
            command=[sys.executable, "-c", "print('inert')"],
            budget=budget,
            risk_level=RiskLevel.R1,
        )

    backend.close_all()


@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows NT host with Job Object support")
def test_contained_runner_live_execution_in_authorized_test(tmp_path: Path):
    """Verify ContainedExecutionRunner dispatches safe process under live test authorization."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    runner = ContainedExecutionRunner(workspace=tmp_path, backend=backend)

    budget = ResourceBudget(
        max_runtime_seconds=10.0,
        max_memory_mb=128,
        max_cpu_time_seconds=2.0,
        max_child_processes=0,
        network_policy=NetworkPolicy.BLOCKED,
    )

    result = runner.execute_contained(
        command=[sys.executable, "-c", "import sys; sys.stdout.write('runner_sandbox_pass')"],
        budget=budget,
        risk_level=RiskLevel.R1,
        cwd=tmp_path,
    )

    assert isinstance(result, JobExecutionResult)
    assert result.success is True
    assert result.returncode == 0
    assert "runner_sandbox_pass" in result.stdout
    assert result.total_processes >= 1

    backend.close_all()


def test_contained_runner_governance_emergency_stop(tmp_path: Path):
    """Verify ContainedExecutionRunner immediately halts when emergency STOP is set."""
    db_path = tmp_path / "gov.db"
    store = GovernanceStateStore(db_path, workspace=tmp_path)
    store.set_emergency_state("stop", "Test emergency halt", "owner")

    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    runner = ContainedExecutionRunner(workspace=tmp_path, store=store, backend=backend)

    res = runner.execute_contained(
        command=[sys.executable, "-c", "print(1)"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R1,
    )

    assert res["status"] == "BLOCKED"
    assert res["success"] is False
    assert "STOP" in res["reason"]


def test_contained_runner_governance_r5_hard_blocked(tmp_path: Path):
    """Verify ContainedExecutionRunner permanently blocks R5 actions."""
    backend = WindowsJobObjectBackend(workspace=tmp_path, allow_live_processes=True)
    runner = ContainedExecutionRunner(workspace=tmp_path, backend=backend)

    res = runner.execute_contained(
        command=["rm", "-rf", "/"],
        budget=ResourceBudget(),
        risk_level=RiskLevel.R5,
    )

    assert res["status"] == "BLOCKED"
    assert res["success"] is False
    assert "R5 is prohibited" in res["reason"]


def test_secret_redaction_in_job_execution_result():
    """Verify JobExecutionResult to_dict redacts credentials from output."""
    raw_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token123"
    result = JobExecutionResult(
        success=True,
        returncode=0,
        stdout=f"Auth header: {raw_token}",
        stderr="No errors",
        job_name="test_redact_job",
    )

    res_dict = result.to_dict()
    assert raw_token not in res_dict["stdout"]
    assert "[REDACTED]" in res_dict["stdout"]
