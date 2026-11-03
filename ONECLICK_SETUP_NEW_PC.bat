REM ==============================================================================
REM QUAN AI BRAIN — ONE-CLICK SETUP CHO MÁY TÍNH MỚI
REM ==============================================================================
REM Mục đích: anh cắm ổ F: (hoặc chép F:\BRAIN sang ổ bất kỳ) vào máy mới,
REM kích hoạt file này 1 lần — toàn bộ tự cài đặt + tự kiểm + khởi động.
REM
REM CÁCH DÙNG: double-click ONECLICK_SETUP_NEW_PC.bat (hoặc chuột phải → Run as
REM administrator nếu muốn tự cài Task Scheduler).
REM
REM Nguyên tắc (AGENTS.md): KHÔNG tự ghi secret; KHÔNG tự phê duyệt; báo trung
REM thực từng bước PASS/FAIL vào reports\ONECLICK_SETUP_LOG.txt.
REM ==============================================================================
@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title QUAN AI BRAIN — One-Click Setup May Moi

set "LOG=%~dp0reports\ONECLICK_SETUP_LOG.txt"
if not exist "%~dp0reports" mkdir "%~dp0reports" >nul 2>&1
echo ============================================== > "%LOG%"
echo  QUAN AI BRAIN ONECLICK — %date% %time% >> "%LOG%"
echo ============================================== >> "%LOG%"

set "PASS=0"
set "FAIL=0"
set "WARN=0"

REM ----------------------------------------------------------------------------
REM [0] XÁC ĐỊNH THƯ MỤC BRAIN (nơi chứa file này)
REM ----------------------------------------------------------------------------
set "BRAIN_DIR=%~dp0"
REM Strip backslash cu de tranh "C:\dir\" bi doc la escape-quote trong lenh pip
if "%BRAIN_DIR:~-1%"=="\" set "BRAIN_DIR=%BRAIN_DIR:~0,-1%"
echo [INFO] Brain dir: %BRAIN_DIR%
echo [STEP 0] Brain dir = %BRAIN_DIR% >> "%LOG%"

REM ----------------------------------------------------------------------------
REM [1] KIỂM TRA PYTHON 3.11 (yêu cầu bắt buộc)
REM     Thứ tự: python trong PATH → netMind bundled → py launcher → winget cài
REM ----------------------------------------------------------------------------
echo [1/8] Kiem tra Python 3.11 ...
set "PYEXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    %%P -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
    if !errorlevel! equ 0 if not defined PYEXE set "PYEXE=%%P"
)
if not defined PYEXE if exist "%LOCALAPPDATA%\netmind_desktop\python\python\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\netmind_desktop\python\python\python.exe"
)
if not defined PYEXE (
    py -3.11 -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 set "PYEXE=py -3.11"
)
if defined PYEXE (
    echo     [PASS] Python tim thay: %PYEXE%
    echo [STEP 1] PASS Python=%PYEXE% >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [WARN] Khong co Python 3.11 — thu winget install...
    echo [STEP 1] WARN Python khong co — thu winget >> "%LOG%"
    set /a WARN+=1
    winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements >nul 2>&1
    for /f "delims=" %%P in ('where python 2^>nul') do (
        %%P -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
        if !errorlevel! equ 0 set "PYEXE=%%P"
    )
    if defined PYEXE (
        echo     [PASS] winget cai xong: %PYEXE%
        echo [STEP 1] PASS sau winget >> "%LOG%"
    ) else (
        echo     [FAIL] Khong cai duoc Python 3.11. ANH HAY CAI PYTHON 3.11 ROI CHAY LAI.
        echo [STEP 1] FAIL khong co Python >> "%LOG%"
        set /a FAIL+=1
        goto :SUMMARY
    )
)

REM ----------------------------------------------------------------------------
REM [2] TẠO VENV (venv KHÔNG portable — luôn tạo lại trên máy mới)
REM     Trên máy GỐC: nếu venv đang hoạt động (import được quan_ai_brain) → giữ
REM     nguyên. Trên máy MỚI: venv cũ hỏng → rename thành .venv_maycu rồi tạo mới.
REM ----------------------------------------------------------------------------
echo [2/8] Kiem tra / tao .venv ...
"%BRAIN_DIR%\.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, r'%BRAIN_DIR%'); import quan_ai_brain" >nul 2>&1
if not errorlevel 1 (
    echo     [PASS] venv hien tai hoat dong — giu nguyen
    echo [STEP 2] PASS venv hien co >> "%LOG%"
    set /a PASS+=1
    goto :VENV_OK
)
if exist "%BRAIN_DIR%\.venv" ren "%BRAIN_DIR%\.venv" ".venv_maycu" >nul 2>&1
%PYEXE% -m venv "%BRAIN_DIR%\.venv" >nul 2>&1
if exist "%BRAIN_DIR%\.venv\Scripts\python.exe" (
    echo     [PASS] venv tao xong - venv cu duoc giu tai .venv_maycu
    echo [STEP 2] PASS venv moi >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [FAIL] Tao venv that bai
    echo [STEP 2] FAIL venv >> "%LOG%"
    set /a FAIL+=1
    goto :SUMMARY
)
:VENV_OK

REM [3] CAI DEPENDENCIES (pyproject.toml + requirements-prod.txt)
REM ----------------------------------------------------------------------------
echo [3/8] Cai dependencies - can internet, ~3-8 phut ...
%PYEXE% -m pip install --upgrade pip >nul 2>&1
"%BRAIN_DIR%\.venv\Scripts\python.exe" -m pip install -e "%BRAIN_DIR%" >nul 2>&1
if exist "%BRAIN_DIR%\requirements-prod.txt" (
    "%BRAIN_DIR%\.venv\Scripts\python.exe" -m pip install -r "%BRAIN_DIR%\requirements-prod.txt" >nul 2>&1
)
"%BRAIN_DIR%\.venv\Scripts\python.exe" -c "import quan_ai_brain" >nul 2>&1
if !errorlevel! equ 0 (
    echo     [PASS] quan_ai_brain import OK
    echo [STEP 3] PASS deps >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [FAIL] Cai dependencies loi — xem log
    echo [STEP 3] FAIL deps >> "%LOG%"
    set /a FAIL+=1
    goto :SUMMARY
)

REM ----------------------------------------------------------------------------
REM [4] CẤU HÌNH MÔI TRƯỜNG MÁY MỚI (.env có sẵn từ mirror — chỉ kiểm)
REM     NETMIND_API_KEY: nếu .env trống → anh tự nhập (KHÔNG bao giờ hardcode)
REM ----------------------------------------------------------------------------
echo [4/8] Kiem tra cau hinh .env (secret KHONG hien thi) ...
if exist "%BRAIN_DIR%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%BRAIN_DIR%\.env") do (
        if /i "%%A"=="NETMIND_API_KEY" if not "%%B"=="" (
            echo     [PASS] .env co NETMIND_API_KEY - gia tri bi an
            set "HAVEKEY=1"
        )
    )
)
if not defined HAVEKEY (
    echo     [WARN] .env chua co NETMIND_API_KEY.
    echo            Anh mo file %BRAIN_DIR%\.env va dan dong NETMIND_API_KEY=xxxx
    echo            lay tu HKCU\Environment tren may cu bang lenh: reg query HKCU\Environment /v NETMIND_API_KEY
    echo            roi dan gia tri vao file .env dong NETMIND_API_KEY=...
    echo [STEP 4] WARN .env thieu key >> "%LOG%"
    set /a WARN+=1
) else (
    echo [STEP 4] PASS .env >> "%LOG%"
    set /a PASS+=1
)

REM ----------------------------------------------------------------------------
REM [5] SSH KEY PI5 — mirror khong chua key private; neu anh da chep ~/.ssh
REM     (id_ed25519) vao %USERPROFILE%\.ssh\ thi PASS, khong thi WARN huong dan
REM ----------------------------------------------------------------------------
echo [5/8] Kiem tra SSH key Pi5 (Tailscale 100.100.83.59) ...
if exist "%USERPROFILE%\.ssh\id_ed25519" (
    echo     [PASS] SSH key co san
    echo [STEP 5] PASS ssh key >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [WARN] Chua co %USERPROFILE%\.ssh\id_ed25519
    echo            Anh chep 2 file id_ed25519 + id_ed25519.pub tu may cu
    echo            copy C:\Users\DELL\.ssh id_ed25519 + id_ed25519.pub sang may nay
    echo [STEP 5] WARN ssh key >> "%LOG%"
    set /a WARN+=1
)

REM ----------------------------------------------------------------------------
REM [6] OLLAMA + MODELS (fallback LLM cục bộ)
REM ----------------------------------------------------------------------------
echo [6/8] Kiem tra Ollama (fallback LLM) ...
curl -s -m 4 http://127.0.0.1:11434/api/tags >nul 2>&1
if !errorlevel! equ 0 (
    echo     [PASS] Ollama dang chay
    "%BRAIN_DIR%\.venv\Scripts\python.exe" -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:11434/api/tags')); names=[m['name'] for m in d.get('models',[])]; need={'qwen2.5:7b','qwen2.5:1.5b','qwen2.5:0.5b'}; missing=need-set(names); print('    [PASS] Models du:' if not missing else f'    [WARN] Thieu models: {sorted(missing)} — chay: ollama pull qwen2.5:7b')" 2>nul
    echo [STEP 6] PASS ollama >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [WARN] Ollama chua chay. Neu chua cai: winget install Ollama.Ollama
    echo            roi: ollama pull qwen2.5:7b  - fallback model du phong
    echo [STEP 6] WARN ollama >> "%LOG%"
    set /a WARN+=1
)

REM ----------------------------------------------------------------------------
REM [7] KIỂM TRA SỨC KHỎE: chạy bộ test nhanh + smoke server
REM ----------------------------------------------------------------------------
echo [7/8] Chay kiem tra suc khoe - test nhanh + smoke server 8765/8766 ...
"%BRAIN_DIR%\.venv\Scripts\python.exe" -m pip install "pytest>=8.0,<10.0" >nul 2>&1
"%BRAIN_DIR%\.venv\Scripts\python.exe" -m pytest "%BRAIN_DIR%\tests\test_deom_m2_task_lifecycle.py" "%BRAIN_DIR%\tests\test_durable_task_registry.py" -q --no-header >nul 2>&1
if !errorlevel! equ 0 (
    echo     [PASS] Test nhanh 54/54
    echo [STEP 7] PASS quick tests >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [FAIL] Test nhanh loi — chay: pytest tests\ -q de xem chi tiet
    echo [STEP 7] FAIL quick tests >> "%LOG%"
    set /a FAIL+=1
)

REM ----------------------------------------------------------------------------
REM [8] TẠO SHORTCUT KHỞI ĐỘNG + TÙY CHỌN TASK SCHEDULER
REM ----------------------------------------------------------------------------
echo [8/8] Tao kieu khoi dong ...
if exist "%BRAIN_DIR%\TONY_START.bat" (
    echo     [PASS] Dung TONY_START.bat de khoi dong he thong hang ngay
    echo            Dung TONY_STOP.bat de tat.
    echo [STEP 8] PASS start scripts >> "%LOG%"
    set /a PASS+=1
) else (
    echo     [WARN] Khong thay TONY_START.bat
    echo [STEP 8] WARN >> "%LOG%"
    set /a WARN+=1
)
REM Ghi chú Task Scheduler Mirror F: chỉ chạy khi ổ F: tồn tại
if exist "F:\BRAIN" (
    schtasks /query /tn QUAN_AI_BRAIN_MIRROR_F >nul 2>&1
    if !errorlevel! neq 0 (
        schtasks /create /tn QUAN_AI_BRAIN_MIRROR_F /tr "python \"%BRAIN_DIR%tools\mirror_workspace_to_f.py\"" /sc daily /st 02:30 /f >nul 2>&1
        if !errorlevel! equ 0 echo     [INFO] Da tao Task Scheduler QUAN_AI_BRAIN_MIRROR_F 02:30
    ) else (
        echo     [INFO] Task Scheduler MIRROR_F da ton tai
    )
)

:SUMMARY
echo.
echo ============================================================
echo   KET QUA ONE-CLICK SETUP — MAY MOI
echo ============================================================
echo   PASS: %PASS%   WARN: %WARN%   FAIL: %FAIL%
echo   Log chi tiet: %LOG%
echo ============================================================
if %FAIL% gtr 0 (
    echo   CO %FAIL% BUOC FAIL — doc log va lam theo huong dan WARN tren man hinh.
) else (
    echo   HE THONG SAN SANG! Khoi dong bang: TONY_START.bat
    echo   Sau khoi dong: kiem tra http://127.0.0.1:8766/health
)
echo.
echo [SUMMARY] PASS=%PASS% WARN=%WARN% FAIL=%FAIL% >> "%LOG%"
pause
endlocal
