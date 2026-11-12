"""(12/11/2026) Test tối ưu camera Pi5 — lock + cache + MJPEG privacy + timeout.

100% mock: không gọi rpicam thật, không đụng camera/network thật.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))
sys.path.insert(0, str(WS / "edge_client"))

import client_daemon as cd

# Chống đụng camera/hardware thật trong test env Windows
cd.sys.platform = "win32"


def _fresh_cache() -> None:
    cd.CAMERA_FRAME_CACHE["data"] = None
    cd.CAMERA_FRAME_CACHE["epoch"] = 0.0


def _make_handler() -> cd.KioskHTTPHandler:
    """Handler không qua HTTP thật — chỉ để gọi method nội bộ."""
    h = object.__new__(cd.KioskHTTPHandler)
    h.daemon_state = object.__new__(cd.EdgeDaemonState)
    h.daemon_state.lock = threading.RLock()
    h.daemon_state.camera_enabled = True
    h.daemon_state.camera_streaming = True
    return h


def test_frame_cache_reuses_within_ttl(monkeypatch) -> None:
    """Khung còn tươi (<0.6s) được tái dùng — không chụp lại (tiết kiệm CSI bus)."""
    _fresh_cache()
    h = _make_handler()
    calls = {"n": 0}

    def fake_exec(cmd, timeout=5.0):
        calls["n"] += 1
        return True

    monkeypatch.setattr(type(h), "_exec_system_cmd", staticmethod(fake_exec))
    monkeypatch.setattr(cd, "STATIC_DIR", Path(__file__).parent / "_khong_ton_tai_xyz")

    frame = b"fake-jpeg-data-12345678901234567890"
    cd.CAMERA_FRAME_CACHE["data"] = frame
    cd.CAMERA_FRAME_CACHE["epoch"] = time.time()

    out = h._capture_camera_frame()
    assert out == frame, "phải trả cache còn tươi"
    assert calls["n"] == 0, "không được chụp lại khi cache còn TTL"


def test_capture_lock_serializes_parallel_captures(monkeypatch, tmp_path) -> None:
    """2 thread chụp song song: lock serialize — không crash, có cache cuối."""
    _fresh_cache()
    h = _make_handler()
    exec_times: list[tuple[float, float]] = []

    def fake_exec(cmd, timeout=5.0):
        t0 = time.time()
        exec_times.append((t0, t0 + 0.15))
        time.sleep(0.15)
        # fake "chụp xong" → ghi file snapshot để hàm đọc
        snap = tmp_path / "assets" / "avatar" / "camera_snapshot.jpg"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_bytes(b"x" * 500)
        return True

    monkeypatch.setattr(type(h), "_exec_system_cmd", staticmethod(fake_exec))
    monkeypatch.setattr(cd, "STATIC_DIR", tmp_path)

    results: list = []

    def worker():
        results.append(h._capture_camera_frame())

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start(); t2.start(); t1.join(); t2.join()

    assert len(results) == 2
    # Lock serialize: 2 lần exec không chồng lấn thời gian
    if len(exec_times) == 2:
        no_overlap = exec_times[0][1] <= exec_times[1][0] + 0.01 or exec_times[1][1] <= exec_times[0][0] + 0.01
        assert no_overlap, "2 lần chụp phải tuần tự (lock), không chồng lấn"


def test_mjpeg_privacy_stop_live_rejects() -> None:
    """stop_live (camera_streaming=False) → MJPEG từ chối mở stream (403), không chụp."""
    h = _make_handler()
    h.daemon_state.camera_streaming = False  # đã DỪNG XEM

    sent: dict = {}
    h._send_error_json = lambda msg, status=400: sent.update({"msg": msg, "status": status})

    h._handle_api_kiosk_camera_mjpeg()
    assert sent["status"] == 403
    assert "stopped" in sent["msg"].lower()


def test_mjpeg_runs_when_streaming(monkeypatch, tmp_path) -> None:
    """camera_streaming=True → MJPEG mở stream, ghi >=1 frame rồi client ngắt."""
    _fresh_cache()
    h = _make_handler()
    h.daemon_state.camera_streaming = True

    snap = tmp_path / "assets" / "avatar" / "camera_snapshot.jpg"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(b"y" * 500)

    monkeypatch.setattr(type(h), "_exec_system_cmd", staticmethod(lambda cmd, timeout=5.0: True))
    monkeypatch.setattr(cd, "STATIC_DIR", tmp_path)

    written: list[bytes] = []

    class FakeWFile:
        def write(self, data):
            written.append(data)
            # frame đầu xong → mô phỏng client ngắt để thoát vòng lặp
            raise BrokenPipeError()

        def flush(self):
            pass

    h.wfile = FakeWFile()
    h.send_response = lambda *a, **k: None
    h.send_header = lambda *a, **k: None
    h.end_headers = lambda: None

    h._handle_api_kiosk_camera_mjpeg()
    assert written, "phải ghi được ít nhất 1 multipart frame"
    assert b"--camframe" in written[0]


def test_exec_system_cmd_custom_timeout() -> None:
    """_exec_system_cmd nhận timeout riêng (8s cho rpicam cold-start)."""
    h = _make_handler()
    import subprocess as _sp

    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return _sp.CompletedProcess(cmd, 0)

    real_run = cd.subprocess.run
    cd.subprocess.run = fake_run
    try:
        h._exec_system_cmd(["true"], timeout=8.0)
        assert captured["timeout"] == 8.0
        # mặc định vẫn 5s khi không truyền
        h._exec_system_cmd(["true"])
        assert captured["timeout"] == 5.0
    finally:
        cd.subprocess.run = real_run


def test_constants_sane() -> None:
    """Hằng số tối ưu hợp lý."""
    assert 0.3 <= cd.CAMERA_FRAME_TTL_SEC <= 1.0, "TTL ~0.6s — đủ tươi, không quá dày"
    assert cd.CAMERA_CAPTURE_TIMEOUT_SEC >= 6.0, "rpicam cold-start cần >6s"
    assert hasattr(cd, "CAMERA_CAPTURE_LOCK")
