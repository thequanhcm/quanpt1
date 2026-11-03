# Kiem tra process python co chua chuoi <Marker> trong command line (thay the wmic bi loai khoi Windows 11 26300+).
# Thoat 0 = DA CO process (khong khoi dong lai); thoat 1 = CHUA CO (duoc phep khoi dong).
# Cach dung: powershell -NoProfile -File ensure_single_instance.ps1 -Marker "start_dual_servers"
param(
    [Parameter(Mandatory = $true)]
    [string]$Marker
)

$found = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -like "*$Marker*" }

if ($found) {
    foreach ($p in $found) {
        Write-Output ("FOUND pid=" + $p.ProcessId)
    }
    exit 0
}
exit 1
