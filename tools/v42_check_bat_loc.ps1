$ErrorActionNeutral = 'SilentlyContinue'
Write-Output '===== KHOI_DONG_24_7.bat: TAT CA VI TRI ====='
foreach ($p in @(
  "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
  "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
)) {
  Get-ChildItem $p -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("  [{0}] {1}" -f $p, $_.Name)
  }
}
Write-Output ''
Write-Output '===== PIN: DOC TRUC TIEN ====='
$bat = Get-CimInstance Win32_Battery
Write-Output ("Design: {0} mWh | FullCharge: {1} mWh | Suy hao: {2}%" -f $bat.DesignCapacity, $bat.FullChargeCapacity, [math]::Round(100*($bat.DesignCapacity-$bat.FullChargeCapacity)/$bat.DesignCapacity,1))
Write-Output ("Trang thai: {0} | {1}%" -f $bat.BatteryStatus, $bat.EstimatedChargeRemaining)
