Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\BRAIN"
WshShell.Run """E:/BRAIN/.venv/Scripts/python.exe"" ""E:\BRAIN\tools\mirror_d_daemon.py"" --once", 0, False
