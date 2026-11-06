# V42 - Kiem tra suc khoe he thong (READ-ONLY, khong xoa gi)
$ErrorActionPreference = 'SilentlyContinue'

function FolderSize($p) {
  if (-not (Test-Path $p)) { return $null }
  $m = Get-ChildItem -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum
  return [math]::Round($m.Sum / 1MB, 1)
}
function Line($t, $v) { Write-Output ("{0}: {1}" -f $t, $v) }

Write-Output '===== A. HE DIEU HANH ====='
$os = Get-CimInstance Win32_OperatingSystem
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
Line 'OS' ($os.Caption + ' ' + $cv.DisplayVersion + ' (build ' + $cv.CurrentBuild + '.' + $cv.UBR + ')')
$boot = $os.LastBootUpTime
Line 'Khoi dong lan cuoi' $boot
Line 'Uptime' ((Get-Date) - $boot).ToString('d\d\ hh\h\ mm\p')
Line ' arch' $os.OSArchitecture
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Line 'Phien chay co Admin?' $admin
$pend1 = Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending'
$pend2 = Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
Line 'Cho restart (WU/CBS)' ($pend1 -or $pend2)

Write-Output ''
Write-Output '===== B. O DIA ====='
Get-Volume | Where-Object { $_.DriveLetter -in 'C','E' } | ForEach-Object {
  $tot = [math]::Round($_.Size/1GB,1); $free = [math]::Round($_.SizeRemaining/1GB,1)
  Write-Output ("O {0}: {1} GB / {2} GB  (con tro {3} GB = {4}%)" -f $_.DriveLetter, $tot, ($tot-$free), $free, [math]::Round(100*$free/$tot))
}
Get-PhysicalDisk | ForEach-Object { Write-Output ("Disk: {0} | {1} | Health: {2}" -f $_.FriendlyName, $_.MediaType, $_.HealthStatus) }
foreach ($f in 'C:\hiberfil.sys','C:\pagefile.sys','C:\swapfile.sys') {
  $i = Get-Item $f -Force
  if ($i) { Line $f ([math]::Round($i.Length/1GB,2).ToString() + ' GB') }
}
if (Test-Path 'C:\Windows.old') { Line 'Windows.old TON TAI' (FolderSize 'C:\Windows.old').ToString() + ' GB?' } else { Line 'Windows.old' 'khong co' }

Write-Output ''
Write-Output '===== C. RAM ====='
$totGB = [math]::Round($os.TotalVisibleMemorySize/1MB,1)
$freeGB = [math]::Round($os.FreePhysicalMemory/1MB,1)
Line "Tong / con lai" ("{0} GB / {1} GB" -f $totGB, $freeGB)
Write-Output 'Top 10 tien trinh RAM (MB):'
Get-Process | Sort-Object WS -Descending | Select-Object -First 10 | ForEach-Object {
  Write-Output ("  {0} (PID {1}): {2} MB" -f $_.ProcessName, $_.Id, [math]::Round($_.WS/1MB))
}

Write-Output ''
Write-Output '===== D. RAC HE THONG (MB) ====='
Line 'Temp nguoi dung' (FolderSize $env:TEMP)
Line 'C:\Windows\Temp' (FolderSize 'C:\Windows\Temp')
Line 'WU SoftwareDistribution\Download' (FolderSize 'C:\Windows\SoftwareDistribution\Download')
Line 'CrashDumps nguoi dung' (FolderSize "$env:LOCALAPPDATA\CrashDumps")
Line 'WER nguoi dung' (FolderSize "$env:LOCALAPPDATA\Microsoft\Windows\WER")
Line 'WER ProgramData' (FolderSize 'C:\ProgramData\Microsoft\Windows\WER')
Line 'D3DSCache (shader)' (FolderSize "$env:LOCALAPPDATA\D3DSCache")
Line 'INetCache' (FolderSize "$env:LOCALAPPDATA\Microsoft\Windows\INetCache")
if (Test-Path 'C:\Windows\MEMORY.DMP') { Line 'MEMORY.DMP' ([math]::Round((Get-Item 'C:\Windows\MEMORY.DMP' -Force).Length/1MB,1)) } else { Line 'MEMORY.DMP' 'khong co' }
$rb = 0; $shell = New-Object -ComObject Shell.Application
$shell.Namespace(0xA).Items() | ForEach-Object { $rb += $_.Size }
Line 'Recycle Bin' ([math]::Round($rb/1MB,1))
$chrome = FolderSize "$env:LOCALAPPDATA\Google\Chrome\User Data"; $edge = FolderSize "$env:LOCALAPPDATA\Microsoft\Edge\User Data"
Line 'Chrome User Data (toan bo)' $chrome
Line 'Edge User Data (toan bo)' $edge
$chromeRunning = [bool](Get-Process chrome -ErrorAction SilentlyContinue)
$edgeRunning = [bool](Get-Process msedge -ErrorAction SilentlyContinue)
Line 'Chrome/Edge dang chay?' ("{0} / {1}" -f $chromeRunning, $edgeRunning)

Write-Output ''
Write-Output '===== E. AUTO-START ====='
foreach ($k in 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\Run') {
  $p = Get-ItemProperty $k
  if ($p) { $p.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object { Write-Output ("  [{0}] {1}" -f $k.Substring(0,4), $_.Name) } }
}
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-ChildItem $startup -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("  [startup-folder] " + $_.Name) }
$tasks = Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' -and $_.State -ne 'Disabled' }
Line 'Scheduled tasks ngoai Microsoft (Ready)' $tasks.Count
$tasks | ForEach-Object { Write-Output ("  [{0}] {1}" -f $_.State, $_.TaskName) }
$dis = Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' -and $_.State -eq 'Disabled' }
Line 'Scheduled tasks ngoai Microsoft (Disabled)' $dis.Count
$dis | Select-Object -First 6 | ForEach-Object { Write-Output ("  [DISABLED] " + $_.TaskName) }

Write-Output ''
Write-Output '===== F. LOI 7 NGAY GAN NHAT ====='
foreach ($log in 'System','Application') {
  Write-Output ("--- $log ---")
  Get-WinEvent -FilterHashtable @{LogName=$log; Level=1,2; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 400 |
    Group-Object ProviderName | Sort-Object Count -Descending | Select-Object -First 6 |
    ForEach-Object { Write-Output ("  {0}: {1}" -f $_.Name, $_.Count) }
}

Write-Output ''
Write-Output '===== G. POWER / DEFENDER ====='
powercfg /getactivescheme
$mp = Get-MpComputerStatus
if ($mp) { Line 'Defender realtime' $mp.RealTimeProtectionEnabled; Line 'Defender signature age (ngay)' $mp.AntivirusSignatureAge }
Write-Output '===== HET (READ-ONLY) ====='
