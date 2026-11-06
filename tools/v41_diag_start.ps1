Write-Output '=== BAT TRONG ROOT (khoi dong) ==='
Get-ChildItem 'E:\AI\QUAN AI BRAIN' -Filter '*.bat' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
Write-Output ''
Write-Output '=== Task Scheduler tasks QUAN_AI ==='
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'QUAN|TONY' } |
  Select-Object TaskName, State | Format-Table -AutoSize | Out-String -Width 90
Write-Output '=== watchdog log cuoi ==='
if (Test-Path 'E:\AI\QUAN AI BRAIN\logs\watchdog.log') {
  Get-Content 'E:\AI\QUAN AI BRAIN\logs\watchdog.log' -Tail 4
} else { Write-Output 'khong co watchdog.log' }
