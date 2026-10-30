Write-Output '=== 1. Scheduled tasks (QUAN/TONY/Ollama) ==='
Get-ScheduledTask -ErrorAction SilentlyContinue |
  Where-Object { $_.TaskName -match 'QUAN|TONY|Ollama|ollama' -or $_.Actions.Execute -match 'QUAN|TONY|ollama' } |
  ForEach-Object {
    $act = ($_ | Get-ScheduledTaskInfo -ErrorAction SilentlyContinue)
    Write-Output ($_.TaskName + ' | State=' + $_.State + ' | Path=' + $_.TaskPath)
  }
Write-Output ''
Write-Output '=== 2. User Startup folder ==='
$us = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-ChildItem $us -ErrorAction SilentlyContinue | ForEach-Object { Write-Output $_.Name }
Write-Output ''
Write-Output '=== 3. Common Startup folder ==='
$cs = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
Get-ChildItem $cs -ErrorAction SilentlyContinue | ForEach-Object { Write-Output $_.Name }
Write-Output ''
Write-Output '=== 4. Registry Run keys (HKCU + HKLM) ==='
$runKeys = @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run')
foreach ($rk in $runKeys) {
  if (Test-Path $rk) {
    $props = Get-ItemProperty -Path $rk -ErrorAction SilentlyContinue
    foreach ($p in $props.PSObject.Properties) {
      if ($p.Name -notmatch '^PS') { Write-Output ($rk + '  ::  ' + $p.Name + ' = ' + $p.Value) }
    }
  }
}
Write-Output ''
Write-Output '=== 5. Desktop shortcuts TONY/QUAN ==='
Get-ChildItem "$env:USERPROFILE\Desktop" -Filter '*.lnk' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'TONY|QUAN' } | ForEach-Object { Write-Output $_.Name }
Write-Output ''
Write-Output '=== 6. Processes background QUAN-related con song ==='
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { ($_.Name -match 'ollama|python') -and ($_.CommandLine -match 'QUAN|ollama serve' -or $_.ExecutablePath -match 'Ollama|QUAN') } |
  ForEach-Object { Write-Output ($_.ProcessId.ToString() + '  ' + $_.Name + '  ' + $_.ExecutablePath) }
