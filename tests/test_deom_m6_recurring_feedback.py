"""DEOM M6 — Tests: RecurringTaskEngine + TaskFeedbackRecorder.

Nghiệm thu theo DEOM_M6_DESIGN.md §4: parse VN fail-honest, tạo instance
đúng hạn + chống double-run, template không vào work_queue, pause/resume/
remove=R4, feedback idempotent + lesson luôn candidate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from quan_ai_brain.orchestration.models import AutonomyLevel, TaskRecord, TaskStatus
from quan_ai_brain.orchestration.recurring_engine import (
    RecurringParseError,
    RecurringTaskEngine,
    parse_vn_recurring,
)
from quan_ai_brain.orchestration.task_feedback import (
    TaskFeedbackRecorder,
    safe_record_feedback,
)
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def registry(tmp_path):
    return DurableTaskRegistry(tmp_path / "tasks.db")


@pytest.fixture()
def engine(registry):
    return RecurringTaskEngine(registry)


def _mk_task(**kw) -> TaskRecord:
    base = dict(
        task_id=kw.pop("task_id", "task-x"),
        correlation_id="corr-1",
        idempotency_key=kw.pop("idem", "idem-1"),
        goal=kw.pop("goal", "kiểm tra gì đó"),
        risk_level=kw.pop("risk_level", "R1"),
        autonomy_level=kw.pop("autonomy", AutonomyLevel.LEVEL_A),
        status=kw.pop("status", TaskStatus.COMPLETED_VERIFIED),
        created_at_utc=kw.pop("created", "2026-11-02T00:00:00+00:00"),
        updated_at_utc=kw.pop("updated", "2026-11-02T00:05:00+00:00"),
        completed_at_utc=kw.pop("completed", "2026-11-02T00:05:00+00:00"),
    )
    base.update(kw)
    return TaskRecord(**base)


# ===========================================================================
# Parse chu kỳ tiếng Việt
# ===========================================================================
class TestParseRecurring:
    def test_daily_8h_sang(self):
        spec = parse_vn_recurring("chạy báo cáo hằng ngày 8h sáng")
        assert spec["pattern"] == "daily"
        assert spec["hour_vn"] == 8 and spec["minute_vn"] == 0

    def test_daily_8h_chieu_ra_20h(self):
        spec = parse_vn_recurring("hằng ngày lúc 8h chiều")
        assert spec["pattern"] == "daily"
        assert spec["hour_vn"] == 20

    def test_weekly_thu2_9h(self):
        spec = parse_vn_recurring("hằng tuần thứ 2 lúc 9h sáng")
        assert spec["pattern"] == "weekly"
        assert spec["weekday"] == 0 and spec["hour_vn"] == 9

    def test_interval_30_phut(self):
        spec = parse_vn_recurring("kiểm tra mail mỗi 30 phút")
        assert spec["pattern"] == "interval"
        assert spec["interval_minutes"] == 30

    def test_interval_2_gio(self):
        spec = parse_vn_recurring("mỗi 2 giờ sao lưu")
        assert spec["interval_minutes"] == 120

    def test_parse_fail_honest(self):
        with pytest.raises(RecurringParseError):
            parse_vn_recurring("thỉnh thoảng làm gì đó")
        with pytest.raises(RecurringParseError):
            parse_vn_recurring("hằng tuần không nói thứ nào")  # weekly thiếu thứ

    def test_hour_out_of_range(self):
        with pytest.raises(RecurringParseError):
            parse_vn_recurring("hằng ngày 99h")


# ===========================================================================
# Engine: đăng ký + tạo instance
# ===========================================================================
class TestRegisterAndInstances:
    def test_register_creates_template_blocked(self, engine, registry):
        t = engine.register_recurring("kiểm tra pin", "hằng ngày 8h sáng", risk_level="R1")
        spec = t.progress_weight["recurring"]
        assert spec["pattern"] == "daily" and spec["hour_vn"] == 8
        assert spec["enabled"] is True and spec["next_run_utc"]
        assert t.status == TaskStatus.BLOCKED  # template không dispatchable

    def test_template_not_in_work_queue(self, engine, registry):
        t = engine.register_recurring("việc định kỳ", "hằng ngày 8h sáng")
        q = registry.work_queue(limit=50)
        assert t.task_id not in [x.task_id for x in q]

    def test_not_due_yet_no_instance(self, engine, registry):
        t = engine.register_recurring("việc A", "mỗi 60 phút")
        created = engine.create_due_instances()
        assert created == []

    def test_due_creates_one_instance(self, engine, registry):
        t = engine.register_recurring("việc B", "mỗi 60 phút")
        # đẩy next_run về quá khứ 2 phút
        spec = t.progress_weight["recurring"]
        past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        registry.update_progress_weight(
            t.task_id, {**t.progress_weight, "recurring": {**spec, "next_run_utc": past}}
        )
        created = engine.create_due_instances()
        assert len(created) == 1
        inst = created[0]
        assert inst.parent_task_id == t.task_id
        assert "lần 1" in inst.goal
        # next_run đã đẩy về tương lai (60 phút kế)
        t2 = registry.get_task(t.task_id)
        assert datetime.fromisoformat(t2.progress_weight["recurring"]["next_run_utc"]) > datetime.now(timezone.utc)

    def test_double_run_prevented(self, engine, registry):
        t = engine.register_recurring("việc C", "mỗi 60 phút")
        spec = t.progress_weight["recurring"]
        past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        registry.update_progress_weight(
            t.task_id, {**t.progress_weight, "recurring": {**spec, "next_run_utc": past}}
        )
        first = engine.create_due_instances()
        assert len(first) == 1
        # quét ngay lần 2: instance cũ chưa terminal → KHÔNG tạo thêm
        second = engine.create_due_instances()
        assert second == []

    def test_new_instance_after_previous_terminal(self, engine, registry):
        t = engine.register_recurring("việc D", "mỗi 60 phút")
        spec = t.progress_weight["recurring"]
        past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        registry.update_progress_weight(
            t.task_id, {**t.progress_weight, "recurring": {**spec, "next_run_utc": past}}
        )
        first = engine.create_due_instances()
        registry.update_task_status(first[0].task_id, TaskStatus.COMPLETED)
        second = engine.create_due_instances()
        # instance cuối terminal + next_run đã đẩy 60 phút kế (tương lai) → vẫn 0
        assert second == []


class TestPauseResumeRemove:
    def test_pause_blocks_instances(self, engine, registry):
        t = engine.register_recurring("việc E", "mỗi 30 phút")
        engine.pause(t.task_id)
        spec = registry.get_task(t.task_id).progress_weight["recurring"]
        past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        registry.update_progress_weight(
            t.task_id, {**spec, "next_run_utc": past}
        )
        assert engine.create_due_instances() == []

    def test_resume_recomputes_next_run(self, engine, registry):
        t = engine.register_recurring("việc F", "mỗi 30 phút")
        engine.pause(t.task_id)
        engine.resume(t.task_id)
        spec = registry.get_task(t.task_id).progress_weight["recurring"]
        assert spec["enabled"] is True
        assert datetime.fromisoformat(spec["next_run_utc"]) > datetime.now(timezone.utc)

    def test_resume_skips_missed_cycles(self, engine, registry):
        """Resume KHÔNG chạy bù chu kỳ lỡ — next_run tính từ bây giờ."""
        t = engine.register_recurring("việc G", "mỗi 30 phút")
        engine.pause(t.task_id)
        engine.resume(t.task_id)
        spec = registry.get_task(t.task_id).progress_weight["recurring"]
        delta = datetime.fromisoformat(spec["next_run_utc"]) - datetime.now(timezone.utc)
        assert timedelta(0) < delta <= timedelta(minutes=30, seconds=5)

    def test_remove_requires_approval(self, engine, registry):
        t = engine.register_recurring("việc H", "mỗi 30 phút")
        with pytest.raises(ValueError, match="R4"):
            engine.remove(t.task_id, approval_id=None)
        ok = engine.remove(t.task_id, approval_id="appr_card")
        assert ok.progress_weight["recurring"]["removed"] is True
        assert ok.progress_weight["recurring"]["enabled"] is False

    def test_removed_template_no_instances(self, engine, registry):
        t = engine.register_recurring("việc I", "mỗi 30 phút")
        engine.remove(t.task_id, approval_id="appr_card")
        spec = registry.get_task(t.task_id).progress_weight["recurring"]
        past = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        registry.update_progress_weight(t.task_id, {**spec, "next_run_utc": past})
        assert engine.create_due_instances() == []


# ===========================================================================
# TaskFeedbackRecorder
# ===========================================================================
class TestFeedback:
    def test_completed_verified_creates_lesson_candidate(self, tmp_path):
        rec = TaskFeedbackRecorder(tmp_path / "fb.db")
        r = rec.record_feedback(_mk_task())
        assert r is not None and r["lesson_created"] is True
        lessons = rec.lessons_for("task-x")
        assert len(lessons) == 1
        assert lessons[0]["verification_status"] == "candidate"
        assert lessons[0]["kind"] == "success_pattern"

    def test_failed_creates_failure_lesson(self, tmp_path):
        rec = TaskFeedbackRecorder(tmp_path / "fb.db")
        t = _mk_task(status=TaskStatus.FAILED, error_message="HTTP 503 từ API trong khi chạy")
        r = rec.record_feedback(t)
        assert r["outcome"] == "FAILED"
        lessons = rec.lessons_for("task-x")
        assert lessons[0]["kind"] == "failure_cause"
        assert "503" in lessons[0]["lesson"]

    def test_non_terminal_ignored(self, tmp_path):
        rec = TaskFeedbackRecorder(tmp_path / "fb.db")
        t = _mk_task(status=TaskStatus.IN_PROGRESS, completed=None)
        assert rec.record_feedback(t) is None
        assert rec.stats() == {"feedback": 0, "lessons": 0}

    def test_idempotent_same_task(self, tmp_path):
        rec = TaskFeedbackRecorder(tmp_path / "fb.db")
        t = _mk_task()
        first = rec.record_feedback(t)
        second = rec.record_feedback(t)
        assert first is not None and second is None
        assert rec.stats()["feedback"] == 1

    def test_error_message_redacted(self, tmp_path):
        rec = TaskFeedbackRecorder(tmp_path / "fb.db")
        t = _mk_task(
            status=TaskStatus.FAILED,
            error_message="gọi API với Authorization: Bearer supersecrettoken123 trả 401",
        )
        rec.record_feedback(t)
        lesson = rec.lessons_for("task-x")[0]["lesson"]
        assert "supersecrettoken123" not in lesson
        assert "[REDACTED]" in lesson

    def test_safe_wrapper_never_raises(self, tmp_path):
        class Broken:
            def record_feedback(self, task):
                raise RuntimeError("db exploded")

        t = _mk_task()
        out = safe_record_feedback(Broken(), t)  # type: ignore[arg-type]
        assert out is not None and "feedback_failed" in out.get("error", "")
        # None recorder → None (không crash)
        assert safe_record_feedback(None, t) is None

    def test_blocked_task_feedback(self, tmp_path):
        rec = TaskFeedbackRecorder(tmp_path / "fb.db")
        t = _mk_task(status=TaskStatus.BLOCKED, error_message="dependency failed")
        r = rec.record_feedback(t)
        assert r["outcome"] == "BLOCKED"
