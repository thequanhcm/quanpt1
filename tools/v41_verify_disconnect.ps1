Write-Output '=== Xac nhan cuoi cung: khong con gi QUAN/TONY tu dong ==='
Write-Output ''
Write-Output '1. Task Scheduler:'
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'QUAN|TONY' } |
  ForEach-Object { Write-Output ('   ' + $_.TaskName + ' = ' + $_.State) }
Write-Output ''
Write-Output '2. Startup folder:'
$us = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$items = Get-ChildItem $us -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch 'DISABLED_BY_QUANPT1' }
if ($items) { $items | ForEach-Object { Write-Output ('   CON: ' + $_.Name) } } else { Write-Output '   sach (chi con file .DISABLED_BY_QUANPT1)' }
Write-Output ''
Write-Output '3. Process QUAN/ollama:'
$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'QUAN AI BRAIN' -or $_.ExecutablePath -match 'Ollama' }
if ($p) { $p | ForEach-Object { Write-Output ('   CON: ' + $_.ProcessId.ToString() + ' ' + $_.Name) } } else { Write-Output '   khong con process nao' }
Write-Output ''
Write-Output '4. Port 8765/8766/11434/8768:'
$np = netstat -ano | Select-String ':8765|:8766|:11434|:8768'
if ($np) { $np | ForEach-Object { Write-Output ('   ' + $_.Line.Trim()) } } else { Write-Output '   tat ca da dong' }
