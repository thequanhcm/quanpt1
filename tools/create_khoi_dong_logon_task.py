"""Sprint 7a fix: Task Scheduler ONLOGON cho KHOI_DONG_24_7.bat.

Startup folder KHÔNG chạy được sau reboot thật (27/10 12:02: backup task
fire OK qua trigger, nhưng KHOI_DONG .bat trong Startup folder không chạy —
0 daemon sau boot). Giải pháp bền: Task Scheduler logon trigger chạy .bat,
không phụ thuộc Startup folder policy.
"""
from __future__ import annotations

import win32com.client

TASK_NAME = "QUAN_AI_BRAIN_KHOI_DONG_LOGON"


def main() -> int:
    sched = win32com.client.Dispatch("Schedule.Service")
    sched.Connect()
    root = sched.GetFolder("\\")
    td = sched.NewTask(0)
    td.RegistrationInfo.Description = "QUAN AI BRAIN 24/7 auto-start on login (Sprint 7a)"
    td.Settings.StartWhenAvailable = True
    td.Settings.DisallowStartIfOnBatteries = False
    td.Settings.StopIfGoingOnBatteries = False
    td.Settings.ExecutionTimeLimit = "PT0S"  # không giới hạn thời gian
    trig = td.Triggers.Create(9)  # TASK_TRIGGER_LOGON
    trig.UserId = "DELL"
    trig.Enabled = True
    action = td.Actions.Create(0)
    action.Path = r"E:\AI\QUAN AI BRAIN\KHOI_DONG_24_7.bat"
    action.WorkingDirectory = r"E:\AI\QUAN AI BRAIN"
    root.RegisterTaskDefinition(TASK_NAME, td, 6, None, None, 3)  # 6 = update-or-create
    print(f"{TASK_NAME}: created OK (logon trigger, chạy KHOI_DONG_24_7.bat)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
