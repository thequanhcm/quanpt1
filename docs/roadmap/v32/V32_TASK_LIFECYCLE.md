# V32 Task Lifecycle Design
**Version:** 1.0  
**Date:** 2026-10-28  
**Status:** DRAFT - Based on Existing Implementation

---

## 1. CURRENT STATE MODEL

### 1.1 Existing TaskStatus Enum

```python
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    BLOCKED = "BLOCKED"
```

### 1.2 Existing SupervisorState Enum

```python
class SupervisorState(str, Enum):
    STARTING = "STARTING"
    HEALTH_CHECK = "HEALTH_CHECK"
    READY = "READY"
    IDLE = "IDLE"
    SELECTING_TASK = "SELECTING_TASK"
    PLANNING = "PLANNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RUNNING_AUTHORIZED_TASK = "RUNNING_AUTHORIZED_TASK"
    VERIFYING_RESULT = "VERIFYING_RESULT"
    LEARNING = "LEARNING"
    PREPARING_UPGRADE_PROPOSAL = "PREPARING_UPGRADE_PROPOSAL"
    WAITING_FOR_OWNER = "WAITING_FOR_OWNER"
    RECOVERING = "RECOVERING"
    SAFE_MODE = "SAFE_MODE"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
```

### 1.3 Existing PipelineStage Enum

```python
class PipelineStage(str, Enum):
    UNDERSTAND = "UNDERSTAND"
    DECOMPOSE = "DECOMPOSE"
    DISCOVER = "DISCOVER"
    PLAN = "PLAN"
    LEARN = "LEARN"
    BUILD = "BUILD"
    TEST = "TEST"
    ANALYZE = "ANALYZE"
    VERIFY = "VERIFY"
    ADVISE = "ADVISE"
    REUSE = "REUSE"
```

---

## 2. PROPOSED ENHANCEMENTS

### 2.1 Enhanced TaskStatus

**No changes needed** - Current 9 states are adequate.

**Proposed additional states (optional):**
- `PAUSED` - Temporarily paused (owner request)
- `RETRY_PENDING` - Waiting for retry
- `NEEDS_REVIEW` - Needs manual review

**Decision:** Keep current states, use `BLOCKED` for paused/review cases

### 2.2 Task State Model Enhancement

**Current fields in TaskRecord:**
```python
task_id: str
correlation_id: str
idempotency_key: str
goal: str
risk_level: str
autonomy_level: AutonomyLevel
status: TaskStatus
created_at_utc: str
updated_at_utc: str
acceptance_criteria: list[str]
approved_scope: list[str]
completed_at_utc: str | None
resource_budget: dict[str, Any]
retry_count: int
max_retries: int
error_message: str | None
evidence_refs: list[str]
result_payload: dict[str, Any]
checkpoint_data: dict[str, Any]
```

**Proposed additional fields:**
```python
timeout_at_utc: str | None  # Task deadline
current_step_id: str | None  # Currently executing step
last_checkpoint_id: str | None  # Last valid checkpoint
verification_result: str | None  # VERIFIED/PARTIALLY_VERIFIED/FAILED
policy_version: str  # Policy version at task creation
runtime_version: str  # Runtime version at task creation
```

### 2.3 Task Step Model Enhancement

**Current fields in TaskStepRecord:**
```python
step_id: str
task_id: str
sequence: int
name: str
description: str
risk_level: int
status: str
requires_approval: bool
dependencies: list[str]
expected_output: str
verification_method: str
result_payload: dict[str, Any]
error_message: str | None
started_at_utc: str | None
completed_at_utc: str | None
```

**Proposed additional fields:**
```python
tool_id: str | None  # Tool used for this step
tool_input_hash: str | None  # For idempotency
timeout_at_utc: str | None  # Step deadline
retry_count: int  # Step-specific retry count
checkpoint_id: str | None  # Checkpoint before this step
policy_decision_id: str | None  # Policy decision reference
```

---

## 3. STATE TRANSITION RULES

### 3.1 Valid Transitions

```
PENDING → IN_PROGRESS (when selected for execution)
PENDING → CANCELLED (when cancelled before start)

IN_PROGRESS → WAITING_APPROVAL (when approval needed)
IN_PROGRESS → FAILED (when error occurs)
IN_PROGRESS → CANCELLED (when cancelled)
IN_PROGRESS → BLOCKED (when blocked by policy)

WAITING_APPROVAL → APPROVED (when owner approves)
WAITING_APPROVAL → FAILED (when approval rejected)
WAITING_APPROVAL → CANCELLED (when cancelled)

APPROVED → IN_PROGRESS (when execution resumes)

COMPLETED ← VERIFYING (when verification passes)
FAILED ← VERIFYING (when verification fails)

CANCELLED ← any state (when cancelled)
BLOCKED ← any state (when policy blocks)
OUTCOME_UNKNOWN ← IN_PROGRESS (when outcome uncertain)
```

### 3.2 Invalid Transitions (Must Reject)

```
PENDING → COMPLETED (must execute first)
IN_PROGRESS → COMPLETED (must verify first)
WAITING_APPROVAL → IN_PROGRESS (must be approved first)
COMPLETED → IN_PROGRESS (cannot restart completed)
FAILED → IN_PROGRESS (must create new task)
```

---

## 4. CHECKPOINT MODEL

### 4.1 Checkpoint Structure

```python
@dataclass
class Checkpoint:
    checkpoint_id: str
    task_id: str
    step_id: str | None
    timestamp: str
    runtime_version: str
    task_state_snapshot: dict[str, Any]
    completed_steps: list[dict[str, Any]]
    pending_steps: list[dict[str, Any]]
    approval_state: str | None
    policy_version: str
    integrity_checksum: str | None
```

### 4.2 Checkpoint Strategy

**When to checkpoint:**
1. After task creation (PENDING)
2. After planning complete (PLANNED)
3. Before each tool call (for idempotency)
4. After each tool result (for recovery)
5. Before waiting for approval
6. After verification complete

**Checkpoint frequency:** Every significant state change

---

## 5. RECOVERY STRATEGY

### 5.1 Recovery Process

1. **On startup:** Load all tasks not in terminal state
2. **Validate:** Check checkpoint integrity
3. **Classify:** Determine recovery path for each task
4. **Verify:** Check external action status if needed
5. **Resume:** Continue from last valid checkpoint
6. **Log:** Record recovery event

### 5.2 Recovery Scenarios

| Scenario | Recovery Action |
|----------|----------------|
| Task in IN_PROGRESS, no recent checkpoint | Mark NEEDS_REVIEW |
| Task in WAITING_APPROVAL | Resume waiting |
| Task after tool call, result not saved | Re-check tool status |
| Task before tool call | Safe to retry |
| Checkpoint corrupted | Mark FAILED, log error |

---

## 6. ACCEPTANCE CRITERIA

- [ ] Task lifecycle states match design
- [ ] State transitions enforced
- [ ] Checkpoint created at key points
- [ ] Recovery from checkpoint works
- [ ] Corrupted checkpoint detected
- [ ] Approval cannot be bypassed
- [ ] Tests for all recovery scenarios

---

**Next:** Implement Recovery Manager and add recovery tests