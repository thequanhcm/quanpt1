"""DEOM M5 — Tests: GoalDecomposer (goal tiếng Việt → TaskPlan deterministic).

Nghiệm thu: phân rã đúng số bước theo dấu hiệu chuỗi, risk không bao giờ bị HẠ,
R5 delete → BLOCKED (policy), R4 install → PENDING_APPROVAL, plan validate() pass,
fallback R0 an toàn cho phần không nhận diện được.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.planning.goal_decomposer import GoalDecomposer
from quan_ai_brain.planning.models import StepStatus


@pytest.fixture()
def decomposer(tmp_path):
    return GoalDecomposer(workspace=tmp_path)


class TestSingleAction:
    def test_single_read(self, decomposer):
        r = decomposer.decompose("Kiểm tra hộ em trạng thái server")
        assert len(r.plan.steps) == 1
        s = r.plan.steps[0]
        assert s.risk_level == 0
        assert s.status == StepStatus.VALIDATED
        assert "server" in s.description

    def test_single_write_r2(self, decomposer):
        r = decomposer.decompose("tạo file ghi chú cuộc họp")
        assert r.plan.steps[0].risk_level == 2

    def test_single_install_r4_requires_approval(self, decomposer):
        r = decomposer.decompose("cài đặt Node.js bản mới trên máy")
        s = r.plan.steps[0]
        assert s.risk_level == 4
        assert s.status == StepStatus.PENDING_APPROVAL
        assert s.requires_approval is True
        assert r.plan.requires_approval is True

    def test_single_delete_r5_blocked(self, decomposer):
        r = decomposer.decompose("xóa toàn bộ thư mục hệ thống")
        s = r.plan.steps[0]
        assert s.risk_level == 5
        assert s.status == StepStatus.BLOCKED
        assert "R5" in s.policy_reason or "blocked" in s.policy_reason.lower()


class TestChainedGoals:
    def test_roi_then_write(self, decomposer):
        r = decomposer.decompose("kiểm tra log server rồi tạo báo cáo")
        assert len(r.plan.steps) == 2
        s1, s2 = r.plan.steps
        assert s1.risk_level == 0
        assert s2.risk_level == 2
        # phụ thuộc chuỗi: bước 2 phụ thuộc bước 1
        assert s2.dependencies == ("step-1",)

    def test_enumerated_lines(self, decomposer):
        goal = "1. kiểm tra disk\n2. phân tích dung lượng\n3. gửi báo cáo cho anh"
        r = decomposer.decompose(goal)
        assert len(r.plan.steps) == 3
        risks = [s.risk_level for s in r.plan.steps]
        assert risks == [0, 1, 3]

    def test_semicolon_split(self, decomposer):
        r = decomposer.decompose("đọc cấu hình; cập nhật file notes")
        assert len(r.plan.steps) == 2

    def test_chain_dependencies_sequential(self, decomposer):
        r = decomposer.decompose("kiểm tra a rồi phân tích b sau đó tạo c")
        deps = [s.dependencies for s in r.plan.steps]
        assert deps[0] == ()
        assert deps[1] == ("step-1",)
        assert deps[2] == ("step-2",)


class TestFailHonest:
    def test_unknown_verb_falls_back_to_r0_with_warning(self, decomposer):
        r = decomposer.decompose("xyzabc blurp thing")
        assert len(r.plan.steps) == 1
        s = r.plan.steps[0]
        assert s.risk_level == 0  # an toàn: không đoán risk cao
        assert r.unmatched_fragments
        assert r.plan.warnings

    def test_mixed_known_unknown(self, decomposer):
        r = decomposer.decompose("kiểm tra ram rồi xyzabc")
        assert len(r.plan.steps) == 2
        assert r.matched_verbs == ["kiểm tra"]
        assert r.plan.steps[1].risk_level == 0

    def test_empty_goal_raises(self, decomposer):
        with pytest.raises(ValueError):
            decomposer.decompose("   ")

    def test_no_llm_used(self, decomposer):
        # decomposer là đường deterministic — source không phải LLM provider
        r = decomposer.decompose("kiểm tra cpu")
        assert r.plan.source == "vn_goal"

    def test_redaction_applied(self, decomposer):
        r = decomposer.decompose(
            "kiểm tra kết quả với Authorization: Bearer sk-abc123def456ghi789"
        )
        # redact_text che Bearer token trong goal: chuỗi gốc không còn nguyên vẹn
        assert "sk-abc123def456ghi789" not in r.plan.goal
        assert "[REDACTED]" in r.plan.goal


class TestPlanIntegrity:
    def test_plan_validates(self, decomposer):
        r = decomposer.decompose("kiểm tra a rồi tạo b rồi gửi c")
        assert not r.plan.validation_errors
        # validate() của TaskPlan chạy lại không ném
        r.plan.validate()

    def test_summary_counts_steps(self, decomposer):
        r = decomposer.decompose("kiểm tra a rồi phân tích b")
        assert "2" in r.plan.summary
