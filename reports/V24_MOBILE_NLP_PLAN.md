# V24 - MOBILE APP & NATURAL LANGUAGE INTERFACE
**Sprint Plan**  
**Version:** V24.0  
**Date:** 2024-10-28  
**Duration:** 7-10 ngày

---

## Executive Summary

V24 mở rộng QUAN AI BRAIN sang **mobile platform** và **natural language interface**:

1. **Mobile App (iOS/Android)** - React Native app với đầy đủ tính năng
2. **Natural Language Query** - NLP-powered query interface
3. **Voice Interface** - Speech-to-text + text-to-speech
4. **Offline Mode** - Local caching và sync
5. **Push Notifications** - Real-time alerts

### Goals
- Mobile app với 90%+ API coverage
- Natural language query với >85% accuracy
- Voice interface hỗ trợ tiếng Việt + English
- Offline mode với conflict resolution
- Push notifications với custom rules

---

## Module Breakdown

### Module 1: Mobile App Core (V24.1)
**Priority:** High  
**Lines:** ~8,000 (React Native)  
**Tests:** 40 tests

#### Features
1. **Authentication & Authorization**
   - Login/Logout
   - OAuth 2.0 flow
   - MFA support
   - Session management

2. **Knowledge Base Browser**
   - List/search knowledge units
   - Filter by type, scope, status
   - Detail view with metadata
   - Favorites/bookmarks

3. **Real-time Updates**
   - WebSocket connection
   - Live search results
   - Push notifications
   - Sync status indicator

4. **Offline Mode**
   - Local SQLite database
   - Queue operations offline
   - Auto-sync when online
   - Conflict resolution UI

#### Tech Stack
- **Framework:** React Native 0.72+
- **State Management:** Redux Toolkit
- **Navigation:** React Navigation 6.x
- **Networking:** Axios + WebSocket
- **Local DB:** WatermelonDB (SQLite)
- **Authentication:** React Native OAuth

#### Component Structure
```
src/
├── components/
│   ├── KnowledgeUnitCard.tsx
│   ├── SearchBar.tsx
│   ├── FilterPanel.tsx
│   ├── DetailView.tsx
│   └── SyncStatus.tsx
├── screens/
│   ├── HomeScreen.tsx
│   ├── SearchScreen.tsx
│   ├── DetailScreen.tsx
│   ├── SettingsScreen.tsx
│   └── OfflineScreen.tsx
├── services/
│   ├── api.ts
│   ├── websocket.ts
│   ├── sync.ts
│   └── auth.ts
├── store/
│   ├── slices/
│   │   ├── knowledgeSlice.ts
│   │   ├── searchSlice.ts
│   │   └── syncSlice.ts
│   └── index.ts
└── utils/
    ├── validators.ts
    └── formatters.ts
```

#### API Integration
```typescript
// services/api.ts
class APIService {
  async searchKnowledge(query: string, filters: Filters): Promise<KnowledgeUnit[]>
  async getKnowledgeUnit(id: string): Promise<KnowledgeUnit>
  async createKnowledgeUnit(data: CreateData): Promise<KnowledgeUnit>
  async updateKnowledgeUnit(id: string, data: UpdateData): Promise<KnowledgeUnit>
  async deleteKnowledgeUnit(id: string): Promise<void>
  async syncOfflineChanges(): Promise<SyncResult>
}
```

#### Test Cases
- Test authentication flow
- Test search functionality
- Test offline mode
- Test sync conflict resolution
- Test push notifications
- Test navigation
- Test data persistence

---

### Module 2: Natural Language Query (V24.2)
**Priority:** High  
**Lines:** ~5,000  
**Tests:** 35 tests

#### Features
1. **NLP Pipeline**
   - Tokenization
   - Part-of-speech tagging
   - Named entity recognition
   - Dependency parsing

2. **Query Parser**
   - Intent classification
   - Entity extraction
   - Query structure generation
   - Query optimization

3. **Intent Recognition**
   - SEARCH: Find knowledge units
   - CREATE: Add new knowledge
   - UPDATE: Modify existing
   - ANALYZE: Run analysis
   - SUMMARIZE: Generate summary

4. **Query Translation**
   - NL → SQL/GraphQL
   - NL → API calls
   - NL → Filter expressions
   - Ambiguity resolution

#### Tech Stack
- **NLP Library:** spaCy / Stanza
- **Intent Classification:** Transformers (BERT)
- **Entity Recognition:** Custom model
- **Query Builder:** SQLAlchemy

#### NLP Pipeline
```python
class NLPQueryProcessor:
    def __init__(self):
        self.nlp = spacy.load("vi_core_news_sm")  # Vietnamese
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.query_builder = QueryBuilder()
    
    def process(self, query: str) -> QueryResult:
        # 1. Tokenization & POS tagging
        doc = self.nlp(query)
        
        # 2. Intent classification
        intent = self.intent_classifier.classify(query)
        
        # 3. Entity extraction
        entities = self.entity_extractor.extract(doc)
        
        # 4. Query structure generation
        query_structure = self._build_query_structure(intent, entities)
        
        # 5. Execute query
        results = self.query_builder.execute(query_structure)
        
        return QueryResult(results, intent, entities)
```

#### Intent Examples
```
User: "Tìm các kinh nghiệm triển khai production"
→ Intent: SEARCH
→ Entities: {type: "LESSON_LEARNED", scope: "production"}
→ Query: SELECT * FROM knowledge_units WHERE type='LESSON_LEARNED' AND scope='production'

User: "Nhớ rằng database cần backup hàng ngày"
→ Intent: CREATE
→ Entities: {statement: "database needs daily backup", type: "BEST_PRACTICE"}
→ Action: Create knowledge unit

User: "Show me all errors from last week"
→ Intent: SEARCH
→ Entities: {type: "ERROR", time_range: "last_week"}
→ Query: SELECT * FROM knowledge_units WHERE type='ERROR' AND created_at > NOW() - INTERVAL '7 days'
```

#### Test Cases
- Test intent classification accuracy
- Test entity extraction
- Test query translation
- Test ambiguity handling
- Test multilingual support (VI/EN)
- Test complex queries
- Test error handling

---

### Module 3: Voice Interface (V24.3)
**Priority:** Medium  
**Lines:** ~3,500  
**Tests:** 25 tests

#### Features
1. **Speech-to-Text (STT)**
   - Real-time transcription
   - Vietnamese + English support
   - Noise cancellation
   - Wake word detection

2. **Text-to-Speech (TTS)**
   - Natural voice synthesis
   - Multiple voices
   - Speed/pitch control
   - Offline TTS

3. **Voice Commands**
   - "Hey Quan, tìm..."
   - "Nhớ giúp tôi..."
   - "Show me..."
   - Custom commands

4. **Audio Feedback**
   - Confirmation sounds
   - Error alerts
   - Progress indicators

#### Tech Stack
- **STT:** Google Cloud Speech-to-Text / Vosk (offline)
- **TTS:** Google Cloud TTS / Coqui TTS (offline)
- **Audio Processing:** PyAudio, librosa
- **Wake Word:** Porcupine / Snowboy

#### Voice Flow
```python
class VoiceInterface:
    def __init__(self):
        self.stt = SpeechToTextEngine()
        self.tts = TextToSpeechEngine()
        self.nlp = NLPQueryProcessor()
        self.wake_word = WakeWordDetector()
    
    async def run(self):
        # 1. Listen for wake word
        while not self.wake_word.detected():
            await asyncio.sleep(0.1)
        
        # 2. Capture speech
        audio = await self.stt.capture()
        
        # 3. Transcribe
        text = await self.stt.transcribe(audio)
        
        # 4. Process NLP
        result = self.nlp.process(text)
        
        # 5. Generate response
        response = self._generate_response(result)
        
        # 6. Speak response
        await self.tts.speak(response)
```

#### Test Cases
- Test STT accuracy (Vietnamese/English)
- Test TTS quality
- Test wake word detection
- Test voice command recognition
- Test audio feedback
- Test offline mode
- Test noise handling

---

### Module 4: Offline Sync Engine (V24.4)
**Priority:** High  
**Lines:** ~4,000  
**Tests:** 30 tests

#### Features
1. **Local Database**
   - SQLite with WatermelonDB
   - Schema sync with server
   - Indexes for performance
   - Encryption at rest

2. **Change Tracking**
   - Track local changes
   - Track remote changes
   - Change log
   - Version history

3. **Sync Strategy**
   - Incremental sync
   - Batch operations
   - Conflict detection
   - Conflict resolution (last-write-wins, manual)

4. **Sync UI**
   - Sync status indicator
   - Pending changes list
   - Conflict resolution dialog
   - Manual sync trigger

#### Tech Stack
- **Local DB:** WatermelonDB (React Native) / SQLite (Python)
- **Sync Protocol:** Custom JSON-based
- **Encryption:** SQLCipher
- **Queue:** Redis (server-side)

#### Sync Algorithm
```python
class OfflineSyncEngine:
    def __init__(self, local_db, remote_api):
        self.local_db = local_db
        self.remote_api = remote_api
        self.change_queue = ChangeQueue()
    
    async def sync(self):
        # 1. Get last sync timestamp
        last_sync = self.local_db.get_last_sync_time()
        
        # 2. Fetch remote changes
        remote_changes = await self.remote_api.get_changes(since=last_sync)
        
        # 3. Get local pending changes
        local_changes = self.change_queue.get_pending()
        
        # 4. Detect conflicts
        conflicts = self._detect_conflicts(remote_changes, local_changes)
        
        if conflicts:
            # 5a. Resolve conflicts
            resolved = await self._resolve_conflicts(conflicts)
        else:
            resolved = local_changes
        
        # 6. Apply remote changes
        await self.local_db.apply_changes(remote_changes)
        
        # 7. Upload local changes
        await self.remote_api.upload_changes(resolved)
        
        # 8. Update sync timestamp
        self.local_db.update_last_sync_time()
        
        return SyncResult(len(remote_changes), len(resolved), len(conflicts))
```

#### Test Cases
- Test offline CRUD operations
- Test sync on reconnect
- Test conflict detection
- Test conflict resolution
- Test sync performance
- Test data integrity
- Test encryption

---

### Module 5: Push Notifications (V24.5)
**Priority:** Medium  
**Lines:** ~2,500  
**Tests:** 20 tests

#### Features
1. **Notification Service**
   - Firebase Cloud Messaging (FCM)
   - Apple Push Notification (APNs)
   - Custom notification rules
   - Notification grouping

2. **Notification Types**
   - New knowledge available
   - Review reminders
   - Sync completed
   - System alerts
   - Custom alerts

3. **Notification Rules**
   - Trigger conditions
   - Frequency limits
   - Quiet hours
   - Priority levels

4. **Notification UI**
   - Notification center
   - Action buttons
   - Deep linking
   - Badge count

#### Tech Stack
- **Mobile:** FCM (Android), APNs (iOS)
- **Server:** Firebase Admin SDK
- **Queue:** Redis + Celery
- **Storage:** PostgreSQL (notification history)

#### Notification Flow
```python
class NotificationService:
    def __init__(self):
        self.fcm = FirebaseMessaging()
        self.apns = ApplePushNotification()
        self.rule_engine = NotificationRuleEngine()
    
    async def send_notification(self, user_id: str, notification: Notification):
        # 1. Check notification rules
        if not self.rule_engine.should_send(user_id, notification):
            return
        
        # 2. Get user devices
        devices = await self.get_user_devices(user_id)
        
        # 3. Send to each device
        for device in devices:
            if device.platform == 'android':
                await self.fcm.send(device.token, notification)
            elif device.platform == 'ios':
                await self.apns.send(device.token, notification)
        
        # 4. Log notification
        await self.log_notification(user_id, notification)
```

#### Test Cases
- Test notification delivery
- Test notification rules
- Test notification grouping
- Test deep linking
- Test badge updates
- Test quiet hours
- Test notification actions

---

## Implementation Timeline

### Day 1-2: Module 1 - Mobile App Core
- Morning: React Native setup, project structure
- Afternoon: Authentication screens
- Evening: Knowledge base browser
- Day 2: Search, filters, detail views
- Tests: 40 tests

### Day 3-4: Module 2 - Natural Language Query
- Morning: NLP pipeline setup (spaCy)
- Afternoon: Intent classification
- Evening: Entity extraction
- Day 4: Query translation, testing
- Tests: 35 tests

### Day 5: Module 3 - Voice Interface
- Morning: STT integration
- Afternoon: TTS integration
- Evening: Voice commands
- Tests: 25 tests

### Day 6: Module 4 - Offline Sync
- Morning: Local DB setup
- Afternoon: Change tracking
- Evening: Sync algorithm
- Tests: 30 tests

### Day 7: Module 5 - Push Notifications
- Morning: FCM/APNs setup
- Afternoon: Notification rules
- Evening: Notification UI
- Tests: 20 tests

### Day 8-10: Integration & Testing
- Integration testing
- Bug fixes
- Performance optimization
- Documentation
- App store preparation

---

## Dependencies

### External Services
- **Firebase** - Push notifications, analytics
- **Google Cloud** - STT, TTS (optional)
- **Apple Developer** - iOS app signing
- **Google Play Console** - Android app publishing

### Libraries
```json
{
  "react-native": "0.72.x",
  "react-native-reanimated": "3.x",
  "@react-navigation/native": "6.x",
  "@reduxjs/toolkit": "1.9.x",
  "react-redux": "8.x",
  "watermelondb": "0.27.x",
  "axios": "1.5.x",
  "react-native-voice": "3.x",
  "react-native-fcm": "19.x"
}
```

### Infrastructure
- Firebase project
- Apple Developer account
- Google Play Console account
- Backend API with WebSocket support

---

## Success Criteria

### Mobile App
- [ ] iOS app builds and runs
- [ ] Android app builds and runs
- [ ] 90%+ API coverage
- [ ] Offline mode working
- [ ] Push notifications working
- [ ] App store ready

### NLP
- [ ] Intent classification >85% accuracy
- [ ] Entity extraction >80% accuracy
- [ ] Vietnamese + English support
- [ ] Complex query handling

### Voice
- [ ] STT accuracy >90% (clear audio)
- [ ] TTS sounds natural
- [ ] Wake word detection working
- [ ] Voice commands responsive

### Offline
- [ ] Full offline functionality
- [ ] Sync conflict resolution
- [ ] Data integrity maintained
- [ ] <5% sync failures

---

## Risk Assessment

### High Risk
1. **App Store Approval**
   - Risk: Rejection due to policy violations
   - Mitigation: Review guidelines early
   - Contingency: Adjust features

2. **NLP Accuracy**
   - Risk: Low accuracy for Vietnamese
   - Mitigation: Use pre-trained models, fine-tune
   - Contingency: Fallback to keyword search

### Medium Risk
1. **Offline Sync Complexity**
   - Risk: Data corruption from conflicts
   - Mitigation: Extensive testing, user confirmation
   - Contingency: Last-write-wins default

2. **Voice Recognition**
   - Risk: Poor accuracy in noisy environments
   - Mitigation: Noise cancellation, multiple models
   - Contingency: Text input fallback

---

## Deliverables

### Mobile App
- [ ] React Native project
- [ ] iOS app (IPA file)
- [ ] Android app (APK/AAB file)
- [ ] App store listings
- [ ] User guide

### NLP/Voice
- [ ] NLP pipeline
- [ ] Intent classifier
- [ ] Entity extractor
- [ ] STT integration
- [ ] TTS integration

### Backend
- [ ] Push notification service
- [ ] Offline sync API
- [ ] Notification rules engine
- [ ] Sync conflict resolution

### Tests
- [ ] 150+ unit tests
- [ ] Integration tests
- [ ] E2E tests (Detox)
- [ ] Performance tests

---

## Approval Required

### From Stakeholders
- [ ] Mobile app features approved
- [ ] NLP accuracy targets approved
- [ ] Voice interface scope approved
- [ ] Budget for services (Firebase, Google Cloud)

### From Technical Team
- [ ] Architecture review
- [ ] Security review
- [ ] Performance review
- [ ] App store compliance check

---

## Next Steps After Approval

1. **Setup** (Day 0)
   - Create Firebase project
   - Setup React Native environment
   - Create app store accounts

2. **Development** (Days 1-7)
   - Daily standups
   - Code reviews
   - Continuous integration

3. **Testing** (Days 8-10)
   - QA testing
   - User acceptance testing
   - Performance testing

4. **Launch** (Week 3)
   - Submit to App Store
   - Submit to Google Play
   - Monitor reviews
   - Iterate based on feedback

---

**Document Version:** V24.0  
**Created:** 2024-10-28  
**Status:** Draft - Awaiting V23 Completion & Approval  
**Next Review:** After V23 completion