Write-Output '=== OutOfMemory trong .NET Runtime log ==='
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='.NET Runtime'} -MaxEvents 15 -ErrorAction SilentlyContinue |
  Where-Object { $_.Message -match 'OutOfMemory|FailFast' } |
  ForEach-Object { Write-Output ('--- ' + $_.TimeCreated); Write-Output ($_.Message.Substring(0, [Math]::Min(500, $_.Message.Length))) }
Write-Output ''
Write-Output '=== System log: Resource-Exhaustion ==='
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Resource-Exhaustion-Detector'} -MaxEvents 5 -ErrorAction SilentlyContinue |
  ForEach-Object { Write-Output ('--- ' + $_.TimeCreated); Write-Output ($_.Message.Substring(0, [Math]::Min(300, $_.Message.Length))) }
Write-Output ''
Write-Output '=== Dell services state ==='
Get-Service | Where-Object { $_.DisplayName -match 'Dell' } |
  Select-Object Status, Name, DisplayName | Format-Table -AutoSize | Out-String -Width 110
