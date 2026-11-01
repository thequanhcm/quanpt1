# V33 Improvement Engine Design
**Version:** 1.0  
**Date:** 2026-10-28  
**Status:** DRAFT

---

## 1. OVERVIEW

### 1.1 Goal

Build an **Improvement Engine** that enables QUAN AI BRAIN to:
- Transform observations into actionable improvement proposals
- Separate knowledge learning from behavior improvement from code changes
- Prioritize improvements based on impact, evidence, and risk
- Track improvement lifecycle from detection to deployment
- Ensure all improvements are tested and governed

### 1.2 Design Principles

1. **Evidence-based** - No improvement without evidence
2. **Categorized** - Separate knowledge, behavior, and code changes
3. **Prioritized** - Focus on high-impact, low-risk improvements
4. **Testable** - Every improvement must be testable
5. **Governed** - All changes require appropriate approval
6. **Reversible** - Every change must have rollback plan

---

## 2. IMPROVEMENT CATEGORIES

### 2.1 Three Distinct Streams

#### Stream 1: Knowledge Learning
**Purpose:** Add new knowledge, update existing knowledge, fix knowledge gaps

**Examples:**
- Add new fact from verified source
- Update stale knowledge
- Resolve knowledge conflict
- Fill knowledge gap

**Workflow:**
```
Observation → Research → Candidate Knowledge → Memory Review → Owner Approval → Apply
```

**Governance:** Memory Review Center, Owner approval for VERIFIED status

#### Stream 2: Behavior Improvement
**Purpose:** Improve how system operates without changing code

**Examples:**
- Adjust retrieval parameters
- Improve prompt templates
- Change planning strategy
- Adjust verification criteria
- Improve error handling
- Change tool selection logic

**Workflow:**
```
Observation → Hypothesis → Experiment Design → Run Experiment → Evaluate → Proposal → Owner Approval → Deploy
```

**Governance:** Experiment Manager, Benchmark validation, Owner approval

#### Stream 3: Code/Configuration Changes
**Purpose:** Fix bugs, add features, optimize performance

**Examples:**
- Fix bug in tool execution
- Add input validation
- Improve algorithm
- Optimize database query
- Add telemetry
- Fix workflow logic

**Workflow:**
```
Observation → Root Cause → Code Fix → Unit Tests → Integration Tests → Benchmark → Sandbox Test → Security Review → Owner Approval → Deploy → Verify
```

**Governance:** Full SDLC, Sandbox testing, Security review, Owner approval

---

## 3. IMPROVEMENT BACKLOG

### 3.1 Backlog Item Model

```python
@dataclass
class ImprovementBacklogItem:
    improvement_id: str
    problem_statement: str
    category: str  # knowledge | behavior | code
    
    # Evidence
    evidence_refs: list[str]
    evidence_count: int
    
    # Analysis
    root_cause_hypothesis: str
    confidence: float  # 0-1
    impact: str  # high | medium | low
    risk: str  # high | medium | low
    
    # Solution
    proposed_solution: str
    solution_type: str  # add_knowledge | adjust_param | fix_bug | optimize
    
    # Evaluation
    evaluation_method: str
    acceptance_criteria: list[str]
    success_metrics: dict
    
    # Risk management
    rollback_plan: str
    side_effects: list[str]
    
    # Status
    status: str  # detected | analyzed | proposed | in_progress | tested | approved | deployed | rejected
    priority: int  # 1-5
    
    # Metadata
    detected_at: str
    analyzed_by: str
    last_updated: str
```

### 3.2 Prioritization Matrix

**Priority Score = (Impact × Confidence) / (Risk + 1)**

| Priority | Score Range | Action |
|----------|-------------|--------|
| 1 (Critical) | > 3.0 | Immediate attention |
| 2 (High) | 2.0-3.0 | Address soon |
| 3 (Medium) | 1.0-2.0 | Schedule |
| 4 (Low) | 0.5-1.0 | Backlog |
| 5 (Trivial) | < 0.5 | Consider later |

---

## 4. IMPROVEMENT PIPELINE

### 4.1 Pipeline Stages

```
DETECTED → ANALYZED → PROPOSED → EXPERIMENT_DESIGN → 
EXPERIMENT_RUNNING → EVALUATING → READY_FOR_APPROVAL → 
APPROVED → IMPLEMENTING → TESTING → DEPLOYING → VERIFIED → COMPLETED
```

**Stage Transitions:**

1. **DETECTED** - Problem observed from system
2. **ANALYZED** - Root cause analyzed, hypothesis generated
3. **PROPOSED** - Solution proposed with acceptance criteria
4. **EXPERIMENT_DESIGN** - Experiment plan created
5. **EXPERIMENT_RUNNING** - Experiment executing
6. **EVALUATING** - Results being analyzed
7. **READY_FOR_APPROVAL** - Ready for owner review
8. **APPROVED** - Owner approved for implementation
9. **IMPLEMENTING** - Code/knowledge/parameter changes being made
10. **TESTING** - Tests running (unit, integration, benchmark)
11. **DEPLOYING** - Being deployed to production
12. **VERIFIED** - Post-deployment verification complete
13. **COMPLETED** - Improvement successfully deployed

### 4.2 State Machine

```python
class ImprovementStatus(str, Enum):
    DETECTED = "detected"
    ANALYZED = "analyzed"
    PROPOSED = "proposed"
    EXPERIMENT_DESIGN = "experiment_design"
    EXPERIMENT_RUNNING = "experiment_running"
    EVALUATING = "evaluating"
    READY_FOR_APPROVAL = "ready_for_approval"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    DEPLOYING = "deploying"
    VERIFIED = "verified"
    COMPLETED = "completed"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"
```

**Valid Transitions:**
- DETECTED → ANALYZED
- ANALYZED → PROPOSED or REJECTED
- PROPOSED → EXPERIMENT_DESIGN or REJECTED
- EXPERIMENT_DESIGN → EXPERIMENT_RUNNING
- EXPERIMENT_RUNNING → EVALUATING
- EVALUATING → READY_FOR_APPROVAL or REJECTED
- READY_FOR_APPROVAL → APPROVED or REJECTED
- APPROVED → IMPLEMENTING
- IMPLEMENTING → TESTING
- TESTING → DEPLOYING or REJECTED (if tests fail)
- DEPLOYING → VERIFIED
- VERIFIED → COMPLETED or ROLLED_BACK (if issues)
- Any → BLOCKED (if external dependency)
- Any → REJECTED (if not viable)

---

## 5. EXPERIMENT INTEGRATION

### 5.1 Experiment Link

Each improvement must have associated experiment:

```python
@dataclass
class ImprovementExperiment:
    improvement_id: str
    experiment_id: str
    
    # Baseline
    baseline_version: str
    baseline_metrics: dict
    
    # Candidate
    candidate_version: str
    candidate_metrics: dict
    
    # Results
    improvement_pct: float
    regression_detected: bool
    safety_violations: list[str]
    
    # Decision
    recommendation: str  # PROCEED | REJECT | NEEDS_MORE_TESTING
    confidence: float
```

### 5.2 Experiment Requirements

Before approval:
- [ ] Baseline established
- [ ] Candidate tested on same dataset
- [ ] Regression tests passed
- [ ] Safety checks passed
- [ ] Performance impact measured
- [ ] Side effects documented
- [ ] Rollback plan tested

---

## 6. GOVERNANCE INTEGRATION

### 6.1 Approval Requirements

| Category | Risk Level | Approval Required |
|----------|------------|-------------------|
| Knowledge | Low | Memory Review Center |
| Knowledge | Medium | Owner review |
| Knowledge | High | Owner approval + audit |
| Behavior | Low | Automated validation |
| Behavior | Medium | Owner review |
| Behavior | High | Owner approval + sandbox |
| Code | Any | Owner approval + full SDLC |

### 6.2 Policy Enforcement

Before any improvement can proceed:
1. Check risk level
2. Determine approval requirement
3. Verify approval exists
4. Check scope of approval
5. Verify no changes since approval
6. Log approval decision

---

## 7. IMPLEMENTATION PLAN

### 7.1 Phase 1: Backlog Management (Week 1)

**Deliverables:**
- `ImprovementBacklog` class
- `ImprovementBacklogItem` model
- Priority calculation
- Status tracking
- Query API

**Tests:**
- Test backlog creation
- Test priority calculation
- Test status transitions
- Test query API

### 7.2 Phase 2: Improvement Pipeline (Week 2)

**Deliverables:**
- `ImprovementPipeline` class
- State machine implementation
- Transition validation
- Event logging
- Integration with observation engine

**Tests:**
- Test state machine
- Test transitions
- Test event logging
- Test integration

### 7.3 Phase 3: Experiment Integration (Week 3)

**Deliverables:**
- Integration with Experiment Manager
- Baseline/candidate tracking
- Results comparison
- Recommendation generation

**Tests:**
- Test integration
- Test comparison
- Test recommendation

---

## 8. ACCEPTANCE CRITERIA

### 8.1 Functional

- [ ] Can create improvement backlog items
- [ ] Can calculate priority automatically
- [ ] Can track improvement lifecycle
- [ ] Can enforce state transitions
- [ ] Can link to experiments
- [ ] Can generate recommendations
- [ ] Can enforce approval requirements
- [ ] Can rollback improvements
- [ ] Can query by criteria
- [ ] Can export improvement report

### 8.2 Non-Functional

- [ ] All improvements have evidence
- [ ] All improvements have rollback plan
- [ ] All improvements have acceptance criteria
- [ ] All approvals are logged
- [ ] No improvement can bypass governance
- [ ] Can distinguish knowledge/behavior/code changes

---

## 9. RISK ASSESSMENT

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Improper prioritization | MEDIUM | MEDIUM | Clear formula, owner review |
| Insufficient evidence | HIGH | MEDIUM | Require evidence count |
| Skipping approval | CRITICAL | LOW | Backend enforcement |
| No rollback plan | HIGH | MEDIUM | Require rollback plan |
| Side effects unknown | MEDIUM | HIGH | Thorough testing |

---

## 10. NEXT STEPS

1. Implement `ImprovementBacklogItem` model
2. Implement `ImprovementBacklog` class
3. Implement priority calculation
4. Implement state machine
5. Integrate with observation engine
6. Write tests
7. Run baseline tests

---

**Document Status:** DRAFT  
**Last Updated:** 2026-10-28  
**Next Review:** After Phase 1 implementation