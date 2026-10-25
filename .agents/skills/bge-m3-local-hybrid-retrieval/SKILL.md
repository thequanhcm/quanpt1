---
name: bge-m3-local-hybrid-retrieval
description: |
  Deploy, integrate, and operate local BGE-M3 dense embeddings and multi-signal hybrid semantic retrieval.
  Use when building or upgrading:
    1. Local semantic memory, RAG, or cognitive search for AI assistants and autonomous agents.
    2. Zero-dependency embedding pipelines (pure Python standard library: urllib, json, math - no PyTorch/FAISS needed).
    3. Multi-lingual semantic similarity (Vietnamese, English, Chinese) running locally on Ollama.
    4. Hybrid retrieval architectures combining lexical keyword match (sparse) with dense vector cosine similarity and metadata weighting.
    5. Safe cognitive memory systems with strict candidate quarantine boundaries and regression testing.
license: Apache-2.0
metadata:
  version: v1.0.0
  publisher: QUAN AI BRAIN / DC-OS Engineering
---

# BGE-M3 Local Hybrid Semantic Retrieval Engine

A production-grade, zero-dependency skill for embedding local knowledge and executing hybrid (lexical + dense semantic + metadata-weighted) retrieval using BAAI/bge-m3 via local Ollama.

> [!IMPORTANT]
> **Zero External Dependency Guarantee**: This skill uses only the Python Standard Library (`urllib`, `json`, `math`, `socket`, `time`, `sqlite3`). No PyTorch, Sentence-Transformers, ONNX runtime, or heavyweight vector databases (ChromaDB, Pinecone, FAISS) are required unless explicitly opted into.

---

## 1. Architecture Overview

```
User Query / Task
       │
       ▼
┌────────────────────────────────────────────────────────┐
│             Pre-Flight Availability Probe              │
│    socket.create_connection(("127.0.0.1", 11434))     │
└───────────────────┬────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
 [Ollama Online]         [Ollama Offline]
        │                       │
 ┌──────┴───────────────┐       ▼
 │  BGE-M3 1024-dim     │  Degrade Gracefully to
 │  Dense Embedding     │  Lexical + Metadata Search
 │  (FIFO Bounded Cache)│       │
 └──────┬───────────────┘       │
        │                       │
        ▼                       ▼
┌────────────────────────────────────────────────────────┐
│           Hybrid Multi-Signal Ranking Engine           │
│                                                        │
│  Score = 0.25 * Lexical(BM25/Overlap)                  │
│        + 0.35 * Dense_Semantic(Cosine_Similarity)      │
│        + 0.25 * Memory_Type_Weight                     │
│        + 0.15 * Verification_Status_Weight             │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│          Strict Cognitive Quarantine Boundary          │
│                                                        │
│  BLOCK all CANDIDATE / QUARANTINED records from prompt │
│  injection unless explicitly flagged for owner review. │
└───────────────────┬────────────────────────────────────┘
                    │
                    ▼
         Verified Top-K Context
```

---

## 2. Infrastructure Setup: Ollama & BGE-M3

### Pull and Verify BGE-M3 Model
BGE-M3 is an embedding model trained by BAAI featuring:
- **Dense representation**: 1024 dimensions.
- **Context window**: Up to 8192 tokens.
- **Multi-lingual support**: Exceptional performance on Vietnamese, English, Chinese, and cross-lingual technical terminology.
- **Low hardware footprint**: ~1.2 GB download, ~664 MB VRAM when active in Ollama.

Run in terminal:
```bash
ollama pull bge-m3
```

Verify model is loaded:
```bash
ollama list
```
Expected output:
```text
NAME            ID              SIZE      MODIFIED
bge-m3:latest   967b5744cf24    1.2 GB    ...
```

---

## 3. Standard Library Embedding Client

Use this zero-dependency client pattern in your codebase. It provides:
1. Fast TCP connection check before making HTTP requests.
2. In-memory FIFO bounded cache to avoid redundant GPU calls on recurrent queries.
3. Clean timeout and error isolation.

```python
import json
import socket
import urllib.error
import urllib.request


class LocalBGEEmbeddingClient:
    """Ollama-backed BGE-M3 embedding client using only standard library."""

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
        """Pre-flight check: returns True if Ollama port is open, False otherwise."""
        try:
            with socket.create_connection((self.host, self.port), timeout=1.0):
                return True
        except OSError:
            return False

    def embed(self, text: str) -> list[float] | None:
        """Generate 1024-dim embedding vector with FIFO cache."""
        cleaned = text.strip()
        if not cleaned:
            return None

        # Cache lookup
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
```

---

## 4. Pure Python Cosine Similarity (No NumPy/SciPy)

Avoid heavy dependencies by computing cosine similarity directly in standard Python:

```python
import math


def pure_cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors. Range: [0.0, 1.0]."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))
```

---

## 5. Multi-Signal Hybrid Scoring Formula

Single-signal vector search suffers from false positives on exact keyword IDs (e.g. `UPS-BATT-042`, error codes `E104`), while keyword search fails on semantic paraphrasing. The hybrid formula balances both:

$$Score = w_{lex} \cdot S_{lex} + w_{dense} \cdot S_{dense} + w_{type} \cdot W_{type} + w_{status} \cdot W_{status}$$

### Recommended Weights:
- **Lexical Score ($S_{lex}$, weight 0.25)**: Token overlap or BM25 ratio.
- **Dense Semantic Score ($S_{dense}$, weight 0.35)**: BGE-M3 cosine similarity.
- **Memory Type Weight ($W_{type}$, weight 0.25)**:
  - `PROCEDURAL`: 1.0 (Audited standard operating procedures)
  - `SEMANTIC`: 0.85 (Factual domain knowledge)
  - `EPISODIC`: 0.70 (Historical action traces)
  - `CANDIDATE`: 0.20 (Unverified proposals)
- **Status Weight ($W_{status}$, weight 0.15)**:
  - `VERIFIED`: 1.0 (Human-approved)
  - `ACTIVE`: 0.85 (Standard operational memory)
  - `QUARANTINED`: 0.10 (Pending review)
  - `ARCHIVED`: 0.05 (Deprecated)

### Candidate Generation Bottleneck (Crucial Pattern)
> [!CAUTION]
> If using SQL `WHERE content LIKE ?` to fetch candidate rows before computing cosine similarity, a query with **zero** lexical overlap will return 0 rows, completely defeating the purpose of semantic search!
>
> **Pattern to follow**: When semantic search is enabled, retrieve an unconstrained candidate pool (e.g. `LIMIT 100` most recent / high-relevance memories), calculate dense cosine similarity across the pool, and then rank by the composite score.

---

## 6. Strict Quarantine Boundary

Never allow unverified AI thoughts, self-generated hypotheses, or untrusted user input to enter the production context without isolation:

```python
# Boundary Enforcement Rule
if not include_candidates:
    if record.memory_type == "CANDIDATE" or record.status == "QUARANTINED":
        continue  # Hard-block from LLM prompt injection
```

---

## 7. Verification & Automated Test Harness

Always include two tiers of tests:
1. **Offline Mock Test**: Tests cosine math, cache bounding, and hybrid ranking with mocked vector responses (runs in CI without Ollama).
2. **Live Integration Probe**: Tests actual connectivity to Ollama port 11434 and verifies 1024-dim output.

```python
def test_bge_m3_live_probe():
    client = LocalBGEEmbeddingClient()
    if not client.is_available():
        pytest.skip("Local Ollama daemon not running on port 11434")

    emb = client.embed("Kiểm tra điện áp bình ắc quy")
    assert emb is not None
    assert len(emb) == 1024
    assert all(isinstance(x, float) for x in emb)
```

Run test suite:
```bash
pytest tests/test_bge_m3_embedding.py -v
```

---

## 8. Directory Reference & Ready-To-Use Files
- **Verification Script**: `scripts/verify_bge_m3.py`
  - Run via: `python <path>/scripts/verify_bge_m3.py`
- **Standalone Reference Implementation**: `examples/standalone_hybrid_retriever.py`
  - Drop-in standalone script for any new AI project.
