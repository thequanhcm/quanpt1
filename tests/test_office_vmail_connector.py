# -*- coding: utf-8 -*-
"""Tests cho VmailConnector (CHERRY VMAIL INTELLIGENCE Sprint 1, card TASK-VMAIL-S1).

Mock 100% — KHÔNG gọi SOAP thật. Test interface §4.3 + StructuredResult + R2 guard +
Health States (§13). Mọi test chạy offline, fail-honest (status="error" khi giả
lập lỗi, không fake số liệu).

Bộ test:
1. authenticate(): ok / auth fail / exception
2. validate_session(): cached ok / token chết
3. _ensure_token(): re-auth khi cache miss / fail
4. list_folders(): 13 folder
5. list_messages(): inbox/sent + limit clamp 1-20
6. get_message(): body preview, mid invalid → error
7. search_messages(): query ngắn → error
8. get_thread(): conversation-id probe
9. R2 guard: send/mark_read/delete → unsupported_by_policy
10. Health states: HEALTHY/DEGRADED/UNHEALTHY/DISCONNECTED
11. StructuredResult: status validation + to_dict
12. Singleton: get_connector() trả cùng instance
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE / "tools"))

# Import sau khi sys.path đã chỉnh
from quan_ai_brain.office.vmail_connector import (  # noqa: E402
    DEGRADED,
    DISCONNECTED,
    HEALTHY,
    SOAP_URL,
    StructuredResult,
    UNHEALTHY,
    VmailConnector,
    get_connector,
)


# ---- Fixtures ----
@pytest.fixture
def conn() -> VmailConnector:
    return VmailConnector()


@pytest.fixture
def fake_token() -> str:
    return "FAKE_AUTH_TOKEN_abc123"


# ---- 1. authenticate ----
class TestAuthenticate:
    def test_ok(self, conn: VmailConnector, fake_token: str):
        with patch("mail_reader._auth", return_value=fake_token):
            r = conn.authenticate()
        assert r.status == "ok"
        assert r.operation_id == "authenticate"
        assert r.error is None
        assert r.evidence["health"] in (HEALTHY, DEGRADED)  # force=True → mới nhất
        assert conn._token == fake_token
        assert conn._auth_fails == 0

    def test_auth_fail(self, conn: VmailConnector):
        from mail_reader import _MailError
        with patch("mail_reader._auth", side_effect=_MailError("sai mật khẩu")):
            r = conn.authenticate()
        assert r.status == "error"
        assert "sai mật khẩu" in r.error
        assert r.evidence["auth_fails"] == 1
        assert conn._auth_fails == 1

    def test_auth_exception(self, conn: VmailConnector):
        with patch("mail_reader._auth", side_effect=ConnectionError("dns fail")):
            r = conn.authenticate()
        assert r.status == "error"
        assert "ConnectionError" in r.error


# ---- 2. validate_session ----
class TestValidateSession:
    def test_ok(self, conn: VmailConnector, fake_token: str):
        conn._token = fake_token
        conn._token_issued_at = 100.0
        with patch("mail_reader._search", return_value=[{"id": "1"}]):
            with patch("time.time", return_value=120.0):
                r = conn.validate_session()
        assert r.status == "ok"
        assert r.evidence["token_age_s"] == 20

    def test_no_token(self, conn: VmailConnector):
        r = conn.validate_session()
        assert r.status == "error"
        assert "Chưa có token" in r.error

    def test_token_expired_clears_cache(self, conn: VmailConnector, fake_token: str):
        from mail_reader import _MailError
        conn._token = fake_token
        conn._auth_fails = 0
        with patch("mail_reader._search", side_effect=_MailError("session expired")):
            r = conn.validate_session()
        assert r.status == "error"
        assert conn._token is None  # cache cleared
        assert conn._auth_fails == 1


# ---- 3. _ensure_token ----
class TestEnsureToken:
    def test_reuse_cache(self, conn: VmailConnector, fake_token: str):
        conn._token = fake_token
        conn._token_issued_at = __import__("time").time()
        with patch.object(conn, "validate_session") as vs:
            vs.return_value = StructuredResult("ok", "validate_session")
            tok, err = conn._ensure_token()
        assert tok == fake_token
        assert err is None
        vs.assert_called_once()

    def test_re_auth_on_cache_miss(self, conn: VmailConnector, fake_token: str):
        conn._token = None
        with patch.object(conn, "authenticate") as a:
            a.return_value = StructuredResult("ok", "authenticate", data=None)
            with patch("mail_reader._auth", return_value=fake_token):
                # _ensure_token re-calls authenticate() — we mock that above
                tok, err = conn._ensure_token()
        assert err is None  # mock authenticate returned ok
        a.assert_called()

    def test_auth_fail_returns_error(self, conn: VmailConnector):
        conn._token = None
        with patch.object(conn, "authenticate") as a:
            a.return_value = StructuredResult("error", "authenticate", error="fail")
            tok, err = conn._ensure_token()
        assert tok is None
        assert err is not None
        assert err.status == "error"


# ---- 4. list_folders ----
class TestListFolders:
    def test_13_folders(self, conn: VmailConnector, fake_token: str):
        conn._token = fake_token
        conn._token_issued_at = __import__("time").time()
        # Mock XML response với 13 folder
        folder_xml = (
            f'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
            f'xmlns="urn:zimbraMail">'
            + "<folder id='1' name='Inbox' view='message' u='5' n='42'/>"
            + "<folder id='2' name='Sent' view='message' n='120'/>"
            + "<folder id='3' name='Drafts' view='message' n='3'/>"
            + "<folder id='4' name='Junk' view='message' n='18'/>"
            + "<folder id='5' name='Archive' view='message' n='350'/>"
            + "<folder id='6' name='Calendar' view='appointment'/>"
            + "<folder id='7' name='Tasks' view='task'/>"
            + "<folder id='8' name='Address Book' view='contact'/>"
            + "<folder id='9' name='Notes' view='wiki'/>"
            + "<folder id='10' name='Documents' view='document'/>"
            + "<folder id='11' name='Chats' view='message'/>"
            + "<folder id='12' name='Trash' view='message' n='7'/>"
            + "<folder id='13' name='Outbox' view='message'/>"
            + "</soap:Envelope>"
        )
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._soap", return_value=folder_xml):
                r = conn.list_folders()
        assert r.status == "ok"
        assert r.data["count"] == 13
        names = [f["name"] for f in r.data["folders"]]
        assert "Inbox" in names and "Sent" in names and "Calendar" in names


# ---- 5. list_messages ----
class TestListMessages:
    def test_inbox_default(self, conn: VmailConnector, fake_token: str):
        fake_messages = [
            {"id": "100", "subject": "Test", "from_addr": "x@y", "date": "2026-11-23 10:00"},
            {"id": "101", "subject": "Test 2", "from_addr": "z@y", "date": "2026-11-23 09:00"},
        ]
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._search", return_value=fake_messages) as s:
                r = conn.list_messages("inbox", 5)
        assert r.status == "ok"
        assert r.data["count"] == 2
        # Query mapping: inbox → in:inbox
        args = s.call_args
        assert args[0][1] == "in:inbox"
        # Limit clamp: 5 giữ nguyên
        assert args[0][2] == 5

    def test_limit_clamp_max20(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._search", return_value=[]) as s:
                conn.list_messages("inbox", 100)
        assert s.call_args[0][2] == 20  # clamp về max 20

    def test_limit_clamp_min1(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._search", return_value=[]) as s:
                conn.list_messages("inbox", 0)
        assert s.call_args[0][2] == 1  # clamp về min 1

    def test_custom_folder_query(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._search", return_value=[]) as s:
                conn.list_messages("junk", 3)
        assert "in:junk" in s.call_args[0][1]

    def test_ensure_token_error(self, conn: VmailConnector):
        err = StructuredResult("error", "ensure_token", error="auth fail")
        with patch.object(conn, "_ensure_token", return_value=(None, err)):
            r = conn.list_messages("inbox", 5)
        assert r.status == "error"
        assert "auth fail" in r.error


# ---- 6. get_message ----
class TestGetMessage:
    def test_ok(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._get_body", return_value="Xin chào anh Quân"):
                r = conn.get_message("123")
        assert r.status == "ok"
        assert r.data["body_preview"] == "Xin chào anh Quân"
        assert r.evidence["mid"] == "123"
        assert r.evidence["body_len"] == 17  # "Xin chào anh Quân" = 17 chars có dấu

    def test_invalid_mid(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            r = conn.get_message("abc-not-number")
        assert r.status == "error"
        assert "không hợp lệ" in r.error

    def test_empty_mid(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            r = conn.get_message("")
        assert r.status == "error"

    def test_soap_error(self, conn: VmailConnector, fake_token: str):
        from mail_reader import _MailError
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._get_body", side_effect=_MailError("msg not found")):
                r = conn.get_message("999")
        assert r.status == "error"


# ---- 7. search_messages ----
class TestSearchMessages:
    def test_ok(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._search", return_value=[{"id": "1"}]) as s:
                r = conn.search_messages("from:abc@viettel.com.vn", 5)
        assert r.status == "ok"
        assert s.call_args[0][1] == "from:abc@viettel.com.vn"

    def test_query_too_short(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            r = conn.search_messages("a", 5)
        assert r.status == "error"
        assert "quá ngắn" in r.error

    def test_empty_query(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            r = conn.search_messages("", 5)
        assert r.status == "error"


# ---- 8. get_thread ----
class TestGetThread:
    def test_ok(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            with patch("mail_reader._search", return_value=[
                {"id": "100-1", "subject": "Re: X"},
                {"id": "100-2", "subject": "Re: X"},
                {"id": "100-3", "subject": "Re: X"},
            ]) as s:
                r = conn.get_thread("100")
        assert r.status == "ok"
        assert r.data["count"] == 3
        # Query phải có conv:
        assert "conv:100" in s.call_args[0][1]

    def test_empty_conversation_id(self, conn: VmailConnector, fake_token: str):
        with patch.object(conn, "_ensure_token", return_value=(fake_token, None)):
            r = conn.get_thread("")
        assert r.status == "error"
        assert "trống" in r.error


# ---- 9. R2 Guard (write operations) ----
class TestR2Guard:
    def test_send_unsupported(self, conn: VmailConnector):
        r = conn.send_message("to@x.com", "subj", "body")
        assert r.status == "unsupported"
        assert r.operation_id == "send_message"
        assert "R2 DRAFT-ONLY" in r.evidence["policy"]
        assert r.error == "unsupported_by_policy"

    def test_mark_read_unsupported(self, conn: VmailConnector):
        r = conn.mark_read("123")
        assert r.status == "unsupported"

    def test_delete_unsupported(self, conn: VmailConnector):
        r = conn.delete_message("123")
        assert r.status == "unsupported"

    def test_write_ops_no_token_needed(self, conn: VmailConnector):
        """R2 guard chạy trước _ensure_token — KHÔNG cần auth cho operation GHI."""
        r = conn.send_message("to@x.com", "subj", "body")
        assert r.status == "unsupported"
        assert conn._token is None  # auth KHÔNG bị gọi


# ---- 10. Health States (§13) ----
class TestHealthStates:
    def test_disconnected_when_network_fail(self, conn: VmailConnector):
        with patch("socket.create_connection", side_effect=OSError("no route")):
            h = conn.get_connection_health(force=True)
        assert h == DISCONNECTED

    def test_healthy_when_token_and_probe_ok(self, conn: VmailConnector, fake_token: str):
        conn._token = fake_token
        conn._token_issued_at = __import__("time").time()
        with patch("socket.create_connection"):
            h = conn.get_connection_health(force=True)
        assert h == HEALTHY

    def test_unhealthy_after_2_auth_fails(self, conn: VmailConnector, fake_token: str):
        conn._auth_fails = 2
        conn._token = fake_token
        conn._token_issued_at = __import__("time").time()
        with patch("socket.create_connection"):
            h = conn.get_connection_health(force=True)
        assert h == UNHEALTHY

    def test_degraded_when_token_cache_expired(self, conn: VmailConnector, fake_token: str):
        import time as _t
        conn._token = fake_token
        conn._token_issued_at = _t.time() - (_t.time() - 1) - 1000  # quá hạn rõ ràng
        # Set TTL > 1000s để tạo điều kiện degraded
        import quan_ai_brain.office.vmail_connector as vc
        old_ttl = vc._TOKEN_TTL_S
        vc._TOKEN_TTL_S = 60
        try:
            with patch("socket.create_connection"):
                h = conn.get_connection_health(force=True)
            # Sau 60s token cache → DEGRADED (chưa confirm chết)
            assert h == DEGRADED
        finally:
            vc._TOKEN_TTL_S = old_ttl

    def test_no_token_no_fails_degraded(self, conn: VmailConnector):
        """Chưa authenticate + network OK → DEGRADED (chưa chắc khỏe)."""
        with patch("socket.create_connection"):
            h = conn.get_connection_health(force=True)
        assert h == DEGRADED

    def test_health_cache(self, conn: VmailConnector, fake_token: str):
        """Cache 60s: lần thứ 2 không probe lại."""
        conn._token = fake_token
        conn._token_issued_at = __import__("time").time()
        with patch("socket.create_connection") as probe:
            h1 = conn.get_connection_health(force=True)
            h2 = conn.get_connection_health()  # cache
        assert probe.call_count == 1  # chỉ 1 lần probe


# ---- 11. StructuredResult ----
class TestStructuredResult:
    def test_to_dict(self):
        r = StructuredResult("ok", "list_messages", evidence={"a": 1}, data={"b": 2})
        d = r.to_dict()
        assert d["status"] == "ok"
        assert d["operation_id"] == "list_messages"
        assert d["evidence"] == {"a": 1}
        assert d["data"] == {"b": 2}
        assert d["error"] is None
        assert "T" in d["timestamp"]  # ISO-8601

    def test_invalid_status(self):
        with pytest.raises(ValueError, match="status phải"):
            StructuredResult("unknown", "op")

    def test_repr(self):
        r = StructuredResult("error", "test", error="fail")
        assert "error" in repr(r) and "test" in repr(r)

    def test_operation_index_increments(self, conn: VmailConnector):
        """Mỗi StructuredResult tăng operation_index (audit-friendly)."""
        r1 = StructuredResult("ok", "op1")
        r2 = StructuredResult("ok", "op2")
        # Index tăng theo thứ tự tạo
        assert r2.operation_index > r1.operation_index


# ---- 12. Singleton ----
class TestSingleton:
    def test_same_instance(self):
        a = get_connector()
        b = get_connector()
        assert a is b

    def test_reset_singleton(self):
        import quan_ai_brain.office.vmail_connector as vc
        old = vc._default_connector
        vc._default_connector = None
        try:
            c = get_connector()
            d = get_connector()
            assert c is d
        finally:
            vc._default_connector = old


# ---- 13. Cross-check: SOAP_URL from mail_reader ----
def test_soap_url_constant():
    assert "vmail.viettel.vn" in SOAP_URL
    assert SOAP_URL.startswith("https://")


# ---- 14. End-to-end mock smoke ----
def test_full_flow_mock(conn: VmailConnector):
    """Mock full flow: authenticate → list_messages → get_message → R2 guard."""
    fake_messages = [
        {"id": "200", "subject": "Test", "from_addr": "a@x.vn", "date": "2026-11-23 10:00",
         "body_preview": "preview", "has_attachment": False, "read": True}
    ]
    with patch("mail_reader._auth", return_value="TOKEN"):
        r = conn.authenticate()
        assert r.status == "ok"
        with patch("mail_reader._search", return_value=fake_messages):
            r = conn.list_messages("inbox", 5)
            assert r.status == "ok"
            assert r.data["count"] == 1
            with patch("mail_reader._get_body", return_value="full body"):
                r = conn.get_message("200")
                assert r.status == "ok"
                assert r.data["body_preview"] == "full body"
    # R2: gửi KHÔNG được
    r = conn.send_message("a@x.vn", "subj", "body")
    assert r.status == "unsupported"
