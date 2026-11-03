"""V4.0 (03/11/2026): cập nhật task LOGON qua COM — trỏ sang .vbs ẩn.

Task QUAN_AI_BRAIN_KHOI_DONG_LOGON được tạo bằng COM (schtasks ONLOGON
cần admin). Cập nhật action: KHOI_DONG_24_7.bat → wscript.exe .vbs
(WshShell.Run ..., 0, False) — hết cửa sổ cmd hiện 35s mỗi lần đăng nhập.
"""
from __future__ import annotations

import sys

TASK_NAME = "QUAN_AI_BRAIN_KHOI_DONG_LOGON"
VBS = r"E:\BRAIN\tools\khoi_dong_24_7_hidden.vbs"


def main() -> int:
    try:
        import win32com.client  # type: ignore
    except ImportError:
        print("pywin32 chưa có — thử lại bằng pythonw venv")
        return 1
    sched = win32com.client.Dispatch("Schedule.Service")
    sched.Connect()
    root = sched.GetFolder("\\")
    task = root.GetTask(TASK_NAME)
    td = task.Definition

    # Thay action đầu tiên: wscript.exe "<vbs>"
    action = td.Actions.Item(1)
    action.Path = "wscript.exe"
    action.Arguments = f'"{VBS}"'

    # TASK_CREATE_OR_UPDATE = 6, TASK_LOGON_INTERACTIVE_TOKEN = 3
    root.RegisterTaskDefinition(TASK_NAME, td, 6, None, None, 3)

    # Verify bằng cách đọc lại
    task2 = root.GetTask(TASK_NAME)
    a = task2.Definition.Actions.Item(1)
    print(f"OK: {TASK_NAME}")
    print(f"  Path      = {a.Path}")
    print(f"  Arguments = {a.Arguments}")
    print(f"  State     = {task2.State}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
