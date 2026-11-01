"""Unit and integration tests for SafeToolSandbox (Sprint 3B)."""
import json
from pathlib import Path
import pytest

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.governance.policy import PolicyEngine, RiskLevel
from quan_ai_brain.tools.approval import ApprovalGate
from quan_ai_brain.tools.delegation import DelegationGrant, DelegationRegistry
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry
from quan_ai_brain.tools.sandbox import ExecutionResult, SafeToolSandbox, SystemState


@pytest.fixture
def sandbox_env(tmp_path: Path):
    """Fixture providing an isolated workspace sandbox environment."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "data").mkdir()
    (workspace / "logs").mkdir()

    # Create dummy safe files
    (workspace / "README.md").write_text("# Test Readme", encoding="utf-8")
    (workspace / "docs").mkdir()
    (workspace / "docs" / "guide.md").write_text("# User Guide", encoding="utf-8")

    # Create dummy sensitive files
    (workspace / ".env").write_text("API_KEY=secret_12345", encoding="utf-8")
    (workspace / "id_rsa").write_text("PRIVATE KEY DATA", encoding="utf-8")

    sandbox = SafeToolSandbox(workspace=workspace)
    return sandbox, workspace


def test_unregistered_tool_blocked(sandbox_env):
    sandbox, _ = sandbox_env
    res = sandbox.execute("unknown_hacker_tool", {})
    assert res.success is False
    assert res.governance_decision == "blocked"
    assert "not registered" in res.error


def test_invalid_parameters_denied(sandbox_env):
    sandbox, _ = sandbox_env
    # file_read requires file_path as str
    res = sandbox.execute("file_read", {})
    assert res.success is False
    assert res.governance_decision == "deny"
    assert "Missing required parameter 'file_path'" in res.error


def test_path_guard_escape_denied(sandbox_env):
    sandbox, _ = sandbox_env
    # Path traversal outside workspace
    res = sandbox.execute("file_read", {"file_path": "../../outside.txt"})
    assert res.success is False
    assert res.governance_decision == "deny"
    assert "PathGuard check failed" in res.error


def test_sensitive_file_access_denied(sandbox_env):
    sandbox, _ = sandbox_env
    # Attempting to read .env
    res_env = sandbox.execute("file_read", {"file_path": ".env"})
    assert res_env.success is False
    assert res_env.governance_decision == "deny"
    assert "sensitive file" in res_env.error.lower()

    # Attempting to read id_rsa
    res_rsa = sandbox.execute("file_read", {"file_path": "id_rsa"})
    assert res_rsa.success is False
    assert res_rsa.governance_decision == "deny"
    assert "sensitive file" in res_rsa.error.lower()


def test_owner_consent_required_by_default(sandbox_env):
    sandbox, _ = sandbox_env
    # No approval_id and no active delegation grant
    res = sandbox.execute("file_read", {"file_path": "README.md"})
    assert res.success is False
    assert res.governance_decision == "pending_owner_approval"
    assert "Owner consultation required" in res.error


def test_tool_execution_with_valid_owner_approval(sandbox_env):
    sandbox, workspace = sandbox_env
    req = sandbox.approval_gate.create_request("file_read", "read", {"file_path": "README.md"})
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    res = sandbox.execute("file_read", {"file_path": "README.md"}, approval_id=approval.approval_id)
    assert res.success is True
    assert res.governance_decision == "allowed_by_approval"
    assert res.output["content"] == "# Test Readme"
    assert res.approval_id == approval.approval_id

    # The one-time approval is consumed; replaying it fails immediately
    res_replay = sandbox.execute("file_read", {"file_path": "README.md"}, approval_id=approval.approval_id)
    assert res_replay.success is False
    assert res_replay.governance_decision == "denied"
    assert "already been consumed" in res_replay.error


def test_tool_execution_with_delegation_grant(sandbox_env):
    sandbox, workspace = sandbox_env
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    grant = DelegationGrant(
        grant_id="grant-test-01",
        owner_identity="owner:quanpt1",
        description="Autonomous reading of docs and health checks",
        allowed_tool_ids=["file_read", "dir_list", "system_health"],
        allowed_action_types=["read"],
        allowed_resource_scope="workspace",
        allowed_project_scope="QUAN_AI_BRAIN",
        maximum_risk_level=RiskLevel.R0,
        valid_from=(now - timedelta(hours=1)).isoformat(),
        expires_at=(now + timedelta(hours=12)).isoformat(),
        max_calls=3,
    )
    sandbox.delegation_registry.register_grant(grant)

    # Autonomous execution without passing approval_id
    res = sandbox.execute("file_read", {"file_path": "docs/guide.md"})
    assert res.success is True
    assert res.governance_decision == "allowed_by_delegation"
    assert res.output["content"] == "# User Guide"
    assert res.grant_id == "grant-test-01"
    assert grant.calls_count == 1


def test_file_write_new_creates_file_safely(sandbox_env):
    sandbox, workspace = sandbox_env
    req = sandbox.approval_gate.create_request(
        "file_write_new",
        "write",
        {"file_path": "output/results.txt", "content": "Sample output"},
        risk_level=RiskLevel.R2,
    )
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    res = sandbox.execute(
        "file_write_new",
        {"file_path": "output/results.txt", "content": "Sample output"},
        approval_id=approval.approval_id,
    )
    assert res.success is True
    assert res.governance_decision == "allowed_by_approval"
    assert res.output["created"] is True

    written_path = workspace / "output" / "results.txt"
    assert written_path.exists()
    assert written_path.read_text(encoding="utf-8") == "Sample output"


def test_file_write_new_prohibits_overwriting(sandbox_env):
    sandbox, workspace = sandbox_env
    # README.md already exists!
    req = sandbox.approval_gate.create_request(
        "file_write_new",
        "write",
        {"file_path": "README.md", "content": "Malicious overwrite"},
        risk_level=RiskLevel.R2,
    )
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    res = sandbox.execute(
        "file_write_new",
        {"file_path": "README.md", "content": "Malicious overwrite"},
        approval_id=approval.approval_id,
    )
    assert res.success is False
    assert "already exists" in res.error
    assert "strictly prohibited" in res.error
    # Original file must remain untouched
    assert (workspace / "README.md").read_text(encoding="utf-8") == "# Test Readme"


def test_dry_run_execution(sandbox_env):
    sandbox, workspace = sandbox_env
    req = sandbox.approval_gate.create_request(
        "file_write_new",
        "write",
        {"file_path": "simulated.txt", "content": "Will not be written"},
        risk_level=RiskLevel.R2,
    )
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    res = sandbox.execute(
        "file_write_new",
        {"file_path": "simulated.txt", "content": "Will not be written"},
        approval_id=approval.approval_id,
        dry_run=True,
    )
    assert res.success is True
    assert res.governance_decision == "approved_dry_run"
    assert res.output["dry_run"] is True
    # Verify file was NOT actually created on disk
    assert not (workspace / "simulated.txt").exists()


def test_system_state_stop_and_freeze_blocks(sandbox_env):
    sandbox, _ = sandbox_env
    req = sandbox.approval_gate.create_request("file_read", "read", {"file_path": "README.md"})
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    # Set STOP
    sandbox.set_system_state(SystemState.STOP)
    res_stop = sandbox.execute("file_read", {"file_path": "README.md"}, approval_id=approval.approval_id)
    assert res_stop.success is False
    assert res_stop.governance_decision == "blocked"
    assert "STOP state" in res_stop.error

    # Set FREEZE
    sandbox.set_system_state(SystemState.FREEZE)
    res_freeze = sandbox.execute("file_read", {"file_path": "README.md"}, approval_id=approval.approval_id)
    assert res_freeze.success is False
    assert res_freeze.governance_decision == "blocked"
    assert "FREEZE state" in res_freeze.error

    # Return to NORMAL
    sandbox.set_system_state(SystemState.NORMAL)
    res_normal = sandbox.execute("file_read", {"file_path": "README.md"}, approval_id=approval.approval_id)
    assert res_normal.success is True


def test_r5_tool_hard_blocked(sandbox_env):
    sandbox, _ = sandbox_env

    # Register an intentionally dangerous R5 tool
    def _danger_handler(params):
        return "exploded"

    danger_tool = ToolDefinition(
        tool_id="format_disk",
        description="Dangerous R5 prohibited operation",
        action_type="delete",
        risk_level=RiskLevel.R5,
        handler=_danger_handler,
    )
    sandbox.registry.register(danger_tool)

    req = sandbox.approval_gate.create_request("format_disk", "delete", {}, risk_level=RiskLevel.R5)
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    # Even with owner approval, R5 is hard-blocked by PolicyEngine!
    res = sandbox.execute("format_disk", {}, approval_id=approval.approval_id)
    assert res.success is False
    assert res.governance_decision == "blocked"
    assert "R5 is hard-blocked" in res.error


def test_r4_tool_requires_approval_cannot_be_delegated(sandbox_env):
    sandbox, _ = sandbox_env

    def _sys_handler(params):
        return "modified"

    sys_tool = ToolDefinition(
        tool_id="system_config_change",
        description="Significant system change",
        action_type="system",
        risk_level=RiskLevel.R4,
        handler=_sys_handler,
    )
    sandbox.registry.register(sys_tool)

    # Calling R4 without approval must fail with approval_required
    res = sandbox.execute("system_config_change", {})
    assert res.success is False
    assert res.governance_decision == "approval_required"
    assert "R4 actions require explicit owner approval" in res.error


def test_audit_logger_records_all_invocations(sandbox_env):
    sandbox, workspace = sandbox_env
    # 1. Unregistered tool
    sandbox.execute("ghost_tool", {})
    # 2. Blocked without consent
    sandbox.execute("file_read", {"file_path": "README.md"})

    audit_file = workspace / "logs" / "audit.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2

    event1 = json.loads(lines[0])
    assert event1["event_type"] == "sandbox.tool_rejected"
    assert event1["details"]["tool_id"] == "ghost_tool"

    event2 = json.loads(lines[1])
    assert event2["event_type"] == "sandbox.consent_required"
    assert event2["details"]["decision"] == "pending_owner_approval"


def test_plan_validate_tool_handler(sandbox_env):
    sandbox, workspace = sandbox_env
    plan_dict = {
        "plan_id": "plan-validate-test",
        "goal": "Verify system health",
        "steps": [
            {
                "step_id": "step-1",
                "name": "Check DB",
                "description": "Inspect database file",
                "expected_output": "Database exists",
                "risk_level": 0,
            }
        ],
    }
    req = sandbox.approval_gate.create_request(
        tool_id="plan_validate",
        action="analysis",
        params={"plan": plan_dict},
        risk_level=RiskLevel.R1,
    )
    approval = sandbox.approval_gate.grant_approval(req, approver="owner:quanpt1")

    res = sandbox.execute("plan_validate", {"plan": plan_dict}, approval_id=approval.approval_id)
    assert res.success is True
    assert res.governance_decision == "allowed_by_approval"
    assert res.output["valid"] is True
    assert res.output["plan_id"] == "plan-validate-test"
    assert res.output["steps_count"] == 1


def test_cli_tool_list_and_tool_run(capsys, monkeypatch):
    from quan_ai_brain.cli import main

    # 1. tool-list
    rc_list = main(["tool-list"])
    assert rc_list == 0
    out_list, _ = capsys.readouterr()
    tools = json.loads(out_list)
    assert isinstance(tools, list)
    assert any(t["tool_id"] == "file_read" for t in tools)

    # 2. tool-run without approval in non-interactive mode -> exits 1 with pending_owner_approval
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc_pending = main(["tool-run", "--tool", "file_read", "--params", '{"file_path": "pyproject.toml"}'])
    assert rc_pending == 1
    out_pending, _ = capsys.readouterr()
    res_pending = json.loads(out_pending)
    assert res_pending["success"] is False
    assert res_pending["governance_decision"] == "pending_owner_approval"

    # 3. tool-run with --confirm flag -> executes successfully
    rc_ok = main(["tool-run", "--tool", "file_read", "--params", '{"file_path": "pyproject.toml"}', "--confirm"])
    assert rc_ok == 0
    out_ok, _ = capsys.readouterr()
    res_ok = json.loads(out_ok)
    assert res_ok["success"] is True
    assert res_ok["governance_decision"] == "allowed_by_approval"

