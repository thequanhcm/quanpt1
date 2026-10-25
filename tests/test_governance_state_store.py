"""Unit tests for GovernanceStateStore (Sprint 5: Persistent Governance State)."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
import pytest

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.governance.state_store import (
    CURRENT_SCHEMA_VERSION,
    EmergencyStateRecord,
    GovernanceStateCorruptError,
    GovernanceStateStore,
)
from quan_ai_brain.tools.approval import ApprovalRequest, ApprovalStatus, OwnerApproval
from quan_ai_brain.tools.delegation import DelegationGrant, GrantStatus


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


def test_store_initialization_in_memory():
    """Verify in-memory governance store creates all mandatory tables and schema version."""
    store = GovernanceStateStore(":memory:")
    store.verify_integrity()
    state = store.get_emergency_state()
    assert state.state == "normal"
    store.close()


def test_store_emergency_state_stop_freeze_normal(temp_workspace: Path):
    """Verify emergency state transitions and prioritization (STOP > FREEZE > NORMAL)."""
    db_file = temp_workspace / "governance.db"
    store = GovernanceStateStore(db_file, workspace=temp_workspace)

    # Initial state is normal
    assert store.get_emergency_state().state == "normal"

    # Set FREEZE
    store.set_emergency_state(
        state="freeze",
        reason="Suspicious anomaly detected",
        activated_by="POLICY_ENGINE",
    )
    assert store.get_emergency_state().state == "freeze"

    # Set STOP (should take precedence)
    store.set_emergency_state(
        state="stop",
        reason="Manual owner emergency kill",
        activated_by="OWNER",
    )
    assert store.get_emergency_state().state == "stop"

    # Clear back to normal
    store.set_emergency_state(
        state="normal",
        reason="Incident resolved and owner approved resume",
        activated_by="OWNER",
    )
    assert store.get_emergency_state().state == "normal"
    store.close()


def test_approval_persistence_and_atomic_consumption(temp_workspace: Path):
    """Verify approvals are persisted and can be consumed strictly once."""
    db_file = temp_workspace / "governance.db"
    store = GovernanceStateStore(db_file, workspace=temp_workspace)

    app = OwnerApproval(
        approval_id="app-12345",
        request_id="req-999",
        approver="test_owner",
        tool_id="file_write_new",
        action="write",
        params={"file_path": "test.txt", "content": "hello"},
        resource_scope="workspace",
        risk_level=RiskLevel.R2,
        fingerprint="fp_abc123",
        granted_at="2026-10-18T10:00:00Z",
    )
    store.save_approval(app, auth_method="secret_code")

    # Fetch back
    fetched = store.get_approval("app-12345")
    assert fetched is not None
    assert fetched.approval_id == "app-12345"
    assert not fetched.consumed

    # First consumption succeeds
    assert store.consume_approval("app-12345") is True

    # Second consumption MUST fail (anti-replay single-use)
    assert store.consume_approval("app-12345") is False

    # Check state after consumption
    fetched2 = store.get_approval("app-12345")
    assert fetched2.consumed is True
    assert fetched2.status == ApprovalStatus.COMPLETED
    store.close()


def test_replay_prevention_nonces(temp_workspace: Path):
    """Verify nonces are recorded and duplicates are rejected."""
    db_file = temp_workspace / "governance.db"
    store = GovernanceStateStore(db_file, workspace=temp_workspace)

    # First use of nonce
    assert store.record_nonce("nonce-xyz-001", "app-100") is True
    assert store.is_nonce_consumed("nonce-xyz-001") is True

    # Second use of identical nonce is blocked
    assert store.record_nonce("nonce-xyz-001", "app-101") is False

    store.close()


def test_delegation_grant_persistence_and_revocation(temp_workspace: Path):
    """Verify delegation grants persist, track atomic call count, and support revocation."""
    db_file = temp_workspace / "governance.db"
    store = GovernanceStateStore(db_file, workspace=temp_workspace)

    grant = DelegationGrant(
        grant_id="grant-001",
        owner_identity="owner_quan",
        description="Allow directory listing",
        allowed_tool_ids=["dir_list"],
        allowed_action_types=["read"],
        allowed_resource_scope="workspace",
        allowed_project_scope="QUAN_AI_BRAIN",
        maximum_risk_level=RiskLevel.R0,
        valid_from="2026-10-18T00:00:00Z",
        expires_at="2026-10-18T23:59:59Z",
        max_calls=10,
    )
    store.save_grant(grant)

    fetched = store.get_grant("grant-001")
    assert fetched is not None
    assert fetched.grant_id == "grant-001"
    assert fetched.status == GrantStatus.ACTIVE
    assert fetched.calls_count == 0

    # Increment calls
    c1 = store.increment_grant_usage("grant-001")
    assert c1 == 1
    c2 = store.increment_grant_usage("grant-001")
    assert c2 == 2

    # Revoke grant
    assert store.revoke_grant("grant-001", reason="Security audit rotation") is True
    assert store.revoke_grant("grant-001") is False  # Already revoked

    revoked_grant = store.get_grant("grant-001")
    assert revoked_grant.status == GrantStatus.REVOKED
    store.close()


def test_persistence_survives_process_restart(temp_workspace: Path):
    """Verify that STOP state, consumed approvals, nonces, and revoked grants survive restart."""
    db_file = temp_workspace / "governance.db"

    # Session 1: configure state
    store1 = GovernanceStateStore(db_file, workspace=temp_workspace)
    store1.set_emergency_state("stop", reason="Critical breach", activated_by="OWNER")

    app = OwnerApproval(
        approval_id="app-persist-1",
        request_id="req-1",
        approver="owner_quan",
        tool_id="file_read",
        action="read",
        params={"file_path": "readme.md"},
        resource_scope="workspace",
        risk_level=RiskLevel.R0,
        fingerprint="fp_read",
        granted_at="2026-10-18T10:00:00Z",
    )
    store1.save_approval(app)
    assert store1.consume_approval("app-persist-1") is True

    assert store1.record_nonce("nonce-persist-1", "app-persist-1") is True

    grant = DelegationGrant(
        grant_id="grant-persist-1",
        owner_identity="owner_quan",
        description="Allow read",
        allowed_tool_ids=["file_read"],
        allowed_action_types=["read"],
        allowed_resource_scope="workspace",
        allowed_project_scope="QUAN_AI_BRAIN",
        maximum_risk_level=RiskLevel.R0,
        valid_from="2026-10-18T00:00:00Z",
        expires_at="2026-10-18T23:59:59Z",
    )
    store1.save_grant(grant)
    assert store1.revoke_grant("grant-persist-1", reason="Pre-restart revoke") is True

    # Simulate restart by closing connection
    store1.close()

    # Session 2: reopen store
    store2 = GovernanceStateStore(db_file, workspace=temp_workspace)

    # 1. STOP state MUST still be active
    assert store2.get_emergency_state().state == "stop"

    # 2. Consumed approval MUST still be consumed
    app2 = store2.get_approval("app-persist-1")
    assert app2 is not None
    assert app2.consumed is True
    assert store2.consume_approval("app-persist-1") is False

    # 3. Nonce MUST still be marked consumed
    assert store2.is_nonce_consumed("nonce-persist-1") is True
    assert store2.record_nonce("nonce-persist-1", "app-dummy") is False

    # 4. Revoked grant MUST still be revoked
    grant2 = store2.get_grant("grant-persist-1")
    assert grant2 is not None
    assert grant2.status == GrantStatus.REVOKED

    store2.close()


def test_corrupt_database_fails_closed(temp_workspace: Path):
    """Verify that corrupt database or missing tables raises GovernanceStateCorruptError."""
    db_file = temp_workspace / "corrupt_gov.db"

    # Write a dummy corrupt sqlite file (or a valid sqlite file missing mandatory tables)
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE schema_info (version INTEGER PRIMARY KEY, applied_at_utc TEXT, description TEXT);")
    conn.execute("INSERT INTO schema_info VALUES (1, 'now', 'corrupt schema missing tables');")
    conn.commit()
    conn.close()

    # Reopening without required tables must fail closed
    with pytest.raises(GovernanceStateCorruptError) as exc_info:
        GovernanceStateStore(db_file, workspace=temp_workspace)
    assert "missing mandatory tables" in str(exc_info.value)
