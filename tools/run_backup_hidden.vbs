Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\BRAIN"
WshShell.Run """E:\BRAIN\tools\run_backup.bat""", 0, False
