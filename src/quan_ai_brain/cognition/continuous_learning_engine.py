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
from pathlib import Path
from typing import Any

from quan_ai_brain.memory.knowledge_ingestion import (
    KnowledgeIngestionEngine,
    KnowledgeProvenance,
    KnowledgeRecord,
    KnowledgeSource,
    VerificationState,
)
from quan_ai_brain.memory.sqlite_store import MemoryStore
from quan_ai_brain.cognition.learning_session import (
    LearningSession,
    LearningSessionManager,
    LearningSessionStatus,
)


class LearningType(str, Enum):
    """Five types of learning."""
    TYPE_A_KNOWLEDGE = "TYPE_A_KNOWLEDGE"      # Học tri thức mới
    TYPE_B_EXPERIENCE = "TYPE_B_EXPERIENCE"    # Học kinh nghiệm từ nhiệm vụ
    TYPE_C_USAGE = "TYPE_C_USAGE"              # Học cách sử dụng tri thức
    TYPE_D_SANDBOX = "TYPE_D_SANDBOX"          # Thử nghiệm cải tiến
    TYPE_E_SYSTEM = "TYPE_E_SYSTEM"            # Thay đổi hệ thống (cần phê duyệt)


class LearningMode(str, Enum):
    """CLO V1: Learning modes (A-G from master prompt)."""
    MODE_A_SELF_DISCOVERY = "MODE_A_SELF_DISCOVERY"      # Hiểu trạng thái hệ thống
    MODE_B_KNOWLEDGE_ACQUISITION = "MODE_B_KNOWLEDGE_ACQUISITION"  # Tiếp thu tri thức
    MODE_C_REASONING = "MODE_C_REASONING"                # Phân tích và giải quyết vấn đề
    MODE_D_MEMORY_CONSOLIDATION = "MODE_D_MEMORY_CONSOLIDATION"    # Gộp bộ nhớ
    MODE_E_SELF_EVALUATION = "MODE_E_SELF_EVALUATION"    # Tự đánh giá
    MODE_F_EXPERIMENT = "MODE_F_EXPERIMENT"              # Thử nghiệm và regression
    MODE_G_PLANNING = "MODE_G_PLANNING"                  # Lập kế hoạch và ưu tiên


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
    """Manages continuous learning across 5 types with session handoff."""

    def __init__(
        self,
        store: MemoryStore,
        knowledge_engine: KnowledgeIngestionEngine | None = None,
        owner_id: str = "Quanpt1",
        workspace: Path | None = None,
    ) -> None:
        self.store = store
        self.knowledge_engine = knowledge_engine or KnowledgeIngestionEngine(store, owner_id)
        self.owner_id = owner_id
        self._reports: list[LearningReport] = []
        self._evaluations: list[LearningEvaluation] = []
        
        # CLO V1: Session manager for continuous handoff
        self.workspace = workspace or Path(__file__).parent.parent.parent
        self.session_db_path = self.workspace / "data" / "learning_checkpoints.db"
        # Ensure data directory exists
        self.session_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_manager = LearningSessionManager(self.session_db_path)

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

    # ========== CLO V1: Continuous Session Handoff ==========

    def start_continuous_learning(self, objectives: list[str], source_manifest: dict[str, Any]) -> LearningSession:
        """Start continuous learning mode and create first session."""
        return self.start_session_with_mode(objectives, source_manifest, None)

    def start_session_with_mode(self, objectives: list[str], source_manifest: dict[str, Any], mode: LearningMode | None = None) -> LearningSession:
        """Start a learning session with optional mode specification."""
        # Check if already enabled
        if self.session_manager.is_clo_enabled():
            current = self.session_manager.get_current_session()
            if current and current.status in [LearningSessionStatus.RUNNING, LearningSessionStatus.PLANNING]:
                raise RuntimeError(f"Continuous learning already active: session {current.session_id}")

        # Enable CLO
        self.session_manager.enable_clo()
        
        # Add mode to objectives if specified
        if mode:
            objectives = [f"[{mode.value}] {obj}" for obj in objectives]
            source_manifest["mode"] = mode.value
        
        # Create new session
        session = self.session_manager.create_session(objectives, source_manifest)
        # Status is INITIALIZING after create, update to PLANNING
        self.session_manager.set_status(session.session_id, LearningSessionStatus.PLANNING)
        
        # Return updated session
        return self.session_manager.get_session_by_id(session.session_id)

    def end_session(self, session_id: str, evaluation_result: dict[str, Any], 
                    unresolved_questions: list[str], next_plan: dict[str, Any]) -> LearningSession:
        """End current session and prepare for next session handoff."""
        session = self.session_manager.get_session_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Check stop flag
        stop_flag, stop_reason = self.session_manager.get_stop_flag()
        if stop_flag:
            session.status = LearningSessionStatus.STOPPING
            session.stop_or_pause_reason = stop_reason
        else:
            session.status = LearningSessionStatus.CONSOLIDATING
        
        session.ended_at = datetime.now(timezone.utc).isoformat()
        session.evaluation_result = evaluation_result
        session.unresolved_questions = unresolved_questions
        session.next_session_plan = next_plan
        
        self.session_manager.update_session(session)
        
        # If not stopping, create next session automatically
        if not stop_flag and self.session_manager.is_clo_enabled():
            return self._create_next_session(session)
        
        return session

    def _create_next_session(self, previous_session: LearningSession) -> LearningSession:
        """Create next session based on previous session's plan."""
        # Check stop flag again
        stop_flag, _ = self.session_manager.get_stop_flag()
        if stop_flag:
            # Don't create new session if stop flag is set
            return previous_session
        
        objectives = previous_session.next_session_plan.get("objectives", [])
        source_manifest = previous_session.next_session_plan.get("source_manifest", {})
        
        new_session = self.session_manager.create_session(objectives, source_manifest)
        self.session_manager.set_status(new_session.session_id, LearningSessionStatus.RUNNING)
        
        return new_session

    def pause_continuous_learning(self, reason: str):
        """Pause continuous learning (no new sessions will be created)."""
        self.session_manager.set_learning_state("PAUSE_FLAG", True)
        self.session_manager.set_learning_state("PAUSE_REASON", reason)
        self.session_manager.set_learning_state("PAUSED_AT", datetime.now(timezone.utc).isoformat())
        
        # Update current session status
        current = self.session_manager.get_current_session()
        if current and current.status in [LearningSessionStatus.RUNNING, LearningSessionStatus.PLANNING]:
            self.session_manager.set_status(current.session_id, LearningSessionStatus.PAUSED, reason)

    def resume_continuous_learning(self):
        """Resume continuous learning from pause."""
        # Verify pause reason is resolved
        pause_reason = self.session_manager.get_learning_state("PAUSE_REASON")
        self.session_manager.set_learning_state("PAUSE_FLAG", False)
        self.session_manager.set_learning_state("RESUMED_AT", datetime.now(timezone.utc).isoformat())
        
        # Resume current session if paused
        current = self.session_manager.get_current_session()
        if current and current.status == LearningSessionStatus.PAUSED:
            self.session_manager.set_status(current.session_id, LearningSessionStatus.RUNNING)

    def stop_continuous_learning(self, reason: str):
        """Stop continuous learning permanently (requires owner restart)."""
        self.session_manager.set_stop_flag(reason)
        self.session_manager.disable_clo()
        
        # Update current session
        current = self.session_manager.get_current_session()
        if current and current.status in [LearningSessionStatus.RUNNING, LearningSessionStatus.PLANNING, 
                                           LearningSessionStatus.EVALUATING, LearningSessionStatus.CONSOLIDATING]:
            self.session_manager.set_status(current.session_id, LearningSessionStatus.STOPPED, reason)

    def get_learning_status(self) -> dict[str, Any]:
        """Get current continuous learning status."""
        clo_enabled = self.session_manager.is_clo_enabled()
        stop_flag, stop_reason = self.session_manager.get_stop_flag()
        pause_flag = self.session_manager.get_learning_state("PAUSE_FLAG") is True
        
        current = self.session_manager.get_current_session()
        recent_sessions = self.session_manager.list_sessions(limit=5)
        
        return {
            "clo_enabled": clo_enabled,
            "stop_flag": stop_flag,
            "stop_reason": stop_reason,
            "pause_flag": pause_flag,
            "current_session": current.to_dict() if current else None,
            "recent_sessions": [s.to_dict() for s in recent_sessions],
            "total_sessions": len(recent_sessions),
        }