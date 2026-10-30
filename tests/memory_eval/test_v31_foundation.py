"""Tests for V31 Memory Intelligence - Phase 1: Foundation.

Tests for:
- models_v31.py - Enhanced data models
- provenance_tracker.py - Provenance tracking
- knowledge_pipeline.py - Ingestion pipeline
"""
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
import pytest

from quan_ai_brain.memory.models_v31 import (
    KnowledgeUnit,
    KnowledgeProvenanceV31,
    KnowledgeType,
    VersionEntry,
    LifecycleStatus,
)
from quan_ai_brain.memory.provenance_tracker import ProvenanceTracker
from quan_ai_brain.memory.knowledge_pipeline import (
    KnowledgePipeline,
    PipelineStage,
    PipelineStatus,
)


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Create minimal schema for testing
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE knowledge_units (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            knowledge_type TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            lifecycle_status TEXT DEFAULT 'active',
            quality_score REAL DEFAULT 0.0,
            tags_json TEXT DEFAULT '[]',
            project_scope TEXT DEFAULT 'general',
            conflict_ids TEXT DEFAULT '[]',
            content_hash TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Pipeline checkpoints table
    cursor.execute("""
        CREATE TABLE pipeline_checkpoints (
            pipeline_id TEXT PRIMARY KEY,
            checkpoint_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    
    yield conn
    conn.close()


class TestModelsV31:
    """Tests for enhanced data models."""
    
    def test_knowledge_provenance_creation(self):
        """Test creating provenance record."""
        provenance = KnowledgeProvenanceV31(
            source_type="PROJECT_DOCS",
            source_ref="docs/README.md",
            source_version="v1.0",
            ingested_at="2026-10-28T10:00:00Z",
            ingested_by="test_user",
            verification_state="unverified",
        )
        
        assert provenance.source_type == "PROJECT_DOCS"
        assert provenance.source_ref == "docs/README.md"
        assert provenance.verification_state == "unverified"
        assert provenance.conflict_ids == []
    
    def test_knowledge_provenance_serialization(self):
        """Test provenance to_dict/from_dict."""
        provenance = KnowledgeProvenanceV31(
            source_type="OWNER_DOCUMENT",
            source_ref="file.txt",
            source_version="abc123",
            ingested_at="2026-10-28T10:00:00Z",
            ingested_by="owner",
            verification_state="verified",
            verified_at="2026-10-28T11:00:00Z",
            verified_by="owner",
            effective_from="2026-10-01T00:00:00Z",
            derived_from=["ku-1", "ku-2"],
        )
        
        data = provenance.to_dict()
        assert data["source_type"] == "OWNER_DOCUMENT"
        assert data["verified_at"] == "2026-10-28T11:00:00Z"
        assert data["derived_from"] == ["ku-1", "ku-2"]
        
        # Round-trip
        restored = KnowledgeProvenanceV31.from_dict(data)
        assert restored.source_type == provenance.source_type
        assert restored.derived_from == provenance.derived_from
    
    def test_knowledge_unit_creation(self):
        """Test creating knowledge unit."""
        provenance = KnowledgeProvenanceV31(
            source_type="PROJECT_DOCS",
            source_ref="test.md",
            source_version="v1",
            ingested_at="2026-10-28T10:00:00Z",
            ingested_by="test",
            verification_state="unverified",
        )
        
        ku = KnowledgeUnit(
            id="ku-test-001",
            content="Test knowledge content",
            knowledge_type=KnowledgeType.FACT.value,
            provenance=provenance,
            version=1,
            created_at="2026-10-28T10:00:00Z",
            updated_at="2026-10-28T10:00:00Z",
        )
        
        assert ku.id == "ku-test-001"
        assert ku.knowledge_type == KnowledgeType.FACT.value
        assert ku.version == 1
        assert ku.lifecycle_status == LifecycleStatus.ACTIVE.value
    
    def test_knowledge_unit_serialization(self):
        """Test knowledge unit to_dict/from_dict."""
        provenance = KnowledgeProvenanceV31(
            source_type="TEST_EVIDENCE",
            source_ref="test_result.json",
            source_version="v1",
            ingested_at="2026-10-28T10:00:00Z",
            ingested_by="test",
            verification_state="verified",
        )
        
        ku = KnowledgeUnit(
            id="ku-test-002",
            content="Test content",
            knowledge_type=KnowledgeType.FACT.value,
            provenance=provenance,
            version=2,
            supports=["ku-1"],
            contradicts=["ku-2"],
            tags=["test", "v31"],
            quality_score=0.95,
            created_at="2026-10-28T10:00:00Z",
            updated_at="2026-10-28T10:00:00Z",
        )
        
        data = ku.to_dict()
        assert data["id"] == "ku-test-002"
        assert data["supports"] == ["ku-1"]
        assert data["contradicts"] == ["ku-2"]
        assert data["tags"] == ["test", "v31"]
        assert data["quality_score"] == 0.95
        
        # Round-trip
        restored = KnowledgeUnit.from_dict(data)
        assert restored.id == ku.id
        assert restored.supports == ku.supports
        assert restored.quality_score == ku.quality_score
    
    def test_version_entry(self):
        """Test version entry creation."""
        entry = VersionEntry(
            version=1,
            changed_fields=["content", "provenance"],
            changed_by="test_user",
            changed_at="2026-10-28T10:00:00Z",
            reason="Initial creation",
            content_hash="abc123",
        )
        
        assert entry.version == 1
        assert entry.changed_fields == ["content", "provenance"]
        assert entry.reason == "Initial creation"


class TestProvenanceTracker:
    """Tests for provenance tracker."""
    
    def test_init_creates_tables(self, db_connection):
        """Test that initialization creates tables."""
        tracker = ProvenanceTracker(db_connection)
        
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "provenance_events" in tables
        assert "knowledge_version_history" in tables
        assert "knowledge_conflicts" in tables
    
    def test_log_event(self, db_connection):
        """Test logging provenance event."""
        tracker = ProvenanceTracker(db_connection)
        
        event_id = tracker.log_event(
            knowledge_unit_id="ku-test-001",
            event_type="INGESTED",
            event_data={"source": "test.md"},
            occurred_by="test_user",
        )
        
        assert event_id is not None
        
        # Verify in database
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM provenance_events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["knowledge_unit_id"] == "ku-test-001"
        assert row["event_type"] == "INGESTED"
        assert json.loads(row["event_data"]) == {"source": "test.md"}
    
    def test_get_provenance_chain(self, db_connection):
        """Test retrieving provenance chain."""
        tracker = ProvenanceTracker(db_connection)
        
        # Log multiple events
        tracker.log_event("ku-test", "INGESTED", {}, "user1")
        tracker.log_event("ku-test", "VERIFIED", {}, "user2")
        
        chain = tracker.get_provenance_chain("ku-test")
        
        assert len(chain) == 2
        assert chain[0]["event_type"] == "INGESTED"
        assert chain[1]["event_type"] == "VERIFIED"
    
    def test_create_version_entry(self, db_connection):
        """Test creating version entry."""
        tracker = ProvenanceTracker(db_connection)
        
        entry = tracker.create_version_entry(
            knowledge_unit_id="ku-test",
            version=1,
            changed_fields=["content"],
            changed_by="test_user",
            reason="Test",
            content="test content",
        )
        
        assert entry.version == 1
        assert entry.changed_fields == ["content"]
        assert entry.content_hash is not None
        
        # Verify in database
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM knowledge_version_history")
        rows = cursor.fetchall()
        
        assert len(rows) == 1
    
    def test_create_conflict_record(self, db_connection):
        """Test creating conflict record."""
        tracker = ProvenanceTracker(db_connection)
        
        conflict_id = tracker.create_conflict_record(
            ku1_id="ku-1",
            ku2_id="ku-2",
            conflict_type="SEMANTIC",
            conflict_description="Contradictory statements",
            detected_by="system",
        )
        
        assert conflict_id is not None
        
        # Verify in database
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM knowledge_conflicts WHERE id = ?", (conflict_id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["conflict_type"] == "SEMANTIC"
        assert row["resolution_status"] == "unresolved"
    
    def test_resolve_conflict(self, db_connection):
        """Test resolving conflict."""
        tracker = ProvenanceTracker(db_connection)
        
        conflict_id = tracker.create_conflict_record(
            "ku-1", "ku-2", "SEMANTIC", "Test", "system"
        )
        
        tracker.resolve_conflict(conflict_id, "ku-1 wins", "owner")
        
        cursor = db_connection.cursor()
        cursor.execute("SELECT resolution_status, resolution_decision FROM knowledge_conflicts WHERE id = ?", (conflict_id,))
        row = cursor.fetchone()
        
        assert row["resolution_status"] == "resolved"
        assert row["resolution_decision"] == "ku-1 wins"


class TestKnowledgePipeline:
    """Tests for knowledge ingestion pipeline."""
    
    def test_pipeline_initialization(self, db_connection):
        """Test pipeline initialization."""
        pipeline = KnowledgePipeline(db_connection, owner_id="test_owner")
        
        assert pipeline.owner_id == "test_owner"
        assert pipeline.provenance_tracker is not None
    
    def test_simple_ingestion(self, db_connection):
        """Test simple knowledge ingestion."""
        pipeline = KnowledgePipeline(db_connection, owner_id="test_owner")
        
        result = pipeline.ingest(
            source_type="PROJECT_DOCS",
            source_ref="test.md",
            source_version="v1",
            content="This is a test fact",
            ingested_by="test_user",
        )
        
        # Should pause at OWNER_PREVIEW stage
        assert result.status == PipelineStatus.PAUSED
        assert result.preview is not None
        assert result.preview["content"] == "this is a test fact"  # Normalized
        assert result.preview["knowledge_type"] == "FACT"
    
    def test_pipeline_with_approval(self, db_connection):
        """Test pipeline with owner approval."""
        pipeline = KnowledgePipeline(db_connection, owner_id="test_owner")
        
        # Start ingestion
        result = pipeline.ingest(
            source_type="OWNER_DOCUMENT",
            source_ref="owner_doc.txt",
            source_version="v1",
            content="Owner approved fact",
            ingested_by="owner",
        )
        
        assert result.status == PipelineStatus.PAUSED
        assert result.preview["suggested_action"] == "APPROVE"
        
        # Approve
        result = pipeline.resume_pipeline(result.pipeline_id, "APPROVE")
        
        assert result.status == PipelineStatus.COMPLETED
        assert result.knowledge_unit is not None
        
        # Verify in database
        cursor = db_connection.cursor()
        cursor.execute("SELECT id, content, version FROM knowledge_units WHERE id = ?", (result.knowledge_unit.id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["version"] == 1
    
    def test_pipeline_rejection(self, db_connection):
        """Test pipeline rejection."""
        pipeline = KnowledgePipeline(db_connection, owner_id="test_owner")
        
        result = pipeline.ingest(
            source_type="EXTERNAL_UNVERIFIED",
            source_ref="unknown.txt",
            source_version="v1",
            content="Unverified content",
            ingested_by="system",
        )
        
        assert result.status == PipelineStatus.PAUSED
        
        # Reject
        result = pipeline.resume_pipeline(result.pipeline_id, "REJECT")
        
        assert result.status == PipelineStatus.CANCELLED
    
    def test_pipeline_with_warnings(self, db_connection):
        """Test pipeline with warnings."""
        pipeline = KnowledgePipeline(db_connection, owner_id="test_owner")
        
        result = pipeline.ingest(
            source_type="PROJECT_DOCS",
            source_ref="test.md",
            source_version="v1",
            content="Short",  # Very short content
            ingested_by="test",
        )
        
        assert result.status == PipelineStatus.PAUSED
        # Should have quality score warning for short content
    
    def test_pipeline_secret_detection(self, db_connection):
        """Test that secrets are detected."""
        pipeline = KnowledgePipeline(db_connection, owner_id="test_owner")
        
        result = pipeline.ingest(
            source_type="PROJECT_DOCS",
            source_ref="test.md",
            source_version="v1",
            content="Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            ingested_by="test",
        )
        
        # Should have warning about secret
        assert any("secret" in w.lower() for w in result.preview.get("warnings", []))


class TestIntegration:
    """Integration tests for V31 foundation."""
    
    def test_full_workflow(self, db_connection):
        """Test full knowledge management workflow."""
        # 1. Ingest knowledge
        pipeline = KnowledgePipeline(db_connection, owner_id="owner")
        
        result = pipeline.ingest(
            source_type="OWNER_DOCUMENT",
            source_ref="requirements.md",
            source_version="v1.0",
            content="System must support provenance tracking",
            ingested_by="owner",
            metadata={"tags": ["requirement", "v31"]},
        )
        
        assert result.status == PipelineStatus.PAUSED
        
        # 2. Approve
        result = pipeline.resume_pipeline(result.pipeline_id, "APPROVE")
        assert result.status == PipelineStatus.COMPLETED
        
        ku_id = result.knowledge_unit.id
        
        # 3. Track provenance
        tracker = ProvenanceTracker(db_connection)
        chain = tracker.get_provenance_chain(ku_id)
        assert len(chain) >= 1
        assert chain[0]["event_type"] == "INGESTED"
        
        # 4. Get version history
        history = tracker.get_version_history(ku_id)
        assert len(history) == 1
        assert history[0].version == 1
    
    def test_multiple_knowledge_units(self, db_connection):
        """Test ingesting multiple knowledge units."""
        pipeline = KnowledgePipeline(db_connection, owner_id="owner")
        
        # Ingest multiple units
        results = []
        for i in range(3):
            result = pipeline.ingest(
                source_type="PROJECT_DOCS",
                source_ref=f"doc{i}.md",
                source_version="v1",
                content=f"Fact number {i}",
                ingested_by="system",
            )
            result = pipeline.resume_pipeline(result.pipeline_id, "APPROVE")
            results.append(result)
        
        assert all(r.status == PipelineStatus.COMPLETED for r in results)
        
        # Verify all in database
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge_units")
        count = cursor.fetchone()[0]
        
        assert count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])