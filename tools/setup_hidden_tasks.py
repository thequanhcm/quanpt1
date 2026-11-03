"""Setup Task Scheduler tasks with hidden windows.

Creates tasks that run without visible console windows.
"""
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
VENV_PYTHON = WORKSPACE / ".venv" / "Scripts" / "python.exe"

TASKS = [
    {
        "name": "QUAN-AI-BRAIN-Server",
        "script": "tools/server.py",
        "description": "QUAN AI BRAIN Main Server (port 8765)"
    },
    {
        "name": "QUAN-AI-BRAIN-Watchdog",
        "script": "tools/watchdog.py",
        "description": "QUAN AI BRAIN Watchdog (port 17236)"
    },
    {
        "name": "QUAN-AI-BRAIN-Learning",
        "script": "tools/learning.py",
        "description": "QUAN AI BRAIN Learning Engine (port 7724)"
    },
    {
        "name": "QUAN-AI-BRAIN-Responder",
        "script": "tools/netchat_auto_responder.py",
        "description": "QUAN AI BRAIN NetChat Bot"
    },
    {
        "name": "QUAN-AI-BRAIN-Dashboard",
        "script": "edge_client/main.py",
        "description": "QUAN AI BRAIN Dashboard (port 8766)"
    }
]

def create_hidden_task(task_name: str, script_path: str, description: str):
    """Create a Task Scheduler task that runs hidden."""
    
    script_full_path = WORKSPACE / script_path
    
    # Use PowerShell to start process with hidden window
    # -WindowStyle Hidden ensures no console window appears
    command = f'Start-Process "{VENV_PYTHON}" -ArgumentList "{script_full_path}" -WindowStyle Hidden -NoNewWindow'
    
    # Build schtasks command
    # /SC ONSTART - Run at startup
    # /RL HIGHEST - Run with highest privileges
    # /F - Force overwrite if exists
    schtasks_cmd = [
        "schtasks",
        "/Create",
        "/TN", task_name,
        "/TR", f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{command}"',
        "/SC", "ONSTART",
        "/RL", "HIGHEST",
        "/F",
        "/RU", "SYSTEM",
        "/Description", description
    ]
    
    try:
        result = subprocess.run(
            schtasks_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ {task_name} created (hidden)")
            return True
        else:
            print(f"❌ {task_name} failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ {task_name} error: {e}")
        return False

def main():
    """Create all hidden tasks."""
    print("=" * 60)
    print("QUAN AI BRAIN — Setup Hidden Tasks")
    print("=" * 60)
    print()
    
    # Check admin privileges
    try:
        subprocess.run(["net", "session"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Please run this script as Administrator!")
        print("Right-click and select 'Run as administrator'")
        input("Press Enter to exit...")
        sys.exit(1)
    
    print("✅ Running as Administrator")
    print()
    print("Creating hidden tasks...")
    print()
    
    created = 0
    failed = 0
    
    for task in TASKS:
        if create_hidden_task(task["name"], task["script"], task["description"]):
            created += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Summary: {created}/5 created, {failed} failed")
    print("=" * 60)
    print()
    
    if created == 5:
        print("✅ All tasks configured (hidden mode)")
        print()
        print("Next: Reboot to test auto-start")
        print("Or run: python tools\\health_check.py")
    else:
        print("⚠️ Some tasks failed. Check errors above.")
    
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()