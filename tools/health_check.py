"""Health check for all QUAN AI BRAIN services."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

def check_process(name: str, port: int = None):
    """Check if a process is running."""
    try:
        # Windows tasklist command
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq python.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if name in result.stdout:
            status = "✅ ONLINE"
            running = True
        else:
            status = "❌ OFFLINE"
            running = False
            
        # Check port if provided
        port_status = ""
        if port and running:
            port_result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if f":{port}" in port_result.stdout:
                port_status = f" (port {port} listening)"
            else:
                port_status = f" (port {port} NOT listening)"
                running = False
                
        return status + port_status, running
    except Exception as e:
        return f"⚠️ Error: {e}", False


def check_task(name: str):
    """Check Task Scheduler task status."""
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", name, "/FO", "CSV"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            # Parse CSV
            parts = lines[1].split(',')
            if len(parts) > 2:
                status = parts[2].strip().strip('"')
                if "Ready" in status or "Running" in status:
                    return "✅ Task configured", True
                else:
                    return f"⚠️ Task status: {status}", False
        return "❌ Task not found", False
    except Exception as e:
        return f"⚠️ Error: {e}", False


def main():
    print("=" * 60)
    print("QUAN AI BRAIN — Health Check")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Check services
    print("📊 SERVICE STATUS")
    print("-" * 60)
    
    services = [
        ("server", 8765),
        ("watchdog", 17236),
        ("learning", 7724),
        ("responder", None),
        ("dashboard", 8766),
    ]
    
    all_online = True
    for name, port in services:
        status, running = check_process(name, port)
        print(f"{name:15} {status}")
        if not running:
            all_online = False
    
    print()
    
    # Check tasks
    print("📅 TASK SCHEDULER STATUS")
    print("-" * 60)
    
    tasks = [
        "QUAN-AI-BRAIN-Server",
        "QUAN-AI-BRAIN-Watchdog",
        "QUAN-AI-BRAIN-Learning",
        "QUAN-AI-BRAIN-Responder",
        "QUAN-AI-BRAIN-Dashboard",
    ]
    
    tasks_configured = 0
    for task in tasks:
        status, configured = check_task(task)
        print(f"{task:25} {status}")
        if configured:
            tasks_configured += 1
    
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Services running: {sum(1 for s, p in services if check_process(s, p)[1])}/{len(services)}")
    print(f"Tasks configured: {tasks_configured}/{len(tasks)}")
    print(f"Overall status: {'✅ ALL ONLINE' if all_online and tasks_configured == len(tasks) else '⚠️ SOME SERVICES OFFLINE'}")
    print()
    
    # Return exit code
    return 0 if (all_online and tasks_configured == len(tasks)) else 1


if __name__ == "__main__":
    sys.exit(main())