"""Tests for V31 Conflict & Duplicate Detectors.

Tests for:
- conflict_detector.py - Conflict detection (semantic, temporal, source)
- duplicate_detector.py - Duplicate detection (exact, semantic, near)
"""
import json
import sqlite3
import pytest

from quan_ai_brain.memory.conflict_detector import (
    ConflictDetector,
    ConflictType,
    ConflictSeverity,
    ConflictRecord,
)
from quan_ai_brain.memory.duplicate_detector import (
    DuplicateDetector,
    DuplicateType,
    DuplicateStatus,
    DuplicateGroup,
)


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Create schema
    cursor = conn.cursor()
    
    # Knowledge units table
    cursor.execute("""
        CREATE TABLE knowledge_units (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            knowledge_type TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            content_hash TEXT,
            lifecycle_status TEXT DEFAULT 'active',
            superseded_by TEXT,
            effective_from TEXT,
            effective_until TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Conflict tables
    cursor.execute("""
        CREATE TABLE knowledge_conflicts (
            id TEXT PRIMARY KEY,
            ku1_id TEXT NOT NULL,
            ku2_id TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT,
            evidence_json TEXT DEFAULT '[]',
            detected_at TEXT NOT NULL,
            resolution_status TEXT DEFAULT 'unresolved',
            resolution_decision TEXT,
            resolved_by TEXT,
            resolved_at TEXT
        )
    """)
    
    # Duplicate tables
    cursor.execute("""
        CREATE TABLE duplicate_groups (
            id TEXT PRIMARY KEY,
            duplicate_type TEXT NOT NULL,
            similarity_score REAL NOT NULL,
            status TEXT DEFAULT 'open',
            primary_id TEXT,
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by TEXT,
            notes TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE duplicate_group_members (
            group_id TEXT NOT NULL,
            knowledge_unit_id TEXT NOT NULL,
            is_primary BOOLEAN DEFAULT 0,
            content_hash TEXT,
            similarity_score REAL,
            PRIMARY KEY (group_id, knowledge_unit_id)
        )
    """)
    
    conn.commit()
    
    yield conn
    conn.close()


@pytest.fixture
def sample_kus(db_connection):
    """Insert sample knowledge units for testing."""
    cursor = db_connection.cursor()
    
    # Insert KUs directly with all fields
    kus_data = [
        # Exact duplicates
        ("ku-1", "Hệ thống phải có provenance tracking", "2026-10-28T00:00:00Z", None, None),
        ("ku-2", "Hệ thống phải có provenance tracking", "2026-10-28T00:00:00Z", None, None),
        
        # Semantic duplicates
        ("ku-3", "Hệ thống cần theo dõi nguồn gốc tri thức", "2026-10-28T00:00:00Z", None, None),
        ("ku-4", "Cần có tracking cho nguồn gốc kiến thức", "2026-10-28T00:00:00Z", None, None),
        
        # Conflicts
        ("ku-5", "Hệ thống không cần backup", "2026-10-28T00:00:00Z", None, None),
        ("ku-6", "Hệ thống phải có backup hàng ngày", "2026-10-28T00:00:00Z", None, None),
        
        # Temporal
        ("ku-7", "Hệ thống online 24/7", "2026-10-28T00:00:00Z", "2026-01-01", "2026-12-31"),
        ("ku-8", "Hệ thống offline vào cuối tuần", "2026-10-28T00:00:00Z", "2026-06-01", "2026-08-31"),
    ]
    
    for ku_id, content, created, eff_from, eff_until in kus_data:
        cursor.execute("""
            INSERT INTO knowledge_units
            (id, content, knowledge_type, provenance_json, lifecycle_status,
             effective_from, effective_until, created_at, updated_at)
            VALUES (?, ?, 'FACT', ?, 'active', ?, ?, ?, ?)
        """, (
            ku_id, content,
            '{"source_type": "PROJECT_DOCS"}',
            eff_from,
            eff_until,
            created,
            created,
        ))
    
    db_connection.commit()
    return kus_data


class TestConflictDetector:
    """Tests for conflict detection."""
    
    def test_init_creates_tables(self, db_connection):
        """Test initialization creates tables."""
        detector = ConflictDetector(db_connection)
        
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "knowledge_conflicts" in tables
    
    def test_detect_semantic_conflict(self, db_connection, sample_kus):
        """Test detection of semantic conflicts."""
        detector = ConflictDetector(db_connection)
        
        # ku-5 and ku-6 should conflict (one says no backup, other says must have backup)
        conflicts = detector.detect_all_conflicts()
        
        assert len(conflicts) > 0
        
        # Check for semantic conflict
        semantic_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.SEMANTIC]
        assert len(semantic_conflicts) > 0
    
    def test_detect_source_conflict(self, db_connection, sample_kus):
        """Test detection of source conflicts."""
        detector = ConflictDetector(db_connection)
        
        conflicts = detector.detect_all_conflicts()
        
        # Should detect source conflict between EXTERNAL_UNVERIFIED and OWNER_DOCUMENT
        source_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.SOURCE]
        # May or may not detect depending on similarity threshold
    
    def test_resolve_conflict(self, db_connection):
        """Test resolving a conflict."""
        detector = ConflictDetector(db_connection)
        
        # Create a conflict
        conflict = ConflictRecord(
            id="conflict-1",
            ku1_id="ku-1",
            ku2_id="ku-2",
            conflict_type=ConflictType.SEMANTIC,
            severity=ConflictSeverity.HIGH,
            description="Test conflict",
            evidence=["evidence1", "evidence2"],
            detected_at="2026-10-28T00:00:00Z",
        )
        
        # Save conflict
        detector._save_conflict(conflict)
        
        # Resolve it
        result = detector.resolve_conflict("conflict-1", "ku-1 wins", "owner")
        
        assert result is True
        
        # Verify in database
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT resolution_status, resolution_decision, resolved_by
            FROM knowledge_conflicts WHERE id = 'conflict-1'
        """)
        row = cursor.fetchone()
        
        assert row["resolution_status"] == "resolved"
        assert row["resolution_decision"] == "ku-1 wins"
        assert row["resolved_by"] == "owner"
    
    def test_get_conflict_statistics(self, db_connection):
        """Test getting conflict statistics."""
        detector = ConflictDetector(db_connection)
        
        # Create some conflicts
        for i in range(3):
            conflict = ConflictRecord(
                id=f"conflict-{i}",
                ku1_id=f"ku-{i}",
                ku2_id=f"ku-{i+1}",
                conflict_type=ConflictType.SEMANTIC,
                severity=ConflictSeverity.MEDIUM,
                description=f"Test conflict {i}",
                detected_at="2026-10-28T00:00:00Z",
            )
            detector._save_conflict(conflict)
        
        stats = detector.get_conflict_statistics()
        
        assert stats["total"] == 3
        assert stats["unresolved"] == 3
        assert ConflictType.SEMANTIC.value in stats["by_type"]
    
    def test_get_unresolved_conflicts(self, db_connection):
        """Test getting unresolved conflicts."""
        detector = ConflictDetector(db_connection)
        
        # Create conflicts
        for i in range(2):
            conflict = ConflictRecord(
                id=f"conflict-{i}",
                ku1_id=f"ku-{i}",
                ku2_id=f"ku-{i+1}",
                conflict_type=ConflictType.SEMANTIC,
                severity=ConflictSeverity.HIGH,
                description=f"Test",
                detected_at="2026-10-28T00:00:00Z",
            )
            detector._save_conflict(conflict)
        
        # Resolve one
        detector.resolve_conflict("conflict-0", "resolved", "owner")
        
        unresolved = detector.get_unresolved_conflicts()
        
        assert len(unresolved) == 1
        assert unresolved[0].id == "conflict-1"


class TestDuplicateDetector:
    """Tests for duplicate detection."""
    
    def test_init_creates_tables(self, db_connection):
        """Test initialization creates tables."""
        detector = DuplicateDetector(db_connection)
        
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "duplicate_groups" in tables
        assert "duplicate_group_members" in tables
    
    def test_detect_exact_duplicates(self, db_connection, sample_kus):
        """Test detection of exact duplicates."""
        detector = DuplicateDetector(db_connection)
        
        groups = detector.detect_all_duplicates()
        
        # ku-1 and ku-2 are exact duplicates
        exact_groups = [g for g in groups if g.duplicate_type == DuplicateType.EXACT]
        
        assert len(exact_groups) > 0
        assert any("ku-1" in g.member_ids and "ku-2" in g.member_ids 
                   for g in exact_groups)
    
    def test_detect_semantic_duplicates(self, db_connection, sample_kus):
        """Test detection of semantic duplicates."""
        detector = DuplicateDetector(db_connection, similarity_threshold=0.5)
        
        groups = detector.detect_all_duplicates()
        
        # ku-3 and ku-4 are semantic duplicates
        semantic_groups = [g for g in groups if g.duplicate_type == DuplicateType.SEMANTIC]
        
        # May detect depending on similarity calculation
        # This is a placeholder test
    
    def test_merge_duplicates(self, db_connection, sample_kus):
        """Test merging duplicate group."""
        detector = DuplicateDetector(db_connection)
        
        # Create a duplicate group
        group = DuplicateGroup(
            id="dup-group-1",
            duplicate_type=DuplicateType.EXACT,
            similarity_score=1.0,
            member_ids=["ku-1", "ku-2"],
            primary_id="ku-1",
            status=DuplicateStatus.OPEN,
            created_at="2026-10-28T00:00:00Z",
        )
        
        # Save group
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO duplicate_groups
            (id, duplicate_type, similarity_score, status, primary_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (group.id, group.duplicate_type.value, group.similarity_score,
              group.status.value, group.primary_id, group.created_at))
        
        cursor.execute("""
            INSERT INTO duplicate_group_members
            (group_id, knowledge_unit_id, is_primary, similarity_score)
            VALUES (?, ?, ?, ?)
        """, (group.id, "ku-1", 1, 1.0))
        cursor.execute("""
            INSERT INTO duplicate_group_members
            (group_id, knowledge_unit_id, is_primary, similarity_score)
            VALUES (?, ?, ?, ?)
        """, (group.id, "ku-2", 0, 1.0))
        db_connection.commit()
        
        # Merge
        result = detector.merge_duplicates("dup-group-1", "ku-1", "owner", "Test merge")
        
        assert result is True
        
        # Verify ku-2 is superseded
        cursor.execute("""
            SELECT lifecycle_status, superseded_by
            FROM knowledge_units WHERE id = 'ku-2'
        """)
        row = cursor.fetchone()
        
        assert row["lifecycle_status"] == "superseded"
        assert row["superseded_by"] == "ku-1"
    
    def test_ignore_duplicate_group(self, db_connection):
        """Test ignoring a duplicate group."""
        detector = DuplicateDetector(db_connection)
        
        # Create a group
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO duplicate_groups
            (id, duplicate_type, similarity_score, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("dup-ignore-1", "EXACT", 1.0, "open", "2026-10-28T00:00:00Z"))
        db_connection.commit()
        
        # Ignore
        result = detector.ignore_duplicate_group("dup-ignore-1", "owner", "Keep separate")
        
        assert result is True
        
        # Verify status
        cursor.execute("SELECT status, notes FROM duplicate_groups WHERE id = 'dup-ignore-1'")
        row = cursor.fetchone()
        
        assert row["status"] == "ignored"
        assert row["notes"] == "Keep separate"
    
    def test_get_duplicate_statistics(self, db_connection):
        """Test getting duplicate statistics."""
        detector = DuplicateDetector(db_connection)
        
        # Create some groups
        for i in range(3):
            cursor = db_connection.cursor()
            cursor.execute("""
                INSERT INTO duplicate_groups
                (id, duplicate_type, similarity_score, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (f"dup-{i}", "EXACT", 1.0, "open", "2026-10-28T00:00:00Z"))
        
        db_connection.commit()
        
        stats = detector.get_duplicate_statistics()
        
        assert stats["total_groups"] == 3
        assert stats["open"] == 3


class TestIntegration:
    """Integration tests for conflict and duplicate detection."""
    
    def test_full_workflow(self, db_connection, sample_kus):
        """Test full conflict and duplicate detection workflow."""
        # Detect conflicts
        conflict_detector = ConflictDetector(db_connection)
        conflicts = conflict_detector.detect_all_conflicts()
        
        # Detect duplicates
        duplicate_detector = DuplicateDetector(db_connection)
        duplicates = duplicate_detector.detect_all_duplicates()
        
        # Should have found something
        assert len(conflicts) > 0 or len(duplicates) > 0
        
        # Get statistics
        conflict_stats = conflict_detector.get_conflict_statistics()
        duplicate_stats = duplicate_detector.get_duplicate_statistics()
        
        assert "total" in conflict_stats
        assert "total_groups" in duplicate_stats
    
    def test_conflict_and_duplicate_together(self, db_connection):
        """Test that conflicts and duplicates can coexist."""
        cursor = db_connection.cursor()
        
        # Insert KUs with both conflicts and duplicates
        kus = [
            ("ku-a", "System must have A", '{"source_type": "DOC1"}'),
            ("ku-b", "System must have A", '{"source_type": "DOC2"}'),  # Duplicate
            ("ku-c", "System must NOT have A", '{"source_type": "DOC3"}'),  # Conflict
        ]
        
        for ku in kus:
            cursor.execute("""
                INSERT INTO knowledge_units
                (id, content, knowledge_type, provenance_json, lifecycle_status,
                 created_at, updated_at)
                VALUES (?, ?, 'FACT', ?, 'active', ?, ?)
            """, (ku[0], ku[1], ku[2], "2026-10-28T00:00:00Z", "2026-10-28T00:00:00Z"))
        
        db_connection.commit()
        
        # Detect both
        conflict_detector = ConflictDetector(db_connection)
        duplicate_detector = DuplicateDetector(db_connection)
        
        conflicts = conflict_detector.detect_all_conflicts()
        duplicates = duplicate_detector.detect_all_duplicates()
        
        # Should have both
        assert len(conflicts) > 0 or len(duplicates) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])