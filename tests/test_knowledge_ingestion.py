"""Tests for Knowledge Ingestion Pipeline — Sprint 3.

Tests:
1. Ingest with provenance
2. Conflict detection
3. Approve/reject workflow
4. Quarantine listing
5. Conflict resolution
"""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, "src")

from quan_ai_brain.memory.knowledge_ingestion import (
    KnowledgeIngestionEngine,
    KnowledgeProvenance,
    KnowledgeRecord,
    KnowledgeSource,
    VerificationState,
)
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_ingest_with_provenance():
    """Test basic ingestion with full provenance tracking."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="TestOwner")

    record = engine.ingest(
        content="Anh Quân là chủ sở hữu duy nhất của QUAN AI BRAIN.",
        source_type=KnowledgeSource.OWNER_DOCUMENT,
        source_ref="docs/OWNER_STATEMENT.md",
        source_version="v1.0",
        tags=["owner_identity", "governance"],
        expires_days=365,
    )

    assert record.id.startswith("know_")
    assert record.statement == "Anh Quân là chủ sở hữu duy nhất của QUAN AI BRAIN."
    assert record.provenance.source_type == KnowledgeSource.OWNER_DOCUMENT
    assert record.provenance.source_ref == "docs/OWNER_STATEMENT.md"
    assert record.provenance.source_version == "v1.0"
    assert record.provenance.verification_state == VerificationState.QUARANTINED
    assert record.confidence_score > 0.9  # High confidence for owner document
    assert "owner_identity" in record.tags

    print("✓ Ingest with provenance: PASS")


def test_conflict_detection():
    """Test conflict detection between contradictory statements."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="TestOwner")

    # First statement
    record1 = engine.ingest(
        content="Hệ thống sử dụng GLM-5.3-Flash cho hội thoại.",
        source_type=KnowledgeSource.PROJECT_DOCS,
        source_ref="docs/LLM_CONFIG.md",
        tags=["llm", "configuration"],
    )

    # Conflicting statement (negation)
    record2 = engine.ingest(
        content="Hệ thống không sử dụng GLM-5.3-Flash cho hội thoại.",
        source_type=KnowledgeSource.PROJECT_DOCS,
        source_ref="docs/LLM_CONFIG_UPDATE.md",
        tags=["llm", "configuration"],
    )

    # Should detect conflict
    assert len(record2.provenance.conflict_ids) > 0
    assert record1.id in record2.provenance.conflict_ids

    print("✓ Conflict detection: PASS")


def test_approve_workflow():
    """Test approve workflow from quarantine to verified."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="Quanpt1")

    record = engine.ingest(
        content="BGE-M3 warm inference latency là 0.39-0.47ms.",
        source_type=KnowledgeSource.TEST_EVIDENCE,
        source_ref="reports/SPRINT0_RUNTIME_PROBE.json",
        tags=["performance", "embedding"],
    )

    # Approve
    success = engine.approve_knowledge(
        record_id=record.id,
        approved_by="Quanpt1",
        notes="Verified by Sprint 0 benchmark",
    )
    assert success is True

    # Check it's no longer in quarantine
    quarantined = engine.list_quarantined()
    assert not any(k["id"] == record.id for k in quarantined)

    print("✓ Approve workflow: PASS")


def test_reject_workflow():
    """Test reject workflow."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="Quanpt1")

    record = engine.ingest(
        content="Thông tin chưa xác minh.",
        source_type=KnowledgeSource.EXTERNAL_UNVERIFIED,
        source_ref="https://untrusted-source.example.com",
        tags=["unverified"],
    )

    # Reject
    success = engine.reject_knowledge(
        record_id=record.id,
        rejected_by="Quanpt1",
        reason="Source not trusted",
    )
    assert success is True

    # Check it's no longer in quarantine
    quarantined = engine.list_quarantined()
    assert not any(k["id"] == record.id for k in quarantined)

    print("✓ Reject workflow: PASS")


def test_quarantine_listing():
    """Test listing quarantined items."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="TestOwner")

    # Ingest multiple items
    for i in range(5):
        engine.ingest(
            content=f"Kiến thức thử nghiệm {i}.",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref=f"docs/test_{i}.md",
        )

    quarantined = engine.list_quarantined(limit=10)
    assert len(quarantined) == 5

    # Check structure
    item = quarantined[0]
    assert "id" in item
    assert "statement" in item
    assert "source_ref" in item
    assert "status" in item

    print("✓ Quarantine listing: PASS")


def test_conflict_retrieval():
    """Test retrieving conflicts for a record."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="TestOwner")

    # Create conflicting records
    record1 = engine.ingest(
        content="Pi 5 có RAM 4GB.",
        source_type=KnowledgeSource.PROJECT_DOCS,
        source_ref="docs/HARDWARE.md",
    )

    record2 = engine.ingest(
        content="Pi 5 không có RAM 4GB.",
        source_type=KnowledgeSource.PROJECT_DOCS,
        source_ref="docs/HARDWARE_UPDATE.md",
    )

    # Get conflicts for record2
    conflicts = engine.get_conflicts(record2.id)
    assert len(conflicts) > 0
    assert conflicts[0]["id"] == record1.id

    print("✓ Conflict retrieval: PASS")


def test_normalization():
    """Test text normalization for comparison."""
    normalized1 = KnowledgeRecord.normalize_text("  Xin Chào Anh  ")
    normalized2 = KnowledgeRecord.normalize_text("xin chào anh")

    assert normalized1 == normalized2
    assert normalized1 == "xin chào anh"

    print("✓ Normalization: PASS")


def test_source_reliability():
    """Test that different sources have different confidence scores."""
    store = MemoryStore(":memory:")
    engine = KnowledgeIngestionEngine(store, owner_id="TestOwner")

    owner_record = engine.ingest(
        content="Test statement.",
        source_type=KnowledgeSource.OWNER_DOCUMENT,
        source_ref="test.md",
    )

    external_record = engine.ingest(
        content="Test statement.",
        source_type=KnowledgeSource.EXTERNAL_UNVERIFIED,
        source_ref="test.md",
    )

    assert owner_record.confidence_score > external_record.confidence_score
    assert owner_record.confidence_score > 0.9
    assert external_record.confidence_score < 0.5

    print("✓ Source reliability: PASS")


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Sprint 3 — Knowledge Ingestion Tests")
    print("=" * 60)

    tests = [
        test_ingest_with_provenance,
        test_conflict_detection,
        test_approve_workflow,
        test_reject_workflow,
        test_quarantine_listing,
        test_conflict_retrieval,
        test_normalization,
        test_source_reliability,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    if failed == 0:
        print(f"✓ All {len(tests)} tests passed — Sprint 3 knowledge ingestion ready")
        return 0
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())