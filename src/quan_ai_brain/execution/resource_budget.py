"""Operating System Resource Budget Policy and Enforcement for QUAN AI BRAIN.

Sprint 6: OS Resource Budget Policy & Validation.
Enforces multi-dimensional resource bounds on execution staging requests.
Prevents runaway processes, resource exhaustion, and unauthorized privilege expansion.

Note on Enforcement Boundaries:
1. Application-Level Validation: Implemented here via ResourceBudgetValidator.
2. OS-Level Kernel Enforcement: Future production execution runner will bind these
   parameters to Windows Job Objects (JOB_OBJECT_LIMIT_*) and AppContainer tokens.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from quan_ai_brain.core.redaction import redact_value


class NetworkPolicy(str, Enum):
    BLOCKED = "BLOCKED"                 # No outbound network access permitted
    LOCALHOST_ONLY = "LOCALHOST_ONLY"   # Loopback only (127.0.0.1 / localhost for Ollama)
    RESTRICTED = "RESTRICTED"           # Explicit whitelist only (disabled in Sprint 6)


@dataclass
class ResourceBudget:
    """Resource allocation limits for a task or execution step."""

    max_runtime_seconds: float = 30.0
    max_memory_mb: int = 512
    max_cpu_time_seconds: float = 10.0
    max_output_bytes: int = 102400  # 100 KB limit matching safe tool baseline
    max_child_processes: int = 0    # Strictly 0 in staging/inert mode
    max_tool_calls: int = 1
    max_retries: int = 0
    network_policy: NetworkPolicy = NetworkPolicy.BLOCKED
    allowed_workspace_scope: str = "workspace"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["network_policy"] = self.network_policy.value
        data["metadata"] = redact_value(self.metadata)
        return data


@dataclass
class ResourceBudgetPolicy:
    """System-wide ceilings that no execution budget may exceed."""

    ceiling_max_runtime_seconds: float = 300.0   # 5 minutes maximum
    ceiling_max_memory_mb: int = 2048            # 2 GB maximum
    ceiling_max_cpu_time_seconds: float = 60.0   # 60s CPU time maximum
    ceiling_max_output_bytes: int = 10485760     # 10 MB maximum
    ceiling_max_child_processes: int = 0         # 0 in inert staging; max 1 in future production
    ceiling_max_tool_calls: int = 5              # 5 recursive calls maximum
    ceiling_max_retries: int = 2                 # 2 retries maximum
    allowed_network_policies: tuple[NetworkPolicy, ...] = (
        NetworkPolicy.BLOCKED,
        NetworkPolicy.LOCALHOST_ONLY,
    )


class ResourceBudgetValidator:
    """Validates execution budgets against system policy ceilings, delegation bounds, and parent tasks."""

    def __init__(self, policy: ResourceBudgetPolicy | None = None) -> None:
        self.policy = policy or ResourceBudgetPolicy()

    def validate_budget(self, budget: ResourceBudget) -> tuple[bool, str]:
        """Validate that a budget has positive values and does not exceed system ceilings."""
        # Check non-negative and positive bounds
        if budget.max_runtime_seconds <= 0:
            return False, f"max_runtime_seconds must be positive, got {budget.max_runtime_seconds}"
        if budget.max_memory_mb <= 0:
            return False, f"max_memory_mb must be positive, got {budget.max_memory_mb}"
        if budget.max_cpu_time_seconds <= 0:
            return False, f"max_cpu_time_seconds must be positive, got {budget.max_cpu_time_seconds}"
        if budget.max_output_bytes <= 0:
            return False, f"max_output_bytes must be positive, got {budget.max_output_bytes}"
        if budget.max_child_processes < 0:
            return False, f"max_child_processes cannot be negative, got {budget.max_child_processes}"
        if budget.max_tool_calls < 1:
            return False, f"max_tool_calls must be at least 1, got {budget.max_tool_calls}"
        if budget.max_retries < 0:
            return False, f"max_retries cannot be negative, got {budget.max_retries}"

        # Enforce system ceiling limits
        if budget.max_runtime_seconds > self.policy.ceiling_max_runtime_seconds:
            return (
                False,
                f"max_runtime_seconds {budget.max_runtime_seconds} exceeds system ceiling ({self.policy.ceiling_max_runtime_seconds}s)",
            )
        if budget.max_memory_mb > self.policy.ceiling_max_memory_mb:
            return (
                False,
                f"max_memory_mb {budget.max_memory_mb} exceeds system ceiling ({self.policy.ceiling_max_memory_mb}MB)",
            )
        if budget.max_cpu_time_seconds > self.policy.ceiling_max_cpu_time_seconds:
            return (
                False,
                f"max_cpu_time_seconds {budget.max_cpu_time_seconds} exceeds system ceiling ({self.policy.ceiling_max_cpu_time_seconds}s)",
            )
        if budget.max_output_bytes > self.policy.ceiling_max_output_bytes:
            return (
                False,
                f"max_output_bytes {budget.max_output_bytes} exceeds system ceiling ({self.policy.ceiling_max_output_bytes} bytes)",
            )
        if budget.max_child_processes > self.policy.ceiling_max_child_processes:
            return (
                False,
                f"max_child_processes {budget.max_child_processes} exceeds system ceiling ({self.policy.ceiling_max_child_processes})",
            )
        if budget.max_tool_calls > self.policy.ceiling_max_tool_calls:
            return (
                False,
                f"max_tool_calls {budget.max_tool_calls} exceeds system ceiling ({self.policy.ceiling_max_tool_calls})",
            )
        if budget.max_retries > self.policy.ceiling_max_retries:
            return (
                False,
                f"max_retries {budget.max_retries} exceeds system ceiling ({self.policy.ceiling_max_retries})",
            )
        if budget.network_policy not in self.policy.allowed_network_policies:
            return (
                False,
                f"network_policy '{budget.network_policy}' is not allowed by policy; permitted: {[p.value for p in self.policy.allowed_network_policies]}",
            )

        return True, "Resource budget is valid and within system ceilings"

    def validate_against_parent(
        self,
        child_budget: ResourceBudget,
        parent_budget: ResourceBudget,
    ) -> tuple[bool, str]:
        """Monotonic containment: Child tasks cannot inherit wider budgets than their parent task."""
        if child_budget.max_runtime_seconds > parent_budget.max_runtime_seconds:
            return (
                False,
                f"Child task runtime ({child_budget.max_runtime_seconds}s) exceeds parent budget ({parent_budget.max_runtime_seconds}s)",
            )
        if child_budget.max_memory_mb > parent_budget.max_memory_mb:
            return (
                False,
                f"Child task memory ({child_budget.max_memory_mb}MB) exceeds parent budget ({parent_budget.max_memory_mb}MB)",
            )
        if child_budget.max_cpu_time_seconds > parent_budget.max_cpu_time_seconds:
            return (
                False,
                f"Child task CPU time ({child_budget.max_cpu_time_seconds}s) exceeds parent budget ({parent_budget.max_cpu_time_seconds}s)",
            )
        if child_budget.max_output_bytes > parent_budget.max_output_bytes:
            return (
                False,
                f"Child task output ({child_budget.max_output_bytes} bytes) exceeds parent budget ({parent_budget.max_output_bytes} bytes)",
            )
        if child_budget.max_child_processes > parent_budget.max_child_processes:
            return (
                False,
                f"Child task child processes ({child_budget.max_child_processes}) exceeds parent budget ({parent_budget.max_child_processes})",
            )
        if child_budget.max_tool_calls > parent_budget.max_tool_calls:
            return (
                False,
                f"Child task tool calls ({child_budget.max_tool_calls}) exceeds parent budget ({parent_budget.max_tool_calls})",
            )
        if child_budget.max_retries > parent_budget.max_retries:
            return (
                False,
                f"Child task retries ({child_budget.max_retries}) exceeds parent budget ({parent_budget.max_retries})",
            )

        return True, "Child budget is monotonically contained within parent budget"

    def validate_against_grant(
        self,
        budget: ResourceBudget,
        grant: Any,
    ) -> tuple[bool, str]:
        """Ensure budget does not violate delegation grant bounds."""
        if grant is None:
            return True, "No delegation grant constraints applied"

        # If grant specifies maximum calls, check tool calls
        if hasattr(grant, "max_calls") and grant.max_calls is not None:
            if budget.max_tool_calls > grant.max_calls:
                return (
                    False,
                    f"Requested tool calls ({budget.max_tool_calls}) exceeds delegation grant max_calls ({grant.max_calls})",
                )

        return True, "Budget complies with delegation grant boundaries"

    def prevent_llm_self_escalation(
        self,
        requested_budget: ResourceBudget,
        base_budget: ResourceBudget,
        requested_by_llm: bool = False,
    ) -> tuple[bool, str]:
        """Prevent an LLM from expanding resource limits autonomously."""
        if not requested_by_llm:
            return True, "Budget request is from an authorized human caller"

        # Check if any limit was escalated
        if (
            requested_budget.max_runtime_seconds > base_budget.max_runtime_seconds
            or requested_budget.max_memory_mb > base_budget.max_memory_mb
            or requested_budget.max_cpu_time_seconds > base_budget.max_cpu_time_seconds
            or requested_budget.max_output_bytes > base_budget.max_output_bytes
            or requested_budget.max_child_processes > base_budget.max_child_processes
            or requested_budget.max_tool_calls > base_budget.max_tool_calls
            or requested_budget.max_retries > base_budget.max_retries
        ):
            return False, "LLM self-escalation of resource budget is strictly prohibited; requires explicit owner approval"

        return True, "No unauthorized self-escalation detected"
