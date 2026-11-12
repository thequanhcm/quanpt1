"""Test greeting anti-spam guard trong netchat_auto_responder (12/11 audit).

Restart loop 14:01-14:23 gửi 10 greeting giống nhau → guard: chỉ gửi nếu
lần trước >60 phút. Test bằng cách đọc source (guard phải tồn tại) + mô phỏng
logic state file. KHÔNG gửi DM thật, KHÔNG khởi động responder thật.
"""
from __future__ import annotations

import importlib.util
import re
import time
from pathlib import Path

RESPONDER = Path(__file__).resolve().parent.parent / "tools" / "netchat_auto_responder.py"


def _src() -> str:
    return RESPONDER.read_text(encoding="utf-8")


def test_greeting_guard_exists_in_main():
    """main() phải có guard 60 phút trước khi gửi greeting."""
    src = _src()
    # Tìm đoạn trong main: guard state file + ngưỡng 3600s
    assert "greeting_last_sent.txt" in src, "thiếu state file greeting"
    assert "3600" in src, "thiếu ngưỡng 60 phút"
    assert "Skip greeting" in src, "thiếu nhánh skip"


def test_greeting_guard_before_send():
    """Guard phải nằm TRƯỚC lời gọi send_greeting_message trong main()."""
    src = _src()
    main_start = src.index("def main(")
    main_body = src[main_start:]
    guard_pos = main_body.index("greeting_last_sent.txt")
    send_pos = main_body.index("send_greeting_message()")
    assert guard_pos < send_pos, "guard phải chạy trước send"


def test_greeting_logic_simulation(tmp_path):
    """Mô phỏng state file: lần 1 gửi, lần 2 trong 60 phút skip."""
    state = tmp_path / "greeting_last_sent.txt"
    calls = []

    def maybe_greet(now: float) -> bool:
        last = 0.0
        if state.exists():
            last = float(state.read_text(encoding="utf-8").strip() or 0)
        if now - last > 3600:
            calls.append(now)
            state.write_text(str(now), encoding="utf-8")
            return True
        return False

    t0 = time.time()
    assert maybe_greet(t0) is True          # lần đầu: gửi
    assert maybe_greet(t0 + 60) is False    # 1 phút sau: skip
    assert maybe_greet(t0 + 3601) is True   # quá 60 phút: gửi lại
    assert len(calls) == 2
