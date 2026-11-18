Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = """E:\BRAIN"""
WshShell.Run """E:\BRAIN\tools\run_morning_report.bat""", 0, False
