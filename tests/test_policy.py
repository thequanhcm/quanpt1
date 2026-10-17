from pathlib import Path

from quan_ai_brain.governance.policy import (
    ActionRequest,
    DecisionStatus,
    PolicyEngine,
    RiskLevel,
)


def test_r0_r1_are_allowed_without_execution(tmp_path: Path):
    engine = PolicyEngine(tmp_path)
    assert engine.authorize(ActionRequest("read", RiskLevel.R0)).status == DecisionStatus.ALLOW
    assert engine.authorize(ActionRequest("analyze", RiskLevel.R1)).status == DecisionStatus.ALLOW


def test_r2_requires_workspace_target_and_blocks_traversal(tmp_path: Path):
    engine = PolicyEngine(tmp_path)
    assert engine.authorize(ActionRequest("write", RiskLevel.R2)).status == DecisionStatus.DENY
    allowed = engine.authorize(ActionRequest("write", RiskLevel.R2, "docs/report.md"))
    assert allowed.status == DecisionStatus.ALLOW
    assert Path(allowed.normalized_target).is_relative_to(tmp_path.resolve())
    denied = engine.authorize(ActionRequest("write", RiskLevel.R2, "../outside.txt"))
    assert denied.status == DecisionStatus.DENY


def test_r3_requires_notice_r4_approval_r5_hard_blocked(tmp_path: Path):
    engine = PolicyEngine(tmp_path)
    assert engine.authorize(ActionRequest("external", RiskLevel.R3)).status == DecisionStatus.ALLOW_WITH_NOTICE
    assert engine.authorize(ActionRequest("modify-system", RiskLevel.R4)).status == DecisionStatus.APPROVAL_REQUIRED
    assert engine.authorize(ActionRequest("danger", RiskLevel.R5)).status == DecisionStatus.BLOCKED
