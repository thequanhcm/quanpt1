"""Local System & OS Telemetry Connector (High-Value, Zero-Risk Read-Only Reference Connector)."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import platform
import shutil
import socket
import sys
import time
from typing import Any

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.integration.adapter import BaseConnectorAdapter, ConnectorResponse, VerificationResult
from quan_ai_brain.integration.manifest import (
    AuthType,
    AutonomyLevelScope,
    ConnectorManifest,
    ConnectorOperation,
    ConnectorType,
)


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _read_windows_ram() -> tuple[int, int, float]:
    """Read RAM metrics on Windows via kernel32 GlobalMemoryStatusEx."""
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    total_mb = int(stat.ullTotalPhys // (1024 * 1024))
    avail_mb = int(stat.ullAvailPhys // (1024 * 1024))
    load_pct = float(stat.dwMemoryLoad)
    return total_mb, avail_mb, load_pct


def _read_linux_ram() -> tuple[int, int, float]:
    """Read RAM metrics on Linux / Raspberry Pi via /proc/meminfo."""
    mem_info: dict[str, int] = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem_info[key] = int(val)
        total_kb = mem_info.get("MemTotal", 1024)
        avail_kb = mem_info.get("MemAvailable", mem_info.get("MemFree", 512))
        total_mb = total_kb // 1024
        avail_mb = avail_kb // 1024
        used_pct = round(((total_kb - avail_kb) / total_kb) * 100.0, 1)
        return total_mb, avail_mb, used_pct
    except Exception:
        return 1024, 512, 50.0


def create_system_telemetry_manifest() -> ConnectorManifest:
    """Instantiate the standard declarative manifest for System Telemetry."""
    ops = [
        ConnectorOperation(
            operation_id="get_cpu_memory",
            name="Lấy Thông Số CPU & Bộ Nhớ RAM",
            description="Đọc số lượng nhân CPU, tổng dung lượng RAM, RAM còn trống và tỷ lệ tải hệ thống",
            action_type="read",
            risk_level=RiskLevel.R0,
            autonomy_level=AutonomyLevelScope.A0_OBSERVE,
            input_schema={},
            output_schema={"type": "object", "properties": ["cpu_cores", "ram_total_mb", "ram_available_mb", "ram_used_percent"]},
            side_effects=False,
            requires_approval=False,
            supports_dry_run=True,
            timeout_seconds=5.0,
        ),
        ConnectorOperation(
            operation_id="get_disk_metrics",
            name="Kiểm Tra Dung Lượng Ổ Đĩa",
            description="Đọc tổng dung lượng, khoảng trống còn lại và tỷ lệ sử dụng ổ đĩa workspace",
            action_type="read",
            risk_level=RiskLevel.R0,
            autonomy_level=AutonomyLevelScope.A0_OBSERVE,
            input_schema={"types": {"path": str}},
            output_schema={"type": "object", "properties": ["total_gb", "free_gb", "used_percent"]},
            side_effects=False,
            requires_approval=False,
            supports_dry_run=True,
            timeout_seconds=5.0,
        ),
        ConnectorOperation(
            operation_id="get_network_info",
            name="Kiểm Tra Giao Diện Mạng Nội Bộ",
            description="Đọc tên máy tính và địa chỉ IP cục bộ được gán cho thiết bị",
            action_type="read",
            risk_level=RiskLevel.R0,
            autonomy_level=AutonomyLevelScope.A0_OBSERVE,
            input_schema={},
            output_schema={"type": "object", "properties": ["hostname", "ips"]},
            side_effects=False,
            requires_approval=False,
            supports_dry_run=True,
            timeout_seconds=5.0,
        ),
    ]

    return ConnectorManifest(
        system_id="system_telemetry",
        system_name="Giám Sát Phần Cứng & OS Cục Bộ",
        system_type=ConnectorType.SYSTEM_TELEMETRY,
        version="1.0.0",
        description="Thu thập số liệu đo lường tài nguyên CPU, RAM, Disk và Mạng của PC Core hoặc Pi 5 (chế độ chỉ đọc R0)",
        auth_type=AuthType.NONE,
        base_endpoint="local://kernel/telemetry",
        operations=ops,
        rate_limit_per_minute=300,
        timeout_seconds=5.0,
        read_only_default=True,
        environment="local",
        owner_signoff_required=False,
        metadata={"platform": platform.system(), "owner": "Quanpt1"},
    )


class SystemTelemetryConnector(BaseConnectorAdapter):
    """Reference adapter implementing System Telemetry with pure standard library."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        manifest = create_system_telemetry_manifest()
        super().__init__(manifest)
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def health_check(self) -> dict[str, Any]:
        """Fast non-destructive probe validating that telemetry queries function."""
        try:
            cores = os.cpu_count() or 1
            return {
                "healthy": True,
                "status": "HEALTHY",
                "cpu_cores": cores,
                "platform": platform.platform(),
                "hostname": socket.gethostname(),
            }
        except Exception as exc:
            return {"healthy": False, "status": "ERROR", "error": str(exc)}

    def discover_schema(self) -> dict[str, Any]:
        return {
            "system_id": self.manifest.system_id,
            "system_name": self.manifest.system_name,
            "version": self.manifest.version,
            "endpoints": [op.to_dict() for op in self.manifest.operations],
            "metrics_available": ["cpu_cores", "ram_total_mb", "ram_available_mb", "disk_free_gb", "network_ips"],
            "security_boundaries": "Read-only R0; no process execution, no configuration mutation.",
        }

    def execute_operation(self, operation_id: str, params: dict[str, Any]) -> ConnectorResponse:
        t0 = time.perf_counter()
        try:
            if operation_id == "get_cpu_memory":
                cores = os.cpu_count() or 1
                if platform.system() == "Windows":
                    total_mb, avail_mb, load_pct = _read_windows_ram()
                else:
                    total_mb, avail_mb, load_pct = _read_linux_ram()

                data = {
                    "cpu_cores": cores,
                    "ram_total_mb": total_mb,
                    "ram_available_mb": avail_mb,
                    "ram_used_percent": load_pct,
                    "os_platform": platform.system(),
                    "machine": platform.machine(),
                }
                latency = (time.perf_counter() - t0) * 1000.0
                return ConnectorResponse(success=True, data=data, latency_ms=round(latency, 2))

            elif operation_id == "get_disk_metrics":
                target_p = params.get("path", str(self.workspace))
                usage = shutil.disk_usage(target_p)
                total_gb = round(usage.total / (1024**3), 2)
                free_gb = round(usage.free / (1024**3), 2)
                used_gb = round(usage.used / (1024**3), 2)
                pct = round((usage.used / usage.total) * 100.0, 1)

                data = {
                    "path": target_p,
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "used_percent": pct,
                }
                latency = (time.perf_counter() - t0) * 1000.0
                return ConnectorResponse(success=True, data=data, latency_ms=round(latency, 2))

            elif operation_id == "get_network_info":
                host = socket.gethostname()
                try:
                    _, _, ip_list = socket.gethostbyname_ex(host)
                except Exception:
                    ip_list = ["127.0.0.1"]

                data = {
                    "hostname": host,
                    "ips": ip_list,
                }
                latency = (time.perf_counter() - t0) * 1000.0
                return ConnectorResponse(success=True, data=data, latency_ms=round(latency, 2))

            else:
                return ConnectorResponse(
                    success=False,
                    data=None,
                    error=f"Unknown operation_id '{operation_id}'",
                    status_code=404,
                )

        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000.0
            return ConnectorResponse(
                success=False,
                data=None,
                error=str(exc),
                status_code=500,
                latency_ms=round(latency, 2),
            )

    def verify_target_state(
        self,
        operation_id: str,
        params: dict[str, Any],
        response: ConnectorResponse,
    ) -> VerificationResult:
        """Verify that observed telemetry metrics adhere to physical and mathematical invariants."""
        if not response.success or not isinstance(response.data, dict):
            return VerificationResult(
                verified=False,
                method="telemetry_invariant_check",
                notes="Response data is missing or operation returned failure",
            )

        data = response.data
        if operation_id == "get_cpu_memory":
            cores = data.get("cpu_cores", 0)
            ram_total = data.get("ram_total_mb", 0)
            ram_pct = data.get("ram_used_percent", -1)
            valid = cores > 0 and ram_total > 0 and (0.0 <= ram_pct <= 100.0)
            return VerificationResult(
                verified=valid,
                method="cpu_ram_invariant_check",
                target_state_observed=f"{cores} Cores, {ram_total}MB RAM, {ram_pct}% Load",
                evidence_payload={"cores": cores, "ram_total_mb": ram_total, "ram_pct": ram_pct},
                notes="Verified physical CPU/RAM bounds" if valid else "Metrics violated bounds",
            )

        elif operation_id == "get_disk_metrics":
            total = data.get("total_gb", 0)
            free = data.get("free_gb", 0)
            pct = data.get("used_percent", -1)
            valid = total > 0 and free >= 0 and (0.0 <= pct <= 100.0)
            return VerificationResult(
                verified=valid,
                method="disk_invariant_check",
                target_state_observed=f"{total}GB Total, {free}GB Free ({pct}% Used)",
                evidence_payload={"total_gb": total, "free_gb": free, "used_percent": pct},
                notes="Verified physical disk usage bounds" if valid else "Disk metrics violated bounds",
            )

        elif operation_id == "get_network_info":
            host = data.get("hostname", "")
            ips = data.get("ips", [])
            valid = bool(host) and len(ips) > 0
            return VerificationResult(
                verified=valid,
                method="network_invariant_check",
                target_state_observed=f"Host: {host}, IPs: {ips}",
                evidence_payload={"hostname": host, "ips": ips},
                notes="Verified network interface resolution" if valid else "Network info incomplete",
            )

        return VerificationResult(
            verified=True,
            method="generic_telemetry_check",
            target_state_observed=data,
        )
