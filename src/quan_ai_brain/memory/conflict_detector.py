"""V31 Conflict Detector - Detect contradictions between knowledge units.

Conflict types:
1. SEMANTIC - Contradictory meaning (A says X, B says NOT X)
2. TEMPORAL - Time-based contradiction (A says X at time T1, B says NOT X at T2)
3. LOGICAL - Logical inconsistency (A implies B, but C implies NOT B)
4. SOURCE - Different sources make conflicting claims

Detection methods:
- Exact negation matching
- Semantic similarity with negation
- Temporal range overlap analysis
- Logical implication analysis
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Type of conflict between knowledge units."""
    SEMANTIC = "SEMANTIC"      # Contradictory meaning
    TEMPORAL = "TEMPORAL"      # Time-based contradiction
    LOGICAL = "LOGICAL"        # Logical inconsistency
    SOURCE = "SOURCE"          # Different sources, same claim


class ConflictSeverity(str, Enum):
    """Severity of conflict."""
    LOW = "low"           # Minor inconsistency
    MEDIUM = "medium"     # Moderate contradiction
    HIGH = "high"         # Major contradiction
    CRITICAL = "critical" # Direct contradiction on important fact


@dataclass
class ConflictRecord:
    """Record of a detected conflict."""
    id: str
    ku1_id: str
    ku2_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    evidence: list[str] = field(default_factory=list)
    detected_at: str = ""
    resolution_status: str = "unresolved"
    resolution_decision: str = ""
    resolved_by: str = ""
    resolved_at: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ku1_id": self.ku1_id,
            "ku2_id": self.ku2_id,
            "conflict_type": self.conflict_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "detected_at": self.detected_at,
            "resolution_status": self.resolution_status,
            "resolution_decision": self.resolution_decision,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ConflictRecord':
        return cls(
            id=data["id"],
            ku1_id=data["ku1_id"],
            ku2_id=data["ku2_id"],
            conflict_type=ConflictType(data["conflict_type"]),
            severity=ConflictSeverity(data["severity"]),
            description=data["description"],
            evidence=data.get("evidence", []),
            detected_at=data.get("detected_at", ""),
            resolution_status=data.get("resolution_status", "unresolved"),
            resolution_decision=data.get("resolution_decision", ""),
            resolved_by=data.get("resolved_by", ""),
            resolved_at=data.get("resolved_at", ""),
        )


class ConflictDetector:
    """Detects conflicts between knowledge units."""
    
    # Negation markers in Vietnamese
    NEGATION_MARKERS = [
        "không", "chưa", "chẳng", "đừng", "chớ", "không thể", "không có",
        "phủ định", "trừ khi", "ngoại trừ", "mà không", "nhưng không"
    ]
    
    # Contradiction patterns
    CONTRADICTION_PATTERNS = [
        r"không\s+(?:phải|có|thể|được)",
        r"chưa\s+(?:phải|có|thể|được)",
        r"chẳng\s+(?:phải|có|thể|được)",
        r"phủ\s+định",
        r"trái\s+(?:ngược|lại)",
        r"mâu\s+thuẫn",
        r"xung\s+đột",
    ]
    
    def __init__(self, db_connection):
        """Initialize with database connection.
        
        Args:
            db_connection: SQLite connection to brain.db
        """
        self.db = db_connection
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create conflict tracking tables if they don't exist."""
        cursor = self.db.cursor()
        
        # Conflict records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_conflicts (
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
                resolved_at TEXT,
                FOREIGN KEY (ku1_id) REFERENCES knowledge_units(id),
                FOREIGN KEY (ku2_id) REFERENCES knowledge_units(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_ku1 
            ON knowledge_conflicts(ku1_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_ku2 
            ON knowledge_conflicts(ku2_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_status 
            ON knowledge_conflicts(resolution_status)
        """)
        
        self.db.commit()
        logger.info("Conflict detector tables initialized")
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return str(uuid.uuid4())
    
    def _now(self) -> str:
        """Get current UTC timestamp."""
        return datetime.utcnow().isoformat() + "Z"
    
    def detect_all_conflicts(self) -> list[ConflictRecord]:
        """Detect all conflicts in the knowledge base.
        
        Returns:
            List of detected conflicts
        """
        logger.info("Starting full conflict detection scan")
        
        # Get all knowledge units
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, content, knowledge_type, provenance_json, 
                   effective_from, effective_until
            FROM knowledge_units
            WHERE lifecycle_status != 'archived'
        """)
        
        kus = cursor.fetchall()
        conflicts = []
        
        # Compare each pair
        for i, ku1 in enumerate(kus):
            for j, ku2 in enumerate(kus):
                if i >= j:
                    continue
                
                # Check for conflicts
                ku1_data = {
                    "id": ku1[0],
                    "content": ku1[1],
                    "knowledge_type": ku1[2],
                    "provenance": ku1[3],
                    "effective_from": ku1[4],
                    "effective_until": ku1[5],
                }
                ku2_data = {
                    "id": ku2[0],
                    "content": ku2[1],
                    "knowledge_type": ku2[2],
                    "provenance": ku2[3],
                    "effective_from": ku2[4],
                    "effective_until": ku2[5],
                }
                
                # Run all detection methods
                detected = self.detect_conflicts_between(ku1_data, ku2_data)
                conflicts.extend(detected)
        
        logger.info(f"Conflict detection complete: {len(conflicts)} conflicts found")
        return conflicts
    
    def detect_conflicts_between(
        self,
        ku1: dict[str, Any],
        ku2: dict[str, Any],
    ) -> list[ConflictRecord]:
        """Detect conflicts between two knowledge units.
        
        Args:
            ku1: First knowledge unit data
            ku2: Second knowledge unit data
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # 1. Check semantic conflicts (negation)
        semantic_conflicts = self._check_semantic_conflict(ku1, ku2)
        conflicts.extend(semantic_conflicts)
        
        # 2. Check temporal conflicts
        temporal_conflicts = self._check_temporal_conflict(ku1, ku2)
        conflicts.extend(temporal_conflicts)
        
        # 3. Check source conflicts
        source_conflicts = self._check_source_conflict(ku1, ku2)
        conflicts.extend(source_conflicts)
        
        return conflicts
    
    def _check_semantic_conflict(
        self,
        ku1: dict[str, Any],
        ku2: dict[str, Any],
    ) -> list[ConflictRecord]:
        """Check for semantic (meaning-based) conflicts.
        
        Args:
            ku1: First knowledge unit
            ku2: Second knowledge unit
            
        Returns:
            List of semantic conflicts
        """
        conflicts = []
        
        content1 = ku1.get("content", "").lower()
        content2 = ku2.get("content", "").lower()
        
        # Skip if same content
        if content1 == content2:
            return conflicts
        
        # Check for negation patterns
        has_negation_1 = self._has_negation(content1)
        has_negation_2 = self._has_negation(content2)
        
        if has_negation_1 and has_negation_2:
            # Both have negations - check if they contradict
            base1 = self._remove_negation(content1)
            base2 = self._remove_negation(content2)
            
            if self._is_semantically_similar(base1, base2):
                conflict = ConflictRecord(
                    id=self._generate_id(),
                    ku1_id=ku1["id"],
                    ku2_id=ku2["id"],
                    conflict_type=ConflictType.SEMANTIC,
                    severity=ConflictSeverity.HIGH,
                    description=f"Các phát biểu đối lập: '{content1}' vs '{content2}'",
                    evidence=[content1, content2],
                    detected_at=self._now(),
                )
                conflicts.append(conflict)
                self._save_conflict(conflict)
        
        # Check for direct contradiction patterns
        if self._is_direct_contradiction(content1, content2):
            conflict = ConflictRecord(
                id=self._generate_id(),
                ku1_id=ku1["id"],
                ku2_id=ku2["id"],
                conflict_type=ConflictType.SEMANTIC,
                severity=ConflictSeverity.CRITICAL,
                description=f"Mâu thuẫn trực tiếp giữa hai phát biểu",
                evidence=[content1, content2],
                detected_at=self._now(),
            )
            conflicts.append(conflict)
            self._save_conflict(conflict)
        
        return conflicts
    
    def _check_temporal_conflict(
        self,
        ku1: dict[str, Any],
        ku2: dict[str, Any],
    ) -> list[ConflictRecord]:
        """Check for temporal (time-based) conflicts.
        
        Args:
            ku1: First knowledge unit
            ku2: Second knowledge unit
            
        Returns:
            List of temporal conflicts
        """
        conflicts = []
        
        eff_from_1 = ku1.get("effective_from")
        eff_until_1 = ku1.get("effective_until")
        eff_from_2 = ku2.get("effective_from")
        eff_until_2 = ku2.get("effective_until")
        
        # Check if time ranges overlap
        if not self._time_ranges_overlap(
            eff_from_1, eff_until_1,
            eff_from_2, eff_until_2
        ):
            # No overlap - no temporal conflict
            return conflicts
        
        # Time ranges overlap - check if content contradicts
        content1 = ku1.get("content", "").lower()
        content2 = ku2.get("content", "").lower()
        
        if self._is_direct_contradiction(content1, content2):
            conflict = ConflictRecord(
                id=self._generate_id(),
                ku1_id=ku1["id"],
                ku2_id=ku2["id"],
                conflict_type=ConflictType.TEMPORAL,
                severity=ConflictSeverity.MEDIUM,
                description=f"Mâu thuẫn thời gian: cả hai đều hiệu lực trong cùng khoảng thời gian",
                evidence=[
                    f"KU1: {eff_from_1} đến {eff_until_1}",
                    f"KU2: {eff_from_2} đến {eff_until_2}",
                ],
                detected_at=self._now(),
            )
            conflicts.append(conflict)
            self._save_conflict(conflict)
        
        return conflicts
    
    def _check_source_conflict(
        self,
        ku1: dict[str, Any],
        ku2: dict[str, Any],
    ) -> list[ConflictRecord]:
        """Check for source-based conflicts.
        
        Args:
            ku1: First knowledge unit
            ku2: Second knowledge unit
            
        Returns:
            List of source conflicts
        """
        conflicts = []
        
        # Parse provenance
        import json
        try:
            prov1 = json.loads(ku1.get("provenance_json", "{}"))
            prov2 = json.loads(ku2.get("provenance_json", "{}"))
        except:
            return conflicts
        
        source_type_1 = prov1.get("source_type", "")
        source_type_2 = prov2.get("source_type", "")
        
        # Check if different source types make same claim
        if source_type_1 != source_type_2:
            content1 = ku1.get("content", "").lower()
            content2 = ku2.get("content", "").lower()
            
            # Check if they're making similar claims
            if self._is_semantically_similar(content1, content2):
                # Same claim, different sources - potential conflict if sources have different reliability
                severity = ConflictSeverity.LOW
                if (source_type_1 == "EXTERNAL_UNVERIFIED" or 
                    source_type_2 == "EXTERNAL_UNVERIFIED"):
                    severity = ConflictSeverity.MEDIUM
                
                conflict = ConflictRecord(
                    id=self._generate_id(),
                    ku1_id=ku1["id"],
                    ku2_id=ku2["id"],
                    conflict_type=ConflictType.SOURCE,
                    severity=severity,
                    description=f"Cùng nội dung từ các nguồn khác nhau: {source_type_1} vs {source_type_2}",
                    evidence=[source_type_1, source_type_2],
                    detected_at=self._now(),
                )
                conflicts.append(conflict)
                self._save_conflict(conflict)
        
        return conflicts
    
    def _has_negation(self, text: str) -> bool:
        """Check if text contains negation markers."""
        text_lower = text.lower()
        return any(marker in text_lower for marker in self.NEGATION_MARKERS)
    
    def _remove_negation(self, text: str) -> str:
        """Remove negation from text for comparison."""
        result = text
        for marker in self.NEGATION_MARKERS:
            result = result.replace(marker, "").strip()
        return result
    
    def _is_semantically_similar(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """Check if two texts are semantically similar.
        
        Simple implementation using word overlap.
        TODO: Replace with embedding-based similarity in production.
        
        Args:
            text1: First text
            text2: Second text
            threshold: Similarity threshold
            
        Returns:
            True if similar
        """
        # Simple word overlap (placeholder for embedding-based)
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        similarity = overlap / min(len(words1), len(words2))
        
        return similarity > threshold
    
    def _is_direct_contradiction(self, text1: str, text2: str) -> bool:
        """Check if two texts directly contradict each other.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if direct contradiction
        """
        # Check for contradiction patterns
        for pattern in self.CONTRADICTION_PATTERNS:
            if re.search(pattern, text1) and re.search(pattern, text2):
                return True
        
        # Check if one has negation and other doesn't, but they're similar otherwise
        has_neg_1 = self._has_negation(text1)
        has_neg_2 = self._has_negation(text2)
        
        if has_neg_1 != has_neg_2:  # XOR - one has negation, other doesn't
            base1 = self._remove_negation(text1)
            base2 = self._remove_negation(text2)
            
            if self._is_semantically_similar(base1, base2, threshold=0.6):
                return True
        
        return False
    
    def _time_ranges_overlap(
        self,
        from1: Optional[str],
        until1: Optional[str],
        from2: Optional[str],
        until2: Optional[str],
    ) -> bool:
        """Check if two time ranges overlap.
        
        Args:
            from1: Start of first range
            until1: End of first range
            from2: Start of second range
            until2: End of second range
            
        Returns:
            True if ranges overlap
        """
        # If no temporal info, assume they overlap
        if not from1 and not until1 and not from2 and not until2:
            return True
        
        # Simple overlap check (placeholder - needs proper date parsing)
        return True  # Conservative: assume overlap if uncertain
    
    def _save_conflict(self, conflict: ConflictRecord):
        """Save conflict to database.
        
        Args:
            conflict: Conflict record to save
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_conflicts
            (id, ku1_id, ku2_id, conflict_type, severity, description,
             evidence_json, detected_at, resolution_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conflict.id,
            conflict.ku1_id,
            conflict.ku2_id,
            conflict.conflict_type.value,
            conflict.severity.value,
            conflict.description,
            json.dumps(conflict.evidence),
            conflict.detected_at,
            conflict.resolution_status,
        ))
        self.db.commit()
    
    def get_conflicts_for_ku(self, ku_id: str) -> list[ConflictRecord]:
        """Get all conflicts involving a knowledge unit.
        
        Args:
            ku_id: Knowledge unit ID
            
        Returns:
            List of conflicts
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, ku1_id, ku2_id, conflict_type, severity, description,
                   evidence_json, detected_at, resolution_status,
                   resolution_decision, resolved_by, resolved_at
            FROM knowledge_conflicts
            WHERE ku1_id = ? OR ku2_id = ?
            ORDER BY detected_at DESC
        """, (ku_id, ku_id))
        
        conflicts = []
        for row in cursor.fetchall():
            conflicts.append(ConflictRecord(
                id=row[0],
                ku1_id=row[1],
                ku2_id=row[2],
                conflict_type=ConflictType(row[3]),
                severity=ConflictSeverity(row[4]),
                description=row[5],
                evidence=json.loads(row[6]) if row[6] else [],
                detected_at=row[7],
                resolution_status=row[8],
                resolution_decision=row[9],
                resolved_by=row[10],
                resolved_at=row[11],
            ))
        
        return conflicts
    
    def get_unresolved_conflicts(self) -> list[ConflictRecord]:
        """Get all unresolved conflicts.
        
        Returns:
            List of unresolved conflicts
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, ku1_id, ku2_id, conflict_type, severity, description,
                   evidence_json, detected_at, resolution_status,
                   resolution_decision, resolved_by, resolved_at
            FROM knowledge_conflicts
            WHERE resolution_status = 'unresolved'
            ORDER BY detected_at DESC
        """)
        
        conflicts = []
        for row in cursor.fetchall():
            conflicts.append(ConflictRecord(
                id=row[0],
                ku1_id=row[1],
                ku2_id=row[2],
                conflict_type=ConflictType(row[3]),
                severity=ConflictSeverity(row[4]),
                description=row[5],
                evidence=json.loads(row[6]) if row[6] else [],
                detected_at=row[7],
                resolution_status=row[8],
                resolution_decision=row[9],
                resolved_by=row[10],
                resolved_at=row[11],
            ))
        
        return conflicts
    
    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_decision: str,
        resolved_by: str,
    ) -> bool:
        """Resolve a conflict.
        
        Args:
            conflict_id: Conflict ID
            resolution_decision: How it was resolved
            resolved_by: Who resolved it
            
        Returns:
            True if resolved successfully
        """
        timestamp = self._now()
        
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE knowledge_conflicts
            SET resolution_status = 'resolved',
                resolution_decision = ?,
                resolved_by = ?,
                resolved_at = ?
            WHERE id = ?
        """, (resolution_decision, resolved_by, timestamp, conflict_id))
        
        self.db.commit()
        
        logger.info(f"Resolved conflict {conflict_id}: {resolution_decision} by {resolved_by}")
        return True
    
    def get_conflict_statistics(self) -> dict[str, Any]:
        """Get conflict statistics.
        
        Returns:
            Statistics about conflicts
        """
        cursor = self.db.cursor()
        
        # Total conflicts
        cursor.execute("SELECT COUNT(*) FROM knowledge_conflicts")
        total = cursor.fetchone()[0]
        
        # Unresolved
        cursor.execute("SELECT COUNT(*) FROM knowledge_conflicts WHERE resolution_status = 'unresolved'")
        unresolved = cursor.fetchone()[0]
        
        # By type
        cursor.execute("""
            SELECT conflict_type, COUNT(*) 
            FROM knowledge_conflicts 
            GROUP BY conflict_type
        """)
        by_type = dict(cursor.fetchall())
        
        # By severity
        cursor.execute("""
            SELECT severity, COUNT(*) 
            FROM knowledge_conflicts 
            GROUP BY severity
        """)
        by_severity = dict(cursor.fetchall())
        
        return {
            "total": total,
            "unresolved": unresolved,
            "resolved": total - unresolved,
            "by_type": by_type,
            "by_severity": by_severity,
        }


# Import json at module level
import json