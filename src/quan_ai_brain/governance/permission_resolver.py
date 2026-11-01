"""DEOM M4 — PermissionResolver: hợp nhất PolicyEngine + RBAC/ABAC + Approval.

Thiết kế: reports/DEOM_M4_DESIGN.md (§2). Fail-closed tổng:
  1. PolicyEngine (R0–R5, ActionRequest) — R5 BLOCKED dừng ngay.
  2. RBAC 13 quyền seed 3 role: tony / owner / tony-escalate.
  3. ABAC deny-policy thắng ngay nếu match.
  4. R4 (policy → approval_required) không card hợp lệ → APPROVAL_REQUIRED;
     card APPROVED + chưa consumed → consume + ALLOW_WITH_NOTICE.
Bất biến: `approve:action` DENY vĩnh viễn với mọi subject ≠ quanpt1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quan_ai_brain.governance.approval_service import (
    OWNER_ID,
    ApprovalCardError,
    ApprovalCardService,
)
from quan_ai_brain.governance.policy import (
    ActionRequest,
    DecisionStatus,
    PolicyEngine,
    RiskLevel,
)
from quan_ai_brain.security.rbac import (
    ABACEngine,
    AuthorizationEngine,
    RBACEngine,
    Role,
)

# ---------------------------------------------------------------------------
# 13 quyền M1 (doc 2/4): (permission_id, resource, action, risk khi TONY làm)
# ---------------------------------------------------------------------------
PERMISSION_CATALOG: tuple[tuple[str, str, str, RiskLevel], ...] = (
    ("P1", "read:plan", "read", RiskLevel.R0),
    ("P2", "memory", "read", RiskLevel.R0),
    ("P3", "memory", "write", RiskLevel.R2),
    ("P4", "computer_use", "read", RiskLevel.R1),
    ("P5", "computer_use", "act", RiskLevel.R4),
    ("P6", "messages", "read", RiskLevel.R1),
    ("P7", "messages", "send", RiskLevel.R3),
    ("P8", "tasks", "create", RiskLevel.R2),
    ("P9", "tasks", "delete", RiskLevel.R4),
    ("P10", "devices", "control", RiskLevel.R4),
    ("P11", "deploy", "act", RiskLevel.R4),
    ("P12", "config", "write", RiskLevel.R4),
    ("P13", "approve:action", "grant", RiskLevel.R5),
)

# Quyền 1–8: tony có trực tiếp. P5/P9–P12: APPROVAL_REQUIRED. P13: DENY.
TONY_DIRECT = {"P1", "P2", "P3", "P4", "P6", "P7", "P8"}
TONY_APPROVAL_REQUIRED = {"P5", "P9", "P10", "P11", "P12"}
ESCALATED = {"P5", "P9", "P10", "P11", "P12"}


def _build_rbac() -> RBACEngine:
    """Seed 3 role theo ma trận M1. P13 (approve:action) KHÔNG grant cho ai."""
    from quan_ai_brain.security.rbac import Permission

    rbac = RBACEngine()

    def perms(pids: set[str]):
        return [Permission(resource=rid, action=act) for pid, rid, act, _ in PERMISSION_CATALOG if pid in pids]

    rbac.add_role(Role(name="tony", description="TONY base — nhận thức + tác vụ an toàn", permissions=perms(TONY_DIRECT)))
    rbac.add_role(Role(name="tony-escalate", description="TONY khi task R4 đã duyệt — theo scope card", permissions=perms(ESCALATED)))
    rbac.add_role(Role(name="owner", description="Quanpt1 — quyền phê duyệt cuối cùng", permissions=perms({p[0] for p in PERMISSION_CATALOG})))
    rbac.assign_role_to_user("tony", "tony")
    rbac.assign_role_to_user(OWNER_ID, "owner")
    return rbac


@dataclass
class ResolverDecision:
    """Kết quả resolve — status + vết đầy đủ từng lớp."""

    status: str  # ALLOW | ALLOW_WITH_NOTICE | APPROVAL_REQUIRED | BLOCKED
    reason: str
    layers: list[dict[str, Any]] = field(default_factory=list)
    approval_id: str | None = None
    consumed: bool = False

    @property
    def allowed(self) -> bool:
        return self.status in ("ALLOW", "ALLOW_WITH_NOTICE")


class PermissionResolver:
    """Điểm quyết định duy nhất cho 'TONY/agent có được làm X không?'."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        approval_service: ApprovalCardService | None = None,
        abac_engine: ABACEngine | None = None,
        *,
        workspace: str | Any = ".",
        subject_id: str = "tony",
    ) -> None:
        self.policy = policy_engine or PolicyEngine(workspace)
        self.approvals = approval_service or ApprovalCardService(":memory:")
        self.rbac = _build_rbac()
        self.abac = abac_engine or ABACEngine()
        self.authz = AuthorizationEngine(rbac=self.rbac, abac=self.abac)
        self.subject_id = subject_id

    # ------------------------------------------------------------------
    def resolve(
        self,
        *,
        permission_id: str,
        task_id: str = "",
        subject_id: str | None = None,
        environment_attrs: dict[str, Any] | None = None,
        approval_id: str | None = None,
        target_path: str | None = None,
    ) -> ResolverDecision:
        """Resolve một permission. Lớp 1→4 fail-closed. KHÔNG có lối tắt."""
        subject = subject_id or self.subject_id
        perm = next((p for p in PERMISSION_CATALOG if p[0] == permission_id), None)
        if perm is None:
            return ResolverDecision("BLOCKED", f"unknown permission_id {permission_id}")
        _, resource, action, base_risk = perm
        layers: list[dict[str, Any]] = []
        env = environment_attrs or {}

        # ---- Lớp 1: PolicyEngine R0–R5 (ActionRequest thật) ----
        pol = self.policy.authorize(ActionRequest(action=action, risk=base_risk, target_path=target_path))
        layers.append(
            {
                "layer": "policy_engine",
                "status": pol.status.value,
                "risk_level": pol.risk.name,
                "reason": pol.reason,
            }
        )
        if pol.status in (DecisionStatus.BLOCKED, DecisionStatus.DENY):
            return ResolverDecision("BLOCKED", f"policy: {pol.reason}", layers)

        # ---- Lớp 1.5: bất biến approve:action (P13) ----
        if permission_id == "P13" and subject != OWNER_ID:
            return ResolverDecision(
                "BLOCKED", "approve:action is permanently denied to non-owner subjects", layers
            )

        # ---- Lớp 2: RBAC ----
        roles = ["tony"] if subject == "tony" else (["owner"] if subject == OWNER_ID else [])
        rbac_dec = self.authz.check_permission(subject, resource, action, role_names=roles)
        layers.append({"layer": "rbac", "allowed": rbac_dec.allowed, "reason": rbac_dec.reason})
        rbac_granted = rbac_dec.allowed

        # ---- Lớp 3: ABAC deny policy thắng ngay ----
        for pol2 in self.abac.list_policies():
            if pol2.effect == "deny" and pol2.matches({}, {}, env):
                layers.append({"layer": "abac", "matched": pol2.name, "effect": "deny"})
                return ResolverDecision("BLOCKED", f"abac deny: {pol2.name}", layers)

        # ---- Lớp 4: mapping policy status / risk → status ----
        risk = pol.risk
        if rbac_granted and risk in (RiskLevel.R0, RiskLevel.R1, RiskLevel.R2):
            return ResolverDecision("ALLOW", rbac_dec.reason, layers)
        if rbac_granted and risk == RiskLevel.R3:
            return ResolverDecision(
                "APPROVAL_REQUIRED", "R3 requires owner notice-confirmation per M1 matrix", layers
            )
        if not rbac_granted:
            if subject == "tony" and permission_id in TONY_APPROVAL_REQUIRED:
                pass  # tony thiếu role trực tiếp → rơi xuống approval gate
            else:
                return ResolverDecision("BLOCKED", f"rbac: {rbac_dec.reason}", layers)

        # ---- Approval gate: R4 (policy trả approval_required) ----
        if pol.status is not DecisionStatus.APPROVAL_REQUIRED:
            return ResolverDecision(
                "APPROVAL_REQUIRED", f"policy status {pol.status.value} without approval path", layers
            )
        if not approval_id:
            return ResolverDecision(
                "APPROVAL_REQUIRED", "no approval card supplied — request owner decision", layers
            )
        card = self.approvals.get_card(approval_id)
        if card is None:
            return ResolverDecision("BLOCKED", f"approval card {approval_id} not found", layers)
        if card.requested_by != subject and subject != OWNER_ID:
            return ResolverDecision("BLOCKED", f"card belongs to {card.requested_by}", layers)
        if card.state == "APPROVED" and card.consumed_at_utc:
            return ResolverDecision("BLOCKED", "card already consumed — one-time use enforced", layers)
        if card.state != "APPROVED":
            return ResolverDecision("APPROVAL_REQUIRED", f"card state is {card.state}", layers)
        # Consume 1 lần (nonce)
        try:
            self.approvals.consume(approval_id, actor="permission_resolver")
        except ApprovalCardError as exc:
            return ResolverDecision("BLOCKED", f"consume failed: {exc}", layers)
        layers.append({"layer": "approval", "approval_id": approval_id, "consumed": True})
        return ResolverDecision(
            "ALLOW_WITH_NOTICE",
            f"R4 action approved via card {approval_id} (scope: {', '.join(card.scope) or 'unspecified'})",
            layers,
            approval_id=approval_id,
            consumed=True,
        )
