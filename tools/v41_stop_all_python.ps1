$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue
$killed = @()
$kept = @()
foreach ($p in $procs) {
  $exe = ''
  if ($p.ExecutablePath) { $exe = $p.ExecutablePath }
  $cmd = ''
  if ($p.CommandLine) { $cmd = $p.CommandLine }
  $isNetmind = ($exe -like '*netmind_desktop*') -or ($cmd -like '*netmind_desktop*')
  if ($isNetmind) {
    $kept += ($p.ProcessId.ToString() + '  ' + $exe)
    continue
  }
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
  $killed += ($p.ProcessId.ToString() + '  ' + $exe + '  ' + $cmd)
}
Write-Output '=== DA KILL ==='
if ($killed.Count -eq 0) { Write-Output '(khong con python nao ngoai runtime netMind)' }
$killed | ForEach-Object { Write-Output $_ }
Write-Output '=== GIU LAI (runtime netMind Desktop - runtime cua tro ly) ==='
$kept | ForEach-Object { Write-Output $_ }
Write-Output '=== VERIFY: python con lai ==='
$left = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue
$left | ForEach-Object { Write-Output ($_.ProcessId.ToString() + '  ' + $_.ExecutablePath) }
Write-Output ('Tong con lai: ' + (@($left).Count))
