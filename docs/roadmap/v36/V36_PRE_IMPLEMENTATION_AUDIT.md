# V36 PRE-IMPLEMENTATION AUDIT
**Date:** 2026-10-28  
**Audit Scope:** Natural Voice & Cognitive Conversation Engine  
**Baseline:** V35 Enterprise Reliability (pre-implementation)  
**Auditor:** Antigravity Technical Team

---

## 1. EXECUTIVE SUMMARY

### 1.1 Current State

QUAN AI BRAIN có **nền tảng voice cơ bản** nhưng **chưa có implementation thật**:

| Component | Status | Confidence |
|-----------|--------|------------|
| Voice State Machine | ✅ VERIFIED_WORKING | High |
| Voice Pipeline Logic | 🟡 PARTIALLY_WORKING | Medium |
| Mock ASR/TTS | ✅ SIMULATED | High |
| Mouth Sync Engine | ✅ VERIFIED_WORKING | High |
| TTS Configuration | ✅ VERIFIED_WORKING | High |
| **Real Microphone Input** | ❌ NOT_IMPLEMENTED | N/A |
| **Real TTS (Azure/Google)** | ❌ NOT_IMPLEMENTED | N/A |
| **Real ASR (Azure/Google)** | ❌ NOT_IMPLEMENTED | N/A |
| **Barge-in/Interrupt** | ❌ NOT_IMPLEMENTED | N/A |
| **Streaming Audio** | ❌ NOT_IMPLEMENTED | N/A |
| **VAD (Voice Activity Detection)** | ❌ NOT_IMPLEMENTED | N/A |
| **Echo Cancellation** | ❌ NOT_IMPLEMENTED | N/A |
| **Conversation State Engine** | 🟡 PARTIALLY_WORKING | Medium |
| **Cognitive Reasoning Layer** | 🟡 PARTIALLY_WORKING | Medium |

### 1.2 Key Findings

**✅ Strengths:**
1. **Voice State Machine** - Complete state transitions (DISABLED → STANDBY → LISTENING → TRANSCRIBING → THINKING → SPEAKING → INTERRUPTED)
2. **Voice Pipeline** - End-to-end logic with sanitization, context, intent routing
3. **Mouth Sync Engine** - Avatar lip-sync with syllable timing
4. **TTS Config** - Vietnamese voice configuration structure
5. **Mock ASR/TTS** - Test infrastructure ready
6. **Conversation Turn** - Data model for multi-turn context
7. **Text Sanitization** - Removes code/JSON/Markdown for spoken output

**🟡 Gaps:**
1. **No real audio capture** - MockASR only replays scripted strings
2. **No real TTS** - MockTTS doesn't produce audio
3. **No VAD** - Cannot detect voice activity or silence
4. **No streaming** - No real-time audio processing
5. **No barge-in** - Cannot interrupt TTS when user speaks
6. **No echo cancellation** - Cannot distinguish user voice from TTS output
7. **No conversation state persistence** - Context not stored across sessions
8. **No tool integration** - Voice cannot trigger actions

**🔴 Critical Issues:**
1. **No microphone access** - System cannot hear user
2. **No speaker output** - System cannot speak
3. **No ASR provider** - Cannot convert speech to text
4. **No TTS provider** - Cannot convert text to speech
5. **No real-time processing** - Cannot handle streaming audio
6. **No interrupt handling** - Cannot stop speaking when interrupted

### 1.3 Overall Assessment

**V36 Readiness Score: 15/100**

- Voice State Machine: 100/100 ✅
- Voice Pipeline Logic: 60/100 🟡
- Mock Infrastructure: 100/100 ✅
- Real Audio Capture: 0/100 ❌
- Real TTS: 0/100 ❌
- Real ASR: 0/100 ❌
- Barge-in: 0/100 ❌
- Streaming: 0/100 ❌
- VAD: 0/100 ❌
- Echo Cancellation: 0/100 ❌
- Conversation State: 40/100 🟡
- Tool Integration: 20/100 🟡

---

## 2. EXISTING COMPONENTS ANALYSIS

### 2.1 Voice Module Files

| File | Lines | Status | Can Reuse |
|------|-------|--------|-----------|
| `voice/state_machine.py` | 56 | ✅ Complete | ✅ Yes |
| `voice/voice_interface.py` | 311 | 🟡 Mock only | 🟡 Interfaces only |
| `voice/voice_pipeline.py` | 299 | 🟡 Logic only | 🟡 Logic, not I/O |
| `voice/tts_config.py` | 384 | ✅ Complete | ✅ Yes |
| `voice/mouth_sync.py` | 287 | ✅ Complete | ✅ Yes |
| `voice/wake_word_config.py` | 156 | 🟡 Config only | 🟡 Config, not detection |

### 2.2 Test Files

| File | Status | Notes |
|------|--------|-------|
| `tests/test_voice_first_pipeline.py` | ✅ Exists | Tests mock pipeline |
| `tests/test_voice_api_endpoints.py` | ✅ Exists | Tests API structure |
| `tests/test_vietnamese_tts.py` | ✅ Exists | Tests TTS config |

### 2.3 Existing Logic

**Voice Pipeline (`voice_pipeline.py`):**
- ✅ ConversationTurn data model
- ✅ VoiceInteractionResult data model
- ✅ `sanitize_for_spoken_vietnamese()` - removes code/JSON/Markdown
- ✅ Intent detection stub
- ✅ Role routing stub
- ✅ Context turn tracking
- ❌ No real ASR call
- ❌ No real TTS call
- ❌ No audio capture

**State Machine (`state_machine.py`):**
- ✅ 9 states defined (DISABLED, STANDBY, WAKE_DETECTED, LISTENING, TRANSCRIBING, THINKING, SPEAKING, INTERRUPTED, ERROR)
- ✅ Valid transitions defined
- ✅ Thread-safe implementation
- ✅ State history tracking
- ❌ No actual state transitions triggered by real events

**Mouth Sync (`mouth_sync.py`):**
- ✅ UtteranceTimeline data model
- ✅ MouthSyncEngine with syllable timing
- ✅ Avatar lip-sync logic
- ✅ Audio energy tracking
- ✅ Interrupt handling (stop audio, snap mouth closed)
- ❌ No real audio playback
- ❌ No real audio analysis

---

## 3. MISSING COMPONENTS

### 3.1 Audio Capture Layer

**Required:**
- Microphone access (PyAudio or similar)
- Audio streaming (chunk-based)
- Sample rate normalization (16kHz, 16-bit, mono)
- VAD (Voice Activity Detection)
- Noise suppression
- Gain control

**Options:**
1. **PyAudio + WebRTC VAD** - Local, free
2. **Azure Speech SDK** - Cloud, high quality
3. **Google Cloud Speech** - Cloud, high quality
4. **Vosk** - Offline, lower quality

### 3.2 ASR Layer

**Required:**
- Speech-to-text conversion
- Streaming support
- Vietnamese language model
- Confidence scores
- Partial results
- Timestamp alignment

**Options:**
1. **Azure Speech-to-Text** - Best Vietnamese, streaming, $0.008/minute
2. **Google Cloud Speech** - Good Vietnamese, streaming, $0.006/minute
3. **Whisper** - Offline, good quality, requires GPU
4. **Vosk** - Offline, lower quality, CPU-only

### 3.3 TTS Layer

**Required:**
- Text-to-speech synthesis
- Streaming audio output
- Vietnamese neural voices
- SSML support
- Prosody control
- Interruptible playback

**Options:**
1. **Azure Neural TTS** - Best Vietnamese (vi-VN-HoaiMyNeural), streaming, $0.016/1000 chars
2. **Google Cloud TTS** - Good Vietnamese, streaming, $0.016/1000 chars
3. **Coqui TTS** - Offline, open-source, requires GPU
4. **eSpeak NG** - Offline, low quality, CPU-only

### 3.4 Barge-in & Echo Cancellation

**Required:**
- Detect user voice while TTS playing
- Cancel TTS playback immediately
- Distinguish user voice from echo
- Acoustic echo cancellation (AEC)

**Options:**
1. **Azure Speech SDK** - Built-in barge-in
2. **Google Cloud Speech** - Built-in barge-in
3. **WebRTC AEC** - Open-source, complex
4. **Custom implementation** - High effort, uncertain quality

### 3.5 Conversation State Engine

**Required:**
- Session management
- Multi-turn context storage
- Reference resolution ("đó", "cái này", "tiếp tục")
- Intent tracking
- Slot filling
- Clarification handling

**Options:**
1. **Extend existing `ConversationTurn`** - Low effort
2. **Rasa NLU** - Full conversation framework
3. **Custom implementation** - Medium effort
4. **Azure Bot Service** - Cloud, full-featured

---

## 4. RECOMMENDATIONS

### 4.1 Option A: Azure Speech Services (Recommended)

**Pros:**
- Best Vietnamese quality
- Built-in streaming
- Built-in barge-in
- Built-in echo cancellation
- Neural voices (HoaiMy)
- Easy integration
- Free tier (5000 min/month)

**Cons:**
- Requires internet
- Requires API key
- Cost after free tier

**Timeline:** 2-3 weeks

### 4.2 Option B: Offline Stack (Privacy)

**Pros:**
- No internet required
- Privacy-focused
- No ongoing cost

**Cons:**
- Lower quality
- Requires GPU for Whisper
- Complex setup
- No built-in barge-in
- No built-in AEC

**Timeline:** 4-6 weeks

### 4.3 Option C: Hybrid (Cloud ASR + Offline TTS)

**Pros:**
- Good recognition quality
- Privacy for output
- Lower cost

**Cons:**
- Still requires internet for ASR
- Complex routing
- Inconsistent quality

**Timeline:** 3-4 weeks

---

## 5. IMPLEMENTATION PLAN (Option A - Azure)

### Phase 1: Audio Capture & VAD (Week 1)

**Deliverables:**
- Microphone capture with PyAudio
- Audio streaming (chunk-based)
- WebRTC VAD integration
- Noise suppression
- Gain control

**Tests:**
- Audio capture tests
- VAD accuracy tests
- Noise suppression tests

### Phase 2: ASR Integration (Week 1-2)

**Deliverables:**
- Azure Speech-to-Text integration
- Streaming ASR
- Partial results
- Confidence scores
- Timestamp alignment
- Vietnamese language model

**Tests:**
- ASR accuracy tests
- Streaming latency tests
- Partial result tests

### Phase 3: TTS Integration (Week 2)

**Deliverables:**
- Azure Neural TTS integration
- Streaming TTS
- vi-VN-HoaiMyNeural voice
- SSML support
- Prosody control
- Audio playback

**Tests:**
- TTS quality tests
- Streaming latency tests
- SSML rendering tests

### Phase 4: Barge-in & Echo Cancellation (Week 3)

**Deliverables:**
- Barge-in detection
- TTS interruption
- Echo cancellation
- User voice isolation

**Tests:**
- Barge-in latency tests
- Echo cancellation tests
- Interrupt handling tests

### Phase 5: Conversation State Engine (Week 3)

**Deliverables:**
- Session management
- Multi-turn context
- Reference resolution
- Intent tracking
- Clarification handling

**Tests:**
- Context retention tests
- Reference resolution tests
- Multi-turn conversation tests

### Phase 6: Integration & Benchmark (Week 4)

**Deliverables:**
- End-to-end integration
- Latency benchmark
- Quality benchmark
- Failure recovery tests

**Tests:**
- End-to-end tests
- Latency benchmark
- Quality benchmark
- Recovery tests

---

## 6. RISK ASSESSMENT

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Azure API limits | MEDIUM | LOW | Monitor usage, implement fallback |
| Network latency | HIGH | MEDIUM | Use local region, implement timeout |
| Vietnamese accuracy | MEDIUM | LOW | Test with real data, tune model |
| Barge-in latency | HIGH | MEDIUM | Optimize VAD, use hardware acceleration |
| Echo cancellation | HIGH | MEDIUM | Use Azure AEC, test in real environment |
| Cost overruns | MEDIUM | LOW | Monitor usage, set budget alerts |
| Privacy concerns | HIGH | LOW | Implement local processing option |
| GPU requirements | MEDIUM | MEDIUM | Use cloud services, optimize model |

---

## 7. CONCLUSION

### 7.1 Recommendation

**Recommended: Option A - Azure Speech Services**

**Rationale:**
- Best Vietnamese quality
- Built-in streaming, barge-in, AEC
- Fastest time to market
- Free tier sufficient for development
- Matches existing `voice_profile: "vi-VN-HoaiMyNeural"`

**Scope:**
- ✅ Audio capture (PyAudio + WebRTC VAD)
- ✅ ASR (Azure Speech-to-Text)
- ✅ TTS (Azure Neural TTS - HoaiMy)
- ✅ Barge-in (Azure built-in)
- ✅ Echo cancellation (Azure built-in)
- ✅ Conversation state engine (custom)
- ✅ Integration with existing pipeline

### 7.2 Next Steps

1. **Confirm scope** - Quanpt1 approves Option A
2. **Get Azure credentials** - Speech Services resource
3. **Phase 1** - Audio capture & VAD
4. **Phase 2** - ASR integration
5. **Phase 3** - TTS integration
6. **Phase 4** - Barge-in & AEC
7. **Phase 5** - Conversation state
8. **Phase 6** - Integration & benchmark
9. **Report** - V36 completion report

---

**Document Status:** DRAFT - Pending Owner Decision  
**Last Updated:** 2026-10-28  
**Decision Required:** Option A, B, or C?