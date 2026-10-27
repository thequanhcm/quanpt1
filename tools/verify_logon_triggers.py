"""Verify logon triggers đã gắn (Sprint 7a)."""
import win32com.client

sched = win32com.client.Dispatch("Schedule.Service")
sched.Connect()
root = sched.GetFolder("\\")
for name in ["QUAN_AI_BRAIN_BACKUP_2AM", "QUAN_AI_BRAIN_MORNING_REPORT_8AM"]:
    td = root.GetTask(name).Definition
    types = [td.Triggers.Item(i).Type for i in range(1, td.Triggers.Count + 1)]
    print(name, "-> triggers:", types, "(9 = LOGON)")
