Write-Output '=== Daemon/ingest python con song? ==='
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object { $cl = $_.CommandLine -replace '\s+', ' '; if ($cl.Length -gt 95) { $cl = $cl.Substring(0, 95) }; Write-Output ($_.ProcessId.ToString() + '  ' + $cl) }
Write-Output '=== Ollama state ==='
Get-Process ollama* -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ($_.Id.ToString() + '  ' + $_.ProcessName + '  WS_GB=' + [math]::Round($_.WorkingSet64/1GB, 2)) }
