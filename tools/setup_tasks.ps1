# QUAN AI BRAIN 24/7 Setup Script - PowerShell
# Run as Administrator for best results
# Usage: powershell -ExecutionPolicy Bypass -File tools/setup_tasks.ps1

$baseDir = "E:\AI\QUAN AI BRAIN"
$venvPython = "C:\Users\DELL\.venv\Scripts\python.exe"
$watchdog = "$baseDir\tools\watchdog.py"
$backupScript = "$baseDir\tools\backup_database.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "QUAN AI BRAIN 24/7 Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Task 1: Watchdog (runs at logon)
Write-Host "`n1. Creating Watchdog task..." -ForegroundColor Yellow
$watchdogAction = New-ScheduledTaskAction -Execute $venvPython -Argument "`"$watchdog`""
$watchdogTrigger = New-ScheduledTaskTrigger -AtLogOn -Delay "PT5M"
$watchdogPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$watchdogSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

try {
    Register-ScheduledTask -TaskName "QUAN_AIBRAIN_Watchdog" `
        -Action $watchdogAction `
        -Trigger $watchdogTrigger `
        -Principal $watchdogPrincipal `
        -Settings $watchdogSettings `
        -Description "Auto-restart QUAN AI BRAIN server on crash" `
        -Force
    Write-Host "  ✅ Watchdog task created successfully" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Warning: $_" -ForegroundColor Red
}

# Task 2: Daily Backup (2AM)
Write-Host "`n2. Creating Backup task..." -ForegroundColor Yellow
$backupAction = New-ScheduledTaskAction -Execute $venvPython -Argument "`"$backupScript`""
$backupTrigger = New-ScheduledTaskTrigger -Daily -At 2am
$backupPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$backupSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

try {
    Register-ScheduledTask -TaskName "QUAN_AIBRAIN_Backup" `
        -Action $backupAction `
        -Trigger $backupTrigger `
        -Principal $backupPrincipal `
        -Settings $backupSettings `
        -Description "Daily database backup at 2AM" `
        -Force
    Write-Host "  ✅ Backup task created successfully" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Warning: $_" -ForegroundColor Red
}

# Verify tasks
Write-Host "`n3. Verifying tasks..." -ForegroundColor Yellow
$tasks = Get-ScheduledTask -TaskName "QUAN_AIBRAIN_*" -ErrorAction SilentlyContinue

if ($tasks) {
    Write-Host "`n  Created tasks:" -ForegroundColor Cyan
    foreach ($task in $tasks) {
        $state = $task.State
        $color = if ($state -eq "Ready") { "Green" } else { "Yellow" }
        Write-Host "    - $($task.TaskName): $state" -ForegroundColor $color
    }
} else {
    Write-Host "  ⚠ No tasks found. Check if script ran with correct permissions." -ForegroundColor Red
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Setup complete! Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open Task Scheduler: taskschd.msc" -ForegroundColor White
Write-Host "  2. Open Health Dashboard: http://127.0.0.1:8765/health_dashboard.html" -ForegroundColor White
Write-Host "  3. Check logs: $baseDir\logs\" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan