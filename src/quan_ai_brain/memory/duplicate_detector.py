"""V31 Duplicate Detector - Detect duplicate knowledge units.

Duplicate types:
1. EXACT - Identical content (hash-based)
2. SEMANTIC - Same meaning, different wording (embedding-based)
3. NEAR_DUPLICATE - Minor variations (fuzzy matching)

Detection methods:
- SHA-256 hash for exact matches
- Cosine similarity for semantic matches (placeholder for embeddings)
- Levenshtein distance for near-duplicates
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

logger = logging.getLogger(__name__)


class DuplicateType(str, Enum):
    """Type of duplicate."""
    EXACT = "EXACT"           # Identical content
    SEMANTIC = "SEMANTIC"     # Same meaning, different wording
    NEAR_DUPLICATE = "NEAR_DUPLICATE"  # Minor variations


class DuplicateStatus(str, Enum):
    """Status of duplicate group."""
    OPEN = "open"             # Detected, not processed
    MERGED = "merged"         # Duplicates merged
    IGNORED = "ignored"       # Deliberately kept separate
    REVIEWED = "reviewed"     # Reviewed, no action needed


@dataclass
class DuplicateGroup:
    """Group of duplicate knowledge units."""
    id: str
    duplicate_type: DuplicateType
    similarity_score: float  # 0.0 to 1.0
    member_ids: list[str] = field(default_factory=list)
    primary_id: Optional[str] = None  # Which one to keep
    status: DuplicateStatus = DuplicateStatus.OPEN
    created_at: str = ""
    reviewed_at: str = ""
    reviewed_by: str = ""
    notes: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "duplicate_type": self.duplicate_type.value,
            "similarity_score": round(self.similarity_score, 3),
            "member_ids": self.member_ids,
            "primary_id": self.primary_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'DuplicateGroup':
        return cls(
            id=data["id"],
            duplicate_type=DuplicateType(data["duplicate_type"]),
            similarity_score=float(data["similarity_score"]),
            member_ids=data.get("member_ids", []),
            primary_id=data.get("primary_id"),
            status=DuplicateStatus(data.get("status", "open")),
            created_at=data.get("created_at", ""),
            reviewed_at=data.get("reviewed_at", ""),
            reviewed_by=data.get("reviewed_by", ""),
            notes=data.get("notes", ""),
        )


class DuplicateDetector:
    """Detects duplicates in knowledge base."""
    
    def __init__(self, db_connection, similarity_threshold: float = 0.85):
        """Initialize duplicate detector.
        
        Args:
            db_connection: SQLite connection to brain.db
            similarity_threshold: Threshold for semantic similarity (0-1)
        """
        self.db = db_connection
        self.similarity_threshold = similarity_threshold
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create duplicate tracking tables if they don't exist."""
        cursor = self.db.cursor()
        
        # Duplicate groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_groups (
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
        
        # Duplicate group members
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_group_members (
                group_id TEXT NOT NULL,
                knowledge_unit_id TEXT NOT NULL,
                is_primary BOOLEAN DEFAULT 0,
                content_hash TEXT,
                similarity_score REAL,
                FOREIGN KEY (group_id) REFERENCES duplicate_groups(id),
                FOREIGN KEY (knowledge_unit_id) REFERENCES knowledge_units(id),
                PRIMARY KEY (group_id, knowledge_unit_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dup_members_ku 
            ON duplicate_group_members(knowledge_unit_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dup_groups_status 
            ON duplicate_groups(status)
        """)
        
        self.db.commit()
        logger.info("Duplicate detector tables initialized")
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return str(uuid.uuid4())
    
    def _now(self) -> str:
        """Get current UTC timestamp."""
        return datetime.utcnow().isoformat() + "Z"
    
    def _compute_hash(self, text: str) -> str:
        """Compute SHA-256 hash of text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove stopwords (basic list)
        stopwords = {
            'và', 'của', 'các', 'được', 'là', 'có', 'trong', 'một', 'cho',
            'với', 'này', 'đó', 'khi', 'để', 'từ', 'theo', 'trên', 'không',
            'những', 'về', 'cũng', 'như', 'anh', 'em', 'tôi', 'bạn', 'bot',
            'trợ', 'lý', 'rồi', 'sẽ', 'mà', 'đi', 'ra', 'vào', 'thì', 'vì',
            'nếu', 'đã', 'vẫn'
        }
        words = text.split()
        words = [w for w in words if w not in stopwords]
        
        return ' '.join(words)
    
    def detect_all_duplicates(self) -> list[DuplicateGroup]:
        """Detect all duplicates in the knowledge base.
        
        Returns:
            List of duplicate groups
        """
        logger.info("Starting duplicate detection scan")
        
        # Get all knowledge units
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, content, content_hash
            FROM knowledge_units
            WHERE lifecycle_status != 'archived'
        """)
        
        kus = cursor.fetchall()
        duplicate_groups = []
        
        # 1. Detect exact duplicates (by hash)
        exact_groups = self._detect_exact_duplicates(kus)
        duplicate_groups.extend(exact_groups)
        
        # 2. Detect semantic duplicates
        semantic_groups = self._detect_semantic_duplicates(kus)
        duplicate_groups.extend(semantic_groups)
        
        # 3. Detect near-duplicates
        near_groups = self._detect_near_duplicates(kus)
        duplicate_groups.extend(near_groups)
        
        logger.info(f"Duplicate detection complete: {len(duplicate_groups)} groups found")
        return duplicate_groups
    
    def _detect_exact_duplicates(
        self,
        kus: list[tuple],
    ) -> list[DuplicateGroup]:
        """Detect exact duplicates by hash.
        
        Args:
            kus: List of (id, content, hash) tuples
            
        Returns:
            List of exact duplicate groups
        """
        groups = []
        
        # Group by hash
        hash_to_kus: dict[str, list[tuple]] = {}
        for ku in kus:
            ku_id, content, content_hash = ku
            if not content_hash:
                content_hash = self._compute_hash(content)
            
            if content_hash not in hash_to_kus:
                hash_to_kus[content_hash] = []
            hash_to_kus[content_hash].append(ku)
        
        # Create groups for hashes with multiple KUs
        for content_hash, ku_list in hash_to_kus.items():
            if len(ku_list) > 1:
                group = DuplicateGroup(
                    id=self._generate_id(),
                    duplicate_type=DuplicateType.EXACT,
                    similarity_score=1.0,
                    member_ids=[ku[0] for ku in ku_list],
                    primary_id=ku_list[0][0],  # First one is primary
                    status=DuplicateStatus.OPEN,
                    created_at=self._now(),
                )
                groups.append(group)
                self._save_duplicate_group(group, ku_list, 1.0)
        
        return groups
    
    def _detect_semantic_duplicates(
        self,
        kus: list[tuple],
    ) -> list[DuplicateGroup]:
        """Detect semantic duplicates using similarity.
        
        Args:
            kus: List of (id, content, hash) tuples
            
        Returns:
            List of semantic duplicate groups
        """
        groups = []
        
        # Normalize all content
        normalized_kus = []
        for ku in kus:
            ku_id, content, _ = ku
            normalized = self._normalize_text(content)
            normalized_kus.append((ku_id, content, normalized))
        
        # Compare each pair (simple implementation)
        # TODO: Replace with embedding-based similarity in production
        compared = set()
        for i, (id1, _, norm1) in enumerate(normalized_kus):
            for j, (id2, _, norm2) in enumerate(normalized_kus):
                if i >= j:
                    continue
                
                pair_key = (id1, id2)
                if pair_key in compared:
                    continue
                compared.add(pair_key)
                
                # Compute similarity (word overlap as placeholder)
                similarity = self._compute_word_similarity(norm1, norm2)
                
                if similarity >= self.similarity_threshold:
                    group = DuplicateGroup(
                        id=self._generate_id(),
                        duplicate_type=DuplicateType.SEMANTIC,
                        similarity_score=similarity,
                        member_ids=[id1, id2],
                        primary_id=id1,
                        status=DuplicateStatus.OPEN,
                        created_at=self._now(),
                    )
                    groups.append(group)
                    self._save_duplicate_group(group, [(id1,), (id2,)], similarity)
        
        return groups
    
    def _detect_near_duplicates(
        self,
        kus: list[tuple],
    ) -> list[DuplicateGroup]:
        """Detect near-duplicates using fuzzy matching.
        
        Args:
            kus: List of (id, content, hash) tuples
            
        Returns:
            List of near-duplicate groups
        """
        groups = []
        
        # Lower threshold for near-duplicates
        near_threshold = 0.7
        
        # Normalize all content
        normalized_kus = []
        for ku in kus:
            ku_id, content, _ = ku
            normalized = self._normalize_text(content)
            normalized_kus.append((ku_id, content, normalized))
        
        # Compare each pair
        compared = set()
        for i, (id1, _, norm1) in enumerate(normalized_kus):
            for j, (id2, _, norm2) in enumerate(normalized_kus):
                if i >= j:
                    continue
                
                pair_key = (id1, id2)
                if pair_key in compared:
                    continue
                compared.add(pair_key)
                
                # Skip if already detected as semantic duplicate
                if self._compute_word_similarity(norm1, norm2) >= self.similarity_threshold:
                    continue
                
                # Compute similarity
                similarity = self._compute_word_similarity(norm1, norm2)
                
                if near_threshold <= similarity < self.similarity_threshold:
                    group = DuplicateGroup(
                        id=self._generate_id(),
                        duplicate_type=DuplicateType.NEAR_DUPLICATE,
                        similarity_score=similarity,
                        member_ids=[id1, id2],
                        primary_id=id1,
                        status=DuplicateStatus.OPEN,
                        created_at=self._now(),
                    )
                    groups.append(group)
                    self._save_duplicate_group(group, [(id1,), (id2,)], similarity)
        
        return groups
    
    def _compute_word_similarity(self, text1: str, text2: str) -> float:
        """Compute word-based similarity between two texts.
        
        Uses Jaccard similarity as a simple placeholder.
        TODO: Replace with cosine similarity on embeddings in production.
        
        Args:
            text1: First normalized text
            text2: Second normalized text
            
        Returns:
            Similarity score (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _save_duplicate_group(
        self,
        group: DuplicateGroup,
        members: list[tuple],
        similarity: float,
    ):
        """Save duplicate group to database.
        
        Args:
            group: Duplicate group
            members: List of (ku_id,) tuples
            similarity: Similarity score
        """
        cursor = self.db.cursor()
        
        # Insert group
        cursor.execute("""
            INSERT OR REPLACE INTO duplicate_groups
            (id, duplicate_type, similarity_score, status, primary_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            group.id,
            group.duplicate_type.value,
            group.similarity_score,
            group.status.value,
            group.primary_id,
            group.created_at,
        ))
        
        # Insert members
        for i, member in enumerate(members):
            ku_id = member[0]
            is_primary = 1 if ku_id == group.primary_id else 0
            
            cursor.execute("""
                INSERT OR REPLACE INTO duplicate_group_members
                (group_id, knowledge_unit_id, is_primary, similarity_score)
                VALUES (?, ?, ?, ?)
            """, (group.id, ku_id, is_primary, similarity))
        
        self.db.commit()
    
    def get_duplicates_for_ku(self, ku_id: str) -> list[DuplicateGroup]:
        """Get all duplicate groups involving a knowledge unit.
        
        Args:
            ku_id: Knowledge unit ID
            
        Returns:
            List of duplicate groups
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT dg.id, dg.duplicate_type, dg.similarity_score, dg.status,
                   dg.primary_id, dg.created_at, dg.reviewed_at,
                   dg.reviewed_by, dg.notes
            FROM duplicate_groups dg
            JOIN duplicate_group_members dgm ON dg.id = dgm.group_id
            WHERE dgm.knowledge_unit_id = ?
            ORDER BY dg.similarity_score DESC
        """, (ku_id,))
        
        groups = []
        for row in cursor.fetchall():
            # Get all members
            cursor.execute("""
                SELECT knowledge_unit_id, is_primary
                FROM duplicate_group_members
                WHERE group_id = ?
            """, (row[0],))
            
            members = [m[0] for m in cursor.fetchall()]
            
            group = DuplicateGroup(
                id=row[0],
                duplicate_type=DuplicateType(row[1]),
                similarity_score=row[2],
                status=DuplicateStatus(row[3]),
                primary_id=row[4],
                created_at=row[5],
                reviewed_at=row[6],
                reviewed_by=row[7],
                notes=row[8],
                member_ids=members,
            )
            groups.append(group)
        
        return groups
    
    def get_open_duplicate_groups(self) -> list[DuplicateGroup]:
        """Get all open (unprocessed) duplicate groups.
        
        Returns:
            List of open duplicate groups
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT dg.id, dg.duplicate_type, dg.similarity_score, dg.status,
                   dg.primary_id, dg.created_at, dg.reviewed_at,
                   dg.reviewed_by, dg.notes
            FROM duplicate_groups dg
            WHERE dg.status = 'open'
            ORDER BY dg.similarity_score DESC
        """)
        
        groups = []
        for row in cursor.fetchall():
            # Get all members
            cursor.execute("""
                SELECT knowledge_unit_id
                FROM duplicate_group_members
                WHERE group_id = ?
            """, (row[0],))
            
            members = [m[0] for m in cursor.fetchall()]
            
            group = DuplicateGroup(
                id=row[0],
                duplicate_type=DuplicateType(row[1]),
                similarity_score=row[2],
                status=DuplicateStatus(row[3]),
                primary_id=row[4],
                created_at=row[5],
                reviewed_at=row[6],
                reviewed_by=row[7],
                notes=row[8],
                member_ids=members,
            )
            groups.append(group)
        
        return groups
    
    def merge_duplicates(
        self,
        group_id: str,
        primary_id: str,
        merged_by: str,
        notes: str = "",
    ) -> bool:
        """Merge duplicate group into primary.
        
        Args:
            group_id: Duplicate group ID
            primary_id: ID of primary KU to keep
            merged_by: Who performed the merge
            notes: Merge notes
            
        Returns:
            True if merged successfully
        """
        cursor = self.db.cursor()
        
        # Get all member IDs
        cursor.execute("""
            SELECT knowledge_unit_id, is_primary
            FROM duplicate_group_members
            WHERE group_id = ?
        """, (group_id,))
        
        members = cursor.fetchall()
        member_ids = [m[0] for m in members]
        
        if primary_id not in member_ids:
            logger.error(f"Primary ID {primary_id} not in group {group_id}")
            return False
        
        # Mark non-primary KUs as superseded
        for ku_id in member_ids:
            if ku_id != primary_id:
                cursor.execute("""
                    UPDATE knowledge_units
                    SET lifecycle_status = 'superseded',
                        superseded_by = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (primary_id, self._now(), ku_id))
        
        # Update group status
        cursor.execute("""
            UPDATE duplicate_groups
            SET status = 'merged',
                primary_id = ?,
                reviewed_at = ?,
                reviewed_by = ?,
                notes = ?
            WHERE id = ?
        """, (primary_id, self._now(), merged_by, notes, group_id))
        
        self.db.commit()
        
        logger.info(f"Merged duplicate group {group_id} into {primary_id}")
        return True
    
    def ignore_duplicate_group(
        self,
        group_id: str,
        ignored_by: str,
        notes: str = "",
    ) -> bool:
        """Mark duplicate group as ignored (keep separate).
        
        Args:
            group_id: Duplicate group ID
            ignored_by: Who ignored it
            notes: Reason for ignoring
            
        Returns:
            True if ignored successfully
        """
        cursor = self.db.cursor()
        
        cursor.execute("""
            UPDATE duplicate_groups
            SET status = 'ignored',
                reviewed_at = ?,
                reviewed_by = ?,
                notes = ?
            WHERE id = ?
        """, (self._now(), ignored_by, notes, group_id))
        
        self.db.commit()
        
        logger.info(f"Ignored duplicate group {group_id}")
        return True
    
    def get_duplicate_statistics(self) -> dict[str, Any]:
        """Get duplicate statistics.
        
        Returns:
            Statistics about duplicates
        """
        cursor = self.db.cursor()
        
        # Total groups
        cursor.execute("SELECT COUNT(*) FROM duplicate_groups")
        total = cursor.fetchone()[0]
        
        # By status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM duplicate_groups 
            GROUP BY status
        """)
        by_status = dict(cursor.fetchall())
        
        # By type
        cursor.execute("""
            SELECT duplicate_type, COUNT(*) 
            FROM duplicate_groups 
            GROUP BY duplicate_type
        """)
        by_type = dict(cursor.fetchall())
        
        # Open groups
        cursor.execute("SELECT COUNT(*) FROM duplicate_groups WHERE status = 'open'")
        open_count = cursor.fetchone()[0]
        
        return {
            "total_groups": total,
            "open": open_count,
            "merged": by_status.get("merged", 0),
            "ignored": by_status.get("ignored", 0),
            "by_type": by_type,
        }