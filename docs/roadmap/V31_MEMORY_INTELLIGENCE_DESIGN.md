# V31 MEMORY INTELLIGENCE - DESIGN SPECIFICATION
**Version:** 1.0  
**Date:** 2026-10-28  
**Status:** DRAFT - Awaiting Owner Review  
**Author:** Antigravity Technical Team

---

## 1. OVERVIEW

### 1.1 Goal

Transform QUAN AI BRAIN memory from simple storage/retrieval to **intelligent knowledge management** with:
- Full provenance tracking (source, lineage, version)
- Automated conflict detection
- Duplicate identification
- Preview-before-apply workflow
- Integrity validation & rollback

### 1.2 Design Principles

1. **Additive-only** - Do not break existing working functionality
2. **Backward compatible** - Existing 150 knowledge_units must remain accessible
3. **Deterministic** - No LLM for core pipeline logic (only for semantic analysis if needed)
4. **Owner-controlled** - All changes require owner approval before applying
5. **Evidence-based** - Every claim must have traceable provenance

---

## 2. CURRENT STATE ANALYSIS

### 2.1 Existing Assets (from V30 Audit)

**Database (brain.db):**
- `knowledge_units` table: 150 rows (existing structured knowledge)
- `knowledge_relations` table: 210 rows (relationships)
- `episodes`, `memories`, `semantic_memory`, `candidate_knowledge`: 108K+ rows
- `memory_review_sessions`: 2 rows (V10 feature)
- `approval_cards`: 0 rows (feature unused?)

**Existing Modules:**
- `memory/deep_memory.py` (934 lines) - Core knowledge unit management
- `memory/models.py` (85 lines) - Data models with VerificationStatus, LifecycleStatus
- `memory/knowledge_ingestion.py` (399 lines) - **Already has provenance tracking!**
- `memory/knowledge_graph.py` (15.8KB) - Relationship management
- `memory/memory_quality.py` (22.5KB) - Quality assessment
- `cognition/memory_review_session.py` (877 lines) - Review workflow (V10)

**Key Finding:** V30 already has significant foundation:
- ✅ Provenance model exists (`KnowledgeProvenance` class)
- ✅ Verification states defined
- ✅ Review session workflow implemented
- ✅ Knowledge graph with relationships

### 2.2 Gaps to Fill

| Gap | Priority | Description |
|-----|----------|-------------|
| G1 | HIGH | Provenance not fully integrated across all ingestion paths |
| G2 | HIGH | No automated conflict detection engine |
| G3 | HIGH | No duplicate detection (exact + semantic) |
| G4 | MEDIUM | Review center UI limited (V10 has basic version) |
| G5 | MEDIUM | No version history/rollback mechanism |
| G6 | LOW | No integrity validation engine |
| G7 | LOW | No baseline benchmark for memory quality |

---

## 3. TARGET ARCHITECTURE

### 3.1 Knowledge Model Enhancement

**Current Model (from `models.py`):**
```python
@dataclass
class MemoryRecord:
    id: str
    memory_type: str
    content: str
    source_ref: str
    verification_status: str
    confidence_score: float
    version: int
    superseded_by: str | None
    created_at_utc: str
    updated_at_utc: str
    metadata: dict
```

**Enhanced Model (V31):**
```python
@dataclass
class KnowledgeUnit:
    # Core identity
    id: str  # UUID
    content: str  # Original text (redacted if needed)
    knowledge_type: str  # FACT, OPINION, QUESTION, RULE, PROCESS, CONCLUSION
    
    # Provenance (enhanced)
    provenance: KnowledgeProvenance
    # - source_type, source_ref, source_version
    # - ingested_at, ingested_by
    # - verification_state, verified_at, verified_by
    # - review_notes, expires_at, conflict_ids
    
    # Temporal awareness
    effective_from: str | None  # When this knowledge became effective
    effective_until: str | None  # When this knowledge expired
    observed_at: str | None  # When the event was observed (if different from ingested)
    
    # Relationships
    supports: list[str]  # IDs of knowledge this supports
    contradicts: list[str]  # IDs of knowledge this contradicts
    derived_from: list[str]  # IDs this was derived from
    depends_on: list[str]  # IDs this depends on
    
    # Versioning
    version: int
    version_history: list[VersionEntry]
    superseded_by: str | None
    superseded_at: str | None
    
    # Status
    lifecycle_status: str  # ACTIVE, SUPERSEDED, ARCHIVED, QUARANTINED
    quality_score: float  # 0-1, computed from multiple factors
    
    # Metadata
    tags: list[str]
    project_scope: str
    created_at: str
    updated_at: str
```

### 3.2 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE INGESTION PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Source] → INGEST → VALIDATE → PARSE → NORMALIZE → DEDUP →    │
│              ↓                                                   │
│          CONFLICT_DETECT → QUALITY_SCORE → PROVENANCE_BUILD →  │
│              ↓                                                   │
│          OWNER_PREVIEW → [APPROVE/REJECT] → APPLY → VERIFY     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pipeline Stages:**

1. **INGEST** - Read from source (file, API, conversation)
2. **VALIDATE** - Check format, permissions, redaction
3. **PARSE** - Extract structured data (deterministic rules)
4. **NORMALIZE** - Standardize format, language, encoding
5. **DEDUP** - Check for exact + semantic duplicates
6. **CONFLICT_DETECT** - Compare against existing knowledge
7. **QUALITY_SCORE** - Compute confidence based on source, evidence
8. **PROVENANCE_BUILD** - Create full lineage record
9. **OWNER_PREVIEW** - Show owner proposed changes
10. **APPROVE/REJECT** - Owner decision
11. **APPLY** - Write to database (if approved)
12. **VERIFY** - Integrity check after write

### 3.3 Module Structure

```
src/quan_ai_brain/memory/
├── provenance_tracker.py       [NEW] - Full lineage tracking
├── knowledge_pipeline.py       [ENHANCE] - Orchestrate pipeline
├── conflict_detector.py        [NEW] - Detect contradictions
├── duplicate_detector.py       [NEW] - Exact + semantic dedup
├── review_center.py            [ENHANCE] - Owner review interface
├── version_control.py          [NEW] - Version history & rollback
├── integrity_checker.py        [NEW] - Post-write validation
├── benchmark_engine.py         [NEW] - Memory quality benchmarks
├── models.py                   [EXISTING] - Enhanced data models
└── deep_memory.py              [EXISTING] - Core storage (unchanged)
```

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Foundation (Week 1)

**Day 1-2: Enhanced Models**
- [ ] Extend `models.py` with new fields
- [ ] Create migration script for existing 150 knowledge_units
- [ ] Write tests for model changes

**Day 3-4: Provenance Tracker**
- [ ] Implement `provenance_tracker.py`
- [ ] Integrate with existing ingestion paths
- [ ] Write unit tests

**Day 5-7: Knowledge Pipeline**
- [ ] Implement `knowledge_pipeline.py` (orchestrator)
- [ ] Connect existing components
- [ ] Add pipeline logging
- [ ] Write integration tests

### Phase 2: Intelligence (Week 2)

**Day 8-10: Conflict Detection**
- [ ] Implement `conflict_detector.py`
- [ ] Define conflict types (semantic, temporal, logical)
- [ ] Implement detection algorithms
- [ ] Write tests with known conflict cases

**Day 11-12: Duplicate Detection**
- [ ] Implement `duplicate_detector.py`
- [ ] Exact match (hash-based)
- [ ] Semantic similarity (embedding-based)
- [ ] Write tests

### Phase 3: Review & Control (Week 3)

**Day 13-15: Review Center Enhancement**
- [ ] Enhance `review_center.py`
- [ ] Add conflict visualization
- [ ] Add duplicate grouping
- [ ] Add preview diff view
- [ ] Write UI tests

**Day 16-17: Version Control**
- [ ] Implement `version_control.py`
- [ ] Version history tracking
- [ ] Rollback mechanism
- [ ] Write recovery tests

### Phase 4: Validation (Week 4)

**Day 18-19: Integrity Checker**
- [ ] Implement `integrity_checker.py`
- [ ] Post-write validation
- [ ] Relationship consistency checks
- [ ] Write tests

**Day 20-21: Benchmark Engine**
- [ ] Implement `benchmark_engine.py`
- [ ] Define metrics (quality, coverage, consistency)
- [ ] Run baseline benchmark
- [ ] Create benchmark report

---

## 5. DATABASE SCHEMA CHANGES

### 5.1 New Tables

```sql
-- Version history for knowledge units
CREATE TABLE knowledge_version_history (
    id TEXT PRIMARY KEY,
    knowledge_unit_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    changed_fields TEXT NOT NULL,  -- JSON array of field names
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY (knowledge_unit_id) REFERENCES knowledge_units(id)
);

-- Provenance events (immutable log)
CREATE TABLE provenance_events (
    id TEXT PRIMARY KEY,
    knowledge_unit_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- INGESTED, VERIFIED, SUPERSEDED, ARCHIVED, etc.
    event_data TEXT NOT NULL,  -- JSON payload
    occurred_at TEXT NOT NULL,
    occurred_by TEXT NOT NULL,
    FOREIGN KEY (knowledge_unit_id) REFERENCES knowledge_units(id)
);

-- Conflict records
CREATE TABLE knowledge_conflicts (
    id TEXT PRIMARY KEY,
    knowledge_unit_1_id TEXT NOT NULL,
    knowledge_unit_2_id TEXT NOT NULL,
    conflict_type TEXT NOT NULL,  -- SEMANTIC, TEMPORAL, LOGICAL
    conflict_description TEXT,
    detected_at TEXT NOT NULL,
    resolution_status TEXT NOT NULL,  -- UNRESOLVED, RESOLVED, IGNORED
    resolution_decision TEXT,
    resolved_by TEXT,
    resolved_at TEXT,
    FOREIGN KEY (knowledge_unit_1_id) REFERENCES knowledge_units(id),
    FOREIGN KEY (knowledge_unit_2_id) REFERENCES knowledge_units(id)
);

-- Duplicate groups
CREATE TABLE duplicate_groups (
    id TEXT PRIMARY KEY,
    group_type TEXT NOT NULL,  -- EXACT, SEMANTIC
    similarity_score REAL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL  -- OPEN, MERGED, IGNORED
);

CREATE TABLE duplicate_group_members (
    group_id TEXT NOT NULL,
    knowledge_unit_id TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL,  -- Which one to keep
    FOREIGN KEY (group_id) REFERENCES duplicate_groups(id),
    FOREIGN KEY (knowledge_unit_id) REFERENCES knowledge_units(id)
);
```

### 5.2 Schema Migration Strategy

1. **Backup first** - Create `brain_pre_v31_backup.db`
2. **Additive changes only** - CREATE NEW TABLES, no ALTER existing
3. **Migration script** - Populate new tables from existing data
4. **Rollback script** - Drop new tables if needed
5. **Test migration** - Run on copy before production

---

## 6. API ENDPOINTS

### 6.1 New Endpoints

```
GET    /api/memory/provenance/{unit_id}       - Get full provenance chain
GET    /api/memory/conflicts                  - List all detected conflicts
POST   /api/memory/conflicts/{id}/resolve     - Resolve a conflict
GET    /api/memory/duplicates                 - List duplicate groups
POST   /api/memory/duplicates/{id}/merge      - Merge duplicates
GET    /api/memory/versions/{unit_id}         - Get version history
POST   /api/memory/versions/{unit_id}/rollback - Rollback to version
POST   /api/memory/integrity/check            - Run integrity check
POST   /api/memory/benchmark                  - Run benchmark
GET    /api/memory/benchmark/latest           - Get latest benchmark results
```

### 6.2 Enhanced Endpoints

```
POST   /api/memory/ingest                     - Now returns preview before apply
GET    /api/memory/review/sessions            - Enhanced with conflict/duplicate info
POST   /api/memory/review/respond             - Now supports conflict resolution
```

---

## 7. TEST STRATEGY

### 7.1 Test Categories

**Unit Tests:**
- Model serialization/deserialization
- Provenance tracking accuracy
- Conflict detection algorithms
- Duplicate detection accuracy
- Version control operations

**Integration Tests:**
- Full pipeline execution
- Review workflow end-to-end
- Rollback scenarios
- Migration scripts

**Benchmark Tests:**
- Memory quality metrics
- Retrieval accuracy
- Conflict detection rate
- Duplicate detection rate

### 7.2 Test Data

Create synthetic test datasets:
- `test_data/knowledge_with_provenance.json`
- `test_data/knowledge_conflicts.json`
- `test_data/knowledge_duplicates.json`
- `test_data/version_history_test.json`

---

## 8. RISK ASSESSMENT

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R1: Migration breaks existing data | HIGH | LOW | Backup + rollback script + test on copy |
| R2: Conflict detection false positives | MEDIUM | MEDIUM | Owner review required before auto-action |
| R3: Performance degradation | MEDIUM | MEDIUM | Benchmark before/after, index optimization |
| R4: Existing 150 KUs not migrated | HIGH | LOW | Automated migration + manual verification |
| R5: Review UI too complex | LOW | MEDIUM | Iterative design, owner feedback |

---

## 9. ACCEPTANCE CRITERIA (V31)

### 9.1 Functional Criteria

- [ ] **V31-01** - Provenance traceable for all knowledge units
- [ ] **V31-02** - Duplicate detection (exact + semantic) working
- [ ] **V31-03** - Conflict detection working with 3 conflict types
- [ ] **V31-04** - Review center shows conflicts/duplicates/versions
- [ ] **V31-05** - Decision logging for all owner actions
- [ ] **V31-06** - Integrity checks pass after all operations
- [ ] **V31-07** - Baseline benchmark established
- [ ] **V31-08** - Existing memory functions not broken (regression tests pass)

### 9.2 Non-Functional Criteria

- [ ] **V31-NF1** - No data loss during migration
- [ ] **V31-NF2** - All new tables have indexes for query performance
- [ ] **V31-NF3** - Pipeline processing time < 5 seconds per knowledge unit
- [ ] **V31-NF4** - Rollback completes within 30 seconds

---

## 10. DECISION LOG

| Date | Decision | Rationale | Alternative Considered |
|------|----------|-----------|------------------------|
| 2026-10-28 | Additive-only schema changes | Preserve existing working data | ALTER tables (risky) |
| 2026-10-28 | Deterministic pipeline (no LLM) | Reproducible, auditable | LLM-based parsing (less reliable) |
| 2026-10-28 | Owner approval required for all changes | Safety-first,符合 MASTER PROMPT | Auto-apply low-risk changes |

---

## 11. NEXT STEPS

1. **Owner Review** - Quanpt1 reviews this design document
2. **Approval** - Quanpt1 approves design or requests changes
3. **Implementation** - Begin Phase 1 (Foundation)
4. **Weekly Updates** - Report progress every 3-4 days
5. **Gate Review** - Present all evidence for V31 acceptance

---

**Document Status:** DRAFT - Awaiting Owner Review  
**Last Updated:** 2026-10-28  
**Next Review:** After owner feedback