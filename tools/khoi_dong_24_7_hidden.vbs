REM KHOI DONG CHERRY 24/7 - logon launcher (24/11/2026 owner: cherry tu chay lai sau moi lan khoi dong may)
REM Goi KHOI_DONG_CHERRY.bat - 1 CUA SO CONSOLE HIEN DIEN (owner 19/11: khong an cua so cherry)
REM Task Scheduler chay VBS nay; .bat tu idempotent (port 8765) nen chay nhieu lan an toan.
Set oWS = CreateObject("WScript.Shell")
oWS.CurrentDirectory = "E:\BRAIN"
oWS.Run """E:\BRAIN\KHOI_DONG_CHERRY.bat""", 1, False
