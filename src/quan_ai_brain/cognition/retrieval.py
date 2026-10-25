"""Cognitive Memory Retriever for QUAN AI BRAIN.

Retrieves and ranks relevant long-term memories using transparent, explainable
scoring based on keyword overlap, memory type priority, verification status,
and project scope alignment.
"""
from __future__ import annotations

import re
import time
from typing import Any

from quan_ai_brain.cognition.models import (
    MEMORY_TYPE_WEIGHTS,
    VERIFICATION_STATUS_WEIGHTS,
    MemoryQuery,
    RetrievalResult,
    RetrievedMemory,
)
from quan_ai_brain.cognition.embedding import BGEEmbeddingService
from quan_ai_brain.memory.models import LifecycleStatus, MemoryRecord, MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words/terms, preserving diacritics and alphanumeric tokens."""
    tokens = re.findall(r"[\w\u00C0-\u1EF9]+", text.lower())
    return [t for t in tokens if len(t) > 1]


class CognitiveRetriever:
    """Retrieves relevant memories from MemoryStore with deterministic ranking and optional BGE-M3 hybrid scoring."""

    def __init__(self, store: MemoryStore, embedding_service: BGEEmbeddingService | None = None) -> None:
        self.store = store
        self.embedding_service = embedding_service

    def retrieve(self, query: MemoryQuery | str, **kwargs: Any) -> RetrievalResult:
        start_time = time.perf_counter()
        if isinstance(query, str):
            query = MemoryQuery(query=query, **kwargs)

        allowed_types = query.normalized_memory_types()
        allowed_statuses = query.normalized_verification_statuses()
        lifecycle_val = (
            query.lifecycle_status.value
            if isinstance(query.lifecycle_status, LifecycleStatus)
            else str(query.lifecycle_status)
        )

        query_tokens = _tokenize(query.query)
        candidates_map: dict[str, MemoryRecord] = {}

        # 1. First probe exact query string match
        exact_matches = self.store.search_memories(
            query=query.query.strip(),
            lifecycle_status=lifecycle_val,
            limit=50,
        )
        for rec in exact_matches:
            candidates_map[rec.id] = rec

        # 2. Token-level probing for broader recall (top terms)
        for token in query_tokens[:6]:
            token_matches = self.store.search_memories(
                query=token,
                lifecycle_status=lifecycle_val,
                limit=30,
            )
            for rec in token_matches:
                candidates_map[rec.id] = rec

        # 3. If project_scope is specified, fetch scope memories for contextual recall
        if query.project_scope:
            scope_matches = self.store.search_memories(
                query="",
                project_scope=query.project_scope,
                lifecycle_status=lifecycle_val,
                limit=30,
            )
            for rec in scope_matches:
                candidates_map[rec.id] = rec

        # 3.1 If semantic embedding service is active, fetch broader memory candidates for dense matching
        if self.embedding_service:
            dense_candidates = self.store.search_memories(
                query="",
                project_scope=query.project_scope,
                lifecycle_status=lifecycle_val,
                limit=100,
            )
            for rec in dense_candidates:
                candidates_map[rec.id] = rec

        # 4. Filter and score candidates
        scored_memories: list[RetrievedMemory] = []
        for rec in candidates_map.values():
            # Filter memory type
            if rec.memory_type not in allowed_types:
                continue

            # Quarantine rule: CANDIDATE memory is never allowed in trusted pool
            # unless explicitly requested with include_candidates=True
            if rec.memory_type == MemoryType.CANDIDATE.value and not query.include_candidates:
                continue

            # Filter verification status
            if rec.verification_status not in allowed_statuses:
                continue

            # Scope alignment check: if query has scope, don't include irrelevant other scopes
            if query.project_scope and rec.project_scope not in (query.project_scope, "general"):
                continue

            # Calculate explainable score
            score, reason = self._score_memory(rec, query, query_tokens)
            if score <= 0.0:
                continue

            is_allowed = (
                rec.memory_type != MemoryType.CANDIDATE.value
                and rec.verification_status in (
                    VerificationStatus.VERIFIED.value,
                    VerificationStatus.USER_PROVIDED.value,
                    VerificationStatus.OBSERVED.value,
                )
            )

            scored_memories.append(
                RetrievedMemory(
                    memory_id=rec.id,
                    memory_type=rec.memory_type,
                    content=rec.content,
                    source_ref=rec.source_ref,
                    verification_status=rec.verification_status,
                    confidence_score=rec.confidence_score,
                    project_scope=rec.project_scope,
                    version=rec.version,
                    score=score,
                    selection_reason=reason,
                    is_allowed_in_prompt=is_allowed,
                    tags=rec.tags,
                    created_at_utc=rec.created_at_utc,
                )
            )

        # 5. Sort descending by explainable score, break ties by version and created_at
        scored_memories.sort(
            key=lambda m: (m.score, m.confidence_score, m.version, m.created_at_utc),
            reverse=True,
        )

        # 6. Apply top_k
        selected = scored_memories[: query.top_k]

        total_chars = sum(len(m.content) for m in selected)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return RetrievalResult(
            query=query.query,
            memories=selected,
            total_found=len(scored_memories),
            total_chars=total_chars,
            elapsed_ms=elapsed_ms,
            query_params={
                "project_scope": query.project_scope,
                "top_k": query.top_k,
                "max_chars": query.max_chars,
                "allowed_types": allowed_types,
                "allowed_statuses": allowed_statuses,
            },
        )

    def _score_memory(
        self,
        record: MemoryRecord,
        query: MemoryQuery,
        query_tokens: list[str],
    ) -> tuple[float, str]:
        """Compute transparent, explainable ranking score in range [0.0, 1.0]."""
        content_lower = record.content.lower()
        reasons: list[str] = []

        # 1. Keyword match score [0.0 - 1.0]
        keyword_score = 0.0
        if query.query.lower() in content_lower:
            keyword_score = 1.0
            reasons.append("exact_phrase_match")
        elif query_tokens:
            matched_tokens = [t for t in query_tokens if t in content_lower]
            overlap_ratio = len(matched_tokens) / len(query_tokens)
            keyword_score = overlap_ratio

            # Tag match bonus
            tags_lower = [t.lower() for t in record.tags]
            matched_tags = [t for t in query_tokens if t in tags_lower]
            if matched_tags:
                keyword_score = min(1.0, keyword_score + 0.25)
                reasons.append(f"tag_match({','.join(matched_tags)})")

            if matched_tokens:
                reasons.append(f"token_overlap({len(matched_tokens)}/{len(query_tokens)})")

        # 1.1 BGE-M3 Dense Semantic Similarity [0.0 - 1.0]
        dense_similarity = 0.0
        if self.embedding_service:
            try:
                raw_sim = self.embedding_service.compute_similarity(query.query, record.content)
                dense_similarity = max(0.0, raw_sim)
                if dense_similarity >= 0.4:
                    reasons.append(f"bge_m3_semantic({dense_similarity:.2f})")
            except Exception:
                dense_similarity = 0.0

        # If zero keyword overlap and query has tokens:
        if keyword_score == 0.0 and query_tokens:
            if dense_similarity >= 0.50:
                reasons.append("semantic_dense_match")
            elif query.project_scope and record.project_scope == query.project_scope:
                keyword_score = 0.2  # Contextual background baseline
                reasons.append("scope_only_match")
            else:
                return 0.0, "no_keyword_overlap"

        # 2. Memory Type weight
        type_weight = MEMORY_TYPE_WEIGHTS.get(record.memory_type, 0.5)

        # 3. Verification Status weight
        verification_weight = VERIFICATION_STATUS_WEIGHTS.get(record.verification_status, 0.3)

        # 4. Scope alignment bonus
        scope_score = 0.5
        if query.project_scope:
            if record.project_scope == query.project_scope:
                scope_score = 1.0
                reasons.append("exact_scope_match")
            elif record.project_scope == "general":
                scope_score = 0.7
                reasons.append("general_scope_fallback")
            else:
                scope_score = 0.2

        # 5. Composite weighted score (Hybrid if BGE-M3 present, else classic lexical)
        if self.embedding_service and dense_similarity > 0.0:
            raw_score = (
                keyword_score * 0.25
                + dense_similarity * 0.30
                + type_weight * 0.25
                + verification_weight * 0.15
                + scope_score * 0.05
            )
        else:
            raw_score = (
                keyword_score * 0.45
                + type_weight * 0.25
                + verification_weight * 0.20
                + scope_score * 0.10
            )
        final_score = raw_score * float(record.confidence_score)

        reason_str = (
            f"Type={record.memory_type}({type_weight:.2f}), "
            f"Status={record.verification_status}({verification_weight:.2f}), "
            f"Matches=[{'; '.join(reasons)}]"
        )
        return final_score, reason_str
