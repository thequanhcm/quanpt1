"""Best Practices - Library of proven practices and guidelines.

Provides:
- Best practices library
- Practice recommendation
- Practice validation
- Practice evolution tracking
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path

from .experience_store import ExperienceStore, OutcomeType, ExperienceType


class PracticeStatus(str, Enum):
    """Status of best practice."""
    DRAFT = 'draft'
    APPROVED = 'approved'
    REVIEWED = 'reviewed'
    OBSOLETE = 'obsolete'


class PracticeDomain(str, Enum):
    """Domain of best practice."""
    DEVELOPMENT = 'development'
    OPERATIONS = 'operations'
    SECURITY = 'security'
    PERFORMANCE = 'performance'
    DATA_MANAGEMENT = 'data_management'
    COMMUNICATION = 'communication'
    DECISION_MAKING = 'decision_making'
    PROBLEM_SOLVING = 'problem_solving'
    GENERAL = 'general'


@dataclass
class BestPractice:
    """Best practice entry."""
    id: str
    title: str
    description: str
    domain: PracticeDomain
    category: str
    steps: str
    benefits: str
    when_to_use: str
    when_avoid: str
    related_experiences: str
    status: PracticeStatus
    confidence_score: float
    created_at: str
    updated_at: str
    reviewed_by: str | None = None
    tags_json: str = field(default_factory=lambda: '[]')
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BestPractice':
        return cls(**data)


class BestPracticesLibrary:
    """Manage best practices library."""
    
    def __init__(self, db_path: str = "data/brain.db",
                 experience_store: ExperienceStore | None = None):
        self.db_path = Path(db_path)
        self.experience_store = experience_store or ExperienceStore()
        self._init_schema()
        self._practices: dict[str, BestPractice] = {}
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize best practices tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS best_practices (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                domain TEXT NOT NULL,
                category TEXT NOT NULL,
                steps TEXT NOT NULL,
                benefits TEXT NOT NULL,
                when_to_use TEXT NOT NULL,
                when_avoid TEXT,
                related_experiences TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reviewed_by TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Practice usage log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_id TEXT NOT NULL,
                used_at TEXT NOT NULL,
                context_json TEXT NOT NULL,
                outcome TEXT,
                effectiveness_score REAL,
                notes TEXT,
                FOREIGN KEY (practice_id) REFERENCES best_practices(id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_domain 
            ON best_practices(domain)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_status 
            ON best_practices(status)
        """)
        
        conn.commit()
        conn.close()
    
    def add_practice(self, title: str, description: str, domain: PracticeDomain,
                    category: str, steps: list[str], benefits: str,
                    when_to_use: str, when_avoid: str | None = None,
                    tags: list[str] | None = None,
                    metadata: dict | None = None) -> BestPractice:
        """Add a new best practice."""
        import uuid
        practice_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        practice = BestPractice(
            id=practice_id,
            title=title,
            description=description,
            domain=domain,
            category=category,
            steps=json.dumps(steps),
            benefits=benefits,
            when_to_use=when_to_use,
            when_avoid=when_avoid or "No specific avoidance",
            related_experiences=json.dumps([]),
            status=PracticeStatus.DRAFT,
            confidence_score=0.5,
            created_at=now,
            updated_at=now,
            tags_json=json.dumps(tags or []),
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO best_practices 
            (id, title, description, domain, category, steps, benefits,
             when_to_use, when_avoid, related_experiences, status,
             confidence_score, created_at, updated_at, tags_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            practice.id,
            practice.title,
            practice.description,
            practice.domain.value,
            practice.category,
            practice.steps,
            practice.benefits,
            practice.when_to_use,
            practice.when_avoid,
            practice.related_experiences,
            practice.status.value,
            practice.confidence_score,
            practice.created_at,
            practice.updated_at,
            practice.tags_json,
            practice.metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        self._practices[practice_id] = practice
        return practice
    
    def get_practice(self, practice_id: str) -> BestPractice | None:
        """Get practice by ID."""
        if practice_id in self._practices:
            return self._practices[practice_id]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM best_practices WHERE id = ?
        """, (practice_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        practice = BestPractice(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            domain=PracticeDomain(row['domain']),
            category=row['category'],
            steps=row['steps'],
            benefits=row['benefits'],
            when_to_use=row['when_to_use'],
            when_avoid=row['when_avoid'],
            related_experiences=row['related_experiences'],
            status=PracticeStatus(row['status']),
            confidence_score=row['confidence_score'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            reviewed_by=row['reviewed_by'],
            tags_json=row['tags_json'],
            metadata_json=row['metadata_json']
        )
        
        self._practices[practice_id] = practice
        return practice
    
    def search_practices(self, domain: PracticeDomain | None = None,
                        category: str | None = None,
                        status: PracticeStatus | None = None,
                        tags: list[str] | None = None,
                        limit: int = 50) -> list[BestPractice]:
        """Search best practices."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM best_practices WHERE 1=1"
        params = []
        
        if domain:
            query += " AND domain = ?"
            params.append(domain.value)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if tags:
            for tag in tags:
                query += " AND tags_json LIKE ?"
                params.append(f'%{tag}%')
        
        query += " ORDER BY confidence_score DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        practices = []
        for row in cursor.fetchall():
            practice = BestPractice(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                domain=PracticeDomain(row['domain']),
                category=row['category'],
                steps=row['steps'],
                benefits=row['benefits'],
                when_to_use=row['when_to_use'],
                when_avoid=row['when_avoid'],
                related_experiences=row['related_experiences'],
                status=PracticeStatus(row['status']),
                confidence_score=row['confidence_score'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                reviewed_by=row['reviewed_by'],
                tags_json=row['tags_json'],
                metadata_json=row['metadata_json']
            )
            practices.append(practice)
            self._practices[row['id']] = practice
        
        conn.close()
        return practices
    
    def approve_practice(self, practice_id: str, reviewed_by: str):
        """Approve a best practice."""
        practice = self.get_practice(practice_id)
        if not practice:
            raise ValueError(f"Practice {practice_id} not found")
        
        now = datetime.now(timezone.utc).isoformat()
        
        practice.status = PracticeStatus.APPROVED
        practice.reviewed_by = reviewed_by
        practice.updated_at = now
        practice.confidence_score = min(practice.confidence_score + 0.2, 1.0)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE best_practices 
            SET status = ?, reviewed_by = ?, updated_at = ?, confidence_score = ?
            WHERE id = ?
        """, (
            practice.status.value,
            practice.reviewed_by,
            practice.updated_at,
            practice.confidence_score,
            practice_id
        ))
        
        conn.commit()
        conn.close()
    
    def log_usage(self, practice_id: str, context: dict,
                 outcome: str | None = None,
                 effectiveness_score: float | None = None,
                 notes: str | None = None):
        """Log usage of a best practice."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO practice_usage 
            (practice_id, used_at, context_json, outcome, effectiveness_score, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            practice_id,
            now,
            json.dumps(context),
            outcome,
            effectiveness_score,
            notes
        ))
        
        conn.commit()
        conn.close()
    
    def recommend_practices(self, domain: PracticeDomain,
                           context: dict | None = None,
                           max_results: int = 5) -> list[BestPractice]:
        """Recommend best practices for a domain."""
        practices = self.search_practices(
            domain=domain,
            status=PracticeStatus.APPROVED,
            limit=50
        )
        
        # Sort by confidence score
        practices.sort(key=lambda p: p.confidence_score, reverse=True)
        
        return practices[:max_results]
    
    def get_practice_effectiveness(self, practice_id: str) -> dict[str, Any]:
        """Get effectiveness statistics for a practice."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_usage,
                AVG(effectiveness_score) as avg_effectiveness,
                COUNT(CASE WHEN outcome = 'success' THEN 1 END) as success_count
            FROM practice_usage
            WHERE practice_id = ?
        """, (practice_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total_usage': row['total_usage'] or 0,
            'avg_effectiveness': row['avg_effectiveness'] or 0,
            'success_count': row['success_count'] or 0
        }
    
    def get_statistics(self) -> dict[str, Any]:
        """Get library statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {
            'total_practices': len(self._practices),
            'by_status': {},
            'by_domain': {},
            'approved_count': 0
        }
        
        for status in PracticeStatus:
            cursor.execute("""
                SELECT COUNT(*) FROM best_practices WHERE status = ?
            """, (status.value,))
            count = cursor.fetchone()[0]
            stats['by_status'][status.value] = count
            if status == PracticeStatus.APPROVED:
                stats['approved_count'] = count
        
        for domain in PracticeDomain:
            cursor.execute("""
                SELECT COUNT(*) FROM best_practices WHERE domain = ?
            """, (domain.value,))
            stats['by_domain'][domain.value] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def create_from_experience(self, experience_id: str) -> BestPractice | None:
        """Create a best practice from a successful experience."""
        exp = self.experience_store.get_experience(experience_id)
        if not exp or exp.outcome != OutcomeType.SUCCESS:
            return None
        
        # Parse steps from action_taken
        steps = [exp.action_taken]
        
        practice = self.add_practice(
            title=f"Best Practice: {exp.title}",
            description=exp.description,
            domain=PracticeDomain.GENERAL,
            category=exp.experience_type.value,
            steps=steps,
            benefits=exp.outcome_details or "Successful outcome achieved",
            when_to_use=exp.description,
            when_avoid=None,
            tags=json.loads(exp.tags_json),
            metadata={"source_experience": experience_id}
        )
        
        # Link to experience
        related = json.loads(practice.related_experiences)
        related.append(experience_id)
        practice.related_experiences = json.dumps(related)
        
        return practice