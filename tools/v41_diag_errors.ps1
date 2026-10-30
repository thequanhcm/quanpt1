$events = Get-WinEvent -FilterHashtable @{LogName='Application'; Level=2} -MaxEvents 40 -ErrorAction SilentlyContinue
$events | Group-Object { ($_.Message -split "`n")[0].Trim() } | Sort-Object Count -Descending |
  Select-Object Count, Name | Format-Table -AutoSize | Out-String -Width 120
Write-Output "=== Dell.TechHub errors chi tiết ==="
$events | Where-Object { $_.Message -match 'Dell|DcfRedirection' } |
  Select-Object TimeCreated, @{N='Src';E={$_.ProviderName}}, @{N='Msg';E={($_.Message -split "`n")[0..2] -join ' | '}} |
  Format-Table -AutoSize | Out-String -Width 140
