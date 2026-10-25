"""QUAN AI BRAIN 24/7 Manual Setup Instructions.

Run this script to generate setup instructions for Windows.

Usage:
    python tools/manual_24_7_setup.py
"""
import os
from pathlib import Path


def main() -> int:
    """Print manual setup instructions."""
    base_dir = r"E:\AI\QUAN AI BRAIN"
    venv_python = r"C:\Users\DELL\.venv\Scripts\python.exe"
    watchdog = os.path.join(base_dir, "tools", "watchdog.py")
    backup_script = os.path.join(base_dir, "tools", "backup_database.py")
    
    print("=" * 70)
    print("QUAN AI BRAIN 24/7 MANUAL SETUP INSTRUCTIONS")
    print("=" * 70)
    
    print("\n📋 STEP 1: ENABLE WATCHDOG (Auto-restart on crash)")
    print("-" * 70)
    print("Option A: Using Task Scheduler (Recommended)")
    print("  1. Open Task Scheduler (taskschd.msc)")
    print("  2. Click 'Create Task' (not 'Create Basic Task')")
    print("  3. General tab:")
    print("     - Name: QUAN_AIBRAIN_Watchdog")
    print("     - Run whether user is logged on or not")
    print("     - Run with highest privileges")
    print("  4. Triggers tab:")
    print("     - New... → Begin the task: At logon")
    print("     - Delay: 5 minutes")
    print("  5. Actions tab:")
    print("     - New... → Action: Start a program")
    print(f"     - Program: {venv_python}")
    print(f"     - Arguments: \"{watchdog}\"")
    print("  6. Conditions tab:")
    print("     - Uncheck 'Start only if on AC power'")
    print("  7. Settings tab:")
    print("     - Check 'Allow task to be run on demand'")
    print("     - Check 'If the task fails, restart every: 1 minute'")
    print("     - Set 'Attempt to restart up to: 3 times'")
    print("  8. Click OK, enter your password")
    
    print("\n" + "-" * 70)
    print("Option B: Using NSSM (More robust)")
    print("  1. Download NSSM: https://nssm.cc/download")
    print("  2. Extract to C:\\nssm\\nssm-2.24\\win64\\")
    print("  3. Open CMD as Administrator")
    print(f"  4. Run: C:\\nssm\\nssm-2.24\\win64\\nssm.exe install QUAN_AIBRAIN")
    print("  5. In GUI:")
    print(f"     - Application path: {venv_python}")
    print(f"     - Startup directory: {base_dir}")
    print(f"     - Arguments: tools\\watchdog.py")
    print("     - I/O tab: Redirect stdout/stderr to logs/")
    print("  6. Click 'Install service'")
    print("  7. Run: nssm start QUAN_AIBRAIN")
    print("  8. Run: nssm set QUAN_AIBRAIN Start SERVICE_AUTO_START")
    
    print("\n📋 STEP 2: ENABLE DAILY BACKUP (2AM)")
    print("-" * 70)
    print("Option A: Using Task Scheduler")
    print("  1. Open Task Scheduler")
    print("  2. Create Task")
    print("  3. General: Name = QUAN_AIBRAIN_Backup")
    print("  4. Triggers: New... → Daily at 2:00 AM")
    print("  5. Actions: New...")
    print(f"     - Program: {venv_python}")
    print(f"     - Arguments: \"{backup_script}\"")
    print("     - Start in: E:\\AI\\QUAN AI BRAIN")
    print("  6. Click OK")
    
    print("\n" + "-" * 70)
    print("Option B: Using PowerShell Script")
    print("  1. Create file: C:\\Scripts\\backup_quan_ai_brain.ps1")
    print("  2. Paste content:")
    print("""
# Backup script for QUAN AI BRAIN
$baseDir = \"E:\\AI\\QUAN AI BRAIN\"
$dbPath = \"$baseDir\\data\\brain.db\"
$backupDir = \"$baseDir\\backups\"
$timestamp = Get-Date -Format \"yyyy-MM-dd_HHmmss\"
$backupFile = \"$backupDir\\brain_$timestamp.db\"

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item $dbPath $backupFile

# Keep only last 30 backups
Get-ChildItem \"$backupDir\\brain_*.db\" | Sort-Object LastWriteTime -Descending | Select-Object -SkipFirst 30 | Remove-Item
    """)
    print("  3. Open Task Scheduler")
    print("  4. Create Task → Daily at 2AM")
    print("  5. Action: Program = powershell.exe")
    print("     Arguments: -ExecutionPolicy Bypass -File C:\\Scripts\\backup_quan_ai_brain.ps1")
    
    print("\n📋 STEP 3: VERIFY SETUP")
    print("-" * 70)
    print("  1. Check Task Scheduler:")
    print("     - taskschd.msc")
    print("     - Look for: QUAN_AIBRAIN_Watchdog, QUAN_AIBRAIN_Backup")
    print("  2. Check logs:")
    print(f"     - {base_dir}\\logs\\watchdog.log")
    print(f"     - {base_dir}\\logs\\resource_monitor.log")
    print("  3. Check backups:")
    print(f"     - {base_dir}\\backups\\")
    print("  4. Open health dashboard:")
    print("     - http://127.0.0.1:8765/health_dashboard.html")
    
    print("\n📋 STEP 4: MONITORING")
    print("-" * 70)
    print("  - Watchdog log: " + os.path.join(base_dir, "logs", "watchdog.log"))
    print("  - Resource monitor: " + os.path.join(base_dir, "logs", "resource_monitor.log"))
    print("  - Health dashboard: http://127.0.0.1:8765/health_dashboard.html")
    print("  - Task Scheduler: taskschd.msc")
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE - Follow steps above to enable 24/7 operation")
    print("=" * 70)
    
    # Save to file
    output_file = os.path.join(base_dir, "docs", "24_7_SETUP_INSTRUCTIONS.md")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# QUAN AI BRAIN 24/7 Setup Instructions\n\n")
        f.write("Follow these steps to enable 24/7 operation:\n\n")
        f.write("## Step 1: Enable Watchdog\n")
        f.write("See Option A or Option B above.\n\n")
        f.write("## Step 2: Enable Daily Backup\n")
        f.write("See Option A or Option B above.\n\n")
        f.write("## Step 3: Verify Setup\n")
        f.write("Check Task Scheduler and logs.\n\n")
        f.write("## Step 4: Monitoring\n")
        f.write("Open health dashboard and check logs regularly.\n")
    
    print(f"\n📄 Instructions saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())