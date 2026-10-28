"""V37.3 Quarantine Mechanism - Knowledge Isolation for Self-Learned Content.

Implements:
- Quarantine store for unverified knowledge
- Approval workflow for moving to verified
- Automatic expiration for stale quarantine
- DIR-04 weekly reports
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional
from enum import Enum


class QuarantineStatus(str, Enum):
    """Status of quarantined knowledge."""
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class QuarantinedKnowledge:
    """Knowledge in quarantine awaiting approval."""
    id: str
    content: str
    source_ref: str
    discovered_at: str
    expires_at: str
    status: str = QuarantineStatus.PENDING_REVIEW.value
    review_notes: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'QuarantinedKnowledge':
        return cls(**data)


class QuarantineStore:
    """SQLite store for quarantined knowledge."""
    
    def __init__(self, db_path: str = "data/quarantine.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quarantined_knowledge (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
                review_notes TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                metadata_json TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON quarantined_knowledge(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires ON quarantined_knowledge(expires_at)
        """)
        
        conn.commit()
        conn.close()
    
    def add_knowledge(
        self,
        content: str,
        source_ref: str,
        expires_days: int = 30,
        metadata: dict[str, Any] = None
    ) -> str:
        """Add knowledge to quarantine."""
        import uuid
        
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=expires_days)
        
        record = QuarantinedKnowledge(
            id=str(uuid.uuid4()),
            content=content,
            source_ref=source_ref,
            discovered_at=now.isoformat(),
            expires_at=expires.isoformat(),
            status=QuarantineStatus.PENDING_REVIEW.value,
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quarantined_knowledge 
            (id, content, source_ref, discovered_at, expires_at, status, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.content,
            record.source_ref,
            record.discovered_at,
            record.expires_at,
            record.status,
            json.dumps(record.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        return record.id
    
    def list_pending(self, limit: int = 50) -> List[QuarantinedKnowledge]:
        """List all pending quarantine items."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM quarantined_knowledge
            WHERE status = 'PENDING_REVIEW'
            ORDER BY discovered_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [QuarantinedKnowledge.from_dict(dict(row)) for row in rows]
    
    def approve(self, ku_id: str, reviewed_by: str, notes: str = "") -> bool:
        """Approve quarantine item."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE quarantined_knowledge
            SET status = 'APPROVED',
                reviewed_by = ?,
                reviewed_at = ?,
                review_notes = ?
            WHERE id = ? AND status = 'PENDING_REVIEW'
        """, (reviewed_by, now, notes, ku_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def reject(self, ku_id: str, reviewed_by: str, reason: str = "") -> bool:
        """Reject quarantine item."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE quarantined_knowledge
            SET status = 'REJECTED',
                reviewed_by = ?,
                reviewed_at = ?,
                review_notes = ?
            WHERE id = ? AND status = 'PENDING_REVIEW'
        """, (reviewed_by, now, reason, ku_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def expire_stale(self) -> int:
        """Mark expired items as EXPIRED."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE quarantined_knowledge
            SET status = 'EXPIRED'
            WHERE status = 'PENDING_REVIEW' AND expires_at < ?
        """, (now,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected
    
    def get_stats(self) -> dict[str, Any]:
        """Get quarantine statistics."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        stats = {}
        
        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM quarantined_knowledge
            GROUP BY status
        """)
        
        stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Total
        cursor.execute("SELECT COUNT(*) as total FROM quarantined_knowledge")
        stats['total'] = cursor.fetchone()['total']
        
        # Pending
        cursor.execute("SELECT COUNT(*) as pending FROM quarantined_knowledge WHERE status = 'PENDING_REVIEW'")
        stats['pending'] = cursor.fetchone()['pending']
        
        conn.close()
        
        return stats
    
    def generate_weekly_report(self) -> dict[str, Any]:
        """Generate DIR-04 weekly report."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        # New this week
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM quarantined_knowledge
            WHERE discovered_at > ?
        """, (week_ago,))
        new_this_week = cursor.fetchone()['count']
        
        # Approved this week
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM quarantined_knowledge
            WHERE status = 'APPROVED' AND reviewed_at > ?
        """, (week_ago,))
        approved_this_week = cursor.fetchone()['count']
        
        # Rejected this week
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM quarantined_knowledge
            WHERE status = 'REJECTED' AND reviewed_at > ?
        """, (week_ago,))
        rejected_this_week = cursor.fetchone()['count']
        
        # Expired this week
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM quarantined_knowledge
            WHERE status = 'EXPIRED' AND expires_at > ? AND expires_at < ?
        """, (week_ago, datetime.now(timezone.utc).isoformat()))
        expired_this_week = cursor.fetchone()['count']
        
        # Top sources
        cursor.execute("""
            SELECT source_ref, COUNT(*) as count
            FROM quarantined_knowledge
            WHERE discovered_at > ?
            GROUP BY source_ref
            ORDER BY count DESC
            LIMIT 5
        """, (week_ago,))
        top_sources = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "period": f"Last 7 days (until {datetime.now(timezone.utc).strftime('%Y-%m-%d')})",
            "new_knowledge": new_this_week,
            "approved": approved_this_week,
            "rejected": rejected_this_week,
            "expired": expired_this_week,
            "top_sources": top_sources,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Factory function
def create_quarantine_store(db_path: str = "data/quarantine.db") -> QuarantineStore:
    """Create quarantine store."""
    return QuarantineStore(db_path)