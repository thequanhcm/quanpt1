"""
Standalone, Zero-Dependency Reference Implementation of BGE-M3 Hybrid Retrieval.
Can be copied directly into any Python project (3.10+) without third-party dependencies.
"""

from __future__ import annotations

import io
import json
import math
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

# Ensure UTF-8 output on Windows consoles to support Vietnamese diacritics
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


@dataclass
class MemoryRecord:
    id: str
    content: str
    memory_type: str = "EPISODIC"  # EPISODIC, SEMANTIC, PROCEDURAL, CANDIDATE
    status: str = "ACTIVE"         # ACTIVE, VERIFIED, QUARANTINED, ARCHIVED
    scope: str = "PROJECT"         # GLOBAL, PROJECT, PRIVATE
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


def pure_cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Pure Python cosine similarity - zero dependency on numpy or scipy."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class LocalBGEEmbeddingClient:
    """Ollama-backed BGE-M3 embedding client with connection safety and bounded FIFO cache."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,
        model: str = "bge-m3",
        cache_size: int = 2000,
        timeout: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.model = model
        self.timeout = timeout
        self.cache_size = cache_size
        self._cache: dict[str, list[float]] = {}
        self._cache_keys: list[str] = []

    def is_available(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=1.0):
                return True
        except OSError:
            return False

    def embed(self, text: str) -> list[float] | None:
        cleaned = text.strip()
        if not cleaned:
            return None

        # Check cache
        if cleaned in self._cache:
            return self._cache[cleaned]

        url = f"http://{self.host}:{self.port}/api/embeddings"
        payload = json.dumps({"model": self.model, "prompt": cleaned}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                vector = data.get("embedding")
                if not vector or not isinstance(vector, list):
                    return None

                # Maintain bounded FIFO cache
                if len(self._cache_keys) >= self.cache_size:
                    oldest = self._cache_keys.pop(0)
                    self._cache.pop(oldest, None)
                self._cache[cleaned] = vector
                self._cache_keys.append(cleaned)
                return vector
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None


class HybridRetriever:
    """
    Multi-signal Hybrid Search Engine.
    Combines:
      - Lexical token overlap (BM25-approximated)
      - Dense semantic vector similarity (BGE-M3 1024-dim)
      - Memory type weighting (PROCEDURAL > SEMANTIC > EPISODIC)
      - Verification status weighting (VERIFIED > ACTIVE > QUARANTINED)
      - Strict candidate quarantine enforcement
    """

    TYPE_WEIGHTS = {
        "PROCEDURAL": 1.0,
        "SEMANTIC": 0.85,
        "EPISODIC": 0.70,
        "CANDIDATE": 0.20,
    }

    STATUS_WEIGHTS = {
        "VERIFIED": 1.0,
        "ACTIVE": 0.85,
        "QUARANTINED": 0.10,
        "ARCHIVED": 0.05,
    }

    def __init__(self, embedding_client: LocalBGEEmbeddingClient | None = None) -> None:
        self.client = embedding_client
        self.records: list[MemoryRecord] = []

    def add_record(self, record: MemoryRecord, compute_embedding: bool = True) -> None:
        if compute_embedding and self.client and not record.embedding:
            record.embedding = self.client.embed(record.content)
        self.records.append(record)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_candidates: bool = False,
    ) -> list[tuple[MemoryRecord, float, dict[str, float]]]:
        if not self.records:
            return []

        q_clean = query.strip()
        q_tokens = set(q_clean.lower().split())

        # Generate query embedding if client is active
        q_vec = self.client.embed(q_clean) if self.client else None

        scored: list[tuple[MemoryRecord, float, dict[str, float]]] = []

        for record in self.records:
            # QUARANTINE ENFORCEMENT: block CANDIDATE or QUARANTINED items unless requested
            if not include_candidates:
                if record.memory_type == "CANDIDATE" or record.status == "QUARANTINED":
                    continue

            # 1. Lexical Score (token overlap ratio)
            content_lower = record.content.lower()
            rec_tokens = set(content_lower.split())
            if q_tokens and rec_tokens:
                overlap = len(q_tokens & rec_tokens)
                lexical_score = overlap / len(q_tokens)
            else:
                lexical_score = 0.0

            # 2. Dense Semantic Score
            dense_score = 0.0
            if q_vec and record.embedding:
                dense_score = pure_cosine_similarity(q_vec, record.embedding)

            # 3. Metadata weights
            type_weight = self.TYPE_WEIGHTS.get(record.memory_type, 0.5)
            status_weight = self.STATUS_WEIGHTS.get(record.status, 0.5)

            # 4. Composite Hybrid Formula
            # 0.25 Lexical + 0.35 Dense Semantic + 0.25 Type + 0.15 Status
            composite_score = (
                0.25 * lexical_score
                + 0.35 * dense_score
                + 0.25 * type_weight
                + 0.15 * status_weight
            )

            metrics = {
                "composite": composite_score,
                "lexical": lexical_score,
                "dense": dense_score,
                "type_weight": type_weight,
                "status_weight": status_weight,
            }
            scored.append((record, composite_score, metrics))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# --- SELF-TEST / DEMONSTRATION ---
if __name__ == "__main__":
    print("Testing Standalone Hybrid Retriever with BGE-M3...")
    client = LocalBGEEmbeddingClient()
    available = client.is_available()
    print(f"Ollama server online: {available}")

    retriever = HybridRetriever(embedding_client=client if available else None)

    # Populate sample memories
    retriever.add_record(MemoryRecord(
        id="mem-001",
        content="Quy trình xả bảo dưỡng chuỗi ắc quy UPS Emerson 40 bình phòng máy chủ.",
        memory_type="PROCEDURAL",
        status="VERIFIED",
    ))
    retriever.add_record(MemoryRecord(
        id="mem-002",
        content="Nhiệt độ môi trường phòng máy vượt quá 32 độ C gây phồng bình ắc quy.",
        memory_type="SEMANTIC",
        status="ACTIVE",
    ))
    retriever.add_record(MemoryRecord(
        id="mem-003",
        content="Gợi ý chưa được duyệt: Thay đổi ngưỡng cảnh báo điện áp tế bào xuống 1.75V.",
        memory_type="CANDIDATE",
        status="QUARANTINED",
    ))

    query = "Cách xả nạp định kỳ bình lưu điện data center"
    print(f"\nQuery: '{query}'")
    results = retriever.retrieve(query, top_k=3, include_candidates=False)

    for rank, (rec, score, met) in enumerate(results, 1):
        print(f"#{rank} [Score: {score:.3f} | Dense: {met['dense']:.3f} | Lex: {met['lexical']:.3f}] - {rec.content}")
