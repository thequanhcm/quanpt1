$report = @()

# 1. Scheduled tasks: DISABLE (khong xoa de rollback duoc)
foreach ($t in @('QUAN_AI_BRAIN_BACKUP_2AM', 'QUAN_AI_BRAIN_KHOI_DONG_LOGON', 'QUAN_AI_BRAIN_MORNING_REPORT_8AM')) {
  try {
    Disable-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null
    $report += ('TASK DISABLED: ' + $t)
  } catch {
    $report += ('TASK DISABLE FAILED: ' + $t + ' :: ' + $_.Exception.Message)
  }
}

# 2. Startup folder: rename (de rollback, khong xoa mat bay)
$us = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$startupBat = Join-Path $us 'KHOI_DONG_24_7.bat'
if (Test-Path $startupBat) {
  $disabled = Join-Path $us 'KHOI_DONG_24_7.bat.DISABLED_BY_QUANPT1'
  Move-Item -LiteralPath $startupBat -Destination $disabled -Force
  $report += ('STARTUP RENAMED: ' + $startupBat + ' -> .DISABLED_BY_QUANPT1')
} else {
  $report += 'STARTUP: khong thay KHOI_DONG_24_7.bat (da tat truoc do?)'
}

# 3. Stop ollama
$oll = Get-Process ollama -ErrorAction SilentlyContinue
if ($oll) {
  Stop-Process -Id $oll.Id -Force -ErrorAction SilentlyContinue
  $report += ('OLLAMA STOPPED: PID ' + $oll.Id)
} else {
  $report += 'OLLAMA: khong chay'
}

$report | ForEach-Object { Write-Output $_ }
