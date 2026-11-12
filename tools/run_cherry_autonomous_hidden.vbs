Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "E:\BRAIN"
WshShell.Run """E:\BRAIN\tools\run_cherry_autonomous.bat""", 0, False
