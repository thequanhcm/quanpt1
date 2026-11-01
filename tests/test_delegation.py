"""Unit tests for Delegated Autonomy Governance and Grant Registry (Sprint 3B)."""
from datetime import datetime, timedelta, timezone
import pytest

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.delegation import (
    DelegationGrant,
    DelegationRegistry,
    GrantStatus,
)


def _make_valid_grant(
    grant_id: str = "grant-001",
    owner_identity: str = "owner:quanpt1",
    allowed_tools: list[str] | None = None,
    allowed_actions: list[str] | None = None,
    maximum_risk: RiskLevel = RiskLevel.R1,
    max_calls: int | None = 5,
    valid_offset_hours: int = -1,
    expire_offset_hours: int = 24,
) -> DelegationGrant:
    now = datetime.now(timezone.utc)
    start = (now + timedelta(hours=valid_offset_hours)).isoformat()
    end = (now + timedelta(hours=expire_offset_hours)).isoformat()
    return DelegationGrant(
        grant_id=grant_id,
        owner_identity=owner_identity,
        description="Autonomous safe inspection and planning grant",
        allowed_tool_ids=allowed_tools or ["file_read", "dir_list", "git_status", "system_health", "plan_validate"],
        allowed_action_types=allowed_actions or ["read", "analysis"],
        allowed_resource_scope="workspace",
        allowed_project_scope="QUAN_AI_BRAIN",
        maximum_risk_level=maximum_risk,
        valid_from=start,
        expires_at=end,
        max_calls=max_calls,
    )


def test_delegation_grant_creation_and_validation():
    grant = _make_valid_grant()
    assert grant.grant_id == "grant-001"
    assert grant.status == GrantStatus.ACTIVE
    assert grant.calls_count == 0


def test_delegation_prohibits_r4_and_r5():
    # Attempting to delegate R4
    with pytest.raises(ValueError, match="cannot exceed R2"):
        _make_valid_grant(maximum_risk=RiskLevel.R4)

    # Attempting to delegate R5
    with pytest.raises(ValueError, match="cannot exceed R2"):
        _make_valid_grant(maximum_risk=RiskLevel.R5)


def test_delegation_prohibits_wildcard_tools():
    with pytest.raises(ValueError, match="Wildcard '\\*' tool authorization is strictly prohibited"):
        _make_valid_grant(allowed_tools=["*"])


def test_delegation_prohibits_invalid_timestamps():
    now = datetime.now(timezone.utc)
    past = (now - timedelta(hours=2)).isoformat()
    future = (now + timedelta(hours=2)).isoformat()

    # expires_at earlier than valid_from
    with pytest.raises(ValueError, match="expires_at must be strictly after valid_from"):
        DelegationGrant(
            grant_id="grant-bad-time",
            owner_identity="owner:quanpt1",
            description="bad time",
            allowed_tool_ids=["file_read"],
            allowed_action_types=["read"],
            allowed_resource_scope="workspace",
            allowed_project_scope="QUAN_AI_BRAIN",
            maximum_risk_level=RiskLevel.R0,
            valid_from=future,
            expires_at=past,
        )


def test_check_delegation_success():
    registry = DelegationRegistry()
    grant = _make_valid_grant()
    registry.register_grant(grant)

    ok, reason, matched = registry.check_delegation(
        tool_id="file_read",
        action_type="read",
        risk_level=RiskLevel.R0,
        resource_path="README.md",
        project_scope="QUAN_AI_BRAIN",
    )
    assert ok is True
    assert matched is not None
    assert matched.grant_id == "grant-001"
    assert "Authorized by delegation grant" in reason


def test_check_delegation_tool_mismatch():
    registry = DelegationRegistry()
    grant = _make_valid_grant(allowed_tools=["file_read"])
    registry.register_grant(grant)

    # dir_list is not in allowed_tool_ids
    ok, reason, matched = registry.check_delegation(
        tool_id="dir_list",
        action_type="read",
        risk_level=RiskLevel.R0,
    )
    assert ok is False
    assert matched is None


def test_check_delegation_action_mismatch():
    registry = DelegationRegistry()
    grant = _make_valid_grant(allowed_actions=["read"])
    registry.register_grant(grant)

    # action_type write is not in allowed_action_types
    ok, reason, matched = registry.check_delegation(
        tool_id="file_read",
        action_type="write",
        risk_level=RiskLevel.R0,
    )
    assert ok is False
    assert matched is None


def test_check_delegation_risk_exceeded():
    registry = DelegationRegistry()
    grant = _make_valid_grant(maximum_risk=RiskLevel.R0)
    registry.register_grant(grant)

    # action requires R1, but grant only permits up to R0
    ok, reason, matched = registry.check_delegation(
        tool_id="file_read",
        action_type="read",
        risk_level=RiskLevel.R1,
    )
    assert ok is False
    assert matched is None


def test_check_delegation_expiry():
    registry = DelegationRegistry()
    # Expired 1 hour ago
    grant = _make_valid_grant(valid_offset_hours=-24, expire_offset_hours=-1)
    registry.register_grant(grant)

    ok, reason, matched = registry.check_delegation(
        tool_id="file_read",
        action_type="read",
        risk_level=RiskLevel.R0,
    )
    assert ok is False
    assert matched is None
    assert grant.status == GrantStatus.EXPIRED


def test_check_delegation_revocation():
    registry = DelegationRegistry()
    grant = _make_valid_grant()
    registry.register_grant(grant)

    revoked = registry.revoke_grant(grant.grant_id, reason="Owner revoked permissions")
    assert revoked is True
    assert grant.status == GrantStatus.REVOKED

    ok, reason, matched = registry.check_delegation(
        tool_id="file_read",
        action_type="read",
        risk_level=RiskLevel.R0,
    )
    assert ok is False
    assert matched is None


def test_check_delegation_max_calls_limit():
    registry = DelegationRegistry()
    grant = _make_valid_grant(max_calls=2)
    registry.register_grant(grant)

    # First call: permitted
    ok1, _, _ = registry.check_delegation("file_read", "read", RiskLevel.R0)
    assert ok1 is True
    registry.record_usage(grant.grant_id)

    # Second call: permitted
    ok2, _, _ = registry.check_delegation("file_read", "read", RiskLevel.R0)
    assert ok2 is True
    registry.record_usage(grant.grant_id)

    # Third call: budget exhausted -> rejected
    ok3, reason, matched = registry.check_delegation("file_read", "read", RiskLevel.R0)
    assert ok3 is False
    assert matched is None
    assert grant.calls_count == 2


def test_untrusted_owner_grant_rejected():
    registry = DelegationRegistry(trusted_owner_identities={"owner:quanpt1"})
    untrusted_grant = _make_valid_grant(owner_identity="malicious_user")

    with pytest.raises(PermissionError, match="not in trusted owner identities"):
        registry.register_grant(untrusted_grant)


def test_duplicate_grant_id_rejected():
    registry = DelegationRegistry()
    g1 = _make_valid_grant(grant_id="grant-fixed")
    g2 = _make_valid_grant(grant_id="grant-fixed")

    registry.register_grant(g1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_grant(g2)
