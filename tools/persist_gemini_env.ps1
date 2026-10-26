# Nạp GEMINI_API_KEY từ temp file vào user-level environment (persist qua reboot).
# An toàn: key KHÔNG in/log/truyền qua command line; temp file xoá ngay sau khi nạp.
# Script này KHÔNG chứa secret — an toàn khi commit.

$src = "$env:LOCALAPPDATA\Temp\qab_gemini_key.txt"
if (-not (Test-Path $src)) {
    Write-Output "SOURCE: temp key file khong ton tai - ABORT"
    exit 1
}
$key = (Get-Content $src -Raw).Trim()
Remove-Item $src -Force

if ([string]::IsNullOrEmpty($key)) {
    Write-Output "KEY: rong - ABORT"
    exit 1
}

[Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $key, 'User')
if (-not [Environment]::GetEnvironmentVariable('GEMINI_MODEL', 'User')) {
    [Environment]::SetEnvironmentVariable('GEMINI_MODEL', 'gemini-2.5-flash', 'User')
}

Write-Output "=== VERIFY (existence only) ==="
foreach ($n in 'GEMINI_API_KEY', 'GEMINI_MODEL') {
    $v = [Environment]::GetEnvironmentVariable($n, 'User')
    if ([string]::IsNullOrEmpty($v)) { Write-Output "$n : MISSING" }
    else { Write-Output "$n : SET (len=$($v.Length))" }
}
