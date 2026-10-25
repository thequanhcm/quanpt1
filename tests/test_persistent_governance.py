"""Integration tests for Persistent Governance State across Sandbox, Gates, and Verifiers."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateCorruptError, GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate
from quan_ai_brain.tools.delegation import DelegationGrant, DelegationRegistry
from quan_ai_brain.tools.sandbox import SafeToolSandbox, SystemState
from quan_ai_brain.tools.verifier import (
    AuthenticatedApprovalVerifier,
    SignedApproval,
    VerificationMethod,
    VerificationOutcome,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "hello.txt").write_text("Hello Persistent Governance", encoding="utf-8")
    return ws


def test_sandbox_emergency_stop_persists_across_instances(workspace: Path):
    """Verify emergency STOP state set in one sandbox instance blocks execution in a new instance."""
    db_path = workspace / "gov.db"
    store1 = GovernanceStateStore(db_path, workspace=workspace)

    sandbox1 = SafeToolSandbox(workspace=workspace, store=store1)
    sandbox1.set_system_state(SystemState.STOP, reason="Owner emergency halt", activated_by="OWNER")
    assert sandbox1.get_system_state() == SystemState.STOP
    store1.close()

    # Create a completely new store and sandbox instance pointing to the same DB
    store2 = GovernanceStateStore(db_path, workspace=workspace)
    sandbox2 = SafeToolSandbox(workspace=workspace, store=store2)

    # 1. New sandbox MUST detect STOP state on startup
    assert sandbox2.get_system_state() == SystemState.STOP

    # 2. Any tool execution attempt MUST be blocked by Step 5
    res = sandbox2.execute(tool_id="dir_list", params={})
    assert res.success is False
    assert res.governance_decision == "blocked"
    assert "STOP state" in (res.error or "")

    store2.close()


def test_approval_consumption_persists_across_sandbox_restarts(workspace: Path):
    """Verify an approval consumed in session 1 cannot be reused in session 2."""
    db_path = workspace / "gov.db"
    store1 = GovernanceStateStore(db_path, workspace=workspace)

    gate1 = ApprovalGate(store=store1)
    sandbox1 = SafeToolSandbox(workspace=workspace, approval_gate=gate1, store=store1)

    req = gate1.create_request(
        tool_id="file_read",
        action="read",
        params={"file_path": "hello.txt"},
        resource_scope="workspace",
        risk_level=RiskLevel.R0,
    )
    approval = gate1.grant_approval(req, approver="owner_quan")

    # Session 1: Execute tool with approval -> succeeds and consumes approval
    res1 = sandbox1.execute(
        tool_id="file_read",
        params={"file_path": "hello.txt"},
        approval_id=approval.approval_id,
    )
    assert res1.success is True
    assert res1.output["content"] == "Hello Persistent Governance"
    store1.close()

    # Session 2: Fresh instances pointing to same database
    store2 = GovernanceStateStore(db_path, workspace=workspace)
    gate2 = ApprovalGate(store=store2)
    sandbox2 = SafeToolSandbox(workspace=workspace, approval_gate=gate2, store=store2)

    # Attempt to reuse the consumed approval -> MUST be denied
    res2 = sandbox2.execute(
        tool_id="file_read",
        params={"file_path": "hello.txt"},
        approval_id=approval.approval_id,
    )
    assert res2.success is False
    assert res2.governance_decision == "denied"
    assert "already been consumed" in (res2.error or "")

    store2.close()


def test_delegation_revocation_persists_across_sandbox_restarts(workspace: Path):
    """Verify delegation grant revoked in session 1 remains revoked in session 2."""
    db_path = workspace / "gov.db"
    store1 = GovernanceStateStore(db_path, workspace=workspace)

    delegation1 = DelegationRegistry(store=store1)
    sandbox1 = SafeToolSandbox(workspace=workspace, delegation_registry=delegation1, store=store1)

    now = datetime.now(timezone.utc)
    grant = DelegationGrant(
        grant_id="grant-read-txt",
        owner_identity="owner_quan",
        description="Allow reading text files",
        allowed_tool_ids=["file_read"],
        allowed_action_types=["read"],
        allowed_resource_scope="workspace",
        allowed_project_scope="QUAN_AI_BRAIN",
        maximum_risk_level=RiskLevel.R0,
        valid_from=(now - timedelta(hours=1)).isoformat(),
        expires_at=(now + timedelta(hours=24)).isoformat(),
        max_calls=5,
    )
    delegation1.register_grant(grant)

    # Tool executes autonomously under delegation
    res1 = sandbox1.execute(tool_id="file_read", params={"file_path": "hello.txt"})
    assert res1.success is True
    assert res1.governance_decision == "allowed_by_delegation"

    # Revoke grant in session 1
    delegation1.revoke_grant("grant-read-txt", reason="Revocation test")
    store1.close()

    # Session 2: Reopen in new sandbox
    store2 = GovernanceStateStore(db_path, workspace=workspace)
    delegation2 = DelegationRegistry(store=store2)
    sandbox2 = SafeToolSandbox(workspace=workspace, delegation_registry=delegation2, store=store2)

    # Autonomous execution must now fail because grant is revoked
    res2 = sandbox2.execute(tool_id="file_read", params={"file_path": "hello.txt"})
    assert res2.success is False
    assert res2.governance_decision == "pending_owner_approval"

    store2.close()


def test_verifier_replay_protection_persists_across_restarts(workspace: Path):
    """Verify AuthenticatedApprovalVerifier blocks reused nonces across process restart."""
    db_path = workspace / "gov.db"
    store1 = GovernanceStateStore(db_path, workspace=workspace)

    key = b"super-secret-owner-key-256bit-ok"
    verifier1 = AuthenticatedApprovalVerifier(owner_secret_key=key, store=store1)

    now = datetime.now(timezone.utc)
    app = SignedApproval(
        approval_id="app-sig-101",
        tool_id="file_read",
        action="read",
        params={"file_path": "hello.txt"},
        resource_scope="workspace",
        risk_level=RiskLevel.R0,
        fingerprint="fp-test-101",
        nonce="unique-nonce-101",
        expires_at=(now + timedelta(hours=24)).isoformat(),
        signer_identity="owner_quan",
        verification_method=VerificationMethod.SECRET_CODE,
    )
    app.signature = verifier1.sign_approval(app)

    # First verification & consumption succeeds
    ok1, outcome1, _ = verifier1.verify_approval(
        approval=app,
        current_fingerprint="fp-test-101",
        current_risk=RiskLevel.R0,
    )
    assert ok1 is True
    assert outcome1 == VerificationOutcome.VERIFIED
    assert verifier1.consume_approval(app) is True
    store1.close()

    # Session 2: New verifier instance with same store
    store2 = GovernanceStateStore(db_path, workspace=workspace)
    verifier2 = AuthenticatedApprovalVerifier(owner_secret_key=key, store=store2)

    # Replay of the same approval / nonce MUST be rejected
    ok2, outcome2, _ = verifier2.verify_approval(
        approval=app,
        current_fingerprint="fp-test-101",
        current_risk=RiskLevel.R0,
    )
    assert ok2 is False
    assert outcome2 == VerificationOutcome.DENIED_CONSUMED

    store2.close()


def test_corrupt_database_causes_sandbox_fail_closed(workspace: Path):
    """Verify that corrupt governance database causes SafeToolSandbox to fail closed."""
    db_path = workspace / "corrupt.db"
    db_path.write_text("NOT A VALID SQLITE DATABASE FILE", encoding="utf-8")

    # Creating store with corrupt file must raise GovernanceStateCorruptError
    with pytest.raises(GovernanceStateCorruptError):
        store = GovernanceStateStore(db_path, workspace=workspace)
        SafeToolSandbox(workspace=workspace, store=store)
