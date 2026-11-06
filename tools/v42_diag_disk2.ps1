$ErrorActionPreference = 'SilentlyContinue'
Write-Output '===== HARD DISK 2 (bad block 25/10) la o nao? ====='
Get-CimInstance Win32_DiskDrive | ForEach-Object {
  Write-Output ("Index={0} | {1} | {2} GB | Interface={3}" -f $_.Index, $_.Model, [math]::Round($_.Size/1GB), $_.InterfaceType)
}
Write-Output ''
Write-Output '===== AUTODESK LICENSING (service loi x7) ====='
Get-CimInstance Win32_Service -Filter "Name='AdskLicensingService'" | ForEach-Object {
  Write-Output ("{0}: StartMode={1} State={2}" -f $_.Name, $_.StartMode, $_.State)
}
Write-Output ''
Write-Output '===== EDGE AUTO-LAUNCH (Run key HKCU) ====='
$v = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run').'MicrosoftEdgeAutoLaunch_6B770857D9B81538FA9524CBB2D560C5'
Write-Output ("Gia tri: " + $v)
