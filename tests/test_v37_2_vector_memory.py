"""Tests for V37.2 Long-Term Memory with Vector DB (ChromaDB).

Tests cover:
- Memory chunk creation and splitting
- Vector store add/search
- Tiered memory architecture
- Verification status filtering
- Batch operations
"""
import json
import pytest
from pathlib import Path
import tempfile

from quan_ai_brain.memory.vector_store import (
    LongTermMemoryStore,
    MemoryChunk,
    MemoryTieringEngine,
    create_memory_store
)
from quan_ai_brain.memory.models import MemoryType, VerificationStatus, LifecycleStatus


@pytest.fixture
def temp_db_path(tmp_path_factory):
    """Create temporary database path for testing.

    (30/10/2026) FIX Windows: chromadb 1.5.9 (rust bindings) giữ sqlite
    connection pool đến khi GC hủy toàn bộ reference — pytest fixture cache
    giữ store alive nên TemporaryDirectory cleanup crash PermissionError
    WinError 32. Chiến lược: dùng tmp_path (pytest tự quản, không rmtree
    ngay) + ignore cleanup errors — temp dir được OS dọn theo Temp cleanup,
    test không còn ERROR teardown. Best-effort clear cache + GC sau mỗi test.
    """
    tmpdir = tmp_path_factory.mktemp("v37_2_chroma")
    yield tmpdir / "test_vector_db"
    from chromadb.api.shared_system_client import SharedSystemClient
    SharedSystemClient.clear_system_cache()
    import gc
    gc.collect()
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)  # best-effort, không raise


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    class MockEmbeddingService:
        def embed(self, texts: list) -> list:
            # Return dummy embeddings (1024 dims)
            return [[0.1] * 1024 for _ in texts]
        
        def get_dimension(self) -> int:
            return 1024
    
    return MockEmbeddingService()


@pytest.fixture
def memory_store(temp_db_path, mock_embedding_service):
    """Create memory store for testing."""
    store = LongTermMemoryStore(
        db_path=str(temp_db_path),
        embedding_service=mock_embedding_service,
        collection_name="test_memory"
    )
    yield store
    # (30/10/2026) Cleanup: drop references TRƯỚC khi temp dir bị xóa —
    # chroma client phải được GC/clear cache trước TemporaryDirectory exit.
    del store
    from chromadb.api.shared_system_client import SharedSystemClient
    SharedSystemClient.clear_system_cache()
    import gc
    gc.collect()


class TestMemoryChunk:
    """Test MemoryChunk creation and splitting."""
    
    def test_create_chunk(self):
        """Test basic chunk creation."""
        chunk = MemoryChunk(
            id="test_1",
            content="This is a test memory.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="chat_123",
            verification_status=VerificationStatus.USER_PROVIDED.value,
            tags=["test", "demo"],
            metadata={"key": "value"}
        )
        
        assert chunk.id == "test_1"
        assert len(chunk.content) > 0
        assert chunk.tags == ["test", "demo"]
    
    def test_chunk_from_record(self):
        """Test creating chunks from memory record."""
        record = {
            "id": "mem_123",
            "content": "First sentence. Second sentence. Third sentence.",
            "memory_type": MemoryType.SEMANTIC.value,
            "source_ref": "chat_456",
            "verification_status": VerificationStatus.VERIFIED.value,
            "tags": ["important"],
            "created_at_utc": "2026-10-28T00:00:00Z",
            "metadata": {"custom": "data"}
        }
        
        chunks = MemoryChunk.from_memory_record(record, chunk_size=30)
        
        assert len(chunks) > 0
        assert all(chunk.id.startswith("mem_123_chunk_") for chunk in chunks)
        assert all(chunk.source_ref == "chat_456" for chunk in chunks)
        assert all(chunk.verification_status == VerificationStatus.VERIFIED.value for chunk in chunks)
    
    def test_chunk_splitting(self):
        """Test that long content is split into multiple chunks."""
        record = {
            "id": "long_mem",
            "content": "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five.",
            "memory_type": MemoryType.SEMANTIC.value,
            "source_ref": "test",
            "verification_status": VerificationStatus.USER_PROVIDED.value,
            "tags": [],
            "created_at_utc": "",
            "metadata": {}
        }
        
        chunks = MemoryChunk.from_memory_record(record, chunk_size=20)
        
        assert len(chunks) > 1  # Should be split
        assert all(len(chunk.content) <= 30 for chunk in chunks)  # With some buffer


class TestLongTermMemoryStore:
    """Test vector store operations."""
    
    def test_store_initialization(self, memory_store):
        """Test store creates collection."""
        assert memory_store.collection is not None
        assert memory_store.collection.count() == 0
    
    def test_add_single_memory(self, memory_store):
        """Test adding a single memory chunk."""
        chunk = MemoryChunk(
            id="chunk_1",
            content="Test knowledge about UPS batteries.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="user_chat",
            verification_status=VerificationStatus.USER_PROVIDED.value,
            tags=["ups", "battery"],
            metadata={}
        )
        
        result_id = memory_store.add_memory(chunk)
        
        assert result_id == "chunk_1"
        assert memory_store.collection.count() == 1
    
    def test_add_batch_memories(self, memory_store):
        """Test adding multiple memories in batch."""
        chunks = [
            MemoryChunk(
                id=f"chunk_{i}",
                content=f"Knowledge item {i} about electrical systems.",
                memory_type=MemoryType.SEMANTIC.value,
                source_ref="user_chat",
                verification_status=VerificationStatus.USER_PROVIDED.value,
                tags=["electrical"],
                metadata={}
            )
            for i in range(5)
        ]
        
        added = memory_store.add_memories_batch(chunks)
        
        assert added == 5
        assert memory_store.collection.count() == 5
    
    def test_semantic_search(self, memory_store):
        """Test semantic search functionality."""
        # Add some memories
        chunks = [
            MemoryChunk(
                id=f"chunk_{i}",
                content=f"UPS battery voltage should be between 12.0 and 13.0 volts.",
                memory_type=MemoryType.SEMANTIC.value,
                source_ref="user_chat",
                verification_status=VerificationStatus.USER_PROVIDED.value,
                tags=["ups", "battery"],
                metadata={}
            )
            for i in range(3)
        ]
        memory_store.add_memories_batch(chunks)
        
        # Search
        results = memory_store.search("UPS battery voltage", n_results=2)
        
        assert len(results["ids"][0]) > 0
        assert results["distances"][0][0] >= 0
    
    def test_search_with_filters(self, memory_store):
        """Test search with verification status filter."""
        # Add verified and unverified
        verified = MemoryChunk(
            id="verified_1",
            content="Verified knowledge about electrical safety.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="user_chat",
            verification_status=VerificationStatus.VERIFIED.value,
            tags=["safety"],
            metadata={}
        )
        
        unverified = MemoryChunk(
            id="unverified_1",
            content="Unverified hypothesis about power systems.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="system_observation",
            verification_status=VerificationStatus.INFERRED.value,
            tags=["hypothesis"],
            metadata={}
        )
        
        memory_store.add_memory(verified)
        memory_store.add_memory(unverified)
        
        # Search only verified
        results = memory_store.search(
            "electrical safety",
            filters={"verification_status": VerificationStatus.VERIFIED.value}
        )
        
        assert len(results["ids"][0]) > 0
        assert all(
            m["verification_status"] == VerificationStatus.VERIFIED.value
            for m in results["metadatas"][0]
        )
    
    def test_search_user_provided(self, memory_store):
        """Test searching USER_PROVIDED knowledge."""
        # (30/10/2026) FIX: MemoryType KHÔNG có RULE (enum: EPISODIC/SEMANTIC/
        # PROCEDURAL/DECISION/PREFERENCE/CANDIDATE) → test lỗi AttributeError
        # ngay khi tạo chunk. Dùng DECISION (ngữ nghĩa gần nhất: owner quyết
        # định/luật vận hành).
        chunk = MemoryChunk(
            id="user_knowledge",
            content="Anh dạy: ATS chuyển nguồn khi điện áp dưới 180V.",
            memory_type=MemoryType.DECISION.value,
            source_ref="owner_chat",
            verification_status=VerificationStatus.USER_PROVIDED.value,
            tags=["ats", "owner"],
            metadata={}
        )

        memory_store.add_memory(chunk)

        results = memory_store.search_user_provided("ATS voltage threshold")

        assert len(results) > 0
        assert results[0]["verification_status"] == VerificationStatus.USER_PROVIDED.value
    
    def test_get_stats(self, memory_store):
        """Test statistics retrieval."""
        # Add some memories
        for i in range(3):
            chunk = MemoryChunk(
                id=f"stat_{i}",
                content=f"Test content {i}",
                memory_type=MemoryType.SEMANTIC.value,
                source_ref="test",
                verification_status=VerificationStatus.USER_PROVIDED.value,
                tags=[],
                metadata={}
            )
            memory_store.add_memory(chunk)
        
        stats = memory_store.get_stats()
        
        assert stats["total_chunks"] == 3
        assert stats["by_verification"][VerificationStatus.USER_PROVIDED.value] == 3
        assert stats["embedding_dim"] == 1024
    
    def test_delete_chunk(self, memory_store):
        """Test deleting a chunk."""
        chunk = MemoryChunk(
            id="to_delete",
            content="This will be deleted.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="test",
            verification_status=VerificationStatus.USER_PROVIDED.value,
            tags=[],
            metadata={}
        )
        
        memory_store.add_memory(chunk)
        assert memory_store.collection.count() == 1
        
        result = memory_store.delete_chunk("to_delete")
        
        assert result is True
        assert memory_store.collection.count() == 0
    
    def test_export_import(self, memory_store, temp_db_path):
        """Test export and import functionality."""
        # Add memories
        chunk = MemoryChunk(
            id="export_test",
            content="Content to export and import.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="test",
            verification_status=VerificationStatus.VERIFIED.value,
            tags=["export"],
            metadata={"custom": "data"}
        )
        memory_store.add_memory(chunk)
        
        # Export
        export_path = temp_db_path / "export.json"
        count = memory_store.export_to_json(str(export_path))
        
        assert count == 1
        assert export_path.exists()
        
        # Clear store
        memory_store.reset()
        assert memory_store.collection.count() == 0
        
        # Import
        import_count = memory_store.import_from_json(str(export_path))
        
        assert import_count == 1
        assert memory_store.collection.count() == 1


class TestMemoryTieringEngine:
    """Test memory tiering logic."""
    
    def test_tier_to_long_term(self, memory_store):
        """Test tiering to long-term memory."""
        engine = MemoryTieringEngine(memory_store)
        
        record = {
            "id": "tier_test",
            "content": "Short. Medium length sentence. Longer sentence here.",
            "memory_type": MemoryType.SEMANTIC.value,
            "source_ref": "chat",
            "verification_status": VerificationStatus.UNVERIFIED.value,
            "tags": [],
            "created_at_utc": ""
        }
        
        result = engine.tier_memory(record, target_tier="long_term")
        
        assert "long-term memory" in result
        assert memory_store.collection.count() > 0
    
    def test_tier_to_verified(self, memory_store):
        """Test tiering with verified status."""
        engine = MemoryTieringEngine(memory_store)
        
        record = {
            "id": "verified_tier",
            "content": "This is verified knowledge.",
            "memory_type": MemoryType.SEMANTIC.value,
            "source_ref": "audit",
            "verification_status": VerificationStatus.UNVERIFIED.value,
            "tags": [],
            "created_at_utc": ""
        }
        
        result = engine.tier_memory(record, target_tier="verified")
        
        assert "Verified" in result
        results = memory_store.search_by_verification("verified knowledge")
        assert len(results) > 0
        assert results[0]["verification_status"] == VerificationStatus.VERIFIED.value
    
    def test_retrieve_with_tiering(self, memory_store):
        """Test retrieval with tier preference."""
        engine = MemoryTieringEngine(memory_store)
        
        # Add verified and unverified
        verified = MemoryChunk(
            id="v1",
            content="Verified UPS battery specification.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="manual",
            verification_status=VerificationStatus.VERIFIED.value,
            tags=[],
            metadata={}
        )
        
        unverified = MemoryChunk(
            id="u1",
            content="Hypothesis about battery degradation.",
            memory_type=MemoryType.SEMANTIC.value,
            source_ref="observation",
            verification_status=VerificationStatus.INFERRED.value,
            tags=[],
            metadata={}
        )
        
        memory_store.add_memory(verified)
        memory_store.add_memory(unverified)
        
        # Retrieve with verified preference
        results = engine.retrieve_with_tiering("battery", require_verified=True)
        
        assert len(results) > 0
        assert all(r["verification_status"] == VerificationStatus.VERIFIED.value for r in results)
    
    def test_retrieve_all_tiers(self, memory_store):
        """Test retrieval from all tiers."""
        engine = MemoryTieringEngine(memory_store)
        
        # Add mixed verification statuses
        for i, status in enumerate([
            VerificationStatus.VERIFIED.value,
            VerificationStatus.USER_PROVIDED.value,
            VerificationStatus.INFERRED.value
        ]):
            chunk = MemoryChunk(
                id=f"tier_{i}",
                content=f"Content with {status} status.",
                memory_type=MemoryType.SEMANTIC.value,
                source_ref="test",
                verification_status=status,
                tags=[],
                metadata={}
            )
            memory_store.add_memory(chunk)
        
        # Retrieve without verification requirement
        results = engine.retrieve_with_tiering("content", require_verified=False)
        
        assert len(results) > 0
        # Verified should be ranked higher
        if len(results) > 1:
            assert results[0]["verification_status"] == VerificationStatus.VERIFIED.value


class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_full_ingestion_pipeline(self, temp_db_path, mock_embedding_service):
        """Test complete memory ingestion pipeline."""
        store = LongTermMemoryStore(
            db_path=str(temp_db_path),
            embedding_service=mock_embedding_service
        )
        engine = MemoryTieringEngine(store)
        
        # Simulate owner providing knowledge
        # (30/10/2026) FIX: MemoryType KHÔNG có RULE → dùng DECISION.
        owner_knowledge = {
            "id": "owner_123",
            "content": "ATS should switch to backup when voltage drops below 180V for more than 5 seconds.",
            "memory_type": MemoryType.DECISION.value,
            "source_ref": "owner_chat_2026-10-28",
            "verification_status": VerificationStatus.USER_PROVIDED.value,
            "tags": ["ats", "rule", "owner"],
            "created_at_utc": "2026-10-28T10:00:00Z"
        }
        
        # Tier to USER_PROVIDED
        result = engine.tier_memory(owner_knowledge, target_tier="user_provided")
        assert "USER_PROVIDED" in result or "user_provided" in result.lower()
        
        # Search for it
        results = store.search_user_provided("ATS voltage threshold")
        assert len(results) > 0
        assert "180V" in results[0]["content"]
        
        # Get stats
        stats = store.get_stats()
        assert stats["total_chunks"] > 0
        assert stats["by_verification"][VerificationStatus.USER_PROVIDED.value] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])