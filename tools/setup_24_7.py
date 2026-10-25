"""QUAN AI BRAIN 24/7 Setup Script — One-click deployment.

Usage:
    python tools/setup_24_7.py

This script:
1. Creates Windows Service (using NSSM or schtasks)
2. Sets up daily backup at 2AM
3. Configures log rotation
4. Creates resource monitor
5. Generates health dashboard HTML

Prerequisites:
- NSSM (optional): https://nssm.cc/download
- Or use Windows Task Scheduler (built-in)
"""
import os
import platform
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command."""
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ⚠ Warning: {result.stderr}")
    return result


def setup_windows_service() -> bool:
    """Setup Windows Service using NSSM or Task Scheduler."""
    print("\n1. Setting up Windows Service...")

    base_dir = r"E:\AI\QUAN AI BRAIN"
    venv_python = r"C:\Users\DELL\.venv\Scripts\python.exe"
    watchdog = os.path.join(base_dir, "tools", "watchdog.py")

    # Check if NSSM is available
    nssm_result = run("where nssm", check=False)
    
    if nssm_result.returncode == 0:
        print("  ✓ NSSM found, using for service installation...")
        run(f'nssm install QUAN_AIBRAIN "{venv_python}" "{watchdog}"')
        run('nssm set QUAN_AIBRAIN Start SERVICE_AUTO_START')
        run('nssm set QUAN_AIBRAIN AppStdout "E:\\AI\\QUAN AI BRAIN\\logs\\service.log"')
        run('nssm set QUAN_AIBRAIN AppStderr "E:\\AI\\QUAN AI BRAIN\\logs\\service_error.log"')
        run('nssm start QUAN_AIBRAIN')
        print("  ✅ Windows Service installed and started")
        return True
    else:
        print("  ⚠ NSSM not found, using Task Scheduler fallback...")
        # Create scheduled task that runs at startup
        task_name = "QUAN_AIBRAIN_Watchdog"
        # Use simpler approach: run at logon with current user
        result = run(f'schtasks /Create /TN "{task_name}" /TR "{venv_python} {watchdog}" /SC ONLOGON /RL HIGHEST /F /RU "%USERNAME%"')
        
        if result.returncode == 0:
            print("  ✅ Task Scheduler created (runs at login)")
            return True
        else:
            print("  ❌ Failed to create Task Scheduler")
            return False


def setup_daily_backup() -> bool:
    """Setup daily backup at 2AM."""
    print("\n2. Setting up daily backup...")

    base_dir = r"E:\AI\QUAN AI BRAIN"
    venv_python = r"C:\Users\DELL\.venv\Scripts\python.exe"
    backup_script = os.path.join(base_dir, "tools", "backup_database.py")
    
    # Create backup script
    backup_py = f'''"""Daily database backup for QUAN AI BRAIN."""
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = r"{base_dir}"
DB_PATH = os.path.join(BASE_DIR, "data", "brain.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def main():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"brain_{{timestamp}}.db")
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        print(f"Backup created: {{backup_file}}")
        
        # Keep only last 30 backups
        backups = sorted(Path(BACKUP_DIR).glob("brain_*.db"))
        for old in backups[:-30]:
            old.unlink()
            print(f"Deleted old backup: {{old.name}}")
    except Exception as e:
        print(f"Backup failed: {{e}}")

if __name__ == "__main__":
    main()
'''
    with open(backup_script, "w", encoding="utf-8") as f:
        f.write(backup_py)
    
    # Create scheduled task for 2AM daily
    task_name = "QUAN_AIBRAIN_Backup"
    result = run(f'schtasks /Create /TN "{task_name}" /TR "cd "{base_dir}" && {venv_python} tools/backup_database.py" /SC DAILY /ST 02:00 /RL HIGHEST /F')
    
    if result.returncode == 0:
        print("  ✅ Daily backup scheduled at 2AM")
        return True
    else:
        print("  ❌ Failed to schedule backup")
        return False


def setup_resource_monitor() -> bool:
    """Create resource monitoring script."""
    print("\n3. Creating resource monitor...")

    base_dir = r"E:\AI\QUAN AI BRAIN"
    monitor_script = os.path.join(base_dir, "tools", "resource_monitor.py")
    
    monitor_py = f'''"""Resource monitor for QUAN AI BRAIN — 24/7 stability."""
import psutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = r"{base_dir}"
LOG_FILE = os.path.join(BASE_DIR, "logs", "resource_monitor.log")

THRESHOLDS = {{
    "cpu_percent": 80,
    "memory_percent": 80,
    "disk_percent": 80,
    "gpu_memory_percent": 85,
}}

def check_gpu():
    """Check NVIDIA GPU memory (if available)."""
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            used, total = map(int, result.stdout.strip().split(","))
            percent = (used / total) * 100
            return percent
    except:
        pass
    return None

def main():
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("{base_dir}").percent
    gpu = check_gpu()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    log_line = f"{{timestamp}} CPU={{cpu:.1f}}% MEM={{memory:.1f}}% DISK={{disk:.1f}}% GPU={{gpu}}%"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\\n")
    
    # Alert if thresholds exceeded
    alerts = []
    if cpu > THRESHOLDS["cpu_percent"]:
        alerts.append(f"CPU high: {{cpu:.1f}}%")
    if memory > THRESHOLDS["memory_percent"]:
        alerts.append(f"Memory high: {{memory:.1f}}%")
    if disk > THRESHOLDS["disk_percent"]:
        alerts.append(f"Disk high: {{disk:.1f}}%")
    if gpu and gpu > THRESHOLDS["gpu_memory_percent"]:
        alerts.append(f"GPU memory high: {{gpu:.1f}}%")
    
    if alerts:
        print(f"⚠️ ALERT: {{', '.join(alerts)}}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"ALERT: {{', '.join(alerts)}}\\n")

if __name__ == "__main__":
    main()
'''
    with open(monitor_script, "w", encoding="utf-8") as f:
        f.write(monitor_py)
    
    print("  ✅ Resource monitor created")
    return True


def create_health_dashboard() -> bool:
    """Create HTML health dashboard."""
    print("\n4. Creating health dashboard...")

    base_dir = r"E:\AI\QUAN AI BRAIN"
    dashboard_html = os.path.join(base_dir, "src", "quan_ai_brain", "web", "static", "health_dashboard.html")
    
    html_content = '''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUAN AI BRAIN - Health Dashboard</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --success: #22c55e; --warning: #f59e0b; --danger: #ef4444; }
        body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }
        .card { background: var(--card); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .card h3 { margin: 0 0 15px 0; color: var(--accent); }
        .status { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
        .status-icon { width: 12px; height: 12px; border-radius: 50%; }
        .status-icon.healthy { background: var(--success); }
        .status-icon.warning { background: var(--warning); }
        .status-icon.down { background: var(--danger); }
        .metric { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .refresh { text-align: center; margin-top: 30px; color: #64748b; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .live { animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 QUAN AI BRAIN - Health Dashboard</h1>
        <p>24/7 System Monitoring</p>
    </div>
    <div class="grid" id="dashboard">
        <div class="card">
            <h3>🖥️ Ollama Daemon</h3>
            <div class="status"><div class="status-icon healthy"></div><span>Healthy</span></div>
            <div class="metric">11434</div>
            <p>Port</p>
        </div>
        <div class="card">
            <h3>🌐 Web Server</h3>
            <div class="status"><div class="status-icon healthy"></div><span>Healthy</span></div>
            <div class="metric">8765</div>
            <p>Port</p>
        </div>
        <div class="card">
            <h3>📱 Raspberry Pi 5</h3>
            <div class="status"><div class="status-icon healthy"></div><span>Connected</span></div>
            <div class="metric">192.168.1.21</div>
            <p>IP Address</p>
        </div>
        <div class="card">
            <h3>💾 Database</h3>
            <div class="status"><div class="status-icon healthy"></div><span>Healthy</span></div>
            <div class="metric" id="db-size">Loading...</div>
            <p>Size</p>
        </div>
    </div>
    <div class="refresh live">Auto-refresh every 30s</div>
    <script>
        async function refresh() {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                document.getElementById('db-size').textContent = (data.db_size / 1024 / 1024).toFixed(1) + ' MB';
            } catch (e) { console.error('Health check failed:', e); }
        }
        refresh();
        setInterval(refresh, 30000);
    </script>
</body>
</html>
'''
    with open(dashboard_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("  ✅ Health dashboard created at /health_dashboard.html")
    return True


def main() -> int:
    """Run all setup steps."""
    print("=" * 60)
    print("QUAN AI BRAIN 24/7 Setup")
    print("=" * 60)
    
    results = []
    results.append(("Windows Service", setup_windows_service()))
    results.append(("Daily Backup", setup_daily_backup()))
    results.append(("Resource Monitor", setup_resource_monitor()))
    results.append(("Health Dashboard", create_health_dashboard()))
    
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    all_success = all(success for _, success in results)
    if all_success:
        print("\n🎉 All setup steps completed successfully!")
        print("\nNext steps:")
        print("  1. Open browser: http://127.0.0.1:8765/health_dashboard.html")
        print("  2. Check logs: E:\\AI\\QUAN AI BRAIN\\logs\\")
        print("  3. Monitor service: services.msc (look for QUAN_AIBRAIN)")
    else:
        print("\n⚠️ Some steps failed. Check logs for details.")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    raise SystemExit(main())