Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\BRAIN"
WshShell.Run """E:\BRAIN\.venv\Scripts\python.exe"" ""E:\BRAIN\tools\pi5_monitor.py"" --once --notify", 0, False
