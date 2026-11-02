"""SEC-S1 (c): Hành động khống chế tiến trình — TẠM GIỮ / THẢ / HẠ GỤC.

Mô hình quyền lực owner chọn (02/11/2026): "tạm thời nắm quyền kiểm soát, quản trị":
- Suspend (treo ngay, giữ dữ liệu) / Resume (thả) / Kill (hạ gục).
- PROTECTED_WHITELIST cứng: tiến trình hệ thống Windows + chính TONY/netMind —
  TỪ CHỐI fail-closed ngay cả khi owner ra lệnh nhầm (bảo vệ kép).
- Chỉ đụng tiến trình user-level được; SYSTEM/admin → lỗi trung thực "cần quyền admin".

Stdlib only (ctypes + tasklist). KHÔNG tự gọi — mọi action do lệnh owner DM hoặc
auto_contain của hợp đồng đã duyệt trigger.
"""
from __future__ import annotations

import ctypes
import subprocess
from typing import Any

# ---------------------------------------------------------------------------
# Whitelist cứng — KHÔNG BAO GIỜ đụng (fail-closed)
# ---------------------------------------------------------------------------
PROTECTED_SYSTEM_NAMES = {
    "system", "wininit", "csrss.exe", "smss.exe", "services.exe", "lsass.exe",
    "winlogon.exe", "svchost.exe", "dwm.exe", "explorer.exe", "fontdrvhost.exe",
    "conhost.exe", "registry",
}

# cmdline/đường dẫn chứa 1 trong các chuỗi sau = hệ thống TONY/netMind của mình
PROTECTED_CMDLINE_MARKERS = (
    "hermes", "netmind_desktop", "netmind-agent",
    "start_dual_servers", "netchat_auto_responder", "learning_daemon",
    "tools\\watchdog.py", "tools/watchdog.py", "watchdog.py",
    "quan_ai_brain", "e:\\brain",
)

PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_TERMINATE = 0x0001


def get_process_info(pid: int) -> dict[str, Any] | None:
    """Tên + cmdline của 1 PID qua PowerShell CIM (đúng chuẩn terminal tool).
    None = PID không tồn tại / đã chết."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}') | "
             "Select-Object Name, CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0 or not r.stdout.strip() or r.stdout.strip() == "null":
            return None
        import json

        data = json.loads(r.stdout)
        if isinstance(data, list):  # phòng khi trả mảng
            data = data[0] if data else None
        if not data:
            return None
        return {
            "pid": int(pid),
            "name": (data.get("Name") or "").strip(),
            "cmdline": (data.get("CommandLine") or "").strip(),
        }
    except Exception:
        return None


def protected_reason(pid: int) -> str | None:
    """Trả lý do BẢO VỆ nếu PID thuộc whitelist; None = được phép khống chế."""
    info = get_process_info(pid)
    if info is None:
        return "PID không tồn tại (đã chết hoặc sai)"
    name = info["name"].lower()
    cmdline = (info["cmdline"] or "").lower()
    if name in PROTECTED_SYSTEM_NAMES:
        return f"tiến trình hệ thống ({info['name']}) — TỪ CHỐI theo whitelist cứng"
    for marker in PROTECTED_CMDLINE_MARKERS:
        if marker in cmdline:
            return f"thành phần TONY/netMind ('{marker}') — TỪ CHỐI theo whitelist cứng"
    return None


def _open_process(pid: int, access: int):
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = k32.OpenProcess(access, False, int(pid))
    return k32, handle


def suspend_process(pid: int) -> dict[str, Any]:
    """TẠM GIỮ: treo tiến trình, giữ nguyên bộ nhớ (an toàn hơn kill — thả được)."""
    reason = protected_reason(pid)
    if reason:
        return {"success": False, "action": "suspend", "pid": pid, "reason": reason}

    k32, handle = _open_process(pid, PROCESS_SUSPEND_RESUME)
    if not handle:
        err = ctypes.get_last_error()
        return {"success": False, "action": "suspend", "pid": pid,
                "reason": f"không mở được tiến trình (access={err}) — có thể cần quyền admin"}
    try:
        ntdll = ctypes.WinDLL("ntdll")
        status = ntdll.NtSuspendProcess(ctypes.c_void_p(handle))
        if status != 0:
            return {"success": False, "action": "suspend", "pid": pid,
                    "reason": f"NtSuspendProcess status=0x{status:08x}"}
        return {"success": True, "action": "suspend", "pid": pid,
                "reason": "đã TẠM GIỮ (treo) — tiến trình đứng yên, anh nhắn 'thả <pid>' để cho chạy lại"}
    finally:
        k32.CloseHandle(handle)


def resume_process(pid: int) -> dict[str, Any]:
    """THẢ: cho tiến trình đang bị treo chạy lại bình thường."""
    reason = protected_reason(pid)
    if reason:
        return {"success": False, "action": "resume", "pid": pid, "reason": reason}

    k32, handle = _open_process(pid, PROCESS_SUSPEND_RESUME)
    if not handle:
        err = ctypes.get_last_error()
        return {"success": False, "action": "resume", "pid": pid,
                "reason": f"không mở được tiến trình (access={err})"}
    try:
        ntdll = ctypes.WinDLL("ntdll")
        status = ntdll.NtResumeProcess(ctypes.c_void_p(handle))
        if status != 0:
            return {"success": False, "action": "resume", "pid": pid,
                    "reason": f"NtResumeProcess status=0x{status:08x}"}
        return {"success": True, "action": "resume", "pid": pid,
                "reason": "đã THẢ — tiến trình chạy lại bình thường"}
    finally:
        k32.CloseHandle(handle)


def kill_process(pid: int) -> dict[str, Any]:
    """HẠ GỤC: kết thúc vĩnh viễn (chỉ khi owner ra lệnh 'hạ')."""
    reason = protected_reason(pid)
    if reason:
        return {"success": False, "action": "kill", "pid": pid, "reason": reason}

    info = get_process_info(pid)
    name = info["name"] if info else "?"
    r = subprocess.run(
        ["taskkill", "/F", "/PID", str(pid)],
        capture_output=True, text=True, timeout=15,
    )
    ok = r.returncode == 0
    return {
        "success": ok, "action": "kill", "pid": pid, "name": name,
        "reason": ("đã HẠ GỤC vĩnh viễn" if ok else
                   (r.stderr or r.stdout or "taskkill thất bại").strip()[:200]),
    }
