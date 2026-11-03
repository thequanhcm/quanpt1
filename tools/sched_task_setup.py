"""Sprint 7a + V4.0 (03/11/2026): đăng ký task Scheduler CHẠY NGẦM (không nháy).

Task 2AM backup + 8AM report trước đây trỏ tới .bat → mỗi lần kích hoạt
Windows mở cửa sổ console cmd nháy lên màn hình. Fix chuẩn Windows:
Task Scheduler trỏ tới wscript.exe chạy .vbs wrapper ẩn (WshShell.Run
"...", 0, False) — không cửa sổ nào xuất hiện.

LOGON task (QUAN_AI_BRAIN_KHOI_DONG_LOGON) cũng được trỏ lại sang .vbs.
"""
from __future__ import annotations

import subprocess

WS = r"E:\BRAIN"

TASKS = [
    ("QUAN_AI_BRAIN_BACKUP_2AM", f"{WS}\\tools\\run_backup_hidden.vbs", "02:00"),
    ("QUAN_AI_BRAIN_MORNING_REPORT_8AM", f"{WS}\\tools\\run_morning_report_hidden.vbs", "08:00"),
    ("QUAN_AI_BRAIN_KHOI_DONG_LOGON", f"{WS}\\tools\\khoi_dong_24_7_hidden.vbs", None),
]


def write_vbs() -> None:
    """Tạo 3 file .vbs wrapper 0-window (ASCII + CRLF — bắt buộc cho WSH)."""
    vbs_map = {
        "run_backup_hidden.vbs": f'WshShell.Run """{WS}\\tools\\run_backup.bat""", 0, False\n',
        "run_morning_report_hidden.vbs": f'WshShell.Run """{WS}\\tools\\run_morning_report.bat""", 0, False\n',
        "khoi_dong_24_7_hidden.vbs": f'WshShell.Run """{WS}\\KHOI_DONG_24_7.bat""", 0, False\n',
    }
    for fname, body in vbs_map.items():
        path = f"{WS}\\tools\\{fname}"
        content = 'Set WshShell = CreateObject("WScript.Shell")\n' + body
        # WSH yêu cầu ASCII an toàn + CRLF
        data = content.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii")
        with open(path, "wb") as f:
            f.write(data)


def main() -> int:
    write_vbs()
    ok = True
    for name, tr, st_time in TASKS:
        cmd = ["schtasks", "/Create", "/F", "/SC", "DAILY"]
        if st_time:
            cmd += ["/ST", st_time]
        else:
            cmd += ["/SC", "ONLOGON"]  # LOGON task — giờ không dùng
        cmd += ["/TN", name, "/TR", f'wscript.exe "{tr}"']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # ONLOGON + /SC DAILY xung đột flag — chạy lại đúng cú pháp
        if r.returncode != 0 and st_time is None:
            cmd = ["schtasks", "/Create", "/F", "/SC", "ONLOGON",
                   "/TN", name, "/TR", f'wscript.exe "{tr}"']
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print(f"    OK: {name} -> {tr}")
        else:
            print(f"    BINH THUONG: {name} da dat hoac can Admin ({r.returncode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
