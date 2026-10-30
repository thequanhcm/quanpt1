$ErrorActionPreference = 'SilentlyContinue'
$stamp = 'Truoc toi uu'

Write-Output '===== 4. POWER SETTINGS CHI TIET ====='
powercfg /getactivescheme
$bat = Get-CimInstance Win32_Battery
if ($bat) {
  Write-Output ("Pin: {0}% | Trang thai: {1} | Thoi luong uoc tinh: {2} phut" -f $bat.EstimatedChargeRemaining, $bat.BatteryStatus, $bat.EstimatedRunTime)
} else { Write-Output 'KHONG CO PIN (may ban)' }

Write-Output ''
Write-Output '===== 5. BATTERY REPORT 7 NGAY (đọc sẵn để anh xem) ====='
powercfg /batteryreport /output "$env:TEMP\battery_report.html" 2>&1 | Out-Null
if (Test-Path "$env:TEMP\battery_report.html") {
  $html = Get-Content "$env:TEMP\battery_report.html" -Raw
  $dc = [regex]::Match($html, 'DESIGN CAPACITY</SPAN></td><td[^>]*>([\d,]+) mWh').Groups[1].Value
  $fc = [regex]::Match($html, 'FULL CHARGE CAPACITY</SPAN></td><td[^>]*>([\d,]+) mWh').Groups[1].Value
  Write-Output ("Design: {0} mWh | Full charge: {1} mWh" -f $dc, $fc)
  if ($dc -and $fc) {
    $d = [long]($dc -replace ',',''); $f = [long]($fc -replace ',','')
    Write-Output ("Suy hao pin: {0}%" -f [math]::Round(100*($d-$f)/$d,1))
  }
  # 7 ngày gần nhất
  $rows = [regex]::Matches($html, '<td>(\d{2}/\d{2}/\d{4})[\s\S]{0,300}?FULL CHARGE CAPACITY</td><td>([\d,]+) mWh[\s\S]{0,300}?<td>([\d,]+)</td>')
  $rows | Select-Object -Last 5 | ForEach-Object {
    Write-Output ("  {0}: capacity {1} mWh" -f $_.Groups[1].Value, $_.Groups[2].Value)
  }
}

Write-Output ''
Write-Output '===== 6. BOOT TIME + SERVICES TU DONG ====='
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$uptime = (Get-Date) - $boot
Write-Output ("Boot lan cuoi: {0:HH:mm:ss dd/MM} | Uptime: {1:hh\:mm}" -f $boot, $uptime)
# servicios automáticos parados = rác cấu hình
$autoStopped = Get-CimInstance Win32_Service -Filter "StartMode='Auto' AND State='Stopped'" |
  Select-Object -First 12 Name, DisplayName
Write-Output ("Services Auto-nhung-dang-DUNG (co the rac cau hinh): {0}" -f $autoStopped.Count)
$autoStopped | ForEach-Object { Write-Output ("  {0} | {1}" -f $_.Name, $_.DisplayName) }

Write-Output ''
Write-Output '===== 7. STARTUP APPS (Win32 startup) ====='
Get-CimInstance Win32_StartupCommand | ForEach-Object {
  Write-Output ("  [{0}] {1}" -f $_.Location, $_.Name)
}

Write-Output ''
Write-Output '===== 8. PAGEFILE + VSS SHADOW COPIES ước lượng ====='
Get-CimInstance Win32_PageFileSetting | ForEach-Object {
  Write-Output ("Pagefile: {0} Initial={1}MB Max={2}MB" -f $_.Name, $_.InitialSize, $_.MaximumSize)
}
$sp = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -ErrorAction SilentlyContinue).PagingFiles
Write-Output ("PagingFiles raw: {0}" -f ($sp -join ' | '))
