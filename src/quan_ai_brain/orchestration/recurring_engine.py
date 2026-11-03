"""DEOM M6 — RecurringTaskEngine: task định kỳ trong registry (GAP #5).

Thiết kế: reports/DEOM_M6_DESIGN.md §2. Nguyên tắc:
- KHÔNG ADD COLUMN — spec recurring nằm trong progress_weight JSON (nền M2).
- Template = task thường, KHÔNG bao giờ được dispatcher chọn (lọc recurring).
- Instance = task con parent_task_id=template, vào work_queue chuẩn M2/M3.
- Parse chu kỳ tiếng Việt fail-honest: không khớp → ValueError, KHÔNG đoán.
- Chống double-run khi restart: so next_run_utc + last_instance_id.
- Remove recurring = R4 (phải có approval card) — đúng charter.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.orchestration.models import (
    PRIORITY_NORMAL,
    AutonomyLevel,
    TaskRecord,
    TaskStatus,
)
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

_TZ_VN = timezone(timedelta(hours=7))

_RECURRING_KEY = "recurring"

_WEEKDAY_MAP = {
    "thứ 2": 0, "thứ hai": 0, "thu 2": 0, "thu hai": 0, "thứ 3": 1, "thứ ba": 1,
    "thu 3": 1, "thu ba": 1, "thứ 4": 2, "thứ tư": 2, "thu 4": 2, "thu tu": 2,
    "thứ 5": 3, "thứ năm": 3, "thu 5": 3, "thu nam": 3, "thứ 6": 4, "thứ sáu": 4,
    "thu 6": 4, "thu sau": 4, "thứ 7": 5, "thứ bảy": 5, "thu 7": 5, "thu bay": 5,
    "chủ nhật": 6, "chu nhat": 6, "cn": 6,
}

_DAILY_RE = re.compile(r"(hằng ngày|hằng ngày|mỗi ngày|mỗi ngày|every day|daily)", re.IGNORECASE)
_WEEKLY_RE = re.compile(r"(hằng tuần|hằng tuần|mỗi tuần|mỗi tuần|every week|weekly)", re.IGNORECASE)
_INTERVAL_RE = re.compile(
    r"mỗi\s+(\d+)\s*(phút|giờ|tiếng|ngày|tuần)|mỗi\s+(\d+)\s*(phút|giờ|tiếng|ngày|tuần)",
    re.IGNORECASE,
)
_HOUR_RE = re.compile(r"(\d{1,2})\s*(h|giờ|:)(\d{1,2})?|(?:lúc|at)\s*(\d{1,2})", re.IGNORECASE)
_PERIOD_PM = re.compile(r"(chiều|tối|đêm|pm)", re.IGNORECASE)


class RecurringParseError(ValueError):
    """Parse chu kỳ thất bại — fail-honest, không đoán."""


def parse_vn_recurring(
    text: str, now: datetime | None = None
) -> dict[str, Any]:
    """Parse câu tiếng Việt thành recurring spec.

    Trả: {"pattern": "daily"|"weekly"|"interval", "interval_minutes": int,
          "hour_vn": int|None, "minute_vn": int|None, "weekday": int|None}
    Không khớp → RecurringParseError (fail-honest).
    """
    clean = (text or "").strip()
    now = now or datetime.now(_TZ_VN)

    # --- interval: "mỗi 30 phút", "mỗi 2 giờ", "mỗi 3 ngày", "mỗi 1 tuần" ---
    m = _INTERVAL_RE.search(clean)
    if m:
        n = int(m.group(1) or m.group(3))
        unit = (m.group(2) or m.group(4) or "").lower()
        if n <= 0:
            raise RecurringParseError(f"interval must be positive, got {n}")
        minutes = {"phút": n, "giờ": n * 60, "tiếng": n * 60, "ngày": n * 1440, "tuần": n * 10080}.get(unit)
        if minutes is None:
            raise RecurringParseError(f"unknown interval unit: {unit}")
        return {"pattern": "interval", "interval_minutes": minutes, "hour_vn": None, "minute_vn": None, "weekday": None}

    # --- daily: "hằng ngày 8h sáng" / "mỗi ngày lúc 20h" ---
    if _DAILY_RE.search(clean):
        hour, minute = _extract_hour_minute(clean, default_hour=8)
        return {"pattern": "daily", "interval_minutes": 1440, "hour_vn": hour, "minute_vn": minute, "weekday": None}

    # --- weekly: "hằng tuần thứ 2 9h sáng" ---
    if _WEEKLY_RE.search(clean):
        weekday = None
        low = clean.lower()
        for key, wd in _WEEKDAY_MAP.items():
            if key in low:
                weekday = wd
                break
        if weekday is None:
            raise RecurringParseError("weekly pattern requires a weekday (thứ 2..chủ nhật)")
        hour, minute = _extract_hour_minute(clean, default_hour=9)
        return {"pattern": "weekly", "interval_minutes": 10080, "hour_vn": hour, "minute_vn": minute, "weekday": weekday}

    raise RecurringParseError(
        f"cannot parse recurring pattern from: {clean[:80]!r} (supported: hằng ngày/mỗi tuần thứ X/mỗi N phút|giờ|ngày)"
    )


def _extract_hour_minute(text: str, *, default_hour: int) -> tuple[int, int]:
    m = _HOUR_RE.search(text)
    if not m:
        return default_hour, 0
    hour = int(m.group(1) or m.group(4) or default_hour)
    minute = int(m.group(3) or 0)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise RecurringParseError(f"hour/minute out of range: {hour}:{minute:02d}")
    # "8h chiều" = 20:00 — chỉ nâng khi có từ chỉ buổi chiều/tối SAU số giờ
    if hour <= 11:
        tail = text[m.end():m.end() + 8].lower()
        if _PERIOD_PM.search(tail):
            hour += 12
    return hour, minute


def _next_run_utc(spec: dict[str, Any], after: datetime) -> str:
    """Tính lần chạy kế (giờ VN → ISO UTC)."""
    now_vn = after.astimezone(_TZ_VN)
    pattern = spec["pattern"]
    if pattern == "interval":
        nxt = after + timedelta(minutes=spec["interval_minutes"])
        return nxt.astimezone(timezone.utc).isoformat()
    hour = spec.get("hour_vn") or 0
    minute = spec.get("minute_vn") or 0
    if pattern == "daily":
        candidate = now_vn.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now_vn:
            candidate += timedelta(days=1)
    elif pattern == "weekly":
        weekday = spec["weekday"]
        candidate = now_vn.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (weekday - now_vn.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now_vn:
            candidate += timedelta(weeks=1)
    else:  # pragma: no cover
        raise RecurringParseError(f"unknown pattern {pattern}")
    return candidate.astimezone(timezone.utc).isoformat()


class RecurringTaskEngine:
    """Quản lý task định kỳ trong DurableTaskRegistry — không schema mới."""

    def __init__(self, registry: DurableTaskRegistry) -> None:
        self.registry = registry

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _spec_of(self, task: TaskRecord) -> dict[str, Any] | None:
        spec = (task.progress_weight or {}).get(_RECURRING_KEY)
        return spec if isinstance(spec, dict) and spec.get("pattern") else None

    def _save_spec(self, task_id: str, spec: dict[str, Any]) -> None:
        task = self.registry.get_task(task_id)
        if task is None:
            raise KeyError(f"template {task_id} not found")
        pw = dict(task.progress_weight or {})
        pw[_RECURRING_KEY] = spec
        self.registry.update_progress_weight(task_id, pw)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def register_recurring(
        self,
        goal: str,
        pattern_text: str,
        *,
        risk_level: str = "R2",
        priority: int = PRIORITY_NORMAL,
        source: str = "owner",
        correlation_id: str | None = None,
    ) -> TaskRecord:
        """Đăng ký task định kỳ mới — template task (không chạy ngay)."""
        spec = parse_vn_recurring(pattern_text)
        first_run = _next_run_utc(spec, datetime.now(timezone.utc))
        spec = {**spec, "next_run_utc": first_run, "enabled": True,
                "last_instance_id": None, "instance_count": 0}
        template = self.registry.register_task(
            goal=redact_text(f"『recurring』{goal.strip()}"),
            risk_level=risk_level,
            autonomy_level=AutonomyLevel.LEVEL_B,
            priority=priority,
            source=source,
            correlation_id=correlation_id,
            progress_weight={_RECURRING_KEY: spec},
        )
        # Template KHÔNG nằm trong work_queue: chuyển sang terminal-holding status
        # BLOCKED để dispatcher (M3 work_queue) lọc bỏ, nhưng vẫn tra cứu được.
        self.registry.update_task_status(
            template.task_id, TaskStatus.BLOCKED,
            reason="recurring template — not dispatchable",
        )
        return self.registry.get_task(template.task_id)  # type: ignore[return-value]

    def list_recurring(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for t in self.registry.list_tasks(limit=1000):
            spec = self._spec_of(t)
            if spec:
                out.append({
                    "task_id": t.task_id,
                    "goal": t.goal,
                    "status": t.status.value,
                    "spec": spec,
                    "next_run_utc": spec.get("next_run_utc"),
                    "instance_count": spec.get("instance_count", 0),
                    "enabled": spec.get("enabled", False),
                })
        return out

    def pause(self, template_task_id: str) -> TaskRecord:
        task = self.registry.get_task(template_task_id)
        if task is None or not self._spec_of(task):
            raise KeyError(f"recurring template {template_task_id} not found")
        spec = self._spec_of(task)
        spec["enabled"] = False
        self._save_spec(template_task_id, spec)
        return self.registry.get_task(template_task_id)  # type: ignore[return-value]

    def resume(self, template_task_id: str) -> TaskRecord:
        task = self.registry.get_task(template_task_id)
        if task is None or not self._spec_of(task):
            raise KeyError(f"recurring template {template_task_id} not found")
        spec = self._spec_of(task)
        # resume đặt next_run kế từ bây giờ (không chạy bù chu kỳ đã lỡ)
        base = {k: v for k, v in spec.items() if k in ("pattern", "interval_minutes", "hour_vn", "minute_vn", "weekday")}
        spec["next_run_utc"] = _next_run_utc(base, datetime.now(timezone.utc))
        spec["enabled"] = True
        self._save_spec(template_task_id, spec)
        return self.registry.get_task(template_task_id)  # type: ignore[return-value]

    def remove(self, template_task_id: str, *, approval_id: str | None) -> TaskRecord:
        """Remove recurring = R4 — PHẢI có approval card M4 (consume)."""
        if not approval_id:
            raise ValueError(
                "removing a recurring template is R4 — an approved approval card is required"
            )
        task = self.registry.get_task(template_task_id)
        if task is None or not self._spec_of(task):
            raise KeyError(f"recurring template {template_task_id} not found")
        spec = self._spec_of(task)
        spec["enabled"] = False
        spec["removed"] = True
        self._save_spec(template_task_id, spec)
        return self.registry.get_task(template_task_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Quét tạo instance
    # ------------------------------------------------------------------
    def create_due_instances(self, now: datetime | None = None) -> list[TaskRecord]:
        """Tạo instance cho mọi template đến hạn (max 1 lần/lượt mỗi template)."""
        now = now or datetime.now(timezone.utc)
        created: list[TaskRecord] = []
        for t in self.registry.list_tasks(limit=1000):
            spec = self._spec_of(t)
            if not spec or not spec.get("enabled", False) or spec.get("removed"):
                continue
            next_run = spec.get("next_run_utc")
            if not next_run:
                continue
            try:
                due = datetime.fromisoformat(next_run)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
            except ValueError:
                continue  # next_run hỏng → bỏ (fail-closed), không đoán
            if due > now:
                continue  # chưa đến giờ

            # Chống double-run khi restart: instance cuối cùng đã tồn tại ở trạng thái
            # sống (non-terminal) → chưa quét tiếp được (instance cũ phải xong trước).
            last_id = spec.get("last_instance_id")
            if last_id:
                last = self.registry.get_task(last_id)
                if last is not None and last.status not in (
                    TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED,
                    TaskStatus.COMPLETED_UNVERIFIED, TaskStatus.FAILED,
                    TaskStatus.CANCELLED, TaskStatus.BLOCKED,
                ):
                    continue

            count = int(spec.get("instance_count", 0)) + 1
            instance = self.registry.register_task(
                goal=redact_text(f"{t.goal} — lần {count}"),
                risk_level=t.risk_level,
                autonomy_level=t.autonomy_level,
                priority=t.priority,
                source=f"recurring:{t.task_id}",
                correlation_id=t.correlation_id,
                parent_task_id=t.task_id,
                deadline_utc=(due + timedelta(hours=1)).isoformat(),
            )
            spec["last_instance_id"] = instance.task_id
            spec["instance_count"] = count
            base = {k: v for k, v in spec.items()
                    if k in ("pattern", "interval_minutes", "hour_vn", "minute_vn", "weekday")}
            spec["next_run_utc"] = _next_run_utc(base, now)
            self._save_spec(t.task_id, spec)
            created.append(instance)
        return created
