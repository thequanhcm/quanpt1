"""Unit tests for Owner Approval Gate and Consent Management (Sprint 3B)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.approval import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
    compute_action_fingerprint,
)


def test_default_approval_request_pending():
    gate = ApprovalGate()
    req = gate.create_request(
        tool_id="file_read",
        action="read",
        params={"file_path": "README.md"},
        resource_scope="workspace",
        risk_level=RiskLevel.R0,
        goal="Read project readme",
    )
    assert req.status == ApprovalStatus.PENDING_OWNER_APPROVAL
    assert req.tool_id == "file_read"
    assert req.fingerprint == compute_action_fingerprint(
        "file_read", "read", {"file_path": "README.md"}, "workspace", 0
    )


def test_approval_grant_and_one_time_consumption():
    gate = ApprovalGate()
    req = gate.create_request("file_read", "read", {"file_path": "README.md"})
    approval = gate.grant_approval(req, approver="owner:quanpt1")

    assert approval.status == ApprovalStatus.APPROVED
    assert not approval.consumed
    assert approval.approver == "owner:quanpt1"

    # Evaluate approval passes
    valid, reason = gate.evaluate_approval(approval.approval_id, req)
    assert valid is True
    assert "Valid" in reason

    # Consume approval
    consumed = gate.consume_approval(approval.approval_id)
    assert consumed is True
    assert approval.consumed is True
    assert approval.status == ApprovalStatus.COMPLETED

    # Subsequent evaluation must fail (replay attack protection)
    valid_again, reason_again = gate.evaluate_approval(approval.approval_id, req)
    assert valid_again is False
    assert "already been consumed" in reason_again


def test_fingerprint_tampering_protection():
    gate = ApprovalGate()
    req = gate.create_request("file_read", "read", {"file_path": "safe.txt"})
    approval = gate.grant_approval(req, approver="owner:quanpt1")

    # Tampered request with different file path
    tampered_req = gate.create_request("file_read", "read", {"file_path": "secret.txt"})

    valid, reason = gate.evaluate_approval(approval.approval_id, tampered_req)
    assert valid is False
    assert "fingerprint mismatch" in reason.lower()


def test_approval_expiry():
    gate = ApprovalGate()
    req = gate.create_request("file_read", "read", {"file_path": "README.md"})

    # Expired 1 hour ago
    past_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    approval = gate.grant_approval(req, approver="owner:quanpt1", expires_at=past_ts)

    valid, reason = gate.evaluate_approval(approval.approval_id, req)
    assert valid is False
    assert "expired" in reason.lower()
    assert approval.status == ApprovalStatus.EXPIRED


def test_approval_revocation():
    gate = ApprovalGate()
    req = gate.create_request("file_read", "read", {"file_path": "README.md"})
    approval = gate.grant_approval(req, approver="owner:quanpt1")

    # Revoke approval
    revoked = gate.revoke_approval(approval.approval_id, reason="Owner changed mind")
    assert revoked is True
    assert approval.revoked is True
    assert approval.status == ApprovalStatus.REVOKED

    valid, reason = gate.evaluate_approval(approval.approval_id, req)
    assert valid is False
    assert "revoked" in reason.lower()


def test_approval_tool_and_risk_mismatch():
    gate = ApprovalGate()
    req_read = gate.create_request("file_read", "read", {"file_path": "README.md"}, risk_level=RiskLevel.R0)
    approval = gate.grant_approval(req_read, approver="owner:quanpt1")

    # Request with different tool ID
    req_other_tool = ApprovalRequest(
        request_id="other-req",
        tool_id="dir_list",
        action="read",
        params={"file_path": "README.md"},
        resource_scope="workspace",
        risk_level=RiskLevel.R0,
        fingerprint=approval.fingerprint,  # force same fp
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    valid, reason = gate.evaluate_approval(approval.approval_id, req_other_tool)
    assert valid is False
    assert "Approval is for tool" in reason

    # Request with different risk level
    req_other_risk = ApprovalRequest(
        request_id="risk-req",
        tool_id="file_read",
        action="read",
        params={"file_path": "README.md"},
        resource_scope="workspace",
        risk_level=RiskLevel.R2,
        fingerprint=approval.fingerprint,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    valid_risk, reason_risk = gate.evaluate_approval(approval.approval_id, req_other_risk)
    assert valid_risk is False
    assert "risk level does not match" in reason_risk


def test_untrusted_approver_rejected():
    gate = ApprovalGate(trusted_approvers={"owner:quanpt1"})
    req = gate.create_request("file_read", "read", {"file_path": "README.md"})

    with pytest.raises(PermissionError, match="not in trusted owner identities"):
        gate.grant_approval(req, approver="attacker:fake_admin")


def test_empty_approver_rejected():
    gate = ApprovalGate()
    req = gate.create_request("file_read", "read", {"file_path": "README.md"})

    with pytest.raises(ValueError, match="Approver identity must not be empty"):
        gate.grant_approval(req, approver="   ")
