"""Skill Registry — Master Prompt V6 (§V).

Quản lý Skill nghiệp vụ: quy trình nhiều bước phối hợp tool, có lifecycle
PROPOSED → IMPLEMENTED_IN_SANDBOX → TESTED → APPROVED_IF_REQUIRED → AVAILABLE →
BLOCKED/RETIRED.

Thiết kế:
- Lưu JSON file (data/skill_registry.json) — KHÔNG tạo DB mới, KHÔNG đụng CapabilityRegistry.
- Read-only mặc định; ghi chỉ qua method có kiểm soát (save) và phải có notes.
- Fail-honest: skill chưa test thì status không bao giờ là AVAILABLE.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class SkillStatus(str, Enum):
    PROPOSED = "PROPOSED"
    IMPLEMENTED_IN_SANDBOX = "IMPLEMENTED_IN_SANDBOX"
    TESTED = "TESTED"
    APPROVED = "APPROVED"
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    RETIRED = "RETIRED"


@dataclass
class SkillRecord:
    """Một Skill nghiệp vụ — quy trình tái sử dụng có kiểm chứng."""

    skill_id: str
    name: str
    goal: str
    trigger_patterns: list[str]           # từ khoá/câu mẫu kích hoạt
    inputs: dict[str, str]                # tên -> mô tả
    steps: list[str]                      # quy trình chuẩn
    tools: list[str]                      # tool/connector sử dụng
    acceptance_criteria: list[str]
    status: SkillStatus = SkillStatus.PROPOSED
    version: str = "0.1.0"
    evidence_refs: list[str] = field(default_factory=list)  # bằng chứng kiểm chứng
    known_limits: list[str] = field(default_factory=list)
    source_ref: str = ""                  # pipeline_id / task_id gốc
    created_at: str = ""
    updated_at: str = ""
    change_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SkillRecord:
        d = dict(d)
        d["status"] = SkillStatus(d.get("status", "PROPOSED"))
        return cls(**d)


# Chuyển trạng thái hợp lệ — fail-closed: nhảy cóc không cho phép (trừ APPROVED)
_VALID_TRANSITIONS: dict[SkillStatus, set[SkillStatus]] = {
    SkillStatus.PROPOSED: {SkillStatus.IMPLEMENTED_IN_SANDBOX, SkillStatus.BLOCKED, SkillStatus.RETIRED},
    SkillStatus.IMPLEMENTED_IN_SANDBOX: {SkillStatus.TESTED, SkillStatus.BLOCKED, SkillStatus.RETIRED},
    SkillStatus.TESTED: {SkillStatus.APPROVED, SkillStatus.BLOCKED, SkillStatus.RETIRED},
    SkillStatus.APPROVED: {SkillStatus.AVAILABLE, SkillStatus.BLOCKED, SkillStatus.RETIRED},
    SkillStatus.AVAILABLE: {SkillStatus.BLOCKED, SkillStatus.RETIRED, SkillStatus.TESTED},
    SkillStatus.BLOCKED: {SkillStatus.PROPOSED, SkillStatus.RETIRED},
    SkillStatus.RETIRED: {SkillStatus.PROPOSED},
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class SkillRegistry:
    """Registry Skill lưu JSON file; mọi thay đổi có audit note."""

    def __init__(self, registry_path: Path):
        self.path = Path(registry_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, SkillRecord] = {}
        self._load()

    # ---------- persistence ----------

    def _load(self) -> None:
        if not self.path.exists():
            self._skills = {}
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._skills = {s["skill_id"]: SkillRecord.from_dict(s) for s in data.get("skills", [])}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            # Fail-honest: file hỏng → bắt đầu rỗng nhưng giữ file lại để chủ nhân xem
            self._skills = {}
            self._corrupt_backup = self.path.with_suffix(".json.corrupt")
            self._corrupt_backup.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
            raise ValueError(f"Skill registry file corrupt; backup saved: {exc}") from exc

    def _save(self) -> None:
        data = {
            "version": 1,
            "updated_at": now_utc(),
            "skills": [s.to_dict() for s in self._skills.values()],
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # ---------- API ----------

    def register_skill(
        self,
        name: str,
        goal: str,
        trigger_patterns: list[str],
        inputs: dict[str, str],
        steps: list[str],
        tools: list[str],
        acceptance_criteria: list[str],
        source_ref: str = "",
        evidence_refs: list[str] | None = None,
        known_limits: list[str] | None = None,
        initial_status: SkillStatus = SkillStatus.PROPOSED,
    ) -> SkillRecord:
        if not name.strip() or not goal.strip():
            raise ValueError("name and goal are required")
        if not steps:
            raise ValueError("a skill must define at least one step")
        if not acceptance_criteria:
            raise ValueError("a skill must define acceptance criteria (fail-closed)")
        if initial_status not in (SkillStatus.PROPOSED, SkillStatus.IMPLEMENTED_IN_SANDBOX):
            raise ValueError("new skills must start PROPOSED or IMPLEMENTED_IN_SANDBOX")

        now = now_utc()
        skill = SkillRecord(
            skill_id=f"skill_{uuid.uuid4().hex[:10]}",
            name=name.strip(),
            goal=goal.strip(),
            trigger_patterns=list(trigger_patterns),
            inputs=dict(inputs),
            steps=list(steps),
            tools=list(tools),
            acceptance_criteria=list(acceptance_criteria),
            status=initial_status,
            evidence_refs=list(evidence_refs or []),
            known_limits=list(known_limits or []),
            source_ref=source_ref,
            created_at=now,
            updated_at=now,
            change_notes=[f"{now}: registered as {initial_status.value}"],
        )
        self._skills[skill.skill_id] = skill
        self._save()
        return skill

    def transition(
        self,
        skill_id: str,
        new_status: SkillStatus,
        reason: str,
        evidence_refs: list[str] | None = None,
    ) -> SkillRecord:
        """Chuyển trạng thái có kiểm soát; AVAILABLE bắt buộc đã TESTED và có evidence."""
        skill = self._skills.get(skill_id)
        if skill is None:
            raise KeyError(f"Unknown skill: {skill_id}")
        if not reason or not reason.strip():
            raise ValueError("transition requires a reason (audit trail)")
        allowed = _VALID_TRANSITIONS[skill.status]
        if new_status not in allowed:
            raise ValueError(
                f"Illegal transition {skill.status.value} -> {new_status.value}; allowed: "
                f"{sorted(s.value for s in allowed)}"
            )
        if new_status in (SkillStatus.AVAILABLE, SkillStatus.APPROVED) and not skill.evidence_refs:
            raise ValueError(
                f"{new_status.value} requires verified evidence_refs (fail-closed: no untested skill in production)"
            )
        skill.status = new_status
        skill.updated_at = now_utc()
        skill.change_notes.append(f"{skill.updated_at}: -> {new_status.value}: {reason.strip()}")
        if evidence_refs:
            for r in evidence_refs:
                if r not in skill.evidence_refs:
                    skill.evidence_refs.append(r)
        self._save()
        return skill

    def find_matching_skills(self, request_text: str) -> list[SkillRecord]:
        """Tìm skill khả dụng theo trigger patterns của yêu cầu."""
        q = (request_text or "").lower()
        matches = []
        for skill in self._skills.values():
            if skill.status not in (SkillStatus.AVAILABLE, SkillStatus.APPROVED, SkillStatus.TESTED):
                continue
            if any(p.lower() in q for p in skill.trigger_patterns):
                matches.append(skill)
        return matches

    def get_skill(self, skill_id: str) -> SkillRecord | None:
        return self._skills.get(skill_id)

    def list_skills(self, status: SkillStatus | None = None) -> list[SkillRecord]:
        skills = list(self._skills.values())
        if status is not None:
            skills = [s for s in skills if s.status == status]
        return skills
