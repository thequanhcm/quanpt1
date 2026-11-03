"""Conversation State Manager — M5 (Human-like Conversation, phần 1).

Đóng gap G-22 (Dialogue State Manager) cho kênh THOẠI Pi5: voice hiện
stateless — mỗi câu được STT → intent/GLM → trả lời riêng lẻ, nên đại từ
("nó", "vậy", "anh ấy") bị mất ngữ cảnh lượt trước.

Thiết kế (nhỏ, tái sử dụng, không tạo DB mới):
- Lưu JSON file data/conversation_state.json (convention giống skill_registry.json).
- Mỗi kênh 1 state riêng: voice / web / dm.
- TTL mặc định 10 phút — hết hạn → coi như không có ngữ cảnh.
- Fail-honest: file hỏng → bắt đầu lại, không crash server.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

DEFAULT_TTL_SEC = 600.0
DEFAULT_MAX_CHARS = 4000

# Đại từ / cụm chỉ-đại-từ tiếng Việt thường gặp trong câu hỏi nối lượt.
# Chỉ dùng để QUYẾT ĐỊNH có bọc ngữ cảnh hay không — không dùng để trả lời.
_ANAPHORA_PATTERN = re.compile(
    r"\b(nó|nós|anh ấy|cô ấy|ông ấy|bà ấy|hắn|thằng đó|thằng ấy|con đó|con ấy|"
    r"đó|ấy|vậy|thế|như thế nào|cái đó|cái ấy|việc đó|vấn đề đó|"
    r"cũng|lại|tiếp|thêm|kia|nãy|vừa rồi|lúc nãy)\b",
    re.IGNORECASE,
)


class ConversationStateManager:
    """Lưu trữ + phân tích ngữ cảnh hội thoại ngắn hạn per-channel (JSON)."""

    def __init__(self, workspace: str | Path = ".",
                 ttl_sec: float = DEFAULT_TTL_SEC,
                 max_chars: int = DEFAULT_MAX_CHARS) -> None:
        self.workspace = Path(workspace)
        self.ttl_sec = float(ttl_sec)
        self.max_chars = int(max_chars)
        self._lock = threading.Lock()
        self._path = self.workspace / "data" / "conversation_state.json"

    # ---------- persistence ----------
    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(self._path)

    # ---------- API chính ----------
    def get(self, channel: str) -> dict[str, Any] | None:
        """Trả state còn hạn của kênh; None nếu chưa có hoặc hết TTL."""
        with self._lock:
            data = self._load()
            entry = data.get(channel)
            if not entry:
                return None
            age = time.time() - float(entry.get("updated_ts", 0))
            if age > self.ttl_sec:
                return None
            return entry

    def update(self, channel: str, user_text: str, assistant_reply: str,
               intent: Any = None) -> None:
        """Ghi state sau 1 lượt hội thoại (an toàn gọi fire-and-forget)."""
        with self._lock:
            data = self._load()
            data[channel] = {
                "last_user_text": str(user_text or "")[: self.max_chars],
                "last_reply": str(assistant_reply or "")[: self.max_chars],
                "last_intent": (str(intent) if intent else None),
                "updated_ts": time.time(),
                "updated_at_utc": datetime_now_utc(),
            }
            # Giữ tối đa 3 kênh gần nhất — chống phình file.
            if len(data) > 3:
                for ch in sorted(data, key=lambda k: data[k].get("updated_ts", 0))[:-3]:
                    data.pop(ch, None)
            try:
                self._save(data)
            except OSError:
                pass  # fail-honest: mất state không được giết luồng hội thoại

    def has_anaphora(self, text: str) -> bool:
        """Câu hỏi có đại từ/đại từ chỉ-vật cần ngữ cảnh lượt trước không."""
        return bool(_ANAPHORA_PATTERN.search(str(text or "")))

    def build_contextualized_query(self, channel: str, query: str) -> str:
        """Trả query bọc ngữ cảnh nếu cần; query gốc nếu không có đại từ
        hoặc state hết hạn. Không bao giờ tự bịa nội dung."""
        entry = self.get(channel)
        if entry is None:
            return query
        if not self.has_anaphora(query):
            return query
        last_q = str(entry.get("last_user_text", "")).strip()
        last_a = str(entry.get("last_reply", "")).strip()
        if not last_q:
            return query
        ctx = (f"[NGỮ CẢNH lượt trước — Anh hỏi: \"{last_q[:300]}\"; "
               f"Em trả lời: \"{last_a[:300]}\"]\n"
               f"Câu hỏi hiện tại của Anh: \"{query}\"\n"
               f"Nếu đại từ trong câu hỏi hiện tại nói về đối tượng ở ngữ cảnh "
               f"trên thì hiểu theo ngữ cảnh đó; nếu không liên quan thì trả "
               f"lời bình thường.")
        return ctx


def datetime_now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
