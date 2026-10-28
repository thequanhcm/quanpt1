# Create Desktop Shortcuts for TONY Assistant
$WshShell = New-Object -ComObject WScript.Shell

# Start Shortcut
$startShortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\🚀 START TONY.lnk")
$startShortcut.TargetPath = "E:\AI\QUAN AI BRAIN\START_ALL_ONECLICK.bat"
$startShortcut.WorkingDirectory = "E:\AI\QUAN AI BRAIN"
$startShortcut.Description = "Start all QUAN AI BRAIN services"
$startShortcut.IconLocation = "shell32.dll,238"
$startShortcut.Save()

Write-Host "✅ Created: 🚀 START TONY.lnk" -ForegroundColor Green

# Stop Shortcut
$stopShortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\🛑 STOP TONY.lnk")
$stopShortcut.TargetPath = "E:\AI\QUAN AI BRAIN\STOP_ALL_ONECLICK.bat"
$stopShortcut.WorkingDirectory = "E:\AI\QUAN AI BRAIN"
$stopShortcut.Description = "Stop all QUAN AI BRAIN services"
$stopShortcut.IconLocation = "shell32.dll,25"
$stopShortcut.Save()

Write-Host "✅ Created: 🛑 STOP TONY.lnk" -ForegroundColor Green

Write-Host ""
Write-Host "Desktop shortcuts created successfully!" -ForegroundColor Cyan
Write-Host "You can now double-click the icons on your Desktop." -ForegroundColor Cyan