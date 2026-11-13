"""Trifecta Guard — TASK-AGENTIC-SEC-1 Slice (c).

Áp dụng khung ATTT Agentic AI (MIT + Viettel Cyber Security 261113_VTNET_ATTT_Agentic_AI_v4):
- Slide 13 "Lethal Trifecta" (Simon Willison): Agent hội đủ CẢ BA năng lực
  (dữ liệu riêng tư + nội dung không tin cậy + giao tiếp ra ngoài) → nội dung độc
  hại có thể khiến Agent lấy dữ liệu và gửi ra ngoài (EchoLeak).
- → Thiết kế: tách ít nhất một năng lực, hoặc BẮT PHÊ DUYỆT khi hội đủ.

Quy tắc: task/tool-call hội đủ cả 3 cờ → FORCE PROPOSE (LỚP 2), kể cả khi đang
nằm trong LỚP 1 AUTO (self-heal). Giữ nguyên mọi hành vi AUTO/PROPOSE/NEVER hiện có —
chỉ THÊM điều kiện nâng cấp (ngoại phạm vi card §3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrifectaFlags:
    """3 năng lực nguy hiểm trên cùng 1 task/tool-call."""
    private_data: bool = False        # chạm dữ liệu riêng tư (brain.db, knowledge, DM riêng tư)
    untrusted_content: bool = False   # xử lý nội dung ngoài (web, log, tin nhắn, tài liệu ngoài)
    external_egress: bool = False     # gửi/đẩy dữ liệu ra ngoài hệ thống (DM, email, API ngoài)

    @property
    def count(self) -> int:
        return sum((self.private_data, self.untrusted_content, self.external_egress))

    @property
    def lethal(self) -> bool:
        return self.count == 3


@dataclass
class TrifectaDecision:
    """Kết quả đánh giá trifecta cho 1 task."""
    flags: TrifectaFlags
    required_approval: bool          # True → bắt buộc đi PROPOSE (LỚP 2)
    reason: str = ""
    force_upgraded: bool = False     # True nếu đã nâng từ AUTO lên PROPOSE

    @property
    def lethal(self) -> bool:
        return self.flags.lethal


# Từ khóa nhận diện từng cờ (deterministic, không LLM-judge)
_PRIVATE_KEYWORDS = (
    "brain.db", "knowledge", "memory", "hồ sơ", "dữ liệu riêng", "danh sách khách hàng",
    "sdt", "số điện thoại", "email cá nhân", "chat", "tin nhắn riêng", "hồ sơ nhân sự",
)
_UNTRUSTED_KEYWORDS = (
    "web", "email", "tin nhắn", "tài liệu", "log", "message", "internet",
    "document", "báo cáo ngoài", "liên bang", "attachment", "file tải về",
)
_EGRESS_KEYWORDS = (
    "gửi", "send", "gửi đi", "đăng", "post", "upload", "email", "dm", "forward",
    "chuyển tiếp", "gửi ra ngoài", "webhook", "api ngoài",
)


def evaluate_task(description: str, *, task_class: str = "AUTO") -> TrifectaDecision:
    """Đánh giá 1 task/tool-call dựa trên mô tả (deterministic).

    Args:
        description: mô tả task/hành định/argument của tool-call.
        task_class: lớp tự chủ hiện tại ("AUTO" / "PROPOSE" / "NEVER").

    Returns:
        TrifectaDecision: lethal → required_approval=True (FORCE PROPOSE nếu
        task_class="AUTO"); NEVER giữ nguyên (đã cứng); PROPOSE giữ nguyên.
    """
    desc_low = (description or "").lower()
    flags = TrifectaFlags(
        private_data=any(k in desc_low for k in _PRIVATE_KEYWORDS),
        untrusted_content=any(k in desc_low for k in _UNTRUSTED_KEYWORDS),
        external_egress=any(k in desc_low for k in _EGRESS_KEYWORDS),
    )

    if task_class == "NEVER":
        # LỚP 3 — hard block rồi, không cần trifecta
        return TrifectaDecision(flags, required_approval=False,
                                reason="NEVER: đã hard-block, trifecta không đổi hành vi")

    if flags.lethal:
        if task_class == "AUTO":
            # Force nâng lên PROPOSE — deadly combo không được tự động chạy
            return TrifectaDecision(
                flags, required_approval=True, force_upgraded=True,
                reason="LETHAL TRIFECTA: AUTO → PROPOSE (bộ ba nguy hiểm, slide 13)",
            )
        return TrifectaDecision(flags, required_approval=True,
                                reason="LETHAL TRIFECTA: đã ở PROPOSE, giữ phê duyệt")

    return TrifectaDecision(
        flags, required_approval=(task_class == "PROPOSE"),
        reason=f"flags={flags.count}/3 — không hội đủ bộ ba",
    )


def check_and_upgrade(action_class: str, description: str) -> tuple[str, TrifectaDecision]:
    """Hàm tiện cho cherry_autonomous: trả về lớp hiệu dụng sau trifecta.

    >>> check_and_upgrade("AUTO", "đọc web + gửi DM dữ liệu knowledge")
    ('PROPOSE', ...)
    """
    d = evaluate_task(description, task_class=action_class)
    effective = "PROPOSE" if (action_class == "AUTO" and d.force_upgraded) else action_class
    return effective, d
