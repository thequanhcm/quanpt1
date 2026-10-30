"""V16 — Emotional Memory & Sentiment Analysis.

Thêm chiều cảm xúc vào trí nhớ: emotional weight, sentiment tracking, mood patterns, emotion-based retrieval.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# Emotion lexicon (simplified rule-based)
EMOTION_LEXICON = {
    'joy': ['happy', 'joy', 'glad', 'pleased', 'delighted', 'cheerful', 'elated', 'thrilled', 'excited', 'pleasure'],
    'sadness': ['sad', 'unhappy', 'depressed', 'sorrow', 'grief', 'miserable', 'down', 'dejected', 'melancholy'],
    'anger': ['angry', 'mad', 'furious', 'irritated', 'annoyed', 'rage', 'hostile', 'bitter', 'resentful'],
    'fear': ['afraid', 'scared', 'fear', 'anxious', 'nervous', 'worried', 'terrified', 'panic', 'dread'],
    'surprise': ['surprised', 'shocked', 'astonished', 'amazed', 'stunned', 'startled'],
    'disgust': ['disgusted', 'revolted', 'nauseated', 'repulsed', 'hate', 'loathe', 'despise'],
    'trust': ['trust', 'confidence', 'faith', 'reliable', 'dependable', 'certain'],
    'anticipation': ['expect', 'anticipate', 'look forward', 'hope', 'await', 'predict']
}

SENTIMENT_WORDS = {
    'positive': ['good', 'great', 'excellent', 'wonderful', 'amazing', 'fantastic', 'love', 'best', 'happy', 'success'],
    'negative': ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'fail', 'wrong', 'sad', 'angry'],
    'neutral': ['okay', 'average', 'normal', 'regular', 'standard', 'typical']
}


@dataclass
class EmotionalWeight:
    """Emotional weight for a knowledge unit."""
    ku_id: str
    sentiment: str  # 'positive', 'negative', 'neutral'
    sentiment_score: float  # -1.0 to +1.0
    emotions: dict[str, float]  # emotion → intensity (0-1)
    dominant_emotion: str
    intensity: float  # overall emotional intensity (0-1)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EmotionEvent:
    """Emotion event for tracking."""
    user_id: str
    emotion: str
    intensity: float
    context: str | None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmotionalMemory:
    """Emotional memory storage and retrieval."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
    
    def _create_schema(self):
        """Create emotional memory schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS emotional_weights (
                ku_id TEXT PRIMARY KEY,
                sentiment TEXT NOT NULL,
                sentiment_score REAL NOT NULL,
                emotions TEXT NOT NULL,
                dominant_emotion TEXT NOT NULL,
                intensity REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS emotion_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                emotion TEXT NOT NULL,
                intensity REAL NOT NULL,
                context TEXT,
                timestamp TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_emotion_events_user ON emotion_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_emotion_events_time ON emotion_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_emotion_events_emotion ON emotion_events(emotion);
        """)
        self._conn.commit()
    
    def detect_sentiment(self, text: str) -> tuple[str, float]:
        """Detect sentiment from text."""
        if not text:
            return 'neutral', 0.0
        
        text_lower = text.lower()
        words = re.findall(r'\w+', text_lower)
        
        positive_count = 0
        negative_count = 0
        
        for word in words:
            if word in SENTIMENT_WORDS['positive']:
                positive_count += 1
            elif word in SENTIMENT_WORDS['negative']:
                negative_count += 1
        
        total = positive_count + negative_count
        if total == 0:
            return 'neutral', 0.0
        
        sentiment_score = (positive_count - negative_count) / total
        
        if sentiment_score > 0.1:
            sentiment = 'positive'
        elif sentiment_score < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return sentiment, sentiment_score
    
    def detect_emotions(self, text: str) -> dict[str, float]:
        """Detect emotions from text."""
        if not text:
            return {}
        
        text_lower = text.lower()
        words = re.findall(r'\w+', text_lower)
        
        emotion_scores = defaultdict(float)
        
        for emotion, emotion_words in EMOTION_LEXICON.items():
            for ew in emotion_words:
                if ew in text_lower:
                    emotion_scores[emotion] += 1
        
        # Normalize to 0-1
        max_score = max(emotion_scores.values()) if emotion_scores else 1
        if max_score > 0:
            emotion_scores = {k: v / max_score for k, v in emotion_scores.items()}
        
        return dict(emotion_scores)
    
    def calculate_intensity(self, emotions: dict[str, float]) -> float:
        """Calculate overall emotional intensity."""
        if not emotions:
            return 0.0
        
        # Intensity is the max emotion intensity
        return max(emotions.values()) if emotions else 0.0
    
    def add_emotional_weight(self, ku_id: str, text: str | None = None, 
                            manual_emotions: dict[str, float] | None = None) -> EmotionalWeight:
        """Add emotional weight to a KU."""
        if manual_emotions:
            emotions = manual_emotions
        elif text:
            emotions = self.detect_emotions(text)
        else:
            emotions = {}
        
        sentiment, sentiment_score = self.detect_sentiment(text) if text else ('neutral', 0.0)
        intensity = self.calculate_intensity(emotions)
        dominant_emotion = max(emotions, key=emotions.get) if emotions else 'neutral'
        
        emotional_weight = EmotionalWeight(
            ku_id=ku_id,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            emotions=emotions,
            dominant_emotion=dominant_emotion,
            intensity=intensity
        )
        
        self._conn.execute(
            """INSERT OR REPLACE INTO emotional_weights 
               (ku_id, sentiment, sentiment_score, emotions, dominant_emotion, intensity, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ku_id, sentiment, sentiment_score, json.dumps(emotions), 
             dominant_emotion, intensity, emotional_weight.created_at, emotional_weight.updated_at)
        )
        self._conn.commit()
        
        return emotional_weight
    
    def get_emotional_weight(self, ku_id: str) -> EmotionalWeight | None:
        """Get emotional weight for a KU."""
        row = self._conn.execute(
            "SELECT ku_id, sentiment, sentiment_score, emotions, dominant_emotion, intensity, created_at, updated_at "
            "FROM emotional_weights WHERE ku_id = ?",
            (ku_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return EmotionalWeight(
            ku_id=row[0],
            sentiment=row[1],
            sentiment_score=row[2],
            emotions=json.loads(row[3]),
            dominant_emotion=row[4],
            intensity=row[5],
            created_at=row[6],
            updated_at=row[7]
        )
    
    def update_emotional_weight(self, ku_id: str, decay_rate: float = 0.01) -> EmotionalWeight | None:
        """Update emotional weight with decay."""
        emotional_weight = self.get_emotional_weight(ku_id)
        if not emotional_weight:
            return None
        
        # Apply decay to emotions
        new_emotions = {k: max(0, v * (1 - decay_rate)) for k, v in emotional_weight.emotions.items()}
        new_intensity = self.calculate_intensity(new_emotions)
        
        emotional_weight.emotions = new_emotions
        emotional_weight.intensity = new_intensity
        emotional_weight.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._conn.execute(
            """UPDATE emotional_weights 
               SET emotions = ?, intensity = ?, updated_at = ?
               WHERE ku_id = ?""",
            (json.dumps(new_emotions), new_intensity, emotional_weight.updated_at, ku_id)
        )
        self._conn.commit()
        
        return emotional_weight
    
    def get_emotion_timeline(self, user_id: str, days: int = 30) -> list[dict]:
        """Get emotion timeline for a user."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        rows = self._conn.execute(
            """SELECT emotion, intensity, timestamp, context 
               FROM emotion_events 
               WHERE user_id = ? AND timestamp >= ?
               ORDER BY timestamp""",
            (user_id, cutoff)
        ).fetchall()
        
        timeline = []
        for row in rows:
            timeline.append({
                'emotion': row[0],
                'intensity': row[1],
                'timestamp': row[2],
                'context': row[3]
            })
        
        return timeline
    
    def get_dominant_emotions(self, scope: str | None = None, days: int = 30) -> dict[str, float]:
        """Get dominant emotions in a period."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        query = """SELECT emotions FROM emotional_weights WHERE updated_at >= ?"""
        params = [cutoff]
        
        if scope:
            query += " AND ku_id LIKE ?"
            params.append(f"%{scope}%")
        
        rows = self._conn.execute(query, params).fetchall()
        
        emotion_totals = defaultdict(float)
        emotion_counts = defaultdict(int)
        
        for row in rows:
            emotions = json.loads(row[0])
            for emotion, intensity in emotions.items():
                emotion_totals[emotion] += intensity
                emotion_counts[emotion] += 1
        
        # Average
        dominant = {}
        for emotion in emotion_totals:
            dominant[emotion] = emotion_totals[emotion] / emotion_counts[emotion] if emotion_counts[emotion] > 0 else 0
        
        return dominant
    
    def find_emotional_peaks(self, threshold: float = 0.8, days: int = 30) -> list[dict]:
        """Find high-intensity emotional moments."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        rows = self._conn.execute(
            """SELECT ku_id, intensity, dominant_emotion, updated_at 
               FROM emotional_weights 
               WHERE intensity >= ? AND updated_at >= ?
               ORDER BY intensity DESC""",
            (threshold, cutoff)
        ).fetchall()
        
        peaks = []
        for row in rows:
            peaks.append({
                'ku_id': row[0],
                'intensity': row[1],
                'dominant_emotion': row[2],
                'timestamp': row[3]
            })
        
        return peaks
    
    def track_emotion(self, user_id: str, emotion: str, intensity: float, context: str | None = None):
        """Track an emotion event."""
        self._conn.execute(
            """INSERT INTO emotion_events (user_id, emotion, intensity, context, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, emotion, intensity, context, datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()
    
    def retrieve_by_emotion(self, emotion_type: str, top_k: int = 10) -> list[dict]:
        """Retrieve KUs by emotion type."""
        rows = self._conn.execute(
            """SELECT ku_id, dominant_emotion, intensity, sentiment_score
               FROM emotional_weights 
               WHERE dominant_emotion = ?
               ORDER BY intensity DESC
               LIMIT ?""",
            (emotion_type, top_k)
        ).fetchall()
        
        results = []
        for row in rows:
            results.append({
                'ku_id': row[0],
                'dominant_emotion': row[1],
                'intensity': row[2],
                'sentiment_score': row[3]
            })
        
        return results
    
    def retrieve_by_sentiment(self, sentiment: str, top_k: int = 10) -> list[dict]:
        """Retrieve KUs by sentiment."""
        rows = self._conn.execute(
            """SELECT ku_id, sentiment, sentiment_score, intensity
               FROM emotional_weights 
               WHERE sentiment = ?
               ORDER BY sentiment_score DESC
               LIMIT ?""",
            (sentiment, top_k)
        ).fetchall()
        
        results = []
        for row in rows:
            results.append({
                'ku_id': row[0],
                'sentiment': row[1],
                'sentiment_score': row[2],
                'intensity': row[3]
            })
        
        return results
    
    def retrieve_by_intensity(self, min_intensity: float, top_k: int = 10) -> list[dict]:
        """Retrieve KUs by emotional intensity."""
        rows = self._conn.execute(
            """SELECT ku_id, dominant_emotion, intensity, sentiment
               FROM emotional_weights 
               WHERE intensity >= ?
               ORDER BY intensity DESC
               LIMIT ?""",
            (min_intensity, top_k)
        ).fetchall()
        
        results = []
        for row in rows:
            results.append({
                'ku_id': row[0],
                'dominant_emotion': row[1],
                'intensity': row[2],
                'sentiment': row[3]
            })
        
        return results
    
    def close(self):
        """Close database connection."""
        self._conn.close()