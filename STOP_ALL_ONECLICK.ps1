# QUAN AI BRAIN — Emergency Stop (PowerShell)
# More robust process termination

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Red
Write-Host "🛑 QUAN AI BRAIN — EMERGENCY STOP" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

$confirm = Read-Host "⚠️  This will stop ALL services immediately! Continue? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "❌ Cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Step 1: Stopping Task Scheduler Tasks" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$tasks = @(
    "QUAN-AI-BRAIN-Server",
    "QUAN-AI-BRAIN-Watchdog",
    "QUAN-AI-BRAIN-Learning",
    "QUAN-AI-BRAIN-Responder",
    "QUAN-AI-BRAIN-Dashboard"
)

foreach ($task in $tasks) {
    try {
        Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
        Write-Host "✅ $task stopped" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  $task not running or not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Step 2: Killing Python Processes" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Get all python processes
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "Found $($pythonProcesses.Count) Python processes..." -ForegroundColor Yellow
    
    foreach ($proc in $pythonProcesses) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "✅ Killed PID $($proc.Id) - $($proc.Path)" -ForegroundColor Green
        }
        catch {
            Write-Host "⚠️  Could not kill PID $($proc.Id): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "✅ No Python processes running" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Step 3: Verifying Stop" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Wait for processes to terminate
Start-Sleep -Seconds 2

# Check again
$remaining = Get-Process -Name "python" -ErrorAction SilentlyContinue

if ($remaining) {
    Write-Host "⚠️  Some processes still running, forcing..." -ForegroundColor Yellow
    foreach ($proc in $remaining) {
        Stop-Process -Id $proc.Id -Force
        Write-Host "✅ Force killed PID $($proc.Id)" -ForegroundColor Green
    }
} else {
    Write-Host "✅ All processes stopped" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "🛑 EMERGENCY STOP COMPLETE" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""
Write-Host "All services have been stopped." -ForegroundColor White
Write-Host ""
Write-Host "To restart:" -ForegroundColor Cyan
Write-Host "  tools\start_services.bat" -ForegroundColor White
Write-Host "  OR" -ForegroundColor Cyan
Write-Host "  tools\start_services_hidden.bat" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")