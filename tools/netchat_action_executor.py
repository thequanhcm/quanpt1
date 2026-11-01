"""Bounded PC Action Executor for TONY via NetChat DM (31/10/2026).

Owner (quanpt1) yêu cầu: "thiết lập để khi anh sử dụng lệnh là TONY có thể
hành động, tác động, điều khiển, nhận lệnh và thực thi" — sau sự cố TONY trả
lời "em chưa có công cụ điều khiển máy tính" khi được yêu cầu mở UltraViewer.

THIẾT KẾ AN TOÀN (biên cứng, không vượt quá):
1. CHỈ MỞ/ĐÓNG ứng dụng trong ALLOWLIST dưới đây — KHÔNG BAO GIỜ thực thi
   lệnh shell tùy ý, không nhận chuỗi lệnh tự do từ DM.
2. KHÔNG nâng quyền admin, KHÔNG xóa file, KHÔNG đọc/ghi credentials,
   KHÔNG đụng vào hệ điều hành ngoài: launch app / kill app theo tên /
   khóa màn hình (reversible) / mở URL nội bộ / mở thư mục.
3. Mọi hành động THÀNH CÔNG hay THẤT BẠI đều ghi audit log.
4. Lỗi = báo thật (fail-honest), không bao giờ giả "đã làm".
5. Đóng app dùng taskkill /IM <exe> /F — CHỈ với exe của app trong allowlist.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
_SRC = WORKSPACE / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _audit(event_type: str, details: dict[str, Any]) -> None:
    try:
        from quan_ai_brain.core.audit import AuditLogger

        AuditLogger(WORKSPACE).record(event_type, details)
    except Exception:
        pass  # audit failure không được giết hành động chính


# ---------------------------------------------------------------------------
# ALLOWLIST — nguồn duy nhất của các hành động được phép
# kind: "exe"     → tên file trong PATH hệ thống
#       "path"    → đường dẫn cài đặt thường gặp (hỗ trợ %LOCALAPPDATA%...)
#       "appaths" → registry App Paths (HKLM/HKCU\...\App Paths\<exe>)
#       "url"     → mở bằng trình duyệt mặc định
#       "folder"  → mở bằng Windows Explorer
# ---------------------------------------------------------------------------
APP_ALLOWLIST: dict[str, list[tuple[str, str]]] = {
    "ultraviewer": [
        ("path", r"C:\Program Files (x86)\UltraViewer\UltraViewer_Desktop.exe"),
        ("path", r"C:\Program Files (x86)\UltraViewer\UltraViewer.exe"),
        ("path", r"C:\Program Files\UltraViewer\UltraViewer.exe"),
        ("appaths", "UltraViewer.exe"),
        ("path", r"%LOCALAPPDATA%\UltraViewer\UltraViewer.exe"),
    ],
    "notepad": [("exe", "notepad.exe")],
    "calc": [("exe", "calc.exe")],
    "paint": [("exe", "mspaint.exe")],
    "explorer": [("exe", "explorer.exe")],
    "taskmgr": [("exe", "taskmgr.exe")],
    "cmd": [("exe", "cmd.exe")],
    "powershell": [("exe", "powershell.exe")],
    "chrome": [
        ("appaths", "chrome.exe"),
        ("path", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ("path", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ("path", r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ],
    "firefox": [
        ("appaths", "firefox.exe"),
        ("path", r"C:\Program Files\Mozilla Firefox\firefox.exe"),
        ("path", r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"),
        ("path", r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"),
    ],
    "edge": [
        ("appaths", "msedge.exe"),
        ("path", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ],
    "cococ": [
        ("appaths", "CocCoc.exe"),
        ("path", r"%LOCALAPPDATA%\CocCoc\Application\browser.exe"),
    ],
    "vscode": [("appaths", "Code.exe"), ("where", "code")],
    "word": [("appaths", "Winword.exe")],
    "excel": [("appaths", "Excel.exe")],
    "powerpoint": [("appaths", "POWERPNT.EXE")],
    "outlook": [("appaths", "Outlook.exe")],
    "zalo": [("path", r"%LOCALAPPDATA%\Zalo\Zalo.exe"), ("appaths", "Zalo.exe")],
    "dashboard": [("url", "http://127.0.0.1:8766/")],
    "chatui": [("url", "http://127.0.0.1:8765/")],
    "thumucduan": [("folder", str(WORKSPACE))],
}

# Nhận diện từ tự nhiên → app key (không phân biệt hoa thường, tìm bằng 'in')
APP_ALIASES: dict[str, tuple[str, ...]] = {
    "ultraviewer": ("ultraviewer", "ultraview", "ultra view", "ultra viewer", "ultraviewer"),
    "notepad": ("notepad", "notepad++", "sổ tay"),
    "calc": ("calculator", "calc", "máy tính bỏ túi"),
    "paint": ("paint", "mspaint", "vẽ"),
    "explorer": ("explorer", "quản lý tệp", "file explorer"),
    "taskmgr": ("task manager", "taskmanager", "taskmgr", "trình quản lý tác vụ"),
    "cmd": ("cmd", "command prompt"),
    "powershell": ("powershell",),
    "chrome": ("chrome", "google chrome"),
    "firefox": ("firefox", "mozilla firefox", "mozila"),
    "edge": ("edge", "microsoft edge"),
    "cococ": ("cốc cốc", "coc coc", "coccoc"),
    "vscode": ("vscode", "visual studio code", "vs code"),
    "word": ("word", "microsoft word"),
    "excel": ("excel", "microsoft excel"),
    "powerpoint": ("powerpoint", "power point"),
    "outlook": ("outlook",),
    "zalo": ("zalo",),
    "dashboard": ("dashboard", "cockpit", "phòng điều hành"),
    "chatui": ("chat ui", "giao diện chat"),
    "thumucduan": ("thư mục dự án", "thu muc du an", "thư mục brain", "thu muc brain"),
}

_APP_LABELS = {
    "ultraviewer": "UltraViewer", "notepad": "Notepad", "calc": "Calculator",
    "paint": "Paint", "explorer": "File Explorer", "taskmgr": "Task Manager",
    "cmd": "CMD", "powershell": "PowerShell", "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "edge": "Microsoft Edge", "cococ": "Cốc Cốc", "vscode": "VS Code",
    "word": "Microsoft Word", "excel": "Microsoft Excel",
    "powerpoint": "PowerPoint", "outlook": "Outlook", "zalo": "Zalo",
    "dashboard": "Dashboard điều hành (8766)", "chatui": "Chat UI (8765)",
    "thumucduan": "Thư mục dự án BRAIN",
}


def find_app_in_text(text: str) -> str | None:
    """Tìm app key trong câu lệnh tự do (không phân biệt hoa/thường)."""
    t = (text or "").lower()
    # Ưu tiên alias dài nhất để 'google chrome' không dính 'chrome' sai ngữ cảnh (đangs same key)
    for key, aliases in APP_ALIASES.items():
        for alias in aliases:
            if alias in t:
                return key
    return None


def app_label(app_key: str) -> str:
    return _APP_LABELS.get(app_key, app_key)


def _resolve_apppaths(exe_name: str) -> str | None:
    """Đọc registry App Paths (HKLM + HKCU) → đường dẫn exe."""
    try:
        import winreg

        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
                with winreg.OpenKey(root, key_path) as k:
                    val, _t = winreg.QueryValueEx(k, None)
                    val = os.path.expandvars(str(val).strip().strip('"'))
                    if val and os.path.isfile(val):
                        return val
                    # đôi khi default chỉ là tên exe → thử where
                    if val:
                        w = shutil.which(Path(val).name)
                        if w:
                            return w
            except OSError:
                continue
    except Exception:
        pass
    return None


def resolve_app(app_key: str) -> str | None:
    """Trả về đường dẫn thực thi / URL / folder của app, hoặc None nếu không thấy."""
    entries = APP_ALLOWLIST.get(app_key)
    if not entries:
        return None
    for kind, value in entries:
        try:
            if kind == "exe":
                w = shutil.which(value)
                if w:
                    return w
            elif kind == "path":
                p = os.path.expandvars(value)
                if os.path.isfile(p):
                    return p
            elif kind == "where":
                w = shutil.which(value)
                if w:
                    return w
            elif kind == "appaths":
                p = _resolve_apppaths(value)
                if p:
                    return p
            elif kind in ("url", "folder"):
                return value
        except Exception:
            continue
    return None


def open_app(app_key: str) -> tuple[bool, str]:
    """Mở ứng dụng trong allowlist. Trả (success, message)."""
    target = resolve_app(app_key)
    label = app_label(app_key)
    if target is None:
        _audit("pc_action.open_not_found", {"app": app_key})
        return False, f"Không tìm thấy {label} trên máy này (chưa cài hoặc path khác thường)."

    try:
        entries = APP_ALLOWLIST.get(app_key, [])
        kind = next((k for k, v in entries if resolve_app(app_key) == (v if k in ("url", "folder") else os.path.expandvars(v)) or resolve_app(app_key) == v), None)
        if app_key in ("dashboard", "chatui"):
            os.startfile(target)  # URL → trình duyệt mặc định
        elif app_key == "thumucduan":
            os.startfile(target)  # folder → explorer
        else:
            # GUI app: Popen detached — không chờ, không console
            subprocess.Popen(
                [target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
                close_fds=True,
            )
        _audit("pc_action.open", {"app": app_key, "target": target})
        return True, f"Đã mở {label}."
    except Exception as exc:
        _audit("pc_action.open_error", {"app": app_key, "error": str(exc)[:200]})
        return False, f"{type(exc).__name__}: {exc}"


def close_app(app_key: str) -> tuple[bool, str]:
    """Đóng (taskkill /F) exe của app trong allowlist. Trả (success, message)."""
    if app_key in ("dashboard", "chatui", "thumucduan"):
        return False, "Đây là URL/thư mục — không có tiến trình để đóng."
    target = resolve_app(app_key)
    if target is None:
        _audit("pc_action.close_not_found", {"app": app_key})
        return False, f"Không tìm thấy {app_label(app_key)} đang cài trên máy."
    exe_name = Path(target).name
    try:
        r = subprocess.run(
            ["taskkill", "/IM", exe_name, "/F"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        ok = r.returncode == 0
        detail = (r.stdout or r.stderr or "").strip()[:150]
        _audit("pc_action.close", {"app": app_key, "exe": exe_name, "success": ok})
        if ok:
            return True, f"Đã đóng {app_label(app_key)} ({exe_name})."
        # 128 = không tìm thấy process → app không chạy
        if "not found" in detail.lower() or "không" in detail.lower() or r.returncode == 128:
            return False, f"{app_label(app_key)} đang không chạy."
        return False, f"taskkill: {detail}"
    except Exception as exc:
        _audit("pc_action.close_error", {"app": app_key, "error": str(exc)[:200]})
        return False, f"{type(exc).__name__}: {exc}"


def lock_pc() -> tuple[bool, str]:
    """Khóa màn hình Windows (an toàn — anh tự mở lại bằng mật khẩu)."""
    try:
        subprocess.Popen(
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _audit("pc_action.lock", {})
        return True, "Đã khóa màn hình máy tính."
    except Exception as exc:
        _audit("pc_action.lock_error", {"error": str(exc)[:200]})
        return False, f"{type(exc).__name__}: {exc}"


def list_capabilities() -> str:
    """Danh sách app trong allowlist (dùng cho help/lỗi)."""
    return ", ".join(app_label(k) for k in sorted(APP_ALLOWLIST))


# ---------------------------------------------------------------------------
# (31/10/2026) CHỤP MÀN HÌNH + GỬI ẢNH VÀO DM NETCHAT
# Owner lệnh: "chụp lại ảnh màn hình máy tính hiện tại và gửi cho anh"
# ---------------------------------------------------------------------------

_SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "logs", "screenshots")


def capture_screenshot() -> tuple[bool, str]:
    """Chụp toàn màn hình → lưu PNG vào logs/screenshots/. Trả (ok, đường_dẫn|lỗi)."""
    try:
        os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
        from PIL import ImageGrab
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(_SCREENSHOT_DIR, f"tony_screen_{ts}.png")
        img = ImageGrab.grab()
        img.save(path)
        size_kb = os.path.getsize(path) / 1024
        _audit("pc_action.screenshot", {"path": path, "size_kb": round(size_kb)})
        return True, path
    except Exception as exc:
        _audit("pc_action.screenshot_error", {"error": str(exc)[:200]})
        return False, f"{type(exc).__name__}: {exc}"


def send_file_to_dm(file_path: str, caption: str = "") -> tuple[bool, str]:
    """Upload file (ảnh chụp màn hình...) vào DM bot↔quanpt1 qua netchat_bot.py
    upload_dm + cổng xác nhận 2 bước tự động. Trả (ok, thông_báo)."""
    try:
        python_exe = (r"C:\Users\quocd\AppData\Local\netmind_desktop"
                      r"\netmind-agent\venv\Scripts\python.exe")
        bot_script = (r"C:\Users\quocd\AppData\Local\netmind_desktop"
                      r"\skills\bot-netchat\netchat_bot.py")
        cmd = [python_exe, bot_script, "upload_dm", "quanpt1", file_path, caption]
        r1 = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                            encoding="utf-8", errors="replace")
        out1 = (r1.stdout or "") + (r1.stderr or "")
        m = re.search(r"CONFIRM-REQUIRED:\s*([a-f0-9]+)", out1)
        if not m:
            return False, f"upload step1: {out1[:200]}"
        cmd.append("--confirmed")
        cmd.append(m.group(1))
        r2 = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                            encoding="utf-8", errors="replace")
        out2 = (r2.stdout or "") + (r2.stderr or "")
        if r2.returncode == 0 and '"post_id"' in out2:
            fm = re.search(r'"post_id":\s*"([^"]+)"', out2)
            _audit("pc_action.send_file", {"file": os.path.basename(file_path),
                                           "post_id": fm.group(1) if fm else "?"})
            return True, "Đã gửi file vào DM."
        return False, f"upload step2: {out2[:200]}"
    except Exception as exc:
        _audit("pc_action.send_file_error", {"error": str(exc)[:200]})
        return False, f"{type(exc).__name__}: {exc}"


def screenshot_to_dm() -> tuple[bool, str]:
    """Chuỗi hoàn chỉnh: chụp màn hình → gửi ảnh vào DM. Trả (ok, thông_báo)."""
    ok, path_or_err = capture_screenshot()
    if not ok:
        return False, f"❌ Không chụp được màn hình: {path_or_err}"
    ts = time.strftime("%H:%M:%S %d/%m/%Y")
    caption = (f"📸 Ảnh màn hình máy tính của anh lúc {ts} "
               f"(TONY chụp theo lệnh DM)")
    ok2, msg2 = send_file_to_dm(path_or_err, caption)
    if not ok2:
        return False, (f"✅ Đã chụp ({os.path.basename(path_or_err)}) nhưng "
                       f"gửi DM lỗi: {msg2}")
    return True, (f"📸 Đã chụp màn hình ({os.path.basename(path_or_err)}) và "
                  f"gửi vào DM cho anh rồi nhé!")
