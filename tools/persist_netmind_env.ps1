# Lưu API key + base URL vào user-level environment (persist qua reboot)
# An toàn: giá trị KHÔNG bao giờ in ra, không log, không truyền qua command line.
# Nguồn: biến env hiện tại (kế thừa từ netMind Desktop).

$names = @('NETMIND_API_KEY', 'HERMES_CUSTOM_NETMIND_API_KEY', 'NETMIND_DESKTOP_LLM_BASE_URL', 'NETMIND_EXTERNAL_DATA_ALLOWED')

# NETMIND_API_KEY lấy từ HERMES_CUSTOM_NETMIND_API_KEY (giá trị giống nhau)
$key = $env:HERMES_CUSTOM_NETMIND_API_KEY
$base = $env:NETMIND_DESKTOP_LLM_BASE_URL

if ([string]::IsNullOrEmpty($key)) {
    Write-Output "SOURCE_KEY: MISSING in current session - ABORT (khong ghi gi)"
    exit 1
}

[Environment]::SetEnvironmentVariable('NETMIND_API_KEY', $key, 'User')
[Environment]::SetEnvironmentVariable('HERMES_CUSTOM_NETMIND_API_KEY', $key, 'User')
if (-not [string]::IsNullOrEmpty($base)) {
    [Environment]::SetEnvironmentVariable('NETMIND_DESKTOP_LLM_BASE_URL', $base, 'User')
}
[Environment]::SetEnvironmentVariable('NETMIND_EXTERNAL_DATA_ALLOWED', 'true', 'User')

Write-Output "=== VERIFY (existence only, khong in gia tri) ==="
foreach ($n in $names) {
    $v = [Environment]::GetEnvironmentVariable($n, 'User')
    if ([string]::IsNullOrEmpty($v)) {
        Write-Output "$n : MISSING"
    } else {
        Write-Output "$n : SET (len=$($v.Length))"
    }
}
