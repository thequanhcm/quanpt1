# -*- coding: utf-8 -*-
"""VmailConnector — CHERRY VMAIL INTELLIGENCE V1.0 — Sprint 1.

(23/11/2026, owner: "em cho thực hiện CHERRY VMAIL INTELLIGENCE V1.0" + duyệt card
TASK-VMAIL-S1). Lớp mỏng đóng gói tools.mail_reader (SOAP đã kiểm chứng live
23/11: 13 folder, conversation search, authToken OK) thành 1 class có interface
rõ ràng + StructuredResult + Health States — phục vụ Sprint 2 Thread Analyzer,
Sprint 3 Shared Memory, Sprint 4 Reply Draft.

TÁI SỬ DỤNG 100% mail_reader (268 dòng, đã LIVE — không viết lại I/O).
KHÔNG có cognitive core thứ 2 (đúng §2.1 master prompt): chỉ là wrapper class.
R2 bất biến: CHỈ ĐỌC — mọi op GHI trả `unsupported_by_policy`.

Connection health (master prompt §13):
- HEALTHY: token mới auth + SOAP search OK trong 25s
- DEGRADED: timeout/500 trên 1 request nhưng session còn
- UNHEALTHY: auth fail 2 lần liên tiếp
- DISCONNECTED: không thể kết nối vmail.viettel.vn (network/DNS)

Fail-honest: status="error" + operation_id + evidence — không fake số liệu.
"""
from __future__ import annotations

import datetime as _dt
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Tái sử dụng mail_reader (đã chứng minh live: GetFolder 13 folder OK, Auth OK)
WORKSPACE = Path(__file__).resolve().parents[3]  # src/quan_ai_brain/office/ → E:/BRAIN
TOOLS = WORKSPACE / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import mail_reader  # noqa: E402 — công cụ đã verified 23/11

# ---- Constants ----
HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
UNHEALTHY = "UNHEALTHY"
DISCONNECTED = "DISCONNECTED"

SOAP_URL = mail_reader.SOAP_URL
MAIL_NS = mail_reader.MAIL_NS
ACC_NS = mail_reader.ACC_NS

# Auth cache TTL (giây) — token Zimbra thường sống ~60 phút nhưng không tài liệu
# chính thức; cache 10 phút, validate lại nếu fail
_TOKEN_TTL_S = 600
_HEALTH_CACHE_TTL_S = 60  # chỉ re-probe 1 lần/phút


class VmailConnectorError(RuntimeError):
    """Lỗi runtime từ VmailConnector. Inherit để caller biết loại lỗi."""


class StructuredResult:
    """Bao bọc kết quả — không coi HTTP 200 là thành công nghiệp vụ.

    Fields:
        status: 'ok' | 'error' | 'unsupported'
        operation_id: tên operation (authenticate/list_messages/...)
        operation_index: số thứ tự trong phiên (để audit)
        evidence: dict ngữ cảnh (request/response sample, count, health)
        data: payload thật (mail list, thread, message body)
        error: thông báo lỗi (nếu có)
        timestamp: ISO-8601 lúc tạo
    """

    def __init__(
        self,
        status: str,
        operation_id: str,
        evidence: dict[str, Any] | None = None,
        data: Any = None,
        error: str | None = None,
    ) -> None:
        if status not in ("ok", "error", "unsupported"):
            raise ValueError(f"status phải là ok|error|unsupported — nhận {status!r}")
        self.status = status
        self.operation_id = operation_id
        self.operation_index = VmailConnector._operation_counter()
        self.evidence = dict(evidence or {})
        self.data = data
        self.error = error
        self.timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "operation_id": self.operation_id,
            "operation_index": self.operation_index,
            "evidence": self.evidence,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return f"StructuredResult({self.status!r}, {self.operation_id!r}, op#{self.operation_index})"


class VmailConnector:
    """CHERRY VMAIL connector — Zimbra SOAP (READONLY R2).

    Interface §4.3 master prompt:
    - authenticate(): login → token, cache TTL 10 phút
    - validate_session(token): token còn sống không
    - list_folders(): 13 folder inbox/sent/drafts/junk/...
    - list_messages(folder, limit): email trong folder
    - get_message(mid): nội dung 1 email
    - search_messages(query, limit): search theo Zimbra query
    - get_thread(conversation_id): ghép luồng theo conversation-id
    - get_connection_health(): HEALTHY|DEGRADED|UNHEALTHY|DISCONNECTED

    Operations GHI (send/mark_read/delete) trả status="unsupported" R2.
    """

    _op_counter = 0

    @classmethod
    def _operation_counter(cls) -> int:
        cls._op_counter += 1
        return cls._op_counter

    # ---- Auth state ----
    def __init__(self) -> None:
        self._token: str | None = None
        self._token_issued_at: float = 0.0
        self._auth_fails: int = 0
        self._last_health: str = DISCONNECTED
        self._last_health_check: float = 0.0

    # ---- Health (§13) ----
    def get_connection_health(self, force: bool = False) -> str:
        """Trả 1 trong HEALTHY|DEGRADED|UNHEALTHY|DISCONNECTED.

        Cache 60s. 'force=True' bỏ qua cache (dùng khi vừa fail)."""
        now = time.time()
        if not force and now - self._last_health_check < _HEALTH_CACHE_TTL_S:
            return self._last_health
        try:
            # Probe: DNS + TCP tới SOAP endpoint (không tốn 1 auth)
            import socket
            from urllib.parse import urlparse
            u = urlparse(SOAP_URL)
            socket.create_connection((u.hostname, u.port or 443), timeout=5).close()
        except Exception:
            self._last_health = DISCONNECTED
            self._last_health_check = now
            return self._last_health
        if self._auth_fails >= 2:
            self._last_health = UNHEALTHY
        elif self._token and (now - self._token_issued_at) > _TOKEN_TTL_S:
            # Token quá hạn cache → DEGRADED (chưa xác nhận chết)
            self._last_health = DEGRADED
        elif self._token:
            self._last_health = HEALTHY
        else:
            self._last_health = DEGRADED
        self._last_health_check = now
        return self._last_health

    # ---- Auth (§4.3) ----
    def authenticate(self) -> StructuredResult:
        """Đăng nhập SOAP → token. Cache 10 phút."""
        try:
            token = mail_reader._auth()
            self._token = token
            self._token_issued_at = time.time()
            self._auth_fails = 0
            self.get_connection_health(force=True)
            return StructuredResult(
                "ok",
                "authenticate",
                evidence={
                    "host": SOAP_URL,
                    "token_age_s": 0,
                    "health": self._last_health,
                },
            )
        except mail_reader._MailError as e:
            self._auth_fails += 1
            self.get_connection_health(force=True)
            return StructuredResult(
                "error",
                "authenticate",
                evidence={"host": SOAP_URL, "auth_fails": self._auth_fails, "health": self._last_health},
                error=str(e),
            )
        except Exception as e:
            self._auth_fails += 1
            return StructuredResult(
                "error",
                "authenticate",
                evidence={"host": SOAP_URL},
                error=f"{type(e).__name__}: {e}",
            )

    def validate_session(self, token: str | None = None) -> StructuredResult:
        """Probe session bằng SearchRequest nhẹ (in:inbox limit=1).
        Nếu thành công → ok; nếu auth lỗi → error.
        """
        tk = token if token is not None else self._token
        if not tk:
            return StructuredResult(
                "error", "validate_session", error="Chưa có token — gọi authenticate() trước."
            )
        try:
            mail_reader._search(tk, "in:inbox", 1)
            return StructuredResult(
                "ok", "validate_session", evidence={"token_age_s": int(time.time() - self._token_issued_at)}
            )
        except mail_reader._MailError as e:
            # Token hết hạn → xóa cache để re-auth lần tới
            self._token = None
            self._token_issued_at = 0.0
            self._auth_fails += 1
            return StructuredResult("error", "validate_session", error=str(e))
        except Exception as e:
            return StructuredResult("error", "validate_session", error=f"{type(e).__name__}: {e}")

    def _ensure_token(self) -> tuple[str | None, StructuredResult | None]:
        """Đảm bảo token còn hiệu lực. Trả (token, None) nếu ok, (None, error_result) nếu lỗi."""
        if self._token and (time.time() - self._token_issued_at) < _TOKEN_TTL_S:
            # Probe nhẹ 1 lần trước khi dùng
            v = self.validate_session()
            if v.status == "ok":
                return self._token, None
            # Token chết — thử re-auth 1 lần
        res = self.authenticate()
        if res.status != "ok":
            return None, res
        return self._token, None

    # ---- Folders (§4.3) ----
    def list_folders(self) -> StructuredResult:
        """13 folder đã probe OK 23/11 (Inbox, Sent, Drafts, Junk, Archive, Calendar, Tasks...)."""
        token, err = self._ensure_token()
        if err:
            return err
        try:
            out = mail_reader._soap(
                f'<GetFolderRequest xmlns="{MAIL_NS}"/>', token
            )
            root = ET.fromstring(out)
            folders = []
            for f in root.iter(f"{{{MAIL_NS}}}folder"):
                folders.append({
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "view": f.get("view"),  # "message" | "appointment" | "task" | "wiki" | "document"
                    "unread_count": f.get("u"),  # số chưa đọc (nếu có)
                    "total_count": f.get("n"),
                })
            return StructuredResult(
                "ok", "list_folders", evidence={"host": SOAP_URL}, data={"count": len(folders), "folders": folders}
            )
        except mail_reader._MailError as e:
            return StructuredResult("error", "list_folders", error=str(e))
        except Exception as e:
            return StructuredResult("error", "list_folders", error=f"{type(e).__name__}: {e}")

    # ---- Messages (§4.3) ----
    def list_messages(self, folder: str = "inbox", limit: int = 10) -> StructuredResult:
        """Danh sách email trong folder (in:inbox, in:sent, in:drafts, in:junk...)."""
        token, err = self._ensure_token()
        if err:
            return err
        # Map alias thân thiện → query
        q_map = {
            "inbox": "in:inbox",
            "sent": "in:sent",
            "drafts": "in:drafts",
            "junk": "in:junk",
            "archive": "in:archive",
        }
        query = q_map.get(folder.lower(), folder)
        try:
            items = mail_reader._search(token, query, max(1, min(limit, 20)))
            return StructuredResult(
                "ok",
                "list_messages",
                evidence={"folder": folder, "query": query, "host": SOAP_URL},
                data={"count": len(items), "messages": items},
            )
        except mail_reader._MailError as e:
            return StructuredResult("error", "list_messages", error=str(e))
        except Exception as e:
            return StructuredResult("error", "list_messages", error=f"{type(e).__name__}: {e}")

    def get_message(self, mid: str) -> StructuredResult:
        """Nội dung 1 email theo id (cắt body 2000 ký tự)."""
        token, err = self._ensure_token()
        if err:
            return err
        if not mid or not mid.isdigit():
            return StructuredResult("error", "get_message", error=f"mid không hợp lệ: {mid!r}")
        try:
            body = mail_reader._get_body(token, mid)
            return StructuredResult(
                "ok",
                "get_message",
                evidence={"mid": mid, "host": SOAP_URL, "body_len": len(body)},
                data={"id": mid, "body_preview": body},
            )
        except mail_reader._MailError as e:
            return StructuredResult("error", "get_message", error=str(e))
        except Exception as e:
            return StructuredResult("error", "get_message", error=f"{type(e).__name__}: {e}")

    def search_messages(self, query: str, limit: int = 10) -> StructuredResult:
        """Search theo Zimbra query (from:, subject:, has:, after:MM/DD/YYYY, ...)."""
        token, err = self._ensure_token()
        if err:
            return err
        if not query or len(query.strip()) < 2:
            return StructuredResult("error", "search_messages", error="Query quá ngắn (< 2 ký tự).")
        try:
            items = mail_reader._search(token, query, max(1, min(limit, 20)))
            return StructuredResult(
                "ok",
                "search_messages",
                evidence={"query": query, "host": SOAP_URL},
                data={"count": len(items), "messages": items},
            )
        except mail_reader._MailError as e:
            return StructuredResult("error", "search_messages", error=str(e))
        except Exception as e:
            return StructuredResult("error", "search_messages", error=f"{type(e).__name__}: {e}")

    def get_thread(self, conversation_id: str, limit: int = 30) -> StructuredResult:
        """Ghép luồng theo conversation-id (SearchRequest types=conversation).

        Lưu ý: Zimbra dùng conversation-id có dạng '123-456'; truyền đúng id
        từ list_messages (trường 'id' đã strip phần '-456') sẽ match root.
        """
        token, err = self._ensure_token()
        if err:
            return err
        if not conversation_id:
            return StructuredResult("error", "get_thread", error="conversation_id trống.")
        # Tìm message có conv-id khớp
        try:
            query = f"in:inbox conv:{conversation_id}"
            items = mail_reader._search(token, query, max(1, min(limit, 50)))
            return StructuredResult(
                "ok",
                "get_thread",
                evidence={"conversation_id": conversation_id, "host": SOAP_URL},
                data={"count": len(items), "messages": items},
            )
        except mail_reader._MailError as e:
            return StructuredResult("error", "get_thread", error=str(e))
        except Exception as e:
            return StructuredResult("error", "get_thread", error=f"{type(e).__name__}: {e}")

    # ---- READONLY contract (R2) ----
    def _write_op_guard(self, op: str) -> StructuredResult:
        """Mọi operation GHI → unsupported_by_policy. Trừ khi owner phê duyệt riêng."""
        return StructuredResult(
            "unsupported",
            op,
            evidence={
                "policy": "R2 DRAFT-ONLY",
                "reason": "Cherry CHỈ ĐỌC mail. Gửi/mark_read/delete cần owner phê duyệt riêng từng lần.",
            },
            error="unsupported_by_policy",
        )

    def send_message(self, *_args: Any, **_kwargs: Any) -> StructuredResult:
        """R2: KHÔNG hỗ trợ gửi mail."""
        return self._write_op_guard("send_message")

    def mark_read(self, *_args: Any, **_kwargs: Any) -> StructuredResult:
        """R2: KHÔNG đánh dấu đã đọc (giữ nguyên trạng thái trên server)."""
        return self._write_op_guard("mark_read")

    def delete_message(self, *_args: Any, **_kwargs: Any) -> StructuredResult:
        """R2: KHÔNG xóa mail."""
        return self._write_op_guard("delete_message")


# Singleton instance — caller dùng VmailConnector() hoặc get_connector()
_default_connector: VmailConnector | None = None


def get_connector() -> VmailConnector:
    """Singleton VmailConnector (an toàn đa-thread basic — không lock, chấp nhận
    2 lần auth song song, dùng sau token cache 10 phút)."""
    global _default_connector
    if _default_connector is None:
        _default_connector = VmailConnector()
    return _default_connector


if __name__ == "__main__":
    # Smoke test: list_folders + connection_health
    conn = get_connector()
    print("Health:", conn.get_connection_health(force=True))
    r = conn.authenticate()
    print("Auth:", r.status, "|", r.error or "ok")
    if r.status == "ok":
        r2 = conn.list_folders()
        print("Folders:", r2.status, "| count:", (r2.data or {}).get("count", 0))
        r3 = conn.list_messages("inbox", 3)
        print("Messages:", r3.status, "| count:", (r3.data or {}).get("count", 0))
    # Verify R2 guard
    print("Send:", conn.send_message("to@x.com", "subj", "body").status)
