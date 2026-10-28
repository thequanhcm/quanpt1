# QUAN AI BRAIN — Update Tasks to Hidden Mode
# Run this as Administrator in PowerShell

$USERNAME = [System.Environment]::UserName
$WORKSPACE = "E:\AI\QUAN AI BRAIN"
$VENV_PYTHON = "$WORKSPACE\.venv\Scripts\python.exe"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "QUAN AI BRAIN — Update to Hidden Mode" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$tasks = @(
    @{Name="QUAN-AI-BRAIN-Server"; Script="tools/server.py"; Desc="Main Server"},
    @{Name="QUAN-AI-BRAIN-Watchdog"; Script="tools/watchdog.py"; Desc="Watchdog"},
    @{Name="QUAN-AI-BRAIN-Learning"; Script="tools/learning.py"; Desc="Learning Engine"},
    @{Name="QUAN-AI-BRAIN-Responder"; Script="tools/netchat_auto_responder.py"; Desc="NetChat Bot"},
    @{Name="QUAN-AI-BRAIN-Dashboard"; Script="edge_client/main.py"; Desc="Dashboard"}
)

foreach ($task in $tasks) {
    $scriptPath = Join-Path $WORKSPACE $task.Script
    $command = "Start-Process `"$VENV_PYTHON`" -ArgumentList `"$scriptPath`" -WindowStyle Hidden -NoNewWindow"
    
    # Remove existing task
    try {
        Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false -ErrorAction SilentlyContinue
    } catch {}
    
    # Create new hidden task
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$command`""
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -Hidden
    
    try {
        Register-ScheduledTask `
            -TaskName $task.Name `
            -Action $action `
            -Trigger $trigger `
            -Principal $principal `
            -Settings $settings `
            -Description $task.Desc `
            -ErrorAction Stop
        
        Write-Host "OK Hidden: $($task.Name)" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL $($task.Name): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "All tasks updated to HIDDEN mode" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Reboot to test" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")