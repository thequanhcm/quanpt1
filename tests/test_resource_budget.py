"""Unit tests for OS Resource Budget Policy and Validation."""
from __future__ import annotations

from dataclasses import dataclass
import pytest

from quan_ai_brain.execution.resource_budget import (
    NetworkPolicy,
    ResourceBudget,
    ResourceBudgetPolicy,
    ResourceBudgetValidator,
)


@dataclass
class MockDelegationGrant:
    grant_id: str = "grant_001"
    max_calls: int = 2


def test_valid_default_budget_accepted():
    """Verify default resource budget passes validation."""
    validator = ResourceBudgetValidator()
    budget = ResourceBudget()
    valid, reason = validator.validate_budget(budget)
    assert valid is True
    assert "within system ceilings" in reason


def test_negative_or_zero_values_rejected():
    """Verify negative or invalid values are rejected."""
    validator = ResourceBudgetValidator()

    # Negative runtime
    b1 = ResourceBudget(max_runtime_seconds=-5.0)
    ok, err = validator.validate_budget(b1)
    assert ok is False
    assert "max_runtime_seconds must be positive" in err

    # Zero memory
    b2 = ResourceBudget(max_memory_mb=0)
    ok, err = validator.validate_budget(b2)
    assert ok is False
    assert "max_memory_mb must be positive" in err

    # Zero CPU time
    b3 = ResourceBudget(max_cpu_time_seconds=0)
    ok, err = validator.validate_budget(b3)
    assert ok is False
    assert "max_cpu_time_seconds must be positive" in err

    # Negative child processes
    b4 = ResourceBudget(max_child_processes=-1)
    ok, err = validator.validate_budget(b4)
    assert ok is False
    assert "max_child_processes cannot be negative" in err


def test_system_ceilings_enforced():
    """Verify that requests exceeding system policy ceilings are rejected."""
    policy = ResourceBudgetPolicy(
        ceiling_max_runtime_seconds=60.0,
        ceiling_max_memory_mb=1024,
        ceiling_max_child_processes=0,
    )
    validator = ResourceBudgetValidator(policy=policy)

    # Exceed runtime ceiling
    b_runtime = ResourceBudget(max_runtime_seconds=120.0)
    ok, err = validator.validate_budget(b_runtime)
    assert ok is False
    assert "exceeds system ceiling" in err

    # Exceed memory ceiling
    b_mem = ResourceBudget(max_memory_mb=2048)
    ok, err = validator.validate_budget(b_mem)
    assert ok is False
    assert "exceeds system ceiling" in err

    # Exceed child processes ceiling
    b_proc = ResourceBudget(max_child_processes=1)
    ok, err = validator.validate_budget(b_proc)
    assert ok is False
    assert "exceeds system ceiling" in err


def test_network_policy_validation():
    """Verify network policy whitelist is strictly checked."""
    validator = ResourceBudgetValidator()

    # Allowed policies
    b_blocked = ResourceBudget(network_policy=NetworkPolicy.BLOCKED)
    assert validator.validate_budget(b_blocked)[0] is True

    b_local = ResourceBudget(network_policy=NetworkPolicy.LOCALHOST_ONLY)
    assert validator.validate_budget(b_local)[0] is True

    # Unauthorized policy
    b_unauth = ResourceBudget(network_policy=NetworkPolicy.RESTRICTED)
    ok, err = validator.validate_budget(b_unauth)
    assert ok is False
    assert "network_policy" in err


def test_monotonic_parent_child_budget_containment():
    """Verify child tasks cannot exceed parent task resource envelopes."""
    validator = ResourceBudgetValidator()
    parent = ResourceBudget(max_runtime_seconds=30.0, max_memory_mb=512, max_tool_calls=3)

    # Valid child
    child_valid = ResourceBudget(max_runtime_seconds=15.0, max_memory_mb=256, max_tool_calls=2)
    ok, _ = validator.validate_against_parent(child_valid, parent)
    assert ok is True

    # Child exceeds runtime
    child_excess_runtime = ResourceBudget(max_runtime_seconds=45.0, max_memory_mb=512)
    ok, err = validator.validate_against_parent(child_excess_runtime, parent)
    assert ok is False
    assert "exceeds parent budget" in err

    # Child exceeds tool calls
    child_excess_tools = ResourceBudget(max_runtime_seconds=20.0, max_memory_mb=256, max_tool_calls=5)
    ok, err = validator.validate_against_parent(child_excess_tools, parent)
    assert ok is False
    assert "exceeds parent budget" in err


def test_delegation_grant_bounds_enforced():
    """Verify budget adheres to delegation grant limits."""
    validator = ResourceBudgetValidator()
    grant = MockDelegationGrant(max_calls=3)

    # Compliant budget
    b_ok = ResourceBudget(max_tool_calls=2)
    ok, _ = validator.validate_against_grant(b_ok, grant)
    assert ok is True

    # Exceeding budget
    b_excess = ResourceBudget(max_tool_calls=5)
    ok, err = validator.validate_against_grant(b_excess, grant)
    assert ok is False
    assert "exceeds delegation grant max_calls" in err


def test_prevent_llm_self_escalation():
    """Verify LLMs cannot autonomously escalate resource budgets."""
    validator = ResourceBudgetValidator()
    base = ResourceBudget(max_runtime_seconds=30.0, max_memory_mb=512)
    escalated = ResourceBudget(max_runtime_seconds=60.0, max_memory_mb=1024)

    # Authorized human caller allowed
    ok_human, _ = validator.prevent_llm_self_escalation(escalated, base, requested_by_llm=False)
    assert ok_human is True

    # LLM escalation strictly rejected
    ok_llm, err = validator.prevent_llm_self_escalation(escalated, base, requested_by_llm=True)
    assert ok_llm is False
    assert "LLM self-escalation of resource budget is strictly prohibited" in err
