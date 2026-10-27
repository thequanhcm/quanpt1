"""Sprint 9 (C): Email Intake Adapter — interface + connector dễ thay thế.

Trạng thái THẬT của hệ thống email:
- Vmail/Outlook: BLOCKED — mật khẩu SSO đã lộ trong chat (27/10), chờ owner đổi
  mật khẩu và đăng nhập lại. KHÔNG đọc hộp thư thật trong sprint này (§IX master prompt).
- Do đó connector duy nhất hiện có là MockEmailConnector: dữ liệu giả lập CÓ GHI RÕ
  nguồn="mock", không bao giờ tự nhận là mail thật.

Thiết kế theo master prompt §IV.2:
- read-only: không đánh dấu đã đọc, không xóa, không gửi.
- dedupe theo message_id: cùng email không xử lý 2 lần (sync state lưu cursor).
- lỗi connector → trả ConnectorStatus trung thực, không giả vờ đã đọc.
- không log nội dung nhạy cảm; không tự mở attachment.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class ConnectorStatus(str, Enum):
    """Trạng thái connector — chỉ dùng giá trị đã kiểm chứng (§V.3)."""

    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    DEGRADED = "DEGRADED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"  # bị chặn bởi chính sách/bảo mật (Vmail hiện tại)


class EmailCategory(str, Enum):
    """Phân loại §IV.1 — không phải mọi email đều tạo nhiệm vụ."""

    ACTION_REQUIRED = "ACTION_REQUIRED"      # có yêu cầu cần xử lý
    FYI = "FYI"                              # thông báo, đọc là đủ
    NEWSLETTER = "NEWSLETTER"                # quảng cáo / bản tin
    DUPLICATE = "DUPLICATE"                  # trùng email đã xử lý
    UNCLEAR = "UNCLEAR"                      # không phân loại được → hỏi owner nếu cần


@dataclass
class EmailMessage:
    """Email tiếp nhận — metadata tối thiểu, không giữ nội dung nhạy cảm thừa."""

    message_id: str
    sender: str
    subject: str
    body_preview: str          # tối đa ~500 ký tự đầu, chỉ để phân loại
    received_at_utc: str
    source: str                # "mock" | "vmail" | ... — BẮT BUỘC ghi nguồn
    category: EmailCategory = EmailCategory.UNCLEAR
    related_task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "subject": self.subject,
            "body_preview": self.body_preview[:500],
            "received_at_utc": self.received_at_utc,
            "source": self.source,
            "category": self.category.value,
            "related_task_id": self.related_task_id,
        }


@dataclass
class IntakeResult:
    """Kết quả 1 lần sync — trung thực về nguồn và số lượng."""

    connector_status: ConnectorStatus
    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_status": self.connector_status.value,
            "fetched": self.fetched,
            "new": self.new,
            "duplicates": self.duplicates,
            "by_category": self.by_category,
            "error": self.error,
        }


class EmailConnector(Protocol):
    """Interface connector — thay thế được (Vmail sau này chỉ cần hiện thực class này)."""

    def status(self) -> ConnectorStatus: ...
    def fetch_recent(self, limit: int = 20) -> list[EmailMessage]: ...


class MockEmailConnector:
    """Connector giả lập — DỮ LIỆU GẢN, nguồn="mock" ghi trên từng message.

    Mục đích: chạy được luồng intake → phân loại → dedupe → gắn nhiệm vụ mà KHÔNG
    chạm hộp thư thật. Test dùng connector này; Vmail thật vẫn BLOCKED.
    """

    def __init__(self, seed_messages: list[dict[str, Any]] | None = None) -> None:
        self._seed = seed_messages or _DEFAULT_MOCK_MESSAGES
        self._status = ConnectorStatus.CONNECTED

    def status(self) -> ConnectorStatus:
        return self._status

    def set_status(self, status: ConnectorStatus) -> None:
        self._status = status

    def fetch_recent(self, limit: int = 20) -> list[EmailMessage]:
        if self._status != ConnectorStatus.CONNECTED:
            return []
        out: list[EmailMessage] = []
        for raw in self._seed[:limit]:
            out.append(
                EmailMessage(
                    message_id=str(raw.get("message_id", "")),
                    sender=str(raw.get("sender", "")),
                    subject=str(raw.get("subject", "")),
                    body_preview=str(raw.get("body", ""))[:500],
                    received_at_utc=str(
                        raw.get("received_at_utc")
                        or datetime.now(timezone.utc).isoformat()
                    ),
                    source="mock",
                )
            )
        return out


class VmailConnector:
    """Vmail thật — hiện BLOCKED (mật khẩu SSO đã lộ, chờ owner đổi).

    Không đăng nhập, không đọc. Chỉ báo cáo trạng thái trung thực. Sau này khi
    owner đổi mật khẩu + có cấu hình an toàn + phê duyệt riêng, hiện thực
    fetch_recent() bằng IMAP/OWA theo quyền được cấp — KHÔNG trong Sprint 9.
    """

    def status(self) -> ConnectorStatus:
        return ConnectorStatus.BLOCKED

    def fetch_recent(self, limit: int = 20) -> list[EmailMessage]:
        return []  # BLOCKED — không đọc gì cả, trung thực tuyệt đối


# ---------------------------------------------------------------------------
# Intake pipeline: sync → dedupe → phân loại → lưu (data/email_intake.db)
# ---------------------------------------------------------------------------

class EmailIntakeStore:
    """Lưu email đã tiếp nhận + dedupe state. SQLite data/email_intake.db."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)  # Sprint 9: data/ có thể chưa tồn tại
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS intake_emails (
                    message_id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body_preview TEXT NOT NULL,
                    received_at_utc TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    related_task_id TEXT DEFAULT '',
                    synced_at_utc TEXT NOT NULL
                )
                """
            )

    def already_seen(self, message_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM intake_emails WHERE message_id = ?", (message_id,)
        ).fetchone()
        return row is not None

    def save(self, msg: EmailMessage, category: EmailCategory) -> bool:
        """Lưu 1 email. Trả False nếu trùng (đã có) — KHÔNG ghi đè."""
        if self.already_seen(msg.message_id):
            return False
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO intake_emails
                    (message_id, sender, subject, body_preview, received_at_utc,
                     source, category, related_task_id, synced_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg.message_id,
                    msg.sender,
                    msg.subject,
                    msg.body_preview[:500],
                    msg.received_at_utc,
                    msg.source,
                    category.value,
                    msg.related_task_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return True

    def list_emails(self, limit: int = 50, category: str | None = None) -> list[dict[str, Any]]:
        if category:
            cur = self._conn.execute(
                "SELECT * FROM intake_emails WHERE category = ? ORDER BY received_at_utc DESC LIMIT ?",
                (category, limit),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM intake_emails ORDER BY received_at_utc DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM intake_emails").fetchone()[0]


# ---------------------------------------------------------------------------
# Phân loại — luật đơn giản, rõ ràng, có thể kiểm tra (không LLM trong sprint này)
# ---------------------------------------------------------------------------

_ACTION_HINTS = ("yêu cầu", "đề nghị", "gấp", "deadline", "hạn", "cần anh/chị", "vui lòng xử lý")
_NEWSLETTER_HINTS = ("unsubscribe", "hủy đăng ký", "khuyến mãi", "sale", "newsletter", "% giảm")


def classify_email(msg: EmailMessage) -> EmailCategory:
    """Phân loại bằng luật từ khóa (mock/pipeline sprint 9). LLM phân loại sâu hơn để sau."""
    text = f"{msg.subject}\n{msg.body_preview}".lower()
    if any(k in text for k in _NEWSLETTER_HINTS):
        return EmailCategory.NEWSLETTER
    if any(k in text for k in _ACTION_HINTS):
        return EmailCategory.ACTION_REQUIRED
    if msg.subject.strip():
        return EmailCategory.FYI
    return EmailCategory.UNCLEAR


def sync_intake(
    connector: EmailConnector,
    store: EmailIntakeStore,
    *,
    limit: int = 20,
) -> IntakeResult:
    """1 chu kỳ tiếp nhận: fetch → dedupe → classify → save. Fail-honest."""
    try:
        st = connector.status()
        if st != ConnectorStatus.CONNECTED:
            return IntakeResult(connector_status=st, error="connector không ở trạng thái CONNECTED — không đọc gì")
        messages = connector.fetch_recent(limit=limit)
    except Exception as exc:
        return IntakeResult(
            connector_status=ConnectorStatus.UNKNOWN,
            error=f"{type(exc).__name__}: {exc}",
        )

    result = IntakeResult(connector_status=ConnectorStatus.CONNECTED, fetched=len(messages))
    for msg in messages:
        if store.already_seen(msg.message_id):
            result.duplicates += 1
            continue
        category = classify_email(msg)
        if store.save(msg, category):
            result.new += 1
            result.by_category[category.value] = result.by_category.get(category.value, 0) + 1
    return result


_DEFAULT_MOCK_MESSAGES: list[dict[str, Any]] = [
    {
        "message_id": "mock-001",
        "sender": "trinhvien@viettel.com.vn",
        "subject": "Yêu cầu báo cáo tuần nhóm AI",
        "body": "Chào Quân, vui lòng xử lý và gửi báo cáo tuần trước 17h thứ Sáu. Cảm ơn.",
    },
    {
        "message_id": "mock-002",
        "sender": "no-reply@viettel.com.vn",
        "subject": "Khuyến mãi nội bộ tháng 11",
        "body": "Giảm 20% cho nhân viên. Unsubscribe: bấm vào đây để hủy đăng ký.",
    },
    {
        "message_id": "mock-003",
        "sender": "hoidap@viettel.com.vn",
        "subject": "Thông báo bảo trì hệ thống M-Suite",
        "body": "Hệ thống sẽ bảo trì 22:00-23:00 ngày 28/10. Đây là thông báo FYI.",
    },
]
