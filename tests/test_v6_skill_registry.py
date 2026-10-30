"""Tests — Master Prompt V6: Skill Registry (skill_registry.py).

Phủ: đăng ký skill, lifecycle fail-closed (không nhảy cóc, AVAILABLE cần evidence),
find_matching, persist round-trip, file corrupt fail-honest.
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

import pytest

from quan_ai_brain.cognition.skill_registry import (
    SkillRegistry,
    SkillStatus,
)


@pytest.fixture()
def registry_path(tmp_path) -> Path:
    return tmp_path / "data" / "skill_registry.json"


@pytest.fixture()
def registry(registry_path) -> SkillRegistry:
    return SkillRegistry(registry_path)


def _register_sample(reg: SkillRegistry, name: str = "TASK_PROGRESS_AUDIT") -> object:
    return reg.register_skill(
        name=name,
        goal="Kiểm tra tiến độ công việc từ nguồn dữ liệu được phép",
        trigger_patterns=["kiểm tra tiến độ", "progress audit", "tiến độ công việc"],
        inputs={"task_db": "Đường dẫn data/tasks.db"},
        steps=[
            "UNDERSTAND yêu cầu chủ nhân",
            "Query durable_tasks GROUP BY status",
            "Đối chiếu với bằng chứng khác (nếu có)",
            "ADVISE với khuyến nghị có nguồn",
        ],
        tools=["sqlite3", "data/tasks.db"],
        acceptance_criteria=["Số liệu khớp DB nguồn", "Mọi kết luận có nguồn"],
        source_ref="tp_smoke_v6",
        evidence_refs=["procedure:task_progress_audit_tasksdb"],
        initial_status=SkillStatus.IMPLEMENTED_IN_SANDBOX,
    )


class TestRegistration:
    def test_register_creates_proposed_or_sandbox(self, registry):
        skill = _register_sample(registry)
        assert skill.status == SkillStatus.IMPLEMENTED_IN_SANDBOX
        assert skill.skill_id.startswith("skill_")
        assert len(registry.list_skills()) == 1

    def test_register_requires_steps_and_criteria(self, registry):
        with pytest.raises(ValueError):
            registry.register_skill(
                name="X", goal="g", trigger_patterns=[], inputs={},
                steps=[], tools=[], acceptance_criteria=[],
            )
        with pytest.raises(ValueError):
            registry.register_skill(
                name="X", goal="g", trigger_patterns=[], inputs={},
                steps=["s1"], tools=[], acceptance_criteria=[],
            )

    def test_register_rejects_starting_available(self, registry):
        """Không cho đăng ký skill mới ngay lập tức là AVAILABLE (fail-closed)."""
        with pytest.raises(ValueError):
            registry.register_skill(
                name="X", goal="g", trigger_patterns=[], inputs={},
                steps=["s"], tools=[], acceptance_criteria=["c"],
                initial_status=SkillStatus.AVAILABLE,
            )


class TestLifecycle:
    def test_valid_transition_chain(self, registry):
        skill = _register_sample(registry)
        # sandbox -> tested -> approved -> available (evidence đã có từ register)
        registry.transition(skill.skill_id, SkillStatus.TESTED, reason="16 tests pass")
        registry.transition(skill.skill_id, SkillStatus.APPROVED, reason="owner approved")
        out = registry.transition(skill.skill_id, SkillStatus.AVAILABLE, reason="activated")
        assert out.status == SkillStatus.AVAILABLE
        assert any("-> AVAILABLE" in n for n in out.change_notes)

    def test_skip_transition_rejected(self, registry):
        """Nhảy cóc PROPOSED -> AVAILABLE bị chặn."""
        skill = _register_sample(registry, name="JUMPER")
        with pytest.raises(ValueError):
            registry.transition(skill.skill_id, SkillStatus.AVAILABLE, reason="nhảy cóc")

    def test_available_without_evidence_rejected(self, registry):
        skill = registry.register_skill(
            name="NO_EVIDENCE", goal="g", trigger_patterns=[], inputs={},
            steps=["s"], tools=[], acceptance_criteria=["c"],
            initial_status=SkillStatus.PROPOSED,
        )
        # PROPOSED -> IMPLEMENTED_IN_SANDBOX (hợp lệ)
        registry.transition(skill.skill_id, SkillStatus.IMPLEMENTED_IN_SANDBOX, reason="built")
        # IMPLEMENTED_IN_SANDBOX -> TESTED hợp lệ, nhưng TESTED -> APPROVED cần evidence
        registry.transition(skill.skill_id, SkillStatus.TESTED, reason="tested")
        with pytest.raises(ValueError):
            registry.transition(skill.skill_id, SkillStatus.APPROVED, reason="không có evidence")

    def test_transition_requires_reason(self, registry):
        skill = _register_sample(registry)
        with pytest.raises(ValueError):
            registry.transition(skill.skill_id, SkillStatus.TESTED, reason="  ")

    def test_unknown_skill_rejected(self, registry):
        with pytest.raises(KeyError):
            registry.transition("skill_khongtontai", SkillStatus.TESTED, reason="r")


class TestMatching:
    def test_find_matching_returns_only_usable(self, registry):
        """Chỉ skill APPROVED/AVAILABLE/TESTED được match — PROPOSED không."""
        _register_sample(registry)
        matches = registry.find_matching_skills("Cho em kiểm tra tiến độ các công việc")
        # skill đang IMPLEMENTED_IN_SANDBOX -> không match
        assert matches == []
        registry.transition(list(registry.list_skills())[0].skill_id, SkillStatus.TESTED, reason="ok")
        matches = registry.find_matching_skills("Cho em kiểm tra tiến độ các công việc")
        assert len(matches) == 1
        assert matches[0].name == "TASK_PROGRESS_AUDIT"

    def test_no_match_returns_empty(self, registry):
        _register_sample(registry)
        registry.transition(list(registry.list_skills())[0].skill_id, SkillStatus.TESTED, reason="ok")
        assert registry.find_matching_skills("hôm nay thời tiết thế nào") == []


class TestPersistence:
    def test_round_trip(self, registry, registry_path):
        skill = _register_sample(registry)
        registry2 = SkillRegistry(registry_path)
        loaded = registry2.get_skill(skill.skill_id)
        assert loaded is not None
        assert loaded.name == "TASK_PROGRESS_AUDIT"
        assert loaded.steps == skill.steps

    def test_corrupt_file_fail_honest(self, registry_path):
        """File hỏng -> backup + raise, không im lặng trả registry rỗng."""
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{khong phai json", encoding="utf-8")
        with pytest.raises(ValueError):
            SkillRegistry(registry_path)
        backup = registry_path.with_suffix(".json.corrupt")
        assert backup.exists()

    def test_missing_file_starts_empty(self, registry_path):
        reg = SkillRegistry(registry_path)
        assert reg.list_skills() == []
