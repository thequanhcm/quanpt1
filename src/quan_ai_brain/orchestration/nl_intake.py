"""DEOM M2 — Natural Language Task Intake (DEOM GAP #2).

Chuyển câu giao việc tự nhiên của owner ("em theo dõi việc này đến khi hoàn thành",
"gấp: kiểm tra hộ anh X trước 5 chiều") thành task có cấu trúc trong DurableTaskRegistry.

Nguyên tắc:
- KHÔNG dùng LLM để parse (deterministic, kiểm thử được) — regex + từ điển tiếng Việt.
- Fail-honest: không đoán mạo thời hạn; nếu không rút ra được deadline → None.
- Deadline hiểu theo GIỜ VIỆT NAM (+07:00) vì owner ở VN — lưu ISO UTC.
- Mọi task intake vào ở status RECEIVED (không tự chạy) — quyền thực thi theo policy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

_TZ_VN = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh — không phụ thuộc máy

# ---------------------------------------------------------------- từ điển VN

_PRIORITY_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    # 1=Critical: khẩn, gấp nhất, ngay lập tức, cháy
    (1, re.compile(r"\b(khẩn|khẩn cấp|gấp nhất|cháy|ngay lập tức|cực gấp)\b", re.I)),
    # 2=High: gấp, nhanh, hôm nay, trước (giờ) chiều
    (2, re.compile(r"\b(gấp|nhanh|hôm nay|trong ngày| ASAP)\b", re.I)),
    # 5=Background: khi rảnh, không gấp, từ từ
    (5, re.compile(r"\b(khi rảnh|không gấp|từ từ|lâu dài|background)\b", re.I)),
    # 4=Low: rỗi việc thì làm, nếu tiện
    (4, re.compile(r"\b(nếu tiện|rỗi|thong thả)\b", re.I)),
]
_PRIORITY_DEFAULT = 3  # Normal

_DEADLINE_RULES: list[tuple[re.Pattern[str], str]] = [
    # "trước 5 chiều" / "trước 17h" / "trước 9h sáng"
    (re.compile(r"trước\s+(\d{1,2})\s*(giờ|h|hề|chiều|sáng|tối)", re.I), "hour"),
    # "trước mai" / "trước ngày mai" → 09:00 mai
    (re.compile(r"trước\s+(ngày\s+)?mai", re.I), "tomorrow_9"),
    # "trước chủ nhật|thứ 2..8" (tuần này) — map thứ → ngày gần nhất
    (re.compile(r"trước\s+(chủ nhật|thứ\s*[2-8]|cn)", re.I), "weekday"),
    # "trước cuối tuần" → thứ 7 12:00
    (re.compile(r"trước\s+cuối tuần", re.I), "saturday_noon"),
    # "trong N ngày|giờ|phút tới"
    (re.compile(r"trong\s+(\d+)\s*(phút|giờ|ngày)", re.I), "relative"),
    # "đến khi hoàn thành" → không deadline (theo dõi đến xong)
    (re.compile(r"đến khi|cho đến khi|theo dõi.*đến khi", re.I), "none"),
]

_WEEKDAY_MAP = {
    "thứ 2": 0, "thứ hai": 0, "thứ 3": 1, "thứ ba": 1, "thứ 4": 2, "thứ tư": 2,
    "thứ 5": 3, "thứ năm": 3, "thứ 6": 4, "thứ sáu": 4, "thứ 7": 5, "thứ bảy": 5,
    "chủ nhật": 6, "cn": 6,
}

# Công việc cần theo dõi dài hạn → BACKGROUND mặc định nếu không nói gấp
_LONG_RUNNING = re.compile(r"theo dõi|theo sát|giám sát|nhắc.*(hàng ngày|hàng tuần|định kỳ)", re.I)


@dataclass
class IntakeResult:
    """Kết quả parse 1 câu giao việc."""
    goal: str
    priority: int
    deadline_utc: str | None
    source: str = "owner"
    initial_status: TaskStatus = TaskStatus.RECEIVED
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "priority": self.priority,
            "deadline_utc": self.deadline_utc,
            "source": self.source,
            "initial_status": self.initial_status.value,
            "meta": self.meta,
        }


def parse_vn_deadline(text: str, now: datetime | None = None) -> str | None:
    """Rút deadline ISO-UTC từ câu tiếng Việt (giờ VN +07). Không khớp → None (không đoán)."""
    now = now or datetime.now(timezone.utc)
    now_vn = now.astimezone(_TZ_VN)
    for pattern, kind in _DEADLINE_RULES:
        m = pattern.search(text)
        if not m:
            continue
        try:
            if kind == "hour":
                h = int(m.group(1))
                if not 0 <= h <= 23:
                    continue
                # "5 chiều" = 17:00; "9 sáng" = 09:00; "8 tối" = 20:00.
                # 'chiều/sáng/tối' có thể nằm TRONG match (trước 5 chiều) hoặc sau số giờ (9h tối)
                after = text[m.end():m.end() + 6].lower()
                before = m.group(0).lower()
                if h <= 11 and ("chiều" in after or "tối" in after or "chiều" in before or "tối" in before):
                    h += 12
                target_vn = now_vn.replace(hour=h, minute=0, second=0, microsecond=0)
                if target_vn <= now_vn:
                    target_vn += timedelta(days=1)  # giờ đã qua → hiểu là mai
                return target_vn.astimezone(timezone.utc).isoformat()
            if kind == "tomorrow_9":
                target_vn = (now_vn + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                return target_vn.astimezone(timezone.utc).isoformat()
            if kind == "saturday_noon":
                days_ahead = (5 - now_vn.weekday()) % 7 or 7
                target_vn = (now_vn + timedelta(days=days_ahead)).replace(hour=12, minute=0, second=0, microsecond=0)
                return target_vn.astimezone(timezone.utc).isoformat()
            if kind == "weekday":
                wd_raw = m.group(1).lower()
                target_wd = _WEEKDAY_MAP.get(wd_raw)
                if target_wd is None:
                    continue
                days_ahead = (target_wd - now_vn.weekday()) % 7 or 7
                target_vn = (now_vn + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
                return target_vn.astimezone(timezone.utc).isoformat()
            if kind == "relative":
                n = int(m.group(1))
                unit = m.group(2).lower()
                delta = {"phút": timedelta(minutes=n), "giờ": timedelta(hours=n), "ngày": timedelta(days=n)}[unit]
                return (now + delta).isoformat()
            if kind == "none":
                return None
        except (ValueError, OverflowError):
            continue
    return None


def detect_priority(text: str) -> int:
    for prio, pattern in _PRIORITY_PATTERNS:
        if pattern.search(text):
            return prio
    if _LONG_RUNNING.search(text):
        return 4  # việc theo dõi dài hạn mặc định Low
    return _PRIORITY_DEFAULT


def intake_task(
    registry: DurableTaskRegistry,
    text: str,
    *,
    source: str = "owner",
    risk_level: str = "R1",
    acceptance_criteria: list[str] | None = None,
) -> IntakeResult:
    """Parse câu giao việc tiếng Việt → tạo task RECEIVED trong registry.

    Trả về IntakeResult (goal đã redact qua registry). Không bao giờ tự chuyển
    task sang trạng thái chạy — quyền thực thi nằm ở Supervisor + policy.
    """
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        raise ValueError("Câu giao việc trống")
    priority = detect_priority(clean)
    deadline = parse_vn_deadline(clean)
    record = registry.register_task(
        clean,
        risk_level=risk_level,
        priority=priority,
        deadline_utc=deadline,
        source=source,
        initial_status=TaskStatus.RECEIVED,
        acceptance_criteria=acceptance_criteria or [],
    )
    return IntakeResult(
        goal=record.goal,
        priority=priority,
        deadline_utc=deadline,
        source=source,
        initial_status=TaskStatus.RECEIVED,
        meta={"task_id": record.task_id},
    )
