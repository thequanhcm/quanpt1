"""DEOM M3 — AgentDispatcher: chọn agent theo capability + risk + workload.

Thiết kế: reports/DEOM_M3_DESIGN.md (§2). Nguyên tắc:
- Deterministic, KHÔNG dùng AI/LLM khi chọn.
- R3/R4/R5 KHÔNG BAO GIỜ tự gán cho agent nào (phải qua approval_verifier trước).
- 1 agent giữ tối đa max_concurrent task (mặc định 1) — anti-overload.
- Task source='learning' chỉ agent có capability 'learning' nhận.
- Không tìm được agent → trả None, task ở lại queue (không ép chạy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import Any

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.orchestration.models import TaskRecord
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

# Mức rủi ro KHÔNG BAO GIỜ được dispatcher tự gán — luôn chờ owner duyệt
# (approval_verifier fail-closed) trước khi vào execution.
NEVER_AUTO_ASSIGN_RISKS = ("R3", "R4", "R5")


def make_registry_recorder(registry: DurableTaskRegistry):
    """Callback ghi assignment vào registry (assigned_agents_json + transition).

    Trả về callable(task_id, agent_id, reason) → None nếu OK, chuỗi lỗi nếu fail.
    """

    def _record(task_id: str, agent_id: str, reason: str) -> str | None:
        try:
            registry.assign_agent(task_id, agent_id, actor="dispatcher", reason=reason)
            return None
        except Exception as exc:  # noqa: BLE001 — fail-honest: báo lỗi ra ngoài
            return f"registry assign failed: {exc}"

    return _record


@dataclass
class AgentProfile:
    """Hồ sơ năng lực một agent trong pool của Dispatcher."""

    agent_id: str
    capabilities: list[str] = field(default_factory=list)
    max_concurrent: int = 1
    allowed_risks: list[str] = field(default_factory=lambda: ["R0", "R1", "R2"])
    current_tasks: list[str] = field(default_factory=list)
    source_filter: list[str] | None = None  # None = nhận mọi nguồn

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "capabilities": list(self.capabilities),
            "max_concurrent": self.max_concurrent,
            "allowed_risks": list(self.allowed_risks),
            "current_tasks": list(self.current_tasks),
            "source_filter": list(self.source_filter) if self.source_filter else None,
        }


class DispatchResult:
    """Kết quả dispatch: agent được chọn hoặc lý do không ai nhận."""

    def __init__(self, agent: AgentProfile | None, reason: str = "", recorder: Any = None) -> None:
        self.agent = agent
        self.reason = reason
        self.recorder = recorder  # callable(task_id, agent_id, reason) hoặc None

    @property
    def ok(self) -> bool:
        return self.agent is not None

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        if self.agent:
            return f"DispatchResult(agent={self.agent.agent_id})"
        return f"DispatchResult(None, reason={self.reason!r})"


class AgentDispatcher:
    """Chọn agent cho task theo năng lực kiểm chứng — DEOM §6.3.

    Pool agent do caller đăng ký (supervisor giữ danh sách tĩnh, không tự
    khám phá). Chọn deterministic: capability ⊇ required_tools, risk cho phép,
    còn chỗ, workload thấp nhất; hòa thì theo thứ tự đăng ký.
    """

    def __init__(self, agents: list[AgentProfile] | None = None) -> None:
        self._agents: list[AgentProfile] = list(agents or [])

    # ------------------------------------------------------------------
    # Quản lý pool
    # ------------------------------------------------------------------
    def register_agent(self, profile: AgentProfile) -> AgentProfile:
        """Đăng ký agent; trùng agent_id → thay thế (idempotent)."""
        for i, existing in enumerate(self._agents):
            if existing.agent_id == profile.agent_id:
                self._agents[i] = profile
                return profile
        self._agents.append(profile)
        return profile

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        for agent in self._agents:
            if agent.agent_id == agent_id:
                return agent
        return None

    def list_agents(self) -> list[AgentProfile]:
        return list(self._agents)

    # ------------------------------------------------------------------
    # Chọn agent
    # ------------------------------------------------------------------
    def dispatch(
        self,
        task: TaskRecord,
        *,
        registry: DurableTaskRegistry | None = None,
    ) -> DispatchResult:
        """Chọn agent phù hợp nhất cho task. Không thay đổi trạng thái task.

        registry truyền vào → supervisor dùng chung callback ghi assignment
        (mỗi DispatchResult giữ recorder, assign() tự ghi nếu caller không truyền).
        """
        risk = str(task.risk_level).upper()
        if risk in NEVER_AUTO_ASSIGN_RISKS:
            return DispatchResult(
                None, f"risk {risk} requires owner approval — dispatcher never auto-assigns"
            )

        if not self._agents:
            return DispatchResult(None, "no agents registered")

        candidates: list[tuple[int, AgentProfile]] = []
        for idx, agent in enumerate(self._agents):
            # 1. capability
            missing = [tool for tool in task.required_tools if tool not in agent.capabilities]
            if missing:
                continue
            # 2. risk
            if agent.allowed_risks and risk not in [r.upper() for r in agent.allowed_risks]:
                continue
            # 3. chỗ trống
            if len(agent.current_tasks) >= max(1, agent.max_concurrent):
                continue
            # 4. nguồn
            if agent.source_filter is not None and task.source not in agent.source_filter:
                continue
            candidates.append((idx, agent))

        if not candidates:
            return DispatchResult(None, "no eligible agent (capability/risk/capacity/source)")

        # 5. workload thấp nhất; 6. hòa → thứ tự đăng ký (idx nhỏ hơn thắng)
        candidates.sort(key=lambda pair: (len(pair[1].current_tasks), pair[0]))
        chosen = candidates[0][1]
        result = DispatchResult(chosen)
        if registry is not None:
            result.recorder = make_registry_recorder(registry)
        return result

    # ------------------------------------------------------------------
    # Assignment + release (audit qua transition log của registry)
    # ------------------------------------------------------------------
    def conflict_check(self, task: TaskRecord, agent: AgentProfile) -> str | None:
        """Trả về lý do conflict hoặc None nếu an toàn.

        Anti-conflict: agent đang giữ task khác có cùng goal (chuẩn hoá) hoặc
        task là cha/con của task đang giữ → không nhận thêm.
        """
        goal_norm = redact_text(task.goal.strip().lower())
        for held_id in agent.current_tasks:
            if held_id == task.task_id:
                return f"agent {agent.agent_id} already holds this task"
            if task.parent_task_id and task.parent_task_id == held_id:
                return f"agent {agent.agent_id} holds parent task {held_id}"
            # goal trùng (sau redaction) → lệnh trái ngược khả năng cao
            for other in self._held_goal_cache.values():
                if other == goal_norm and held_id != task.task_id:
                    return f"agent {agent.agent_id} already holds a task with the same goal"
        return None

    # cache goal các task đang giữ (điền qua assign; không persist — in-memory)
    _held_goal_cache: dict[str, str] = {}

    def assign(
        self,
        task: TaskRecord,
        agent: AgentProfile,
        *,
        assign_task: Any = None,
    ) -> str | None:
        """Gán task cho agent. Trả về None nếu OK, chuỗi lý do nếu từ chối.

        assign_task: callable(task_id, agent_id, reason) — caller (supervisor)
        truyền vào để ghi `assigned_agents_json` + transition qua registry
        (Dispatcher không giữ connection DB). Conflict → KHÔNG gán.
        Mặc định (không truyền assign_task): tự ghi transition qua registry của
        task nếu có thể — dùng callback `_registry_assign_recorder`.
        """
        if agent.agent_id not in {a.agent_id for a in self._agents}:
            return f"agent {agent.agent_id} not registered"
        if len(agent.current_tasks) >= max(1, agent.max_concurrent):
            return f"agent {agent.agent_id} at capacity ({agent.max_concurrent})"
        conflict = self.conflict_check(task, agent)
        if conflict:
            return conflict

        if assign_task is not None:
            err = assign_task(task.task_id, agent.agent_id, f"assigned to {agent.agent_id}")
            if err:
                return err
        agent.current_tasks.append(task.task_id)
        self._held_goal_cache[task.task_id] = redact_text(task.goal.strip().lower())
        return None

    def release(self, task_id: str) -> bool:
        """Gỡ task khỏi mọi agent (khi COMPLETED_*/FAILED/CANCELLED)."""
        released = False
        for agent in self._agents:
            if task_id in agent.current_tasks:
                agent.current_tasks.remove(task_id)
                released = True
        self._held_goal_cache.pop(task_id, None)
        return released
