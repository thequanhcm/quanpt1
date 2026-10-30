"""Feedback Processor - Collect and process user feedback.

Provides:
- Multi-scale feedback collection (1-5 stars, thumbs, text)
- Feedback categorization
- Sentiment analysis
- Feedback-driven improvements
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path


class FeedbackType(str, Enum):
    """Type of feedback."""
    RATING = 'rating'
    THUMBS = 'thumbs'
    TEXT = 'text'
    COMBINED = 'combined'


class FeedbackCategory(str, Enum):
    """Category of feedback."""
    QUALITY = 'quality'
    ACCURACY = 'accuracy'
    SPEED = 'speed'
    USABILITY = 'usability'
    HELPFULNESS = 'helpfulness'
    RELEVANCE = 'relevance'
    COMPLETENESS = 'completeness'
    OTHER = 'other'


class Sentiment(str, Enum):
    """Sentiment of feedback."""
    POSITIVE = 'positive'
    NEUTRAL = 'neutral'
    NEGATIVE = 'negative'


@dataclass
class Feedback:
    """Single feedback record."""
    id: str
    feedback_type: FeedbackType
    category: FeedbackCategory
    created_at: str
    rating: float | None = None
    thumbs: int | None = None
    text: str | None = None
    sentiment: Sentiment | None = None
    context_json: str = '{}'
    entity_type: str | None = None
    entity_id: str | None = None
    processed: bool = False
    metadata_json: str = '{}'
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Feedback':
        return cls(**data)


@dataclass
class FeedbackSummary:
    """Aggregated feedback summary."""
    entity_type: str
    entity_id: str
    total_feedbacks: int
    avg_rating: float | None
    thumbs_distribution: dict[str, int]
    sentiment_distribution: dict[str, int]
    category_breakdown: dict[str, int]
    recent_trend: str  # 'improving', 'stable', 'declining'
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FeedbackProcessor:
    """Process and analyze feedback."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize feedback tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                feedback_type TEXT NOT NULL,
                category TEXT NOT NULL,
                rating REAL,
                thumbs INTEGER,
                text TEXT,
                sentiment TEXT,
                context_json TEXT NOT NULL DEFAULT '{}',
                entity_type TEXT,
                entity_id TEXT,
                created_at TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Feedback aggregations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_aggregations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                category TEXT NOT NULL,
                total_count INTEGER NOT NULL,
                avg_rating REAL,
                thumbs_positive INTEGER NOT NULL DEFAULT 0,
                thumbs_neutral INTEGER NOT NULL DEFAULT 0,
                thumbs_negative INTEGER NOT NULL DEFAULT 0,
                sentiment_positive INTEGER NOT NULL DEFAULT 0,
                sentiment_neutral INTEGER NOT NULL DEFAULT 0,
                sentiment_negative INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(entity_type, entity_id, category)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_entity 
            ON feedback(entity_type, entity_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_category 
            ON feedback(category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_sentiment 
            ON feedback(sentiment)
        """)
        
        conn.commit()
        conn.close()
    
    def submit_feedback(self, feedback_type: FeedbackType, category: FeedbackCategory,
                       rating: float | None = None, thumbs: int | None = None,
                       text: str | None = None, context: dict | None = None,
                       entity_type: str | None = None, entity_id: str | None = None,
                       metadata: dict | None = None) -> Feedback:
        """Submit new feedback."""
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        
        # Determine sentiment
        sentiment = self._determine_sentiment(rating, thumbs, text)
        
        feedback = Feedback(
            id=str(uuid.uuid4()),
            feedback_type=feedback_type,
            category=category,
            rating=rating,
            thumbs=thumbs,
            text=text,
            sentiment=sentiment,
            context_json=json.dumps(context or {}),
            entity_type=entity_type,
            entity_id=entity_id,
            created_at=now,
            metadata_json=json.dumps(metadata or {})
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feedback 
            (id, feedback_type, category, rating, thumbs, text, sentiment,
             context_json, entity_type, entity_id, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback.id,
            feedback.feedback_type.value,
            feedback.category.value,
            feedback.rating,
            feedback.thumbs,
            feedback.text,
            feedback.sentiment.value if feedback.sentiment else None,
            feedback.context_json,
            feedback.entity_type,
            feedback.entity_id,
            feedback.created_at,
            feedback.metadata_json
        ))
        
        # Update aggregation
        self._update_aggregation(cursor, feedback)
        
        conn.commit()
        conn.close()
        
        return feedback
    
    def _determine_sentiment(self, rating: float | None, thumbs: int | None,
                            text: str | None) -> Sentiment | None:
        """Determine sentiment from feedback."""
        # Priority: rating > thumbs > text analysis
        if rating is not None:
            if rating >= 4:
                return Sentiment.POSITIVE
            elif rating <= 2:
                return Sentiment.NEGATIVE
            else:
                return Sentiment.NEUTRAL
        
        if thumbs is not None:
            if thumbs > 0:
                return Sentiment.POSITIVE
            elif thumbs < 0:
                return Sentiment.NEGATIVE
            else:
                return Sentiment.NEUTRAL
        
        # Simple text analysis
        if text:
            text_lower = text.lower()
            positive_words = ['good', 'great', 'excellent', 'helpful', 'useful', 'perfect']
            negative_words = ['bad', 'terrible', 'useless', 'wrong', 'failed', 'error']
            
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count > neg_count:
                return Sentiment.POSITIVE
            elif neg_count > pos_count:
                return Sentiment.NEGATIVE
            else:
                return Sentiment.NEUTRAL
        
        return None
    
    def _update_aggregation(self, cursor, feedback: Feedback):
        """Update feedback aggregation."""
        if not feedback.entity_type or not feedback.entity_id:
            return
        
        # Get current aggregation
        cursor.execute("""
            SELECT * FROM feedback_aggregations 
            WHERE entity_type = ? AND entity_id = ? AND category = ?
        """, (feedback.entity_type, feedback.entity_id, feedback.category.value))
        
        row = cursor.fetchone()
        
        if row:
            # Update existing
            new_count = row['total_count'] + 1
            new_avg = self._calculate_new_avg(
                row['avg_rating'] or 0,
                row['total_count'],
                feedback.rating
            ) if feedback.rating is not None else row['avg_rating']
            
            thumbs_pos = row['thumbs_positive']
            thumbs_neu = row['thumbs_neutral']
            thumbs_neg = row['thumbs_negative']
            
            if feedback.thumbs is not None:
                if feedback.thumbs > 0:
                    thumbs_pos += 1
                elif feedback.thumbs < 0:
                    thumbs_neg += 1
                else:
                    thumbs_neu += 1
            
            sent_pos = row['sentiment_positive']
            sent_neu = row['sentiment_neutral']
            sent_neg = row['sentiment_negative']
            
            if feedback.sentiment == Sentiment.POSITIVE:
                sent_pos += 1
            elif feedback.sentiment == Sentiment.NEUTRAL:
                sent_neu += 1
            elif feedback.sentiment == Sentiment.NEGATIVE:
                sent_neg += 1
            
            now = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                UPDATE feedback_aggregations 
                SET total_count = ?, avg_rating = ?,
                    thumbs_positive = ?, thumbs_neutral = ?, thumbs_negative = ?,
                    sentiment_positive = ?, sentiment_neutral = ?, sentiment_negative = ?,
                    updated_at = ?
                WHERE entity_type = ? AND entity_id = ? AND category = ?
            """, (
                new_count, new_avg,
                thumbs_pos, thumbs_neu, thumbs_neg,
                sent_pos, sent_neu, sent_neg,
                now,
                feedback.entity_type, feedback.entity_id, feedback.category.value
            ))
        else:
            # Create new
            thumbs_pos = 1 if feedback.thumbs and feedback.thumbs > 0 else 0
            thumbs_neu = 1 if feedback.thumbs and feedback.thumbs == 0 else 0
            thumbs_neg = 1 if feedback.thumbs and feedback.thumbs < 0 else 0
            
            sent_pos = 1 if feedback.sentiment == Sentiment.POSITIVE else 0
            sent_neu = 1 if feedback.sentiment == Sentiment.NEUTRAL else 0
            sent_neg = 1 if feedback.sentiment == Sentiment.NEGATIVE else 0
            
            now = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                INSERT INTO feedback_aggregations 
                (entity_type, entity_id, category, total_count, avg_rating,
                 thumbs_positive, thumbs_neutral, thumbs_negative,
                 sentiment_positive, sentiment_neutral, sentiment_negative,
                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.entity_type,
                feedback.entity_id,
                feedback.category.value,
                1,
                feedback.rating,
                thumbs_pos, thumbs_neu, thumbs_neg,
                sent_pos, sent_neu, sent_neg,
                now
            ))
    
    def _calculate_new_avg(self, current_avg: float, current_count: int,
                          new_value: float | None) -> float | None:
        """Calculate new average with new value."""
        if new_value is None:
            return current_avg
        
        return ((current_avg * current_count) + new_value) / (current_count + 1)
    
    def get_feedback(self, feedback_id: str) -> Feedback | None:
        """Get feedback by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Feedback(
            id=row['id'],
            feedback_type=FeedbackType(row['feedback_type']),
            category=FeedbackCategory(row['category']),
            rating=row['rating'],
            thumbs=row['thumbs'],
            text=row['text'],
            sentiment=Sentiment(row['sentiment']) if row['sentiment'] else None,
            context_json=row['context_json'],
            entity_type=row['entity_type'],
            entity_id=row['entity_id'],
            created_at=row['created_at'],
            processed=bool(row['processed']),
            metadata_json=row['metadata_json']
        )
    
    def get_feedbacks(self, entity_type: str | None = None,
                     entity_id: str | None = None,
                     category: FeedbackCategory | None = None,
                     limit: int = 100) -> list[Feedback]:
        """Get feedbacks with filters."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM feedback WHERE 1=1"
        params = []
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        
        if category:
            query += " AND category = ?"
            params.append(category.value)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        feedbacks = []
        for row in cursor.fetchall():
            feedbacks.append(Feedback(
                id=row['id'],
                feedback_type=FeedbackType(row['feedback_type']),
                category=FeedbackCategory(row['category']),
                rating=row['rating'],
                thumbs=row['thumbs'],
                text=row['text'],
                sentiment=Sentiment(row['sentiment']) if row['sentiment'] else None,
                context_json=row['context_json'],
                entity_type=row['entity_type'],
                entity_id=row['entity_id'],
                created_at=row['created_at'],
                processed=bool(row['processed']),
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return feedbacks
    
    def get_aggregation(self, entity_type: str, entity_id: str,
                       category: FeedbackCategory) -> FeedbackSummary | None:
        """Get feedback aggregation for entity."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM feedback_aggregations 
            WHERE entity_type = ? AND entity_id = ? AND category = ?
        """, (entity_type, entity_id, category.value))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Determine trend
        trend = self._calculate_trend(entity_type, entity_id, category)
        
        return FeedbackSummary(
            entity_type=entity_type,
            entity_id=entity_id,
            total_feedbacks=row['total_count'],
            avg_rating=row['avg_rating'],
            thumbs_distribution={
                'positive': row['thumbs_positive'],
                'neutral': row['thumbs_neutral'],
                'negative': row['thumbs_negative']
            },
            sentiment_distribution={
                'positive': row['sentiment_positive'],
                'neutral': row['sentiment_neutral'],
                'negative': row['sentiment_negative']
            },
            category_breakdown={category.value: row['total_count']},
            recent_trend=trend
        )
    
    def _calculate_trend(self, entity_type: str, entity_id: str,
                        category: FeedbackCategory) -> str:
        """Calculate feedback trend."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get last 10 feedbacks
        cursor.execute("""
            SELECT rating, sentiment, created_at FROM feedback
            WHERE entity_type = ? AND entity_id = ? AND category = ?
            AND rating IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """, (entity_type, entity_id, category.value))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 2:
            return 'stable'
        
        # Compare first half vs second half
        first_half = rows[len(rows)//2:]
        second_half = rows[:len(rows)//2]
        
        first_avg = sum(r['rating'] for r in first_half if r['rating']) / len(first_half)
        second_avg = sum(r['rating'] for r in second_half if r['rating']) / len(second_half)
        
        diff = second_avg - first_avg
        
        if diff > 0.5:
            return 'improving'
        elif diff < -0.5:
            return 'declining'
        else:
            return 'stable'
    
    def mark_processed(self, feedback_id: str):
        """Mark feedback as processed."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE feedback SET processed = 1 WHERE id = ?
        """, (feedback_id,))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> dict[str, Any]:
        """Get feedback statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total feedbacks
        cursor.execute("SELECT COUNT(*) FROM feedback")
        stats['total_feedbacks'] = cursor.fetchone()[0]
        
        # By type
        cursor.execute("""
            SELECT feedback_type, COUNT(*) FROM feedback GROUP BY feedback_type
        """)
        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # By category
        cursor.execute("""
            SELECT category, COUNT(*) FROM feedback GROUP BY category
        """)
        stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # By sentiment
        cursor.execute("""
            SELECT sentiment, COUNT(*) FROM feedback WHERE sentiment IS NOT NULL GROUP BY sentiment
        """)
        stats['by_sentiment'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average rating
        cursor.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL")
        stats['avg_rating'] = cursor.fetchone()[0] or 0
        
        conn.close()
        return stats