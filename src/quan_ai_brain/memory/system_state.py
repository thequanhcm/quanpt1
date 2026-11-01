"""System State - System health and status monitoring.

Provides:
- System health monitoring (CPU, memory, disk)
- Service status tracking
- Health check endpoints
- Historical health data
"""
from __future__ import annotations

import json
import sqlite3
import psutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pathlib import Path


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


@dataclass
class SystemMetrics:
    """System resource metrics."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    active_processes: int
    health_status: HealthStatus
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SystemMetrics':
        return cls(**data)


@dataclass
class ServiceStatus:
    """Service status information."""
    service_name: str
    status: str  # 'running', 'stopped', 'error', 'unknown'
    pid: int | None
    uptime_seconds: float | None
    last_check: str
    error_message: str | None = None
    metadata_json: str = field(default_factory=lambda: '{}')
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ServiceStatus':
        return cls(**data)


class SystemStateMonitor:
    """Monitor system health and status."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
        self._services: dict[str, dict] = {}  # Track known services
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize system state tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # System metrics history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_percent REAL NOT NULL,
                memory_used_gb REAL NOT NULL,
                memory_total_gb REAL NOT NULL,
                disk_percent REAL NOT NULL,
                disk_used_gb REAL NOT NULL,
                disk_total_gb REAL NOT NULL,
                active_processes INTEGER NOT NULL,
                health_status TEXT NOT NULL
            )
        """)
        
        # Service status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_status (
                service_name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                pid INTEGER,
                uptime_seconds REAL,
                last_check TEXT NOT NULL,
                error_message TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Health check log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_check_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_time TEXT NOT NULL,
                overall_status TEXT NOT NULL,
                cpu_status TEXT,
                memory_status TEXT,
                disk_status TEXT,
                services_status TEXT,
                issues_json TEXT NOT NULL DEFAULT '[]'
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_time 
            ON system_metrics(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_time 
            ON health_check_log(check_time)
        """)
        
        conn.commit()
        conn.close()
    
    def register_service(self, service_name: str, 
                        check_command: str | None = None,
                        metadata: dict | None = None):
        """Register a service to monitor."""
        self._services[service_name] = {
            'check_command': check_command,
            'metadata': metadata or {}
        }
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        now = datetime.now(timezone.utc).isoformat()
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        
        # Processes
        active_processes = len(psutil.pids())
        
        # Determine health status
        health_status = self._calculate_health_status(
            cpu_percent, memory_percent, disk_percent
        )
        
        metrics = SystemMetrics(
            timestamp=now,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=round(memory_used_gb, 2),
            memory_total_gb=round(memory_total_gb, 2),
            disk_percent=disk_percent,
            disk_used_gb=round(disk_used_gb, 2),
            disk_total_gb=round(disk_total_gb, 2),
            active_processes=active_processes,
            health_status=health_status
        )
        
        # Store metrics
        self._store_metrics(metrics)
        
        return metrics
    
    def _calculate_health_status(self, cpu: float, memory: float, 
                                 disk: float) -> HealthStatus:
        """Calculate overall health status from metrics."""
        issues = 0
        
        # CPU thresholds
        if cpu > 90:
            issues += 2
        elif cpu > 75:
            issues += 1
        
        # Memory thresholds
        if memory > 90:
            issues += 2
        elif memory > 75:
            issues += 1
        
        # Disk thresholds
        if disk > 95:
            issues += 2
        elif disk > 85:
            issues += 1
        
        if issues >= 4:
            return HealthStatus.UNHEALTHY
        elif issues >= 2:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_metrics 
            (timestamp, cpu_percent, memory_percent, memory_used_gb, 
             memory_total_gb, disk_percent, disk_used_gb, disk_total_gb,
             active_processes, health_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.timestamp,
            metrics.cpu_percent,
            metrics.memory_percent,
            metrics.memory_used_gb,
            metrics.memory_total_gb,
            metrics.disk_percent,
            metrics.disk_used_gb,
            metrics.disk_total_gb,
            metrics.active_processes,
            metrics.health_status.value
        ))
        
        conn.commit()
        conn.close()
    
    def check_service(self, service_name: str) -> ServiceStatus:
        """Check status of a specific service."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Try to find process by name
        pid = None
        status = 'unknown'
        uptime = None
        error_msg = None
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if service_name.lower() in proc.info['name'].lower():
                    pid = proc.info['pid']
                    status = 'running'
                    
                    # Calculate uptime
                    try:
                        create_time = proc.create_time()
                        uptime = (datetime.now().timestamp() - create_time)
                    except:
                        uptime = None
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if status == 'unknown':
            status = 'stopped'
        
        service_status = ServiceStatus(
            service_name=service_name,
            status=status,
            pid=pid,
            uptime_seconds=round(uptime, 2) if uptime else None,
            last_check=now,
            error_message=error_msg
        )
        
        # Store in database
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO service_status 
            (service_name, status, pid, uptime_seconds, last_check, 
             error_message, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            service_status.service_name,
            service_status.status,
            service_status.pid,
            service_status.uptime_seconds,
            service_status.last_check,
            service_status.error_message,
            service_status.metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        return service_status
    
    def check_all_services(self) -> list[ServiceStatus]:
        """Check all registered services."""
        statuses = []
        for service_name in self._services:
            status = self.check_service(service_name)
            statuses.append(status)
        return statuses
    
    def run_health_check(self) -> dict[str, Any]:
        """Run comprehensive health check."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Get metrics
        metrics = self.get_current_metrics()
        
        # Check services
        service_statuses = self.check_all_services()
        
        # Determine individual statuses
        cpu_status = 'ok' if metrics.cpu_percent < 75 else 'warning'
        if metrics.cpu_percent > 90:
            cpu_status = 'critical'
        
        memory_status = 'ok' if metrics.memory_percent < 75 else 'warning'
        if metrics.memory_percent > 90:
            memory_status = 'critical'
        
        disk_status = 'ok' if metrics.disk_percent < 85 else 'warning'
        if metrics.disk_percent > 95:
            disk_status = 'critical'
        
        services_status = 'ok'
        running_count = sum(1 for s in service_statuses if s.status == 'running')
        if running_count < len(service_statuses) * 0.5:
            services_status = 'critical'
        elif running_count < len(service_statuses):
            services_status = 'warning'
        
        # Collect issues
        issues = []
        if cpu_status != 'ok':
            issues.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        if memory_status != 'ok':
            issues.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        if disk_status != 'ok':
            issues.append(f"Low disk space: {metrics.disk_percent:.1f}%")
        
        for service in service_statuses:
            if service.status != 'running':
                issues.append(f"Service {service.service_name}: {service.status}")
        
        # Overall status
        overall_status = metrics.health_status.value
        
        # Log health check
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO health_check_log 
            (check_time, overall_status, cpu_status, memory_status, 
             disk_status, services_status, issues_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            overall_status,
            cpu_status,
            memory_status,
            disk_status,
            services_status,
            json.dumps(issues)
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'timestamp': now,
            'overall_status': overall_status,
            'metrics': metrics.to_dict(),
            'cpu_status': cpu_status,
            'memory_status': memory_status,
            'disk_status': disk_status,
            'services_status': services_status,
            'services': [s.to_dict() for s in service_statuses],
            'issues': issues
        }
    
    def get_metrics_history(self, hours: int = 24, 
                           limit: int = 100) -> list[SystemMetrics]:
        """Get historical metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, cpu_percent, memory_percent, memory_used_gb,
                   memory_total_gb, disk_percent, disk_used_gb, disk_total_gb,
                   active_processes, health_status
            FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append(SystemMetrics(
                timestamp=row['timestamp'],
                cpu_percent=row['cpu_percent'],
                memory_percent=row['memory_percent'],
                memory_used_gb=row['memory_used_gb'],
                memory_total_gb=row['memory_total_gb'],
                disk_percent=row['disk_percent'],
                disk_used_gb=row['disk_used_gb'],
                disk_total_gb=row['disk_total_gb'],
                active_processes=row['active_processes'],
                health_status=HealthStatus(row['health_status'])
            ))
        
        conn.close()
        return list(reversed(metrics))
    
    def get_health_history(self, hours: int = 24,
                          limit: int = 100) -> list[dict[str, Any]]:
        """Get health check history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT check_time, overall_status, cpu_status, memory_status,
                   disk_status, services_status, issues_json
            FROM health_check_log
            ORDER BY check_time DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'check_time': row['check_time'],
                'overall_status': row['overall_status'],
                'cpu_status': row['cpu_status'],
                'memory_status': row['memory_status'],
                'disk_status': row['disk_status'],
                'services_status': row['services_status'],
                'issues': json.loads(row['issues_json'])
            })
        
        conn.close()
        return history
    
    def get_statistics(self) -> dict[str, Any]:
        """Get system state statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Average metrics (last 100 entries)
        cursor.execute("""
            SELECT AVG(cpu_percent), AVG(memory_percent), AVG(disk_percent)
            FROM (SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT 100)
        """)
        row = cursor.fetchone()
        stats['avg_cpu'] = round(row[0] or 0, 2)
        stats['avg_memory'] = round(row[1] or 0, 2)
        stats['avg_disk'] = round(row[2] or 0, 2)
        
        # Health status distribution
        cursor.execute("""
            SELECT health_status, COUNT(*) 
            FROM system_metrics 
            GROUP BY health_status
        """)
        stats['health_distribution'] = {
            row[0]: row[1] for row in cursor.fetchall()
        }
        
        # Total health checks
        cursor.execute("SELECT COUNT(*) FROM health_check_log")
        stats['total_health_checks'] = cursor.fetchone()[0]
        
        conn.close()
        return stats