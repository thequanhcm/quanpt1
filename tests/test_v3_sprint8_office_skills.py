"""Tests — Sprint 8: To-do store, Email draft (draft-only), Approval Center API.

Mock/tmprath 100%: không đụng data/todos.db thật, không gửi mail, không đụng
governance.db thật.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.tools.email_draft import EmailDraftError, create_draft, validate_address
from quan_ai_brain.tools.todo_store import TodoStore


# ---------------------------------------------------------------------------
# (a) TodoStore
# ---------------------------------------------------------------------------

class TestTodoStore:
    def test_add_and_list(self, tmp_path):
        store = TodoStore(tmp_path / "todos.db")
        item = store.add(title="Gửi báo cáo tuần cho anh Hùng", due="2026-10-28")
        assert item["id"] > 0
        assert item["status"] == "open"
        items = store.list_open()
        assert len(items) == 1
        assert items[0]["title"] == "Gửi báo cáo tuần cho anh Hùng"

    def test_add_empty_title_raises(self, tmp_path):
        store = TodoStore(tmp_path / "todos.db")
        with pytest.raises(ValueError):
            store.add(title="   ")

    def test_mark_done(self, tmp_path):
        store = TodoStore(tmp_path / "todos.db")
        item = store.add(title="Việc test")
        assert store.mark_done(item["id"]) is True
        assert store.list_open() == []
        # done lần nữa → False (không done 2 lần)
        assert store.mark_done(item["id"]) is False

    def test_invalid_priority_normalized(self, tmp_path):
        store = TodoStore(tmp_path / "todos.db")
        item = store.add(title="Việc ưu tiên lạ", priority="urgent-max")
        assert item["priority"] == "normal"  # chuẩn hoá, không chết

    def test_overdue_and_today(self, tmp_path):
        store = TodoStore(tmp_path / "todos.db")
        store.add(title="Việc trễ", due="2026-10-20")
        store.add(title="Việc hôm nay", due="2026-10-27")
        store.add(title="Việc tương lai", due="2026-11-01")
        store.add(title="Việc không hạn", due="")
        groups = store.overdue_and_today(today="2026-10-27")
        assert [t["title"] for t in groups["overdue"]] == ["Việc trễ"]
        assert [t["title"] for t in groups["today"]] == ["Việc hôm nay"]


# ---------------------------------------------------------------------------
# (b) Email draft — DRAFT ONLY
# ---------------------------------------------------------------------------

class TestEmailDraft:
    def test_create_draft_writes_eml(self, tmp_path):
        result = create_draft(
            to="colleague@viettel.com.vn",
            subject="Báo cáo tuần 43",
            body="Kính gửi anh,\nĐây là báo cáo tuần 43.",
            draft_dir=tmp_path,
        )
        assert result["created"] is True
        path = Path(result["path"])
        assert path.exists()
        # Đọc .eml bằng email lib với policy default (tự decode RFC2047 subject)
        import email as email_lib

        msg = email_lib.message_from_bytes(path.read_bytes(), policy=email_lib.policy.default)
        assert msg["To"] == "colleague@viettel.com.vn"
        assert "Báo cáo tuần 43" in str(msg["Subject"])
        body = msg.get_payload(decode=True).decode("utf-8")
        assert "Đây là báo cáo tuần 43" in body
        # .eml KHÔNG chứa lệnh gửi — chỉ là file nháp
        assert "SMTP" not in path.read_text(encoding="utf-8", errors="replace")

    def test_missing_subject_raises(self, tmp_path):
        with pytest.raises(EmailDraftError):
            create_draft(to="a@b.vn", subject="  ", body="nội dung", draft_dir=tmp_path)

    def test_missing_body_raises(self, tmp_path):
        with pytest.raises(EmailDraftError):
            create_draft(to="a@b.vn", subject="Tiêu đề", body="", draft_dir=tmp_path)

    def test_invalid_address_raises(self, tmp_path):
        with pytest.raises(EmailDraftError):
            create_draft(to="khong-phai-email", subject="S", body="B", draft_dir=tmp_path)

    def test_validate_address(self):
        assert validate_address("quanpt1@viettel.com.vn") == "quanpt1@viettel.com.vn"
        with pytest.raises(EmailDraftError):
            validate_address("a b@c")


# ---------------------------------------------------------------------------
# (a) NetChat router: lệnh todo
# ---------------------------------------------------------------------------

def _load_router():
    spec = importlib.util.spec_from_file_location(
        "netchat_command_center_s8", WORKSPACE / "tools" / "netchat_command_center.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["netchat_command_center_s8"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestNetChatTodoRouting:
    def test_parse_todo_add_simple(self):
        mod = _load_router()
        parsed = mod._parse_todo_add("nhớ giúp tôi: gửi báo cáo tuần")
        assert parsed == ("gửi báo cáo tuần", "")

    def test_parse_todo_add_with_due(self):
        mod = _load_router()
        parsed = mod._parse_todo_add("nhớ giúp tôi: họp ban hành hạn 2026-11-05")
        assert parsed is not None
        title, due = parsed
        assert title == "họp ban hành"
        assert due == "2026-11-05"

    def test_parse_todo_add_wrong_command(self):
        mod = _load_router()
        assert mod._parse_todo_add("trạng thái hệ thống") is None
        assert mod._parse_todo_add("nhớ giúp tôi:") is None  # rỗng

    def test_route_todo_add_end_to_end(self, tmp_path, monkeypatch):
        mod = _load_router()
        # trỏ WORKSPACE của router sang tmp để không đụng DB thật
        monkeypatch.setattr(mod, "WORKSPACE", tmp_path)
        intent, reply = mod.route_message("nhớ giúp tôi: kiểm tra camera Pi 5 hạn mai")
        assert intent == "todo_add"
        assert "✅" in reply
        # DB nằm trong tmp
        assert (tmp_path / "data" / "todos.db").exists()

    def test_route_todo_list_command(self, tmp_path, monkeypatch):
        mod = _load_router()
        monkeypatch.setattr(mod, "WORKSPACE", tmp_path)
        mod.route_message("nhớ giúp tôi: việc A")
        intent, reply = mod.route_message("việc cần làm")
        assert intent == "todo"
        assert "VIỆC CẦN LÀM" in reply and "việc A" in reply


# ---------------------------------------------------------------------------
# (c) Approval Center API handlers
# ---------------------------------------------------------------------------

def _server_mod():
    """Load server.py 1 lần, trả về module (dùng cho monkeypatch path helper)."""
    import sys as _sys

    _sys.path.insert(0, str(WORKSPACE / "src"))
    import quan_ai_brain.web.server as srv

    return srv


def mod_placeholder():
    return _server_mod()


class TestApprovalCenterAPI:
    def _make_handler(self, monkeypatch, tmp_path, client="127.0.0.1"):
        """Dựng fake handler instance gắn method THẬT từ BrainAPIHandler."""
        import sys as _sys

        _sys.path.insert(0, str(WORKSPACE / "src"))
        from quan_ai_brain.web.server import BrainAPIHandler

        class FakeHandler:
            sent = None
            error = None

            def _send_json(self, payload, code=200):
                FakeHandler.sent = payload

            def _send_error_json(self, msg, code=400):
                FakeHandler.error = {"error": msg, "code": code}

        # Gắn method THẬT từ class handler của server (bound thủ công)
        FakeHandler._handle_api_approvals_decide = BrainAPIHandler._handle_api_approvals_decide
        FakeHandler._handle_api_approvals_list = BrainAPIHandler._handle_api_approvals_list
        FakeHandler._handle_api_todos_list = BrainAPIHandler._handle_api_todos_list

        h = FakeHandler()
        h.client_address = (client, 12345)
        return h, mod_placeholder()

    def test_decide_requires_localhost(self, tmp_path, monkeypatch):
        h, mod = self._make_handler(monkeypatch, tmp_path, client="192.168.1.50")
        monkeypatch.setattr(
            mod, "_find_workspace_root", lambda: tmp_path, raising=False
        )
        h._handle_api_approvals_decide({"task_code": "X", "decision": "approve"})
        assert h.error and h.error["code"] == 403

    def test_decide_unknown_card_404(self, tmp_path, monkeypatch):
        h, mod = self._make_handler(monkeypatch, tmp_path)
        monkeypatch.setattr(
            mod, "_find_workspace_root", lambda: tmp_path, raising=False
        )
        # governance.db trống trong tmp → card không tồn tại
        h._handle_api_approvals_decide({"task_code": "TASK-KHONGCO", "decision": "approve"})
        assert h.error and h.error["code"] == 404

    def test_decide_bad_decision_400(self, tmp_path, monkeypatch):
        h, mod = self._make_handler(monkeypatch, tmp_path)
        monkeypatch.setattr(
            mod, "_find_workspace_root", lambda: tmp_path, raising=False
        )
        # Tạo card thật trong tmp governance.db
        from quan_ai_brain.governance.approval_cards import ApprovalCardStore

        store = ApprovalCardStore(tmp_path / "data" / "governance.db", workspace=str(tmp_path))
        store.create_card("TASK-T8", "Test card", "nội dung")
        h._handle_api_approvals_decide({"task_code": "TASK-T8", "decision": "abc"})
        assert h.error and h.error["code"] == 400

    def test_decide_approve_consumes_once(self, tmp_path, monkeypatch):
        h, mod = self._make_handler(monkeypatch, tmp_path)
        monkeypatch.setattr(
            mod, "_find_workspace_root", lambda: tmp_path, raising=False
        )
        from quan_ai_brain.governance.approval_cards import ApprovalCardStore

        store = ApprovalCardStore(tmp_path / "data" / "governance.db", workspace=str(tmp_path))
        store.create_card("TASK-T9", "Card duyệt qua dashboard", "nội dung")

        h._handle_api_approvals_decide({"task_code": "TASK-T9", "decision": "approve"})
        assert h.sent and h.sent["status"] == "APPROVED"
        # approve lần 2 → 409 (đã duyệt) — reset CLASS attrs (method ghi vào class)
        type(h).sent = None
        type(h).error = None
        h._handle_api_approvals_decide({"task_code": "TASK-T9", "decision": "approve"})
        assert h.error and h.error["code"] == 409
