# Create Desktop Shortcuts for TONY
$WshShell = New-Object -ComObject WScript.Shell

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
Write-Host "Desktop shortcuts created successfully!" -ForegroundColor Cyan
Write-Host "Double-click to start/stop TONY Assistant" -ForegroundColor Cyan