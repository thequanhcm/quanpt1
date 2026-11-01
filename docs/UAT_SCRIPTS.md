# QUAN AI BRAIN - User Acceptance Testing (UAT) Scripts
**Version:** V22.0  
**Last Updated:** 2024-10-28  
**Tester:** [Name]  
**Date:** [Date]

---

## Table of Contents
1. [Test Environment](#1-test-environment)
2. [Functional Tests](#2-functional-tests)
3. [Performance Tests](#3-performance-tests)
4. [Security Tests](#4-security-tests)
5. [Integration Tests](#5-integration-tests)
6. [User Experience Tests](#6-user-experience-tests)
7. [Regression Tests](#7-regression-tests)
8. [Sign-off](#8-sign-off)

---

## 1. Test Environment

### 1.1 Environment Setup
```bash
# Environment: UAT
URL: https://uat-api.quan-ai-brain.vn
Database: PostgreSQL 15
Redis: 7.0
Docker: 20.10+
Python: 3.11

# Test credentials
Username: uat_tester
Password: [secure-password]
API Token: [generated-token]
```

### 1.2 Test Data
```sql
-- Create test knowledge units
INSERT INTO knowledge_units (knowledge_id, knowledge_type, subject, predicate, object, statement, scope, status, confidence)
VALUES 
  ('uat_001', 'FACT', 'test', 'is', 'example', 'This is a test fact', 'uat', 'VERIFIED', 0.9),
  ('uat_002', 'QUESTION', 'what', 'is', 'test', 'What is the test question?', 'uat', 'VERIFIED', 0.85),
  ('uat_003', 'EVENT', 'meeting', 'happened', 'yesterday', 'Team meeting occurred yesterday', 'uat', 'VERIFIED', 0.95);

-- Create test relations
INSERT INTO relations (source_ku_id, target_ku_id, relation_type, confidence)
VALUES ('uat_001', 'uat_002', 'RELATED_TO', 0.8);
```

---

## 2. Functional Tests

### Test Case 1: Knowledge Unit Creation
**ID:** UAT-FUNC-001  
**Priority:** High  
**Preconditions:** User authenticated

**Steps:**
1. Send POST request to `/v1/memory/write`
2. Include knowledge unit data:
```json
{
  "knowledge_type": "FACT",
  "subject": "UAT",
  "predicate": "tests",
  "object": "functional",
  "statement": "UAT functional test case",
  "scope": "uat"
}
```

**Expected Result:**
- HTTP 201 Created
- Returns knowledge_id
- Unit appears in database

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 2: Knowledge Unit Search
**ID:** UAT-FUNC-002  
**Priority:** High  
**Preconditions:** Test data exists

**Steps:**
1. Send GET request to `/v1/memory/search?q=UAT&limit=10`
2. Verify response structure

**Expected Result:**
- HTTP 200 OK
- Returns array of knowledge units
- Contains at least 1 result with "UAT"
- Response time < 100ms

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 3: Temporal Memory
**ID:** UAT-FUNC-003  
**Priority:** Medium  
**Preconditions:** Temporal data exists

**Steps:**
1. Send GET to `/v1/memory/temporal/stats`
2. Verify statistics returned
3. Send GET to `/v1/memory/temporal/scores?limit=5`
4. Verify freshness scores

**Expected Result:**
- Stats include total_kus, avg_freshness, avg_confidence
- Scores array returned
- Freshness scores between 0-1

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 4: Cross-Modal Context
**ID:** UAT-FUNC-004  
**Priority:** Medium  
**Preconditions:** None

**Steps:**
1. Set context: POST `/v1/memory/context/set`
```json
{
  "project": "UAT-Test",
  "task": "Functional-Testing",
  "user": "uat_tester"
}
```
2. Verify context set
3. Get context: GET `/v1/memory/context/current`

**Expected Result:**
- HTTP 200 OK
- Context returned matches sent data

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 5: Quality Scoring
**ID:** UAT-FUNC-005  
**Priority:** Medium  
**Preconditions:** Knowledge units exist

**Steps:**
1. GET `/v1/memory/quality/metrics`
2. Verify metrics structure
3. GET `/v1/memory/quality/low-quality?threshold=0.4`
4. Verify low quality KUs returned

**Expected Result:**
- Metrics include total_kus, high/medium/low counts
- Average scores calculated
- Low quality list returned (may be empty)

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 6: Knowledge Graph
**ID:** UAT-FUNC-006  
**Priority:** Medium  
**Preconditions:** Graph data exists

**Steps:**
1. GET `/v1/memory/graph/entities`
2. GET `/v1/memory/graph/relationships`
3. GET `/v1/memory/graph/metrics`

**Expected Result:**
- Entities array returned
- Relationships array returned
- Metrics include num_nodes, num_edges, density

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 7: Emotional Memory
**ID:** UAT-FUNC-007  
**Priority:** Low  
**Preconditions:** Emotional data exists

**Steps:**
1. GET `/v1/memory/emotional/timeline/{user_id}?days=30`
2. GET `/v1/memory/emotional/peaks?threshold=0.8`
3. GET `/v1/memory/retrieve/emotion/joy?top_k=5`

**Expected Result:**
- Timeline array returned
- Peaks array returned (may be empty)
- Emotion-based results returned

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 8: Causal Reasoning
**ID:** UAT-FUNC-008  
**Priority:** Low  
**Preconditions:** Causal data exists

**Steps:**
1. GET `/v1/memory/causal/causes/{event_id}?depth=3`
2. GET `/v1/memory/causal/effects/{event_id}?depth=3`
3. POST `/v1/memory/causal/root-cause` with `{effect_id: "event2"}`

**Expected Result:**
- Causes array returned
- Effects array returned
- Root cause identified

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 9: Recommendations
**ID:** UAT-FUNC-009  
**Priority:** Medium  
**Preconditions:** User profile exists

**Steps:**
1. GET `/v1/ai/recommend/{user_id}?top_k=10`
2. Verify recommendations returned
3. Check recommendation scores

**Expected Result:**
- Recommendations array returned
- Each has item_id, score, reason
- Scores sorted descending

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

## 3. Performance Tests

### Test Case 10: Query Latency
**ID:** UAT-PERF-001  
**Priority:** High  
**Tool:** Apache Bench / wrk

**Steps:**
```bash
wrk -t12 -c400 -d30s http://localhost:8080/v1/memory/search?q=test
```

**Expected Result:**
- P50 latency < 50ms
- P95 latency < 100ms
- P99 latency < 200ms
- Throughput > 100 req/sec

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 11: Concurrent Users
**ID:** UAT-PERF-002  
**Priority:** High  
**Tool:** Locust

**Steps:**
1. Configure Locust with 100 concurrent users
2. Run for 5 minutes
3. Monitor error rate and latency

**Expected Result:**
- Error rate < 1%
- P95 latency < 200ms
- No crashes or timeouts

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 12: Cache Performance
**ID:** UAT-PERF-003  
**Priority:** Medium  
**Preconditions:** Cache enabled

**Steps:**
1. Run same query 100 times
2. Measure first vs subsequent queries
3. Check cache hit rate

**Expected Result:**
- First query: ~50-100ms
- Cached queries: < 10ms
- Cache hit rate > 90%

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

## 4. Security Tests

### Test Case 13: Authentication
**ID:** UAT-SEC-001  
**Priority:** High  
**Preconditions:** Valid/invalid tokens available

**Steps:**
1. Request without token → Should get 401
2. Request with invalid token → Should get 401
3. Request with valid token → Should get 200

**Expected Result:**
- Unauthorized requests rejected
- Authorized requests succeed

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 14: Rate Limiting
**ID:** UAT-SEC-002  
**Priority:** High  
**Preconditions:** Rate limiting enabled

**Steps:**
```bash
for i in {1..150}; do curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/v1/memory/health; done
```

**Expected Result:**
- First 100 requests succeed
- Requests 101-150 get 429 Too Many Requests
- Rate limit header present

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 15: Input Validation
**ID:** UAT-SEC-003  
**Priority:** High  
**Preconditions:** None

**Steps:**
1. Send SQL injection: `q=' OR '1'='1`
2. Send XSS: `q=<script>alert('xss')</script>`
3. Send oversized input (10MB)

**Expected Result:**
- All inputs sanitized or rejected
- No SQL execution
- No script execution
- Proper error messages

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

## 5. Integration Tests

### Test Case 16: End-to-End Workflow
**ID:** UAT-INT-001  
**Priority:** High  
**Preconditions:** All services running

**Steps:**
1. Create knowledge unit
2. Search for it
3. Update it
4. Verify update
5. Delete it
6. Verify deletion

**Expected Result:**
- All operations succeed
- Data consistent throughout
- No errors in logs

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 17: Cross-Module Integration
**ID:** UAT-INT-002  
**Priority:** Medium  
**Preconditions:** Multiple modules enabled

**Steps:**
1. Create KU with emotional content
2. Verify emotional scoring
3. Search by emotion
4. Verify causal links
5. Check quality score

**Expected Result:**
- All modules interact correctly
- Data flows between modules
- No conflicts or errors

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

## 6. User Experience Tests

### Test Case 18: API Documentation
**ID:** UAT-UX-001  
**Priority:** Medium  
**Preconditions:** OpenAPI spec available

**Steps:**
1. Access `/docs` or Swagger UI
2. Try example requests
3. Verify documentation accuracy

**Expected Result:**
- Documentation accessible
- Examples work correctly
- All endpoints documented

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

### Test Case 19: Error Messages
**ID:** UAT-UX-002  
**Priority:** Medium  
**Preconditions:** None

**Steps:**
1. Trigger various errors (404, 500, 400)
2. Check error message clarity
3. Verify error codes

**Expected Result:**
- Error messages clear and helpful
- Error codes consistent
- No sensitive data exposed

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

## 7. Regression Tests

### Test Case 20: V11-V20 Features
**ID:** UAT-REG-001  
**Priority:** High  
**Preconditions:** All versions deployed

**Steps:**
1. Test V11 temporal features
2. Test V12 cross-modal features
3. Test V13 quality features
4. Test V14-V20 features
5. Verify no regressions

**Expected Result:**
- All V11-V20 features work
- No performance degradation
- No new bugs introduced

**Actual Result:** _______________  
**Status:** ☐ Pass ☐ Fail  
**Notes:** _______________

---

## 8. Sign-off

### Test Summary
| Category | Total | Pass | Fail | Skip |
|---|---|---|---|---|
| Functional | 9 | ___ | ___ | ___ |
| Performance | 3 | ___ | ___ | ___ |
| Security | 3 | ___ | ___ | ___ |
| Integration | 2 | ___ | ___ | ___ |
| UX | 2 | ___ | ___ | ___ |
| Regression | 1 | ___ | ___ | ___ |
| **Total** | **20** | ___ | ___ | ___ |

### Issues Found
| ID | Severity | Description | Status |
|---|---|---|---|
| | | | |
| | | | |

### Recommendations
1. _______________
2. _______________
3. _______________

### Sign-off
**Tester:** _______________  
**Date:** _______________  
**Decision:** ☐ Approved ☐ Approved with Conditions ☐ Rejected

**Conditions/Notes:**  
_______________  
_______________  
_______________

**Approver:** _______________  
**Date:** _______________  
**Final Decision:** ☐ Go to Production ☐ Hold ☐ Reject

---

**Document Version:** V22.0  
**Last Updated:** 2024-10-28