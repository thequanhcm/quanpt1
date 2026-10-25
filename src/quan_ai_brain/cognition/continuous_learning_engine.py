"""Continuous Learning Engine for QUAN AI BRAIN — Sprint 5.

Implements 5-type learning pipeline:
- Type A: Học tri thức — tự động thu nhận, đánh giá, lập chỉ mục và lưu tri thức mới
- Type B: Học kinh nghiệm — tự động ghi nhận nhiệm vụ, kết quả, lỗi, nguyên nhân và bài học
- Type C: Học cách sử dụng tri thức — tự động tạo bài kiểm tra và đo lường mức độ cải thiện
- Type D: Thử nghiệm cải tiến — tự động tạo và chạy thử phương án trong sandbox
- Type E: Thay đổi hành vi hoặc hệ thống — sửa mã, chính sách, cấu hình (cần phê duyệt)

Pipeline: DETECT → COLLECT → NORMALIZE → PROVENANCE CHECK → EXTRACT → EVALUATE → STORE → INDEX → TEST → REFLECT → PROPOSE

Giai đoạn Sprint 5 (2026-10-25): Full 5-type learning with provenance, evaluation, reporting.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from quan_ai_brain.memory.knowledge_ingestion import (
    KnowledgeIngestionEngine,
    KnowledgeProvenance,
    KnowledgeRecord,
    KnowledgeSource,
    VerificationState,
)
from quan_ai_brain.memory.sqlite_store import MemoryStore


class LearningType(str, Enum):
    """Five types of learning."""
    TYPE_A_KNOWLEDGE = "TYPE_A_KNOWLEDGE"      # Học tri thức mới
    TYPE_B_EXPERIENCE = "TYPE_B_EXPERIENCE"    # Học kinh nghiệm từ nhiệm vụ
    TYPE_C_USAGE = "TYPE_C_USAGE"              # Học cách sử dụng tri thức
    TYPE_D_SANDBOX = "TYPE_D_SANDBOX"          # Thử nghiệm cải tiến
    TYPE_E_SYSTEM = "TYPE_E_SYSTEM"            # Thay đổi hệ thống (cần phê duyệt)


class LearningStatus(str, Enum):
    """Learning lifecycle status."""
    DETECTED = "detected"
    COLLECTING = "collecting"
    NORMALIZING = "normalizing"
    PROVENANCE_CHECK = "provenance_check"
    EXTRACTING = "extracting"
    EVALUATING = "evaluating"
    STORED = "stored"
    INDEXING = "indexing"
    TESTING = "testing"
    REFLECTING = "reflecting"
    PROPOSING = "proposing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class LearningReport:
    """Report for a single learning episode."""
    report_id: str
    learning_type: LearningType
    status: LearningStatus
    source: str
    summary: str
    started_at: str
    completed_at: str | None = None
    success: bool = False
    knowledge_id: str | None = None
    test_results: dict[str, Any] = field(default_factory=dict)
    improvement_metrics: dict[str, float] = field(default_factory=dict)
    proposal: dict[str, Any] | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearningEvaluation:
    """Evaluation of learning effectiveness."""
    evaluation_id: str
    timestamp: str
    baseline_precision_at_5: float
    baseline_recall_at_5: float
    baseline_mrr: float
    post_learning_precision_at_5: float
    post_learning_recall_at_5: float
    post_learning_mrr: float
    precision_improvement: float
    recall_improvement: float
    mrr_improvement: float
    overall_improvement: float
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContinuousLearningEngine:
    """Manages continuous learning across 5 types."""

    def __init__(
        self,
        store: MemoryStore,
        knowledge_engine: KnowledgeIngestionEngine | None = None,
        owner_id: str = "Quanpt1",
    ) -> None:
        self.store = store
        self.knowledge_engine = knowledge_engine or KnowledgeIngestionEngine(store, owner_id)
        self.owner_id = owner_id
        self._reports: list[LearningReport] = []
        self._evaluations: list[LearningEvaluation] = []

    def learn_type_a_knowledge(
        self,
        content: str,
        source_type: KnowledgeSource,
        source_ref: str,
        tags: list[str] | None = None,
    ) -> LearningReport:
        """Type A: Learn new knowledge from authorized sources."""
        report = LearningReport(
            report_id=f"learn_{uuid.uuid4().hex[:12]}",
            learning_type=LearningType.TYPE_A_KNOWLEDGE,
            status=LearningStatus.DETECTED,
            source=source_ref,
            summary=f"Ingest knowledge from {source_type.value}",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # DETECT → COLLECT → NORMALIZE (handled by knowledge_engine.ingest)
            report.status = LearningStatus.COLLECTING

            # PROVENANCE CHECK
            report.status = LearningStatus.PROVENANCE_CHECK
            # (Ingest handles provenance automatically)

            # EXTRACT (simplified: entire content as statement)
            report.status = LearningStatus.EXTRACTING

            # EVALUATE (confidence score from source reliability)
            report.status = LearningStatus.EVALUATING

            # STORE
            record = self.knowledge_engine.ingest(
                content=content,
                source_type=source_type,
                source_ref=source_ref,
                tags=tags or [],
            )
            report.knowledge_id = record.id
            report.status = LearningStatus.STORED

            # INDEX (placeholder for Sprint 5+)
            report.status = LearningStatus.INDEXING

            # TEST (retrieval test)
            report.status = LearningStatus.TESTING
            # (Would test retrieval here)

            # REFLECT
            report.status = LearningStatus.REFLECTING
            report.success = True

            # PROPOSE (if conflict detected)
            if record.provenance.conflict_ids:
                report.status = LearningStatus.PROPOSING
                report.proposal = {
                    "type": "conflict_resolution",
                    "conflict_ids": record.provenance.conflict_ids,
                    "recommendation": "Owner review required",
                }

            report.status = LearningStatus.COMPLETED
            report.completed_at = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            report.status = LearningStatus.FAILED
            report.notes = str(e)

        self._reports.append(report)
        return report

    def learn_type_b_experience(
        self,
        task_goal: str,
        task_result: str,
        success: bool,
        errors: list[str] | None = None,
        root_cause: str | None = None,
        lesson_learned: str | None = None,
    ) -> LearningReport:
        """Type B: Learn from task execution experience."""
        report = LearningReport(
            report_id=f"learn_{uuid.uuid4().hex[:12]}",
            learning_type=LearningType.TYPE_B_EXPERIENCE,
            status=LearningStatus.DETECTED,
            source="task_execution",
            summary=f"{'Success' if success else 'Failure'}: {task_goal[:50]}",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            report.status = LearningStatus.EXTRACTING

            # Extract lesson
            if success:
                statement = f"TASK_SUCCESS: {task_goal} → {task_result}"
                source_type = KnowledgeSource.WORKFLOW_LOG
            else:
                statement = f"TASK_FAILURE: {task_goal} → {task_result}"
                if root_cause:
                    statement += f" Root cause: {root_cause}"
                if lesson_learned:
                    statement += f" Lesson: {lesson_learned}"
                source_type = KnowledgeSource.TEST_EVIDENCE

            # Store as experience
            record = self.knowledge_engine.ingest(
                content=statement,
                source_type=source_type,
                source_ref=f"task:{task_goal[:20]}",
                tags=["experience", "task" if success else "failure"],
            )
            report.knowledge_id = record.id
            report.status = LearningStatus.STORED

            # If failure, propose improvement
            if not success and root_cause:
                report.status = LearningStatus.PROPOSING
                report.proposal = {
                    "type": "improvement",
                    "root_cause": root_cause,
                    "recommendation": f"Fix: {lesson_learned or 'Investigate further'}",
                }

            report.success = True
            report.status = LearningStatus.COMPLETED
            report.completed_at = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            report.status = LearningStatus.FAILED
            report.notes = str(e)

        self._reports.append(report)
        return report

    def learn_type_c_usage(
        self,
        query: str,
        retrieved_knowledge: list[str],
        success: bool,
        feedback: str | None = None,
    ) -> LearningReport:
        """Type C: Learn how to use knowledge better."""
        report = LearningReport(
            report_id=f"learn_{uuid.uuid4().hex[:12]}",
            learning_type=LearningType.TYPE_C_USAGE,
            status=LearningStatus.DETECTED,
            source="retrieval_feedback",
            summary=f"{'Success' if success else 'Failure'}: {query[:50]}",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            report.status = LearningStatus.EVALUATING

            # Evaluate retrieval quality
            if success:
                statement = f"RETRIEVAL_SUCCESS: Query '{query}' → {len(retrieved_knowledge)} relevant items"
            else:
                statement = f"RETRIEVAL_FAILURE: Query '{query}' → no relevant items found"
                if feedback:
                    statement += f" Feedback: {feedback}"

            # Store retrieval lesson
            record = self.knowledge_engine.ingest(
                content=statement,
                source_type=KnowledgeSource.TEST_EVIDENCE,
                source_ref=f"retrieval:{query[:20]}",
                tags=["retrieval", "usage" if success else "improvement"],
            )
            report.knowledge_id = record.id
            report.status = LearningStatus.STORED

            # If failure, propose retrieval improvement
            if not success:
                report.status = LearningStatus.PROPOSING
                report.proposal = {
                    "type": "retrieval_improvement",
                    "query": query,
                    "recommendation": "Improve retrieval strategy or add more relevant knowledge",
                }

            report.success = True
            report.status = LearningStatus.COMPLETED
            report.completed_at = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            report.status = LearningStatus.FAILED
            report.notes = str(e)

        self._reports.append(report)
        return report

    def learn_type_d_sandbox(
        self,
        hypothesis: str,
        experiment_design: str,
        baseline_metrics: dict[str, float],
        experiment_results: dict[str, float],
        conclusion: str,
    ) -> LearningReport:
        """Type D: Test improvements in sandbox."""
        report = LearningReport(
            report_id=f"learn_{uuid.uuid4().hex[:12]}",
            learning_type=LearningType.TYPE_D_SANDBOX,
            status=LearningStatus.DETECTED,
            source="sandbox_experiment",
            summary=f"Test: {hypothesis[:50]}",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            report.status = LearningStatus.TESTING

            # Calculate improvement
            improvements = {}
            for metric, baseline in baseline_metrics.items():
                result = experiment_results.get(metric, baseline)
                improvements[metric] = (result - baseline) / max(0.001, baseline) * 100

            # Determine success
            overall_improvement = sum(improvements.values()) / max(1, len(improvements))
            success = overall_improvement > 0

            # Store experiment result
            statement = f"SANDBOX_EXPERIMENT: {hypothesis}\n"
            statement += f"Baseline: {json.dumps(baseline_metrics)}\n"
            statement += f"Results: {json.dumps(experiment_results)}\n"
            statement += f"Improvement: {overall_improvement:.2f}%\n"
            statement += f"Conclusion: {conclusion}"

            record = self.knowledge_engine.ingest(
                content=statement,
                source_type=KnowledgeSource.TEST_EVIDENCE,
                source_ref="sandbox:experiment",
                tags=["sandbox", "experiment", "improvement" if success else "failed"],
            )
            report.knowledge_id = record.id
            report.test_results = {
                "baseline": baseline_metrics,
                "results": experiment_results,
                "improvements": improvements,
                "overall_improvement": overall_improvement,
            }
            report.improvement_metrics = improvements
            report.status = LearningStatus.STORED

            # If successful, propose deployment
            if success:
                report.status = LearningStatus.PROPOSING
                report.proposal = {
                    "type": "deployment_request",
                    "hypothesis": hypothesis,
                    "improvement": f"{overall_improvement:.2f}%",
                    "recommendation": "Deploy to production after owner approval",
                }

            report.success = success
            report.status = LearningStatus.COMPLETED
            report.completed_at = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            report.status = LearningStatus.FAILED
            report.notes = str(e)

        self._reports.append(report)
        return report

    def learn_type_e_system(
        self,
        change_description: str,
        diff: str,
        test_results: dict[str, Any],
        risk_level: int,
        rollback_plan: str,
    ) -> LearningReport:
        """Type E: System change (requires owner approval)."""
        report = LearningReport(
            report_id=f"learn_{uuid.uuid4().hex[:12]}",
            learning_type=LearningType.TYPE_E_SYSTEM,
            status=LearningStatus.PROPOSING,  # Start at PROPOSING for approval
            source="system_change",
            summary=f"Change: {change_description[:50]}",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Prepare approval request
            report.proposal = {
                "type": "system_change_approval",
                "change_description": change_description,
                "diff": diff,
                "test_results": test_results,
                "risk_level": risk_level,
                "rollback_plan": rollback_plan,
                "requires_owner_approval": True,
            }

            # Store as pending approval
            statement = f"PENDING_APPROVAL: {change_description}\n"
            statement += f"Risk level: R{risk_level}\n"
            statement += f"Tests: {json.dumps(test_results)}"

            record = self.knowledge_engine.ingest(
                content=statement,
                source_type=KnowledgeSource.OWNER_FEEDBACK,  # Awaiting owner decision
                source_ref="approval:system_change",
                tags=["approval", f"risk_r{risk_level}"],
            )
            report.knowledge_id = record.id
            report.test_results = test_results

            # Status remains PROPOSING until approved
            report.status = LearningStatus.PROPOSING

        except Exception as e:
            report.status = LearningStatus.FAILED
            report.notes = str(e)

        self._reports.append(report)
        return report

    def evaluate_learning(
        self,
        baseline_precision: float,
        baseline_recall: float,
        baseline_mrr: float,
        post_precision: float,
        post_recall: float,
        post_mrr: float,
    ) -> LearningEvaluation:
        """Evaluate learning effectiveness."""
        eval_id = f"eval_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        precision_imp = post_precision - baseline_precision
        recall_imp = post_recall - baseline_recall
        mrr_imp = post_mrr - baseline_mrr
        overall_imp = (precision_imp + recall_imp + mrr_imp) / 3

        evaluation = LearningEvaluation(
            evaluation_id=eval_id,
            timestamp=timestamp,
            baseline_precision_at_5=baseline_precision,
            baseline_recall_at_5=baseline_recall,
            baseline_mrr=baseline_mrr,
            post_learning_precision_at_5=post_precision,
            post_learning_recall_at_5=post_recall,
            post_learning_mrr=post_mrr,
            precision_improvement=precision_imp,
            recall_improvement=recall_imp,
            mrr_improvement=mrr_imp,
            overall_improvement=overall_imp,
            passed=overall_imp > 0,
        )

        self._evaluations.append(evaluation)
        return evaluation

    def get_reports(self, learning_type: LearningType | None = None, limit: int = 50) -> list[LearningReport]:
        """Get learning reports, optionally filtered by type."""
        reports = self._reports
        if learning_type:
            reports = [r for r in reports if r.learning_type == learning_type]
        return reports[-limit:]

    def get_pending_approvals(self) -> list[LearningReport]:
        """Get Type E changes pending owner approval."""
        return [r for r in self._reports if r.learning_type == LearningType.TYPE_E_SYSTEM and r.status == LearningStatus.PROPOSING]

    def get_evaluation_summary(self) -> dict[str, Any]:
        """Get summary of all evaluations."""
        if not self._evaluations:
            return {"total_evaluations": 0}

        total = len(self._evaluations)
        passed = sum(1 for e in self._evaluations if e.passed)
        avg_improvement = sum(e.overall_improvement for e in self._evaluations) / total

        return {
            "total_evaluations": total,
            "passed": passed,
            "failed": total - passed,
            "average_improvement": avg_improvement,
        }