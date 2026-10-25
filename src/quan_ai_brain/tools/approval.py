"""Owner Approval Gate and Consent Management for QUAN AI BRAIN.

Principle:
All tool actions default to requiring explicit, informed, and verified owner approval,
unless explicitly covered by a valid, active delegation grant.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.governance.policy import RiskLevel


class ApprovalStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING_OWNER_APPROVAL = "pending_owner_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    DENIED = "denied"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    REVOKED = "revoked"


def compute_action_fingerprint(
    tool_id: str,
    action: str,
    params: dict[str, Any],
    resource_scope: str = "",
    risk_level: int = 0,
) -> str:
    """Compute deterministic SHA-256 digest of action parameters to prevent tampering."""
    canonical_payload = {
        "tool_id": str(tool_id).strip(),
        "action": str(action).strip(),
        "params": redact_value(params or {}),
        "resource_scope": str(resource_scope).strip(),
        "risk_level": int(risk_level),
    }
    raw = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class ApprovalRequest:
    """Formal request for owner approval prior to executing a tool action."""

    request_id: str
    tool_id: str
    action: str
    params: dict[str, Any]
    resource_scope: str
    risk_level: RiskLevel
    fingerprint: str
    created_at: str
    goal: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING_OWNER_APPROVAL
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OwnerApproval:
    """Specific owner approval token bound to an exact action fingerprint."""

    approval_id: str
    request_id: str
    approver: str
    tool_id: str
    action: str
    params: dict[str, Any]
    resource_scope: str
    risk_level: RiskLevel
    fingerprint: str
    granted_at: str
    expires_at: str | None = None
    consumed: bool = False
    revoked: bool = False
    status: ApprovalStatus = ApprovalStatus.APPROVED
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApprovalGate:
    """Evaluates and manages explicit owner approvals."""

    def __init__(
        self,
        trusted_approvers: set[str] | None = None,
        store: Any | None = None,
    ) -> None:
        self.trusted_approvers = trusted_approvers  # None means any non-empty identity string accepted in dev/test
        self.store = store
        self._requests: dict[str, ApprovalRequest] = {}
        self._approvals: dict[str, OwnerApproval] = {}

    def create_request(
        self,
        tool_id: str,
        action: str,
        params: dict[str, Any],
        resource_scope: str = "workspace",
        risk_level: RiskLevel = RiskLevel.R0,
        goal: str = "",
        request_id: str | None = None,
    ) -> ApprovalRequest:
        """Create a structured request for owner approval."""
        r_id = request_id or str(uuid.uuid4())
        fp = compute_action_fingerprint(tool_id, action, params, resource_scope, int(risk_level))
        now_ts = datetime.now(timezone.utc).isoformat()
        req = ApprovalRequest(
            request_id=r_id,
            tool_id=tool_id,
            action=action,
            params=dict(params),
            resource_scope=resource_scope,
            risk_level=risk_level,
            fingerprint=fp,
            created_at=now_ts,
            goal=goal,
            status=ApprovalStatus.PENDING_OWNER_APPROVAL,
        )
        self._requests[r_id] = req
        if self.store is not None:
            self.store.save_request(req)
        return req

    def grant_approval(
        self,
        request: ApprovalRequest,
        approver: str,
        expires_at: str | None = None,
        approval_id: str | None = None,
        notes: str = "",
    ) -> OwnerApproval:
        """Grant owner approval for a specific request."""
        clean_approver = approver.strip()
        if not clean_approver:
            raise ValueError("Approver identity must not be empty")

        if self.trusted_approvers is not None and clean_approver not in self.trusted_approvers:
            raise PermissionError(f"Approver '{clean_approver}' is not in trusted owner identities")

        app_id = approval_id or str(uuid.uuid4())
        now_ts = datetime.now(timezone.utc).isoformat()

        approval = OwnerApproval(
            approval_id=app_id,
            request_id=request.request_id,
            approver=clean_approver,
            tool_id=request.tool_id,
            action=request.action,
            params=dict(request.params),
            resource_scope=request.resource_scope,
            risk_level=request.risk_level,
            fingerprint=request.fingerprint,
            granted_at=now_ts,
            expires_at=expires_at,
            consumed=False,
            revoked=False,
            status=ApprovalStatus.APPROVED,
            notes=notes,
        )
        self._approvals[app_id] = approval
        request.status = ApprovalStatus.APPROVED
        if self.store is not None:
            self.store.save_approval(approval)
            self.store.save_request(request)
        return approval

    def deny_approval(self, request_id: str, reason: str = "Denied by owner") -> None:
        """Explicitly deny an approval request."""
        req = self.get_request(request_id)
        if req:
            req.status = ApprovalStatus.DENIED
            req.metadata["denial_reason"] = reason
            if self.store is not None:
                self.store.save_request(req)

    def evaluate_approval(self, approval_id: str, current_request: ApprovalRequest) -> tuple[bool, str]:
        """Evaluate whether a specific approval token authorizes the current request."""
        approval = self.get_approval(approval_id)
        if not approval:
            return False, f"Approval '{approval_id}' not found"

        if approval.revoked or approval.status == ApprovalStatus.REVOKED:
            return False, "Approval has been revoked by owner"

        if approval.consumed or approval.status == ApprovalStatus.COMPLETED:
            return False, "Approval has already been consumed (one-time use only)"

        # Expiry check
        if approval.expires_at:
            try:
                exp_dt = datetime.fromisoformat(approval.expires_at)
                now_dt = datetime.now(timezone.utc)
                if now_dt > exp_dt:
                    approval.status = ApprovalStatus.EXPIRED
                    return False, f"Approval expired at {approval.expires_at}"
            except ValueError:
                return False, "Approval contains invalid expiry timestamp format"

        # Fingerprint match check (prevents parameter tampering or cross-action replay)
        if approval.fingerprint != current_request.fingerprint:
            return False, "Action fingerprint mismatch: parameters or scope have changed since approval was granted"

        # Tool and risk check
        if approval.tool_id != current_request.tool_id:
            return False, f"Approval is for tool '{approval.tool_id}', not '{current_request.tool_id}'"

        if approval.risk_level != current_request.risk_level:
            return False, "Approval risk level does not match current request risk level"

        return True, "Valid owner approval"

    def consume_approval(self, approval_id: str) -> bool:
        """Mark approval as consumed so it cannot be used a second time."""
        if self.store is not None:
            stored_ok = self.store.consume_approval(approval_id)
            if not stored_ok:
                return False
            # Sync memory
            if approval_id in self._approvals:
                self._approvals[approval_id].consumed = True
                self._approvals[approval_id].status = ApprovalStatus.COMPLETED
            return True

        approval = self._approvals.get(approval_id)
        if not approval or approval.consumed:
            return False
        approval.consumed = True
        approval.status = ApprovalStatus.COMPLETED
        return True

    def revoke_approval(self, approval_id: str, reason: str = "") -> bool:
        """Revoke an approval immediately."""
        if self.store is not None:
            self.store.revoke_approval(approval_id, reason=reason)

        approval = self.get_approval(approval_id)
        if not approval:
            return False
        approval.revoked = True
        approval.status = ApprovalStatus.REVOKED
        approval.notes = f"{approval.notes} [REVOKED: {reason}]".strip()
        return True

    def get_approval(self, approval_id: str) -> OwnerApproval | None:
        if approval_id in self._approvals:
            return self._approvals[approval_id]
        if self.store is not None:
            stored = self.store.get_approval(approval_id)
            if stored is not None:
                self._approvals[approval_id] = stored
                return stored
        return None

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        if request_id in self._requests:
            return self._requests[request_id]
        if self.store is not None:
            stored_req = self.store.get_request(request_id)
            if stored_req is not None:
                self._requests[request_id] = stored_req
                return stored_req
        return None
