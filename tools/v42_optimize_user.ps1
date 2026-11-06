# V42 - Tối ưu user-level (KHÔNG admin). Mục tiêu: boot nhanh, bớt preload rác.
# Không đụng: UniKey, Zalo, GoogleDriveFS, audio (Rtk/Waves), SecurityHealth, Dell services.
$ErrorActionPreference = 'SilentlyContinue'

Write-Output '===== 1. TAT EDGE PRELOAD KHI BOOT (AutoLaunch) ====='
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'MicrosoftEdgeAutoLaunch_6B770857D9B81538FA9524CBB2D560C5'
if ($?) { Write-Output 'Da xoa Edge AutoLaunch (edge khong tu chay nua, van mo binh thuong khi bam icon)' }

Write-Output ''
Write-Output '===== 2. DISABLE UPDATER TASKS (user-level) ====='
foreach ($t in @(
  'CorelUpdateHelperTask-2B6063FC35C10D58B90A4E6F69967309',
  'ZoomUpdateTaskUser-S-1-5-21-1410210442-2824532312-2499475624-1001',
  'OneDrive Reporting Task-S-1-5-21-1410210442-2824532312-2499475624-1001'
)) {
  Disable-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue | Out-Null
  $s = (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue).State
  Write-Output ("{0} -> {1}" -f ($t -split '-')[0], $s)
}

Write-Output ''
Write-Output '===== 3. STORAGE SENSE: bat don temp tu dong ====='
$sp = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy'
if (-not (Test-Path $sp)) { New-Item -Path $sp -Force | Out-Null }
Set-ItemProperty $sp '01' 1          # Storage Sense on
Set-ItemProperty $sp '04' 1          # xoa file temp cua app
Set-ItemProperty $sp '08' 1          # xoa Recycle Bin qua 1 ngay
Write-Output 'StorageSense: 01=1 (on), 04=1 (temp), 08=1 (recycle 1 ngay)'

Write-Output ''
Write-Output '===== 4. VERIFY ====='
$edge = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run').'MicrosoftEdgeAutoLaunch_6B770857D9B81538FA9524CBB2D560C5'
Write-Output ("Edge AutoLaunch con lai: " + $(if ($edge) {'VAN CON - LOI'} else {'da xoa OK'}))
$ss = Get-ItemProperty $sp
Write-Output ("StorageSense verify: 01={0} 04={1} 08={2}" -f $ss.'01', $ss.'04', $ss.'08')
