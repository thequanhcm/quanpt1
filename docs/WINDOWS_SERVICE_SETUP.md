# Windows Service Setup Guide — QUAN AI BRAIN

## Overview

This guide sets up QUAN AI BRAIN to run as Windows services with auto-start on boot.

## Prerequisites

- Windows 10/11
- Administrator privileges
- Python 3.11+ with virtual environment

## Installation

### Step 1: Run Setup Script (Administrator Required)

```cmd
# Right-click and "Run as administrator"
tools\setup_windows_services.bat
```

This will:
- Create 5 Task Scheduler tasks
- Configure auto-start on boot
- Set up recovery options (auto-restart on failure)
- Test all tasks

### Step 2: Verify Setup

```cmd
# Check all tasks
schtasks /Query /TN "QUAN-AI-BRAIN-*"

# Or use health check
python tools\health_check.py
```

### Step 3: Start Services

```cmd
# Option 1: Reboot PC (services auto-start)
# Option 2: Start manually
tools\start_services.bat
```

## Management Commands

### List Services

```cmd
schtasks /Query /TN "QUAN-AI-BRAIN-*" /V
```

### Start All Services

```cmd
tools\start_services.bat
```

### Stop All Services

```cmd
tools\stop_services.bat
```

### Remove All Services

```cmd
tools\remove_services.bat
```

### Check Health

```cmd
python tools\health_check.py
```

## Services Created

| Task Name | Process | Port | Description |
|-----------|---------|------|-------------|
| QUAN-AI-BRAIN-Server | server.py | 8765 | Core API server |
| QUAN-AI-BRAIN-Watchdog | watchdog.py | 17236 | Health monitoring |
| QUAN-AI-BRAIN-Learning | learning_daemon.py | 7724 | Background learning |
| QUAN-AI-BRAIN-Responder | netchat_auto_responder.py | - | NetChat bot |
| QUAN-AI-BRAIN-Dashboard | edge_client/main.py | 8766 | Executive dashboard |

## Configuration

### Task Scheduler Settings

- **Trigger:** ONSTART (Windows boot)
- **User:** SYSTEM (highest privileges)
- **Restart:** On failure (1 attempt, 60s delay)
- **Run:** Hidden (no console window)

### Logs

All services log to `logs/` directory:
- `server.log`
- `watchdog.log`
- `learning.log`
- `responder.log`
- `dashboard.log`
- `audit.log`

Log rotation: 5 files, 10MB each

## Troubleshooting

### Services Not Starting

1. Check Task Scheduler:
   ```cmd
   schtasks /Query /TN "QUAN-AI-BRAIN-Server" /V
   ```

2. Check logs:
   ```cmd
   type logs\server.log
   ```

3. Re-run setup as administrator

### Permission Issues

- Ensure running as Administrator
- Check Windows Security logs
- Verify Python path is correct

### Port Conflicts

- Check if ports are in use:
  ```cmd
  netstat -ano | findstr :8765
  ```

- Kill conflicting process or change port in config

## Recovery Options

### Auto-restart on Failure

All tasks configured to:
- Restart once after 60 seconds on failure
- Run with highest privileges
- Run as SYSTEM account

### Manual Recovery

1. Stop all services:
   ```cmd
   tools\stop_services.bat
   ```

2. Fix the issue

3. Start services:
   ```cmd
   tools\start_services.bat
   ```

4. Check health:
   ```cmd
   python tools\health_check.py
   ```

## Security Notes

- Services run as SYSTEM (highest privileges)
- Logs may contain sensitive data - protect `logs/` directory
- Audit log tracks all administrative actions
- STOP/FREEZE commands available for emergency halt

## Uninstall

```cmd
# Remove all tasks
tools\remove_services.bat

# Or manually:
schtasks /Delete /TN "QUAN-AI-BRAIN-Server" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Watchdog" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Learning" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Responder" /F
schtasks /Delete /TN "QUAN-AI-BRAIN-Dashboard" /F
```

## Next Steps

After setup:
1. ✅ Verify all services are running
2. ✅ Check health check passes
3. ✅ Test auto-start by rebooting PC
4. ✅ Monitor logs for first 24 hours
5. ✅ Configure log rotation if needed

---

**Status:** Ready for deployment  
**Last updated:** 2026-10-28