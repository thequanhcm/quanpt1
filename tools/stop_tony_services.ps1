# Dung toan bo services TONY (QUAN AI BRAIN) theo MARKER script trong command line.
# (30/10/2026) May moi: kill theo Path '*QUAN AI BRAIN*' khong con dung — path
# workspace hien tai la 'E:\BRAIN' va interpreter con (base python cua
# venv launcher) mang path khac hoan toan. Kill theo marker script:
#   - Bat duoc CA launcher (.venv\pythonw.exe) LAN interpreter con (base python)
#     vi ca hai deu co ten script trong CommandLine.
#   - KHONG bao gio dung netMind Desktop / ung dung Python khac (khong match).
# Dung: powershell -NoProfile -ExecutionPolicy Bypass -File tools\stop_tony_services.ps1 [-VerifyOnly]
param(
    [switch]$VerifyOnly
)

$markers = @(
    'start_dual_servers',
    'netchat_auto_responder',
    'learning_daemon',
    'watchdog\.py',
    'khoi_dong_ollama'
)

$pattern = ($markers -join '|')

$targets = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^python(w)?\.exe$' -and
        $_.CommandLine -match $pattern
    }

if ($VerifyOnly) {
    if ($targets) {
        foreach ($p in $targets) {
            Write-Output ("[!!] Con song: PID " + $p.ProcessId + " :: " + $p.CommandLine)
        }
        exit 1
    }
    Write-Output "[OK] Toan bo TONY process da dung."
    exit 0
}

if ($targets) {
    foreach ($p in $targets) {
        $cl = ($p.CommandLine -replace '\s+', ' ')
        if ($cl.Length -gt 90) { $cl = $cl.Substring(0, 90) }
        Write-Output ("   Stopping PID " + $p.ProcessId + " :: " + $cl)
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Output "   Khong co TONY process nao dang chay."
}
exit 0
