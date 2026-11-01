"""Delegated Autonomy Governance and Delegation Grant Registry for QUAN AI BRAIN.

Principle:
Autonomous action without real-time owner consultation is only permitted
under an explicit, verified, bounded, revocable Delegation Grant.
R4 and R5 can NEVER be delegated.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from quan_ai_brain.governance.policy import RiskLevel


class GrantStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class DelegationGrant:
    """Explicit grant of bounded delegated autonomy from project owner."""

    grant_id: str
    owner_identity: str
    description: str
    allowed_tool_ids: list[str]
    allowed_action_types: list[str]
    allowed_resource_scope: str  # e.g. "workspace"
    allowed_project_scope: str  # e.g. "QUAN_AI_BRAIN"
    maximum_risk_level: RiskLevel
    valid_from: str
    expires_at: str
    max_calls: int | None = None
    calls_count: int = 0
    status: GrantStatus = GrantStatus.ACTIVE
    created_by: str = ""
    approval_reference: str = ""
    audit_reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.grant_id or not self.grant_id.strip():
            raise ValueError("grant_id must not be empty")
        if not self.owner_identity or not self.owner_identity.strip():
            raise ValueError("owner_identity must not be empty")
        if not self.allowed_tool_ids:
            raise ValueError("allowed_tool_ids must not be empty")
        if "*" in self.allowed_tool_ids:
            raise ValueError("Wildcard '*' tool authorization is strictly prohibited in delegation grants")
        if not self.allowed_action_types:
            raise ValueError("allowed_action_types must not be empty")

        # R4 and R5 can NEVER be delegated
        if int(self.maximum_risk_level) > int(RiskLevel.R2):
            raise ValueError(
                f"Delegation grant maximum risk level cannot exceed R2 (got {self.maximum_risk_level}). "
                "R4 requires explicit owner approval; R5 is hard-blocked."
            )

        # Validate timestamp bounds
        try:
            start_dt = datetime.fromisoformat(self.valid_from)
            end_dt = datetime.fromisoformat(self.expires_at)
            if start_dt >= end_dt:
                raise ValueError("expires_at must be strictly after valid_from")
        except ValueError as exc:
            if "strictly after" in str(exc):
                raise
            raise ValueError(f"Invalid timestamp format in delegation grant: {exc}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DelegationRegistry:
    """Manages active delegation grants and verifies autonomous execution rights."""

    def __init__(
        self,
        trusted_owner_identities: set[str] | None = None,
        store: Any | None = None,
    ) -> None:
        self.trusted_owner_identities = trusted_owner_identities
        self.store = store
        self._grants: dict[str, DelegationGrant] = {}

    def register_grant(self, grant: DelegationGrant) -> None:
        """Register a validated delegation grant."""
        if not isinstance(grant, DelegationGrant):
            raise TypeError("grant must be a DelegationGrant instance")

        if self.trusted_owner_identities is not None:
            if grant.owner_identity not in self.trusted_owner_identities:
                raise PermissionError(
                    f"Delegation grant owner '{grant.owner_identity}' is not in trusted owner identities"
                )

        if grant.grant_id in self._grants:
            raise ValueError(f"Delegation grant '{grant.grant_id}' is already registered")

        self._grants[grant.grant_id] = grant
        if self.store is not None:
            self.store.save_grant(grant)

    def get_grant(self, grant_id: str) -> DelegationGrant | None:
        if grant_id in self._grants:
            return self._grants[grant_id]
        if self.store is not None:
            stored = self.store.get_grant(grant_id)
            if stored is not None:
                self._grants[grant_id] = stored
                return stored
        return None

    def revoke_grant(self, grant_id: str, reason: str = "") -> bool:
        """Revoke a delegation grant immediately."""
        if self.store is not None:
            self.store.revoke_grant(grant_id, reason=reason)

        grant = self.get_grant(grant_id)
        if not grant:
            return False
        grant.status = GrantStatus.REVOKED
        grant.metadata["revocation_reason"] = reason
        return True

    def list_active_grants(self) -> list[DelegationGrant]:
        if self.store is not None:
            stored_grants = self.store.list_grants()
            for g in stored_grants:
                self._grants[g.grant_id] = g

        now_dt = datetime.now(timezone.utc)
        active = []
        for grant in self._grants.values():
            if grant.status != GrantStatus.ACTIVE:
                continue
            exp_dt = datetime.fromisoformat(grant.expires_at)
            if now_dt > exp_dt:
                grant.status = GrantStatus.EXPIRED
                continue
            active.append(grant)
        return active

    def check_delegation(
        self,
        tool_id: str,
        action_type: str,
        risk_level: RiskLevel,
        resource_path: str | None = None,
        project_scope: str = "QUAN_AI_BRAIN",
    ) -> tuple[bool, str, DelegationGrant | None]:
        """Evaluate whether any active delegation grant authorizes this action.

        Returns: (authorized, reason, matching_grant)
        """
        # Rule: R4 and R5 can NEVER be delegated under any circumstances
        if int(risk_level) > int(RiskLevel.R2):
            return False, f"Risk level {risk_level.name} exceeds delegatable threshold (max R2)", None

        now_dt = datetime.now(timezone.utc)

        for grant in self._grants.values():
            # Check 1: Status must be ACTIVE
            if grant.status != GrantStatus.ACTIVE:
                continue

            # Check 2: Expiry and validity window
            start_dt = datetime.fromisoformat(grant.valid_from)
            exp_dt = datetime.fromisoformat(grant.expires_at)
            if now_dt < start_dt:
                continue
            if now_dt > exp_dt:
                grant.status = GrantStatus.EXPIRED
                continue

            # Check 3: Revocation
            if grant.status == GrantStatus.REVOKED:
                continue

            # Check 4: Tool ID must be explicitly in allowed list
            if tool_id not in grant.allowed_tool_ids:
                continue

            # Check 5: Action type must be explicitly allowed
            if action_type not in grant.allowed_action_types:
                continue

            # Check 6: Risk level must not exceed grant's maximum
            if int(risk_level) > int(grant.maximum_risk_level):
                continue

            # Check 7: Project scope must match
            if grant.allowed_project_scope and grant.allowed_project_scope != project_scope:
                continue

            # Check 8: Resource scope check
            # "workspace" allows any workspace-relative resource
            if grant.allowed_resource_scope != "workspace" and resource_path:
                if not resource_path.startswith(grant.allowed_resource_scope):
                    continue

            # Check 9: Call budget check
            if grant.max_calls is not None and grant.calls_count >= grant.max_calls:
                continue

            # Check 10: Owner identity must be trusted if enforcement configured
            if self.trusted_owner_identities is not None:
                if grant.owner_identity not in self.trusted_owner_identities:
                    continue

            # All 10 conditions satisfied!
            return True, f"Authorized by delegation grant '{grant.grant_id}'", grant

        return False, "No active delegation grant matches tool, action, risk, or scope", None

    def record_usage(self, grant_id: str) -> None:
        """Increment usage count for a grant."""
        if self.store is not None:
            new_calls = self.store.increment_grant_usage(grant_id)
            grant = self.get_grant(grant_id)
            if grant:
                grant.calls_count = new_calls
            return

        grant = self._grants.get(grant_id)
        if grant:
            grant.calls_count += 1

