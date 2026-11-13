"""Minimal, deterministic R0-R5 policy gate. No tools are executed here."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path

class RiskLevel(IntEnum):
    R0 = 0  # Read/query operations
    R1 = 1  # Analysis/planning/compute in memory
    R2 = 2  # Safe write within project workspace
    R3 = 3  # Low-impact external action
    R4 = 4  # Significant system change
    R5 = 5  # Prohibited/high-danger operation


class DecisionStatus(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_NOTICE = "allow_with_notice"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"
    DENY = "deny"


@dataclass(frozen=True)
class ActionRequest:
    action: str
    risk: RiskLevel
    target_path: str | Path | None = None


@dataclass(frozen=True)
class PolicyDecision:
    status: DecisionStatus
    risk: RiskLevel
    reason: str
    normalized_target: str | None = None


class PolicyEngine:
    """Policy-only component. It must not run the requested action itself."""

    def __init__(self, workspace: str | Path) -> None:
        from quan_ai_brain.tools.path_guard import PathGuard

        self.workspace = Path(workspace).resolve()
        self.path_guard = PathGuard(self.workspace)

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        risk = RiskLevel(request.risk)
        if risk == RiskLevel.R5:
            return PolicyDecision(DecisionStatus.BLOCKED, risk, "R5 is hard-blocked in this release.")
        if risk == RiskLevel.R4:
            return PolicyDecision(DecisionStatus.APPROVAL_REQUIRED, risk, "Explicit owner approval is required; no executor is provided.")
        if risk == RiskLevel.R3:
            # TASK-AGENTIC-SEC-1 Slice (c): Lethal Trifecta check (slide 13).
            # Mô tả action hội đủ 3 cờ (dữ liệu riêng tư + nội dung không tin cậy +
            # egress ngoài) → bắt buộc phê duyệt kể cả R3.
            try:
                from quan_ai_brain.security.audit_sources import record_trifecta_event
                from quan_ai_brain.security.trifecta_guard import evaluate_task
                desc = request.action or ""
                _tri = evaluate_task(desc, task_class="AUTO")
                if _tri.flags.lethal:
                    record_trifecta_event(desc, "R3", "APPROVAL_REQUIRED", _tri.flags.count)
                    return PolicyDecision(
                        DecisionStatus.APPROVAL_REQUIRED, risk,
                        f"Lethal Trifecta ({_tri.flags.count}/3 cờ): action mô tả "
                        f"private_data + untrusted_content + external_egress — "
                        f"bắt buộc phê duyệt owner (slide 13).",
                    )
            except Exception:
                pass  # trifecta fail-open: policy gate gốc vẫn hoạt động
            return PolicyDecision(DecisionStatus.ALLOW_WITH_NOTICE, risk, "Low-impact external action would require notice and a separately authorized executor.")
        if risk == RiskLevel.R2:
            if request.target_path is None:
                return PolicyDecision(DecisionStatus.DENY, risk, "R2 write actions must declare a workspace-relative target path.")
            from quan_ai_brain.tools.path_guard import PathOutsideWorkspaceError

            try:
                target = self.path_guard.resolve(request.target_path)
            except (PathOutsideWorkspaceError, ValueError) as exc:
                return PolicyDecision(DecisionStatus.DENY, risk, f"Workspace path check failed: {exc}")
            return PolicyDecision(DecisionStatus.ALLOW, risk, "Workspace-only write is permitted by policy; executor must still validate the operation.", str(target))
        return PolicyDecision(DecisionStatus.ALLOW, risk, "Read/analysis action permitted by policy; no execution is performed by this gate.")
