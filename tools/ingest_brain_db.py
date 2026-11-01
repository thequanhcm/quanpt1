"""Ingest existing knowledge from brain.db into vector DB."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from quan_ai_brain.memory.vector_store import MemoryChunk, MemoryTieringEngine, create_memory_store
from quan_ai_brain.memory.models import MemoryType, VerificationStatus

print("=" * 60)
print("INGEST BRAIN.DB INTO VECTOR DB")
print("=" * 60)

# Step 1: Connect to brain.db
print("\n[1/4] Connecting to brain.db...")
conn = sqlite3.connect("data/brain.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Count knowledge units
cursor.execute("SELECT COUNT(*) as count FROM knowledge_units")
total = cursor.fetchone()["count"]
print(f"✅ Found {total} knowledge units in brain.db")

# Step 2: Initialize vector store
print("\n[2/4] Initializing vector store...")
# Use mock embedding for now (BGE needs Ollama running)
class MockEmbeddingService:
    def embed(self, texts):
        return [[0.1] * 1024 for _ in texts]
    def get_dimension(self):
        return 1024

embedding_service = MockEmbeddingService()
print(f"✅ Using mock embedding (1024 dims)")

memory_store = create_memory_store(
    db_path="data/vector_db",
    embedding_service=embedding_service
)
engine = MemoryTieringEngine(memory_store)

# Step 3: Ingest knowledge units
print("\n[3/4] Ingesting knowledge units...")
cursor.execute("""
    SELECT knowledge_id, statement, knowledge_type, source_refs_json,
           created_at_utc, updated_at_utc, verification_method
    FROM knowledge_units
    LIMIT 50
""")

rows = cursor.fetchall()
ingested = 0
errors = 0

for row in rows:
    try:
        # Parse provenance
        source_refs = json.loads(row["source_refs_json"] or "[]")
        source_ref = source_refs[0] if source_refs else "brain.db"
        
        # Map verification state
        verification = row["verification_method"] or "UNVERIFIED"
        if verification == "VERIFIED":
            verification = VerificationStatus.VERIFIED.value
        elif "USER" in str(verification).upper():
            verification = VerificationStatus.USER_PROVIDED.value
        else:
            verification = VerificationStatus.UNVERIFIED.value
        
        # Create record
        record = {
            "id": f"brain_{row['knowledge_id']}",
            "content": row["statement"] or "",
            "memory_type": MemoryType.SEMANTIC.value,
            "source_ref": source_ref,
            "verification_status": verification,
            "tags": [],
            "created_at_utc": row["created_at_utc"] or "",
            "metadata": {
                "original_id": row["knowledge_id"],
                "knowledge_type": row["knowledge_type"]
            }
        }
        
        # Tier to appropriate level
        if verification == VerificationStatus.USER_PROVIDED.value:
            engine.tier_memory(record, "user_provided")
        elif verification == VerificationStatus.VERIFIED.value:
            engine.tier_memory(record, "verified")
        else:
            engine.tier_memory(record, "long_term")
        
        ingested += 1
        
        if ingested % 10 == 0:
            print(f"   Ingested {ingested} chunks...")
            
    except Exception as e:
        errors += 1
        print(f"   ❌ Error ingesting {row['knowledge_id']}: {e}")

print(f"\n✅ Ingested {ingested} chunks, {errors} errors")

# Step 4: Show stats
print("\n[4/4] Vector DB Statistics")
stats = memory_store.get_stats()
print(f"Total chunks: {stats['total_chunks']}")
print(f"By verification:")
for status, count in stats['by_verification'].items():
    if count > 0:
        print(f"  {status}: {count}")

print("\n" + "=" * 60)
print("✅ INGESTION COMPLETE")
print("=" * 60)
print(f"\nIngested {ingested} knowledge units from brain.db")
print(f"Vector DB now has {stats['total_chunks']} total chunks")

conn.close()