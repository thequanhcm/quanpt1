"""Data models for Self-Learning & Self-Upgrade Engine V1.

Enforces:
1. Candidate knowledge quarantine by default (never auto-trusted).
2. Canonical 17-point UpgradeProposal dossier with pros, cons, diff, and rollback plan.
3. Strict Owner Approval Gates before sandbox testing and software modification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from quan_ai_brain.core.redaction import redact_text, redact_value


class UpgradeProposalStatus(str, Enum):
    DISCOVERED = "discovered"
    PROPOSED = "proposed"
    WAITING_OWNER_REVIEW = "waiting_owner_review"
    APPROVED_FOR_SANDBOX = "approved_for_sandbox"
    SANDBOX_TESTED = "sandbox_tested"
    SECURITY_REVIEWED = "security_reviewed"
    READY_FOR_OWNER_DECISION = "ready_for_owner_decision"
    APPROVED_FOR_APPLY = "approved_for_apply"
    APPLIED = "applied"
    POST_APPLY_VERIFIED = "post_apply_verified"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class LearningGap:
    """Identified weakness, missing capability, or repeating error."""
    gap_id: str
    task_id: str
    description: str
    gap_type: str  # missing_knowledge | repeated_error | procedural_defect | performance_bottleneck
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    severity: int = 1  # 0 to 5
    detected_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "task_id": self.task_id,
            "description": redact_text(self.description),
            "gap_type": self.gap_type,
            "evidence_refs": list(self.evidence_refs),
            "severity": self.severity,
            "detected_at_utc": self.detected_at_utc,
        }


@dataclass(frozen=True)
class ResearchDossier:
    """Documented research findings from authorized sources."""
    research_id: str
    gap_id: str
    question: str
    sources: tuple[dict[str, Any], ...]
    findings: str
    candidate_knowledge_statement: str
    confidence_score: float = 0.5
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_id": self.research_id,
            "gap_id": self.gap_id,
            "question": redact_text(self.question),
            "sources": [redact_value(s) for s in self.sources],
            "findings": redact_text(self.findings),
            "candidate_knowledge_statement": redact_text(self.candidate_knowledge_statement),
            "confidence_score": self.confidence_score,
            "created_at_utc": self.created_at_utc,
        }


@dataclass(frozen=True)
class ExperimentPlan:
    """Bounded, isolated testing plan for a candidate hypothesis."""
    experiment_id: str
    gap_id: str
    hypothesis: str
    target_modules: tuple[str, ...]
    isolation_level: str = "python_sandbox_workspace"
    test_suite_ref: str = ""
    resource_budget_mb: int = 512
    timeout_seconds: int = 60
    rollback_procedure: str = "Revert candidate files and reset isolated sandbox."
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "gap_id": self.gap_id,
            "hypothesis": redact_text(self.hypothesis),
            "target_modules": list(self.target_modules),
            "isolation_level": self.isolation_level,
            "test_suite_ref": self.test_suite_ref,
            "resource_budget_mb": self.resource_budget_mb,
            "timeout_seconds": self.timeout_seconds,
            "rollback_procedure": redact_text(self.rollback_procedure),
            "status": self.status,
        }


@dataclass(frozen=True)
class ExperimentResult:
    """Outcome of an isolated sandbox experiment."""
    experiment_id: str
    success: bool
    baseline_tests_passed: int
    candidate_tests_passed: int
    regressions_detected: int
    measured_metrics: dict[str, Any]
    test_log_summary: str
    completed_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "success": self.success,
            "baseline_tests_passed": self.baseline_tests_passed,
            "candidate_tests_passed": self.candidate_tests_passed,
            "regressions_detected": self.regressions_detected,
            "measured_metrics": redact_value(self.measured_metrics),
            "test_log_summary": redact_text(self.test_log_summary),
            "completed_at_utc": self.completed_at_utc,
        }


@dataclass
class UpgradeProposal:
    """Canonical 17-point software upgrade proposal dossier for Quanpt1.

    Invariant: Brain proposes; Owner Quanpt1 alone decides.
    """
    proposal_id: str
    problem_statement: str
    target_goal: str
    proposed_solution: str
    new_knowledge_refs: list[str]
    expected_benefits: str
    advantages: list[str]
    disadvantages_and_risks: list[str]
    impact_scope: list[str]
    unified_diff: str
    test_results: dict[str, Any]
    security_evaluation: str
    compatibility_assessment: str
    measured_metrics: dict[str, Any]
    rollback_plan: str
    recommendation: str  # apply | experiment_further | defer | reject | keep_status_quo
    confidence_score: float
    uncertainties: list[str]
    status: UpgradeProposalStatus = UpgradeProposalStatus.PROPOSED
    owner_decision: str = "pending_review"
    owner_decision_reason: str = ""
    owner_decision_at_utc: str | None = None
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "problem_statement": redact_text(self.problem_statement),
            "target_goal": redact_text(self.target_goal),
            "proposed_solution": redact_text(self.proposed_solution),
            "new_knowledge_refs": list(self.new_knowledge_refs),
            "expected_benefits": redact_text(self.expected_benefits),
            "advantages": [redact_text(a) for a in self.advantages],
            "disadvantages_and_risks": [redact_text(d) for d in self.disadvantages_and_risks],
            "impact_scope": list(self.impact_scope),
            "unified_diff": self.unified_diff,
            "test_results": redact_value(self.test_results),
            "security_evaluation": redact_text(self.security_evaluation),
            "compatibility_assessment": redact_text(self.compatibility_assessment),
            "measured_metrics": redact_value(self.measured_metrics),
            "rollback_plan": redact_text(self.rollback_plan),
            "recommendation": self.recommendation,
            "confidence_score": self.confidence_score,
            "uncertainties": [redact_text(u) for u in self.uncertainties],
            "status": self.status.value,
            "owner_decision": self.owner_decision,
            "owner_decision_reason": redact_text(self.owner_decision_reason),
            "owner_decision_at_utc": self.owner_decision_at_utc,
            "created_at_utc": self.created_at_utc,
        }

    def explain(self) -> str:
        """Produce an executive briefing in Markdown for Owner review."""
        lines = [
            f"# HỒ SƠ ĐỀ XUẤT NÂNG CẤP PHẦN MỀM: {self.proposal_id}",
            f"- **Trạng thái:** `{self.status.value}` | **Khuyến nghị của Brain:** `{self.recommendation}`",
            f"- **Độ tự tin:** {self.confidence_score * 100:.1f}%",
            f"- **Quyết định của Chủ nhân:** `{self.owner_decision}`",
            "",
            "## 1. Vấn đề & Mục tiêu",
            f"- **Vấn đề:** {self.problem_statement}",
            f"- **Mục tiêu:** {self.target_goal}",
            "",
            "## 2. Giải pháp & Tri thức mới",
            f"- **Phương án:** {self.proposed_solution}",
            f"- **Tri thức sử dụng:** {', '.join(self.new_knowledge_refs) or 'Không có'}",
            "",
            "## 3. Phân tích Hai Mặt (Ưu & Nhược)",
            "### Ưu điểm:",
            *[f"- ✅ {a}" for a in self.advantages],
            "### Nhược điểm & Rủi ro:",
            *[f"- ⚠️ {d}" for d in self.disadvantages_and_risks],
            "",
            "## 4. Phạm vi & Kết quả Thử nghiệm",
            f"- **Phạm vi tác động:** {', '.join(self.impact_scope)}",
            f"- **Kết quả kiểm thử:** Baseline {self.test_results.get('baseline_passed', 0)} pass; Candidate {self.test_results.get('candidate_passed', 0)} pass; Regressions: {self.test_results.get('regressions', 0)}",
            f"- **Đánh giá an ninh:** {self.security_evaluation}",
            f"- **Tương thích ngược:** {self.compatibility_assessment}",
            "",
            "## 5. Phương án Quay lui & Bất định",
            f"- **Phương án rollback:** {self.rollback_plan}",
            "### Điểm còn bất định:",
            *[f"- ❓ {u}" for u in self.uncertainties],
            "",
            "```diff",
            self.unified_diff or "No diff provided.",
            "```",
            "",
            "> **LƯU Ý:** Đề xuất này ở trạng thái chờ phê duyệt từ Quanpt1 trước khi bất kỳ thay đổi nào được áp dụng.",
        ]
        return "\n".join(lines)
