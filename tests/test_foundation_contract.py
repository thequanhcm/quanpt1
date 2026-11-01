"""Tests for Brain Foundation Contract V1 and Control Plane."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.contract.control_plane import BrainControlPlane
from quan_ai_brain.contract.models import (
    AgentIdentity,
    AgentTrustLevel,
    AgentType,
    CapabilityRequest,
    EvidenceRecord,
    MemoryProposal,
    TaskOutcome,
    TaskRequest,
    TaskState,
)
from quan_ai_brain.execution.resource_budget import NetworkPolicy, ResourceBudget
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate
from quan_ai_brain.tools.sandbox import SystemState


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "hello.txt").write_text("Test content", encoding="utf-8")
    return ws


def test_agent_identity_invariants():
    """Verify claimed identity does not confer verified status or trust."""
    agent = AgentIdentity(
        agent_id="agent:mock-worker",
        agent_type=AgentType.WORKER,
        declared_domain="battery",
        declared_capabilities=("data_read", "report_generate"),
    )
    assert agent.is_verified_by_brain is False
    assert agent.trust_level == AgentTrustLevel.UNTRUSTED
    d = agent.to_dict()
    assert d["agent_id"] == "agent:mock-worker"
    assert d["is_verified_by_brain"] is False


def test_task_request_serialization():
    """Verify TaskRequest serializes cleanly and redacts sensitive data."""
    agent = AgentIdentity(agent_id="agent:test")
    req = TaskRequest(
        objective="Analyze system logs",
        agent_identity=agent,
        task_input={"token": "secret_abc123", "param": "safe_val"},
    )
    d = req.to_dict()
    assert d["objective"] == "Analyze system logs"
    assert d["task_input"]["token"] == "[REDACTED]"
    assert d["task_input"]["param"] == "safe_val"


def test_control_plane_emergency_stop(workspace: Path):
    """Verify ControlPlane fails closed immediately when STOP is active."""
    store = GovernanceStateStore(workspace / "gov.db", workspace=workspace)
    store.set_emergency_state(state="stop", reason="Emergency halt", activated_by="OWNER")

    cp = BrainControlPlane(workspace=workspace, store=store)
    agent = AgentIdentity(agent_id="agent:test")
    req = TaskRequest(objective="Read status", agent_identity=agent)

    outcome = cp.dispatch_task(req)
    assert outcome.state == TaskState.BLOCKED
    assert "blocked_emergency" in outcome.governance_decision
    assert outcome.attempted_actions == []
    store.close()


def test_control_plane_r5_hard_blocked(workspace: Path):
    """Verify R5 dangerous actions are permanently blocked."""
    cp = BrainControlPlane(workspace=workspace)
    agent = AgentIdentity(agent_id="agent:test")
    req = TaskRequest(
        objective="delete all files and wipe disk",
        agent_identity=agent,
        requested_capabilities=[
            CapabilityRequest(capability_name="disk_wipe", risk_level_claimed=5)
        ],
    )

    outcome = cp.dispatch_task(req)
    assert outcome.state == TaskState.BLOCKED
    assert outcome.governance_decision == "blocked_r5_prohibited"
    assert outcome.attempted_actions == []


def test_control_plane_r4_requires_approval(workspace: Path):
    """Verify R4 actions transition to WAITING_FOR_APPROVAL when approval_id is absent."""
    cp = BrainControlPlane(workspace=workspace)
    agent = AgentIdentity(agent_id="agent:test")
    req = TaskRequest(
        objective="restart service and modify config",
        agent_identity=agent,
        requested_capabilities=[
            CapabilityRequest(capability_name="service_restart", risk_level_claimed=4)
        ],
    )

    outcome = cp.dispatch_task(req)
    assert outcome.state == TaskState.WAITING_FOR_APPROVAL
    assert outcome.governance_decision == "waiting_owner_approval_r4"
    assert outcome.approval_id is None
    assert outcome.attempted_actions == []


def test_control_plane_r4_with_valid_approval(workspace: Path):
    """Verify R4 actions transition to AUTHORIZED when valid approval is attached."""
    store = GovernanceStateStore(workspace / "gov.db", workspace=workspace)
    gate = ApprovalGate(store=store)

    app_req = gate.create_request(
        tool_id="service_restart",
        action="invoke",
        params={},
        resource_scope="workspace",
        risk_level=4,
    )
    app = gate.grant_approval(app_req, approver="owner:quanpt1")

    cp = BrainControlPlane(workspace=workspace, store=store, approval_gate=gate)
    agent = AgentIdentity(agent_id="agent:test")
    req = TaskRequest(
        objective="restart service and modify config",
        agent_identity=agent,
        approval_id=app.approval_id,
        requested_capabilities=[
            CapabilityRequest(capability_name="service_restart", risk_level_claimed=4)
        ],
    )

    outcome = cp.dispatch_task(req)
    assert outcome.state == TaskState.AUTHORIZED
    assert outcome.governance_decision == "authorized_by_owner_approval"
    assert outcome.approval_id == app.approval_id
    # Guarantees zero execution in inert mode
    assert outcome.attempted_actions == []
    store.close()


def test_control_plane_inert_invariant(workspace: Path):
    """Verify that in inert mode, attempted_actions is ALWAYS empty and is_inert is True."""
    cp = BrainControlPlane(workspace=workspace)
    agent = AgentIdentity(agent_id="agent:test")
    req = TaskRequest(objective="Examine directory contents", agent_identity=agent)

    outcome = cp.dispatch_task(req)
    assert outcome.is_inert is True
    assert outcome.attempted_actions == []
    assert len(outcome.planned_actions) > 0


def test_control_plane_evidence_generation(workspace: Path):
    """Verify outcome contains traceable EvidenceRecords."""
    cp = BrainControlPlane(workspace=workspace)
    agent = AgentIdentity(agent_id="agent:analyzer", is_verified_by_brain=True)
    req = TaskRequest(objective="Check system health", agent_identity=agent)

    outcome = cp.dispatch_task(req)
    assert len(outcome.evidence) >= 2
    sources = [e.source_type for e in outcome.evidence]
    assert "identity_verification" in sources
    assert "plan_generation" in sources


def test_memory_proposal_quarantine():
    """Verify memory proposals default to CANDIDATE verification status."""
    proposal = MemoryProposal(
        proposal_id="prop_01",
        memory_type="PROCEDURAL",
        content="Standard log rotate procedure",
        source_task_id="task_123",
        confidence_score=0.7,
    )
    assert proposal.verification_status == "CANDIDATE"
    d = proposal.to_dict()
    assert d["verification_status"] == "CANDIDATE"


def test_control_plane_budget_rejection(workspace: Path):
    """Verify requests with excessive resource budgets are blocked."""
    cp = BrainControlPlane(workspace=workspace)
    agent = AgentIdentity(agent_id="agent:test")
    excessive_budget = ResourceBudget(max_memory_mb=100000)  # Exceeds max 4096MB

    req = TaskRequest(
        objective="Run massive workload",
        agent_identity=agent,
        budget_request=excessive_budget,
    )

    outcome = cp.dispatch_task(req)
    assert outcome.state == TaskState.BLOCKED
    assert outcome.governance_decision == "blocked_budget_violation"
