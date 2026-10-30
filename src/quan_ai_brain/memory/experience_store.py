"""Experience Store - Storage and retrieval of experiences and outcomes.

Provides:
- Success/failure pattern storage
- Experience-based recommendations
- Pattern matching for similar situations
- Experience analytics
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path


class OutcomeType(str, Enum):
    """Type of outcome."""
    SUCCESS = 'success'
    FAILURE = 'failure'
    PARTIAL = 'partial'
    UNKNOWN = 'unknown'


class ExperienceType(str, Enum):
    """Type of experience."""
    TASK = 'task'
    WORKFLOW = 'workflow'
    DECISION = 'decision'
    PROBLEM_SOLVING = 'problem_solving'
    LEARNING = 'learning'
    GENERAL = 'general'


@dataclass
class Experience:
    """Single experience record."""
    id: str
    experience_type: ExperienceType
    title: str
    description: str
    context_json: str
    action_taken: str
    outcome: OutcomeType
    created_at: str
    updated_at: str
    outcome_details: str | None = None
    lessons_learned: str | None = None
    tags_json: str = field(default_factory=lambda: '[]')
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Experience':
        return cls(**data)


@dataclass
class PatternMatch:
    """Matched pattern with similarity score."""
    experience: Experience
    similarity_score: float
    matching_factors: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'experience': self.experience.to_dict(),
            'similarity_score': self.similarity_score,
            'matching_factors': self.matching_factors
        }


class ExperienceStore:
    """Store and retrieve experiences."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize experience tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Experiences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                experience_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                context_json TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                outcome TEXT NOT NULL,
                outcome_details TEXT,
                lessons_learned TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Experience outcomes summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experience_id TEXT NOT NULL,
                outcome_type TEXT NOT NULL,
                outcome_at TEXT NOT NULL,
                outcome_details TEXT,
                FOREIGN KEY (experience_id) REFERENCES experiences(id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exp_type 
            ON experiences(experience_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exp_outcome 
            ON experiences(outcome)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_exp_tags 
            ON experiences(tags_json)
        """)
        
        conn.commit()
        conn.close()
    
    def add_experience(self, experience_type: ExperienceType, title: str,
                      description: str, context: dict, action_taken: str,
                      outcome: OutcomeType, outcome_details: str | None = None,
                      lessons_learned: str | None = None,
                      tags: list[str] | None = None,
                      metadata: dict | None = None) -> Experience:
        """Add a new experience."""
        import uuid
        exp_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        experience = Experience(
            id=exp_id,
            experience_type=experience_type,
            title=title,
            description=description,
            context_json=json.dumps(context),
            action_taken=action_taken,
            outcome=outcome,
            outcome_details=outcome_details,
            lessons_learned=lessons_learned,
            created_at=now,
            updated_at=now,
            tags_json=json.dumps(tags or []),
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experiences 
            (id, experience_type, title, description, context_json,
             action_taken, outcome, outcome_details, lessons_learned,
             created_at, updated_at, tags_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            experience.id,
            experience.experience_type.value,
            experience.title,
            experience.description,
            experience.context_json,
            experience.action_taken,
            experience.outcome.value,
            experience.outcome_details,
            experience.lessons_learned,
            experience.created_at,
            experience.updated_at,
            experience.tags_json,
            experience.metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        return experience
    
    def get_experience(self, exp_id: str) -> Experience | None:
        """Get experience by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, experience_type, title, description, context_json,
                   action_taken, outcome, outcome_details, lessons_learned,
                   created_at, updated_at, tags_json, metadata_json
            FROM experiences
            WHERE id = ?
        """, (exp_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Experience(
            id=row['id'],
            experience_type=ExperienceType(row['experience_type']),
            title=row['title'],
            description=row['description'],
            context_json=row['context_json'],
            action_taken=row['action_taken'],
            outcome=OutcomeType(row['outcome']),
            outcome_details=row['outcome_details'],
            lessons_learned=row['lessons_learned'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            tags_json=row['tags_json'],
            metadata_json=row['metadata_json']
        )
    
    def search_experiences(self, experience_type: ExperienceType | None = None,
                          outcome: OutcomeType | None = None,
                          tags: list[str] | None = None,
                          limit: int = 50) -> list[Experience]:
        """Search experiences with filters."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM experiences WHERE 1=1"
        params = []
        
        if experience_type:
            query += " AND experience_type = ?"
            params.append(experience_type.value)
        
        if outcome:
            query += " AND outcome = ?"
            params.append(outcome.value)
        
        if tags:
            for tag in tags:
                query += " AND tags_json LIKE ?"
                params.append(f'%{tag}%')
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        experiences = []
        for row in cursor.fetchall():
            experiences.append(Experience(
                id=row['id'],
                experience_type=ExperienceType(row['experience_type']),
                title=row['title'],
                description=row['description'],
                context_json=row['context_json'],
                action_taken=row['action_taken'],
                outcome=OutcomeType(row['outcome']),
                outcome_details=row['outcome_details'],
                lessons_learned=row['lessons_learned'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                tags_json=row['tags_json'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return experiences
    
    def find_similar_experiences(self, context: dict,
                                experience_type: ExperienceType,
                                max_results: int = 10) -> list[PatternMatch]:
        """Find experiences with similar context."""
        all_experiences = self.search_experiences(
            experience_type=experience_type,
            limit=100
        )
        
        matches = []
        for exp in all_experiences:
            exp_context = json.loads(exp.context_json)
            score, factors = self._calculate_similarity(context, exp_context)
            
            if score > 0.3:
                matches.append(PatternMatch(
                    experience=exp,
                    similarity_score=score,
                    matching_factors=factors
                ))
        
        # Sort by similarity
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:max_results]
    
    def _calculate_similarity(self, context1: dict, context2: dict) -> tuple[float, list[str]]:
        """Calculate similarity between two contexts."""
        factors = []
        score = 0.0
        
        # Check common keys
        keys1 = set(context1.keys())
        keys2 = set(context2.keys())
        common_keys = keys1 & keys2
        
        if common_keys:
            # Score based on common keys
            key_score = len(common_keys) / max(len(keys1), len(keys2))
            score += key_score * 0.4
            factors.append(f"Common keys: {', '.join(common_keys)}")
        
        # Check matching values
        matches = 0
        for key in common_keys:
            if context1[key] == context2[key]:
                matches += 1
        
        if common_keys:
            value_score = matches / len(common_keys)
            score += value_score * 0.4
            if matches > 0:
                factors.append(f"Matching values: {matches}/{len(common_keys)}")
        
        # Check type match
        score += 0.2  # Base score for same experience type
        factors.append("Same experience type")
        
        return min(score, 1.0), factors
    
    def get_outcome_statistics(self) -> dict[str, Any]:
        """Get outcome statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count by outcome
        for outcome in OutcomeType:
            cursor.execute("""
                SELECT COUNT(*) FROM experiences WHERE outcome = ?
            """, (outcome.value,))
            stats[f'{outcome.value}_count'] = cursor.fetchone()[0]
        
        # Total experiences
        cursor.execute("SELECT COUNT(*) FROM experiences")
        stats['total_experiences'] = cursor.fetchone()[0]
        
        # Success rate
        success_count = stats.get('success_count', 0)
        total = stats['total_experiences']
        stats['success_rate'] = (success_count / total * 100) if total > 0 else 0
        
        # Count by type
        for exp_type in ExperienceType:
            cursor.execute("""
                SELECT COUNT(*) FROM experiences WHERE experience_type = ?
            """, (exp_type.value,))
            stats[f'{exp_type.value}_count'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def get_lessons_learned(self, experience_type: ExperienceType | None = None,
                           outcome: OutcomeType | None = None) -> list[str]:
        """Get all lessons learned."""
        experiences = self.search_experiences(
            experience_type=experience_type,
            outcome=outcome,
            limit=100
        )
        
        lessons = []
        for exp in experiences:
            if exp.lessons_learned:
                lessons.append({
                    'title': exp.title,
                    'lesson': exp.lessons_learned,
                    'outcome': exp.outcome.value
                })
        
        return lessons
    
    def update_experience(self, exp_id: str, lessons_learned: str | None = None,
                         outcome_details: str | None = None,
                         metadata: dict | None = None):
        """Update experience with new information."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get current experience
        cursor.execute("""
            SELECT lessons_learned, outcome_details, metadata_json FROM experiences
            WHERE id = ?
        """, (exp_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Experience {exp_id} not found")
        
        # Update fields
        new_lessons = lessons_learned or row['lessons_learned']
        new_outcome = outcome_details or row['outcome_details']
        
        current_metadata = json.loads(row['metadata_json'])
        if metadata:
            current_metadata.update(metadata)
        
        cursor.execute("""
            UPDATE experiences 
            SET lessons_learned = ?, outcome_details = ?, 
                metadata_json = ?, updated_at = ?
            WHERE id = ?
        """, (
            new_lessons,
            new_outcome,
            json.dumps(current_metadata),
            now,
            exp_id
        ))
        
        conn.commit()
        conn.close()