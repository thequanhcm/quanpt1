Write-Output '=== pythonw dang chay ==='
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object {
    $cl = ''
    if ($_.CommandLine) { $cl = ($_.CommandLine -replace '\s+', ' ') }
    if ($cl.Length -gt 100) { $cl = $cl.Substring(0, 100) }
    Write-Output ($_.ProcessId.ToString() + '  ' + $cl)
  }
if (-not (Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue)) {
  Write-Output '(KHONG CO pythonw nao dang chay)'
}
Write-Output ''
Write-Output '=== python exe trong QUAN AI BRAIN ==='
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'QUAN' } |
  ForEach-Object {
    $cl = ($_.CommandLine -replace '\s+', ' ')
    if ($cl.Length -gt 100) { $cl = $cl.Substring(0, 100) }
    Write-Output ($_.ProcessId.ToString() + '  ' + $cl)
  }
if (-not (Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'QUAN' })) {
  Write-Output '(KHONG CO python QUAN AI BRAIN nao dang chay)'
}
