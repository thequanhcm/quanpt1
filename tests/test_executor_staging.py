"""Tests for IsolatedStagingExecutor and Sprint 5 Design Sign-Off."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.execution.staging import (
    ExecutionStageRequest,
    ExecutionStageResult,
    IsolatedStagingExecutor,
    StageStatus,
)
from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate
from quan_ai_brain.tools.delegation import DelegationGrant, DelegationRegistry


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "staging_ws"
    ws.mkdir()
    return ws


def test_executor_is_strictly_inert_and_no_production(workspace: Path):
    """Verify that IsolatedStagingExecutor is inert and permanently refuses production execution."""
    executor = IsolatedStagingExecutor(workspace=workspace)
    assert executor.is_inert is True
    assert executor.supports_production is False

    with pytest.raises(PermissionError) as exc_info:
        executor.execute_production({"action": "do_something"})
    assert "strictly disabled" in str(exc_info.value)
    assert "PENDING_OWNER_SIGNOFF" in str(exc_info.value)


def test_staging_simulation_does_not_modify_filesystem(workspace: Path):
    """Verify dry-run simulation never writes real files to the workspace."""
    store = GovernanceStateStore(":memory:")
    gate = ApprovalGate(store=store)
    executor = IsolatedStagingExecutor(workspace=workspace, approval_gate=gate, store=store)

    req_data = gate.create_request(
        tool_id="file_write_new",
        action="write",
        params={"file_path": "should_never_exist.txt", "content": "secret data"},
        resource_scope="workspace",
        risk_level=RiskLevel.R2,
    )
    app = gate.grant_approval(req_data, approver="owner_quan")

    stage_req = ExecutionStageRequest(
        tool_id="file_write_new",
        action="write",
        params={"file_path": "should_never_exist.txt", "content": "secret data"},
        risk_level=RiskLevel.R2,
        approval_id=app.approval_id,
    )

    res: ExecutionStageResult = executor.stage_and_simulate(stage_req)
    assert res.success is True
    assert res.status == StageStatus.SIMULATED
    assert res.is_inert is True
    assert "[INERT STAGING" in res.notice

    # Crucial assertion: real file MUST NOT have been created!
    target = workspace / "should_never_exist.txt"
    assert not target.exists()

    store.close()


def test_staging_blocked_by_emergency_stop(workspace: Path):
    """Verify that persistent emergency STOP blocks staging execution."""
    db_path = workspace / "gov.db"
    store = GovernanceStateStore(db_path, workspace=workspace)
    store.set_emergency_state("stop", reason="Security incident", activated_by="OWNER")

    executor = IsolatedStagingExecutor(workspace=workspace, store=store)
    stage_req = ExecutionStageRequest(
        tool_id="dir_list",
        action="read",
        params={},
        risk_level=RiskLevel.R0,
    )

    res = executor.stage_and_simulate(stage_req)
    assert res.success is False
    assert res.status == StageStatus.BLOCKED
    assert "STOP" in (res.error or "")

    store.close()


def test_staging_denies_r5_unconditionally(workspace: Path):
    """Verify R5 dangerous actions are unconditionally hard-blocked by PolicyEngine."""
    executor = IsolatedStagingExecutor(workspace=workspace)
    stage_req = ExecutionStageRequest(
        tool_id="arbitrary_cmd",
        action="exec_shell",
        params={"cmd": "format c:"},
        risk_level=RiskLevel.R5,
    )

    res = executor.stage_and_simulate(stage_req)
    assert res.success is False
    assert res.status == StageStatus.BLOCKED
    assert "hard-blocked" in (res.error or "")


def test_staging_denies_unapproved_action(workspace: Path):
    """Verify actions lacking both approval and delegation are denied."""
    executor = IsolatedStagingExecutor(workspace=workspace)
    stage_req = ExecutionStageRequest(
        tool_id="file_read",
        action="read",
        params={"file_path": "confidential.txt"},
        risk_level=RiskLevel.R0,
    )

    res = executor.stage_and_simulate(stage_req)
    assert res.success is False
    assert res.status == StageStatus.DENIED
    assert "requires explicit owner approval" in (res.error or "")


def test_staging_with_resource_budget_validation_success(workspace: Path):
    """Verify staging request with valid ResourceBudget validates and simulates cleanly."""
    from quan_ai_brain.execution.resource_budget import ResourceBudget

    store = GovernanceStateStore(":memory:")
    gate = ApprovalGate(store=store)
    executor = IsolatedStagingExecutor(workspace=workspace, approval_gate=gate, store=store)

    req_data = gate.create_request(
        tool_id="dir_list",
        action="read",
        params={},
        resource_scope="workspace",
        risk_level=RiskLevel.R0,
    )
    app = gate.grant_approval(req_data, approver="owner_quan")

    budget = ResourceBudget(max_runtime_seconds=15.0, max_memory_mb=256, max_tool_calls=1)
    stage_req = ExecutionStageRequest(
        tool_id="dir_list",
        action="read",
        params={},
        risk_level=RiskLevel.R0,
        approval_id=app.approval_id,
        budget=budget,
    )

    res = executor.stage_and_simulate(stage_req)
    assert res.success is True
    assert res.status == StageStatus.SIMULATED
    assert res.simulated_output["resource_budget"]["max_runtime_seconds"] == 15.0

    store.close()


def test_staging_denies_invalid_resource_budget(workspace: Path):
    """Verify staging request with invalid/excessive ResourceBudget is rejected before simulation."""
    from quan_ai_brain.execution.resource_budget import ResourceBudget

    executor = IsolatedStagingExecutor(workspace=workspace)
    invalid_budget = ResourceBudget(max_runtime_seconds=-10.0)  # Invalid negative runtime

    stage_req = ExecutionStageRequest(
        tool_id="dir_list",
        action="read",
        params={},
        risk_level=RiskLevel.R0,
        budget=invalid_budget,
    )

    res = executor.stage_and_simulate(stage_req)
    assert res.success is False
    assert res.status == StageStatus.DENIED
    assert res.governance_decision == "denied_budget"
    assert "Resource budget validation failed" in (res.error or "")


def test_staging_denies_budget_exceeding_delegation_grant(workspace: Path):
    """Verify staging request where budget exceeds delegation grant max_calls is rejected."""
    from quan_ai_brain.execution.resource_budget import ResourceBudget

    store = GovernanceStateStore(":memory:")
    delegation = DelegationRegistry(store=store)
    executor = IsolatedStagingExecutor(workspace=workspace, delegation_registry=delegation, store=store)

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    grant = DelegationGrant(
        grant_id="grant_budget_test",
        owner_identity="owner_quan",
        description="test grant",
        allowed_tool_ids=["dir_list"],
        allowed_action_types=["read"],
        allowed_resource_scope="workspace",
        allowed_project_scope="QUAN_AI_BRAIN",
        maximum_risk_level=RiskLevel.R0,
        valid_from=now,
        expires_at=future,
        max_calls=2,
    )
    delegation.register_grant(grant)

    # Budget requests 5 calls, exceeding grant limit of 2
    excess_budget = ResourceBudget(max_tool_calls=5)
    stage_req = ExecutionStageRequest(
        tool_id="dir_list",
        action="read",
        params={},
        risk_level=RiskLevel.R0,
        grant_id="grant_budget_test",
        budget=excess_budget,
    )

    res = executor.stage_and_simulate(stage_req)
    assert res.success is False
    assert res.status == StageStatus.DENIED
    assert "Delegation grant budget exceeded" in (res.error or "")

    store.close()


def test_production_execution_prohibited_error_raised(workspace: Path):
    """Verify ProductionExecutionProhibitedError is specifically raised on execute_production."""
    from quan_ai_brain.execution.staging import ProductionExecutionProhibitedError

    executor = IsolatedStagingExecutor(workspace=workspace)
    with pytest.raises(ProductionExecutionProhibitedError) as exc_info:
        executor.execute_production({"cmd": "whoami"})
    assert "strictly disabled in Sprint 6" in str(exc_info.value)
    assert "PENDING_OWNER_SIGNOFF" in str(exc_info.value)


def test_design_signoff_documents_exist_and_are_pending():
    """Verify that both docs/SPRINT5_DESIGN_SIGNOFF.md and docs/SPRINT6_DESIGN_SIGNOFF.md are PENDING_OWNER_SIGNOFF."""
    root = Path(__file__).resolve().parents[1]

    # Sprint 5
    sprint5_doc = root / "docs" / "SPRINT5_DESIGN_SIGNOFF.md"
    assert sprint5_doc.exists(), "docs/SPRINT5_DESIGN_SIGNOFF.md must exist"
    c5 = sprint5_doc.read_text(encoding="utf-8")
    assert "PENDING_OWNER_SIGNOFF" in c5

    # Sprint 6
    sprint6_doc = root / "docs" / "SPRINT6_DESIGN_SIGNOFF.md"
    assert sprint6_doc.exists(), "docs/SPRINT6_DESIGN_SIGNOFF.md must exist"
    c6 = sprint6_doc.read_text(encoding="utf-8")
    assert "PENDING_OWNER_SIGNOFF" in c6
    assert "ZERO PRODUCTION EXECUTION" in c6

