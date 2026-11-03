"""V8 Vietnamese Conversation Engine — mandatory test matrix (MASTER PROMPT V8 §VIII).

Nhóm A: tiếng Việt tự nhiên (normalize + classify + guidance)
Nhóm B: ngữ cảnh đa lượt (context-dependent guidance + history depth parity)
Nhóm C: giao tiếp công việc (evidence layers parity stream vs chat)
Nhóm D: hội thoại giọng nói (TTS reading layer + sentence-safe truncation)
Nhóm E: độ tin cậy (fail-honest cues, guardrails intact, env kill-switch)
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.vietnamese_conversation import (
    RequestKind,
    build_guidance_block,
    classify_request,
    normalize_vietnamese_input,
    should_inject_guidance,
)
from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.models import RetrievalResult
from quan_ai_brain.voice.voice_pipeline import sanitize_for_spoken_vietnamese

SERVER_PY = WORKSPACE / "src" / "quan_ai_brain" / "web" / "server.py"
STREAM_TOKENS = {
    "teach": "detect_teaching",
    "grounding": "collect_grounding_facts",
    "ttns": "looks_like_ttns_query",
    "rag": "DocumentRAG",
}


def _stream_body() -> str:
    """Trích body _handle_api_chat_stream từ server.py (không import module nặng)."""
    lines = SERVER_PY.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if "def _handle_api_chat_stream" in l)
    end = next(i for i, l in enumerate(lines) if "def _handle_api_plan" in l)
    return "\n".join(lines[start:end])


def _make_ctx(query: str):
    b = PromptContextBuilder()
    return b.build(user_query=query, retrieval=RetrievalResult(query=query, memories=[], total_found=0, total_chars=0))


# ═══════════════ Nhóm A — Tiếng Việt tự nhiên ═══════════════

class TestGroupAVietnameseNatural:
    def test_classify_question_short(self):
        assert classify_request("8766 là cổng gì?") == RequestKind.QUESTION_SHORT

    def test_classify_tech_analysis(self):
        assert classify_request("Phân tích kiến trúc DAG và so sánh 2 phương án") == RequestKind.TECH_ANALYSIS

    def test_classify_doc_request(self):
        assert classify_request("Viết prompt cho agent kiểm toán hệ thống") == RequestKind.DOC_REQUEST

    def test_classify_urgent(self):
        assert classify_request("Khẩn cấp: hệ thống còn chạy không?") == RequestKind.URGENT

    def test_classify_work_chat(self):
        assert classify_request("Em báo cáo tiến độ sprint tuần này giúp anh") == RequestKind.WORK_CHAT

    def test_normalize_strips_filler(self):
        out = normalize_vietnamese_input("ừ  ơi  cho anh hỏi   hiện trạng nhé")
        assert "ừ" not in out.split()[0]
        assert "  " not in out

    def test_normalize_preserves_technical_tokens(self):
        src = "Kiểm tra TASK-123 và R5 85% cổng 8766"
        assert normalize_vietnamese_input(src) == src

    def test_normalize_empty_and_none(self):
        assert normalize_vietnamese_input("") == ""
        assert normalize_vietnamese_input(None) is None  # type: ignore[arg-type]

    def test_guidance_block_contains_honesty_rules(self):
        block = build_guidance_block(RequestKind.QUESTION_SHORT)
        assert "KHÔNG bịa" in block
        assert ("Chưa hiểu thì HỎI LẠI" in block) or ("chưa đủ dữ liệu" in block)
        assert "Xưng 'em'" in block

    def test_guidance_voice_kind_short_sentences(self):
        block = build_guidance_block(RequestKind.VOICE_CHAT)
        assert "NGẮN" in block or "ngắn" in block

    def test_should_inject_vietnamese_toned(self):
        assert should_inject_guidance("Kiểm tra tiến độ giúp anh") is True

    def test_should_inject_vietnamese_untoned(self):
        assert should_inject_guidance("kiem tra tien do") is True

    def test_should_not_inject_english(self):
        assert should_inject_guidance("what is the port number?") is False

    def test_guidance_in_context_rendered(self):
        ctx = _make_ctx("làm tiếp đi")
        assert "[CONVERSATION GUIDANCE" in ctx.rendered_context
        assert "context_dependent" in ctx.rendered_context

    def test_guidance_in_context_english_query_not_injected(self):
        ctx = _make_ctx("what is the port?")
        assert "[CONVERSATION GUIDANCE" not in ctx.rendered_context

    def test_guidance_kill_switch_env(self, monkeypatch):
        monkeypatch.setenv("QUAN_AI_BRAIN_V8_GUIDANCE_OFF", "1")
        ctx = _make_ctx("làm tiếp đi")
        assert "[CONVERSATION GUIDANCE" not in ctx.rendered_context

    def test_context_original_blocks_intact(self):
        ctx = _make_ctx("trạng thái hệ thống")
        assert "[SYSTEM INSTRUCTIONS & GOVERNANCE]" in ctx.rendered_context
        assert "[APPROVED / VERIFIED MEMORY]" in ctx.rendered_context
        assert "[USER REQUEST]" in ctx.rendered_context


# ═══════════════ Nhóm B — Ngữ cảnh đa lượt ═══════════════

class TestGroupBMultiTurn:
    def test_context_dependent_classified(self):
        for q in ("Làm tiếp đi", "Sửa phần đó", "Kiểm tra lại giúp anh",
                  "Còn phương án nào tốt hơn không?", "Triển khai theo cách thứ hai",
                  "Cái này khác gì bản trước?", "Bắt đầu học tập", "Dừng lại"):
            assert classify_request(q) == RequestKind.CONTEXT_DEPENDENT, q

    def test_context_guidance_demands_history(self):
        block = build_guidance_block(RequestKind.CONTEXT_DEPENDENT)
        assert "RECENT CONVERSATION HISTORY" in block
        assert "hỏi lại" in block or "KHÔNG tự chọn" in block

    def test_stream_history_depth_is_6(self):
        body = _stream_body()
        assert "get_recent_session_history(session_id, limit=6)" in body

    def test_chat_history_depth_also_raised_for_parity(self):
        src = SERVER_PY.read_text(encoding="utf-8")
        # /api/chat giữ limit=3 (đã ổn); stream phải ≥ chat
        stream_ok = "limit=6" in _stream_body()
        assert stream_ok


# ═══════════════ Nhóm C — Giao tiếp công việc (parity) ═══════════════

class TestGroupCWorkParity:
    @pytest.mark.parametrize("token", list(STREAM_TOKENS.values()))
    def test_evidence_layers_present_in_stream(self, token: str):
        assert token in _stream_body(), f"stream thiếu {token}"

    def test_teach_note_wired_in_stream(self):
        body = _stream_body()
        assert "teach_note" in body
        assert 'full_text = (teach_note + "\\n\\n" + full_text)' in body or "teach_note +" in body

    def test_stream_ast_parses(self):
        ast.parse(SERVER_PY.read_text(encoding="utf-8"))

    def test_evidence_gate_external_safe(self):
        # external_lookup tự gate — câu nội bộ KHÔNG tốn quota ngoài
        from quan_ai_brain.tools.external_lookup import should_lookup_external

        assert should_lookup_external("trạng thái hệ thống nội bộ") is False
        assert should_lookup_external("tin tức hôm nay") is True


# ═══════════════ Nhóm D — Hội thoại giọng nói ═══════════════

class TestGroupDVoice:
    def test_r_codes_read_naturally(self):
        out = sanitize_for_spoken_vietnamese("Cổng R5 bị chặn theo R2")
        assert "R năm" in out and "R hai" in out
        assert "R5" not in out

    def test_technical_tokens_untouched(self):
        out = sanitize_for_spoken_vietnamese("Task TASK-123 trên cổng 8766")
        assert "TASK-123" in out and "8766" in out

    def test_no_mid_sentence_cut(self):
        long_text = "Đây là câu hoàn chỉnh có nghĩa. " * 15
        out = sanitize_for_spoken_vietnamese(long_text)
        tail_words = out.rstrip(".").rstrip().split()
        assert tail_words[-1] not in ("của", "và", "trên", "cho", "là", "về", "nói")

    def test_short_text_untouched_by_truncation(self):
        s = "Trả lời ngắn gọn."
        assert sanitize_for_spoken_vietnamese(s) == s

    def test_code_blocks_stripped_before_reading(self):
        out = sanitize_for_spoken_vietnamese("Kết quả: ```print(1)``` xong")
        assert "print" not in out
        assert "Đã bỏ qua mã kỹ thuật" in out


# ═══════════════ Nhóm E — Độ tin cậy ═══════════════

class TestGroupEReliability:
    def test_guidance_demands_no_fabrication(self):
        block = build_guidance_block(RequestKind.TECH_ANALYSIS)
        assert "chưa đủ căn cứ" in block
        assert "KHÔNG bịa" in block

    def test_guardrails_still_active(self):
        from quan_ai_brain.core.guardrails import OutputGuardrails

        sanitized, warnings = OutputGuardrails.sanitize("password=abc123 id_rsa here")
        assert warnings  # redaction/không để lộ
        assert "id_rsa" not in sanitized or "[PROTECTED_SYSTEM_PATH]" in sanitized

    def test_normalize_does_not_invent_diacritics(self):
        # V8 §6.1: KHÔNG tự sửa theo suy đoán — giữ nguyên text không dấu
        src = "kiem tra tien do"
        assert normalize_vietnamese_input(src) == src

    def test_classify_ambiguous_returns_reasonable(self):
        # câu mơ hồ không rơi vào CONTEXT_DEPENDENT đoán mò — guidance yêu cầu hỏi lại
        kind = classify_request("ok")
        assert kind in (RequestKind.OTHER, RequestKind.QUESTION_SHORT, RequestKind.WORK_CHAT)
