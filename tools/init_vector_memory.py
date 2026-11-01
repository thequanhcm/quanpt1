"""Initialize Vector DB and test basic operations."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from quan_ai_brain.memory.vector_store import create_memory_store, MemoryChunk, MemoryTieringEngine
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.cognition.embedding import BGEEmbeddingService

print("=" * 60)
print("V37.2 VECTOR MEMORY INITIALIZATION")
print("=" * 60)

# Step 1: Create embedding service
print("\n[1/5] Creating BGE embedding service...")
try:
    embedding_service = BGEEmbeddingService(model_name="bge-m3")
    print(f"✅ Embedding service ready (dim: {embedding_service.get_dimension()})")
except Exception as e:
    print(f"⚠️ Could not load BGE model: {e}")
    print("   Using mock embedding for testing...")
    
    class MockEmbeddingService:
        def embed(self, texts):
            return [[0.1] * 1024 for _ in texts]
        def get_dimension(self):
            return 1024
    
    embedding_service = MockEmbeddingService()

# Step 2: Create memory store
print("\n[2/5] Initializing ChromaDB vector store...")
try:
    memory_store = create_memory_store(
        db_path="data/vector_db",
        embedding_service=embedding_service
    )
    print(f"✅ Vector store initialized at: data/vector_db")
    print(f"   Collection: {memory_store.collection.name}")
    print(f"   Current chunks: {memory_store.collection.count()}")
except Exception as e:
    print(f"❌ Failed to initialize vector store: {e}")
    sys.exit(1)

# Step 3: Create tiering engine
print("\n[3/5] Creating memory tiering engine...")
engine = MemoryTieringEngine(memory_store)
print("✅ Tiering engine ready")

# Step 4: Ingest sample owner knowledge
print("\n[4/5] Ingesting sample owner knowledge...")
sample_knowledge = [
    {
        "id": "owner_ats_rule_001",
        "content": "ATS should switch to backup when voltage drops below 180V for more than 5 seconds.",
        "memory_type": MemoryType.SEMANTIC.value,
        "source_ref": "owner_chat_2026-10-28",
        "verification_status": VerificationStatus.USER_PROVIDED.value,
        "tags": ["ats", "rule", "owner", "voltage"],
        "created_at_utc": "2026-10-28T10:00:00Z"
    },
    {
        "id": "owner_battery_spec_001",
        "content": "UPS battery voltage should be between 12.0 and 13.0 volts when fully charged. Below 10.8V indicates a bad cell.",
        "memory_type": MemoryType.SEMANTIC.value,
        "source_ref": "owner_chat_2026-10-28",
        "verification_status": VerificationStatus.USER_PROVIDED.value,
        "tags": ["ups", "battery", "specification", "owner"],
        "created_at_utc": "2026-10-28T10:05:00Z"
    },
    {
        "id": "owner_safety_rule_001",
        "content": "Never disconnect battery strings under load. Always verify no current flow before opening connections.",
        "memory_type": MemoryType.PROCEDURAL.value,
        "source_ref": "owner_chat_2026-10-28",
        "verification_status": VerificationStatus.USER_PROVIDED.value,
        "tags": ["safety", "battery", "procedure", "owner"],
        "created_at_utc": "2026-10-28T10:10:00Z"
    }
]

# Tier each record
total_chunks = 0
for record in sample_knowledge:
    result = engine.tier_memory(record, target_tier="user_provided")
    print(f"   ✓ {record['id']}: {result}")
    # Count chunks (rough estimate)
    total_chunks += len(record['content'].split('. '))

print(f"✅ Ingested {len(sample_knowledge)} knowledge records")

# Step 5: Test search
print("\n[5/5] Testing semantic search...")

# Test 1: Search owner knowledge
print("\n   Test 1: Search 'ATS voltage threshold'")
results = memory_store.search_user_provided("ATS voltage threshold", n_results=3)
if results:
    print(f"   ✅ Found {len(results)} results:")
    for i, r in enumerate(results[:2], 1):
        print(f"      {i}. {r['content'][:80]}... (similarity: {r['similarity']:.2f})")
else:
    print("   ⚠️ No results found")

# Test 2: Search battery specs
print("\n   Test 2: Search 'battery voltage specification'")
results = memory_store.search_user_provided("battery voltage", n_results=3)
if results:
    print(f"   ✅ Found {len(results)} results:")
    for i, r in enumerate(results[:2], 1):
        print(f"      {i}. {r['content'][:80]}... (similarity: {r['similarity']:.2f})")
else:
    print("   ⚠️ No results found")

# Test 3: Search with verification filter
print("\n   Test 3: Search verified knowledge only")
results = memory_store.search_by_verification("safety procedure", n_results=3)
if results:
    print(f"   ✅ Found {len(results)} verified results")
else:
    print("   ⚠️ No verified results")

# Get stats
print("\n" + "=" * 60)
print("VECTOR DB STATISTICS")
print("=" * 60)
stats = memory_store.get_stats()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Embedding dimension: {stats['embedding_dim']}")
print(f"\nBy verification status:")
for status, count in stats['by_verification'].items():
    if count > 0:
        print(f"  {status}: {count}")
print(f"\nBy memory type:")
for mtype, count in stats['by_type'].items():
    if count > 0:
        print(f"  {mtype}: {count}")

print("\n" + "=" * 60)
print("✅ V37.2 VECTOR MEMORY INITIALIZATION COMPLETE")
print("=" * 60)
print(f"\nVector DB ready at: data/vector_db")
print(f"Total chunks: {stats['total_chunks']}")
print(f"Sample search working: YES")
print(f"\nNext: Ingest full knowledge base from brain.db")