REM LIVENESS_30MIN backstop - hoi phuc Cherry khi chet (24/11/2026)
REM Chay .bat voi co --hidden: khi Cherry DANG CHAY thi thoat NGAM, KHONG tao
REM cua so (an toan chay moi 30 phut). Khi Cherry CHET thi .bat khoi phuc va
REM mo dung 1 cua so console host (owner thay Cherry song lai).
Set oWS = CreateObject("WScript.Shell")
oWS.CurrentDirectory = "E:\BRAIN"
oWS.Run """E:\BRAIN\KHOI_DONG_CHERRY.bat"" --hidden", 0, False
