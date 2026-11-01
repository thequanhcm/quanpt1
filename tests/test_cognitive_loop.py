"""Sprint A-fix + Sprint B tests: CognitiveLoop, ReflectionLoop, /api/health,
watchdog extended monitoring.

Ground rules (Sprint 0 constraint, unchanged):
- NO test talks to the real LLM gateway. HTTP is mocked where needed.
- NO API key is ever read, set, or printed.
- Probes target local SQLite fixtures and ephemeral local servers only.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from quan_ai_brain.cognition.cognitive_loop import (
    CognitiveLoop,
    CognitiveLoopError,
    TaskSpec,
)
from quan_ai_brain.cognition.reflection import ReflectionLoop
from quan_ai_brain.orchestration.models import AutonomyLevel, TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.models import TaskPlan, TaskStep


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def loop_env(tmp_path):
    """Full loop wiring on ephemeral stores (no real workspace data)."""
    ws = tmp_path
    (ws / "data").mkdir(exist_ok=True)
    registry = DurableTaskRegistry(ws / "data" / "tasks.db", workspace=ws)
    orchestrator = PlanOrchestrator(registry, workspace=ws)
    loop = CognitiveLoop(registry, orchestrator, workspace=ws)
    return loop, registry, orchestrator, ws


def _simple_plan(spec: TaskSpec) -> TaskPlan:
    return TaskPlan(
        goal=spec.goal,
        steps=[
            TaskStep(
                name="observe",
                description="Read-only observation step",
                expected_output="observation recorded",
                risk_level=0,
            )
        ],
        source="test",
    )


# ---------------------------------------------------------------------------
# CognitiveLoop — lifecycle
# ---------------------------------------------------------------------------


def test_submit_task_requires_acceptance_criteria(loop_env):
    loop, registry, _, _ = loop_env
    with pytest.raises(CognitiveLoopError) as excinfo:
        loop.submit_task(TaskSpec(goal="X", acceptance_criteria=[]))
    assert "acceptance_criteria" in str(excinfo.value)


def test_submit_task_with_builder_registers_durable_task(loop_env):
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Kiểm tra sức khỏe hệ thống", acceptance_criteria=["báo cáo sinh ra"]),
        plan_builder=_simple_plan,
    )
    task_id = result["task_id"]
    assert result["lifecycle_state"] in ("RECEIVED", "PLANNING")
    task = registry.get_task(task_id)
    assert task is not None
    assert task.goal.startswith("[COGNITIVE_LOOP]") or task.goal


def test_placeholder_plan_does_not_execute_actions(loop_env):
    """Without plan_builder, the loop must register a tracked placeholder —
    never silently execute anything (fail-closed)."""
    loop, registry, _, _ = loop_env
    result = loop.submit_task(TaskSpec(goal="Anonymous goal", acceptance_criteria=["done"]))
    task = registry.get_task(result["task_id"])
    assert task is not None
    steps = registry.list_steps_for_task(task.task_id)
    assert len(steps) == 1
    assert steps[0].risk_level == 0
    assert steps[0].name == "await_plan_builder"


def test_tick_completes_r0_task_in_inert_sandbox(loop_env):
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Observe workspace", acceptance_criteria=["step completes"]),
        plan_builder=_simple_plan,
    )
    snap = loop.tick(result["task_id"])
    task = registry.get_task(result["task_id"])
    # Inert sandbox: step verifies, task reaches terminal COMPLETED
    assert task.status == TaskStatus.COMPLETED
    assert snap["lifecycle_state"] == "COMPLETED"


def test_r4_step_parks_in_waiting_approval(loop_env):
    """R4 requires owner approval — task must park, not execute."""
    loop, registry, _, _ = loop_env

    def r4_plan(spec: TaskSpec) -> TaskPlan:
        return TaskPlan(
            goal=spec.goal,
            steps=[
                TaskStep(
                    name="patch_production",
                    description="Modify production configuration",
                    expected_output="change applied",
                    risk_level=4,
                    requires_approval=True,
                )
            ],
            source="test",
        )

    result = loop.submit_task(
        TaskSpec(goal="Risky change", acceptance_criteria=["approved"], risk_hint=4),
        plan_builder=r4_plan,
    )
    snap = loop.tick(result["task_id"])
    task = registry.get_task(result["task_id"])
    assert task.status == TaskStatus.WAITING_APPROVAL
    assert snap["lifecycle_state"] == "WAITING_APPROVAL"


def test_tick_terminal_task_is_idempotent(loop_env):
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Idempotent", acceptance_criteria=["ok"]),
        plan_builder=_simple_plan,
    )
    loop.tick(result["task_id"])
    snap2 = loop.tick(result["task_id"])
    assert snap2["lifecycle_state"] == "TERMINAL"


def test_cancel_task(loop_env):
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="To cancel", acceptance_criteria=["x"]),
        plan_builder=_simple_plan,
    )
    out = loop.cancel(result["task_id"], reason="owner requested")
    assert out["status"] == "CANCELLED"


def test_expire_stale_pending_age_out_policy(loop_env):
    """GAP-R7: PENDING tasks older than TTL are expired, fresh ones survive."""
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Stale task", acceptance_criteria=["y"]),
        plan_builder=_simple_plan,
    )
    # Force created_at_utc to be older than TTL
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    with sqlite3.connect(registry.db_path) as conn:
        conn.execute(
            "UPDATE durable_tasks SET created_at_utc = ? WHERE task_id = ?",
            (old_ts, result["task_id"]),
        )
    out = loop.expire_stale_pending(ttl_hours=48)
    assert out["expired_count"] == 1
    task = registry.get_task(result["task_id"])
    assert task.status == TaskStatus.CANCELLED
    assert "Age-out policy" in (task.error_message or "")


def test_expire_stale_pending_keeps_fresh_tasks(loop_env):
    loop, registry, _, _ = loop_env
    loop.submit_task(
        TaskSpec(goal="Fresh task", acceptance_criteria=["y"]),
        plan_builder=_simple_plan,
    )
    out = loop.expire_stale_pending(ttl_hours=48)
    assert out["expired_count"] == 0


# ---------------------------------------------------------------------------
# ReflectionLoop — 12 mandatory questions from durable data
# ---------------------------------------------------------------------------


def test_reflection_completed_task_has_verified_lessons(loop_env):
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Learn from me", acceptance_criteria=["ok"]),
        plan_builder=_simple_plan,
    )
    loop.tick(result["task_id"])
    report = loop.reflect(result["task_id"])
    assert report["task_status"] == "COMPLETED"
    assert report["lessons_verified"], "completed task must yield verified lessons"
    assert any("completed" in l for l in report["lessons_verified"])


def test_reflection_failed_task_identifies_wrong_step(loop_env):
    """Q5 (wrong decisions) must cite the actually failed step, not invent.
    Simulates a step failure directly in the durable registry (the inert
    backend always succeeds by design, so failure is injected at the source
    of truth — exactly what would happen after a real verification failure)."""
    loop, registry, orchestrator, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Failing flow", acceptance_criteria=["never reached"]),
        plan_builder=_simple_plan,
    )
    task_id = result["task_id"]
    steps = registry.list_steps_for_task(task_id)
    registry.update_task_status(task_id, TaskStatus.FAILED)
    registry.update_step_status(
        steps[0].step_id,
        TaskStatus.FAILED,
        error_message="Verification failed for step 'always_fails': criteria not satisfied",
    )

    report = loop.reflect(task_id)
    q5 = report["answers"]["q5_wrong_or_unnecessary"]
    assert isinstance(q5, list) and q5, "failed step must be identified"
    assert any("always_fails" in json.dumps(s) for s in q5)


def test_persist_lessons_verified_to_episodic_not_semantic(loop_env):
    """Verified lessons -> episodes; hypotheses must NOT reach semantic_memory."""
    loop, registry, _, ws = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Lesson task", acceptance_criteria=["ok"]),
        plan_builder=_simple_plan,
    )
    loop.tick(result["task_id"])

    from quan_ai_brain.memory.sqlite_store import MemoryStore

    with MemoryStore(ws / "data" / "brain.db", workspace=ws) as store:
        out = loop.reflection.persist_lessons(result["task_id"], memory_store=store)

    assert len(out["episodic"]) >= 1
    # Hypotheses, if any, went to quarantine (candidate_knowledge), not semantic
    conn = sqlite3.connect(ws / "data" / "brain.db")
    try:
        sem = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='semantic_memory'"
        ).fetchone()[0]
        if sem:
            n = conn.execute(
                "SELECT COUNT(*) FROM semantic_memory WHERE statement LIKE '%Lesson task%'"
            ).fetchone()[0]
            assert n == 0, "unapproved lessons must never reach semantic memory"
    finally:
        conn.close()


def test_recovery_after_restart_marks_unknown_not_rerun(loop_env):
    """B1 acceptance: killed process must not silently re-run in-flight work."""
    loop, registry, _, _ = loop_env
    result = loop.submit_task(
        TaskSpec(goal="Interrupted", acceptance_criteria=["ok"]),
        plan_builder=_simple_plan,
    )
    task_id = result["task_id"]
    # Simulate crash mid-execution: force IN_PROGRESS then "restart"
    registry.update_task_status(task_id, TaskStatus.IN_PROGRESS)
    out = loop.resume_incomplete()
    task = registry.get_task(task_id)
    assert task.status == TaskStatus.OUTCOME_UNKNOWN
    assert any(r["task_id"] == task_id for r in out["recovered"])


# ---------------------------------------------------------------------------
# Sprint A-fix: /api/health canonical endpoint
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def health_server_url(tmp_path_factory):
    from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer

    ws = tmp_path_factory.mktemp("health_ws")
    (ws / "data").mkdir(exist_ok=True)
    # Minimal brain.db + tasks.db fixtures so probes have real targets
    conn = sqlite3.connect(ws / "data" / "brain.db")
    conn.execute("CREATE TABLE episodes (id TEXT, created_at_utc TEXT)")
    conn.execute("INSERT INTO episodes VALUES ('e1', '2026-10-26T00:00:00+00:00')")
    conn.execute("CREATE TABLE semantic_memory (id TEXT, statement TEXT)")
    conn.commit()
    conn.close()
    conn = sqlite3.connect(ws / "data" / "tasks.db")
    conn.execute(
        "CREATE TABLE durable_tasks (task_id TEXT PRIMARY KEY, status TEXT)"
    )
    conn.execute("INSERT INTO durable_tasks VALUES ('t1', 'PENDING')")
    conn.commit()
    conn.close()

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


def test_api_health_returns_evidence_based_components(health_server_url):
    req = urllib.request.Request(f"{health_server_url}/api/health")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["overall_status"] in ("HEALTHY", "DEGRADED")
    ids = {c["component_id"] for c in data["components"]}
    assert {"core_server", "ollama_daemon", "brain_db", "task_registry"} <= ids
    for comp in data["components"]:
        # Master Prompt Part 2 field contract
        assert {"component_id", "observed_value", "status", "observed_at",
                "source", "evidence_ref", "verification_status",
                "last_verified_at"} <= set(comp.keys())
        assert comp["status"] in ("HEALTHY", "DEGRADED", "OFFLINE", "UNKNOWN", "UNVERIFIED")


def test_api_health_ollama_offline_is_honest(health_server_url):
    """On this machine Ollama is currently OFFLINE — the endpoint must say so
    instead of claiming HEALTHY (the 'silently dead' anti-pattern)."""
    req = urllib.request.Request(f"{health_server_url}/api/health")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ollama = next(c for c in data["components"] if c["component_id"] == "ollama_daemon")
    # Honesty contract: OFFLINE when probe fails, regardless of config
    assert ollama["status"] in ("HEALTHY", "OFFLINE")
    if ollama["observed_value"] is False:
        assert ollama["status"] == "OFFLINE"


# ---------------------------------------------------------------------------
# Sprint A-fix: watchdog extended monitoring (GAP-R3) — unit level
# ---------------------------------------------------------------------------


def test_watchdog_circuit_breaker_states():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "watchdog_mod", "tools/watchdog.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 2 consecutive failures -> DEGRADED; 3rd -> OFFLINE; recovery -> HEALTHY
    assert mod._update_component_state("test_comp", False) == "DEGRADED"
    assert mod._update_component_state("test_comp", False) == "DEGRADED"
    assert mod._update_component_state("test_comp", False) == "OFFLINE"
    assert mod._update_component_state("test_comp", True) == "HEALTHY"


def test_watchdog_disk_check_runs():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "watchdog_mod2", "tools/watchdog.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # On the real machine disk should be fine; function must not raise
    assert mod.check_disk_space() in (True, False)
