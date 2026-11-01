# V37.2 Long-Term Memory with Vector DB — Design & Implementation Plan

## Overview

V37.2 implements **tiered long-term memory** using vector database (ChromaDB) to enable semantic search and retrieval of knowledge across sessions.

## Architecture

### Memory Tiers

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY TIERS                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. SHORT-TERM (Session Memory)                              │
│     └─ SQLite brain.db (current session)                    │
│     └─ Ephemeral, fast access                                │
│     └─ Conversation context, working memory                  │
│                                                              │
│  2. LONG-TERM (Vector DB)                                    │
│     └─ ChromaDB persistent store                             │
│     └─ Semantic search, embedding-based retrieval            │
│     └─ All knowledge chunks with embeddings                  │
│                                                              │
│  3. VERIFIED KNOWLEDGE (USER_PROVIDED)                       │
│     └─ Owner-validated knowledge                             │
│     └─ High-priority retrieval                               │
│     └─ Provenance tracking, audit trail                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input → Knowledge Extraction → Chunking → Embedding → Vector Store
                                                      ↓
                                              Semantic Search
                                                      ↓
                                              Ranked Results
                                                      ↓
                                              Response Generation
```

## Components

### 1. MemoryChunk (`vector_store.py`)

**Purpose:** Unit of storage in vector DB

**Fields:**
- `id`: Unique identifier
- `content`: Text content (chunked for better retrieval)
- `memory_type`: EPISODIC, SEMANTIC, PROCEDURAL, DECISION, PREFERENCE
- `source_ref`: Origin (chat ID, document, observation)
- `verification_status`: USER_PROVIDED, VERIFIED, OBSERVED, INFERRED, UNVERIFIED
- `tags`: Categorization labels
- `metadata`: Additional context (timestamps, relationships)
- `embedding`: Vector representation (1024 dims with BGE)

**Chunking Strategy:**
- Split by sentences (configurable chunk size, default 500 chars)
- Preserve source metadata in each chunk
- Link chunks to original memory record

### 2. LongTermMemoryStore

**Purpose:** ChromaDB wrapper with business logic

**Key Methods:**

```python
# Add memories
add_memory(chunk: MemoryChunk) -> str
add_memories_batch(chunks: List[MemoryChunk]) -> int

# Search
search(query: str, n_results: int, filters: dict) -> dict
search_by_verification(query: str, verification_status: str) -> List[dict]
search_user_provided(query: str) -> List[dict]

# Utilities
get_stats() -> dict
delete_chunk(chunk_id: str) -> bool
export_to_json(path: str) -> int
import_from_json(path: str) -> int
```

**Features:**
- Persistent storage (disk-based)
- Automatic embedding generation
- Filter by verification status, memory type, tags
- Similarity search with distance scoring
- Batch operations for efficiency

### 3. MemoryTieringEngine

**Purpose:** Manage memory lifecycle across tiers

**Tiering Operations:**

```python
tier_memory(record: dict, target_tier: str) -> str
# target_tier: "long_term", "verified", "user_provided"

retrieve_with_tiering(query: str, require_verified: bool) -> List[dict]
# Returns ranked results (verified > user_provided > inferred > unverified)
```

**Lifecycle:**
1. **Ingestion:** Raw knowledge → Long-term (UNVERIFIED)
2. **Validation:** Owner review → Verified status
3. **Retrieval:** Tier-aware ranking (verified prioritized)

## API Integration

### Endpoints to Add

```python
# Knowledge retrieval
GET /api/memory/search?q={query}&verified_only={true|false}
GET /api/memory/user-provided?q={query}
GET /api/memory/stats

# Memory management
POST /api/memory/ingest
POST /api/memory/verify/{id}
POST /api/memory/reject/{id}

# Bulk operations
POST /api/memory/batch-ingest
GET /api/memory/export
POST /api/memory/import
```

## Installation

### Dependencies

```toml
[project.optional-dependencies]
memory = ["chromadb>=1.0.0", "sentence-transformers>=2.0"]
all = ["chromadb>=1.0.0", "sentence-transformers>=2.0"]
```

### Install Command

```bash
# Install with memory support
pip install -e ".[memory]"

# Or install all dependencies
pip install -e ".[all]"
```

**Note:** ChromaDB installation may take 2-5 minutes due to dependencies.

### Initialize Vector DB

```python
from quan_ai_brain.memory.vector_store import create_memory_store
from quan_ai_brain.cognition.embedding import BGEEmbeddingService

# Create embedding service
embedding_service = BGEEmbeddingService(model_name="bge-m3")

# Create memory store
memory_store = create_memory_store(
    db_path="data/vector_db",
    embedding_service=embedding_service
)

# Verify
stats = memory_store.get_stats()
print(f"Vector DB initialized: {stats['total_chunks']} chunks")
```

## Usage Examples

### 1. Ingest Owner Knowledge

```python
from quan_ai_brain.memory.vector_store import MemoryChunk, MemoryTieringEngine
from quan_ai_brain.memory.models import MemoryType, VerificationStatus

# Create tiering engine
engine = MemoryTieringEngine(memory_store)

# Owner provides knowledge
owner_knowledge = {
    "id": "owner_ats_rule_001",
    "content": "ATS should switch to backup when voltage drops below 180V for more than 5 seconds.",
    "memory_type": MemoryType.RULE.value,
    "source_ref": "owner_chat_2026-10-28",
    "verification_status": VerificationStatus.USER_PROVIDED.value,
    "tags": ["ats", "rule", "owner", "voltage"],
    "created_at_utc": "2026-10-28T10:00:00Z"
}

# Tier to USER_PROVIDED
result = engine.tier_memory(owner_knowledge, target_tier="user_provided")
print(result)  # "Added X chunks to long-term memory"
```

### 2. Semantic Search

```python
# Search all knowledge
results = memory_store.search("ATS voltage threshold", n_results=5)

# Search only verified
verified_results = memory_store.search_by_verification("battery specification")

# Search owner-provided knowledge
owner_knowledge = memory_store.search_user_provided("ATS switching rule")

# Search with filters
filtered = memory_store.search(
    "electrical safety",
    filters={
        "verification_status": VerificationStatus.VERIFIED.value,
        "memory_type": MemoryType.RULE.value
    }
)
```

### 3. Tier-Aware Retrieval

```python
# Retrieve with verified preference (for critical decisions)
critical_info = engine.retrieve_with_tiering(
    "UPS battery voltage",
    require_verified=True,
    n_results=3
)

# Retrieve from all tiers (for general questions)
general_info = engine.retrieve_with_tiering(
    "How does ATS work?",
    require_verified=False,
    n_results=5
)
```

### 4. Batch Ingestion

```python
# Prepare multiple chunks
chunks = []
for record in knowledge_records:
    record_chunks = MemoryChunk.from_memory_record(record)
    chunks.extend(record_chunks)

# Batch add (efficient)
added = memory_store.add_memories_batch(chunks)
print(f"Added {added} chunks to vector DB")
```

## Performance Considerations

### Embedding Generation

- **Model:** BGE-M3 (1024 dimensions)
- **Latency:** ~50-100ms per chunk (warm)
- **Batching:** Process in batches of 32-64 for efficiency

### Vector Search

- **Index:** ChromaDB HNSW (default)
- **Latency:** ~10-50ms for 1000 chunks
- **Scalability:** Up to 100K+ chunks with good performance

### Storage

- **Per chunk:** ~5KB (content + metadata + embedding)
- **1000 chunks:** ~5MB
- **10,000 chunks:** ~50MB

## Migration Plan

### Phase 1: Setup (Current)
- [x] Create `vector_store.py` with ChromaDB integration
- [x] Implement MemoryChunk and chunking logic
- [x] Add search and filtering capabilities
- [x] Create tiering engine
- [x] Write unit tests
- [ ] Install ChromaDB dependencies
- [ ] Initialize vector DB on production system

### Phase 2: Data Ingestion
- [ ] Export existing knowledge from brain.db
- [ ] Convert to MemoryChunk format
- [ ] Batch ingest into vector DB
- [ ] Verify chunk count and quality
- [ ] Test search functionality

### Phase 3: Integration
- [ ] Add API endpoints for search/retrieval
- [ ] Integrate with existing conversation flow
- [ ] Implement tier-aware retrieval in responses
- [ ] Add caching layer for frequent queries
- [ ] Monitor performance and optimize

### Phase 4: Dashboard Integration
- [ ] Add vector DB stats to Knowledge Dashboard
- [ ] Show embedding coverage
- [ ] Display search quality metrics
- [ ] Enable manual re-ingestion

### Phase 5: Optimization
- [ ] Implement incremental indexing
- [ ] Add query optimization
- [ ] Fine-tune chunk size and overlap
- [ ] Add query expansion/re-ranking
- [ ] Implement hybrid search (keyword + vector)

## Testing

### Unit Tests

Run tests:
```bash
pytest tests/test_v37_2_vector_memory.py -v
```

**Test Coverage:**
- Memory chunk creation and splitting
- Vector store add/search operations
- Filter functionality
- Tiering engine logic
- Export/import operations
- Integration workflows

### Integration Tests

**Test Scenarios:**
1. Ingest owner knowledge → Search → Verify retrieval
2. Batch ingest 100+ chunks → Search → Check performance
3. Tier-aware retrieval → Verify ranking
4. Export → Clear → Import → Verify data integrity

## Monitoring

### Metrics to Track

- **Total chunks:** Growth over time
- **Search latency:** P50, P95, P99
- **Embedding latency:** Cold vs warm
- **Retrieval quality:** User feedback (thumbs up/down)
- **Tier distribution:** % verified, user_provided, etc.

### Logs

```python
# Ingestion
logger.info(f"Ingested {added} chunks from {len(records)} records")

# Search
logger.debug(f"Search '{query}' returned {len(results)} results in {latency}ms")

# Tiering
logger.info(f"Tiered memory {memory_id} to {tier} with status {status}")
```

## Owner Decision Required

### 1. Initial Data to Ingest

**Question:** Anh muốn em lập danh sách dữ liệu nào để nạp ban đầu vào vector DB?

**Options:**
1. **Existing brain.db knowledge** - Export 150 KUs from current SQLite
2. **Owner chat history** - Extract USER_PROVIDED from past conversations
3. **Technical documentation** - Ingest system docs, SOPs, manuals
4. **All of the above** - Comprehensive initial load

**Recommendation:** Start with #1 (existing brain.db) + #2 (owner chats) for quick win.

### 2. Chunk Size Configuration

**Current:** 500 characters per chunk

**Options:**
- **300 chars:** More granular, better precision, more chunks
- **500 chars:** Balanced (current default)
- **800 chars:** Fewer chunks, better context, lower precision

**Recommendation:** Start with 500, adjust based on search quality feedback.

### 3. Embedding Model

**Current:** BGE-M3 (1024 dims, multilingual)

**Alternatives:**
- **bge-large-zh:** Better for Chinese/Vietnamese
- **multilingual-e5:** Strong multilingual support
- **Custom fine-tune:** Train on domain-specific data

**Recommendation:** Keep BGE-M3 for now (good Vietnamese support), fine-tune later if needed.

## Next Steps

1. **Owner approves** this design
2. **Install dependencies:** `pip install -e ".[memory]"`
3. **Initialize vector DB:** Run initialization script
4. **Select initial data:** Owner chooses data sources (see questions above)
5. **Ingest data:** Batch load into vector DB
6. **Test search:** Verify retrieval quality
7. **Integrate API:** Add endpoints to existing server
8. **Deploy:** Update production system

## Success Criteria

V37.2 is complete when:

1. ✅ Vector DB initialized with 100+ chunks
2. ✅ Semantic search returns relevant results (user-validated)
3. ✅ Tier-aware retrieval prioritizes verified knowledge
4. ✅ Search latency < 100ms for 1000 chunks
5. ✅ API endpoints functional and tested
6. ✅ Dashboard shows vector DB stats
7. ✅ Owner can ingest new knowledge via API
8. ✅ No regression in existing memory functionality

---

**Status:** Design complete, ready for implementation  
**Files created:** `vector_store.py` (450 lines), tests (400 lines)  
**Next:** Owner approval + dependency installation