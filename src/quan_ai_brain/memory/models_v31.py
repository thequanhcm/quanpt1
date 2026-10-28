"""Enhanced data models for V31 Memory Intelligence.

Extends existing models with:
- Full provenance tracking
- Temporal awareness
- Version history
- Conflict tracking
- Quality scoring
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any

from quan_ai_brain.memory.models import MemoryType, VerificationStatus, LifecycleStatus


class KnowledgeType(str, Enum):
    """Type of knowledge unit."""
    FACT = "FACT"           # Asserted fact
    OPINION = "OPINION"     # Opinion or belief
    QUESTION = "QUESTION"   # Question or inquiry
    RULE = "RULE"           # Rule or constraint
    PROCESS = "PROCESS"     # Procedure or workflow
    CONCLUSION = "CONCLUSION"  # Inferred conclusion


class ConflictType(str, Enum):
    """Type of conflict between knowledge units."""
    SEMANTIC = "SEMANTIC"      # Contradictory meaning
    TEMPORAL = "TEMPORAL"      # Time-based contradiction
    LOGICAL = "LOGICAL"        # Logical inconsistency
    SOURCE = "SOURCE"          # Different sources, same claim


class ResolutionStatus(str, Enum):
    """Status of conflict resolution."""
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    PENDING_REVIEW = "pending_review"


@dataclass
class VersionEntry:
    """Entry in version history."""
    version: int
    changed_fields: list[str]
    changed_by: str
    changed_at: str
    reason: str
    content_hash: str
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'VersionEntry':
        return cls(**data)


@dataclass
class KnowledgeProvenanceV31:
    """Enhanced provenance with full lineage tracking."""
    # Source information
    source_type: str  # KnowledgeSource value
    source_ref: str   # Path/URL/ID
    source_version: str  # Version/hash of source
    
    # Ingestion metadata
    ingested_at: str
    ingested_by: str
    
    # Verification
    verification_state: str  # VerificationState value
    verified_at: str | None = None
    verified_by: str | None = None
    review_notes: str = ""
    
    # Temporal
    effective_from: str | None = None  # When knowledge became effective
    effective_until: str | None = None  # When knowledge expired
    observed_at: str | None = None  # When event was observed
    
    # Conflict tracking
    expires_at: str | None = None
    conflict_ids: list[str] = field(default_factory=list)
    
    # Lineage
    derived_from: list[str] = field(default_factory=list)  # Parent knowledge IDs
    supersedes: list[str] = field(default_factory=list)  # IDs this replaces
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "source_version": self.source_version,
            "ingested_at": self.ingested_at,
            "ingested_by": self.ingested_by,
            "verification_state": self.verification_state,
            "verified_at": self.verified_at,
            "verified_by": self.verified_by,
            "review_notes": self.review_notes,
            "effective_from": self.effective_from,
            "effective_until": self.effective_until,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "conflict_ids": self.conflict_ids,
            "derived_from": self.derived_from,
            "supersedes": self.supersedes,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'KnowledgeProvenanceV31':
        return cls(
            source_type=data["source_type"],
            source_ref=data["source_ref"],
            source_version=data["source_version"],
            ingested_at=data["ingested_at"],
            ingested_by=data["ingested_by"],
            verification_state=data["verification_state"],
            verified_at=data.get("verified_at"),
            verified_by=data.get("verified_by"),
            review_notes=data.get("review_notes", ""),
            effective_from=data.get("effective_from"),
            effective_until=data.get("effective_until"),
            observed_at=data.get("observed_at"),
            expires_at=data.get("expires_at"),
            conflict_ids=data.get("conflict_ids", []),
            derived_from=data.get("derived_from", []),
            supersedes=data.get("supersedes", []),
        )


@dataclass
class KnowledgeUnit:
    """Enhanced knowledge unit with full V31 features."""
    # Core identity
    id: str
    content: str  # Original text (redacted if needed)
    knowledge_type: str  # KnowledgeType value
    
    # Provenance
    provenance: KnowledgeProvenanceV31
    
    # Temporal awareness
    effective_from: str | None = None
    effective_until: str | None = None
    observed_at: str | None = None
    
    # Relationships (IDs of related knowledge units)
    supports: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    
    # Versioning
    version: int = 1
    version_history: list[VersionEntry] = field(default_factory=list)
    superseded_by: str | None = None
    superseded_at: str | None = None
    
    # Status
    lifecycle_status: str = LifecycleStatus.ACTIVE.value
    quality_score: float = 0.0  # 0-1, computed
    
    # Metadata
    tags: list[str] = field(default_factory=list)
    project_scope: str = "general"
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "knowledge_type": self.knowledge_type,
            "provenance": self.provenance.to_dict(),
            "effective_from": self.effective_from,
            "effective_until": self.effective_until,
            "observed_at": self.observed_at,
            "supports": self.supports,
            "contradicts": self.contradicts,
            "derived_from": self.derived_from,
            "depends_on": self.depends_on,
            "version": self.version,
            "version_history": [v.to_dict() for v in self.version_history],
            "superseded_by": self.superseded_by,
            "superseded_at": self.superseded_at,
            "lifecycle_status": self.lifecycle_status,
            "quality_score": round(self.quality_score, 3),
            "tags": self.tags,
            "project_scope": self.project_scope,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'KnowledgeUnit':
        provenance = KnowledgeProvenanceV31.from_dict(data["provenance"])
        version_history = [
            VersionEntry.from_dict(v) for v in data.get("version_history", [])
        ]
        return cls(
            id=data["id"],
            content=data["content"],
            knowledge_type=data["knowledge_type"],
            provenance=provenance,
            effective_from=data.get("effective_from"),
            effective_until=data.get("effective_until"),
            observed_at=data.get("observed_at"),
            supports=data.get("supports", []),
            contradicts=data.get("contradicts", []),
            derived_from=data.get("derived_from", []),
            depends_on=data.get("depends_on", []),
            version=int(data.get("version", 1)),
            version_history=version_history,
            superseded_by=data.get("superseded_by"),
            superseded_at=data.get("superseded_at"),
            lifecycle_status=data.get("lifecycle_status", LifecycleStatus.ACTIVE.value),
            quality_score=float(data.get("quality_score", 0.0)),
            tags=data.get("tags", []),
            project_scope=data.get("project_scope", "general"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
    
    @classmethod
    def from_legacy_memory_record(cls, record: Any) -> 'KnowledgeUnit':
        """Convert legacy MemoryRecord to KnowledgeUnit."""
        from quan_ai_brain.memory.knowledge_ingestion import KnowledgeSource, VerificationState
        
        # Create basic provenance from legacy record
        provenance = KnowledgeProvenanceV31(
            source_type="PROJECT_DOCS",
            source_ref=record.source_ref or "unknown",
            source_version="v1",
            ingested_at=record.created_at_utc or "",
            ingested_by="migration_v31",
            verification_state=record.verification_status or VerificationState.UNVERIFIED.value,
            verified_at=None,
            verified_by=None,
            review_notes="Migrated from legacy system",
            effective_from=None,
            effective_until=None,
            observed_at=None,
            expires_at=None,
            conflict_ids=[],
            derived_from=[],
            supersedes=[],
        )
        
        # Map knowledge type
        knowledge_type = KnowledgeType.FACT.value
        content_lower = record.content.lower()
        if any(marker in content_lower for marker in ["gì", "nào", "bao nhiêu", "có phải", "không?"]):
            knowledge_type = KnowledgeType.QUESTION.value
        elif any(marker in content_lower for marker in ["luôn", "phải", "quy tắc", "không được"]):
            knowledge_type = KnowledgeType.RULE.value
        elif any(marker in content_lower for marker in ["tôi nghĩ", "có lẽ", "có thể"]):
            knowledge_type = KnowledgeType.OPINION.value
        elif any(marker in content_lower for marker in ["vậy nên", "kết luận", "tóm lại"]):
            knowledge_type = KnowledgeType.CONCLUSION.value
        
        return cls(
            id=record.id,
            content=record.content,
            knowledge_type=knowledge_type,
            provenance=provenance,
            version=record.version or 1,
            superseded_by=record.superseded_by,
            lifecycle_status=record.lifecycle_status or LifecycleStatus.ACTIVE.value,
            quality_score=record.confidence_score or 0.0,
            tags=record.tags or [],
            project_scope=record.project_scope or "general",
            created_at=record.created_at_utc or "",
            updated_at=record.updated_at_utc or "",
        )