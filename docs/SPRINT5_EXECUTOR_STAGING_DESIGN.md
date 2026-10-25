# QUAN AI BRAIN — Production Executor Staging & Isolation Architecture Design

> **Document Status:** SPRINT 5 ARCHITECTURAL DESIGN SPECIFICATION  
> **Milestone:** Sprint 5 — Persistent Governance State + Isolated Executor Staging  
> **Execution State:** **INERT / DRY-RUN SIMULATION ONLY (ZERO PRODUCTION EXECUTION)**  
> **Authority:** Non-negotiable safety rules defined in [AGENTS.md](file:///e:/AI/QUAN%20AI%20BRAIN/AGENTS.md).

---

## 1. Executive Summary & Core Principle

QUAN AI BRAIN is being developed as an auditable, safety-first Digital Executive Assistant. In accordance with invariant project governance rules:
- **Zero Production Execution in Sprint 5:** No real production executors, write APIs, Windows 24/7 background services, or autonomous hardware/UPS controllers are activated or created.
- **Fail-Closed Governance:** Any missing, damaged, unreadable, or unverified governance state causes all execution pipelines to immediately fail closed.
- **Strict Boundary Confinement:** All future execution will be strictly confined within the workspace or to explicitly authorized external adapters reviewed and signed off by the owner.

This document defines the comprehensive architecture for the future **Isolated Production Executor**, specifying its isolation boundaries, one-way planner-executor communication, pre-action re-verification, emergency halt mechanisms, and idempotency guarantees.

---

## 2. Architecture & Components of the Future Executor

```mermaid
graph TD
    subgraph "Cognitive & Planning Layer (Read-Only / Compute)"
        C[ExecutiveCoordinator] --> P[TaskPlan / TaskSteps]
    end

    subgraph "Governance & Verification Barrier"
        P --> V[AuthenticatedApprovalVerifier]
        P --> AG[ApprovalGate]
        P --> DR[DelegationRegistry]
        P --> PE[PolicyEngine R0-R5]
        AG <--> GS[(GovernanceStateStore - SQLite WAL)]
        DR <--> GS
        V <--> GS
    end

    subgraph "Isolation & Staging Boundary"
        PE --> IS[IsolatedStagingExecutor (Inert Simulation)]
        IS --> AR[Pre-Execution Re-verification Guard]
        AR --> ES[Emergency Halt Check (STOP / FREEZE)]
    end

    subgraph "Production Executor (Future - Currently Hard-Blocked)"
        ES -.->|PENDING_OWNER_SIGNOFF| PE_STAGE[Future Production Worker]
        PE_STAGE -.->|Strict Sandbox| OS[OS Process / Hardware - BLOCKED]
    end
```

### Component Breakdown
1. **ExecutiveCoordinator (Planner):** Generates structured `TaskPlan` DAGs. Strictly zero-execution; cannot execute tools or invoke shell scripts.
2. **Governance Barrier:**
   - `PolicyEngine`: Invariant risk evaluation (R0-R3 permitted with constraints; R4 requires verified owner approval; R5 hard-blocked).
   - `ApprovalGate`: Evaluates cryptographic owner approvals; enforces action fingerprint binding and single-use token consumption.
   - `DelegationRegistry`: Enforces 10 bounded autonomy conditions; ceiling max R2; non-delegatable R4/R5.
   - `AuthenticatedApprovalVerifier`: Validates HMAC-SHA256 signatures, SMS OTP challenges, and mandatory Dual-Factor for R4.
   - `GovernanceStateStore`: SQLite WAL persistent database storing emergency STOP/FREEZE state, consumed approvals, nonces, and revocations across process restarts.
3. **IsolatedStagingExecutor (Current):** Dry-run simulation engine that validates all parameters, pre-conditions, and governance permissions without touching any production resource.
4. **Future Production Executor (Future - Inert):** Containerized or sub-process worker isolated via OS-level sandbox (AppContainer / Windows Sandbox / Job Object limits).

---

## 3. Isolation Boundaries

The isolation architecture implements concentric defensive rings:

| Ring | Layer | Capabilities | Boundary Constraints |
| :--- | :--- | :--- | :--- |
| **Ring 0** | Core Planning | Prompt analysis, memory retrieval, DAG creation | Zero side effects; read-only RAM |
| **Ring 1** | Governance Engine | Policy check, cryptographic signature verify, persistent state check | Atomic transactions, fail-closed, no network |
| **Ring 2** | Sandbox Staging | Dry-run validation, path resolution via PathGuard, parameter linting | Cannot execute binaries, cannot write external files |
| **Ring 3** | Production Worker *(Future)* | Strictly bounded tool handler invocation | Restricted Job Object, capped CPU/RAM, locked to workspace |

### External Systems Protection
The executor has **zero access** to:
- `E:\AI\DATA CENTER AI OPERATING SYSTEM` (DC-COMMAND / CLAE)
- `E:\AI\BAT-AI-2026-Repo\battery-ai-\os_kernel` (Kernel L3)
- `E:\AI\Skill\SKILL_BAT_AI`
- `E:\AI\battery-ai-\BATTERY_AI_V4`
- `E:\AI\BOT`
- External production databases, VDCIM, NetChat, and UPS/electrical controllers.

---

## 4. Controlled Communication Between Planner and Executor

To prevent prompt injection or rogue LLM outputs from directly hijacking execution:
1. **Asynchronous One-Way Staging Queue:**
   - Planner produces a declarative `TaskStep` serialized as immutable JSON.
   - Planner cannot invoke executor directly; it submits a `ExecutionStageRequest` to the queue.
2. **No Dynamic Code or Shell Scripts:**
   - Arbitrary PowerShell, cmd.exe, or Python `eval()` / `exec()` are permanently barred.
   - Only registered, declarative `ToolDefinition` handlers with strict parameter type schemas are permitted.
3. **Separation of Concerns:**
   - The planner proposes *what* needs to be done.
   - The governance gate determines *if* it is permitted.
   - The executor only determines *how* the pre-approved handler is safely invoked.

---

## 5. Pre-Action Re-Verification Guard

A critical vulnerability in distributed execution is the **Time-of-Check to Time-of-Use (TOCTOU)** window. If an approval is granted at $T_0$, but execution occurs at $T_1$, an owner may have issued a STOP or revoked the approval in the interval.

To eliminate TOCTOU risks:
1. Immediately prior to invoking any handler (Step 8 of execution pipeline), the executor performs an atomic re-verification:
   - Re-checks `GovernanceStateStore.get_emergency_state()`: if STOP or FREEZE, aborts immediately.
   - Re-checks `GovernanceStateStore.get_approval()`: verifies that the approval has not been revoked or expired between queueing and execution.
   - Re-checks `GovernanceStateStore.is_nonce_consumed()`: verifies no race condition has consumed the nonce.
2. The consumption of the approval and marking of the nonce occur within an atomic database transaction.

---

## 6. Emergency Stop, Freeze, and Revocation Controls

### Prioritization Hierarchy
$$\text{STOP} \succ \text{FREEZE} \succ \text{REVOKE} \succ \text{NORMAL}$$

1. **STOP State:**
   - Unconditionally aborts all queued tasks and in-flight staging.
   - Persisted in `GovernanceStateStore` (`emergency_states` table).
   - Survives process crashes, host reboots, and service restarts.
   - Can only be cleared by an authenticated `OWNER` command.
2. **FREEZE State:**
   - Disallows new action submissions; permits read-only status inquiries.
   - Persisted across restarts.
3. **REVOKE Action:**
   - Immediate invalidation of specific `OwnerApproval` or `DelegationGrant`.
   - Written directly to SQLite WAL store; subsequent checks fail-closed.

---

## 7. Input and Postcondition Verification

1. **Input Schema Validation:**
   - Strict typing via `ToolRegistry.validate_params`.
   - Path resolution through `PathGuard`: any path attempting `..` traversal or targeting `.env`, `.pem`, `.key`, `id_rsa`, credentials, or SQLite databases is blocked.
2. **Pre-condition Assertion:**
   - Check resource availability (e.g., target file must exist for read; target file must not exist for write_new).
3. **Post-condition Assertion:**
   - Check expected output format, byte caps (e.g. read capped at 100KB), and non-empty deliverables.

---

## 8. Idempotency, Timeouts, and Resource Limits

1. **Idempotency Keys:**
   - Each action envelope includes an idempotency key derived from `SHA-256(action_fingerprint + nonce)`.
   - If a network or system interruption occurs, re-executing with the same key returns the cached execution result without re-running the underlying handler.
2. **Timeout Enforcement:**
   - Hard execution timeout capped per tool (default 10 seconds for R0-R1; max 30 seconds for R2).
   - Python `subprocess` or thread timeouts prevent hanging processes.
3. **Resource Caps:**
   - Memory allocation capped at 256MB per worker process.
   - File read limited to 100KB per invocation.
   - Maximum write size capped to prevent disk exhaustion attacks.

---

## 9. Evidentiary Audit Trail

All governance decisions and staging results are logged to two independent audit targets:
1. **Append-Only JSONL Audit Ledger (`logs/audit.jsonl`):**
   - High-throughput chronological trace of every event.
   - All credentials, tokens, and sensitive arguments sanitized via `redact_value()`.
2. **Persistent Relational Ledger (`governance_events` table in SQLite):**
   - Queryable audit trail linking `approval_id`, `grant_id`, `nonce`, `risk_level`, and `outcome`.

---

## 10. Checkpoints and State Recovery

1. **SQLite WAL (Write-Ahead Logging):**
   - Provides ACID compliance and crash recovery. In the event of a sudden power loss, SQLite automatically rolls back uncommitted transactions upon reopen.
2. **Fail-Closed on Store Unavailability:**
   - If the database file is missing, locked, or corrupt, the store raises `GovernanceStateCorruptError`.
   - The sandbox catches this and defaults to **hard denial**.
   - Under no circumstances does the system assume a "clean" or "permissive" state when the database cannot be verified.

---

## 11. Prerequisites for Production Execution

Before any real production executor may be activated in future milestones, all of the following conditions must be fulfilled:
1. **Manual Owner Review:** Explicit sign-off on [docs/SPRINT5_DESIGN_SIGNOFF.md](file:///e:/AI/QUAN%20AI%20BRAIN/docs/SPRINT5_DESIGN_SIGNOFF.md).
2. **Cryptographic Identity Anchor:** Real owner public key or HMAC secret key securely loaded into secure storage (DPAPI / Credential Guard).
3. **OS-Level Process Isolation:** Windows Job Object or AppContainer configuration validated by penetration tests.
4. **Complete Regression Passing:** 100% pass rate on all unit, integration, and security test suites.
5. **No Open Critical Deficiencies:** Zero unresolved security flaws in handoff reports.

---

## 12. Residual Risks & Mitigation Matrix

| ID | Residual Risk | Severity | Mitigation in Architecture |
| :--- | :--- | :---: | :--- |
| **R-01** | Power loss during tool execution | Medium | Atomic SQLite transaction for state consumption; idempotency key prevents duplicate side-effects on resume |
| **R-02** | Host filesystem tampering of DB | High | Database integrity verification (`PRAGMA integrity_check`) on startup; fail-closed on corrupt DB |
| **R-03** | Prompt injection trying to bypass R4 | Critical | Hardcoded PolicyEngine gate rejects any R4 without Dual-Factor; R5 is unconditionally hard-blocked |
| **R-04** | Accidental production service autostart | High | Zero Windows Service or background daemons installed; entrypoints remain purely CLI and on-demand |
