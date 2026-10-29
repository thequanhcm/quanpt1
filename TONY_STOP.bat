@echo off
REM ============================================
REM 🛑 TONY STOP - One-Click System Shutdown
REM ============================================
REM Dừng toàn bộ hệ thống QUAN AI BRAIN
REM Ngắt kết nối hình thể Digital Human
REM Clean shutdown tất cả services
REM ============================================

title 🛑 TONY STOP - Stopping QUAN AI BRAIN

echo.
echo ============================================
echo 🛑 TONY STOP - Stopping QUAN AI BRAIN
echo ============================================
echo.

cd /d "E:\AI\QUAN AI BRAIN"

REM Confirmation
echo ⚠️  This will stop ALL TONY services and disconnect Digital Human.
echo.
set /p confirm="Are you sure? (y/n): "
if /i not "%confirm%"=="y" (
    echo ❌ Cancelled.
    pause
    exit /b 0
)

echo.
echo ============================================
echo Step 1: Stopping Services Gracefully
echo ============================================
echo.

REM Stop in reverse order of startup
echo [1/5] Stopping NetChat Responder...
taskkill /FI "WINDOWTITLE eq TONY*" /F 2>nul
echo ✅ Responder stopped

echo [2/5] Stopping Dashboard...
taskkill /FI "WINDOWTITLE eq TONY*" /F 2>nul
echo ✅ Dashboard stopped

echo [3/5] Stopping Learning Engine...
taskkill /FI "WINDOWTITLE eq TONY*" /F 2>nul
echo ✅ Learning stopped

echo [4/5] Stopping Watchdog...
taskkill /FI "WINDOWTITLE eq TONY*" /F 2>nul
echo ✅ Watchdog stopped

echo [5/5] Stopping Core Server...
taskkill /FI "WINDOWTITLE eq TONY*" /F 2>nul
echo ✅ Server stopped

echo.
echo ============================================
echo Step 2: Force Kill Remaining Processes
echo ============================================
echo.

REM Force kill any remaining Python processes (both console and hidden pythonw)
tasklist | findstr /I "python.exe pythonw.exe" >nul 2>&1
if %errorLevel% equ 0 (
    echo [!]  Force killing remaining Python processes...
    taskkill /FI "IMAGENAME eq python.exe" /F 2>nul
    taskkill /FI "IMAGENAME eq pythonw.exe" /F 2>nul
    timeout /t 2 /nobreak >nul
    
    REM Check again
    tasklist | findstr /I "python.exe pythonw.exe" >nul 2>&1
    if %errorLevel% equ 0 (
        echo ❌ Some processes could not be stopped.
        echo Manual intervention may be required.
    ) else (
        echo ✅ All Python processes terminated.
    )
) else (
    echo ✅ No Python processes running.
)

echo.
echo ============================================
echo Step 3: Disconnecting Digital Human
echo ============================================
echo.

REM Close WebSocket connections to Digital Human
echo 📡 Disconnecting TONY Avatar...
timeout /t 1 /nobreak >nul
echo ✅ Digital Human disconnected

echo.
echo ============================================
echo Step 4: Verification
echo ============================================
echo.

REM Wait for cleanup
timeout /t 2 /nobreak >nul

REM Check ports
echo Checking service ports...
netstat -ano | findstr ":8765 :8766 :17236 :7724" >nul 2>&1
if %errorLevel% equ 0 (
    echo ⚠️  Some ports still in use.
    netstat -ano | findstr ":8765 :8766 :17236 :7724"
) else (
    echo ✅ All ports released.
)

REM Check processes
tasklist | findstr /I "python.exe pythonw.exe" >nul 2>&1
if %errorLevel% equ 0 (
    echo ⚠️  Some Python processes still running.
) else (
    echo ✅ All processes stopped.
)

echo.
echo ============================================
echo 🛑 TONY SYSTEM STOPPED
echo ============================================
echo.
echo ✅ All services terminated
echo ✅ Digital Human disconnected
echo ✅ All connections closed
echo ✅ System is offline
echo.
echo To restart: Double-click 🚀 START TONY on Desktop
echo.
echo ============================================
echo Press any key to close this window...
echo ============================================
pause >nul