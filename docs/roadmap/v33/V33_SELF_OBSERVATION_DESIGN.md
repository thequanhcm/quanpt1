# V33 Self-Observation Engine Design
**Version:** 1.0  
**Date:** 2026-10-28  
**Status:** DRAFT

---

## 1. OVERVIEW

### 1.1 Goal

Build a **Self-Observation Engine** that enables QUAN AI BRAIN to:
- Monitor its own operations through verifiable metrics
- Detect failures, anomalies, and quality degradation
- Trace observations back to source data
- Distinguish between facts, hypotheses, and conclusions
- Generate evidence-based improvement proposals

### 1.2 Design Principles

1. **Evidence-based** - No claims without verifiable data
2. **Traceable** - Every observation links to source
3. **Categorical** - Separate facts, hypotheses, conclusions
4. **Bounded** - Only observe within authorized scope
5. **Auditable** - All observations logged for review

---

## 2. OBSERVATION SOURCES

### 2.1 Authorized Data Sources

| Source | Purpose | Access Level | Sensitivity |
|--------|---------|--------------|-------------|
| Task logs | Failure analysis | Read | Medium |
| Task results | Success/failure metrics | Read | Medium |
| Tool execution logs | Tool reliability | Read | High |
| Memory access logs | Retrieval quality | Read | High |
| Benchmark results | Performance tracking | Read | Low |
| Governance decisions | Policy enforcement | Read | High |
| Error reports | Error classification | Read | Medium |
| Performance metrics | Latency, throughput | Read | Low |

### 2.2 Data Provenance Requirements

Each observation must include:
- `source_type` - Type of data source
- `source_ref` - Reference to specific record
- `timestamp` - When data was generated
- `access_authorized` - Whether access was authorized
- `redaction_applied` - Whether sensitive data was redacted
- `quality_score` - Confidence in data quality

---

## 3. OBSERVATION MODEL

### 3.1 Observation Structure

```python
@dataclass
class SystemObservation:
    observation_id: str
    event_type: str  # task_failure | tool_error | memory_gap | performance_degradation
    timestamp: str
    task_id: str | None
    component_id: str
    runtime_version: str
    policy_version: str
    source_reference: str
    severity: int  # 0-5
    result: str  # success | failure | blocked | timeout
    error_code: str | None
    evidence_refs: list[str]
    
    # Classification
    is_fact: bool  # Directly observed
    is_hypothesis: bool  # Inferred cause
    is_conclusion: bool  # Final assessment
    
    # Metadata
    confidence_score: float
    data_quality_score: float
    redaction_applied: bool
```

### 3.2 Observation Categories

| Category | Subcategories |
|----------|---------------|
| **Memory Quality** | Missing knowledge, stale knowledge, conflicting knowledge, retrieval failure |
| **Retrieval Quality** | Low recall, low precision, wrong scope, slow retrieval |
| **Reasoning Quality** | Logical errors, incomplete analysis, wrong conclusions |
| **Tool Execution** | Tool failure, timeout, permission denied, wrong result |
| **Workflow Reliability** | Stage failure, planning error, verification failure |
| **Security & Governance** | Policy violation, unauthorized access, blocked action |
| **Performance** | High latency, high resource usage, throughput drop |
| **Data Quality** | Corrupted data, missing fields, inconsistent state |

---

## 4. OBSERVATION PIPELINE

### 4.1 Pipeline Stages

```
Event Generation → Data Collection → Normalization → Classification → 
Analysis → Hypothesis Generation → Evidence Linking → Observation Storage
```

**Stage Details:**

1. **Event Generation** - System events from task execution, tool calls, etc.
2. **Data Collection** - Gather relevant data from authorized sources
3. **Normalization** - Standardize format, redact sensitive data
4. **Classification** - Categorize by type, severity, component
5. **Analysis** - Identify patterns, anomalies, trends
6. **Hypothesis Generation** - Propose potential causes (with confidence)
7. **Evidence Linking** - Link observations to source data
8. **Observation Storage** - Persist to observation database

### 4.2 Event Types

```python
class EventType(str, Enum):
    # Task events
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_BLOCKED = "task_blocked"
    TASK_TIMEOUT = "task_timeout"
    
    # Tool events
    TOOL_CALLED = "tool_called"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    TOOL_BLOCKED = "tool_blocked"
    TOOL_TIMEOUT = "tool_timeout"
    
    # Memory events
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_NOT_FOUND = "memory_not_found"
    MEMORY_CONFLICT_DETECTED = "memory_conflict"
    MEMORY_DUPLICATE_DETECTED = "memory_duplicate"
    
    # Governance events
    POLICY_CHECK_PASSED = "policy_passed"
    POLICY_CHECK_FAILED = "policy_failed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    
    # Performance events
    LATENCY_HIGH = "latency_high"
    RESOURCE_HIGH = "resource_high"
    THROUGHPUT_LOW = "throughput_low"
    
    # Benchmark events
    BENCHMARK_STARTED = "benchmark_started"
    BENCHMARK_COMPLETED = "benchmark_completed"
    BENCHMARK_FAILED = "benchmark_failed"
    REGRESSION_DETECTED = "regression_detected"
```

---

## 5. ANALYSIS ENGINE

### 5.1 Pattern Detection

**Detectable Patterns:**
- Repeated failures (same error, same component)
- Performance degradation (increasing latency, decreasing throughput)
- Memory quality decline (increasing conflicts, duplicates)
- Tool reliability issues (increasing failure rate)
- Governance violations (increasing blocked actions)
- Benchmark score drops

### 5.2 Root Cause Analysis

For each detected issue:
1. **Gather evidence** - Collect all related observations
2. **Identify patterns** - Look for common factors
3. **Generate hypotheses** - Propose potential causes
4. **Score hypotheses** - Assign confidence based on evidence
5. **Link to source** - Trace back to original data

**Hypothesis Scoring:**
- High confidence: Multiple independent observations, clear pattern
- Medium confidence: Some evidence, plausible explanation
- Low confidence: Limited evidence, speculative
- Unknown: Insufficient data

### 5.3 Output Format

```python
@dataclass
class ProblemAnalysis:
    analysis_id: str
    problem_statement: str
    evidence_count: int
    evidence_refs: list[str]
    
    # Classification
    is_fact: bool  # Problem definitely exists
    is_hypothesis: bool  # Cause is inferred
    
    # Root cause hypotheses
    hypotheses: list[dict]
    # {hypothesis, confidence, evidence, missing_data}
    
    # Recommendations
    proposed_actions: list[str]
    priority: int  # 1-5
    
    # Metadata
    analyzed_at: str
    analyzed_by: str
    confidence_score: float
```

---

## 6. IMPLEMENTATION PLAN

### 6.1 Phase 1: Core Observation Engine (Week 1)

**Deliverables:**
- `SelfObservationEngine` class
- `SystemObservation` model
- Event collection from task logs
- Event collection from tool execution
- Event collection from memory access
- Basic classification
- Observation storage

**Tests:**
- Test event collection
- Test classification
- Test storage
- Test redaction

### 6.2 Phase 2: Analysis Engine (Week 2)

**Deliverables:**
- Pattern detection
- Hypothesis generation
- Root cause analysis
- Confidence scoring
- Evidence linking

**Tests:**
- Test pattern detection
- Test hypothesis generation
- Test confidence scoring
- Test evidence linking

### 6.3 Phase 3: Integration & Dashboard (Week 3)

**Deliverables:**
- Integration with task pipeline
- Integration with tool execution
- Integration with memory system
- Observation dashboard (web-based)
- Query API

**Tests:**
- Test integration
- Test dashboard
- Test API

---

## 7. ACCEPTANCE CRITERIA

### 7.1 Functional

- [ ] Can collect events from task execution
- [ ] Can collect events from tool calls
- [ ] Can collect events from memory access
- [ ] Can classify events by type and severity
- [ ] Can detect repeated failures
- [ ] Can detect performance degradation
- [ ] Can generate hypotheses with confidence scores
- [ ] Can link observations to source data
- [ ] Can redact sensitive data
- [ ] Can query observations by criteria

### 7.2 Non-Functional

- [ ] No secret or sensitive data in observations
- [ ] All observations have source references
- [ ] All hypotheses have confidence scores
- [ ] Can distinguish fact from hypothesis
- [ ] Observations are immutable once stored
- [ ] Can trace observation back to original event

---

## 8. RISK ASSESSMENT

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Observing unauthorized data | HIGH | LOW | Strict access control, audit |
| False positives in detection | MEDIUM | MEDIUM | Confidence scoring, human review |
| Performance overhead | LOW | MEDIUM | Batch processing, sampling |
| Incomplete data | MEDIUM | HIGH | Mark as "insufficient evidence" |

---

## 9. NEXT STEPS

1. Implement `SelfObservationEngine` class
2. Create `SystemObservation` model
3. Implement event collection from task logs
4. Implement classification logic
5. Implement storage
6. Write tests
7. Run baseline tests

---

**Document Status:** DRAFT  
**Last Updated:** 2026-10-28  
**Next Review:** After Phase 1 implementation