"""Tests avatar expression sync — biểu cảm Pi 5 đồng bộ theo pha hội thoại.

Owner requirement 27/10: "thay đổi trạng thái biểu cảm khi anh chat, hỏi đáp...
đồng bộ cùng hiển thị trên giao diện Pi5".

Quy tắc test repo: KHÔNG gọi mạng thật — _send_edge_request được mock; Pi 5 thật
không bao giờ bị chạm trong test.
"""

from __future__ import annotations

from unittest.mock import patch

from quan_ai_brain.web.server import (
    push_avatar_expression,
    push_avatar_speech,
    push_avatar_thinking,
)


class TestPushAvatarExpression:
    def test_sends_set_expression_action(self):
        captured = {}

        def fake_edge(path, method="GET", data=None, timeout=3.0):
            captured["path"] = path
            captured["method"] = method
            captured["data"] = data
            return {"success": True}

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=fake_edge):
            ok = push_avatar_expression("THINKING", transcript="Đang suy nghĩ...")

        assert ok is True
        assert captured["path"] == "/api/kiosk/control"
        assert captured["method"] == "POST"
        assert captured["data"]["action"] == "set_expression"
        assert captured["data"]["state"] == "THINKING"
        assert captured["data"]["transcript"] == "Đang suy nghĩ..."

    def test_transcript_truncated_to_300_chars(self):
        captured = {}

        def fake_edge(path, method="GET", data=None, timeout=3.0):
            captured["data"] = data
            return {"success": True}

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=fake_edge):
            push_avatar_expression("SPEAKING", transcript="x" * 1000)

        assert len(captured["data"]["transcript"]) == 300

    def test_edge_offline_returns_false_not_raise(self):
        def offline(path, method="GET", data=None, timeout=3.0):
            return {"success": False, "offline": True}

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=offline):
            assert push_avatar_expression("IDLE") is False

    def test_network_exception_returns_false_not_raise(self):
        def boom(path, method="GET", data=None, timeout=3.0):
            raise OSError("network down")

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=boom):
            assert push_avatar_expression("IDLE") is False


class TestPushAvatarSpeech:
    def test_sends_speak_action_with_duration(self):
        captured = {}

        def fake_edge(path, method="GET", data=None, timeout=3.0):
            captured["data"] = data
            return {"success": True}

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=fake_edge):
            ok = push_avatar_speech("Xin chào anh Quân", duration_ms=4000)

        assert ok is True
        assert captured["data"]["action"] == "speak"
        assert captured["data"]["state"] == "SPEAKING"
        assert captured["data"]["text"] == "Xin chào anh Quân"
        assert captured["data"]["duration_ms"] == 4000

    def test_text_truncated_to_600_chars(self):
        captured = {}

        def fake_edge(path, method="GET", data=None, timeout=3.0):
            captured["data"] = data
            return {"success": True}

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=fake_edge):
            push_avatar_speech("y" * 2000, duration_ms=3000)

        assert len(captured["data"]["text"]) == 600

    def test_failure_returns_false(self):
        def boom(path, method="GET", data=None, timeout=3.0):
            raise OSError("down")

        with patch("quan_ai_brain.web.server._send_edge_request", side_effect=boom):
            assert push_avatar_speech("test") is False


class TestPushAvatarThinking:
    def test_sets_global_telemetry_and_pushes(self):
        import quan_ai_brain.web.server as ws

        pushed = []

        def fake_edge(path, method="GET", data=None, timeout=3.0):
            pushed.append((data.get("state"), data.get("transcript")))
            return {"success": True}

        old = dict(ws._GLOBAL_EDGE_TELEMETRY)
        try:
            with patch.object(ws, "_send_edge_request", side_effect=fake_edge):
                push_avatar_thinking()
            assert ws._GLOBAL_EDGE_TELEMETRY["target_avatar_state"] == "THINKING"
            assert pushed and pushed[0][0] == "THINKING"
        finally:
            ws._GLOBAL_EDGE_TELEMETRY.clear()
            ws._GLOBAL_EDGE_TELEMETRY.update(old)


class TestTelemetrySync:
    def test_expression_updates_telemetry_transcript(self):
        """Heartbeat pull: telemetry transcript phải cập nhật cùng push (tránh heartbeat đè giá trị cũ)."""
        import quan_ai_brain.web.server as ws

        old = dict(ws._GLOBAL_EDGE_TELEMETRY)
        try:
            with patch.object(ws, "_send_edge_request", return_value={"success": True}):
                push_avatar_expression("RESEARCHING", transcript="Đang tra cứu thông tin ngoài...")
            assert ws._GLOBAL_EDGE_TELEMETRY["target_avatar_state"] == "RESEARCHING"
            assert ws._GLOBAL_EDGE_TELEMETRY["transcript"] == "Đang tra cứu thông tin ngoài..."
        finally:
            ws._GLOBAL_EDGE_TELEMETRY.clear()
            ws._GLOBAL_EDGE_TELEMETRY.update(old)

    def test_speech_updates_telemetry_and_resets_to_idle(self):
        import time

        import quan_ai_brain.web.server as ws

        old = dict(ws._GLOBAL_EDGE_TELEMETRY)
        try:
            with patch.object(ws, "_send_edge_request", return_value={"success": True}):
                push_avatar_speech("Trả lời thử nghiệm", duration_ms=1200)
            assert ws._GLOBAL_EDGE_TELEMETRY["target_avatar_state"] == "SPEAKING"
            assert ws._GLOBAL_EDGE_TELEMETRY["transcript"] == "Trả lời thử nghiệm"
            time.sleep(1.6)
            assert ws._GLOBAL_EDGE_TELEMETRY["target_avatar_state"] == "IDLE"
        finally:
            ws._GLOBAL_EDGE_TELEMETRY.clear()
            ws._GLOBAL_EDGE_TELEMETRY.update(old)


class TestStatesMatchKioskConfig:
    def test_used_states_exist_in_kiosk_state_config(self):
        """Trạng thái đẩy xuống phải tồn tại trong STATE_CONFIG của kiosk.js trên Pi 5.

        Đọc kiosk.js từ edge_client.tar.gz (bản client thực chạy trên Pi) — nếu
        thêm state mới phía PC mà kiosk không có, setAvatarState sẽ rơi về IDLE
        (im lặng mất biểu cảm) — test này chặn lỗi đó.
        """
        import io
        import re
        import tarfile
        from pathlib import Path

        tar_path = Path(__file__).resolve().parent.parent / (
            "src/quan_ai_brain/web/static/edge_client.tar.gz"
        )
        if not tar_path.exists():
            return  # môi trường không có client bundle — bỏ qua
        with tarfile.open(tar_path, "r:gz") as tf:
            kiosk_js = tf.extractfile("kiosk.js")
            if kiosk_js is None:
                return
            content = kiosk_js.read().decode("utf-8", errors="replace")
        match = re.search(r"const STATE_CONFIG = \{(.*?)\};", content, re.S)
        assert match, "STATE_CONFIG not found in kiosk.js"
        kiosk_states = set(re.findall(r"(\w+):\s*\{\s*css:", match.group(1)))

        for state in ["IDLE", "THINKING", "RESEARCHING", "SPEAKING", "BLOCKED",
                      "LISTENING", "LEARNING", "WAITING_FOR_OWNER"]:
            assert state in kiosk_states, (
                f"State '{state}' đẩy từ PC nhưng kiosk.js không có trong STATE_CONFIG"
            )
