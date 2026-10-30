"""Typed plan objects and validation for QUAN AI BRAIN Planning & Governance.

Sprint 3A: Cognitive Executive Coordinator & Safe Action Planning.
No autonomous executor is included in this sprint.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

from quan_ai_brain.core.redaction import redact_text, redact_value


class TaskStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    READY_FOR_REVIEW = "ready_for_review"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class StepStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    PENDING_APPROVAL = "pending_approval"
    BLOCKED = "blocked"
    READY_FOR_REVIEW = "ready_for_review"


@dataclass(frozen=True)
class TaskStep:
    """Individual action step within a TaskPlan."""
    name: str
    description: str
    expected_output: str
    risk_level: int = 0
    requires_approval: bool = False
    step_id: str = ""
    sequence: int = 1
    preconditions: tuple[str, ...] = field(default_factory=tuple)
    verification_method: str = ""
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    status: StepStatus | str = StepStatus.PROPOSED
    policy_status: str = ""
    policy_reason: str = ""
    target_path: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "sequence": self.sequence,
            "name": redact_text(self.name),
            "description": redact_text(self.description),
            "expected_output": redact_text(self.expected_output),
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "preconditions": [redact_text(p) for p in self.preconditions],
            "verification_method": redact_text(self.verification_method),
            "dependencies": list(self.dependencies),
            "status": self.status.value if isinstance(self.status, StepStatus) else str(self.status),
            "policy_status": self.policy_status,
            "policy_reason": redact_text(self.policy_reason),
            "target_path": self.target_path,
            "warnings": [redact_text(w) for w in self.warnings],
        }


@dataclass
class TaskPlan:
    """Structured, auditable plan produced by Executive Coordinator."""
    goal: str
    steps: list[TaskStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.DRAFT
    metadata: dict[str, Any] = field(default_factory=dict)
    plan_id: str = field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}")
    summary: str = ""
    source: str = "manual"
    warnings: list[str] = field(default_factory=list)
    requires_approval: bool = False
    blocked: bool = False
    memory_refs: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cognitive_state: Any = None

    def validate(self) -> None:
        """Thoroughly validate structure, risk boundaries, and dependency integrity."""
        errors: list[str] = []

        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ValueError("Task plan goal must not be empty")

        if not self.steps:
            raise ValueError("Task plan must contain at least one step")

        step_ids: set[str] = set()
        step_id_list: list[str] = []

        # 1. Step-level validation
        for index, step in enumerate(self.steps, start=1):
            if not step.name.strip() or not step.expected_output.strip():
                raise ValueError(f"Step {index} must have a name and expected output")

            if not isinstance(step.risk_level, int) or step.risk_level not in range(0, 6):
                raise ValueError(f"Step {index} has an invalid risk level: {step.risk_level}")

            # Backward-compatible check: R4/R5 must indicate approval/blocking
            if step.risk_level >= 4 and not (step.requires_approval or step.policy_status in ("blocked", "deny")):
                raise ValueError(f"Step {index} at risk R4/R5 must indicate approval/blocking")

            sid = step.step_id or f"step-{index}"
            if sid in step_ids:
                errors.append(f"Duplicate step ID '{sid}' detected at step {index}")
            step_ids.add(sid)
            step_id_list.append(sid)

            if step.risk_level == 5 or step.policy_status in ("blocked", "deny"):
                self.blocked = True

            if step.requires_approval or step.risk_level == 4 or step.policy_status == "approval_required":
                self.requires_approval = True

        # 2. Dependency validation (must reference existing steps, no self-dependency, no cycles)
        for index, step in enumerate(self.steps, start=1):
            sid = step.step_id or f"step-{index}"
            for dep in step.dependencies:
                if not dep:
                    continue
                if dep == sid:
                    errors.append(f"Step '{sid}' cannot depend on itself")
                elif dep not in step_ids:
                    errors.append(f"Step '{sid}' depends on non-existent step '{dep}'")

        # 3. Cycle detection using DFS
        adj: dict[str, list[str]] = {step.step_id or f"step-{i}": list(step.dependencies) for i, step in enumerate(self.steps, start=1)}
        visited: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited

        def has_cycle(node: str) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if neighbor not in adj:
                    continue
                if visited.get(neighbor, 0) == 1:
                    return True
                if visited.get(neighbor, 0) == 0 and has_cycle(neighbor):
                    return True
            visited[node] = 2
            return False

        for node in adj:
            if visited.get(node, 0) == 0:
                if has_cycle(node):
                    errors.append(f"Cyclic dependency detected involving step '{node}'")
                    break

        if errors:
            self.validation_errors.extend(errors)
            raise ValueError(f"Task plan validation failed: {'; '.join(errors)}")

        # Update overall plan status if blocked or waiting approval
        if self.blocked:
            self.status = TaskStatus.BLOCKED
        elif self.requires_approval:
            self.status = TaskStatus.WAITING_APPROVAL
        elif self.status == TaskStatus.DRAFT:
            self.status = TaskStatus.READY_FOR_REVIEW

    def explain(self) -> str:
        """Produce an explainable, audit-ready summary of the plan."""
        lines: list[str] = [
            f"# BẢN KẾ HOẠCH NHIỆM VỤ: {self.plan_id}",
            f"- **Mục tiêu:** {self.goal}",
            f"- **Tóm tắt:** {self.summary or 'Không có tóm tắt bổ sung'}",
            f"- **Trạng thái kế hoạch:** `{self.status.value}`",
            f"- **Nguồn tạo:** `{self.source}`",
            f"- **Yêu cầu phê duyệt (R4):** {'CÓ' if self.requires_approval else 'KHÔNG'}",
            f"- **Bị chặn an toàn (R5):** {'CÓ (BLOCKED)' if self.blocked else 'KHÔNG'}",
            "",
            "## Danh sách các bước hành động (Execution Steps)",
            "| Thứ tự | ID Bước | Tên bước | Mức rủi ro | Phê duyệt | Kết quả mong đợi | Chính sách |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for idx, s in enumerate(self.steps, start=1):
            sid = s.step_id or f"step-{idx}"
            req_app = "BẮT BUỘC" if s.requires_approval else "Không"
            pol_stat = f"`{s.policy_status}`" if s.policy_status else "`chưa thẩm định`"
            lines.append(
                f"| {s.sequence or idx} | `{sid}` | {s.name} | **R{s.risk_level}** | {req_app} | {s.expected_output} | {pol_stat} |"
            )

        if self.warnings:
            lines.extend([
                "",
                "## Cảnh báo an toàn (Safety Warnings)",
            ])
            for w in self.warnings:
                lines.append(f"- ⚠️ {w}")

        if self.memory_refs:
            lines.extend([
                "",
                "## Tham chiếu tri thức đã sử dụng (Memory Provenance)",
            ])
            for ref in self.memory_refs:
                lines.append(f"- 📚 ID: `{ref}`")

        if self.cognitive_state is not None and hasattr(self.cognitive_state, "evaluate_metacognition"):
            meta = self.cognitive_state.evaluate_metacognition()
            lines.extend([
                "",
                "## Trạng thái nhận thức & Bằng chứng (Cognitive & Metacognitive State)",
                f"- **Khả năng kết luận:** `{'ĐỦ ĐIỀU KIỆN KẾT LUẬN' if meta.can_conclude else 'TỪ CHỐI KẾT LUẬN (ABSTAIN)'}`",
                f"- **Tỷ lệ neo bằng chứng (Grounding Score):** {meta.grounding_score * 100:.1f}%",
            ])
            if meta.abstention_reason:
                lines.append(f"- ⚠️ **Lý do từ chối:** {meta.abstention_reason}")
                lines.append(f"- 🔍 **Kiến nghị bước tiếp theo:** {meta.recommended_next_step}")
            if hasattr(self.cognitive_state, "beliefs") and self.cognitive_state.beliefs:
                verified_b = sum(1 for b in self.cognitive_state.beliefs if hasattr(b, "is_verified_fact") and b.is_verified_fact())
                lines.append(f"- **Nhận định (Beliefs):** {len(self.cognitive_state.beliefs)} tổng số (Đã xác minh: {verified_b})")
            if hasattr(self.cognitive_state, "contradictions") and self.cognitive_state.contradictions:
                lines.append(f"- ⚡ **Mâu thuẫn nguồn (Contradictions):** {len(self.cognitive_state.contradictions)} trường hợp")
            if hasattr(self.cognitive_state, "uncertainties") and self.cognitive_state.uncertainties:
                lines.append(f"- ❓ **Khoảng trống tri thức (Uncertainties):** {len(self.cognitive_state.uncertainties)} điểm chưa biết")

        lines.extend([
            "",
            "> **LƯU Ý QUẢN TRỊ:** Kế hoạch này được lập phục vụ xem xét đánh giá; không có hành động thực tế nào được thực thi trong phiên lập kế hoạch này.",
        ])

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "plan_id": self.plan_id,
            "goal": redact_text(self.goal),
            "summary": redact_text(self.summary),
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "source": self.source,
            "requires_approval": self.requires_approval,
            "blocked": self.blocked,
            "warnings": [redact_text(w) for w in self.warnings],
            "memory_refs": self.memory_refs,
            "validation_errors": self.validation_errors,
            "created_at_utc": self.created_at_utc,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": redact_value(self.metadata),
        }
        if self.cognitive_state is not None and hasattr(self.cognitive_state, "to_dict"):
            data["cognitive_state"] = self.cognitive_state.to_dict()
        return data
