"""Knowledge Ingestion Pipeline for QUAN AI BRAIN — Sprint 3.

Implements a truthful, provenance-tracked pipeline for ingesting knowledge from
authorized sources, with versioning, verification cycles, and conflict detection.

Pipeline: INGEST → VALIDATE → PARSE → CHUNK → EMBED → INDEX → RETRIEVE → RERANK → BUILD_CONTEXT → ANSWER_WITH_PROVENANCE

Giai đoạn Sprint 3 (2026-10-25): Core ingestion with provenance, version, conflict detection.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


class KnowledgeSource(str, Enum):
    """Trusted knowledge source types."""
    OWNER_DOCUMENT = "OWNER_DOCUMENT"       # Tài liệu do anh Quân cung cấp
    PROJECT_DOCS = "PROJECT_DOCS"           # Tài liệu dự án nội bộ
    TECHNICAL_SPEC = "TECHNICAL_SPEC"       # Tài liệu kỹ thuật chính thức
    TEST_EVIDENCE = "TEST_EVIDENCE"         # Kết quả kiểm thử đã xác minh
    WORKFLOW_LOG = "WORKFLOW_LOG"           # Log công việc đã hoàn thành
    OWNER_FEEDBACK = "OWNER_FEEDBACK"       # Phản hồi trực tiếp từ anh Quân
    EXTERNAL_UNVERIFIED = "EXTERNAL_UNVERIFIED"  # Nguồn ngoài chưa xác minh


class VerificationState(str, Enum):
    """Verification lifecycle state."""
    QUARANTINED = "quarantined"         # Cách ly, chờ xem xét
    UNDER_REVIEW = "under_review"       # Đang xem xét
    APPROVED = "approved"               # Đã phê duyệt
    REJECTED = "rejected"               # Từ chối
    EXPIRED = "expired"                 # Hết hạn xem xét lại
    CONFLICTED = "conflicted"           # Xung đột với kiến thức khác


@dataclass
class KnowledgeProvenance:
    """Full provenance trail for a knowledge item."""
    source_type: KnowledgeSource
    source_ref: str                     # Path/URL/ID of source document
    source_version: str                 # Version/hash of source
    ingested_at: str                    # ISO timestamp
    ingested_by: str                    # Who/what ingested this
    verification_state: VerificationState
    verified_at: str | None = None
    verified_by: str | None = None
    review_notes: str = ""
    expires_at: str | None = None       # When to re-review
    conflict_ids: list[str] = field(default_factory=list)  # Conflicting knowledge IDs

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
            "source_version": self.source_version,
            "ingested_at": self.ingested_at,
            "ingested_by": self.ingested_by,
            "verification_state": self.verification_state.value,
            "verified_at": self.verified_at,
            "verified_by": self.verified_by,
            "review_notes": self.review_notes,
            "expires_at": self.expires_at,
            "conflict_ids": self.conflict_ids,
        }


@dataclass
class KnowledgeRecord:
    """A single piece of ingested knowledge."""
    id: str
    statement: str                      # Normalized knowledge statement
    normalized_statement: str           # Lowercase, stripped for comparison
    content_snippet: str                # Original snippet (redacted if needed)
    provenance: KnowledgeProvenance
    confidence_score: float = 1.0       # 0.0-1.0 based on source reliability
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "normalized_statement": self.normalized_statement,
            "content_snippet": self.content_snippet,
            "provenance": self.provenance.to_dict(),
            "confidence_score": round(self.confidence_score, 3),
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison (lowercase, strip, collapse whitespace)."""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text


class KnowledgeIngestionEngine:
    """Manages the full knowledge ingestion pipeline with provenance and conflict detection."""

    def __init__(self, store: MemoryStore, owner_id: str = "Quanpt1") -> None:
        self.store = store
        self.owner_id = owner_id
        self._source_reliability: dict[KnowledgeSource, float] = {
            KnowledgeSource.OWNER_DOCUMENT: 0.95,
            KnowledgeSource.PROJECT_DOCS: 0.90,
            KnowledgeSource.TECHNICAL_SPEC: 0.92,
            KnowledgeSource.TEST_EVIDENCE: 0.98,
            KnowledgeSource.WORKFLOW_LOG: 0.85,
            KnowledgeSource.OWNER_FEEDBACK: 0.97,
            KnowledgeSource.EXTERNAL_UNVERIFIED: 0.30,
        }

    def ingest(
        self,
        content: str,
        source_type: KnowledgeSource,
        source_ref: str,
        source_version: str = "unknown",
        tags: list[str] | None = None,
        expires_days: int | None = None,
    ) -> KnowledgeRecord:
        """Ingest new knowledge from a source.

        Steps:
        1. VALIDATE: Check source type, ref format
        2. PARSE: Extract statements (simplified for Sprint 3)
        3. CONFLICT CHECK: Compare with existing knowledge
        4. STORE: Save to candidate_knowledge with QUARANTINED state
        5. INDEX: Prepare for embedding (Sprint 3: placeholder)

        Returns the created KnowledgeRecord.
        """
        # 1. Validate
        if not content.strip():
            raise ValueError("Content must be non-empty")
        if not source_ref.strip():
            raise ValueError("Source ref must be non-empty")

        # 2. Parse (simplified: treat entire content as one statement for Sprint 3)
        # In Sprint 5+, this will use LLM to extract multiple facts
        statement = content.strip()
        normalized = KnowledgeRecord.normalize_text(statement)

        # 3. Conflict detection
        conflict_ids = self._detect_conflicts(normalized)

        # 4. Create provenance
        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_days:
            from datetime import timedelta
            expires_at = (now + timedelta(days=expires_days)).isoformat()

        provenance = KnowledgeProvenance(
            source_type=source_type,
            source_ref=source_ref,
            source_version=source_version,
            ingested_at=now.isoformat(),
            ingested_by=self.owner_id,
            verification_state=VerificationState.QUARANTINED,
            expires_at=expires_at,
            conflict_ids=conflict_ids,
        )

        # 5. Create record
        record_id = f"know_{uuid.uuid4().hex[:12]}"
        confidence = self._source_reliability.get(source_type, 0.5)
        if conflict_ids:
            confidence *= 0.5  # Reduce confidence if conflicts exist

        record = KnowledgeRecord(
            id=record_id,
            statement=statement,
            normalized_statement=normalized,
            content_snippet=content[:500],  # Truncate for storage
            provenance=provenance,
            confidence_score=confidence,
            tags=tags or [],
        )

        # 6. Store in candidate_knowledge table
        self._store_candidate(record)

        return record

    def _detect_conflicts(self, normalized_statement: str) -> list[str]:
        """Detect conflicting knowledge by semantic similarity (Sprint 3: keyword overlap)."""
        # Sprint 3: Simple keyword overlap detection
        # Sprint 5+: Use BGE-M3 embedding for semantic conflict detection
        tokens = set(re.findall(r"[\w\u00C0-\u1EF9]+", normalized_statement))
        if len(tokens) < 3:
            return []

        # Query existing candidate knowledge
        conflicts: list[str] = []
        candidates = self.store._connection.execute(
            "SELECT id, statement FROM candidate_knowledge WHERE status = 'quarantined'"
        ).fetchall()

        for cand_id, cand_stmt in candidates:
            cand_tokens = set(re.findall(r"[\w\u00C0-\u1EF9]+", cand_stmt.lower()))
            overlap = tokens & cand_tokens
            if len(overlap) >= 3:  # Significant overlap
                # Check for negation patterns (simplified)
                if any(neg in normalized_statement for neg in ["không", "không phải", "không có"]):
                    conflicts.append(cand_id)
                elif any(neg in cand_stmt for neg in ["không", "không phải", "không có"]):
                    conflicts.append(cand_id)

        return conflicts

    def _store_candidate(self, record: KnowledgeRecord) -> None:
        """Store knowledge record in candidate_knowledge table."""
        now = datetime.now(timezone.utc).isoformat()
        self.store._connection.execute(
            """
            INSERT INTO candidate_knowledge (
                id, created_at_utc, statement, source_ref, rationale, status, decision_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                now,
                record.statement,
                json.dumps(record.provenance.to_dict()),
                f"Confidence: {record.confidence_score:.2f}; Tags: {', '.join(record.tags)}",
                VerificationState.QUARANTINED.value,
                f"Pending owner review. Conflicts: {len(record.provenance.conflict_ids)}",
            ),
        )
        self.store._connection.commit()

    def approve_knowledge(self, record_id: str, approved_by: str, notes: str = "") -> bool:
        """Approve a quarantined knowledge item, moving it to verified state."""
        # Update candidate_knowledge status
        cur = self.store._connection.execute(
            "SELECT id, statement FROM candidate_knowledge WHERE id = ? AND status = 'quarantined'",
            (record_id,)
        )
        row = cur.fetchone()
        if not row:
            return False

        # Move to semantic_memory (simplified for Sprint 3)
        now = datetime.now(timezone.utc).isoformat()
        self.store._connection.execute(
            """
            INSERT INTO semantic_memory (
                id, created_at_utc, statement, source_ref, approved_by, regression_passed
            ) VALUES (?, ?, ?, ?, ?, 1)
            """,
            (record_id, now, row[1], row[1], approved_by),  # source_ref = statement for now
        )

        # Update candidate status
        self.store._connection.execute(
            "UPDATE candidate_knowledge SET status = 'approved', decision_note = ? WHERE id = ?",
            (notes or "Approved by owner", record_id)
        )
        self.store._connection.commit()
        return True

    def reject_knowledge(self, record_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a quarantined knowledge item."""
        cur = self.store._connection.execute(
            "SELECT id FROM candidate_knowledge WHERE id = ? AND status = 'quarantined'",
            (record_id,)
        )
        if not cur.fetchone():
            return False

        self.store._connection.execute(
            "UPDATE candidate_knowledge SET status = 'rejected', decision_note = ? WHERE id = ?",
            (reason, record_id)
        )
        self.store._connection.commit()
        return True

    def list_quarantined(self, limit: int = 50) -> list[dict[str, Any]]:
        """List all quarantined knowledge items awaiting review."""
        rows = self.store._connection.execute(
            """
            SELECT id, created_at_utc, statement, source_ref, status, decision_note
            FROM candidate_knowledge
            WHERE status = 'quarantined'
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [
            {
                "id": row[0],
                "created_at": row[1],
                "statement": row[2],
                "source_ref": row[3],
                "status": row[4],
                "notes": row[5],
            }
            for row in rows
        ]

    def get_conflicts(self, record_id: str) -> list[dict[str, Any]]:
        """Get conflicting knowledge items for a given record."""
        # Fetch record's provenance
        cur = self.store._connection.execute(
            "SELECT source_ref FROM candidate_knowledge WHERE id = ?", (record_id,)
        )
        row = cur.fetchone()
        if not row:
            return []

        try:
            provenance = json.loads(row[0])
            conflict_ids = provenance.get("conflict_ids", [])
        except (json.JSONDecodeError, TypeError):
            return []

        # Fetch conflict details
        conflicts = []
        for cid in conflict_ids:
            cur = self.store._connection.execute(
                "SELECT id, statement, status FROM candidate_knowledge WHERE id = ?", (cid,)
            )
            crow = cur.fetchone()
            if crow:
                conflicts.append({"id": crow[0], "statement": crow[1], "status": crow[2]})

        return conflicts