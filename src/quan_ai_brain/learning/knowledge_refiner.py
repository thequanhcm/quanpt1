"""Knowledge Refiner - Improve and refine existing knowledge.

Provides:
- Knowledge quality assessment
- Knowledge merging and deduplication
- Knowledge evolution tracking
- Knowledge validation
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from pathlib import Path


@dataclass
class KnowledgeRefinement:
    """Knowledge refinement record."""
    id: str
    knowledge_id: str
    refinement_type: str
    timestamp: str
    old_value: str
    new_value: str
    reason: str
    confidence_before: float
    confidence_after: float
    feedback_score: float | None = None
    metadata_json: str = '{}'
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'KnowledgeRefinement':
        return cls(**data)


@dataclass
class KnowledgeQuality:
    """Knowledge quality metrics."""
    knowledge_id: str
    last_assessed: str
    accuracy_score: float
    completeness_score: float
    recency_score: float
    feedback_score: float
    overall_score: float
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KnowledgeRefiner:
    """Refine and improve knowledge."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize refinement tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Knowledge refinements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_refinements (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                refinement_type TEXT NOT NULL,
                old_value TEXT NOT NULL,
                new_value TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence_before REAL NOT NULL,
                confidence_after REAL NOT NULL,
                feedback_score REAL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Knowledge quality assessments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_quality (
                knowledge_id TEXT PRIMARY KEY,
                accuracy_score REAL NOT NULL,
                completeness_score REAL NOT NULL,
                recency_score REAL NOT NULL,
                feedback_score REAL,
                overall_score REAL NOT NULL,
                last_assessed TEXT NOT NULL
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_refinements_knowledge 
            ON knowledge_refinements(knowledge_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_refinements_type 
            ON knowledge_refinements(refinement_type)
        """)
        
        conn.commit()
        conn.close()
    
    def record_refinement(self, knowledge_id: str, refinement_type: str,
                         old_value: str, new_value: str, reason: str,
                         confidence_before: float, confidence_after: float,
                         feedback_score: float | None = None,
                         metadata: dict | None = None) -> str:
        """Record knowledge refinement."""
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        
        refinement_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO knowledge_refinements 
            (id, knowledge_id, refinement_type, old_value, new_value, reason,
             confidence_before, confidence_after, feedback_score, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            refinement_id,
            knowledge_id,
            refinement_type,
            old_value,
            new_value,
            reason,
            confidence_before,
            confidence_after,
            feedback_score,
            now,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
        
        return refinement_id
    
    def assess_quality(self, knowledge_id: str,
                      accuracy: float, completeness: float,
                      recency: float, feedback: float | None = None) -> KnowledgeQuality:
        """Assess knowledge quality."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Calculate overall score
        weights = {
            'accuracy': 0.4,
            'completeness': 0.3,
            'recency': 0.2,
            'feedback': 0.1
        }
        
        feedback_score = feedback if feedback is not None else 0.5
        overall = (
            accuracy * weights['accuracy'] +
            completeness * weights['completeness'] +
            recency * weights['recency'] +
            feedback_score * weights['feedback']
        )
        
        quality = KnowledgeQuality(
            knowledge_id=knowledge_id,
            accuracy_score=accuracy,
            completeness_score=completeness,
            recency_score=recency,
            feedback_score=feedback_score,
            overall_score=overall,
            last_assessed=now
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge_quality 
            (knowledge_id, accuracy_score, completeness_score, recency_score,
             feedback_score, overall_score, last_assessed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            quality.knowledge_id,
            quality.accuracy_score,
            quality.completeness_score,
            quality.recency_score,
            quality.feedback_score,
            quality.overall_score,
            quality.last_assessed
        ))
        
        conn.commit()
        conn.close()
        
        return quality
    
    def get_quality(self, knowledge_id: str) -> KnowledgeQuality | None:
        """Get knowledge quality metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM knowledge_quality WHERE knowledge_id = ?
        """, (knowledge_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return KnowledgeQuality(
            knowledge_id=row['knowledge_id'],
            accuracy_score=row['accuracy_score'],
            completeness_score=row['completeness_score'],
            recency_score=row['recency_score'],
            feedback_score=row['feedback_score'],
            overall_score=row['overall_score'],
            last_assessed=row['last_assessed']
        )
    
    def get_refinements(self, knowledge_id: str | None = None,
                       refinement_type: str | None = None,
                       limit: int = 50) -> list[KnowledgeRefinement]:
        """Get refinement history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge_refinements WHERE 1=1"
        params = []
        
        if knowledge_id:
            query += " AND knowledge_id = ?"
            params.append(knowledge_id)
        
        if refinement_type:
            query += " AND refinement_type = ?"
            params.append(refinement_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        refinements = []
        for row in cursor.fetchall():
            refinements.append(KnowledgeRefinement(
                id=row['id'],
                knowledge_id=row['knowledge_id'],
                refinement_type=row['refinement_type'],
                old_value=row['old_value'],
                new_value=row['new_value'],
                reason=row['reason'],
                confidence_before=row['confidence_before'],
                confidence_after=row['confidence_after'],
                feedback_score=row['feedback_score'],
                timestamp=row['timestamp'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return refinements
    
    def merge_knowledge(self, source_ids: list[str], target_id: str,
                       merged_value: str, reason: str) -> str:
        """Record knowledge merge."""
        # Get source values
        conn = self._get_connection()
        cursor = conn.cursor()
        
        source_values = []
        for sid in source_ids:
            cursor.execute("""
                SELECT old_value FROM knowledge_refinements 
                WHERE knowledge_id = ? ORDER BY timestamp DESC LIMIT 1
            """, (sid,))
            row = cursor.fetchone()
            source_values.append(row['old_value'] if row else "unknown")
        
        conn.close()
        
        # Record merge
        return self.record_refinement(
            knowledge_id=target_id,
            refinement_type='merge',
            old_value=' | '.join(source_values),
            new_value=merged_value,
            reason=reason,
            confidence_before=0.5,
            confidence_after=0.8,
            metadata={'source_ids': source_ids}
        )
    
    def identify_low_quality(self, threshold: float = 0.5) -> list[str]:
        """Identify low-quality knowledge."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT knowledge_id FROM knowledge_quality
            WHERE overall_score < ?
            ORDER BY overall_score ASC
        """, (threshold,))
        
        ids = [row['knowledge_id'] for row in cursor.fetchall()]
        conn.close()
        
        return ids
    
    def get_improvement_suggestions(self, knowledge_id: str) -> list[dict[str, Any]]:
        """Get improvement suggestions for knowledge."""
        quality = self.get_quality(knowledge_id)
        
        if not quality:
            return []
        
        suggestions = []
        
        if quality.accuracy_score < 0.7:
            suggestions.append({
                'type': 'accuracy',
                'message': 'Knowledge accuracy is low. Consider verification.',
                'priority': 'high'
            })
        
        if quality.completeness_score < 0.7:
            suggestions.append({
                'type': 'completeness',
                'message': 'Knowledge is incomplete. Add more details.',
                'priority': 'medium'
            })
        
        if quality.recency_score < 0.5:
            suggestions.append({
                'type': 'recency',
                'message': 'Knowledge may be outdated. Update with latest info.',
                'priority': 'medium'
            })
        
        if quality.feedback_score and quality.feedback_score < 0.6:
            suggestions.append({
                'type': 'feedback',
                'message': 'Negative feedback received. Review and improve.',
                'priority': 'high'
            })
        
        return suggestions
    
    def get_statistics(self) -> dict[str, Any]:
        """Get refinement statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total refinements
        cursor.execute("SELECT COUNT(*) FROM knowledge_refinements")
        stats['total_refinements'] = cursor.fetchone()[0]
        
        # By type
        cursor.execute("""
            SELECT refinement_type, COUNT(*) FROM knowledge_refinements GROUP BY refinement_type
        """)
        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average confidence improvement
        cursor.execute("""
            SELECT AVG(confidence_after - confidence_before) as avg_improvement
            FROM knowledge_refinements
        """)
        stats['avg_confidence_improvement'] = cursor.fetchone()[0] or 0
        
        # Low quality knowledge count
        cursor.execute("""
            SELECT COUNT(*) FROM knowledge_quality WHERE overall_score < 0.5
        """)
        stats['low_quality_count'] = cursor.fetchone()[0]
        
        conn.close()
        return stats