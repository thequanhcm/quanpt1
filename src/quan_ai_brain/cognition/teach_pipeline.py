"""Teach pipeline — "anh đào tạo, chuyển giao → em thu thập và nhớ".

Khi chủ sở hữu dạy trực tiếp trong chat (dashboard hoặc kênh NetChat), tin
nhắn được nhận diện và lưu vào trí nhớ dài hạn NGAY LẬP TỨC, với:
- memory_type  = FACT (tri thức) hoặc PREFERENCE (sở thích/cách làm)
- verification = USER_PROVIDED (nguồn: chính chủ sở hữu — không cần duyệt thêm)
- source_ref   = "owner_teach:<session>:<timestamp>"

Đây KHÔNG phải đường thăng cấp tri thức tự động (L0-L3 vẫn giữ nguyên cho
knowledge ingestion): đây là kênh chủ sở hữu chuyển giao trực tiếp — chủ
sở hữu là nguồn sự thật tối cao nên tin của anh được tin ngay, và cũng chỉ
chủ sở hữu mới dạy được (kiểm tra user_id/owner flag ở caller).

Sao này dạy lặp lại → ghi bản MỚI (không ghi đè lịch sử — trí nhớ là append-only
theo thiết kế storage; consolidation là việc của Learning Daemon).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from quan_ai_brain.memory.models import MemoryType, VerificationStatus

# Chuỗi nhận biết tin dạy (bắt đầu tin hoặc sau lời dẫn).
_TEACH_PREFIXES = (
    "nhớ rằng",
    "ghi nhớ rằng",
    "nhớ giúp em:",
    "nhớ giúp anh:",
    "em cần nhớ",
    "phải nhớ",
    "đào tạo:",
    "chuyển giao:",
    "từ giờ",
    "từ nay",
)

_TEACH_PATTERN = re.compile(
    r"^\s*(?:nhớ|ghi nhớ|ghi nhận|lưu ý|cập nhật)\s+(?:rằng|giúp em|giúp anh|:)\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)

_PREFERENCE_HINTS = re.compile(
    r"(tôi thích|anh thích|em thích|ưu tiên|luôn |đừng |không được |hãy luôn|cách làm|phong cách)",
    re.IGNORECASE,
)


@dataclass
class TeachResult:
    is_teaching: bool
    content: str
    memory_type: str
    note: str


def detect_teaching(text: str) -> TeachResult:
    """Nhận biết tin dạy từ chủ sở hữu. Đơn giản, deterministic, không LLM."""
    t = (text or "").strip()
    if not t:
        return TeachResult(False, "", "FACT", "")

    lower = t.lower()
    hit_prefix = any(lower.startswith(p) for p in _TEACH_PREFIXES if p)
    m = _TEACH_PATTERN.match(t)

    if not hit_prefix and not m:
        return TeachResult(False, "", "FACT", "")

    content = m.group(1).strip() if m else t
    # bỏ lời dẫn phía trước nếu còn
    for lead in ("rằng ", "giúp em ", "giúp anh ", ": "):
        if content.lower().startswith(lead):
            content = content[len(lead):].strip()

    if not content:
        return TeachResult(False, "", "FACT", "")

    mem_type = "PREFERENCE" if _PREFERENCE_HINTS.search(content) else "FACT"
    return TeachResult(True, content, mem_type, "")


def persist_taught_memory(
    store,  # MemoryStore
    content: str,
    mem_type: str = "FACT",
    session_id: str = "owner_direct",
) -> dict:
    """Lưu tri thức anh dạy vào memories (semantic-reachable, USER_PROVIDED).

    Trả về dict{id, memory_type} hoặc raise nếu store lỗi.
    """
    v_status = (
        VerificationStatus.USER_PROVIDED
        if mem_type == "PREFERENCE"
        else VerificationStatus.USER_PROVIDED
    )
    mtype = MemoryType.PREFERENCE if mem_type == "PREFERENCE" else MemoryType.SEMANTIC
    now = datetime.now(timezone.utc).isoformat()
    rec = store.store_memory(
        content=content,
        memory_type=mtype,
        source_ref=f"owner_teach:{session_id}:{now}",
        verification_status=v_status,
        confidence_score=1.0,
        tags=["owner_teach"],
    )
    return {"id": rec.id, "memory_type": mtype.value}
