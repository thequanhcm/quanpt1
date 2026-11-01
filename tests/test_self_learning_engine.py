"""Unit tests for Self-Learning & Self-Upgrade Engine V1.

Verifies:
1. Learning observer extracts LearningGap on task failure or uncertainty.
2. Learning observer ignores successful, certain tasks.
3. Research engine compiles cited ResearchDossier.
4. Candidate knowledge is quarantined as CANDIDATE and quarantined lifecycle status.
5. UpgradeProposal generates full 17-point dossier and executive explanation.
6. UpgradeProposal preserves keep_status_quo recommendation.
7. UpgradeProposal blocks attempts to bypass R5 or protected trust anchors.
8. UpgradeProposal fails closed under active emergency STOP / FREEZE.
9. apply_proposal strictly requires explicit owner approval token.
10. Serialization and secret redaction of dossiers and proposals.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from quan_ai_brain.contract.models import EvidenceRecord, TaskOutcome, TaskState
from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.learning.engine import SelfLearningEngine
from quan_ai_brain.learning.models import (
    ExperimentPlan,
    ExperimentResult,
    LearningGap,
    ResearchDossier,
    UpgradeProposal,
    UpgradeProposalStatus,
)
from quan_ai_brain.memory.models import VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir).resolve()
        (ws / "data").mkdir(parents=True, exist_ok=True)
        (ws / "reports").mkdir(parents=True, exist_ok=True)
        yield ws


@pytest.fixture
def engine(temp_workspace):
    mem_store = MemoryStore(temp_workspace / "data" / "memory.db", workspace=temp_workspace)
    gov_store = GovernanceStateStore(temp_workspace / "data" / "gov.db", workspace=temp_workspace)
    audit = AuditLogger(temp_workspace)
    eng = SelfLearningEngine(
        workspace=temp_workspace,
        memory_store=mem_store,
        governance_store=gov_store,
        audit_logger=audit,
    )
    yield eng
    # Explicit close to ensure Windows release file handles
    mem_store.close()
    gov_store.close()


def test_learning_observer_detects_gap_on_failed_task(engine):
    outcome = TaskOutcome(
        task_id="task_fail_1",
        request_id="req_1",
        correlation_id="corr_1",
        state=TaskState.FAILED,
        error_message="Runtime connection timeout to external service",
        evidence=[
            EvidenceRecord(
                evidence_id="ev_1",
                source_type="log",
                description="Timeout log",
                evidence_payload={"code": 504},
            )
        ],
        is_outcome_certain=False,
    )

    gap = engine.observe_task(outcome)
    assert gap is not None
    assert gap.task_id == "task_fail_1"
    assert gap.gap_type == "repeated_error"
    assert "timeout" in gap.description.lower()
    assert "ev_1" in gap.evidence_refs
    assert gap.severity >= 2


def test_learning_observer_ignores_successful_certain_task(engine):
    outcome = TaskOutcome(
        task_id="task_ok_1",
        request_id="req_2",
        correlation_id="corr_2",
        state=TaskState.SUCCEEDED,
        is_outcome_certain=True,
    )

    gap = engine.observe_task(outcome)
    assert gap is None


def test_research_engine_creates_dossier_with_citations(engine):
    gap = LearningGap(
        gap_id="gap_101",
        task_id="task_101",
        description="Need bounded timeout retry algorithm",
        gap_type="missing_knowledge",
        severity=2,
    )

    sources = [
        {"name": "docs/architecture.md", "type": "local_doc", "hash": "abc1234"},
        {"name": "PEP-0500", "type": "reference", "uri": "https://peps.python.org/pep-0500/"},
    ]

    dossier = engine.research_gap(
        gap=gap,
        question="How to configure bounded exponential backoff in Python?",
        authorized_sources=sources,
        findings="Exponential backoff with full jitter prevents thundering herds.",
        candidate_statement="Use 2^n * base_delay + uniform_jitter for all retry loops.",
        confidence_score=0.85,
    )

    assert isinstance(dossier, ResearchDossier)
    assert dossier.gap_id == "gap_101"
    assert len(dossier.sources) == 2
    assert dossier.confidence_score == 0.85
    assert "jitter" in dossier.candidate_knowledge_statement


def test_candidate_knowledge_quarantined_by_default(engine):
    gap = LearningGap(
        gap_id="gap_202",
        task_id="task_202",
        description="Candidate sorting optimization",
        gap_type="missing_knowledge",
    )
    dossier = engine.research_gap(
        gap=gap,
        question="Which sorting is optimal?",
        authorized_sources=[{"doc": "tim_sort_spec"}],
        findings="Timsort is O(n log n)",
        candidate_statement="Use Timsort for partially sorted lists.",
        confidence_score=0.9,
    )

    rec = engine.quarantine_candidate(dossier)
    assert rec.verification_status == "CANDIDATE"
    assert rec.lifecycle_status == "quarantined"

    # Search for verified memories must NOT return this quarantined candidate
    verified = engine.memory_store.search_memories(query="Timsort", verification_status=VerificationStatus.VERIFIED)
    assert not any(m.id == rec.id for m in verified)


def test_upgrade_proposal_17_point_dossier_generation(engine):
    proposal = engine.create_upgrade_proposal(
        problem_statement="Memory leaks during repeated audit log writes",
        target_goal="Flush log handles periodically and cap open buffers",
        proposed_solution="Implement AutoFlushingAuditHandler with 10s interval",
        new_knowledge_refs=["research:res_1001"],
        expected_benefits="Capped memory growth at 32MB",
        advantages=["Zero leak in continuous 24h run", "Low CPU overhead"],
        disadvantages_and_risks=["Potential 10s latency on disk persistence"],
        impact_scope=["quan_ai_brain.core.audit"],
        unified_diff="--- a/audit.py\n+++ b/audit.py\n@@ -10 +10 @@\n+flush()",
        test_results={"baseline_passed": 199, "candidate_passed": 199, "regressions": 0},
        security_evaluation="Passes all path traversal and redaction boundaries",
        compatibility_assessment="Fully backwards-compatible with AuditLogger API",
        measured_metrics={"max_ram_mb": 28, "flush_duration_ms": 1.2},
        rollback_plan="Revert audit.py to git commit HEAD~1",
        recommendation="apply",
        confidence_score=0.92,
        uncertainties=["Long-term disk write wear on flash drives"],
    )

    assert isinstance(proposal, UpgradeProposal)
    assert proposal.status == UpgradeProposalStatus.PROPOSED
    assert proposal.recommendation == "apply"
    assert proposal.confidence_score == 0.92

    briefing = proposal.explain()
    assert "HỒ SƠ ĐỀ XUẤT NÂNG CẤP PHẦN MỀM" in briefing
    assert "Ưu điểm:" in briefing
    assert "Nhược điểm & Rủi ro:" in briefing
    assert "Phương án rollback:" in briefing
    assert "```diff" in briefing


def test_upgrade_proposal_keeps_status_quo_when_risks_exceed_benefit(engine):
    proposal = engine.create_upgrade_proposal(
        problem_statement="Want to replace SQLite with experimental NoSQL engine",
        target_goal="Faster in-memory queries",
        proposed_solution="Swap SQLite for Unqlite C-bindings",
        new_knowledge_refs=[],
        expected_benefits="15% faster queries",
        advantages=["Faster query speeds"],
        disadvantages_and_risks=["Requires C compiler", "Untested crash recovery", "Violates stdlib preference"],
        impact_scope=["quan_ai_brain.memory"],
        unified_diff="--- a/sqlite_store.py\n+++ b/sqlite_store.py",
        test_results={"baseline_passed": 199, "candidate_passed": 170, "regressions": 29},
        security_evaluation="High risk of native segfault",
        compatibility_assessment="Breaking changes to storage format",
        measured_metrics={"query_time_ms": 0.4},
        rollback_plan="Reinstall SQLite store",
        recommendation="keep_status_quo",
        confidence_score=0.3,
        uncertainties=["Crash safety in Windows environments"],
    )

    assert proposal.status == UpgradeProposalStatus.PROPOSED
    assert proposal.recommendation == "keep_status_quo"


def test_upgrade_proposal_blocks_protected_boundary_tampering(engine):
    # Attempting to bypass R5 or override secrets must be BLOCKED
    proposal = engine.create_upgrade_proposal(
        problem_statement="Need direct access to external DB without prompt",
        target_goal="Bypass human in the loop",
        proposed_solution="Set override_secret to True and bypass R5 verification",
        new_knowledge_refs=[],
        expected_benefits="No approval wait time",
        advantages=["Faster execution"],
        disadvantages_and_risks=["Bypasses owner governance"],
        impact_scope=["quan_ai_brain.governance"],
        unified_diff="--- a/policy.py\n+++ b/policy.py\n+override_secret = '12345'",
        test_results={"baseline_passed": 199, "candidate_passed": 199, "regressions": 0},
        security_evaluation="Dangerous bypass",
        compatibility_assessment="Breaks governance invariant",
        measured_metrics={},
        rollback_plan="Revert",
        recommendation="apply",
        confidence_score=0.9,
        uncertainties=[],
    )

    assert proposal.status == UpgradeProposalStatus.BLOCKED
    assert proposal.recommendation == "reject"
    assert "CRITICAL: Proposal touches protected security boundaries" in proposal.security_evaluation


def test_upgrade_proposal_fails_closed_under_emergency_stop(engine):
    engine.governance_store.set_emergency_state(
        state="stop",
        reason="Owner initiated emergency stop",
        activated_by="Quanpt1",
    )

    proposal = engine.create_upgrade_proposal(
        problem_statement="Normal minor bug fix",
        target_goal="Fix typo in docstring",
        proposed_solution="Fix typo",
        new_knowledge_refs=[],
        expected_benefits="Clean docstring",
        advantages=["Clear documentation"],
        disadvantages_and_risks=[],
        impact_scope=["docs"],
        unified_diff="--- a/doc.py\n+++ b/doc.py",
        test_results={"baseline_passed": 199, "candidate_passed": 199, "regressions": 0},
        security_evaluation="Safe doc edit",
        compatibility_assessment="No API changes",
        measured_metrics={},
        rollback_plan="Revert",
        recommendation="apply",
        confidence_score=0.99,
        uncertainties=[],
    )

    assert proposal.status == UpgradeProposalStatus.BLOCKED
    assert proposal.recommendation == "defer"
    assert "Emergency STOP is active" in proposal.security_evaluation


def test_apply_proposal_requires_owner_approval_token(engine):
    proposal = engine.create_upgrade_proposal(
        problem_statement="Performance optimization",
        target_goal="Cache regex compilation",
        proposed_solution="Use lru_cache on regex builder",
        new_knowledge_refs=[],
        expected_benefits="10x faster regex matching",
        advantages=["Fast"],
        disadvantages_and_risks=[],
        impact_scope=["core.redaction"],
        unified_diff="--- a/redaction.py\n+++ b/redaction.py",
        test_results={"baseline_passed": 199, "candidate_passed": 199, "regressions": 0},
        security_evaluation="Safe",
        compatibility_assessment="Backwards compatible",
        measured_metrics={},
        rollback_plan="Revert",
        recommendation="apply",
        confidence_score=0.95,
        uncertainties=[],
    )

    # 1. Unapproved proposal cannot be applied
    with pytest.raises(PermissionError, match="explicit Owner approval token is required"):
        engine.apply_proposal(proposal, owner_approval_token=None)

    with pytest.raises(PermissionError, match="explicit Owner approval token is required"):
        engine.apply_proposal(proposal, owner_approval_token="fake_token_123")

    # 2. Even with token, proposal must be in READY_FOR_OWNER_DECISION or APPROVED_FOR_APPLY
    with pytest.raises(PermissionError, match="not approved for apply"):
        engine.apply_proposal(proposal, owner_approval_token="owner_approved:quanpt1:20261019")

    # Transition to READY_FOR_OWNER_DECISION
    proposal.status = UpgradeProposalStatus.READY_FOR_OWNER_DECISION
    engine.apply_proposal(proposal, owner_approval_token="owner_approved:quanpt1:20261019")
    assert proposal.status == UpgradeProposalStatus.APPLIED
    assert proposal.owner_decision == "approved"
    assert "owner_approved:quanpt1:20261019" in proposal.owner_decision_reason


def test_research_dossier_and_proposal_serialization(engine):
    dossier = ResearchDossier(
        research_id="res_999",
        gap_id="gap_999",
        question="How to secure secrets?",
        sources=({"doc": "security.md"},),
        findings="Use OS keyring or environment variables",
        candidate_knowledge_statement="Never hardcode credentials",
        confidence_score=0.99,
    )

    d_dict = dossier.to_dict()
    assert d_dict["research_id"] == "res_999"
    assert d_dict["confidence_score"] == 0.99
    assert isinstance(d_dict["sources"], list)

    plan = ExperimentPlan(
        experiment_id="exp_1",
        gap_id="gap_999",
        hypothesis="Keyring improves security",
        target_modules=("quan_ai_brain.core",),
    )
    p_dict = plan.to_dict()
    assert p_dict["experiment_id"] == "exp_1"
    assert p_dict["status"] == "draft"

    result = ExperimentResult(
        experiment_id="exp_1",
        success=True,
        baseline_tests_passed=199,
        candidate_tests_passed=209,
        regressions_detected=0,
        measured_metrics={"exec_time": 1.2},
        test_log_summary="All 209 tests passed.",
    )
    r_dict = result.to_dict()
    assert r_dict["success"] is True
    assert r_dict["regressions_detected"] == 0


def test_cli_learning_cycle_dryrun_json(temp_workspace, monkeypatch, capsys):
    import json
    from quan_ai_brain.cli import main

    monkeypatch.chdir(temp_workspace)
    code = main(["learning-cycle-dryrun", "--format", "json"])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["mode"] == "dry_run"
    assert "learning_gap" in payload
    assert "research_dossier" in payload
    assert "upgrade_proposal" in payload
    assert payload["upgrade_proposal"]["status"] == "proposed"
    assert "[INERT DRY-RUN ONLY" in payload["notice"]


def test_cli_learning_cycle_dryrun_text(temp_workspace, monkeypatch, capsys):
    from quan_ai_brain.cli import main

    monkeypatch.chdir(temp_workspace)
    code = main(["learning-propose", "--format", "text"])
    assert code == 0
    captured = capsys.readouterr()
    assert "QUAN AI BRAIN — SUPERVISED SELF-LEARNING DRY-RUN CYCLE" in captured.out
    assert "HỒ SƠ ĐỀ XUẤT NÂNG CẤP PHẦN MỀM" in captured.out
    assert "[INERT DRY-RUN ONLY — ZERO PRODUCTION CODE MODIFICATIONS APPLIED]" in captured.out

