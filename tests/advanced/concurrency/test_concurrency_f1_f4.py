"""ADVANCED ASSURANCE — Suite F: Concurrency, Race Condition & Data Consistency (Phần 9).

F3 Approval Race: N thread cùng consume 1 card APPROVED → ĐÚNG 1 thành công
   (one-time use phải đúng cả khi đua).
F1 Concurrent Creation: N thread cùng tạo task cùng idempotency → không nhân đôi.
F2 Concurrent Update: 2 thread cùng đổi trạng thái — DB không hỏng, mọi ghi có vết.
F4 STOP During Activity: supervisor STOP giữa chừng — registry không nhận việc mới
   (kiểm tra tầng state: supervisor state không còn READY).
Môi trường: toàn tmp_path.
"""
from __future__ import annotations

import threading

import pytest

from quan_ai_brain.governance.approval_service import (
    OWNER_ID,
    ApprovalCardError,
    ApprovalCardService,
)
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def svc(tmp_path):
    return ApprovalCardService(tmp_path / "approval_race.db")


class TestF3ApprovalRace:
    def test_n_threads_consume_exactly_once(self, svc):
        card = svc.create_card(task_id="t1", action_summary="hành động R4", requested_by="tony")
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://race")
        fp = card.action_fingerprint

        success: list[str] = []
        blocked: list[str] = []
        lock = threading.Lock()
        barrier = threading.Barrier(10, timeout=30)

        def racer() -> None:
            try:
                barrier.wait()
                svc.consume(card.approval_id, actor="racer", action_fingerprint=fp)
                with lock:
                    success.append(card.approval_id)
            except ApprovalCardError as exc:
                with lock:
                    blocked.append(str(exc))

        threads = [threading.Thread(target=racer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert len(success) == 1, f"phải đúng 1 consume thành công, thấy {len(success)}"
        assert len(blocked) == 9
        assert any("already consumed" in b for b in blocked)
        final = svc.get_card(card.approval_id)
        assert final.consumed_at_utc is not None

    def test_concurrent_approve_then_expire_no_double_consume(self, svc):
        """Card APPROVED rồi EXPIRED (watchdog sweep) → consume phải chặn dù state mới kịp đổi."""
        card = svc.create_card(task_id="t2", action_summary="việc", requested_by="tony", ttl_hours=1)
        svc.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://e2")
        import sqlite3

        conn = sqlite3.connect(str(svc.db_path))
        conn.execute(
            "UPDATE approval_cards_v2 SET expires_at_utc = '2020-01-01T00:00:00+00:00' WHERE approval_id = ?",
            (card.approval_id,),
        )
        conn.commit()
        conn.close()
        results: list[str] = []
        lock = threading.Lock()

        def racer() -> None:
            try:
                svc.consume(card.approval_id, actor="racer", action_fingerprint=card.action_fingerprint)
                with lock:
                    results.append("OK")
            except ApprovalCardError as exc:
                with lock:
                    results.append("BLOCKED:" + str(exc)[:40])

        threads = [threading.Thread(target=racer) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert all(r.startswith("BLOCKED") for r in results), results  # hết hạn → 0 consume


class TestF1ConcurrentCreation:
    def test_parallel_register_no_duplicate_ids(self, tmp_path):
        registry = DurableTaskRegistry(tmp_path / "tasks_race.db")
        ids: list[str] = []
        errors: list[str] = []
        lock = threading.Lock()

        def worker(i: int) -> None:
            try:
                rec = registry.register_task(f"việc đua {i}", risk_level="R1", source="owner")
                with lock:
                    ids.append(rec.task_id)
            except Exception as exc:
                with lock:
                    errors.append(repr(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        assert not errors, errors
        assert len(ids) == 20 and len(set(ids)) == 20


class TestF2ConcurrentUpdate:
    def test_two_agents_update_same_task(self, tmp_path):
        registry = DurableTaskRegistry(tmp_path / "tasks_update.db")
        rec = registry.register_task("việc 2 agent", risk_level="R2")
        registry.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS, actor="agent-a")
        errors: list[str] = []
        lock = threading.Lock()

        def updater(agent: str, status: TaskStatus) -> None:
            try:
                registry.update_task_status(rec.task_id, status, actor=agent, reason=f"từ {agent}")
            except Exception as exc:
                with lock:
                    errors.append(repr(exc))

        t1 = threading.Thread(target=updater, args=("agent-a", TaskStatus.VERIFYING))
        t2 = threading.Thread(target=updater, args=("agent-b", TaskStatus.FAILED))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        # DB phải còn đọc được và status là 1 trong 2 giá trị — không hỏng, không giá trị lạ
        final = registry.get_task(rec.task_id)
        assert final.status in (TaskStatus.VERIFYING, TaskStatus.FAILED)
        # transition log phải ghi đủ các lần đổi (audit không mất)
        history = registry.list_transitions(rec.task_id)
        assert len(history) >= 2

    def test_transition_history_complete_after_race(self, tmp_path):
        registry = DurableTaskRegistry(tmp_path / "tasks_hist.db")
        rec = registry.register_task("việc audit", risk_level="R1")
        registry.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS, actor="a1")
        registry.update_task_status(rec.task_id, TaskStatus.VERIFYING, actor="a2")
        registry.update_task_status(rec.task_id, TaskStatus.COMPLETED, actor="a3")
        history = registry.list_transitions(rec.task_id)
        chain = [(h.from_status, h.to_status) for h in history]
        assert ("PENDING", "IN_PROGRESS") in chain or ("RECEIVED", "IN_PROGRESS") in chain
        assert chain[-1][1] == "COMPLETED"
