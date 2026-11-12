@echo off
REM Load secret từ folder user, pass, token vào biến môi trường
REM Dùng cho Task Scheduler, .bat script, manual debug
REM
REM Cách dùng:
REM   call "E:\BRAIN\user, pass, token\load_env.bat"
REM   echo %NETCHAT_BOT_TOKEN%

setlocal

set _SECRET_DIR=E:\BRAIN\user, pass, token
set _SECRETS_ENV=%_SECRET_DIR%\secrets.env

if not exist "%_SECRETS_ENV%" (
    echo [load_env] WARN: %_SECRETS_ENV% không tồn tại
    endlocal
    exit /b 0
)

for /f "usebackq tokens=1* delims==" %%A in ("%_SECRETS_ENV%") do (
    set "line=%%A"
    if not "!line:~0,1!"=="#" (
        if not "!line!"=="" (
            set "%%A=%%B"
        )
    )
)

endlocal
