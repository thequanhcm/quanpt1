"""Data models and enums for QUAN AI BRAIN Cognitive Retrieval & Context Building."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any

from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.memory.models import LifecycleStatus, MemoryType, VerificationStatus


# Weights for explainable ranking
MEMORY_TYPE_WEIGHTS: dict[str, float] = {
    MemoryType.SEMANTIC.value: 1.0,      # Facts, verified knowledge
    MemoryType.PROCEDURAL.value: 0.95,   # Tested SOPs, workflows
    MemoryType.DECISION.value: 0.90,     # Past decisions & rationale
    MemoryType.PREFERENCE.value: 0.85,   # User preferences & priorities
    MemoryType.EPISODIC.value: 0.70,     # Events and task records
    MemoryType.CANDIDATE.value: 0.15,    # Quarantined candidates
}

VERIFICATION_STATUS_WEIGHTS: dict[str, float] = {
    VerificationStatus.VERIFIED.value: 1.0,        # Independently verified
    VerificationStatus.USER_PROVIDED.value: 0.85,  # Provided by user
    VerificationStatus.OBSERVED.value: 0.80,       # Observed by system
    VerificationStatus.INFERRED.value: 0.40,       # Model/rule inferred
    VerificationStatus.UNVERIFIED.value: 0.30,     # Not yet verified
    VerificationStatus.CANDIDATE.value: 0.10,      # In quarantine
}


@dataclass
class MemoryQuery:
    """Validated query parameters for cognitive memory retrieval."""
    query: str
    project_scope: str | None = None
    memory_types: list[MemoryType | str] = field(default_factory=lambda: [
        MemoryType.SEMANTIC,
        MemoryType.PROCEDURAL,
        MemoryType.DECISION,
        MemoryType.PREFERENCE,
        MemoryType.EPISODIC,
    ])
    allowed_verification_statuses: list[VerificationStatus | str] = field(default_factory=lambda: [
        VerificationStatus.VERIFIED,
        VerificationStatus.USER_PROVIDED,
        VerificationStatus.OBSERVED,
    ])
    top_k: int = 5
    max_chars: int = 4000
    include_candidates: bool = False
    lifecycle_status: LifecycleStatus | str = LifecycleStatus.ACTIVE

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("Query must be a non-empty string")
        if len(self.query) > 5000:
            raise ValueError("Query exceeds maximum allowed length (5000 characters)")

        if not isinstance(self.top_k, int) or not (1 <= self.top_k <= 50):
            raise ValueError("top_k must be an integer between 1 and 50")

        if not isinstance(self.max_chars, int) or not (100 <= self.max_chars <= 50_000):
            raise ValueError("max_chars budget must be an integer between 100 and 50,000")

        if self.project_scope is not None and not isinstance(self.project_scope, str):
            raise TypeError("project_scope must be a string or None")

    def normalized_memory_types(self) -> list[str]:
        result: list[str] = []
        for mt in self.memory_types:
            val = mt.value if isinstance(mt, MemoryType) else str(mt)
            if val not in result:
                result.append(val)
        return result

    def normalized_verification_statuses(self) -> list[str]:
        result: list[str] = []
        for vs in self.allowed_verification_statuses:
            val = vs.value if isinstance(vs, VerificationStatus) else str(vs)
            if val not in result:
                result.append(val)
        return result


@dataclass
class RetrievedMemory:
    """A scored, explainable memory item retrieved from Long-Term Memory."""
    memory_id: str
    memory_type: str
    content: str
    source_ref: str
    verification_status: str
    confidence_score: float
    project_scope: str
    version: int
    score: float
    selection_reason: str
    is_allowed_in_prompt: bool
    tags: list[str] = field(default_factory=list)
    created_at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "content": redact_text(self.content),
            "source_ref": redact_text(self.source_ref),
            "verification_status": self.verification_status,
            "confidence_score": self.confidence_score,
            "project_scope": self.project_scope,
            "version": self.version,
            "score": round(self.score, 4),
            "selection_reason": self.selection_reason,
            "is_allowed_in_prompt": self.is_allowed_in_prompt,
            "tags": self.tags,
            "created_at_utc": self.created_at_utc,
        }


@dataclass
class RetrievalResult:
    """The complete result set of a memory retrieval operation."""
    query: str
    memories: list[RetrievedMemory]
    total_found: int
    total_chars: int
    elapsed_ms: float = 0.0
    query_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": redact_text(self.query),
            "memories": [m.to_dict() for m in self.memories],
            "total_found": self.total_found,
            "total_chars": self.total_chars,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "query_params": redact_value(self.query_params),
        }


@dataclass
class BuiltContext:
    """Rendered context ready for LLM inference, with complete provenance audit."""
    rendered_context: str
    system_instructions: str
    user_query: str
    used_memories: list[RetrievedMemory]
    excluded_memories: list[tuple[str, str]]  # list of (memory_id, reason)
    total_chars: int
    is_truncated: bool
    section_stats: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rendered_context": redact_text(self.rendered_context),
            "system_instructions": self.system_instructions,
            "user_query": redact_text(self.user_query),
            "used_memory_ids": [m.memory_id for m in self.used_memories],
            "excluded_memories": self.excluded_memories,
            "total_chars": self.total_chars,
            "is_truncated": self.is_truncated,
            "section_stats": self.section_stats,
            "metadata": redact_value(self.metadata),
        }


class GroundingStatus(str, Enum):
    """Categorization of grounding evidence in model responses."""
    VERIFIED_FACT = "verified_fact"           # Directly supported by independently verified long-term memory
    USER_PROVIDED = "user_provided"           # Grounded in user-stated instructions, identity, or preferences
    GENERAL_INFERENCE = "general_inference"   # General reasoning by LLM without direct memory citation
    MIXED = "mixed"                           # Both verified facts and model inference
    UNVERIFIED = "unverified"                 # Grounded only in unverified or candidate knowledge


@dataclass
class GroundingAnalysis:
    """Evaluation of grounding evidence supporting an assistant response."""
    status: GroundingStatus
    confidence: str  # HIGH, MEDIUM, LOW
    cited_memory_ids: list[str] = field(default_factory=list)
    cited_sources: list[str] = field(default_factory=list)
    inferred_elements: list[str] = field(default_factory=list)
    has_unverified_claims: bool = False
    grounding_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "confidence": self.confidence,
            "cited_memory_ids": self.cited_memory_ids,
            "cited_sources": [redact_text(s) for s in self.cited_sources],
            "inferred_elements": [redact_text(e) for e in self.inferred_elements],
            "has_unverified_claims": self.has_unverified_claims,
            "grounding_notes": redact_text(self.grounding_notes),
        }

