"""ADVANCED ASSURANCE — Suite E: Chaos Engineering & Fault Injection (Phần 8).

Môi trường: mọi registry/service dùng tmp_path — không đụng DB production.
Không restart service thật; chỉ mô phỏng ở tầng object.

E1 LLM Failure: provider fallback matrix — offline/model lỗi/response rỗng →
   is_mock đúng như cấu hình, KHÔNG fake câu trả lời (fail-honest).
E2 Database Failure: SQLite busy → khoá ghi ngắn không mất dữ liệu; corrupted
   test DB → mở không được phải báo lỗi rõ, không nuốt.
E5 Service Restart: task IN_PROGRESS qua "restart" (mở registry mới trên cùng
   file) → recover_tasks phân loại đúng, không thực thi trùng (không tự đưa
   IN_PROGRESS cũ về chạy lại).
E6 Partial Failure: task nhiều bước, 1 bước lỗi → trạng thái phản ánh đúng
   mức hoàn thành (không COMPLETED trắng).
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from quan_ai_brain.llm.provider import FallbackMode, LLMProvider
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def registry(tmp_path):
    return DurableTaskRegistry(tmp_path / "tasks_chaos.db")


# ---------------------------------------------------------------------------
# E1 — LLM Failure (provider thật, không đụng mạng: endpoint không tồn tại)
# ---------------------------------------------------------------------------
class TestE1LLMFailure:
    def _provider(self, tmp_path, mode):
        return LLMProvider(
            client=None,  # sẽ tự tạo OllamaClient trỏ endpoint chết bên dưới
            fallback_mode=mode,
            default_model="nonexistent-model",
        )

    def test_offline_never_reports_mock_as_llm(self):
        from quan_ai_brain.llm.client import OllamaClient

        dead = OllamaClient(base_url="http://127.0.0.1:1")  # port không thể mở
        p = LLMProvider(client=dead, fallback_mode=FallbackMode.NEVER, default_model="nonexistent-model")
        assert p.is_online() is False
        h = p.health()
        assert h["ollama_online"] is False
        assert h["active_provider"] == "none"  # NEVER mode: không fallback, không fake

    def test_offline_with_mock_fallback_is_marked_mock(self):
        from quan_ai_brain.llm.client import OllamaClient

        dead = OllamaClient(base_url="http://127.0.0.1:1")
        p = LLMProvider(client=dead, fallback_mode=FallbackMode.ON_ERROR, default_model="nonexistent-model")
        h = p.health()
        assert h["ollama_online"] is False
        # fail-honest: health phải nói rõ active provider là mock (không giả làm LLM thật)
        assert h["active_provider"] == "mock"
        assert h["fallback_mode"] == "on_error"


# ---------------------------------------------------------------------------
# E2 — Database Failure
# ---------------------------------------------------------------------------
class TestE2DatabaseFailure:
    def test_concurrent_writes_no_data_loss(self, registry):
        """SQLite busy: 8 thread ghi song song — mọi task đăng ký phải còn nguyên."""
        errors: list[str] = []
        ids: list[str] = []

        def worker(i: int) -> None:
            try:
                rec = registry.register_task(f"task song song {i}", risk_level="R1")
                ids.append(rec.task_id)
            except Exception as exc:  # pragma: no cover
                errors.append(repr(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert not errors, errors
        assert len(set(ids)) == 8  # không mất, không trùng

    def test_corrupted_test_db_reports_clearly(self, tmp_path):
        db = tmp_path / "corrupt.db"
        db.write_bytes(b"this is not a sqlite database" * 100)
        with pytest.raises(Exception):
            DurableTaskRegistry(db)  # phải nổ rõ, không nuốt im lặng

    def test_transaction_atomicity_on_bad_transition(self, registry):
        rec = registry.register_task("t atomic", risk_level="R1")
        registry.update_task_status(rec.task_id, TaskStatus.COMPLETED, actor="chaos", reason="x")
        terminal = registry.get_task(rec.task_id)
        assert terminal.status == TaskStatus.COMPLETED
        # verify_task trên task chưa VERIFYING/COMPLETED_* phải từ chối rõ (fail-honest)
        rec2 = registry.register_task("t verify sai trạng thái", risk_level="R1")
        with pytest.raises(ValueError, match="verify_task requires"):
            registry.verify_task(rec2.task_id, evidence_ok=True)
        still = registry.get_task(rec2.task_id)
        assert still.status in (TaskStatus.RECEIVED, TaskStatus.PENDING)  # dữ liệu không bị ghi đè sai


# ---------------------------------------------------------------------------
# E5 — Service Restart / Recovery
# ---------------------------------------------------------------------------
class TestE5RestartRecovery:
    def test_reopen_registry_keeps_tasks(self, tmp_path):
        db = tmp_path / "tasks_restart.db"
        r1 = DurableTaskRegistry(db)
        rec = r1.register_task("nhiệm vụ qua restart", risk_level="R2")
        r1.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS, actor="chaos")

        r2 = DurableTaskRegistry(db)  # "restart" — instance mới trên cùng file
        loaded = r2.get_task(rec.task_id)
        assert loaded is not None
        assert loaded.status == TaskStatus.IN_PROGRESS
        assert loaded.goal == "nhiệm vụ qua restart"

    def test_recover_in_progress_not_reexecuted(self, tmp_path):
        """IN_PROGRESS cũ sau restart phải được phân loại chờ quyết định —
        KHÔNG tự quay lại chạy (chống thực thi trùng, Phần 5.5 prompt DEOM)."""
        db = tmp_path / "tasks_recover.db"
        r1 = DurableTaskRegistry(db)
        rec = r1.register_task("việc dang dở", risk_level="R2")
        r1.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS, actor="chaos")

        r2 = DurableTaskRegistry(db)
        recovered = r2.recover_in_flight_tasks()  # supervisor.initialize() gọi hàm này
        assert rec.task_id in [t.task_id for t in recovered]
        loaded = r2.get_task(rec.task_id)
        # sau recovery KHÔNG được giữ IN_PROGRESS như thể đang chạy an toàn:
        # phải chuyển sang OUTCOME_UNKNOWN (chờ owner/verifier quyết định)
        assert loaded.status == TaskStatus.OUTCOME_UNKNOWN


# ---------------------------------------------------------------------------
# E6 — Partial Failure: mức hoàn thành phải trung thực
# ---------------------------------------------------------------------------
class TestE6PartialFailure:
    def test_failed_step_not_reported_completed(self, registry):
        rec = registry.register_task("nhiệm vụ 3 bước", risk_level="R2")
        registry.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS, actor="chaos")
        # 1 bước lỗi → task FAILED (không COMPLETED)
        registry.update_task_status(
            rec.task_id, TaskStatus.FAILED, actor="chaos",
            error_message="bước 2/3 lỗi: API timeout",
        )
        loaded = registry.get_task(rec.task_id)
        assert loaded.status == TaskStatus.FAILED
        assert loaded.error_message and "timeout" in loaded.error_message

    def test_partial_completion_is_distinct_state(self, registry):
        rec = registry.register_task("nhiệm vụ một phần", risk_level="R2")
        registry.update_task_status(
            rec.task_id, TaskStatus.COMPLETED_PARTIALLY, actor="chaos",
            result_payload={"done_steps": 2, "total_steps": 3},
        )
        loaded = registry.get_task(rec.task_id)
        assert loaded.status == TaskStatus.COMPLETED_PARTIALLY  # KHÔNG phải COMPLETED
        assert loaded.result_payload["done_steps"] == 2
