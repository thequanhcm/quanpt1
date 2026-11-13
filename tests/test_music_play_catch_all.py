"""'Phát nhạc TẤT CẢ các bài được yêu cầu' (13/11/2026, yêu cầu owner).

3 fix:
1. tony_music_play regex TRƯỚC pc_open + phủ 'mở nhạc/mở bài hát/nghe bài/play music'
   (trước đây 'mở nhạc X' → pc_open mở app PC sai; 'nghe bài X' → không hiểu).
2. Fallback loa PC: Pi5 lỗi/offline → search YouTube → mở browser PC.
3. Music stop TRƯỚC arg intents: 'tắt nhạc' từng bị pc_close nuốt (pre-existing).

100% mock — KHÔNG phát nhạc thật, KHÔNG mở browser, KHÔNG gọi 8766/8768.
"""
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))

import netchat_command_center as cc  # noqa: E402


@pytest.fixture(autouse=True)
def _mock_handlers(monkeypatch):
    """Mock mọi handler có side-effect thật."""
    monkeypatch.setattr(cc, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(cc, "handle_tony_music_play",
                        lambda text, payload=None: f"MOCK_MUSIC({text})")
    monkeypatch.setattr(cc, "handle_pc_open", lambda text: f"MOCK_PC_OPEN({text})")
    monkeypatch.setattr(cc, "handle_pc_close", lambda text: f"MOCK_PC_CLOSE({text})")
    monkeypatch.setattr(cc, "handle_tony_music_stop", lambda payload=None: "MOCK_MUSIC_STOP")
    monkeypatch.setattr(cc, "handle_tony_youtube", lambda text: f"MOCK_YT({text})")


class TestMusicPlayCatchAll:
    """Mọi cách nói 'phát/bật/mở/nghe/play + nhạc/bài' → tony_music_play."""

    @pytest.mark.parametrize("msg,expected_arg", [
        ("cherry phát nhạc sài gòn tôi yêu", "sài gòn tôi yêu"),
        ("cherry mở nhạc mẹ yêu", "mẹ yêu"),
        ("mở nhạc mẹ yêu", "mẹ yêu"),
        ("cherry mở bài hát mẹ yêu", "mẹ yêu"),
        ("nghe bài mẹ yêu", "mẹ yêu"),
        ("cherry nghe nhạc trữ tình", "trữ tình"),
        ("play music heavier than before", "heavier than before"),
        ("phát nhạc đáng yêu nhất điệu ballot", "đáng yêu nhất điệu ballot"),
        ("bật nhạc không lời", "không lời"),
        ("cherry bật bài trăm năm gọi tên ta", "trăm năm gọi tên ta"),
    ])
    def test_play_variants(self, msg, expected_arg):
        intent, reply = cc.route_message(msg, payload={"channel_id": "T", "message_id": "T"})
        assert intent == "tony_music_play", f"{msg!r} → {intent} (sai)"
        assert expected_arg in reply, f"đối số {expected_arg!r} không có trong {reply!r}"


class TestMusicPlayBeforePcOpen:
    """'mở nhạc/mở bài hát' KHÔNG được rơi vào pc_open."""

    @pytest.mark.parametrize("msg", ["mở nhạc mẹ yêu", "cherry mở nhạc mẹ yêu",
                                     "mở bài hát mẹ yêu", "mở ca khúcDuyên phận"])
    def test_not_pc_open(self, msg):
        intent, _ = cc.route_message(msg, payload={"channel_id": "T", "message_id": "T"})
        assert intent != "pc_open", f"{msg!r} bị pc_open nuốt"


class TestPcOpenUntouched:
    """Lệnh mở app THẬT vẫn phải là pc_open (không nuốt nhầm)."""

    def test_open_chrome(self):
        intent, reply = cc.route_message("mở chrome", payload={"channel_id": "T", "message_id": "T"})
        assert intent == "pc_open"
        assert "chrome" in reply

    def test_open_excel(self):
        intent, reply = cc.route_message("bật excel", payload={"channel_id": "T", "message_id": "T"})
        assert intent == "pc_open"


class TestMusicStopPriority:
    """'tắt/dừng nhạc' → tony_music_stop, KHÔNG bị pc_close nuốt."""

    @pytest.mark.parametrize("msg", ["tắt nhạc", "dừng nhạc", "cherry dừng nhạc",
                                     "tony tắt nhạc", "stop nhạc"])
    def test_stop_not_pc_close(self, msg, monkeypatch):
        # Route 2.5 tra HANDLERS dict → patch dict entry (không gọi thật 8766).
        monkeypatch.setitem(cc.HANDLERS, "tony_music_stop", lambda payload=None: "MOCK_MUSIC_STOP")
        intent, reply = cc.route_message(msg, payload={"channel_id": "T", "message_id": "T"})
        assert intent == "tony_music_stop", f"{msg!r} → {intent} (sai, phải music_stop)"
        assert reply == "MOCK_MUSIC_STOP"


class TestFallbackPlayOnPc:
    """Pi5 lỗi → fallback loa PC (search YouTube + webbrowser.open)."""

    def test_fallback_success(self, monkeypatch):
        opened = {}
        monkeypatch.setattr("webbrowser.open", lambda url: opened.setdefault("url", url))
        monkeypatch.setattr(
            "quan_ai_brain.media.youtube_music.search_youtube_music",
            lambda q, max_results=1: [{"video_id": "abc", "title": "Mẹ Yếu",
                                       "url": "https://www.youtube.com/watch?v=abc"}],
        )
        msg = cc._fallback_play_on_pc("mẹ yêu")
        assert msg is not None and "loa PC" in msg and "Mẹ Yếu" in msg
        assert opened["url"] == "https://www.youtube.com/watch?v=abc"

    def test_fallback_no_results_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "quan_ai_brain.media.youtube_music.search_youtube_music",
            lambda q, max_results=1: [],
        )
        assert cc._fallback_play_on_pc("không có bài này xyz") is None

    def test_fallback_search_error_returns_none(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("network down")
        monkeypatch.setattr("quan_ai_brain.media.youtube_music.search_youtube_music", boom)
        assert cc._fallback_play_on_pc("mẹ yêu") is None  # fail-honest, không crash
