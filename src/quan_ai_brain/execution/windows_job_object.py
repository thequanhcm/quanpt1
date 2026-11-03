"""Windows Job Object OS-Level Process Containment Backend for QUAN AI BRAIN.

Sprint 7B: Windows Job Object Kernel Integration.
Provides operating-system-enforced hard containment boundaries via Windows NT
Job Objects using pure Python standard library `ctypes`.

Strict Governance & Safety Invariants:
1. Fail-Closed Staging Default:
   - `allow_live_processes` is False by default.
   - Calls to `spawn_process()` raise `ProductionExecutionProhibitedError` unless
     explicitly initialized with `allow_live_processes=True` in authorized tests.
2. Hard Resource Quotas:
   - Memory limits enforced at kernel level (JOB_OBJECT_LIMIT_JOB_MEMORY).
   - CPU user time limits enforced at kernel level (JOB_OBJECT_LIMIT_PROCESS_TIME).
   - Process count limits enforced at kernel level (JOB_OBJECT_LIMIT_ACTIVE_PROCESS).
   - Auto-kill all child processes on handle close (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE).
3. R5 Command Hard Block:
   - Prohibits destructive commands (e.g. `rm -rf`, `del /s`, `format`, `diskpart`).
4. PathGuard Boundary Enforcement:
   - Working directory strictly confined within the designated workspace.
5. Zero Secret Leakage:
   - All standard output, error streams, and metadata are scrubbed via `redact_value()`.
"""
from __future__ import annotations

import ctypes
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
import subprocess
import sys
from typing import Any

from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.execution.process_containment import (
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS,
    JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION,
    JOB_OBJECT_LIMIT_JOB_MEMORY,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    JOB_OBJECT_LIMIT_PROCESS_MEMORY,
    JOB_OBJECT_LIMIT_PROCESS_TIME,
    ContainmentConfigurationError,
    ContainmentError,
    ProcessBackendInterface,
    ProcessContainmentConfig,
)
from quan_ai_brain.execution.staging import ProductionExecutionProhibitedError
from quan_ai_brain.tools.path_guard import PathGuard, PathOutsideWorkspaceError

logger = logging.getLogger("quan_ai_brain.execution.windows_job_object")

# ---------------------------------------------------------------------------
# Platform Detection & Win32 API Bindings
# ---------------------------------------------------------------------------
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        k32 = ctypes.windll.kernel32
    except Exception as exc:  # pragma: no cover
        k32 = None
        logger.warning(f"Failed to bind kernel32.dll on Windows: {exc}")
else:
    k32 = None

# Information Class Constants
JobObjectBasicAccountingInformation = 1
JobObjectBasicLimitInformation = 2
JobObjectExtendedLimitInformation = 9

# Win32 Ctypes Structures (Standard Windows NT Layout, 64-bit alignment)
if IS_WINDOWS:

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryLimit", ctypes.c_size_t),
            ("PeakJobMemoryLimit", ctypes.c_size_t),
        ]

    class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_int64),
            ("TotalKernelTime", ctypes.c_int64),
            ("ThisPeriodTotalUserTime", ctypes.c_int64),
            ("ThisPeriodTotalKernelTime", ctypes.c_int64),
            ("TotalPageFaultCount", ctypes.c_uint32),
            ("TotalProcesses", ctypes.c_uint32),
            ("ActiveProcesses", ctypes.c_uint32),
            ("TotalTerminatedProcesses", ctypes.c_uint32),
        ]

else:
    IO_COUNTERS = None  # type: ignore[assignment,misc]
    JOBOBJECT_BASIC_LIMIT_INFORMATION = None  # type: ignore[assignment,misc]
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION = None  # type: ignore[assignment,misc]
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Exceptions & Result Dataclasses
# ---------------------------------------------------------------------------
class WindowsJobObjectError(ContainmentError):
    """Base exception for Windows Job Object subsystem errors."""


class JobObjectCreationError(WindowsJobObjectError):
    """Raised when Win32 CreateJobObjectW fails to instantiate a kernel handle."""


class JobLimitConfigurationError(WindowsJobObjectError):
    """Raised when SetInformationJobObject fails to apply kernel quota flags."""


class ProcessAssignmentError(WindowsJobObjectError):
    """Raised when AssignProcessToJobObject fails to bind a process to the Job Object."""


# Prohibited destructive command fragments (Risk Level R5)
_FORBIDDEN_COMMAND_PATTERNS = (
    "rm -rf",
    "rm -r",
    "del /s",
    "del /f",
    "rmdir /s",
    "rd /s",
    "format ",
    "diskpart",
    "reg delete",
    "bcdedit",
    "vssadmin",
    "mkfs",
)


@dataclass
class JobExecutionResult:
    """Telemetry and outcome of a process executed within a Windows Job Object."""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    job_name: str
    total_processes: int = 0
    active_processes: int = 0
    total_terminated_processes: int = 0
    user_time_ms: float = 0.0
    kernel_time_ms: float = 0.0
    limits_enforced: dict[str, Any] = field(default_factory=dict)
    is_inert: bool = False
    command: list[str] = field(default_factory=list)
    executed_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stdout"] = redact_value(self.stdout)
        data["stderr"] = redact_value(self.stderr)
        return data


# ---------------------------------------------------------------------------
# Windows Job Object Process Backend
# ---------------------------------------------------------------------------
class WindowsJobObjectBackend(ProcessBackendInterface):
    """Windows NT Job Object containment backend enforcing kernel-level resource limits.

    Implements `ProcessBackendInterface` to serve as a high-security OS adapter
    for `ContainedExecutionRunner`.
    """

    def __init__(
        self,
        workspace: str | Path | None = None,
        allow_live_processes: bool = False,
        default_timeout_seconds: float = 30.0,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        self.path_guard = PathGuard(self.workspace)
        self.allow_live_processes: bool = allow_live_processes
        self.default_timeout_seconds: float = default_timeout_seconds
        self._active_jobs: dict[str, int] = {}
        self._active_configs: dict[str, ProcessContainmentConfig] = {}

    def is_available(self) -> bool:
        """Check if Windows Job Object kernel facilities are available on this host."""
        return bool(IS_WINDOWS and k32 is not None and hasattr(k32, "CreateJobObjectW"))

    def configure_containment(self, config: ProcessContainmentConfig) -> dict[str, Any]:
        """Create and configure a real Windows Job Object with resource limits.

        Applies:
        - Memory quota: JOB_OBJECT_LIMIT_JOB_MEMORY
        - CPU user time quota: JOB_OBJECT_LIMIT_PROCESS_TIME
        - Active processes count: JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        - Auto-kill on job close: JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        - Die on unhandled exception: JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        """
        if not self.is_available():
            raise ContainmentConfigurationError(
                "WindowsJobObjectBackend is only supported on Windows host platforms with kernel32.dll."
            )

        # 1. Create or open Job Object handle
        h_job = k32.CreateJobObjectW(None, config.job_name)
        if not h_job:
            err = ctypes.GetLastError()
            raise JobObjectCreationError(
                f"Failed to create Win32 Job Object '{config.job_name}': Win32 error {err}"
            )

        # 2. Configure limits via JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()

        limit_flags = 0
        if config.kill_on_job_close:
            limit_flags |= JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if config.max_memory_bytes > 0:
            limit_flags |= JOB_OBJECT_LIMIT_JOB_MEMORY
            info.JobMemoryLimit = config.max_memory_bytes
        if config.max_cpu_time_ms > 0:
            limit_flags |= JOB_OBJECT_LIMIT_PROCESS_TIME
            # Windows PerProcessUserTimeLimit is measured in 100-nanosecond ticks
            # 1 ms = 10,000 * 100ns units
            info.BasicLimitInformation.PerProcessUserTimeLimit = int(config.max_cpu_time_ms * 10000)
        if config.max_active_processes > 0:
            limit_flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            info.BasicLimitInformation.ActiveProcessLimit = int(config.max_active_processes)

        limit_flags |= JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        info.BasicLimitInformation.LimitFlags = limit_flags

        res = k32.SetInformationJobObject(
            h_job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not res:
            err = ctypes.GetLastError()
            k32.CloseHandle(h_job)
            raise JobLimitConfigurationError(
                f"Failed to set limits on Win32 Job Object '{config.job_name}': Win32 error {err}"
            )

        # 3. Track active job state
        self._active_jobs[config.job_name] = h_job
        self._active_configs[config.job_name] = config
        config.is_os_enforced = True

        return {
            "job_name": config.job_name,
            "handle": h_job,
            "status": "CONFIGURED_OS",
            "is_os_enforced": True,
            "limits_applied": {
                "memory_bytes": config.max_memory_bytes,
                "cpu_time_ms": config.max_cpu_time_ms,
                "active_processes": config.max_active_processes,
                "kill_on_job_close": config.kill_on_job_close,
                "limit_flags": limit_flags,
            },
        }

    def spawn_process(
        self,
        command: list[str],
        containment_handle: Any,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> JobExecutionResult:
        """Spawn an operating system process strictly bound to the Job Object.

        Fail-Closed Safety Check:
        If `self.allow_live_processes` is False, execution is unconditionally refused.
        """
        # 1. Fail-closed staging gate
        if not self.allow_live_processes:
            raise ProductionExecutionProhibitedError(
                "WindowsJobObjectBackend is operating in Fail-Closed Staging mode "
                "(allow_live_processes=False). Real OS process execution is prohibited."
            )

        # 2. Command safety validation
        if not command or not isinstance(command, list):
            raise ValueError("Command must be a non-empty list of arguments.")

        cmd_str = " ".join(command).lower()
        for forbidden in _FORBIDDEN_COMMAND_PATTERNS:
            if forbidden in cmd_str:
                raise ValueError(
                    f"Prohibited destructive command pattern '{forbidden}' detected in command: {command}"
                )

        # 3. PathGuard boundary check
        work_dir = Path(cwd).resolve() if cwd else self.workspace
        try:
            work_dir.relative_to(self.workspace)
        except ValueError as exc:
            raise PathOutsideWorkspaceError(
                f"Working directory '{work_dir}' escapes the authorized workspace '{self.workspace}'"
            ) from exc

        # 4. Resolve Job Object handle
        h_job, job_name = self._resolve_job_handle(containment_handle)
        if not h_job:
            raise ContainmentConfigurationError(
                f"Invalid or inactive Job Object containment handle: {containment_handle}"
            )

        # 5. Spawn subprocess and assign immediately
        # On Windows, if command[0] is sys.executable, resolve to _base_executable
        # to prevent the Windows venv redirector stub from spawning an extra child process
        target_cmd = list(command)
        if target_cmd:
            try:
                if Path(target_cmd[0]).resolve() == Path(sys.executable).resolve():
                    base_py = getattr(sys, "_base_executable", None)
                    if base_py and Path(base_py).exists():
                        target_cmd[0] = str(base_py)
            except Exception:
                pass

        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds
        proc = None
        try:
            proc = subprocess.Popen(
                target_cmd,
                cwd=str(work_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Assign process to Job Object via native OS handle
            assigned = k32.AssignProcessToJobObject(h_job, int(proc._handle))
            if not assigned:
                err = ctypes.GetLastError()
                proc.terminate()
                proc.wait(timeout=2)
                raise ProcessAssignmentError(
                    f"Failed to assign process PID {proc.pid} to Job Object '{job_name}': Win32 error {err}"
                )

            # Wait for execution to complete
            raw_out, raw_err = proc.communicate(timeout=timeout)
            ret_code = proc.returncode

        except subprocess.TimeoutExpired:
            if proc:
                proc.kill()
                raw_out, raw_err = proc.communicate()
            else:
                raw_out, raw_err = b"", b""
            ret_code = -1
            raw_err = raw_err + b"\n[TIMEOUT_EXPIRED: Process killed by timeout policy]"

        except Exception as exc:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            raise exc

        # 6. Query accounting telemetry
        acct = self.query_accounting(h_job)
        cfg = self._active_configs.get(job_name)
        limits_dict = cfg.to_dict() if cfg else {}

        stdout_clean = redact_value(raw_out.decode("utf-8", errors="replace"))
        stderr_clean = redact_value(raw_err.decode("utf-8", errors="replace"))

        return JobExecutionResult(
            success=(ret_code == 0),
            returncode=ret_code,
            stdout=stdout_clean,
            stderr=stderr_clean,
            job_name=job_name,
            total_processes=acct.get("total_processes", 1),
            active_processes=acct.get("active_processes", 0),
            total_terminated_processes=acct.get("total_terminated_processes", 0),
            user_time_ms=acct.get("user_time_ms", 0.0),
            kernel_time_ms=acct.get("kernel_time_ms", 0.0),
            limits_enforced=limits_dict,
            is_inert=False,
            command=command,
        )

    def query_accounting(self, job_name_or_handle: Any) -> dict[str, Any]:
        """Query kernel accounting telemetry from a live Job Object."""
        if not self.is_available():
            return {}

        h_job, _ = self._resolve_job_handle(job_name_or_handle)
        if not h_job:
            return {}

        acct = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        res = k32.QueryInformationJobObject(
            h_job,
            JobObjectBasicAccountingInformation,
            ctypes.byref(acct),
            ctypes.sizeof(acct),
            None,
        )
        if not res:
            return {}

        return {
            "total_processes": acct.TotalProcesses,
            "active_processes": acct.ActiveProcesses,
            "total_terminated_processes": acct.TotalTerminatedProcesses,
            "user_time_ms": acct.TotalUserTime / 10000.0,
            "kernel_time_ms": acct.TotalKernelTime / 10000.0,
            "total_page_faults": acct.TotalPageFaultCount,
        }

    def close_containment(self, job_name_or_handle: Any) -> bool:
        """Close the Win32 handle, triggering auto-kill on all processes in the job."""
        if not self.is_available():
            return False

        h_job, job_name = self._resolve_job_handle(job_name_or_handle)
        if not h_job:
            return False

        k32.CloseHandle(h_job)
        if job_name in self._active_jobs:
            del self._active_jobs[job_name]
        if job_name in self._active_configs:
            del self._active_configs[job_name]
        return True

    def close_all(self) -> None:
        """Safely close all currently tracked Job Object handles."""
        for name in list(self._active_jobs.keys()):
            self.close_containment(name)

    def _resolve_job_handle(self, handle_or_name: Any) -> tuple[int | None, str]:
        """Helper to resolve a handle number and job name from various inputs."""
        if isinstance(handle_or_name, dict):
            job_name = handle_or_name.get("job_name", "")
            h_job = handle_or_name.get("handle") or self._active_jobs.get(job_name)
            return h_job, job_name
        if isinstance(handle_or_name, int):
            for name, h in self._active_jobs.items():
                if h == handle_or_name:
                    return handle_or_name, name
            return handle_or_name, f"job_{handle_or_name}"
        if isinstance(handle_or_name, str):
            return self._active_jobs.get(handle_or_name), handle_or_name
        return None, ""

    def __enter__(self) -> WindowsJobObjectBackend:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close_all()
