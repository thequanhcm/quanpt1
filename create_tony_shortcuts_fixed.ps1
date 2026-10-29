# Create Desktop Shortcuts for TONY (Fixed)
$WshShell = New-Object -ComObject WScript.Shell

# Remove old shortcuts if they exist
$oldStart = "$env:USERPROFILE\Desktop\ỴẸ START TONY.lnk"
$oldStop = "$env:USERPROFILE\Desktop\ỴẸ STOP TONY.lnk"
if (Test-Path $oldStart) { Remove-Item $oldStart -Force }
if (Test-Path $oldStop) { Remove-Item $oldStop -Force }

# Start Shortcut
$startPath = "$env:USERPROFILE\Desktop\🚀 START TONY.lnk"
$startShortcut = $WshShell.CreateShortcut($startPath)
$startShortcut.TargetPath = "E:\AI\QUAN AI BRAIN\TONY_START.bat"
$startShortcut.WorkingDirectory = "E:\AI\QUAN AI BRAIN"
$startShortcut.Description = "Start TONY Assistant - All services"
$startShortcut.IconLocation = "shell32.dll,238"
$startShortcut.Save()
Write-Host "✅ Created: 🚀 START TONY.lnk" -ForegroundColor Green

# Stop Shortcut
$stopPath = "$env:USERPROFILE\Desktop\🛑 STOP TONY.lnk"
$stopShortcut = $WshShell.CreateShortcut($stopPath)
$stopShortcut.TargetPath = "E:\AI\QUAN AI BRAIN\TONY_STOP.bat"
$stopShortcut.WorkingDirectory = "E:\AI\QUAN AI BRAIN"
$stopShortcut.Description = "Stop TONY Assistant - All services"
$stopShortcut.IconLocation = "shell32.dll,25"
$stopShortcut.Save()
Write-Host "✅ Created: 🛑 STOP TONY.lnk" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Desktop shortcuts created!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 START TONY  - Double-click to start" -ForegroundColor Green
Write-Host "🛑 STOP TONY   - Double-click to stop" -ForegroundColor Red
Write-Host ""