"""Sprint 7 (a): thêm LogonTrigger cho 2 task (backup 2AM + report 8AM) qua COM.

LogonTrigger cho phép task CHẠY NGAY khi anh đăng nhập (bù cho Interactive
only: sau reboot, task 2AM/8AM sẽ không phải chờ tới mốc giờ đầu tiên —
chạy 1 lần ngay, rồi tiếp tục lịch DAILY như cũ). User-level, không cần
admin (đã thử schtasks /SC ONLOGON → Access denied; COM user context OK).
"""
from __future__ import annotations

import sys

import win32com.client

TASKS = ["QUAN_AI_BRAIN_BACKUP_2AM", "QUAN_AI_BRAIN_MORNING_REPORT_8AM"]


def main() -> int:
    sched = win32com.client.Dispatch("Schedule.Service")
    sched.Connect()
    root = sched.GetFolder("\\")
    ok = []
    for name in TASKS:
        try:
            task = root.GetTask(name)
            td = task.Definition
            # Kiểm đã có LogonTrigger chưa (Type 9 = TASK_TRIGGER_LOGON)
            has_logon = False
            for i in range(1, td.Triggers.Count + 1):
                if td.Triggers.Item(i).Type == 9:
                    has_logon = True
            if has_logon:
                ok.append((name, "đã có logon trigger"))
                continue
            trig = td.Triggers.Create(9)  # TASK_TRIGGER_LOGON
            trig.Enabled = True
            trig.Id = f"{name}_logon_boot"
            # Chỉ dậy khi user DELL đăng nhập (mặc định mọi user — giới hạn)
            try:
                trig.UserId = "DELL"
            except Exception:
                pass
            # RegistrationType 0 = cập nhật tại chỗ, giữ mọi thứ khác
            root.RegisterTaskDefinition(task.Path, td, 6, None, None, 3)
            ok.append((name, "added logon trigger"))
        except Exception as e:
            ok.append((name, f"LỖI: {e}"))
    for name, status in ok:
        print(f"{name}: {status}")
    return 0 if all("LỖI" not in s for _, s in ok) else 1


if __name__ == "__main__":
    sys.exit(main())
