# V16 — EMOTIONAL MEMORY & SENTIMENT ANALYSIS
**Ngày:** 28/10/2026 · Emotional weight, sentiment tracking, mood patterns, emotion-based retrieval

## Deliverables

### Module: `memory/emotional_memory.py` (500 dòng)
**Emotion Detection:**
- `EMOTION_LEXICON`: rule-based emotion lexicon (8 emotions: joy, sadness, anger, fear, surprise, disgust, trust, anticipation)
- `SENTIMENT_WORDS`: positive/negative/neutral word lists
- `detect_sentiment(text)`: sentiment analysis → (sentiment, score -1 to +1)
- `detect_emotions(text)`: emotion classification → {emotion: intensity}
- `calculate_intensity(emotions)`: overall intensity (max emotion intensity)

**Emotional Memory Storage:**
- `EmotionalWeight`: dataclass (ku_id, sentiment, sentiment_score, emotions, dominant_emotion, intensity, timestamps)
- `add_emotional_weight(ku_id, text, manual_emotions)`: attach emotional weight to KU
- `get_emotional_weight(ku_id)`: retrieve emotional weight
- `update_emotional_weight(ku_id, decay_rate)`: apply time decay to emotions

**Emotion Patterns:**
- `EmotionEvent`: dataclass for tracking (user_id, emotion, intensity, context, timestamp)
- `track_emotion(user_id, emotion, intensity, context)`: log emotion event
- `get_emotion_timeline(user_id, days)`: emotion over time
- `get_dominant_emotions(scope, days)`: dominant emotions in period
- `find_emotional_peaks(threshold, days)`: high-intensity moments

**Emotion-Based Retrieval:**
- `retrieve_by_emotion(emotion_type, top_k)`: retrieve by dominant emotion
- `retrieve_by_sentiment(sentiment, top_k)`: retrieve by sentiment
- `retrieve_by_intensity(min_intensity, top_k)`: retrieve by intensity

### Tests: `tests/test_v16_emotional_memory.py` (21 tests)
**Emotion detection (6 tests):**
- Positive/negative/neutral sentiment detection
- Emotion detection (multiple emotions)
- Intensity calculation
- Empty text handling
- **6 passed** ✅

**Emotional storage (4 tests):**
- Add emotional weight
- Get emotional weight
- Get nonexistent weight
- Update with decay
- **4 passed** ✅

**Emotion patterns (4 tests):**
- Track emotion
- Get emotion timeline
- Get dominant emotions
- Find emotional peaks
- **4 passed** ✅

**Emotion retrieval (4 tests):**
- Retrieve by emotion
- Retrieve by sentiment
- Retrieve by intensity
- Empty results
- **4 passed** ✅

**Sentiment analyzer (3 tests):**
- Mixed sentiment
- Multiple emotions
- Case insensitive
- **3 passed** ✅

- **21 passed** ✅

## API Routes (chưa nối server.py)
**Emotional Memory API:**
- POST `/api/memory/emotional/add` → {success: true, ku_id, emotional_weight}
- GET `/api/memory/emotional/{ku_id}` → {emotional_weight}
- PUT `/api/memory/emotional/{ku_id}?decay=0.01` → {success: true, updated_weight}
- GET `/api/memory/emotional/timeline/{user_id}?days=30` → {timeline: [...]}
- GET `/api/memory/emotional/dominant?scope=...&days=30` → {dominant_emotions: {...}}
- GET `/api/memory/emotional/peaks?threshold=0.8&days=30` → {peaks: [...]}

**Emotion-Based Retrieval:**
- GET `/api/memory/retrieve/emotion/{emotion_type}?top_k=10` → {results: [...]}
- GET `/api/memory/retrieve/sentiment/{sentiment}?top_k=10` → {results: [...]}
- GET `/api/memory/retrieve/intensity?min=0.8&top_k=10` → {results: [...]}

## Trung thực
- **IMPLEMENTED**: EmotionalMemory class với đầy đủ features
- **TESTED**: 21/21 tests PASS
- **CHƯA NỐI**: API routes vào server.py
- **LIMITATIONS**:
  - Emotion detection dùng rule-based lexicon (chưa có ML model)
  - Sentiment analysis đơn giản (word count-based)
  - Không có voice tone analysis (chưa có voice input)
  - Emotion propagation chưa implement

## So sánh V11-V12-V13-V14-V15-V16
| Hạng mục | V11 | V12 | V13 | V14 | V15 | V16 |
|---|---|---|---|---|---|---|
| Module | 650 dòng | 450 dòng | 550 dòng | 15KB JS | 1000 dòng | **500 dòng** |
| Tests | 19/23 | 21/21 | 21/21 | 15/15+3sk | 21/22 | **21/21** ✅ |
| Core feature | Temporal | Cross-modal | Quality | UI | Graph+Multi-agent | **Emotion+Sentiment** |
| API | 6 routes | 6 routes | 7 routes | 12 routes | 15 routes | **9 routes** |

## Integration với các sprint trước
- **V11 (Temporal)**: emotion timeline theo thời gian, emotional decay
- **V12 (Cross-Modal)**: emotions trong meetings/documents/text
- **V13 (Quality)**: emotional weight ảnh hưởng quality score (high intensity = high priority)
- **V14 (UI)**: emotion dashboard, sentiment charts, emotion timeline
- **V15 (Graph)**: emotions as node properties, emotion propagation qua edges

## Kế hoạch V17 (dưới đây)