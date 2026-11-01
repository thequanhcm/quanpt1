"""V16 tests — Emotional Memory & Sentiment Analysis (18 tests)."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from quan_ai_brain.memory.emotional_memory import EmotionalMemory


@pytest.fixture
def emotional_db():
    """Create temporary emotional memory database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v16_emotional.db"


class TestEmotionDetection:
    """Tests for emotion detection."""
    
    def test_detect_positive_sentiment(self, emotional_db):
        """Detect positive sentiment."""
        emo = EmotionalMemory(str(emotional_db))
        sentiment, score = emo.detect_sentiment("I am very happy and excited today")
        assert sentiment == 'positive'
        assert score > 0
        emo.close()
    
    def test_detect_negative_sentiment(self, emotional_db):
        """Detect negative sentiment."""
        emo = EmotionalMemory(str(emotional_db))
        sentiment, score = emo.detect_sentiment("This is terrible and awful")
        assert sentiment == 'negative'
        assert score < 0
        emo.close()
    
    def test_detect_neutral_sentiment(self, emotional_db):
        """Detect neutral sentiment."""
        emo = EmotionalMemory(str(emotional_db))
        sentiment, score = emo.detect_sentiment("The meeting is at 3pm")
        assert sentiment == 'neutral'
        emo.close()
    
    def test_detect_emotions(self, emotional_db):
        """Detect multiple emotions."""
        emo = EmotionalMemory(str(emotional_db))
        emotions = emo.detect_emotions("I am happy and excited about the news")
        assert 'joy' in emotions or 'anticipation' in emotions
        assert emotions.get('joy', 0) > 0 or emotions.get('anticipation', 0) > 0
        emo.close()
    
    def test_calculate_intensity(self, emotional_db):
        """Calculate emotional intensity."""
        emo = EmotionalMemory(str(emotional_db))
        emotions = {'joy': 0.8, 'surprise': 0.5}
        intensity = emo.calculate_intensity(emotions)
        assert intensity == 0.8
        emo.close()
    
    def test_empty_text_sentiment(self, emotional_db):
        """Empty text returns neutral."""
        emo = EmotionalMemory(str(emotional_db))
        sentiment, score = emo.detect_sentiment("")
        assert sentiment == 'neutral'
        assert score == 0.0
        emo.close()


class TestEmotionalStorage:
    """Tests for emotional weight storage."""
    
    def test_add_emotional_weight(self, emotional_db):
        """Add emotional weight to KU."""
        emo = EmotionalMemory(str(emotional_db))
        weight = emo.add_emotional_weight("ku1", "I am very happy!")
        
        assert weight.ku_id == "ku1"
        assert weight.sentiment == 'positive'
        assert weight.intensity > 0
        assert weight.dominant_emotion in ['joy', 'anticipation']
        emo.close()
    
    def test_get_emotional_weight(self, emotional_db):
        """Get emotional weight."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku2", "This is terrible")
        
        weight = emo.get_emotional_weight("ku2")
        assert weight is not None
        assert weight.sentiment == 'negative'
        emo.close()
    
    def test_get_nonexistent_weight(self, emotional_db):
        """Get nonexistent emotional weight returns None."""
        emo = EmotionalMemory(str(emotional_db))
        weight = emo.get_emotional_weight("nonexistent")
        assert weight is None
        emo.close()
    
    def test_update_emotional_weight_decay(self, emotional_db):
        """Update emotional weight with decay."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku3", "I am excited and happy")
        
        weight_before = emo.get_emotional_weight("ku3")
        updated = emo.update_emotional_weight("ku3", decay_rate=0.5)
        
        assert updated is not None
        assert updated.intensity <= weight_before.intensity
        emo.close()


class TestEmotionPatterns:
    """Tests for emotion pattern analysis."""
    
    def test_track_emotion(self, emotional_db):
        """Track emotion event."""
        emo = EmotionalMemory(str(emotional_db))
        emo.track_emotion("user1", "joy", 0.8, "Got promotion")
        
        timeline = emo.get_emotion_timeline("user1", days=30)
        assert len(timeline) == 1
        assert timeline[0]['emotion'] == 'joy'
        assert timeline[0]['intensity'] == 0.8
        emo.close()
    
    def test_get_emotion_timeline(self, emotional_db):
        """Get emotion timeline."""
        emo = EmotionalMemory(str(emotional_db))
        emo.track_emotion("user2", "joy", 0.7, "Event 1")
        emo.track_emotion("user2", "sadness", 0.6, "Event 2")
        emo.track_emotion("user2", "anger", 0.5, "Event 3")
        
        timeline = emo.get_emotion_timeline("user2", days=30)
        assert len(timeline) == 3
        emo.close()
    
    def test_get_dominant_emotions(self, emotional_db):
        """Get dominant emotions."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku4", "I am very happy and joyful")
        emo.add_emotional_weight("ku5", "I am excited and anticipating")
        
        dominant = emo.get_dominant_emotions(days=30)
        assert len(dominant) > 0
        assert 'joy' in dominant or 'anticipation' in dominant
        emo.close()
    
    def test_find_emotional_peaks(self, emotional_db):
        """Find emotional peaks."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku6", "Extremely happy and excited!")  # High intensity
        emo.add_emotional_weight("ku7", "Okay, neutral")  # Low intensity
        
        peaks = emo.find_emotional_peaks(threshold=0.5, days=30)
        assert len(peaks) >= 1
        assert peaks[0]['intensity'] >= 0.5
        emo.close()


class TestEmotionRetrieval:
    """Tests for emotion-based retrieval."""
    
    def test_retrieve_by_emotion(self, emotional_db):
        """Retrieve by emotion type."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku8", "I am so happy and joyful")
        emo.add_emotional_weight("ku9", "I am sad and depressed")
        
        joy_results = emo.retrieve_by_emotion("joy", top_k=5)
        sadness_results = emo.retrieve_by_emotion("sadness", top_k=5)
        
        assert len(joy_results) >= 1
        assert len(sadness_results) >= 1
        assert joy_results[0]['ku_id'] == "ku8"
        emo.close()
    
    def test_retrieve_by_sentiment(self, emotional_db):
        """Retrieve by sentiment."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku10", "This is great and wonderful")
        emo.add_emotional_weight("ku11", "This is terrible and awful")
        
        positive = emo.retrieve_by_sentiment("positive", top_k=5)
        negative = emo.retrieve_by_sentiment("negative", top_k=5)
        
        assert len(positive) >= 1
        assert len(negative) >= 1
        assert positive[0]['ku_id'] == "ku10"
        emo.close()
    
    def test_retrieve_by_intensity(self, emotional_db):
        """Retrieve by emotional intensity."""
        emo = EmotionalMemory(str(emotional_db))
        emo.add_emotional_weight("ku12", "Extremely happy!")  # High intensity
        emo.add_emotional_weight("ku13", "Okay, neutral")  # Low intensity
        
        peaks = emo.retrieve_by_intensity(min_intensity=0.5, top_k=5)
        
        assert len(peaks) >= 1
        assert all(p['intensity'] >= 0.5 for p in peaks)
        emo.close()
    
    def test_retrieve_empty_results(self, emotional_db):
        """Retrieve with no matches returns empty list."""
        emo = EmotionalMemory(str(emotional_db))
        
        results = emo.retrieve_by_emotion("joy", top_k=5)
        assert results == []
        emo.close()


class TestSentimentAnalyzer:
    """Tests for sentiment analyzer edge cases."""
    
    def test_mixed_sentiment(self, emotional_db):
        """Mixed sentiment text."""
        emo = EmotionalMemory(str(emotional_db))
        sentiment, score = emo.detect_sentiment("Good but also bad")
        # Should be close to neutral
        assert abs(score) < 0.5
        emo.close()
    
    def test_multiple_emotions(self, emotional_db):
        """Text with multiple emotions."""
        emo = EmotionalMemory(str(emotional_db))
        emotions = emo.detect_emotions("I am happy and surprised")
        assert len(emotions) >= 1
        emo.close()
    
    def test_case_insensitive_detection(self, emotional_db):
        """Emotion detection is case insensitive."""
        emo = EmotionalMemory(str(emotional_db))
        emotions_upper = emo.detect_emotions("I AM HAPPY")
        emotions_lower = emo.detect_emotions("i am happy")
        
        assert emotions_upper == emotions_lower
        emo.close()