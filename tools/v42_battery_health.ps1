$ErrorActionPreference = 'SilentlyContinue'
Write-Output '===== PIN: StaticData (Dell) ====='
$sd = Get-CimInstance -Namespace root\wmi -ClassName BatteryStaticData
$cc = Get-CimInstance -Namespace root\wmi -ClassName BatteryFullChargedCapacity
$dc = Get-CimInstance -Namespace root\wmi -ClassName BatteryCycleCount
if ($sd) {
  $design = $sd.DesignedCapacity
  $full = $cc.FullChargedCapacity
  Write-Output ("Design: {0} mWh | FullCharge: {1} mWh | Suy hao: {2}%" -f $design, $full, [math]::Round(100*($design-$full)/$design,1))
  if ($dc) { Write-Output ("Cycle count: {0}" -f ($dc | ForEach-Object { $_.CycleCount } | Select-Object -First 1)) }
} else {
  Write-Output 'BatteryStaticData khong doc duoc - thu batteryreport XML'
}
