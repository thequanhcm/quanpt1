"""Fix 'ghi âm trong 1 phút' bị hiểu nhầm thành STOP (13/11/2026, screenshot owner).

Root cause 1: alias không dấu 'dung' trong COMMAND_PATTERNS['stop'] match substring
'nội dung' → câu 'Em ghi âm trong 1 phút... nội dung...' → intent 'stop'.
Root cause 2: thiếu intent 'voice_record' — lệnh ghi âm mic PC + STT chưa tồn tại.

100% mock — KHÔNG ghi âm thật, KHÔNG gọi /api/chat trong test.
"""
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))

from netchat_command_center import (  # noqa: E402
    _parse_record_duration,
    detect_intent,
    _is_question,
)


class TestStopAliasNoLongerMatchesSubstring:
    """Fix 1: 'dung'/'ngung'/'mo'/'bat'/'tat' chỉ kích hoạt ở ĐẦU câu."""

    @pytest.mark.parametrize("msg", [
        "Em ghi âm trong 1 phút và tóm tắt các nội dung ghi âm bằng văn bản gửi anh",
        "Nội dung báo cáo gồm những gì?",
        "hướng dẫn sử dụng là ở đâu",
        "chỉnh nội dung này giúp em",
    ])
    def test_no_false_stop(self, msg):
        assert detect_intent(msg) != "stop", f"{msg!r} bị nuốt thành stop"

    @pytest.mark.parametrize("msg", ["dung lai", "dừng lại", "stop", "ngung di"])
    def test_real_stop_commands_still_work(self, msg):
        assert detect_intent(msg) == "stop", f"{msg!r} phải là stop"

    def test_music_stop_precedence_kept(self):
        assert detect_intent("dừng nhạc") == "tony_music_stop"
        assert detect_intent("stop nhạc") == "tony_music_stop"


class TestQuestionDetectionWidened:
    def test_la_gi_is_question(self):
        assert _is_question("nội dung báo cáo là gì") is True

    def test_the_nao_is_question(self):
        assert _is_question("trạng thái hệ thống thế nào") is True

    def test_plain_command_not_question(self):
        assert _is_question("báo cáo") is False
        assert _is_question("trạng thái") is False


class TestVoiceRecordIntent:
    def test_owner_screenshot_command_detected(self):
        msg = "Em ghi âm trong 1 phút và tóm tắt các nội dung ghi âm bằng văn bản gửi anh"
        assert detect_intent(msg) == "voice_record"

    @pytest.mark.parametrize("msg", ["ghi âm", "ghi âm 30 giây", "record audio 2 phút",
                                     "ghi lại âm thanh giúp em"])
    def test_variants_detected(self, msg):
        assert detect_intent(msg) == "voice_record", f"{msg!r} không nhận diện ghi âm"


class TestDurationParser:
    def test_minutes(self):
        assert _parse_record_duration("ghi âm trong 1 phút") == 60
        assert _parse_record_duration("ghi âm 2 phút") == 120

    def test_seconds(self):
        assert _parse_record_duration("ghi âm 30 giây") == 30

    def test_default_60(self):
        assert _parse_record_duration("ghi âm") == 60

    def test_clamped(self):
        assert _parse_record_duration("ghi âm 10 phút") == 300   # max 300s
        assert _parse_record_duration("ghi âm 2 giây") == 5      # min 5s
