# ============================================================
# V42 - GOI TOI UU ADMIN (chay 1 lan voi quyen Administrator)
# Cach chay: Click Start -> go "powershell" -> Ctrl+Shift+Enter (Run as admin)
#   roi: powershell -ExecutionPolicy Bypass -File "E:\AI\QUAN AI BRAIN\tools\v42_admin_optimize.ps1"
# An toan: khong xoa file ca nhan, khong doi config QUAN AI BRAIN.
# ============================================================
$ErrorActionPreference = 'Continue'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Output 'CHUA CO QUYEN ADMIN - hay chay lai trong PowerShell Run as Administrator!'
  exit 1
}

Write-Output '===== [1/7] DON WINDOWS UPDATE CACHE (1.3 GB) ====='
Stop-Service wuauserv -Force -ErrorAction SilentlyContinue
Stop-Service bits -Force -ErrorAction SilentlyContinue
$wu = 'C:\Windows\SoftwareDistribution\Download'
$before = (Get-ChildItem $wu -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Remove-Item "$wu\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service bits -ErrorAction SilentlyContinue
Start-Service wuauserv -ErrorAction SilentlyContinue
$after = (Get-ChildItem $wu -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Output ("Giai phong: {0} MB" -f [math]::Round(($before-$after)/1MB,1))

Write-Output ''
Write-Output '===== [2/7] POWER: HIGH PERFORMANCE + TAT HIBERNATE (xe may ban; laptop khuyen nghi giu hibernate) ====='
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg /getactivescheme
# may Dell laptop -> giu hibernate de tiet kiem pin khi dong nap. Muon tat bo comment dong sau:
# powercfg /hibernate off

Write-Output ''
Write-Output '===== [3/7] DEFENDER EXCLUDE O E (AI/ingestion doc-viet hang chuc nghin file) ====='
Add-MpPreference -ExclusionPath 'E:\AI' -ErrorAction SilentlyContinue
(Get-MpPreference).ExclusionPath

Write-Output ''
Write-Output '===== [4/7] CHKDSK C: READ-ONLY (kiem tra filesystem, KHONG lock o) ====='
chkdsk C: /scan /timeout:180 2>&1 | Select-String 'no problems|problems found|corrupt|khong co van de|co van de' | ForEach-Object { $_.Line }

Write-Output ''
Write-Output '===== [5/7] TRIM SSD (Optimize-Volume) ====='
Optimize-Volume -DriveLetter C -ReTrim -Verbose 4>&1 | Select-Object -Last 3
Optimize-Volume -DriveLetter E -ReTrim -Verbose 4>&1 | Select-Object -Last 3

Write-Output ''
Write-Output '===== [6/7] FIX BOOT CHAM: Autodesk Licensing -> Delayed Start (dang timeout 180s moi boot) ====='
sc.exe config AdskLicensingService start= delayed-auto
sc.exe qc AdskLicensingService | Select-String 'START_TYPE'

Write-Output ''
Write-Output '===== [7/7] DISABLE OneDrive Reporting Task (chua an o tac user) ====='
Get-ScheduledTask -TaskName 'OneDrive Reporting Task*' -ErrorAction SilentlyContinue | Disable-ScheduledTask | Out-Null
Get-ScheduledTask -TaskName 'OneDrive Reporting Task*' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("  {0} -> {1}" -f $_.TaskName, $_.State) }

Write-Output ''
Write-Output '===== HOAN TAT - TONG KET ====='
$v = Get-Volume -DriveLetter C
Write-Output ("O C con tro: {0} GB" -f [math]::Round($v.SizeRemaining/1GB,1))
Write-Output 'Khuyen nghi: restart may 1 lan de Autodesk delay + Edge preload + Corel/Zoom task co hieu luc triet de.'
