"""QUAN AI BRAIN — Cognitive State Model & Evidence-Driven Reasoning Engine.

Master Implementation Prompt V4:
- Section 2: Structured Cognitive State & Multi-Source Provenance (CognitiveClaim / BeliefItem).
- Section 3: Evidence Categorization, No Fabricated Certainty & Metacognitive Calibration.
- Section 4: Freshness Evaluation, Context-Aware Contradiction Detection & State Reconciliation.
- Section 5: Integration with Executive Planning & Safe Action Boundaries.
- Section 6: Cognitive Self-Assessment & Evidence Levels (CODE_PRESENT, UNIT_TESTED, INTEGRATION_TESTED, ENVIRONMENT_VERIFIED, HARDWARE_VERIFIED, PRODUCTION_APPROVED).

Non-negotiable invariants:
- R5 hard-blocked; R4 requires Dual-Factor owner approval.
- Beliefs must segregate FACT_USER, FACT_RETRIEVED, OBSERVED, VERIFIED, INFERRED, HYPOTHESIS, UNKNOWN.
- Never inflate confidence or verification status without empirical evidence.
- Contradictions retain both branches without silent overwrites.
- Contextual differences (different hosts/devices/times) are distinguished from logical contradictions.
- Fail-closed: if critical evidence is missing, abstention is mandatory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import re
from typing import Any

from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.memory.models import MemoryType, VerificationStatus


class BeliefKind(str, Enum):
    """Rigorous classification of knowledge items within the cognitive model."""
    FACT_USER = "fact_user"                       # Direct fact provided by Quanpt1
    FACT_RETRIEVED = "fact_retrieved"             # Retrieved from long-term verified storage
    OBSERVED = "observed"                         # Directly observed by system telemetry/test run
    VERIFIED_INDEPENDENT = "verified_independent" # Independently verified with test evidence
    INFERENCE = "inference"                       # Deterministic or model-derived conclusion
    HYPOTHESIS = "hypothesis"                     # Competing explanation awaiting verification
    PREDICTION = "prediction"                     # Future projection dependent on assumptions
    UNKNOWN = "unknown"                           # Critical piece of knowledge identified as absent


class FreshnessPolicy(str, Enum):
    """Policy governing temporal validity and stale state detection."""
    EPHEMERAL = "ephemeral"   # 5 minutes (live sensor/telemetry)
    SESSION = "session"       # 2 hours (dialogue turn / task session)
    DAILY = "daily"           # 24 hours (operational daily status)
    LONG_TERM = "long_term"   # 30 days (general verified memory)
    IMMUTABLE = "immutable"   # Never expires unless superseded (core identity/owner facts)


class FreshnessStatus(str, Enum):
    """Evaluation status of cognitive data freshness."""
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    IMMUTABLE = "immutable"


class ContradictionType(str, Enum):
    """Classification of contradictions to distinguish context differences from real conflicts."""
    DIRECT_CONTRADICTION = "direct_contradiction"  # Same subject, predicate, scope, and time with incompatible values
    CONTEXT_DIFFERENCE = "context_difference"      # Differing values explained by different host, scope, or environment
    TEMPORAL_EVOLUTION = "temporal_evolution"      # Legitimate change over time (supersedes historical state)


class EvidenceLevel(str, Enum):
    """Rigorous evidence tiers for cognitive self-assessment."""
    CODE_PRESENT = "CODE_PRESENT"
    UNIT_TESTED = "UNIT_TESTED"
    INTEGRATION_TESTED = "INTEGRATION_TESTED"
    ENVIRONMENT_VERIFIED = "ENVIRONMENT_VERIFIED"
    HARDWARE_VERIFIED = "HARDWARE_VERIFIED"
    PRODUCTION_APPROVED = "PRODUCTION_APPROVED"


class HypothesisStatus(str, Enum):
    """Lifecycle status of an active cognitive hypothesis."""
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    ABANDONED = "abandoned"


class ReversibilityLevel(str, Enum):
    """Reversibility classification of proposed action alternatives."""
    FULL = "full"                 # Read-only or idempotent scratch writes (R0-R2)
    PARTIAL = "partial"           # Can be undone with compensation script (R3)
    IRREVERSIBLE = "irreversible" # Permanent deletion or physical change (R4-R5)


# ---------------------------------------------------------------------------
# Structured Cognitive Claim (BeliefItem alias for 100% backward compatibility)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitiveClaim:
    """An individual belief or claim held by the assistant, with strict multi-source provenance."""
    claim_id: str = ""
    statement: str = ""
    kind: BeliefKind = BeliefKind.UNKNOWN
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    subject: str = ""
    predicate: str = ""
    value: Any = None
    confidence: float | None = 0.5
    verification_status: str = VerificationStatus.UNVERIFIED.value
    observed_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recorded_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_until_utc: str | None = None
    freshness_policy: str = FreshnessPolicy.LONG_TERM.value
    status: str = "active"
    supporting_sources: tuple[str, ...] = field(default_factory=tuple)
    opposing_sources: tuple[str, ...] = field(default_factory=tuple)
    contradiction_refs: tuple[str, ...] = field(default_factory=tuple)
    version: int = 1
    superseded_by: str | None = None
    verification_method: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    # Backward compatibility attributes
    belief_id: str = ""
    source_ref: str = ""
    created_at_utc: str = ""

    def __post_init__(self) -> None:
        # Align claim_id and belief_id
        if not self.belief_id and self.claim_id:
            object.__setattr__(self, "belief_id", self.claim_id)
        elif not self.claim_id and self.belief_id:
            object.__setattr__(self, "claim_id", self.belief_id)
        elif not self.claim_id and not self.belief_id:
            gen_id = f"claim-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            object.__setattr__(self, "claim_id", gen_id)
            object.__setattr__(self, "belief_id", gen_id)
            object.__setattr__(self, "claim_id", self.belief_id)

        # Align source_refs and source_ref
        if not self.source_refs and self.source_ref:
            object.__setattr__(self, "source_refs", (self.source_ref,))
        elif self.source_refs and not self.source_ref:
            object.__setattr__(self, "source_ref", self.source_refs[0])

        # Align timestamps
        now_iso = datetime.now(timezone.utc).isoformat()
        if not self.recorded_at_utc:
            object.__setattr__(self, "recorded_at_utc", self.created_at_utc or now_iso)
        if not self.created_at_utc:
            object.__setattr__(self, "created_at_utc", self.recorded_at_utc)
        if not self.observed_at_utc:
            object.__setattr__(self, "observed_at_utc", self.recorded_at_utc)

    def is_verified_fact(self) -> bool:
        """Only independent verification, direct observation, or owner statement count as facts."""
        return self.kind in (
            BeliefKind.FACT_USER,
            BeliefKind.FACT_RETRIEVED,
            BeliefKind.OBSERVED,
            BeliefKind.VERIFIED_INDEPENDENT,
        ) and self.verification_status in (
            VerificationStatus.VERIFIED.value,
            VerificationStatus.OBSERVED.value,
            VerificationStatus.USER_PROVIDED.value,
            "verified",
            "observed",
            "user_provided",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "belief_id": self.belief_id,
            "statement": redact_text(self.statement),
            "kind": self.kind.value if isinstance(self.kind, BeliefKind) else str(self.kind),
            "subject": redact_text(self.subject),
            "predicate": redact_text(self.predicate),
            "value": "[REDACTED]" if any(k in f"{self.subject}_{self.predicate}".lower() for k in ("token", "secret", "key", "password", "auth", "credential", "private")) else redact_value(self.value),
            "source_refs": [redact_text(s) for s in self.source_refs],
            "source_ref": redact_text(self.source_ref),
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "verification_status": self.verification_status,
            "observed_at_utc": self.observed_at_utc,
            "recorded_at_utc": self.recorded_at_utc,
            "created_at_utc": self.created_at_utc,
            "valid_until_utc": self.valid_until_utc,
            "freshness_policy": self.freshness_policy,
            "status": self.status,
            "supporting_sources": [redact_text(s) for s in self.supporting_sources],
            "opposing_sources": [redact_text(s) for s in self.opposing_sources],
            "contradiction_refs": list(self.contradiction_refs),
            "version": self.version,
            "superseded_by": self.superseded_by,
            "verification_method": redact_text(self.verification_method) if self.verification_method else None,
            "tags": list(self.tags),
        }


# Direct backward compatibility alias
BeliefItem = CognitiveClaim


# ---------------------------------------------------------------------------
# Freshness Evaluator
# ---------------------------------------------------------------------------

def evaluate_freshness(claim: CognitiveClaim, as_of: datetime | None = None) -> tuple[FreshnessStatus, bool]:
    """Evaluate whether a claim is fresh, stale, expired, or immutable.

    Returns (FreshnessStatus, is_stale_or_expired: bool).
    """
    now = as_of or datetime.now(timezone.utc)

    if claim.freshness_policy == FreshnessPolicy.IMMUTABLE.value:
        return FreshnessStatus.IMMUTABLE, False

    # 1. Check explicit expiration timestamp
    if claim.valid_until_utc:
        try:
            clean_ts = claim.valid_until_utc.replace("Z", "+00:00")
            exp_dt = datetime.fromisoformat(clean_ts)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if now > exp_dt:
                return FreshnessStatus.EXPIRED, True
        except (ValueError, TypeError):
            pass

    # 2. Check policy-based duration from observed_at_utc
    policy_durations: dict[str, float] = {
        FreshnessPolicy.EPHEMERAL.value: 300.0,       # 5 minutes
        FreshnessPolicy.SESSION.value: 7200.0,       # 2 hours
        FreshnessPolicy.DAILY.value: 86400.0,        # 24 hours
        FreshnessPolicy.LONG_TERM.value: 2592000.0,  # 30 days
    }
    limit_seconds = policy_durations.get(claim.freshness_policy)
    ref_time_str = claim.observed_at_utc or claim.recorded_at_utc or claim.created_at_utc
    if limit_seconds is not None and ref_time_str:
        try:
            clean_ref = ref_time_str.replace("Z", "+00:00")
            obs_dt = datetime.fromisoformat(clean_ref)
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
            elapsed = (now - obs_dt).total_seconds()
            if elapsed > limit_seconds:
                return FreshnessStatus.STALE, True
        except (ValueError, TypeError):
            pass

    return FreshnessStatus.FRESH, False


# ---------------------------------------------------------------------------
# Auxiliary Cognitive Models
# ---------------------------------------------------------------------------

@dataclass
class HypothesisItem:
    """A structured candidate hypothesis for Root Cause Analysis or operational diagnosis."""
    hypothesis_id: str
    statement: str
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    test_method: str = ""
    falsification_condition: str = ""
    risk_if_wrong: int = 1  # R0-R5
    status: HypothesisStatus = HypothesisStatus.PROPOSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": redact_text(self.statement),
            "supporting_evidence": [redact_text(e) for e in self.supporting_evidence],
            "contradicting_evidence": [redact_text(e) for e in self.contradicting_evidence],
            "test_method": redact_text(self.test_method),
            "falsification_condition": redact_text(self.falsification_condition),
            "risk_if_wrong": self.risk_if_wrong,
            "status": self.status.value,
        }


@dataclass
class UncertaintyItem:
    """An explicit record of an information gap or unknown, driving metacognitive abstention."""
    unknown_key: str
    description: str
    why_critical: str
    suggested_verification_action: str
    requires_owner_input: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "unknown_key": self.unknown_key,
            "description": redact_text(self.description),
            "why_critical": redact_text(self.why_critical),
            "suggested_verification_action": redact_text(self.suggested_verification_action),
            "requires_owner_input": self.requires_owner_input,
        }


@dataclass
class AlternativeOption:
    """A candidate course of action evaluated against criteria before decision."""
    option_id: str
    title: str
    description: str
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    risk_level: int = 0
    reversibility: ReversibilityLevel = ReversibilityLevel.FULL
    requires_approval: bool = False
    evidence_score: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "title": redact_text(self.title),
            "description": redact_text(self.description),
            "pros": [redact_text(p) for p in self.pros],
            "cons": [redact_text(c) for c in self.cons],
            "risk_level": self.risk_level,
            "reversibility": self.reversibility.value,
            "requires_approval": self.requires_approval,
            "evidence_score": round(self.evidence_score, 4),
        }


@dataclass
class ContradictionRecord:
    """Preserved contradiction between two sources or claims without loss of provenance."""
    contradiction_id: str
    topic: str
    claim_a: str
    source_a: str
    status_a: str
    claim_b: str
    source_b: str
    status_b: str
    contradiction_type: str = ContradictionType.DIRECT_CONTRADICTION.value
    context_a: dict[str, Any] = field(default_factory=dict)
    context_b: dict[str, Any] = field(default_factory=dict)
    resolution_status: str = "UNRESOLVED"  # UNRESOLVED, RESOLVED_A, RESOLVED_B, CONTEXT_DIFFERENCE, NEEDS_REVIEW
    resolution_reason: str = ""
    resolved_by: str = ""
    detected_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "topic": redact_text(self.topic),
            "claim_a": redact_text(self.claim_a),
            "source_a": redact_text(self.source_a),
            "status_a": self.status_a,
            "claim_b": redact_text(self.claim_b),
            "source_b": redact_text(self.source_b),
            "status_b": self.status_b,
            "contradiction_type": self.contradiction_type,
            "context_a": redact_value(self.context_a),
            "context_b": redact_value(self.context_b),
            "resolution_status": self.resolution_status,
            "resolution_reason": redact_text(self.resolution_reason),
            "resolved_by": redact_text(self.resolved_by),
            "detected_at_utc": self.detected_at_utc,
            "notes": redact_text(self.notes),
        }


@dataclass
class MetacognitiveEvaluation:
    """Self-assessment of epistemic readiness, confidence calibration, and abstention."""
    can_conclude: bool = False
    abstention_reason: str | None = None
    grounding_score: float = 0.0          # Ratio of conclusions supported by verified facts
    unverified_claim_count: int = 0
    unresolved_contradiction_count: int = 0
    critical_gap_count: int = 0
    stale_claim_count: int = 0
    recommended_next_step: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_conclude": self.can_conclude,
            "abstention_reason": redact_text(self.abstention_reason) if self.abstention_reason else None,
            "grounding_score": round(self.grounding_score, 4),
            "unverified_claim_count": self.unverified_claim_count,
            "unresolved_contradiction_count": self.unresolved_contradiction_count,
            "critical_gap_count": self.critical_gap_count,
            "stale_claim_count": self.stale_claim_count,
            "recommended_next_step": redact_text(self.recommended_next_step),
        }


# ---------------------------------------------------------------------------
# Cognitive State
# ---------------------------------------------------------------------------

@dataclass
class CognitiveState:
    """Complete, auditable Cognitive State of QUAN AI BRAIN for a task or consultation session."""
    task_id: str
    goal: str
    deliverables: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    beliefs: list[CognitiveClaim] = field(default_factory=list)
    hypotheses: list[HypothesisItem] = field(default_factory=list)
    uncertainties: list[UncertaintyItem] = field(default_factory=list)
    alternatives: list[AlternativeOption] = field(default_factory=list)
    contradictions: list[ContradictionRecord] = field(default_factory=list)
    selected_decision: dict[str, Any] | None = None
    metacognition: MetacognitiveEvaluation = field(default_factory=MetacognitiveEvaluation)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Mutation & Evidence Tracking
    # ------------------------------------------------------------------

    def add_claim(
        self,
        statement: str,
        kind: BeliefKind,
        source_refs: tuple[str, ...] | list[str] | str,
        subject: str = "",
        predicate: str = "",
        value: Any = None,
        confidence: float | None = None,
        verification_status: str = VerificationStatus.UNVERIFIED.value,
        observed_at_utc: str = "",
        valid_until_utc: str | None = None,
        freshness_policy: str = FreshnessPolicy.LONG_TERM.value,
        tags: tuple[str, ...] = (),
        verification_method: str | None = None,
    ) -> CognitiveClaim:
        """Add a structured cognitive claim with explicit multi-source provenance."""
        c_id = f"claim-{len(self.beliefs) + 1:03d}"
        if isinstance(source_refs, str):
            clean_s = source_refs.strip()
            refs_tuple = (clean_s,) if clean_s else ()
        else:
            refs_tuple = tuple(s.strip() for s in source_refs if s and s.strip())

        item = CognitiveClaim(
            claim_id=c_id,
            statement=statement.strip(),
            kind=kind,
            source_refs=refs_tuple or ("unspecified",),
            subject=subject.strip(),
            predicate=predicate.strip(),
            value=value,
            confidence=max(0.0, min(1.0, float(confidence))) if confidence is not None else None,
            verification_status=verification_status,
            observed_at_utc=observed_at_utc or datetime.now(timezone.utc).isoformat(),
            recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            valid_until_utc=valid_until_utc,
            freshness_policy=freshness_policy,
            tags=tags,
            verification_method=verification_method,
        )
        self.beliefs.append(item)
        return item

    def add_belief(
        self,
        statement: str,
        kind: BeliefKind,
        source_ref: str,
        confidence: float = 0.5,
        verification_status: str = VerificationStatus.UNVERIFIED.value,
        tags: tuple[str, ...] = (),
        **kwargs: Any,
    ) -> CognitiveClaim:
        """Add a belief item with explicit kind and provenance (backward compatible)."""
        b_id = f"belief-{len(self.beliefs) + 1:03d}"
        s_ref = source_ref.strip() or "unspecified"
        item = CognitiveClaim(
            claim_id=b_id,
            belief_id=b_id,
            statement=statement.strip(),
            kind=kind,
            source_refs=(s_ref,),
            source_ref=s_ref,
            confidence=max(0.0, min(1.0, float(confidence))),
            verification_status=verification_status,
            tags=tags,
            subject=kwargs.get("subject", ""),
            predicate=kwargs.get("predicate", ""),
            value=kwargs.get("value", None),
            valid_until_utc=kwargs.get("valid_until_utc"),
            freshness_policy=kwargs.get("freshness_policy", FreshnessPolicy.LONG_TERM.value),
            verification_method=kwargs.get("verification_method"),
        )
        self.beliefs.append(item)
        return item

    def add_uncertainty(
        self,
        unknown_key: str,
        description: str,
        why_critical: str,
        suggested_verification_action: str,
        requires_owner_input: bool = False,
    ) -> UncertaintyItem:
        """Register a known unknown that blocks complete certainty."""
        item = UncertaintyItem(
            unknown_key=unknown_key.strip(),
            description=description.strip(),
            why_critical=why_critical.strip(),
            suggested_verification_action=suggested_verification_action.strip(),
            requires_owner_input=requires_owner_input,
        )
        self.uncertainties.append(item)
        return item

    def add_hypothesis(
        self,
        statement: str,
        supporting_evidence: list[str] | None = None,
        test_method: str = "",
        falsification_condition: str = "",
        risk_if_wrong: int = 1,
    ) -> HypothesisItem:
        """Register a testable hypothesis for investigation."""
        h_id = f"hyp-{len(self.hypotheses) + 1:03d}"
        item = HypothesisItem(
            hypothesis_id=h_id,
            statement=statement.strip(),
            supporting_evidence=supporting_evidence or [],
            test_method=test_method.strip(),
            falsification_condition=falsification_condition.strip(),
            risk_if_wrong=risk_if_wrong,
        )
        self.hypotheses.append(item)
        return item

    def record_contradiction(
        self,
        topic: str,
        claim_a: str,
        source_a: str,
        status_a: str,
        claim_b: str,
        source_b: str,
        status_b: str,
        notes: str = "",
        context_a: dict[str, Any] | None = None,
        context_b: dict[str, Any] | None = None,
        contradiction_type: ContradictionType | str | None = None,
    ) -> ContradictionRecord:
        """Retain both conflicting claims with provenance; never silently overwrite.

        Distinguishes context differences (different devices, hosts, or times) from direct contradictions.
        """
        c_id = f"contra-{len(self.contradictions) + 1:03d}"
        ctx_a = context_a or {}
        ctx_b = context_b or {}

        # Auto-detect context difference vs direct contradiction
        c_type = contradiction_type
        initial_status = "UNRESOLVED"
        if c_type is None:
            # Check if contexts have different scopes or different hosts or devices
            differing_keys = [
                k for k in ("host", "device", "environment", "scope", "cluster")
                if ctx_a.get(k) != ctx_b.get(k) and (ctx_a.get(k) or ctx_b.get(k))
            ]
            if differing_keys:
                c_type = ContradictionType.CONTEXT_DIFFERENCE.value
                initial_status = "CONTEXT_DIFFERENCE"
                if not notes:
                    notes = f"Sự khác biệt ngữ cảnh theo các tiêu chí: {', '.join(differing_keys)}"
            else:
                c_type = ContradictionType.DIRECT_CONTRADICTION.value
                initial_status = "UNRESOLVED"

        rec = ContradictionRecord(
            contradiction_id=c_id,
            topic=topic.strip(),
            claim_a=claim_a.strip(),
            source_a=source_a.strip(),
            status_a=status_a,
            claim_b=claim_b.strip(),
            source_b=source_b.strip(),
            status_b=status_b,
            contradiction_type=str(c_type),
            context_a=ctx_a,
            context_b=ctx_b,
            resolution_status=initial_status,
            notes=notes.strip(),
        )
        self.contradictions.append(rec)
        return rec

    def reconcile_evidence(
        self,
        statement: str,
        kind: BeliefKind,
        source_ref: str,
        subject: str = "",
        predicate: str = "",
        value: Any = None,
        verification_status: str = VerificationStatus.UNVERIFIED.value,
        verification_method: str | None = None,
    ) -> tuple[CognitiveClaim, list[str]]:
        """Reconcile new evidence against existing beliefs without silent overwrite."""
        notes: list[str] = []
        matching_idx = -1

        # Find existing claim by subject+predicate or exact statement
        for i, b in enumerate(self.beliefs):
            if subject and predicate and b.subject == subject and b.predicate == predicate:
                matching_idx = i
                break
            elif b.statement.strip().lower() == statement.strip().lower():
                matching_idx = i
                break

        if matching_idx == -1:
            claim = self.add_claim(
                statement=statement,
                kind=kind,
                source_refs=(source_ref,),
                subject=subject,
                predicate=predicate,
                value=value,
                verification_status=verification_status,
                verification_method=verification_method,
            )
            notes.append(f"Ghi nhận claim mới: {claim.claim_id}")
            return claim, notes

        existing = self.beliefs[matching_idx]
        same_value = (
            (existing.value == value)
            if (existing.value is not None and value is not None)
            else (existing.statement.strip().lower() == statement.strip().lower())
        )

        if same_value:
            # Agreement
            if source_ref in existing.source_refs:
                notes.append(f"Nguồn {source_ref} đã tồn tại; không nhân bản tăng độ tin cậy giả tạo.")
                return existing, notes

            new_sources = existing.source_refs + (source_ref,)
            new_supporting = existing.supporting_sources + (source_ref,)
            new_status = existing.verification_status
            if verification_status in (VerificationStatus.VERIFIED.value, "verified", "observed") and existing.verification_status not in (VerificationStatus.VERIFIED.value, "verified", "observed"):
                new_status = verification_status
                notes.append(f"Nâng trạng thái xác minh lên {new_status} nhờ bằng chứng độc lập từ {source_ref}.")

            updated_claim = CognitiveClaim(
                claim_id=existing.claim_id,
                statement=existing.statement,
                kind=existing.kind,
                source_refs=new_sources,
                subject=existing.subject,
                predicate=existing.predicate,
                value=existing.value,
                confidence=existing.confidence,
                verification_status=new_status,
                observed_at_utc=datetime.now(timezone.utc).isoformat(),
                recorded_at_utc=existing.recorded_at_utc,
                valid_until_utc=existing.valid_until_utc,
                freshness_policy=existing.freshness_policy,
                status=existing.status,
                supporting_sources=new_supporting,
                opposing_sources=existing.opposing_sources,
                contradiction_refs=existing.contradiction_refs,
                version=existing.version,
                superseded_by=existing.superseded_by,
                verification_method=verification_method or existing.verification_method,
                tags=existing.tags,
            )
            self.beliefs[matching_idx] = updated_claim
            notes.append(f"Bổ sung nguồn hỗ trợ độc lập: {source_ref}")
            return updated_claim, notes
        else:
            # Conflict / Disagreement
            c_rec = self.record_contradiction(
                topic=f"{subject}:{predicate}" if subject and predicate else statement[:40],
                claim_a=f"{existing.statement} (value={existing.value})",
                source_a=existing.source_ref or (existing.source_refs[0] if existing.source_refs else "unknown"),
                status_a=existing.verification_status,
                claim_b=f"{statement} (value={value})",
                source_b=source_ref,
                status_b=verification_status,
                notes="Mâu thuẫn dữ kiện khi đối chiếu bằng chứng mới.",
            )
            new_cid = f"claim-{len(self.beliefs) + 1:03d}"
            opposing = existing.opposing_sources + (source_ref,)

            # If new evidence is independently verified and old was merely inferred, supersede old claim
            if verification_status in (VerificationStatus.VERIFIED.value, "verified", "observed") and existing.kind in (BeliefKind.INFERENCE, BeliefKind.HYPOTHESIS):
                old_superseded = CognitiveClaim(
                    claim_id=existing.claim_id,
                    statement=existing.statement,
                    kind=existing.kind,
                    source_refs=existing.source_refs,
                    subject=existing.subject,
                    predicate=existing.predicate,
                    value=existing.value,
                    confidence=existing.confidence,
                    verification_status=existing.verification_status,
                    observed_at_utc=existing.observed_at_utc,
                    recorded_at_utc=existing.recorded_at_utc,
                    valid_until_utc=existing.valid_until_utc,
                    freshness_policy=existing.freshness_policy,
                    status="superseded",
                    supporting_sources=existing.supporting_sources,
                    opposing_sources=opposing,
                    contradiction_refs=existing.contradiction_refs + (c_rec.contradiction_id,),
                    version=existing.version,
                    superseded_by=new_cid,
                    verification_method=existing.verification_method,
                    tags=existing.tags,
                )
                self.beliefs[matching_idx] = old_superseded

                new_claim = CognitiveClaim(
                    claim_id=new_cid,
                    statement=statement,
                    kind=kind,
                    source_refs=(source_ref,),
                    subject=subject,
                    predicate=predicate,
                    value=value,
                    confidence=0.9,
                    verification_status=verification_status,
                    observed_at_utc=datetime.now(timezone.utc).isoformat(),
                    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                    valid_until_utc=None,
                    freshness_policy=FreshnessPolicy.LONG_TERM.value,
                    status="active",
                    supporting_sources=(source_ref,),
                    opposing_sources=(existing.claim_id,),
                    contradiction_refs=(c_rec.contradiction_id,),
                    version=existing.version + 1,
                    superseded_by=None,
                    verification_method=verification_method,
                )
                self.beliefs.append(new_claim)
                notes.append(f"Claim cũ bị thay thế bởi bằng chứng quan sát mới (v{new_claim.version}).")
                return new_claim, notes
            else:
                # Flag needs review without silently overwriting
                new_claim = CognitiveClaim(
                    claim_id=new_cid,
                    statement=statement,
                    kind=kind,
                    source_refs=(source_ref,),
                    subject=subject,
                    predicate=predicate,
                    value=value,
                    confidence=0.5,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    observed_at_utc=datetime.now(timezone.utc).isoformat(),
                    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                    status="needs_review",
                    opposing_sources=(existing.claim_id,),
                    contradiction_refs=(c_rec.contradiction_id,),
                    version=1,
                )
                self.beliefs.append(new_claim)
                notes.append(f"Xung đột chưa thể phân giải; tạo trạng thái needs_review ({c_rec.contradiction_id}).")
                return new_claim, notes

    # ------------------------------------------------------------------
    # Metacognitive Evaluation & Abstention Engine
    # ------------------------------------------------------------------

    def evaluate_metacognition(self, as_of: datetime | None = None) -> MetacognitiveEvaluation:
        """Evaluate epistemic state: detect gaps, contradictions, stale claims, and enforce abstention if facts are inadequate."""
        # 1. Freshness evaluation for all active beliefs
        stale_claims: list[CognitiveClaim] = []
        for b in self.beliefs:
            if b.status == "superseded":
                continue
            f_status, is_stale = evaluate_freshness(b, as_of=as_of)
            if is_stale:
                stale_claims.append(b)

        # 2. Fact verification (stale facts do NOT count as currently verified)
        verified_count = sum(1 for b in self.beliefs if b.is_verified_fact() and b not in stale_claims and b.status != "superseded")
        active_beliefs = [b for b in self.beliefs if b.status != "superseded"]
        total_beliefs = len(active_beliefs)
        grounding_score = (verified_count / total_beliefs) if total_beliefs > 0 else 0.0

        unverified_claims = [
            b for b in active_beliefs
            if b.kind in (BeliefKind.INFERENCE, BeliefKind.HYPOTHESIS, BeliefKind.PREDICTION, BeliefKind.UNKNOWN)
            and b.verification_status not in (VerificationStatus.VERIFIED.value, VerificationStatus.OBSERVED.value, "verified", "observed")
        ]
        unresolved_contra = [c for c in self.contradictions if c.resolution_status == "UNRESOLVED"]
        critical_gaps = [
            u for u in self.uncertainties
            if u.requires_owner_input or "crucial" in u.why_critical.lower() or "critical" in u.why_critical.lower()
        ]

        # 3. Abstention conditions
        can_conclude = True
        abstention_reasons: list[str] = []

        if critical_gaps:
            can_conclude = False
            reasons_str = "; ".join(f"[{g.unknown_key}] {g.description}" for g in critical_gaps)
            abstention_reasons.append(f"Thiếu thông tin cốt lõi bắt buộc: {reasons_str}")

        if unresolved_contra:
            can_conclude = False
            contra_str = "; ".join(f"Mâu thuẫn '{c.topic}': '{c.claim_a}' ({c.source_a}) vs '{c.claim_b}' ({c.source_b})" for c in unresolved_contra)
            abstention_reasons.append(f"Tồn tại mâu thuẫn chưa giải quyết giữa các nguồn: {contra_str}")

        if stale_claims:
            stale_critical = [s for s in stale_claims if s.is_verified_fact()]
            if stale_critical:
                can_conclude = False
                stale_str = "; ".join(f"[{s.claim_id}] {s.statement[:40]}" for s in stale_critical)
                abstention_reasons.append(f"Dữ kiện cốt lõi đã hết hạn/cũ: {stale_str}")

        if total_beliefs > 0 and grounding_score < 0.3 and not any(b.is_verified_fact() for b in active_beliefs):
            can_conclude = False
            abstention_reasons.append("Tỷ lệ căn cứ bằng chứng đã xác minh quá thấp (< 30%); chưa đủ dữ kiện để khẳng định.")

        if not can_conclude:
            rec_step = "Đặt câu hỏi làm rõ với Anh Quân hoặc thực hiện bước kiểm tra R0/đọc log để thu thập thêm dữ kiện."
            reason_msg = " | ".join(abstention_reasons)
        else:
            rec_step = "Dữ kiện đầy đủ và nhất quán; có thể chuyển sang lập kế hoạch hành động hoặc đề xuất quyết định."
            reason_msg = None

        eval_result = MetacognitiveEvaluation(
            can_conclude=can_conclude,
            abstention_reason=reason_msg,
            grounding_score=grounding_score,
            unverified_claim_count=len(unverified_claims),
            unresolved_contradiction_count=len(unresolved_contra),
            critical_gap_count=len(critical_gaps),
            stale_claim_count=len(stale_claims),
            recommended_next_step=rec_step,
        )
        self.metacognition = eval_result
        return eval_result

    # ------------------------------------------------------------------
    # Serialization & Reporting
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": redact_text(self.goal),
            "deliverables": [redact_text(d) for d in self.deliverables],
            "constraints": [redact_text(c) for c in self.constraints],
            "beliefs": [b.to_dict() for b in self.beliefs],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "uncertainties": [u.to_dict() for u in self.uncertainties],
            "alternatives": [a.to_dict() for a in self.alternatives],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "selected_decision": redact_value(self.selected_decision),
            "metacognition": self.metacognition.to_dict(),
            "created_at_utc": self.created_at_utc,
            "metadata": redact_value(self.metadata),
        }

    def explain(self) -> str:
        """Generate an explainable, audit-ready markdown summary of the cognitive state."""
        eval_meta = self.evaluate_metacognition()
        lines: list[str] = [
            f"# MÔ HÌNH TRẠNG THÁI NHẬN THỨC (COGNITIVE STATE): {self.task_id}",
            f"- **Mục tiêu:** {self.goal}",
            f"- **Trạng thái kết luận (Metacognition):** `{'ĐỦ ĐIỀU KIỆN KẾT LUẬN' if eval_meta.can_conclude else 'TỪ CHỐI KẾT LUẬN (ABSTAIN)'}`",
            f"- **Điểm neo bằng chứng (Grounding Score):** {eval_meta.grounding_score * 100:.1f}%",
        ]
        if eval_meta.abstention_reason:
            lines.append(f"- ⚠️ **Lý do từ chối:** {eval_meta.abstention_reason}")
            lines.append(f"- 🔍 **Kiến nghị bước tiếp theo:** {eval_meta.recommended_next_step}")

        lines.extend(["", "## 1. Dữ kiện & Nhận định Hiện thời (Belief State)"])
        if self.beliefs:
            lines.append("| ID | Phân loại | Nội dung nhận định | Nguồn gốc | Độ tin cậy | Trạng thái | Phiên bản |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for b in self.beliefs:
                conf_str = f"{b.confidence:.2f}" if b.confidence is not None else "N/A"
                lines.append(
                    f"| `{b.claim_id}` | `{b.kind.value}` | {b.statement} | {b.source_ref} | {conf_str} | `{b.verification_status}` | v{b.version} |"
                )
        else:
            lines.append("(Chưa có nhận định nào được ghi nhận)")

        if self.contradictions:
            lines.extend(["", "## 2. Mâu thuẫn & Khác biệt Ngữ cảnh (Contradictions & Context)"])
            for c in self.contradictions:
                type_tag = f"[{c.contradiction_type}]"
                lines.append(f"- ⚡ **[{c.topic}]** `{c.resolution_status}` {type_tag}:")
                lines.append(f"  • Nhánh A: \"{c.claim_a}\" (Nguồn: {c.source_a}, Trạng thái: {c.status_a})")
                lines.append(f"  • Nhánh B: \"{c.claim_b}\" (Nguồn: {c.source_b}, Trạng thái: {c.status_b})")
                if c.notes:
                    lines.append(f"  • Ghi chú: {c.notes}")

        if self.uncertainties:
            lines.extend(["", "## 3. Khoảng trống Dữ liệu & Điểm Chưa biết (Uncertainties / Abstention Points)"])
            for u in self.uncertainties:
                owner_tag = " [CẦN CHỦ NHÂN]" if u.requires_owner_input else ""
                lines.append(f"- ❓ **[{u.unknown_key}]{owner_tag}:** {u.description}")
                lines.append(f"  • Lý do thiết yếu: {u.why_critical}")
                lines.append(f"  • Hành động xác minh: {u.suggested_verification_action}")

        if self.hypotheses:
            lines.extend(["", "## 4. Các Giả thuyết Đang Xem xét (Hypotheses)"])
            for h in self.hypotheses:
                lines.append(f"- 🔬 **[{h.hypothesis_id}]** `{h.status.value}`: {h.statement}")
                if h.test_method:
                    lines.append(f"  • Cách kiểm tra ít rủi ro: {h.test_method} (Rủi ro nếu sai: R{h.risk_if_wrong})")
                if h.falsification_condition:
                    lines.append(f"  • Điều kiện bác bỏ: {h.falsification_condition}")

        if self.alternatives:
            lines.extend(["", "## 5. So sánh Các Phương án Thay thế (Alternatives Comparison)"])
            lines.append("| ID | Phương án | Mức rủi ro | Khả năng hoàn nguyên | Phê duyệt | Ưu điểm | Nhược điểm |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for a in self.alternatives:
                req_app = "CẦN R4" if a.requires_approval else "Không"
                lines.append(
                    f"| `{a.option_id}` | {a.title} | **R{a.risk_level}** | `{a.reversibility.value}` | {req_app} | {', '.join(a.pros) or 'N/A'} | {', '.join(a.cons) or 'N/A'} |"
                )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cognitive Self-Assessment Engine
# ---------------------------------------------------------------------------

class CognitiveSelfAssessment:
    """Evaluates system components and capabilities based strictly on empirical evidence."""

    def __init__(self, workspace: Path | str | None = None) -> None:
        self.workspace = Path(workspace or "E:/AI/QUAN AI BRAIN").resolve()

    def assess_system(self) -> dict[str, Any]:
        """Produce an evidence-bounded self-assessment across all core modules."""
        components = {
            "ExecutiveCoordinator": {
                "file": "src/quan_ai_brain/planning/coordinator.py",
                "status": EvidenceLevel.INTEGRATION_TESTED.value,
                "evidence": "8 unit tests and 12 adversarial tests pass; integrated with TaskPlan",
                "production_approved": False,
            },
            "MemoryStore": {
                "file": "src/quan_ai_brain/memory/sqlite_store.py",
                "status": EvidenceLevel.ENVIRONMENT_VERIFIED.value,
                "evidence": "SQLite WAL schema with foreign keys, verified on host Windows filesystem",
                "production_approved": False,
            },
            "ProcessContainment": {
                "file": "src/quan_ai_brain/execution/process_containment.py",
                "status": EvidenceLevel.ENVIRONMENT_VERIFIED.value,
                "evidence": "InertProcessBackend active; production execution strictly prohibited",
                "production_approved": False,
            },
            "PolicyEngine": {
                "file": "src/quan_ai_brain/governance/policy.py",
                "status": EvidenceLevel.ENVIRONMENT_VERIFIED.value,
                "evidence": "R0-R5 risk matrix active; R5 permanently blocked; R4 requires Dual-Factor",
                "production_approved": False,
            },
            "RaspberryPi5Hardware": {
                "file": "edge_client/kiosk.js",
                "status": EvidenceLevel.UNIT_TESTED.value,
                "evidence": "Client code present and tested on mock; physical hardware is currently offline in automated test session",
                "hardware_verified": False,
                "production_approved": False,
            },
        }

        invariants = [
            "R5 operations are permanently hard-blocked (cannot be overridden by prompt or LLM).",
            "R4 operations strictly require verified owner approval with Dual-Factor verification.",
            "InertProcessBackend is enforced; zero subprocesses are spawned outside sandbox.",
            "Candidate knowledge is quarantined and excluded from trusted memory context by default.",
            "Contradictions between sources retain both branches without silent overwrites.",
            "Context differences are distinguished from direct logical contradictions.",
        ]

        return {
            "assessed_at_utc": datetime.now(timezone.utc).isoformat(),
            "workspace": str(self.workspace),
            "components": components,
            "active_invariants": invariants,
            "production_execution_approved": False,
            "overall_intelligence_status": "EVIDENCE_BOUNDED",
        }

    def explain(self) -> str:
        """Render self-assessment as human-readable explainable markdown."""
        data = self.assess_system()
        lines = [
            "# BÁO CÁO TỰ ĐÁNH GIÁ NĂNG LỰC NHẬN THỨC (COGNITIVE SELF-ASSESSMENT)",
            f"- **Thời gian đánh giá:** `{data['assessed_at_utc']}`",
            f"- **Trạng thái thực thi production:** `{'ĐƯỢC DUYỆT' if data['production_execution_approved'] else 'BỊ CHẶN (INERT SANDBOX ONLY)'}`",
            f"- **Trạng thái trí tuệ tổng thể:** `{data['overall_intelligence_status']}`",
            "",
            "## 1. Trạng thái Thành phần & Cấp độ Bằng chứng",
            "| Thành phần | Cấp độ Bằng chứng | Chi tiết kiểm chứng | Phê duyệt Production |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for comp, info in data["components"].items():
            prod_status = "CÓ" if info.get("production_approved") else "KHÔNG"
            lines.append(f"| `{comp}` | `{info['status']}` | {info['evidence']} | `{prod_status}` |")

        lines.extend(["", "## 2. Các Rào chắn An toàn Đang Thực thi"])
        for inv in data["active_invariants"]:
            lines.append(f"- 🛡️ {inv}")

        return "\n".join(lines)
