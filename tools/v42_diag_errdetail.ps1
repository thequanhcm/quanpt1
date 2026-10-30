$ErrorActionPreference = 'SilentlyContinue'
Write-Output '===== CHI TIET LOI DISK (7 ngay) ====='
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='disk'; Level=1,2; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 3 |
  ForEach-Object { Write-Output ("[{0}] {1}" -f $_.TimeCreated, ($_.Message -replace "`r`n", ' ').Substring(0, [Math]::Min(220, $_.Message.Length))) }

Write-Output ''
Write-Output '===== CHI TIET NVLDDMKM (GPU) ====='
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='nvlddmkm'; Level=1,2,3; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 3 |
  ForEach-Object { Write-Output ("[{0}] {1}" -f $_.TimeCreated, ($_.Message -replace "`r`n", ' ').Substring(0, [Math]::Min(220, $_.Message.Length))) }

Write-Output ''
Write-Output '===== SCM 30 LOI: NHOM THEO SERVICE ====='
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'; Level=2; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 40 |
  Group-Object { if ($_.Message -match 'service terminated|dich vu') { ($_.Message -split '\s{2,}')[0] } else { $_.Message.Substring(0,[Math]::Min(60,$_.Message.Length)) } } |
  Sort-Object Count -Descending | Select-Object -First 6 |
  ForEach-Object { Write-Output ("  x{0}: {1}" -f $_.Count, ($_.Name -replace "`r`n", ' ').Substring(0, [Math]::Min(110, $_.Name.Length))) }

Write-Output ''
Write-Output '===== APPLICATION ERROR 62: NHOM THEO APP ====='
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'; Level=2; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 70 |
  ForEach-Object { if ($_.Message -match 'P1: ([^,\s]+)') { $matches[1] } } |
  Group-Object | Sort-Object Count -Descending | Select-Object -First 8 |
  ForEach-Object { Write-Output ("  x{0}: {1}" -f $_.Count, $_.Name) }
