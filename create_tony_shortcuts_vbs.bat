@echo off
REM Rename TONY shortcuts on Desktop
echo.
echo Renaming TONY shortcuts...
echo.

cd /d "%USERPROFILE%\Desktop"

REM Remove old shortcuts
if exist "START TONY.lnk" del /f "START TONY.lnk"
if exist "STOP TONY.lnk" del /f "STOP TONY.lnk"

REM Create new shortcuts using VBScript
echo Creating new shortcuts...

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set sc = WshShell.CreateShortcut^("START TONY.lnk"^)
echo sc.TargetPath = "E:\AI\QUAN AI BRAIN\TONY_START.bat"
echo sc.WorkingDirectory = "E:\AI\QUAN AI BRAIN"
echo sc.Description = "Start TONY Assistant"
echo sc.Save
echo Set sc = WshShell.CreateShortcut^("STOP TONY.lnk"^)
echo sc.TargetPath = "E:\AI\QUAN AI BRAIN\TONY_STOP.bat"
echo sc.WorkingDirectory = "E:\AI\QUAN AI BRAIN"
echo sc.Description = "Stop TONY Assistant"
echo sc.Save
) > "%TEMP%\create_shortcuts.vbs"

cscript //nologo "%TEMP%\create_shortcuts.vbs"
del "%TEMP%\create_shortcuts.vbs"

echo.
echo ✅ Shortcuts created!
echo    - START TONY.lnk
echo    - STOP TONY.lnk
echo.
pause