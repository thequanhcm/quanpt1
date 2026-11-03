# QUAN AI BRAIN - FUNCTIONAL SPECIFICATIONS
**Version:** V30.0  
**Date:** 2026-10-28  
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Core Memory System](#core-memory-system)
2. [Cognitive Engine](#cognitive-engine)
3. [Learning & Adaptation](#learning--adaptation)
4. [Analytics & Insights](#analytics--insights)
5. [Mobile & Voice Interface](#mobile--voice-interface)
6. [Enterprise Integration](#enterprise-integration)
7. [Security & Compliance](#security--compliance)
8. [API Reference](#api-reference)

---

## Core Memory System

### 1.1 Deep Memory Store

**Description:** Persistent knowledge base với semantic search, versioning, và relationship tracking.

**Features:**
- ✅ Store knowledge units (text, documents, media)
- ✅ Automatic metadata extraction (confidence, scope, status)
- ✅ Semantic similarity search (vector embeddings)
- ✅ Relationship mapping (knowledge graph)
- ✅ Version history & audit trail
- ✅ Status workflow (PENDING → VERIFIED → ARCHIVED)

**API Endpoints:**
```http
POST   /api/memory/knowledge-units
GET    /api/memory/knowledge-units/{id}
PUT    /api/memory/knowledge-units/{id}
DELETE /api/memory/knowledge-units/{id}
GET    /api/memory/knowledge-units/search?q=...&type=...&status=...
POST   /api/memory/knowledge-units/batch
```

**Example Usage:**
```python
# Create knowledge unit
response = requests.post('http://localhost:8216/api/memory/knowledge-units', json={
    "content": "Python is a programming language",
    "type": "fact",
    "scope": "general",
    "metadata": {
        "source": "user_input",
        "confidence": 0.95
    }
})

# Search knowledge
results = requests.get('http://localhost:8216/api/memory/knowledge-units/search', 
                       params={"q": "programming", "limit": 10})
```

**Data Model:**
```python
@dataclass
class KnowledgeUnit:
    id: str  # UUID
    content: str
    type: str  # fact, concept, procedure, rule, example
    scope: str  # general, domain-specific, personal
    status: str  # PENDING, VERIFIED, ARCHIVED
    confidence: float  # 0.0 - 1.0
    created_at: datetime
    updated_at: datetime
    metadata: dict
    embeddings: List[float]  # 1024-dim vector
```

---

### 1.2 Knowledge Graph

**Description:** Graph-based relationship mapping giữa knowledge units.

**Features:**
- ✅ Automatic relationship detection
- ✅ Manual relationship creation
- ✅ Graph traversal (BFS, DFS)
- ✅ Community detection
- ✅ Path finding
- ✅ Graph visualization data

**API Endpoints:**
```http
POST   /api/memory/graph/relationships
GET    /api/memory/graph/relationships/{id}
GET    /api/memory/graph/neighbors/{unit_id}
GET    /api/memory/graph/paths?from=...&to=...
POST   /api/memory/graph/traverse
GET    /api/memory/graph/visualization
```

**Example:**
```python
# Create relationship
requests.post('http://localhost:8216/api/memory/graph/relationships', json={
    "from_unit": "uuid-1",
    "to_unit": "uuid-2",
    "type": "related_to",
    "strength": 0.8
})

# Get neighbors
neighbors = requests.get('http://localhost:8216/api/memory/graph/neighbors/uuid-1')
```

---

### 1.3 Temporal Memory

**Description:** Time-aware memory với automatic aging, expiration, và recency weighting.

**Features:**
- ✅ Timestamp tracking (created, accessed, updated)
- ✅ Automatic decay scoring
- ✅ Time-based expiration
- ✅ Recency-weighted search
- ✅ Historical trend analysis
- ✅ Time-range queries

**API Endpoints:**
```http
GET    /api/memory/temporal/age-analysis
POST   /api/memory/temporal/expire-old
GET    /api/memory/temporal/trends?metric=...&period=...
PUT    /api/memory/temporal/update-access/{id}
```

**Example:**
```python
# Get recently accessed knowledge
recent = requests.get('http://localhost:8216/api/memory/temporal/recent?hours=24&limit=50')

# Analyze age distribution
analysis = requests.get('http://localhost:8216/api/memory/temporal/age-analysis')
```

---

### 1.4 Emotional Memory

**Description:** Memory với emotional context và sentiment tracking.

**Features:**
- ✅ Sentiment analysis (positive, negative, neutral)
- ✅ Emotional tagging (joy, sadness, anger, fear, surprise)
- ✅ Emotional context preservation
- ✅ Emotion-based search
- ✅ Mood tracking over time
- ✅ Empathy-aware responses

**API Endpoints:**
```http
POST   /api/memory/emotional/tag
GET    /api/memory/emotional/search?emotion=...
GET    /api/memory/emotional/trends
POST   /api/memory/emotional/analyze/{unit_id}
```

---

### 1.5 Counterfactual Memory

**Description:** Store "what-if" scenarios và alternative outcomes.

**Features:**
- ✅ Counterfactual scenario storage
- ✅ Alternative history tracking
- ✅ Impact assessment
- ✅ Learning from alternatives
- ✅ Scenario comparison

**API Endpoints:**
```http
POST   /api/memory/counterfactual/create
GET    /api/memory/counterfactual/list
POST   /api/memory/counterfactual/simulate
GET    /api/memory/counterfactual/compare
```

---

## Cognitive Engine

### 2.1 Causal Reasoning

**Description:** Advanced causal chain discovery và intervention planning.

**Features:**
- ✅ Causal chain discovery (A → B → C)
- ✅ Counterfactual analysis
- ✅ Intervention planning
- ✅ Side effect prediction
- ✅ Lessons learned extraction
- ✅ Confidence scoring

**API Endpoints:**
```http
POST   /api/cognition/causal/discover-chains
GET    /api/cognition/causal/chains/{id}
POST   /api/cognition/causal/simulate
POST   /api/cognition/causal/intervention-plan
GET    /api/cognition/causal/lessons-learned
```

**Example:**
```python
# Discover causal chains
chains = requests.post('http://localhost:8216/api/cognition/causal/discover-chains', json={
    "start_event": "system_crash",
    "max_depth": 5,
    "confidence_threshold": 0.7
})

# Plan intervention
plan = requests.post('http://localhost:8216/api/cognition/causal/intervention-plan', json={
    "goal": "prevent_system_crash",
    "constraints": ["cost < 1000", "time < 1_week"]
})
```

---

### 2.2 Cross-Modal Linking

**Description:** Connect information across different modalities (text, image, audio, video).

**Features:**
- ✅ Multi-modal embeddings
- ✅ Cross-modal search
- ✅ Automatic modality detection
- ✅ Unified representation
- ✅ Modality translation

**API Endpoints:**
```http
POST   /api/cognition/cross-modal/link
GET    /api/cognition/cross-modal/search?query=...&modalities=text,image
POST   /api/cognition/cross-modal/translate
GET    /api/cognition/cross-modal/alignments
```

---

### 2.3 Logical Reasoning

**Description:** Formal logic-based reasoning với rule inference.

**Features:**
- ✅ Propositional logic
- ✅ First-order logic
- ✅ Rule-based inference
- ✅ Constraint satisfaction
- ✅ Proof generation
- ✅ Logic validation

**API Endpoints:**
```http
POST   /api/cognition/logical/infer
POST   /api/cognition/logical/validate
GET    /api/cognition/logical/rules
POST   /api/cognition/logical/add-rule
```

---

### 2.4 Memory Review Cycle

**Description:** Automated quality review và curation pipeline.

**Features:**
- ✅ Automatic quality scoring
- ✅ Review session creation
- ✅ Human-in-the-loop feedback
- ✅ Quality improvement suggestions
- ✅ Duplicate detection
- ✅ Consolidation recommendations

**API Endpoints:**
```http
GET    /api/memory/review/sessions
POST   /api/memory/review/sessions
POST   /api/memory/review/respond
POST   /api/memory/review/confirm
POST   /api/memory/review/undo
POST   /api/memory/review/close
```

---

## Learning & Adaptation

### 3.1 Federated Learning

**Description:** Privacy-preserving distributed learning across multiple nodes.

**Features:**
- ✅ Distributed model training
- ✅ Privacy guarantees (differential privacy)
- ✅ Model aggregation
- ✅ Client selection
- ✅ Secure aggregation
- ✅ Model versioning

**API Endpoints:**
```http
POST   /api/learning/federated/start
GET    /api/learning/federated/status/{session_id}
POST   /api/learning/federated/update-model
GET    /api/learning/federated/models
```

---

### 3.2 Auto-Tuning System

**Description:** Automatic performance optimization và parameter tuning.

**Features:**
- ✅ Performance monitoring
- ✅ Bottleneck detection
- ✅ Automatic parameter tuning
- ✅ A/B testing framework
- ✅ Rollback capability
- ✅ Safety limits

**API Endpoints:**
```http
GET    /api/tuning/metrics
POST   /api/tuning/optimize
GET    /api/tuning/suggestions
POST   /api/tuning/apply
GET    /api/tuning/history
```

**Example:**
```python
# Get tuning suggestions
suggestions = requests.get('http://localhost:8216/api/tuning/suggestions')

# Apply optimization
response = requests.post('http://localhost:8216/api/tuning/apply', json={
    "optimization_id": "opt-123",
    "rollback_on_failure": True
})
```

---

### 3.3 Self-Learning Engine

**Description:** Continuous improvement từ feedback và usage patterns.

**Features:**
- ✅ Feedback collection
- ✅ Pattern recognition
- ✅ Model updates
- ✅ Performance tracking
- ✅ Continuous learning loop
- ✅ Forgetting prevention

**API Endpoints:**
```http
POST   /api/learning/feedback
GET    /api/learning/improvements
POST   /api/learning/train
GET    /api/learning/progress
```

---

## Analytics & Insights

### 4.1 Analytics Dashboard

**Description:** Real-time metrics, trends, và visualizations.

**Features:**
- ✅ 10+ real-time metrics
- ✅ Time series charts
- ✅ Trend analysis
- ✅ Anomaly detection
- ✅ Customizable widgets
- ✅ Export capabilities

**Metrics Tracked:**
- Knowledge units count (total, by type, by status)
- Freshness metrics (avg age, stale count)
- Quality metrics (avg confidence, verified rate)
- Activity metrics (creates, updates, deletes per day)
- Search metrics (queries, results, click-through rate)
- Performance metrics (latency, throughput, error rate)

**API Endpoints:**
```http
GET    /api/analytics/metrics
GET    /api/analytics/trends?metric=...&period=...
GET    /api/analytics/distribution?by=type|status|scope
GET    /api/analytics/activity?granularity=hour|day|week
GET    /api/analytics/forecast?metric=...&days=30
```

**Dashboard Widgets:**
```python
widgets = [
    {"type": "metric", "title": "Total Knowledge", "value": 15000},
    {"type": "chart", "title": "Growth Trend", "data": [...]},
    {"type": "gauge", "title": "Quality Score", "value": 0.87},
    {"type": "table", "title": "Top Categories", "data": [...]}
]
```

---

### 4.2 AI Insights Engine

**Description:** Pattern detection, anomaly detection, và automated insights.

**Features:**
- ✅ Pattern detection
- ✅ Anomaly detection (Isolation Forest, LOF)
- ✅ Trend forecasting (Prophet, ARIMA)
- ✅ Correlation analysis
- ✅ Automated insight generation
- ✅ Recommendation suggestions

**API Endpoints:**
```http
GET    /api/analytics/insights
POST   /api/analytics/detect-anomalies
GET    /api/analytics/forecasts
POST   /api/analytics/correlations
```

**Example:**
```python
# Get AI insights
insights = requests.get('http://localhost:8216/api/analytics/insights')
# Returns: [
#   {"type": "anomaly", "message": "Unusual spike in errors at 2PM", "severity": "high"},
#   {"type": "trend", "message": "Knowledge growth accelerating", "confidence": 0.92},
#   {"type": "recommendation", "message": "Consider archiving old entries", "impact": "medium"}
# ]
```

---

### 4.3 Report Generator

**Description:** Automated report generation với custom templates.

**Features:**
- ✅ 5+ report templates
- ✅ Scheduled reports
- ✅ Multiple formats (PDF, Excel, HTML, Markdown)
- ✅ Custom date ranges
- ✅ Email delivery
- ✅ Report scheduling

**API Endpoints:**
```http
POST   /api/analytics/reports/generate
GET    /api/analytics/reports/{id}
POST   /api/analytics/reports/schedule
GET    /api/analytics/reports/list
DELETE /api/analytics/reports/{id}
```

**Report Types:**
- Daily Activity Summary
- Weekly Quality Report
- Monthly Analytics Summary
- Custom Ad-hoc Reports

---

### 4.4 Recommendation System

**Description:** Personalized content recommendations.

**Features:**
- ✅ Content-based filtering
- ✅ Collaborative filtering
- ✅ Hybrid recommendations
- ✅ Diversity optimization
- ✅ Freshness balancing
- ✅ Relevance scoring > 90%

**API Endpoints:**
```http
GET    /api/analytics/recommendations?user_id=...&limit=...
POST   /api/analytics/recommendations/rate
GET    /api/analytics/recommendations/explain/{id}
```

---

## Mobile & Voice Interface

### 5.1 Mobile App (React Native)

**Description:** Cross-platform mobile application (iOS/Android).

**Features:**
- ✅ Knowledge base browser
- ✅ Advanced search với filters
- ✅ Real-time updates (WebSocket)
- ✅ Offline mode với sync
- ✅ Push notifications
- ✅ Biometric authentication
- ✅ Dark mode
- ✅ Accessibility support

**Screens:**
- Home Screen (dashboard, quick actions)
- Search Screen (filters, pagination)
- Detail Screen (knowledge unit view)
- Settings Screen (preferences, sync)
- Offline Screen (queued operations)

**API Integration:**
```typescript
// Knowledge API
const knowledge = await api.knowledge.get(id);
const results = await api.knowledge.search(query, { filters, limit: 20 });

// Sync API
await api.sync.pull();
await api.sync.push();

// Notifications
Notifications.subscribe('knowledge_updated', handleUpdate);
```

---

### 5.2 Natural Language Query

**Description:** NLP-powered query interface.

**Features:**
- ✅ Intent recognition
- ✅ Entity extraction
- ✅ Query parsing
- ✅ Semantic understanding
- ✅ Query suggestions
- ✅ Query correction

**API Endpoints:**
```http
POST   /api/nlp/parse-query
GET    /api/nlp/suggestions?q=...
POST   /api/nlp/extract-intent
GET    /api/nlp/entities/{query_id}
```

**Example:**
```python
# Parse natural language query
response = requests.post('http://localhost:8216/api/nlp/parse-query', json={
    "query": "Show me all verified facts about AI from last month"
})
# Returns: {
#   "intent": "search",
#   "entities": {"status": "verified", "type": "fact", "topic": "AI", "time_range": "last_month"},
#   "structured_query": {"status": "VERIFIED", "type": "fact", "tags": ["AI"], "created_after": "..."}
# }
```

---

### 5.3 Voice Interface

**Description:** Speech-to-text và text-to-speech integration.

**Features:**
- ✅ Speech-to-text (STT)
- ✅ Text-to-speech (TTS)
- ✅ Voice commands
- ✅ Multi-language support (Vietnamese, English)
- ✅ Noise cancellation
- ✅ Voice authentication

**API Endpoints:**
```http
POST   /api/voice/speech-to-text
POST   /api/voice/text-to-speech
GET    /api/voice/commands
POST   /api/voice/execute-command
```

**Example:**
```python
# Speech to text
audio_file = open('recording.wav', 'rb')
response = requests.post('http://localhost:8216/api/voice/speech-to-text',
                        files={'audio': audio_file})
text = response.json()['transcript']

# Text to speech
response = requests.post('http://localhost:8216/api/voice/text-to-speech', json={
    "text": "Hello, how can I help you?",
    "voice": "female-vietnamese",
    "speed": 1.0
})
audio = response.content
```

---

## Enterprise Integration

### 6.1 API Gateway

**Description:** Centralized API management với rate limiting, caching, và authentication.

**Features:**
- ✅ Request routing
- ✅ Rate limiting (per-user, per-IP, per-endpoint)
- ✅ Response caching
- ✅ Authentication proxy
- ✅ Request/response transformation
- ✅ API versioning
- ✅ Circuit breakers

**Configuration:**
```yaml
routes:
  - path: /api/v1/*
    upstream: http://backend:8216
    rate_limit: 1000/hour
    cache:
      enabled: true
      ttl: 300
    auth:
      type: jwt
      required: true
```

**API Endpoints:**
```http
GET    /api/gateway/routes
POST   /api/gateway/routes
PUT    /api/gateway/routes/{id}
DELETE /api/gateway/routes/{id}
GET    /api/gateway/metrics
```

---

### 6.2 Enterprise Connectors

**Description:** Pre-built connectors cho enterprise systems.

**Supported Connectors:**
- ✅ Salesforce
- ✅ Microsoft 365
- ✅ Slack
- ✅ Teams
- ✅ SAP
- ✅ Oracle
- ✅ Google Workspace

**Features:**
- ✅ OAuth 2.0 authentication
- ✅ Real-time sync
- ✅ Bi-directional sync
- ✅ Conflict resolution
- ✅ Error handling
- ✅ Retry logic

**API Endpoints:**
```http
GET    /api/connectors/list
POST   /api/connectors/{id}/connect
POST   /api/connectors/{id}/sync
GET    /api/connectors/{id}/status
DELETE /api/connectors/{id}
```

**Example:**
```python
# Connect to Salesforce
connector = requests.post('http://localhost:8216/api/connectors/salesforce/connect', json={
    "client_id": "...",
    "client_secret": "...",
    "callback_url": "https://quanai.company.com/callback"
})

# Sync data
sync = requests.post('http://localhost:8216/api/connectors/salesforce/sync', json={
    "objects": ["Account", "Contact", "Opportunity"],
    "mode": "incremental"
})
```

---

### 6.3 Message Queue Integration

**Description:** Event-driven architecture với message queues.

**Supported Queues:**
- ✅ Apache Kafka
- ✅ RabbitMQ
- ✅ AWS SQS
- ✅ Azure Service Bus

**Features:**
- ✅ Publish/subscribe
- ✅ Message persistence
- ✅ Dead letter queues
- ✅ Message ordering
- ✅ At-least-once delivery
- ✅ Retry policies

**API Endpoints:**
```http
POST   /api/mq/publish
GET    /api/mq/consume?queue=...
POST   /api/mq/subscriptions
DELETE /api/mq/subscriptions/{id}
GET    /api/mq/queues/{name}/stats
```

---

### 6.4 Webhook System

**Description:** Event-driven integrations với webhooks.

**Features:**
- ✅ Webhook registration
- ✅ Event subscriptions
- ✅ HMAC signature verification
- ✅ Retry with exponential backoff
- ✅ Dead letter queue
- ✅ Delivery confirmation

**API Endpoints:**
```http
POST   /api/webhooks
GET    /api/webhooks
PUT    /api/webhooks/{id}
DELETE /api/webhooks/{id}
POST   /api/webhooks/{id}/test
GET    /api/webhooks/{id}/deliveries
```

**Example:**
```python
# Register webhook
webhook = requests.post('http://localhost:8216/api/webhooks', json={
    "url": "https://partner.com/webhook",
    "events": ["knowledge.created", "knowledge.updated"],
    "secret": "webhook-secret-key"
})

# Webhook payload
{
    "event": "knowledge.created",
    "timestamp": "2026-10-28T10:00:00Z",
    "data": {"id": "uuid", "type": "fact", ...},
    "signature": "hmac-sha256-signature"
}
```

---

## Security & Compliance

### 7.1 Authentication

**Description:** Multi-factor authentication với multiple providers.

**Features:**
- ✅ OAuth 2.0 / OIDC
- ✅ TOTP (Google Authenticator, Authy)
- ✅ SMS verification
- ✅ Email verification
- ✅ Hardware keys (FIDO2/WebAuthn)
- ✅ Social login (Google, Microsoft, GitHub)
- ✅ SAML 2.0 SSO

**API Endpoints:**
```http
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
POST   /api/auth/mfa/enable
POST   /api/auth/mfa/verify
POST   /api/auth/mfa/disable
GET    /api/auth/session
POST   /api/auth/session/revoke
```

**Example:**
```python
# Login with MFA
login = requests.post('http://localhost:8216/api/auth/login', json={
    "username": "user@example.com",
    "password": "password123"
})

# MFA required
if login.json().get('mfa_required'):
    mfa = requests.post('http://localhost:8216/api/auth/mfa/verify', json={
        "session_id": login.json()['session_id'],
        "code": "123456"  # TOTP code
    })
    token = mfa.json()['access_token']
```

---

### 7.2 Authorization (RBAC/ABAC)

**Description:** Fine-grained access control.

**Roles:**
- admin - Full system access
- developer - Read/write code & configs
- analyst - Read analytics & reports
- user - Basic read/write
- viewer - Read-only
- auditor - Audit log access
- operator - System operations
- security_admin - Security management

**API Endpoints:**
```http
GET    /api/auth/roles
POST   /api/auth/roles
GET    /api/auth/permissions
POST   /api/auth/permissions
GET    /api/auth/users/{id}/roles
POST   /api/auth/users/{id}/roles
DELETE /api/auth/users/{id}/roles/{role}
```

---

### 7.3 Audit Logging

**Description:** Immutable audit trail cho compliance.

**Features:**
- ✅ SHA-256 hash chaining
- ✅ Tamper-evident logs
- ✅ 1-year retention
- ✅ GDPR compliance
- ✅ SOC2 compliance
- ✅ HIPAA compliance
- ✅ Export capabilities

**API Endpoints:**
```http
GET    /api/audit/logs?start=...&end=...&user=...&action=...
POST   /api/audit/export
GET    /api/audit/compliance-report
GET    /api/audit/integrity-check
```

---

### 7.4 Data Protection

**Description:** Encryption và data security.

**Features:**
- ✅ Encryption at rest (AES-256)
- ✅ Encryption in transit (TLS 1.3)
- ✅ Key management (HSM-ready)
- ✅ Data masking
- ✅ PII detection
- ✅ Data classification

**API Endpoints:**
```http
POST   /api/security/encrypt
POST   /api/security/decrypt
GET    /api/security/keys
POST   /api/security/keys/rotate
GET    /api/security/masking-rules
POST   /api/security/masking-rules
```

---

## API Reference

### Authentication

All API requests require authentication:

```http
Authorization: Bearer <jwt_token>
```

### Rate Limiting

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1698500000
```

### Error Responses

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {"field": "content", "message": "Required field"}
    ]
  }
}
```

### Common Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## Appendix: Complete API Endpoint List

### Memory (26 endpoints)
- `/api/memory/knowledge-units` (GET, POST, PUT, DELETE)
- `/api/memory/knowledge-units/{id}` (GET, PUT, DELETE)
- `/api/memory/knowledge-units/search` (GET)
- `/api/memory/graph/relationships` (GET, POST)
- `/api/memory/temporal/*` (5 endpoints)
- `/api/memory/emotional/*` (4 endpoints)
- `/api/memory/counterfactual/*` (4 endpoints)
- `/api/memory/review/*` (6 endpoints)

### Cognition (15 endpoints)
- `/api/cognition/causal/*` (5 endpoints)
- `/api/cognition/cross-modal/*` (4 endpoints)
- `/api/cognition/logical/*` (4 endpoints)
- `/api/cognition/memory-review/*` (2 endpoints)

### Learning (10 endpoints)
- `/api/learning/federated/*` (4 endpoints)
- `/api/learning/feedback` (POST)
- `/api/learning/improvements` (GET)
- `/api/learning/train` (POST)
- `/api/learning/progress` (GET)

### Analytics (15 endpoints)
- `/api/analytics/metrics` (GET)
- `/api/analytics/trends` (GET)
- `/api/analytics/insights` (GET)
- `/api/analytics/reports/*` (5 endpoints)
- `/api/analytics/recommendations/*` (3 endpoints)

### Mobile & NLP (10 endpoints)
- `/api/nlp/*` (4 endpoints)
- `/api/voice/*` (4 endpoints)
- `/api/mobile/sync` (POST)
- `/api/mobile/notifications` (GET, POST)

### Enterprise (20 endpoints)
- `/api/gateway/*` (5 endpoints)
- `/api/connectors/*` (5 endpoints)
- `/api/mq/*` (5 endpoints)
- `/api/webhooks/*` (5 endpoints)

### Security (15 endpoints)
- `/api/auth/*` (8 endpoints)
- `/api/audit/*` (4 endpoints)
- `/api/security/*` (3 endpoints)

**Total: 100+ API endpoints**

---

**Document Version:** V30.0  
**Last Updated:** 2026-10-28  
**Maintained By:** QUAN AI BRAIN Team