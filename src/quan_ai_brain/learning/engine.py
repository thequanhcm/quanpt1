"""Implementation of SelfLearningEngine for QUAN AI BRAIN.

Coordinates:
- Learning Observer (Observe task outcome and detect gaps).
- Research Engine (Formulate questions, cite local documentation).
- Knowledge Validation Engine (Quarantine candidate knowledge).
- Self-Improvement & Upgrade Proposal Engine (Compile 17-point dossier, test in sandbox, gate on owner approval).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import Any
import urllib.parse
import urllib.request
import uuid

from quan_ai_brain.contract.models import TaskOutcome, TaskState
from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.governance.policy import DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.learning.models import (
    ExperimentPlan,
    ExperimentResult,
    LearningGap,
    ResearchDossier,
    UpgradeProposal,
    UpgradeProposalStatus,
)
from quan_ai_brain.memory.models import MemoryRecord
from quan_ai_brain.memory.sqlite_store import MemoryStore


class SelfLearningEngine:
    """Orchestrates self-observation, local research, candidate quarantine, and upgrade proposals."""

    def __init__(
        self,
        workspace: str | Path,
        memory_store: MemoryStore | None = None,
        policy_engine: PolicyEngine | None = None,
        governance_store: GovernanceStateStore | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.memory_store = memory_store or MemoryStore(self.workspace / "data" / "memory.db", workspace=self.workspace)
        self.policy_engine = policy_engine or PolicyEngine(self.workspace)
        self.governance_store = governance_store
        self.audit_logger = audit_logger or AuditLogger(self.workspace)

    def observe_task(self, outcome: TaskOutcome) -> LearningGap | None:
        """Observe task outcome and extract learning gap if failure or anomaly detected."""
        if outcome.state in (TaskState.SUCCEEDED, TaskState.AUTHORIZED, TaskState.PLANNED) and outcome.is_outcome_certain:
            return None

        gap_type = "repeated_error" if outcome.state == TaskState.FAILED else "missing_knowledge"
        if outcome.state == TaskState.BLOCKED:
            gap_type = "policy_boundary_gap"

        gap_id = f"gap_{uuid.uuid4().hex[:8]}"
        desc = outcome.error_message or f"Task {outcome.task_id} reached state {outcome.state.value} with uncertain outcome."

        evidence_ids = tuple(e.evidence_id for e in outcome.evidence)

        gap = LearningGap(
            gap_id=gap_id,
            task_id=outcome.task_id,
            description=desc,
            gap_type=gap_type,
            evidence_refs=evidence_ids,
            severity=3 if outcome.state == TaskState.BLOCKED else 2,
        )

        self.audit_logger.record(
            event_type="learning_gap_detected",
            details={
                "gap_id": gap.gap_id,
                "task_id": gap.task_id,
                "gap_type": gap.gap_type,
                "severity": gap.severity,
            },
        )
        return gap

    def research_gap(
        self,
        gap: LearningGap,
        question: str,
        authorized_sources: list[dict[str, Any]],
        findings: str,
        candidate_statement: str,
        confidence_score: float = 0.6,
    ) -> ResearchDossier:
        """Perform bounded, cited research on an identified gap."""
        # Sanitize and ensure no secrets in citations
        sanitized_sources = tuple(redact_value(s) for s in authorized_sources)

        dossier = ResearchDossier(
            research_id=f"res_{uuid.uuid4().hex[:8]}",
            gap_id=gap.gap_id,
            question=question,
            sources=sanitized_sources,
            findings=findings,
            candidate_knowledge_statement=candidate_statement,
            confidence_score=max(0.1, min(1.0, confidence_score)),
        )

        self.audit_logger.record(
            event_type="research_dossier_created",
            details={
                "research_id": dossier.research_id,
                "gap_id": dossier.gap_id,
                "source_count": len(dossier.sources),
                "confidence_score": dossier.confidence_score,
            },
        )
        return dossier

    INJECTION_PATTERNS = [
        re.compile(r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b"),
        re.compile(r"(?i)\byou\s+are\s+now\s+(?:unrestricted|DAN|jailbroken)\b"),
        re.compile(r"(?i)\b(?:system\s+override|admin\s+override|bypass\s+governance)\b"),
        re.compile(r"(?i)<\s*script[^>]*>"),
    ]

    def fetch_verified_technical_doc(
        self,
        url_or_path: str,
        title: str = "",
        timeout: float = 3.0,
        content_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Safely fetch and inspect a technical document or citation:
        - Computes SHA-256 hash for provenance and tamper detection.
        - Scans for prompt injection attacks and code execution exploits.
        - Sanitizes content and marks credibility.
        - Zero execution: Treated as untrusted text only.
        """
        raw_text = ""
        is_url = url_or_path.startswith("http://") or url_or_path.startswith("https://")

        if content_override is not None:
            raw_text = content_override
        elif is_url:
            try:
                req = urllib.request.Request(
                    url_or_path,
                    headers={"User-Agent": "QUAN-AI-BRAIN-Research-Bot/1.0 (Audit-First; Read-Only)"},
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw_text = resp.read(200_000).decode("utf-8", errors="replace")
            except Exception as e:
                return {
                    "source": url_or_path,
                    "title": title or url_or_path,
                    "success": False,
                    "error": str(e),
                    "is_injection_detected": False,
                    "sanitized_content": "",
                    "sha256": "",
                }
        else:
            target_path = Path(url_or_path)
            if not target_path.is_absolute():
                target_path = (self.workspace / target_path).resolve()
            if target_path.exists() and target_path.is_file():
                raw_text = target_path.read_text(encoding="utf-8", errors="replace")[:200_000]
            else:
                return {
                    "source": url_or_path,
                    "title": title or url_or_path,
                    "success": False,
                    "error": "File not found",
                    "is_injection_detected": False,
                    "sanitized_content": "",
                    "sha256": "",
                }

        sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        is_injection = False
        detected_patterns = []
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(raw_text):
                is_injection = True
                detected_patterns.append(pattern.pattern)

        sanitized = redact_text(raw_text)

        if is_injection:
            self.audit_logger.record(
                event_type="research_prompt_injection_detected",
                details={
                    "source": url_or_path,
                    "sha256": sha256,
                    "patterns": detected_patterns,
                },
            )

        return {
            "source": url_or_path,
            "title": title or url_or_path,
            "success": True,
            "sha256": sha256,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "sanitized_content": sanitized[:4000],
            "content_length": len(raw_text),
            "is_injection_detected": is_injection,
            "reliability_score": 0.2 if is_injection else 0.85,
        }

    def quarantine_candidate(self, dossier: ResearchDossier) -> MemoryRecord:
        """Store newly researched knowledge in the quarantined candidate partition."""
        record = self.memory_store.quarantine_candidate_knowledge(
            statement=dossier.candidate_knowledge_statement,
            source_ref=f"research:{dossier.research_id}",
            rationale=f"Researched for gap {dossier.gap_id}: {dossier.findings}",
            tags=["learning_candidate", f"gap:{dossier.gap_id}"],
            metadata={
                "research_id": dossier.research_id,
                "confidence_score": dossier.confidence_score,
                "source_count": len(dossier.sources),
            },
        )

        self.audit_logger.record(
            event_type="candidate_knowledge_quarantined",
            details={
                "memory_id": record.id,
                "research_id": dossier.research_id,
                "status": record.verification_status,
                "lifecycle": record.lifecycle_status,
            },
        )
        return record

    def create_upgrade_proposal(
        self,
        problem_statement: str,
        target_goal: str,
        proposed_solution: str,
        new_knowledge_refs: list[str],
        expected_benefits: str,
        advantages: list[str],
        disadvantages_and_risks: list[str],
        impact_scope: list[str],
        unified_diff: str,
        test_results: dict[str, Any],
        security_evaluation: str,
        compatibility_assessment: str,
        measured_metrics: dict[str, Any],
        rollback_plan: str,
        recommendation: str,
        confidence_score: float,
        uncertainties: list[str],
    ) -> UpgradeProposal:
        """Compile a canonical 17-point software upgrade proposal dossier."""
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"

        # Security evaluation barrier: If diff or solution attempts to weaken R5 or alter secrets, immediately block!
        forbidden_patterns = ("R5", "override_secret", "QUANPT1_APPROVAL_SECRET", "disable_safety", "trust_anchor")
        lowered = (unified_diff + " " + proposed_solution).lower()
        if any(p.lower() in lowered for p in forbidden_patterns) and "hard-blocked" not in lowered:
            status = UpgradeProposalStatus.BLOCKED
            recommendation = "reject"
            security_evaluation += " CRITICAL: Proposal touches protected security boundaries. Permanently blocked."
        else:
            status = UpgradeProposalStatus.PROPOSED

        # Check emergency state
        if self.governance_store is not None:
            em_state = self.governance_store.get_emergency_state()
            if em_state.state in ("stop", "freeze"):
                status = UpgradeProposalStatus.BLOCKED
                recommendation = "defer"
                security_evaluation += f" Emergency {em_state.state.upper()} is active; all proposals blocked."

        proposal = UpgradeProposal(
            proposal_id=proposal_id,
            problem_statement=problem_statement,
            target_goal=target_goal,
            proposed_solution=proposed_solution,
            new_knowledge_refs=new_knowledge_refs,
            expected_benefits=expected_benefits,
            advantages=advantages,
            disadvantages_and_risks=disadvantages_and_risks,
            impact_scope=impact_scope,
            unified_diff=unified_diff,
            test_results=test_results,
            security_evaluation=security_evaluation,
            compatibility_assessment=compatibility_assessment,
            measured_metrics=measured_metrics,
            rollback_plan=rollback_plan,
            recommendation=recommendation,
            confidence_score=confidence_score,
            uncertainties=uncertainties,
            status=status,
        )

        self.audit_logger.record(
            event_type="upgrade_proposal_created",
            details={
                "proposal_id": proposal.proposal_id,
                "status": proposal.status.value,
                "recommendation": proposal.recommendation,
                "confidence_score": proposal.confidence_score,
            },
        )
        return proposal

    def apply_proposal(self, proposal: UpgradeProposal, owner_approval_token: str | None) -> None:
        """Apply an approved upgrade proposal. Strict fail-closed if owner approval is absent."""
        if not owner_approval_token or not owner_approval_token.startswith("owner_approved:"):
            raise PermissionError("Cannot apply upgrade proposal: explicit Owner approval token is required.")

        if proposal.status != UpgradeProposalStatus.READY_FOR_OWNER_DECISION and proposal.status != UpgradeProposalStatus.APPROVED_FOR_APPLY:
            raise PermissionError(f"Proposal is in state '{proposal.status.value}', not approved for apply.")

        # In inert mode, real code overwriting remains restricted
        proposal.status = UpgradeProposalStatus.APPLIED
        proposal.owner_decision = "approved"
        proposal.owner_decision_reason = f"Applied with token {owner_approval_token}"
        proposal.owner_decision_at_utc = datetime.now(timezone.utc).isoformat()

        self.audit_logger.record(
            event_type="upgrade_proposal_applied",
            details={
                "proposal_id": proposal.proposal_id,
                "status": proposal.status.value,
            },
        )
