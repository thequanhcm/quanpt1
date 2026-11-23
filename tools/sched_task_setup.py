"""Sprint 7a + V4.0 (03/11/2026): đăng ký task Scheduler CHẠY NGẦM (không nháy).

Task 2AM backup + 8AM report trước đây trỏ tới .bat → mỗi lần kích hoạt
Windows mở cửa sổ console cmd nháy lên màn hình. Fix chuẩn Windows:
Task Scheduler trỏ tới wscript.exe chạy .vbs wrapper ẩn (WshShell.Run
"...", 0, False) — không cửa sổ nào xuất hiện.

(19/11/2026) Owner: Cherry chỉ BẬT TAY — KHÔNG tự khởi động khi logon hay
reboot. Task QUAN_AI_BRAIN_KHOI_DONG_LOGON đã bị DISABLE và bị BỎ khỏi danh
sách đăng ký của script này để không tái sinh. Bật Cherry = owner
double-click E:\\BRAIN\\KHOI_DONG_CHERRY.bat (cửa sổ console hiện rõ).

(19/11/2026) FIX 8007007B (ERROR_INVALID_NAME): CurrentDirectory là LỆNH
GÁN — chỉ dùng 1 cặp quote "E:\\BRAIN". Triple-quote ở dòng .Run là escape
argument string hợp lệ, NHƯNG khi đặt trong docstring Python thì 3 dấu
ngoặc kép liền nhau ĐÓNG docstring → SyntaxError. Dùng cách diễn đạt lại
bằng chữ: bản cũ sinh CurrentDirectory = ba-quotes + E:\\BRAIN + ba-quotes
→ WSH interpret thành chuỗi rỗng + tên không hợp lệ → popup lỗi mỗi 30
phút. Commit 84ef261 (18/11) đã fix tay 3 file .vbs nhưng lần chạy
LIVENESS_30MIN sau đó gọi lại hàm này → ghi đè 3 file về bản lỗi (mtime
22:52:56 18/11 khớp cycle 30 phút). Fix gốc rễ tại template — mọi lần
chạy lại sinh đúng cú pháp.
"""
from __future__ import annotations

import subprocess

WS = r"E:\BRAIN"

TASKS = [
    ("QUAN_AI_BRAIN_BACKUP_2AM", f"{WS}\\tools\\run_backup_hidden.vbs", "02:00"),
    ("QUAN_AI_BRAIN_MORNING_REPORT_8AM", f"{WS}\\tools\\run_morning_report_hidden.vbs", "08:00"),
    # KHÔNG đăng ký lại task logon/autonomous của Cherry — owner tắt auto-start
    # ngày 19/11. Bật Cherry chỉ bằng KHOI_DONG_CHERRY.bat (bật tay, có cửa sổ).
]


def write_vbs() -> None:
    """Tạo .vbs wrapper 0-window (ASCII + CRLF — bắt buộc cho WSH).

    Cú pháp chuẩn: CurrentDirectory dùng 1 cặp quote (lệnh gán); .Run dùng
    triple-quote (escape argument string của WshShell.Run).
    """
    vbs_map = {
        "run_backup_hidden.vbs": (
            f'WshShell.CurrentDirectory = "{WS}"\n'
            f'WshShell.Run """{WS}\\tools\\run_backup.bat""", 0, False\n'
        ),
        "run_morning_report_hidden.vbs": (
            f'WshShell.CurrentDirectory = "{WS}"\n'
            f'WshShell.Run """{WS}\\tools\\run_morning_report.bat""", 0, False\n'
        ),
        # khoi_dong_24_7_hidden.vbs KHÔNG còn được sinh lại — task logon đã hủy.
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
            cmd += ["/SC", "ONLOGON"]  # LOGON task — hiện không dùng
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
