"""DEOM M3 — DependencyManager: chặn task chưa đủ điều kiện + mở khóa chuỗi.

Thiết kế: reports/DEOM_M3_DESIGN.md (§3). Nguyên tắc:
- Task có dependencies chỉ eligible khi MỌI dep đã TERMINAL_OK.
- COMPLETED_UNVERIFIED KHÔNG đủ (fail-honest — phụ thuộc chưa có bằng chứng).
- Dep thiếu trong registry → task BLOCKED (không treo im lặng).
- Phát hiện vòng khi đăng ký (cycle → từ chối, không tự cắt).
"""
from __future__ import annotations

from collections import deque
from typing import NamedTuple

from quan_ai_brain.orchestration.models import TERMINAL_OK_STATES, TaskRecord, TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


class EligibilityCheck(NamedTuple):
    """Kết quả kiểm tra điều kiện chạy của một task."""

    ok: bool
    reason: str


_UNBLOCKING_STATES = (TaskStatus.COMPLETED_VERIFIED, TaskStatus.COMPLETED_PARTIALLY, TaskStatus.COMPLETED)


class DependencyManager:
    """Quản lý ràng buộc phụ thuộc giữa durable tasks (DEOM §6.3/§4.4)."""

    def __init__(self, registry: DurableTaskRegistry) -> None:
        self.registry = registry

    # ------------------------------------------------------------------
    # Kiểm tra đủ điều kiện chạy
    # ------------------------------------------------------------------
    def eligible(self, task: TaskRecord) -> EligibilityCheck:
        """Task chỉ READY-to-run khi mọi dependency đã kết thúc CÓ kết quả."""
        deps = list(task.dependencies or [])
        if not deps:
            return EligibilityCheck(True, "no dependencies")

        missing: list[str] = []
        not_done: list[str] = []
        unverified: list[str] = []
        for dep_id in deps:
            dep = self.registry.get_task(dep_id)
            if dep is None:
                missing.append(dep_id)
                continue
            if dep.status in TERMINAL_OK_STATES:
                if dep.status == TaskStatus.COMPLETED_UNVERIFIED:
                    # kết thúc nhưng không có bằng chứng — không đủ tin cậy
                    unverified.append(dep_id)
                continue
            not_done.append(dep_id)

        if missing:
            return EligibilityCheck(False, f"missing dependencies: {', '.join(missing)}")
        if unverified:
            return EligibilityCheck(
                False,
                f"dependencies completed without evidence (fail-honest): {', '.join(unverified)}",
            )
        if not_done:
            return EligibilityCheck(False, f"dependencies not finished: {', '.join(not_done)}")
        return EligibilityCheck(True, "all dependencies satisfied")

    def block_on_missing_dependencies(self, task: TaskRecord, *, actor: str = "dependency_manager") -> TaskRecord | None:
        """Task còn dep thiếu hẳn trong registry → BLOCKED (transition log đầy đủ).

        Trả về TaskRecord nếu đã chuyển BLOCKED, None nếu không cần.
        """
        check = self.eligible(task)
        if check.ok or "missing dependencies" not in check.reason:
            return None
        if task.status == TaskStatus.BLOCKED:
            return None
        return self.registry.update_task_status(
            task.task_id,
            TaskStatus.BLOCKED,
            actor=actor,
            reason=check.reason,
        )

    # ------------------------------------------------------------------
    # Mở khóa task phụ thuộc sau khi task gốc hoàn tất
    # ------------------------------------------------------------------
    def unblock_dependents(self, task_id: str, *, actor: str = "dependency_manager") -> list[TaskRecord]:
        """Khi task hoàn tất (COMPLETED/VERIFIED/PARTIALLY), các task đang chờ nó
        (status BLOCKED hoặc PENDING/READY chưa qua eligibility) → READY nếu mọi
        dependency khác cũng xong."""
        completed = self.registry.get_task(task_id)
        if completed is None or completed.status not in _UNBLOCKING_STATES:
            return []

        # Tìm mọi task có task_id trong dependencies (quét list_tasks — số task nhỏ,
        # chấp nhận O(n); không thêm bảng/cột mới ngoài schema M2).
        waiting_states = (
            TaskStatus.BLOCKED,
            TaskStatus.PENDING,
            TaskStatus.RECEIVED,
        )
        unblocked: list[TaskRecord] = []
        seen: set[str] = set()
        for state in waiting_states:
            for candidate in self.registry.list_tasks(status=state, limit=500):
                if candidate.task_id in seen:
                    continue
                seen.add(candidate.task_id)
                if task_id not in (candidate.dependencies or []):
                    continue
                check = self.eligible(candidate)
                if check.ok:
                    unblocked.append(
                        self.registry.update_task_status(
                            candidate.task_id,
                            TaskStatus.READY,
                            actor=actor,
                            reason=f"dependency satisfied: {task_id} → {completed.status.value}",
                        )
                    )
        return unblocked

    # ------------------------------------------------------------------
    # Phát hiện vòng phụ thuộc (cycle) khi đăng ký
    # ------------------------------------------------------------------
    def would_create_cycle(self, new_task_id: str, dependencies: list[str]) -> bool:
        """DFS: nếu new_task_id đãreachable từ bất kỳ dep nào → cycle."""
        if new_task_id in dependencies:
            return True
        # graph: dep_id -> list dep của nó
        graph: dict[str, list[str]] = {}
        for dep_id in dependencies:
            stack = [dep_id]
            seen: set[str] = set()
            while stack:
                node = stack.pop()
                if node == new_task_id:
                    return True
                if node in seen:
                    continue
                seen.add(node)
                rec = self.registry.get_task(node)
                if rec is not None:
                    stack.extend(rec.dependencies or [])
        return False

    def assert_acyclic(self, new_task_id: str, dependencies: list[str]) -> None:
        """Đăng ký task tạo cycle → ValueError (caller từ chối, không tự cắt vòng)."""
        if self.would_create_cycle(new_task_id, list(dependencies or [])):
            raise ValueError(
                f"registering {new_task_id} with dependencies {dependencies} would create a cycle"
            )

    # ------------------------------------------------------------------
    # Topological order (hữu ích cho planning nhiều task)
    # ------------------------------------------------------------------
    def topological_order(self, task_ids: list[str]) -> list[str]:
        """Trả về thứ tự chạy hợp lệ (deps trước). Có cycle → ValueError."""
        id_set = set(task_ids)
        indeg: dict[str, int] = {tid: 0 for tid in task_ids}
        adjacency: dict[str, list[str]] = {tid: [] for tid in task_ids}
        for tid in task_ids:
            rec = self.registry.get_task(tid)
            if rec is None:
                continue
            for dep in rec.dependencies or []:
                if dep in id_set:
                    adjacency[dep].append(tid)
                    indeg[tid] += 1
        queue = deque(sorted([tid for tid, d in indeg.items() if d == 0]))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in adjacency[node]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(task_ids):
            raise ValueError("dependency cycle detected in topological_order")
        return order
