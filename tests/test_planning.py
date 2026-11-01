"""Unit and integration tests for QUAN AI BRAIN Planning & Governance (Sprint 3A)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.retrieval import CognitiveRetriever
from quan_ai_brain.governance.policy import PolicyEngine, RiskLevel
from quan_ai_brain.llm import FallbackMode, LLMProvider, MockLLMProvider
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore
from quan_ai_brain.planning.coordinator import ExecutiveCoordinator
from quan_ai_brain.planning.models import StepStatus, TaskPlan, TaskStep, TaskStatus


# ---------------------------------------------------------------------------
# 1. TaskPlan & TaskStep Validation Tests
# ---------------------------------------------------------------------------

def test_valid_task_plan():
    step1 = TaskStep(
        name="read_config",
        description="Đọc file cấu hình từ thư mục config",
        expected_output="Nội dung file cấu hình",
        risk_level=0,
        step_id="step-1",
        sequence=1,
    )
    step2 = TaskStep(
        name="analyze_settings",
        description="Phân tích các tham số cài đặt",
        expected_output="Báo cáo phân tích tham số",
        risk_level=1,
        step_id="step-2",
        sequence=2,
        dependencies=("step-1",),
    )
    plan = TaskPlan(goal="Kiểm tra cấu hình hệ thống", steps=[step1, step2])
    plan.validate()
    assert plan.status in (TaskStatus.DRAFT, TaskStatus.READY_FOR_REVIEW)
    assert not plan.blocked
    assert not plan.requires_approval


def test_empty_goal_rejected():
    step = TaskStep("test", "test description", "output", 0)
    with pytest.raises(ValueError, match="goal must not be empty"):
        TaskPlan(goal="", steps=[step]).validate()

    with pytest.raises(ValueError, match="goal must not be empty"):
        TaskPlan(goal="   ", steps=[step]).validate()


def test_empty_steps_rejected():
    with pytest.raises(ValueError, match="must contain at least one step"):
        TaskPlan(goal="Some goal", steps=[]).validate()


def test_invalid_step_fields_rejected():
    # Missing name
    with pytest.raises(ValueError, match="must have a name and expected output"):
        TaskPlan(goal="Goal", steps=[TaskStep("", "desc", "output", 0)]).validate()

    # Missing expected output
    with pytest.raises(ValueError, match="must have a name and expected output"):
        TaskPlan(goal="Goal", steps=[TaskStep("name", "desc", "", 0)]).validate()

    # Invalid risk level (< 0 or > 5)
    with pytest.raises(ValueError, match="invalid risk level"):
        TaskPlan(goal="Goal", steps=[TaskStep("name", "desc", "output", -1)]).validate()

    with pytest.raises(ValueError, match="invalid risk level"):
        TaskPlan(goal="Goal", steps=[TaskStep("name", "desc", "output", 6)]).validate()


def test_duplicate_step_ids_rejected():
    s1 = TaskStep("s1", "desc1", "out1", 0, step_id="dup-id")
    s2 = TaskStep("s2", "desc2", "out2", 0, step_id="dup-id")
    plan = TaskPlan(goal="Duplicate check", steps=[s1, s2])
    with pytest.raises(ValueError, match="Duplicate step ID 'dup-id' detected"):
        plan.validate()


def test_nonexistent_dependency_rejected():
    s1 = TaskStep("s1", "desc1", "out1", 0, step_id="step-1", dependencies=("ghost-step",))
    plan = TaskPlan(goal="Dependency check", steps=[s1])
    with pytest.raises(ValueError, match="depends on non-existent step 'ghost-step'"):
        plan.validate()


def test_self_dependency_rejected():
    s1 = TaskStep("s1", "desc1", "out1", 0, step_id="step-1", dependencies=("step-1",))
    plan = TaskPlan(goal="Self dependency check", steps=[s1])
    with pytest.raises(ValueError, match="cannot depend on itself"):
        plan.validate()


def test_cyclic_dependency_rejected():
    s1 = TaskStep("s1", "desc1", "out1", 0, step_id="step-1", dependencies=("step-2",))
    s2 = TaskStep("s2", "desc2", "out2", 0, step_id="step-2", dependencies=("step-1",))
    plan = TaskPlan(goal="Cycle check", steps=[s1, s2])
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        plan.validate()


def test_r4_and_r5_step_governance_rules():
    # R4 step requires approval
    s_r4 = TaskStep(
        name="modify_sys",
        description="Thay đổi cấu hình hệ thống",
        expected_output="Hệ thống cập nhật",
        risk_level=4,
        requires_approval=True,
    )
    plan_r4 = TaskPlan(goal="Upgrade system", steps=[s_r4])
    plan_r4.validate()
    assert plan_r4.requires_approval is True
    assert plan_r4.status == TaskStatus.WAITING_APPROVAL

    # R5 step is hard blocked
    s_r5 = TaskStep(
        name="destroy_data",
        description="Xóa toàn bộ dữ liệu máy chủ",
        expected_output="Dữ liệu bị xóa",
        risk_level=5,
        requires_approval=True,
        policy_status="blocked",
    )
    plan_r5 = TaskPlan(goal="Dangerous operation", steps=[s_r5])
    plan_r5.validate()
    assert plan_r5.blocked is True
    assert plan_r5.status == TaskStatus.BLOCKED


# ---------------------------------------------------------------------------
# 2. ExecutiveCoordinator & Independent Governance Tests
# ---------------------------------------------------------------------------

def test_coordinator_creates_valid_plan(tmp_path: Path):
    policy = PolicyEngine(tmp_path)
    mock_llm = MockLLMProvider()
    provider = LLMProvider(mock=mock_llm, fallback_mode=FallbackMode.ALWAYS_MOCK)

    coordinator = ExecutiveCoordinator(
        workspace=tmp_path,
        llm_provider=provider,
        policy_engine=policy,
    )

    plan = coordinator.plan("Kiểm tra và phân tích an toàn hệ thống")

    assert isinstance(plan, TaskPlan)
    assert plan.status in (TaskStatus.READY_FOR_REVIEW, TaskStatus.WAITING_APPROVAL)
    assert len(plan.steps) == 2
    assert plan.source == "mock"
    assert any("MOCK MODE" in w for w in plan.warnings)

    # First step should be read (R0) and allowed
    s1 = plan.steps[0]
    assert s1.risk_level == 0
    assert s1.policy_status == "allow"
    assert s1.status == StepStatus.VALIDATED


def test_coordinator_escalates_and_blocks_r5_keyword(tmp_path: Path):
    policy = PolicyEngine(tmp_path)

    # Mock response where LLM deviously claims a dangerous operation is R0!
    canned_bad_proposal = {
        'GOAL: Xóa toàn bộ dữ liệu phân vùng để giải phóng dung lượng\n\nCONTEXT:\n(No relevant memories found)\n\nRespond ONLY with a JSON object following this exact schema:\n{\n  "summary": "<short plan summary>",\n  "steps": [\n    {\n      "step_id": "step-1",\n      "name": "<action_identifier>",\n      "description": "<detailed action description>",\n      "expected_output": "<verifiable outcome>",\n      "risk_level": <integer 0 to 5>,\n      "preconditions": ["<precondition 1>"],\n      "verification_method": "<how output is verified>",\n      "dependencies": [],\n      "target_path": "<optional workspace relative path or null>"\n    }\n  ]\n}': (
            '{\n'
            '  "summary": "Kế hoạch dọn dẹp hệ thống",\n'
            '  "steps": [\n'
            '    {\n'
            '      "step_id": "step-1",\n'
            '      "name": "wipe_storage",\n'
            '      "description": "rm -rf all files on drive",\n'
            '      "expected_output": "Ổ đĩa trống",\n'
            '      "risk_level": 0,\n'
            '      "preconditions": [],\n'
            '      "verification_method": "df -h",\n'
            '      "dependencies": []\n'
            '    }\n'
            '  ]\n'
            '}'
        )
    }

    mock_llm = MockLLMProvider(canned_responses=canned_bad_proposal)
    provider = LLMProvider(mock=mock_llm, fallback_mode=FallbackMode.ALWAYS_MOCK)
    coordinator = ExecutiveCoordinator(workspace=tmp_path, llm_provider=provider, policy_engine=policy)

    plan = coordinator.plan("Xóa toàn bộ dữ liệu phân vùng để giải phóng dung lượng")

    # LLM claimed R0, but Coordinator must independently escalate to R5 and block it!
    assert plan.blocked is True
    assert plan.status == TaskStatus.BLOCKED
    step = plan.steps[0]
    assert step.risk_level == RiskLevel.R5.value
    assert step.policy_status == "blocked"
    assert step.status == StepStatus.BLOCKED
    assert any("escalated independently" in w for w in step.warnings)
    assert any("Hard-blocked by Policy Engine" in w for w in step.warnings)


def test_coordinator_path_check_for_r2_write(tmp_path: Path):
    policy = PolicyEngine(tmp_path)

    # 1. Write within workspace -> ALLOW
    canned_safe_write = {
        'GOAL: Ghi báo cáo kết quả\n\nCONTEXT:\n(No relevant memories found)\n\nRespond ONLY with a JSON object following this exact schema:\n{\n  "summary": "<short plan summary>",\n  "steps": [\n    {\n      "step_id": "step-1",\n      "name": "<action_identifier>",\n      "description": "<detailed action description>",\n      "expected_output": "<verifiable outcome>",\n      "risk_level": <integer 0 to 5>,\n      "preconditions": ["<precondition 1>"],\n      "verification_method": "<how output is verified>",\n      "dependencies": [],\n      "target_path": "<optional workspace relative path or null>"\n    }\n  ]\n}': (
            '{\n'
            '  "summary": "Ghi báo cáo nội bộ",\n'
            '  "steps": [\n'
            '    {\n'
            '      "step_id": "step-1",\n'
            '      "name": "save_report",\n'
            '      "description": "Ghi tệp kết quả vào reports/summary.md",\n'
            '      "expected_output": "Tệp summary.md được tạo",\n'
            '      "risk_level": 2,\n'
            '      "target_path": "reports/summary.md"\n'
            '    }\n'
            '  ]\n'
            '}'
        )
    }
    mock1 = MockLLMProvider(canned_responses=canned_safe_write)
    coord1 = ExecutiveCoordinator(workspace=tmp_path, llm_provider=LLMProvider(mock=mock1, fallback_mode=FallbackMode.ALWAYS_MOCK), policy_engine=policy)
    plan1 = coord1.plan("Ghi báo cáo kết quả")
    assert plan1.steps[0].policy_status == "allow"
    assert not plan1.blocked

    # 2. Write OUTSIDE workspace -> DENY & BLOCKED
    canned_outside_write = {
        'GOAL: Ghi file hệ thống ngoài\n\nCONTEXT:\n(No relevant memories found)\n\nRespond ONLY with a JSON object following this exact schema:\n{\n  "summary": "<short plan summary>",\n  "steps": [\n    {\n      "step_id": "step-1",\n      "name": "<action_identifier>",\n      "description": "<detailed action description>",\n      "expected_output": "<verifiable outcome>",\n      "risk_level": <integer 0 to 5>,\n      "preconditions": ["<precondition 1>"],\n      "verification_method": "<how output is verified>",\n      "dependencies": [],\n      "target_path": "<optional workspace relative path or null>"\n    }\n  ]\n}': (
            '{\n'
            '  "summary": "Ghi file ngoài",\n'
            '  "steps": [\n'
            '    {\n'
            '      "step_id": "step-1",\n'
            '      "name": "write_external",\n'
            '      "description": "Ghi file ra ngoài workspace",\n'
            '      "expected_output": "File ngoài",\n'
            '      "risk_level": 2,\n'
            '      "target_path": "../../Windows/System32/evil.dll"\n'
            '    }\n'
            '  ]\n'
            '}'
        )
    }
    mock2 = MockLLMProvider(canned_responses=canned_outside_write)
    coord2 = ExecutiveCoordinator(workspace=tmp_path, llm_provider=LLMProvider(mock=mock2, fallback_mode=FallbackMode.ALWAYS_MOCK), policy_engine=policy)
    plan2 = coord2.plan("Ghi file hệ thống ngoài")
    assert plan2.blocked is True
    assert plan2.steps[0].policy_status == "deny"


def test_coordinator_handles_malformed_llm_json(tmp_path: Path):
    policy = PolicyEngine(tmp_path)
    canned_gibberish = {
        'GOAL: Yêu cầu trả về văn bản thường\n\nCONTEXT:\n(No relevant memories found)\n\nRespond ONLY with a JSON object following this exact schema:\n{\n  "summary": "<short plan summary>",\n  "steps": [\n    {\n      "step_id": "step-1",\n      "name": "<action_identifier>",\n      "description": "<detailed action description>",\n      "expected_output": "<verifiable outcome>",\n      "risk_level": <integer 0 to 5>,\n      "preconditions": ["<precondition 1>"],\n      "verification_method": "<how output is verified>",\n      "dependencies": [],\n      "target_path": "<optional workspace relative path or null>"\n    }\n  ]\n}': (
            "Xin chào! Tôi là trợ lý ảo, tôi không thể tạo định dạng JSON cho bạn được."
        )
    }
    mock_llm = MockLLMProvider(canned_responses=canned_gibberish)
    provider = LLMProvider(mock=mock_llm, fallback_mode=FallbackMode.ALWAYS_MOCK)
    coordinator = ExecutiveCoordinator(workspace=tmp_path, llm_provider=provider, policy_engine=policy)

    plan = coordinator.plan("Yêu cầu trả về văn bản thường")

    # Must fail safely without guessing missing fields or crashing!
    assert plan.status == TaskStatus.FAILED
    assert len(plan.validation_errors) > 0
    assert "JSON parse error" in plan.validation_errors[0] or "Failed to parse" in plan.summary


def test_coordinator_with_memory_context_integration(tmp_path: Path):
    db_file = tmp_path / "brain_plan.db"
    with MemoryStore(db_file, workspace=tmp_path) as store:
        rec = store.store_memory(
            content="Quy trình hạ tải khẩn cấp tủ rack DC-A1 khi quá nhiệt 40 độ C",
            memory_type=MemoryType.PROCEDURAL,
            source_ref="SOP-DC-A1",
            verification_status=VerificationStatus.VERIFIED,
            project_scope="DC-COMMAND",
        )

        retriever = CognitiveRetriever(store)
        context_builder = PromptContextBuilder()
        policy = PolicyEngine(tmp_path)
        mock_llm = MockLLMProvider()
        provider = LLMProvider(mock=mock_llm, fallback_mode=FallbackMode.ALWAYS_MOCK)

        coordinator = ExecutiveCoordinator(
            workspace=tmp_path,
            llm_provider=provider,
            policy_engine=policy,
            retriever=retriever,
            context_builder=context_builder,
        )

        plan = coordinator.plan("quy trình hạ tải khẩn cấp DC-A1", project_scope="DC-COMMAND")

        # Memory references must be captured in plan provenance
        assert len(plan.memory_refs) >= 1
        assert rec.id in plan.memory_refs


def test_plan_explanation_format(tmp_path: Path):
    step1 = TaskStep("check_status", "Check status", "OK", 0, step_id="step-1")
    step2 = TaskStep("approve_task", "Apply change", "Changed", 4, requires_approval=True, step_id="step-2", policy_status="approval_required")
    plan = TaskPlan(
        goal="Bảo trì hệ thống DC",
        summary="Kế hoạch bảo trì",
        steps=[step1, step2],
        memory_refs=["mem-101"],
        warnings=["Cảnh báo cần kiểm tra nguồn"],
    )
    plan.validate()

    explanation = plan.explain()
    assert "# BẢN KẾ HOẠCH NHIỆM VỤ:" in explanation
    assert "Bảo trì hệ thống DC" in explanation
    assert "step-1" in explanation
    assert "step-2" in explanation
    assert "approval_required" in explanation
    assert "mem-101" in explanation
    assert "LƯU Ý QUẢN TRỊ" in explanation


def test_zero_execution_guarantee():
    """Ensure TaskPlan objects in Sprint 3A never claim SUCCEEDED or execute actions."""
    step = TaskStep("dummy", "desc", "out", 0)
    plan = TaskPlan(goal="Test non-execution", steps=[step])
    plan.validate()

    assert plan.status in (TaskStatus.DRAFT, TaskStatus.READY_FOR_REVIEW)
    assert plan.status != TaskStatus.SUCCEEDED
    assert plan.status != TaskStatus.RUNNING
    for s in plan.steps:
        assert s.status != "succeeded"
        assert s.status != "running"
