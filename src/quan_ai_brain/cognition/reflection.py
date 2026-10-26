"""QUAN AI BRAIN — Reflection Loop (Sprint B).

Evidence-based reflection per Master Prompt Part 3.2: the 12 mandatory
questions are answered by querying durable execution history
(tasks.db + logs/audit.jsonl + episodes), NOT by letting an LLM narrate
its own success.

Output contract:
- lessons_verified: backed by task outcome/evidence in the registry.
- lessons_hypothesis: plausible but unproven — these go to quarantine and
  MUST NOT be promoted to semantic memory without owner approval.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


class ReflectionLoop:
    """Answers the 12 mandatory reflection questions from durable data."""

    def __init__(
        self,
        workspace: str | Path | None = None,
        task_registry: DurableTaskRegistry | None = None,
        memory_store_factory: Any = None,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        self.registry = task_registry
        self._memory_store_factory = memory_store_factory
        if self.registry is None:
            from quan_ai_brain.orchestration.task_registry import (
                DurableTaskRegistry as _Reg,
            )

            self.registry = _Reg(self.workspace / "data" / "tasks.db", workspace=self.workspace)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reflect_task(self, task_id: str) -> dict[str, Any]:
        task = self.registry.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found")

        steps = self.registry.list_steps_for_task(task_id)
        failed_steps = [s for s in steps if s.status == TaskStatus.FAILED]
        blocked_steps = [s for s in steps if s.status == TaskStatus.BLOCKED]
        approved_tickets = [
            s for s in steps if s.status == TaskStatus.WAITING_APPROVAL
        ]

        now = datetime.now(timezone.utc).isoformat()
        terminal = task.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.BLOCKED,
            TaskStatus.OUTCOME_UNKNOWN,
        )

        answers: dict[str, Any] = {
            # Q1: mục tiêu ban đầu
            "q1_original_goal": task.goal,
            # Q2: đạt được phần nào
            "q2_achieved": {
                "status": task.status.value,
                "steps_total": len(steps),
                "steps_completed": sum(
                    1 for s in steps if s.status == TaskStatus.COMPLETED
                ),
                "terminal": terminal,
            },
            # Q3: bằng chứng xác nhận kết quả
            "q3_evidence": task.evidence_refs
            + [s.result_payload for s in steps if s.result_payload],
            # Q4/Q5: quyết định hiệu quả/sai — chỉ khẳng định khi có outcome thật
            "q4_effective_decisions": self._effective_decisions(task, steps),
            "q5_wrong_or_unnecessary": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "error": s.error_message,
                }
                for s in failed_steps
            ]
            or ("CHƯA CÓ DỮ LIỆU ĐỦ" if not failed_steps else []),
            # Q6: dữ liệu/giả định sai — từ error messages (thực đo)
            "q6_bad_data_or_assumptions": [
                s.error_message for s in failed_steps + blocked_steps if s.error_message
            ]
            or "CHƯA CÓ DỮ LIỆU ĐỦ",
            # Q7: vi phạm giới hạn — R5 step bị chặn là dấu hiệu policy hoạt động
            "q7_boundary_violations": [
                {"step_id": s.step_id, "error": s.error_message}
                for s in blocked_steps
                if s.error_message and "R5" in (s.error_message or "")
            ],
            # Q8: lỗi lặp lại (so sánh error message giữa các step)
            "q8_recurring_errors": self._recurring_errors(steps),
            # Q9: cần bổ sung tri thức/công cụ nào
            "q9_missing_knowledge_or_tools": self._missing_capabilities(task, steps),
            # Q10/Q11: bài học — phân loại verified vs hypothesis
            "q10_lessons": self._lessons(task, steps),
            "q11_lessons_hypothesis_only": self._hypotheses(task, steps),
            # Q12: đề xuất cần owner duyệt
            "q12_proposals_need_approval": (
                [
                    {"step_id": s.step_id, "name": s.name, "reason": s.error_message}
                    for s in steps
                    if s.requires_approval and s.status != TaskStatus.COMPLETED
                ]
                + (["promotion_of_lessons_to_semantic_memory"] if task.status == TaskStatus.COMPLETED else [])
            ),
        }

        return {
            "task_id": task_id,
            "reflected_at": now,
            "task_status": task.status.value,
            "goal": task.goal,
            "answers": answers,
            "lessons_verified": answers["q10_lessons"],
            "lessons_hypothesis": answers["q11_lessons_hypothesis_only"],
            "proposals_need_approval": answers["q12_proposals_need_approval"],
        }

    def persist_lessons(
        self, task_id: str, memory_store: Any | None = None
    ) -> dict[str, Any]:
        """LEARNING_CANDIDATE: verified lessons -> episodic memory;
        hypotheses -> quarantine (candidate_knowledge), never semantic."""
        report = self.reflect_task(task_id)

        stored: dict[str, Any] = {"episodic": [], "quarantined": 0}
        store = memory_store or self._open_memory_store()
        if store is None:
            stored["error"] = "memory store unavailable; lessons kept in report only"
            return {"task_id": task_id, **stored, "report": report}

        for lesson in report["lessons_verified"]:
            try:
                episode_id = store.add_episode(
                    summary=f"[LESSON][{task_id}] {lesson}",
                    kind="lesson",
                    source_ref=f"cognitive_loop:{task_id}",
                    status="verified",
                )
                stored["episodic"].append(episode_id)
            except Exception:
                continue

        # Hypotheses go to candidate_knowledge quarantine when a compatible
        # store is available; otherwise they stay only in the report.
        stored["quarantined"] = self._quarantine_hypotheses(task_id, report)
        return {"task_id": task_id, **stored, "report": report}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _open_memory_store(self) -> Any | None:
        try:
            if self._memory_store_factory is not None:
                return self._memory_store_factory()
            from quan_ai_brain.memory.sqlite_store import MemoryStore

            db = self.workspace / "data" / "brain.db"
            if not db.exists():
                return None
            return MemoryStore(db, workspace=self.workspace)
        except Exception:
            return None

    def _quarantine_hypotheses(self, task_id: str, report: dict[str, Any]) -> int:
        try:
            import sqlite3
            import uuid

            db = self.workspace / "data" / "brain.db"
            if not db.exists() or not report["lessons_hypothesis"]:
                return 0
            conn = sqlite3.connect(str(db))
            try:
                count = 0
                for hyp in report["lessons_hypothesis"]:
                    conn.execute(
                        """
                        INSERT INTO candidate_knowledge(
                            id, statement, source_type, source_ref, rationale,
                            status, created_at_utc
                        ) VALUES(?,?,?,?,?, 'quarantined', ?)
                        """,
                        (
                            f"hyp_{uuid.uuid4().hex[:12]}",
                            f"[HYPOTHESIS][{task_id}] {hyp}",
                            "reflection",
                            f"cognitive_loop:{task_id}",
                            "Auto-quarantined reflection hypothesis; needs owner verification",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    count += 1
                conn.commit()
                return count
            finally:
                conn.close()
        except Exception:
            return 0

    @staticmethod
    def _effective_decisions(task: Any, steps: list[Any]) -> list[str] | str:
        if task.status == TaskStatus.COMPLETED and steps:
            return [f"step '{s.name}' verified OK" for s in steps if s.status == TaskStatus.COMPLETED]
        return "CHƯA CÓ DỮ LIỆU ĐỦ"

    @staticmethod
    def _recurring_errors(steps: list[Any]) -> list[str] | str:
        seen: dict[str, int] = {}
        for s in steps:
            err = (s.error_message or "").split(":")[0].strip()
            if err:
                seen[err] = seen.get(err, 0) + 1
        recurring = [f"{k} (x{v})" for k, v in seen.items() if v > 1]
        return recurring or "CHƯA CÓ DỮ LIỆU ĐỦ"

    @staticmethod
    def _missing_capabilities(task: Any, steps: list[Any]) -> list[str] | str:
        missing: list[str] = []
        for s in steps:
            msg = (s.error_message or "").lower()
            if "not found" in msg or "missing" in msg or "không tìm thấy" in msg:
                missing.append(s.name)
        if task.status == TaskStatus.BLOCKED and not missing:
            missing.append("dependency or approval required")
        return missing or "CHƯA CÓ DỮ LIỆU ĐỦ"

    @staticmethod
    def _lessons(task: Any, steps: list[Any]) -> list[str]:
        lessons: list[str] = []
        if task.status == TaskStatus.COMPLETED:
            lessons.append(
                f"Task '{task.goal}' completed with {len(steps)} verified steps in inert sandbox."
            )
        for s in steps:
            if s.status == TaskStatus.FAILED and s.error_message:
                lessons.append(
                    f"Step '{s.name}' failed: {s.error_message}. Next time verify prerequisites before planning this step."
                )
        return lessons

    @staticmethod
    def _hypotheses(task: Any, steps: list[Any]) -> list[str]:
        hyps: list[str] = []
        if task.status == TaskStatus.COMPLETED:
            hyps.append(
                "Same plan shape will succeed for similar goals (UNPROVEN — requires more samples)."
            )
        for s in steps:
            if s.status == TaskStatus.BLOCKED and "R4" in (s.error_message or ""):
                hyps.append(
                    f"Step '{s.name}' blocked on R4 approval; approval latency may be the bottleneck (UNPROVEN)."
                )
        return hyps
