$ErrorActionPreference = 'SilentlyContinue'

Write-Output '===== 1. INTEGRITY O C (FSUTIL + CHKDSK dirty bit) ====='
fsutil dirty query C:
Write-Output ('FSUTIL USN: ' + (fsutil fsinfo volumeInfo C: | Select-String 'NTFS|Version').ToString().Trim())

Write-Output ''
Write-Output '===== 2. SMART / DISK ====='
Get-PhysicalDisk | ForEach-Object {
  $wa = $_ | Get-StorageReliabilityCounter
  Write-Output ("{0} | Health={1} | Temp={2}C | Wear={3}%" -f $_.FriendlyName, $_.HealthStatus, $wa.Temperature, $wa.Wear)
}
Write-Output '--- chkdsk read-only NTA... can admin, bo qua trong phien nay ---'

Write-Output ''
Write-Output '===== 3. TRIM / OPTIMIZE VOLUME ====='
Get-Volume | Where-Object DriveLetter -in 'C','E' | ForEach-Object {
  Write-Output ("O {0}: FileSystem={1} Health={2}" -f $_.DriveLetter, $_.FileSystemType, $_.OperationalStatus)
}
