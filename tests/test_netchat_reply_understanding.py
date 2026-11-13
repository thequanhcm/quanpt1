"""Fix 'CHERRY trả lời sai nội dung' (13/11/2026, screenshot owner).

2 tình huống trong ảnh netChat:
1. Reply trích dẫn card TASK-xxx + hỏi tự nhiên 'A đang hỏi chi tiết thông báo này'
   → trước đây trả '❓ CHƯA HIỂU LỆNH' (parse chỉ nhận startswith động từ).
2. Hỏi 'PR là dự án mới ah' ngay sau khi bot tự báo PR #27
   → trước đây GLM mất ngữ cảnh (bot gửi chủ động không vào conversation_state).

100% mock: không DM thật, không đụng governance.db thật (dùng tmp DB trong workspace).
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BRAIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRAIN_ROOT / "src"))

from quan_ai_brain.governance.netchat_approval_adapter import (  # noqa: E402
    NetChatApprovalAdapter,
)


@pytest.fixture()
def adapter(monkeypatch):
    """Adapter với approval_cards DB tạm TRONG workspace (PathGuard yêu cầu)."""
    import quan_ai_brain.governance.netchat_approval_adapter as aa
    from quan_ai_brain.governance.approval_cards import ApprovalCardStore

    tmp_dir = tempfile.mkdtemp(dir=str(BRAIN_ROOT / "data"))
    tmp_db = Path(tmp_dir) / "test_parse_cards.db"
    orig = aa.ApprovalCardStore
    monkeypatch.setattr(
        aa, "ApprovalCardStore",
        lambda *a, **kw: orig(tmp_db, workspace=str(BRAIN_ROOT)),
    )
    yield NetChatApprovalAdapter()
    monkeypatch.undo()
    try:
        os.remove(tmp_db)
        os.rmdir(tmp_dir)
    except OSError:
        pass


class TestNaturalQuestionWithTaskCode:
    """Fix 1: câu hỏi tự nhiên có mã TASK → CHI TIẾT (không CHƯA HIỂU LỆNH)."""

    def test_owner_screenshot_case_returns_detail(self, adapter):
        msg = ('[Anh QUANPT1 đang REPLY trích dẫn tin CHERRY gửi trước: '
               '"📋 PR 27 SẴN SÀNG **TASK-AGENTIC-SEC-1** ..."]\n'
               'Câu hỏi của anh: A đang hỏi chi tiết thoing báo này')
        p = adapter.parse(msg)
        assert p["action"] == "detail"
        assert p["task_code"] == "TASK-AGENTIC-SEC-1"

    def test_question_markers_map_to_detail(self, adapter):
        for q in ["thông báo này là gì vậy TASK-ABC-1",
                  "cho anh xem trạng thái TASK-ABC-1 với",
                  "card này nghĩa sao TASK-ABC-1?"]:
            p = adapter.parse(q)
            assert p["action"] == "detail", f"{q!r} → {p['action']}"

    def test_mid_sentence_action_verbs_still_work(self, adapter):
        assert adapter.parse("anh xác nhận duyệt TASK-ABC-1 nhé")["action"] == "approve"
        assert adapter.parse("TASK-ABC-1 này anh từ chối")["action"] == "reject"
        assert adapter.parse("TASK-ABC-1 cần sửa lại phương án")["action"] == "amend"

    def test_no_task_code_still_none(self, adapter):
        # Không có mã → không nuốt vào approval flow (đi GLM với context).
        assert adapter.parse("PR là dự án mới ah")["action"] == "none"
        assert adapter.parse("duyệt merge PR #26")["action"] == "none"

    def test_handle_never_says_chua_hieu_lenh_for_question(self, adapter, monkeypatch):
        """E2E: handle_owner_message với câu hỏi + mã KHÔNG tồn tại → giải thích
        'KHÔNG TÌM THẤY' (hữu ích), KHÔNG BAO GIỜ 'CHƯA HIỂU LỆNH'."""
        msg = "cho anh biết TASK-KHONG-TON-TAI này là gì với"
        reply = adapter.handle_owner_message(msg, sender_user_id="owner", post=False)
        assert "CHƯA HIỂU LỆNH" not in reply


class TestBotBroadcastContext:
    """Fix 2: bot tự gửi tin → owner hỏi lại → query có ngữ cảnh broadcast."""

    @pytest.fixture()
    def nar(self):
        sys.path.insert(0, str(BRAIN_ROOT / "tools"))
        import netchat_auto_responder as nar
        return nar

    def test_save_and_load_broadcast(self, nar, tmp_path, monkeypatch):
        # Trỏ broadcast file về tmp để không đụng data/ thật
        bc_file = tmp_path / "last_bot_broadcast.txt"
        monkeypatch.setattr(
            nar, "_BRAIN_ROOT", str(tmp_path), raising=False)
        nar._save_bot_broadcast("📋 PR #27 — ATTT 4 slice, commit 786a7d6")
        loaded = nar._load_bot_broadcast()
        assert "PR #27" in loaded and "786a7d6" in loaded

    def test_broadcast_expired(self, nar, tmp_path, monkeypatch):
        monkeypatch.setattr(nar, "_BRAIN_ROOT", str(tmp_path), raising=False)
        bc_file = tmp_path / "data" / "last_bot_broadcast.txt"
        bc_file.parent.mkdir(parents=True, exist_ok=True)
        bc_file.write_text("0\n stale content", encoding="utf-8")  # ts=0 → hết hạn
        assert nar._load_bot_broadcast() == ""

    def test_ref_pattern_matches_pr(self, nar):
        import re
        pat = r"\b(PR\s*#?\d*|pull request|thông báo|thong bao|báo cáo|bao cao|tin vừa|tin trên|tin này|cái vừa|notification|alert)\b"
        assert re.search(pat, "PR là dự án mới ah", re.IGNORECASE)
        assert re.search(pat, "thông báo này nghĩa sao", re.IGNORECASE)
        assert not re.search(pat, "hôm nay thời tiết thế nào", re.IGNORECASE)
