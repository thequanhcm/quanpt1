@echo off

chcp 65001 >nul

set "HIDDEN=0"
if /i "%~1"=="--hidden" set "HIDDEN=1"

title CHERRY - KHOI DONG TAY (1 cua so)

REM ============================================================

REM  CHERRY - BAT BANG TAY (owner 19/11: chi khi nao anh muon bat

REM  lan thi moi su dung. Khong tu khoi dong, khong an cua so.)

REM  (23/11/2026 owner: tich hop vao 1 cua so bao gom tong the toan

REM   bo noi dung, khong de thanh 4 cua so terminal dang chay)

REM  - MOT cua so duy nhat: Servers + NetChat + Learning log tron chung

REM  - KHONG khoi dong Cherry Autonomous - auto-mode da disabled

REM  - Task Scheduler logon/liveness DISABLE - file nay chi chay khi anh double-click

REM ============================================================

cd /d "E:\BRAIN"

color 0A

set "PYTHONUTF8=1"

set "PYTHONIOENCODING=utf-8"

set "NETMIND_EXTERNAL_DATA_ALLOWED=true"

if "%NETMIND_API_KEY%"=="" call :LoadUserEnv

echo ============================================================

echo    CHERRY - KHOI DONG TAY - 1 CUA SO DUY NHAT

echo    Log cua 3 thanh phan tron chung, danh mau phan biet.

echo    Muon tat Cherry: chay TAT_CHERRY.bat

echo ============================================================

echo.

if not exist ".venv\Scripts\python.exe" (

    echo [LOI] Khong tim thay .venv tai E:\BRAIN

    pause

    exit /b 1

)

REM ---- Idempotent: neu servers dang chay thi khong mo them ----

netstat -an | findstr /C:":8765 " | findstr LISTENING >nul 2>&1

if not errorlevel 1 (

    REM Cherry dang chay - neu CHUA co cua so console host thi mo dung 1 cua so
    REM giam sat (--attach); neu da co thi thoat ngam, khong tao them cua so.
    if exist "data\console_host.lock" (
        if "%HIDDEN%"=="1" exit /b 0
        echo [INFO] Cherry dang chay va cua so giam sat dang mo - khong mo trung.
        timeout /t 3 >nul
        exit /b 0
    )
    echo [INFO] Cherry dang chay - mo cua so giam sat attach.
    start "CHERRY - KHOI DONG TAY (1 cua so)" ".venv\Scripts\python.exe" "tools\cherry_console_host.py" --attach
    exit /b 0

)

REM ---- MOT CUA SO DUY NHAT: console host tron log 3 service ----

REM (23/11/2026) host tu khoi dong DualServers + NetChat + Learning,

REM doc log moi service va in tron ve cua so nay. Dong cua so = tat het.

".venv\Scripts\python.exe" "tools\cherry_console_host.py"

echo.

echo CHERRY DA TAT - dong cua so la tat het service.

pause

exit /b 0



:LoadUserEnv

for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v NETMIND_API_KEY 2^>nul') do set "NETMIND_API_KEY=%%B"

for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v NETMIND_DESKTOP_LLM_BASE_URL 2^>nul') do set "NETMIND_DESKTOP_LLM_BASE_URL=%%B"

exit /b 0

