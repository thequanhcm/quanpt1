# QUAN AI BRAIN - Service Setup (User Mode)
$USERNAME = [System.Environment]::UserName
$WORKSPACE = "E:\AI\QUAN AI BRAIN"
$VENV_PYTHON = "$WORKSPACE\.venv\Scripts\python.exe"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "QUAN AI BRAIN - Service Setup (User Mode)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

function Create-Task {
    param([string]$TaskName, [string]$ScriptPath, [string]$Description)
    
    $ScriptFullPath = Join-Path $WORKSPACE $ScriptPath
    $Command = "Start-Process `"$VENV_PYTHON`" -ArgumentList `"$ScriptFullPath`" -NoNewWindow -Wait"
    
    $TaskAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command `"$Command`""
    $TaskTrigger = New-ScheduledTaskTrigger -AtStartup
    $TaskPrincipal = New-ScheduledTaskPrincipal -UserId $USERNAME -LogonType S4U -RunLevel Limited
    $TaskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
    
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $TaskTrigger -Principal $TaskPrincipal -Settings $TaskSettings -Description $Description -ErrorAction Stop
        Write-Host "OK Task created: $TaskName" -ForegroundColor Green
        return $true
    }
    catch {
        $errMsg = $_.Exception.Message
        if ($errMsg -like "*already exists*") {
            Write-Host "SKIP Task exists: $TaskName" -ForegroundColor Yellow
            return $true
        }
        Write-Host "FAIL Task $TaskName" -ForegroundColor Red
        Write-Host "  Error: $errMsg" -ForegroundColor Red
        return $false
    }
}

Write-Host "Creating tasks..." -ForegroundColor Cyan
Write-Host ""

$created = 0
$failed = 0

if (Create-Task -TaskName "QUAN-AI-BRAIN-Server" -ScriptPath "tools/server.py" -Description "Main Server") { $created++ } else { $failed++ }
if (Create-Task -TaskName "QUAN-AI-BRAIN-Watchdog" -ScriptPath "tools/watchdog.py" -Description "Watchdog") { $created++ } else { $failed++ }
if (Create-Task -TaskName "QUAN-AI-BRAIN-Learning" -ScriptPath "tools/learning.py" -Description "Learning Engine") { $created++ } else { $failed++ }
if (Create-Task -TaskName "QUAN-AI-BRAIN-Responder" -ScriptPath "tools/netchat_auto_responder.py" -Description "NetChat Bot") { $created++ } else { $failed++ }
if (Create-Task -TaskName "QUAN-AI-BRAIN-Dashboard" -ScriptPath "edge_client/main.py" -Description "Dashboard") { $created++ } else { $failed++ }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Summary: $created/5 created, $failed failed" -ForegroundColor $(if ($created -eq 5) { "Green" } else { "Yellow" })
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($created -eq 5) {
    Write-Host "SUCCESS! All tasks configured." -ForegroundColor Green
    Write-Host "Run: python tools\health_check.py" -ForegroundColor Cyan
} else {
    Write-Host "Partial success. Check errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")