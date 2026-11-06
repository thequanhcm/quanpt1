# V42 - Don rac per-user (KHONG can admin). Chi xoa file rac chuan:
#   1. %TEMP% (file khong bi khoa)
#   2. %LOCALAPPDATA%\CrashDumps (in danh sach top truoc khi xoa)
#   3. INetCache (file khong bi khoa)
# Khong dung Chrome (dang chay), khong dung Recycle Bin, khong dung Windows.
$ErrorActionPreference = 'SilentlyContinue'

function FolderSize($p) {
  if (-not (Test-Path $p)) { return 0 }
  (Get-ChildItem -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
}
function CleanFolder($p, $label) {
  if (-not (Test-Path $p)) { Write-Output ("{0}: khong ton tai" -f $label); return }
  $before = FolderSize $p
  Get-ChildItem -LiteralPath $p -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
  }
  $after = FolderSize $p
  $freed = [math]::Round(($before - $after)/1MB, 1)
  Write-Output ("{0}: giai phong {1} MB (con lai {2} MB = file bi khoa/tai ao)" -f $label, $freed, [math]::Round($after/1MB,1))
}

Write-Output '===== CRASHDUMPS: top 10 file truoc khi xoa ====='
$cd = "$env:LOCALAPPDATA\CrashDumps"
Get-ChildItem $cd -File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 10 |
  ForEach-Object { Write-Output ("  {0} | {1} MB | {2}" -f $_.LastWriteTime.ToString('dd/MM HH:mm'), [math]::Round($_.Length/1MB,1), $_.Name) }

Write-Output ''
Write-Output '===== DON RAC ====='
CleanFolder $env:TEMP 'Temp nguoi dung'
CleanFolder $cd 'CrashDumps (dump loi — goc OOM da root-cause, xoa an toan)'
CleanFolder "$env:LOCALAPPDATA\Microsoft\Windows\INetCache" 'INetCache'

Write-Output ''
Write-Output '===== TRANG THAI SAU DON ====='
$os = Get-CimInstance Win32_OperatingSystem
$v = Get-Volume -DriveLetter C
Write-Output ("O C con tro: {0} GB | RAM con lai: {1} GB" -f [math]::Round($v.SizeRemaining/1GB,1), [math]::Round($os.FreePhysicalMemory/1MB,1))
Write-Output '===== HET ====='
