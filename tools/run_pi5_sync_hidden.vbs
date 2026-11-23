Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\BRAIN"
WshShell.Run """E:\BRAIN\.venv\Scripts\python.exe"" ""E:\BRAIN\tools\pi5_edge_file_sync_guard.py"" --once --quiet", 0, False
