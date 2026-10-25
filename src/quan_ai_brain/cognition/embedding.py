"""BGE-M3 Dense Embedding Service and Semantic Similarity for QUAN AI BRAIN.

Provides:
- Integration with local Ollama BGE-M3 embedding endpoint.
- In-memory vector caching for fast repeated lookups.
- Standard-library cosine similarity computation without requiring numpy or PyTorch.
- Transparent offline fallback with explainable status.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from quan_ai_brain.llm.client import OllamaClient

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors using standard library math.
    
    Returns float in range [-1.0, 1.0], or 0.0 if either vector is zero/empty or lengths mismatch.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot_product = 0.0
    norm_v1_sq = 0.0
    norm_v2_sq = 0.0

    for a, b in zip(v1, v2):
        dot_product += a * b
        norm_v1_sq += a * a
        norm_v2_sq += b * b

    if norm_v1_sq <= 0.0 or norm_v2_sq <= 0.0:
        return 0.0

    norm = math.sqrt(norm_v1_sq) * math.sqrt(norm_v2_sq)
    if norm <= 0.0:
        return 0.0

    return max(-1.0, min(1.0, dot_product / norm))


class BGEEmbeddingService:
    """Embedding service managing BGE-M3 vector generation and caching."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        model_name: str = "bge-m3",
        max_cache_entries: int = 2000,
        timeout: float = 10.0,
    ) -> None:
        self.client = client or OllamaClient(default_timeout=timeout)
        self.model_name = model_name
        self.max_cache_entries = max(100, max_cache_entries)
        self.timeout = timeout
        self._cache: dict[str, list[float]] = {}
        self._cache_keys: list[str] = []

    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable and responding."""
        return self.client.ping(timeout=0.5)

    def embed_text(self, text: str) -> list[float]:
        """Generate or retrieve cached 1024-dim BGE-M3 dense embedding for text."""
        cleaned = text.strip()
        if not cleaned:
            return []

        # Check cache
        cache_key = f"{self.model_name}::{cleaned}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            vector = self.client.embed(
                text=cleaned,
                model=self.model_name,
                timeout=self.timeout,
            )
        except Exception as exc:
            logger.warning("BGE-M3 embedding failed via Ollama: %s", exc)
            return []

        if vector:
            self._put_cache(cache_key, vector)

        return vector

    def _put_cache(self, key: str, vector: list[float]) -> None:
        """Store embedding in bounded FIFO cache."""
        if key not in self._cache:
            self._cache_keys.append(key)
        self._cache[key] = vector

        # Evict oldest if exceeding limit
        if len(self._cache_keys) > self.max_cache_entries:
            oldest_key = self._cache_keys.pop(0)
            self._cache.pop(oldest_key, None)

    def compute_similarity(self, text_or_vec_a: str | list[float], text_or_vec_b: str | list[float]) -> float:
        """Compute cosine similarity between two texts or vectors."""
        vec_a = self.embed_text(text_or_vec_a) if isinstance(text_or_vec_a, str) else text_or_vec_a
        vec_b = self.embed_text(text_or_vec_b) if isinstance(text_or_vec_b, str) else text_or_vec_b

        return cosine_similarity(vec_a, vec_b)

    def stats(self) -> dict[str, Any]:
        """Return diagnostic metrics of embedding cache and service health."""
        return {
            "model_name": self.model_name,
            "cached_entries": len(self._cache),
            "max_cache_entries": self.max_cache_entries,
            "is_available": self.is_available(),
        }
