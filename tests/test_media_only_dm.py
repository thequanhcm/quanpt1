"""Test 'CHỈ GỬI HÌNH' — lệnh media (chụp ảnh/quay video/thu âm/chụp màn hình)
không được kèm tin text xác nhận nữa (owner 06/11/2026 20:54: 'bỏ tin nhắn nội dung').

Contract:
- Thành công + gửi DM OK → handler trả '' (responder im lặng — chỉ có tin ảnh).
- Gửi DM lỗi → text cảnh báo (fail-honest, không mất ảnh âm thầm).
- Không có file PC → text cảnh báo (fail-honest).
Chỉ mock capture + send_file_to_dm — không gọi DM thật, không đụng Pi5.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BRAIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRAIN_ROOT))

from tools import netchat_command_center as cc  # noqa: E402
from tools import netchat_action_executor as exec_mod  # noqa: E402


class _FakeCapture:
    """Giả _pi_media_capture: trả dữ liệu như capture thật."""

    def __init__(self, fname="photo_20261106_205438.jpg", pc_path=r"C:\tmp\photo.jpg",
                 size_bytes=140288, has_audio=False):
        self.fname = fname
        self.pc_path = pc_path
        self.size_bytes = size_bytes
        self.has_audio = has_audio

    def __call__(self, kind, duration=None, mic_kind=None):
        return True, {
            "filename": self.fname,
            "pc_path": self.pc_path,
            "size_bytes": self.size_bytes,
            "has_audio": self.has_audio,
        }


@pytest.fixture()
def patched(monkeypatch, tmp_path):
    """Patch capture + send_file_to_dm; trả (capture, dm_calls) để assert."""
    fake = _FakeCapture(pc_path=str(tmp_path / "photo.jpg"))
    dm_calls: list[tuple[str, str]] = []

    def fake_send(path, caption):
        dm_calls.append((str(path), caption))
        return True, "ok"

    monkeypatch.setattr(cc, "_pi_media_capture", fake)
    monkeypatch.setattr(exec_mod, "send_file_to_dm", fake_send)
    return fake, dm_calls


def test_photo_success_returns_empty_text_only_image(patched):
    fake, dm_calls = patched
    out = cc.handle_tony_pi_photo("chụp hình")
    assert out == ""  # không tin text — chỉ tin ảnh
    assert len(dm_calls) == 1
    path, caption = dm_calls[0]
    assert path == fake.pc_path
    # metadata gộp vào caption — không mất thông tin tên file + dung lượng
    assert fake.fname in caption
    assert "KB" in caption


def test_photo_dm_fail_reports_honestly(monkeypatch, tmp_path):
    fake = _FakeCapture(pc_path=str(tmp_path / "photo.jpg"))
    monkeypatch.setattr(cc, "_pi_media_capture", fake)

    def fail_send(path, caption):
        return False, "HTTP 500"

    monkeypatch.setattr(exec_mod, "send_file_to_dm", fail_send)
    out = cc.handle_tony_pi_photo("chụp hình")
    assert "⚠️" in out and "lỗi" in out.lower()  # fail-honest
    assert fake.fname in out


def test_video_success_returns_empty_text_only_image(patched):
    _, dm_calls = patched
    out = cc.handle_tony_pi_video("quay video từ pi 5 giây")
    assert out == ""
    assert len(dm_calls) == 1
    _, caption = dm_calls[0]
    assert "Video" in caption and "KB" in caption


def test_listen_success_returns_empty_text_only_file(patched):
    _, dm_calls = patched
    out = cc.handle_tony_pi_listen("nghe từ pi 5 giây")
    assert out == ""
    assert len(dm_calls) == 1
    _, caption = dm_calls[0]
    assert "Thu âm" in caption and "KB" in caption


def test_photo_no_pc_path_reports_honestly(monkeypatch):
    fake = _FakeCapture(pc_path="(không tải về PC)")
    monkeypatch.setattr(cc, "_pi_media_capture", fake)

    def must_not_send(path, caption):  # pragma: no cover
        raise AssertionError("không được gửi DM khi không có file PC")

    monkeypatch.setattr(exec_mod, "send_file_to_dm", must_not_send)
    out = cc.handle_tony_pi_photo("chụp hình")
    assert "Pi 5" in out  # báo nơi lưu thật, fail-honest
