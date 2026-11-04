"""sitecustomize — QUAN AI BRAIN: chặn nháy cửa sổ console cho mọi subprocess.

Vấn đề (03/11/2026 — yêu cầu Quanpt1): các daemon TONY 24/7 chạy bằng
pythonw.exe (không console). Mỗi lần daemon gọi lệnh console (ping, tasklist,
netstat, powershell, git, schtasks...) Windows cấp một console MỚI cho tiến
trình con -> cửa sổ đen nháy trên màn hình.

Giải pháp: monkeypatch subprocess.Popen (run/call/check_output/check_call đều
đi qua đây) thêm CREATE_NO_WINDOW (0x08000000) — tiến trình con không bao giờ
tạo cửa sổ. stdout/stderr capture hoạt động bình thường.

Kill-switch: đặt biến môi trường QAB_ALLOW_CONSOLE=1 để tắt patch (debug).
Phạm vi: chỉ áp dụng trong venv E:\\BRAIN\\.venv (file nằm trong site-packages
của venv đó) — không ảnh hưởng venv khác hay ứng dụng khác.

Cài đặt lại nếu tạo venv mới: python tools/install_nogui_sitecustomize.py
Source: tools/sitecustomize_nogui.py (được commit vào git).
"""
import os

if os.name == "nt" and not os.environ.get("QAB_ALLOW_CONSOLE"):
    import subprocess as _sp

    _CREATE_NO_WINDOW = 0x08000000
    _orig_popen = _sp.Popen

    # PHẢI là class, không được là function: asyncio.windows_utils (Python 3.11)
    # khai báo `class Popen(subprocess.Popen)` — nếu subprocess.Popen là function
    # thì import asyncio crash (TypeError: function() argument 'code' must be
    # code, not str). Subclass giữ nguyên khả năng kế thừa + isinstance.
    class _NoWindowPopen(_orig_popen):  # type: ignore[valid-type,misc]
        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    _sp.Popen = _NoWindowPopen
