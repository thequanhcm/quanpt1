"""Resource monitor for QUAN AI BRAIN — 24/7 stability."""
import psutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = r"E:\AI\QUAN AI BRAIN"
LOG_FILE = os.path.join(BASE_DIR, "logs", "resource_monitor.log")

THRESHOLDS = {
    "cpu_percent": 80,
    "memory_percent": 80,
    "disk_percent": 80,
    "gpu_memory_percent": 85,
}

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
    disk = psutil.disk_usage("E:\AI\QUAN AI BRAIN").percent
    gpu = check_gpu()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    log_line = f"{timestamp} CPU={cpu:.1f}% MEM={memory:.1f}% DISK={disk:.1f}% GPU={gpu}%"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")
    
    # Alert if thresholds exceeded
    alerts = []
    if cpu > THRESHOLDS["cpu_percent"]:
        alerts.append(f"CPU high: {cpu:.1f}%")
    if memory > THRESHOLDS["memory_percent"]:
        alerts.append(f"Memory high: {memory:.1f}%")
    if disk > THRESHOLDS["disk_percent"]:
        alerts.append(f"Disk high: {disk:.1f}%")
    if gpu and gpu > THRESHOLDS["gpu_memory_percent"]:
        alerts.append(f"GPU memory high: {gpu:.1f}%")
    
    if alerts:
        print(f"⚠️ ALERT: {', '.join(alerts)}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"ALERT: {', '.join(alerts)}\n")

if __name__ == "__main__":
    main()
