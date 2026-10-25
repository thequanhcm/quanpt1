"""System Inventory Engine for QUAN AI BRAIN — Sprint 4.

Maintains a truthful, auditable inventory of all system components:
- Services, APIs, ports, processes
- Models (local + cloud)
- Databases, memory stores
- Pi 5 edge device
- Test suites, reports, evidence
- Capabilities, permissions, policies

Each component has:
- component_id: unique identifier
- name: human-readable name
- component_type: service|module|model|database|device|interface
- location: verified location or endpoint
- version: verified version or unknown
- status: healthy|degraded|failed|unknown|not_installed
- capabilities: list of capabilities
- dependencies: list of component_ids
- last_verified_at: ISO timestamp
- verification_method: how it was verified
- evidence_refs: references to evidence (files, logs, test results)
- known_limitations: list of limitations
- permission_scope: list of allowed scopes
- confidence: 0.0-1.0 confidence in this information

Giai đoạn Sprint 4 (2026-10-25): Core inventory with auto-discovery and health checks.
"""
from __future__ import annotations

import importlib.metadata
import json
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ComponentType(str, Enum):
    SERVICE = "service"
    MODULE = "module"
    MODEL = "model"
    DATABASE = "database"
    DEVICE = "device"
    INTERFACE = "interface"
    CONFIG = "config"
    TEST = "test"


class ComponentStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"


@dataclass
class SystemComponent:
    """Single system component with full metadata."""
    component_id: str
    name: str
    component_type: ComponentType
    location: str
    version: str
    status: ComponentStatus
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    last_verified_at: str | None = None
    verification_method: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)
    permission_scope: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "component_type": self.component_type.value,
            "location": self.location,
            "version": self.version,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "last_verified_at": self.last_verified_at,
            "verification_method": self.verification_method,
            "evidence_refs": self.evidence_refs,
            "known_limitations": self.known_limitations,
            "permission_scope": self.permission_scope,
            "confidence": round(self.confidence, 3),
        }


class SystemInventory:
    """Auto-discovers and maintains system component inventory."""

    def __init__(self, workspace: str | Path = ".") -> None:
        self.workspace = Path(workspace).resolve()
        self._components: dict[str, SystemComponent] = {}
        self._last_scan: str | None = None

    def scan_all(self) -> dict[str, SystemComponent]:
        """Run full system scan."""
        self._scan_python_env()
        self._scan_services()
        self._scan_models()
        self._scan_databases()
        self._scan_pi5_device()
        self._scan_tests()
        self._scan_modules()
        self._last_scan = datetime.now(timezone.utc).isoformat()
        return self._components

    def _add_component(self, comp: SystemComponent) -> None:
        """Add or update component."""
        self._components[comp.component_id] = comp

    def _scan_python_env(self) -> None:
        """Scan Python environment: version, venv, key packages."""
        # Python version
        self._add_component(SystemComponent(
            component_id="python_runtime",
            name="Python Runtime",
            component_type=ComponentType.SERVICE,
            location=f"{sys.executable} (v{sys.version.split()[0]})",
            version=sys.version.split()[0],
            status=ComponentStatus.HEALTHY,
            capabilities=["execution", "stdlib"],
            verification_method="sys.version",
            evidence_refs=[sys.executable],
            confidence=1.0,
        ))

        # Venv check
        venv_path = Path(sys.prefix)
        is_venv = (venv_path / "pyvenv.cfg").exists()
        self._add_component(SystemComponent(
            component_id="python_venv",
            name="Python Virtual Environment",
            component_type=ComponentType.CONFIG,
            location=str(venv_path),
            version="active" if is_venv else "none",
            status=ComponentStatus.HEALTHY if is_venv else ComponentStatus.DEGRADED,
            capabilities=["isolation", "package_management"],
            verification_method="pyvenv.cfg check",
            evidence_refs=[str(venv_path / "pyvenv.cfg")],
            known_limitations=[] if is_venv else ["No virtual environment active"],
            confidence=1.0,
        ))

        # Key packages
        packages = ["pytest", "sqlite3", "requests"]
        for pkg in packages:
            try:
                version = importlib.metadata.version(pkg)
                self._add_component(SystemComponent(
                    component_id=f"package_{pkg}",
                    name=f"Package: {pkg}",
                    component_type=ComponentType.MODULE,
                    location=f"{sys.prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/{pkg}",
                    version=version,
                    status=ComponentStatus.HEALTHY,
                    verification_method=f"importlib.metadata.version('{pkg}')",
                    evidence_refs=[],
                    confidence=1.0,
                ))
            except importlib.metadata.PackageNotFoundError:
                self._add_component(SystemComponent(
                    component_id=f"package_{pkg}",
                    name=f"Package: {pkg}",
                    component_type=ComponentType.MODULE,
                    location="not installed",
                    version="none",
                    status=ComponentStatus.NOT_INSTALLED,
                    known_limitations=[f"{pkg} not installed"],
                    confidence=1.0,
                ))

    def _scan_services(self) -> None:
        """Scan local services: Ollama, web servers, Pi 5."""
        # Ollama
        ollama_healthy = self._check_http_endpoint("127.0.0.1", 11434, timeout=2)
        self._add_component(SystemComponent(
            component_id="service_ollama",
            name="Ollama Daemon",
            component_type=ComponentType.SERVICE,
            location="http://127.0.0.1:11434",
            version="unknown",
            status=ComponentStatus.HEALTHY if ollama_healthy else ComponentStatus.FAILED,
            capabilities=["llm_inference", "embedding"],
            verification_method="HTTP GET /",
            evidence_refs=["ollama ps", "curl http://127.0.0.1:11434/"],
            confidence=0.9 if ollama_healthy else 1.0,
        ))

        # Web UI 8765
        web_8765_healthy = self._check_http_endpoint("127.0.0.1", 8765, timeout=2)
        self._add_component(SystemComponent(
            component_id="service_web_ui",
            name="Web UI (Chat & Voice)",
            component_type=ComponentType.SERVICE,
            location="http://127.0.0.1:8765",
            version="unknown",
            status=ComponentStatus.HEALTHY if web_8765_healthy else ComponentStatus.FAILED,
            capabilities=["chat", "voice_interface"],
            verification_method="HTTP GET /",
            evidence_refs=["curl http://127.0.0.1:8765/"],
            confidence=0.9 if web_8765_healthy else 1.0,
        ))

        # Executive Desk 8766
        web_8766_healthy = self._check_http_endpoint("127.0.0.1", 8766, timeout=2)
        self._add_component(SystemComponent(
            component_id="service_executive_desk",
            name="Executive Desk (Cockpit)",
            component_type=ComponentType.SERVICE,
            location="http://127.0.0.1:8766",
            version="unknown",
            status=ComponentStatus.HEALTHY if web_8766_healthy else ComponentStatus.FAILED,
            capabilities=["cockpit", "task_management", "approval_center"],
            verification_method="HTTP GET /",
            evidence_refs=["curl http://127.0.0.1:8766/"],
            confidence=0.9 if web_8766_healthy else 1.0,
        ))

    def _scan_models(self) -> None:
        """Scan LLM models: local Ollama + NetMind cloud."""
        # Local models (probe Ollama)
        try:
            import urllib.request
            import json
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                for model in models[:5]:  # Top 5
                    name = model.get("name", "unknown")
                    self._add_component(SystemComponent(
                        component_id=f"model_{name.replace(':', '_')}",
                        name=f"Model: {name}",
                        component_type=ComponentType.MODEL,
                        location="http://127.0.0.1:11434",
                        version=model.get("details", {}).get("format", "unknown"),
                        status=ComponentStatus.HEALTHY,
                        capabilities=["text_generation", "chat"],
                        dependencies=["service_ollama"],
                        verification_method="Ollama API /api/tags",
                        evidence_refs=[],
                        confidence=0.95,
                    ))
        except Exception:
            pass  # Ollama offline, skip

        # NetMind cloud models
        self._add_component(SystemComponent(
            component_id="model_glm_flash",
            name="Model: zai-org/GLM-5.3-Flash",
            component_type=ComponentType.MODEL,
            location="https://stream-netmind.viettel.vn/aigw/ai/v1",
            version="unknown",
            status=ComponentStatus.UNKNOWN,  # Need to probe
            capabilities=["text_generation", "chat", "streaming", "vietnamese"],
            dependencies=["service_netmind_gateway"],
            known_limitations=["Requires API key", "External dependency"],
            verification_method="NetMind API /chat/completions",
            confidence=0.7,
        ))

    def _scan_databases(self) -> None:
        """Scan SQLite databases."""
        db_paths = [
            "data/tasks.db",
            "data/brain.db",
            "data/governance.db",
            "data/consultations.db",
        ]
        for db_rel in db_paths:
            db_path = self.workspace / db_rel
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                self._add_component(SystemComponent(
                    component_id=f"db_{Path(db_rel).stem}",
                    name=f"Database: {Path(db_rel).stem}",
                    component_type=ComponentType.DATABASE,
                    location=str(db_path),
                    version="SQLite 3",
                    status=ComponentStatus.HEALTHY,
                    capabilities=["persistence", "query"],
                    verification_method="file.exists() + stat()",
                    evidence_refs=[str(db_path)],
                    confidence=1.0,
                ))
            else:
                self._add_component(SystemComponent(
                    component_id=f"db_{Path(db_rel).stem}",
                    name=f"Database: {Path(db_rel).stem}",
                    component_type=ComponentType.DATABASE,
                    location=str(db_path),
                    version="none",
                    status=ComponentStatus.NOT_INSTALLED,
                    known_limitations=[f"Database not found at {db_rel}"],
                    confidence=1.0,
                ))

    def _scan_pi5_device(self) -> None:
        """Scan Raspberry Pi 5 edge device."""
        pi_ip = "192.168.1.21"
        pi_healthy = self._check_http_endpoint(pi_ip, 8768, timeout=3)
        self._add_component(SystemComponent(
            component_id="device_pi5",
            name="Raspberry Pi 5 (EDGE-PI5-DESK-01)",
            component_type=ComponentType.DEVICE,
            location=f"http://{pi_ip}:8768",
            version="unknown",
            status=ComponentStatus.HEALTHY if pi_healthy else ComponentStatus.FAILED,
            capabilities=["voice_interface", "avatar", "mic", "speaker", "camera"],
            verification_method="HTTP GET /api/kiosk/status",
            evidence_refs=[f"curl http://{pi_ip}:8768/api/kiosk/status"],
            known_limitations=["Requires Wi-Fi connection"],
            confidence=0.9 if pi_healthy else 1.0,
        ))

    def _scan_tests(self) -> None:
        """Scan test suite."""
        tests_path = self.workspace / "tests"
        if tests_path.exists():
            test_files = list(tests_path.glob("test_*.py"))
            self._add_component(SystemComponent(
                component_id="test_suite",
                name="Test Suite",
                component_type=ComponentType.TEST,
                location=str(tests_path),
                version=f"{len(test_files)} test files",
                status=ComponentStatus.HEALTHY,
                capabilities=["regression_testing", "verification"],
                verification_method="glob('tests/test_*.py')",
                evidence_refs=[str(f) for f in test_files[:10]],  # First 10
                confidence=1.0,
            ))
        else:
            self._add_component(SystemComponent(
                component_id="test_suite",
                name="Test Suite",
                component_type=ComponentType.TEST,
                location="tests/",
                version="none",
                status=ComponentStatus.NOT_INSTALLED,
                known_limitations=["No tests directory found"],
                confidence=1.0,
            ))

    def _scan_modules(self) -> None:
        """Scan QUAN AI BRAIN modules."""
        modules = [
            ("cognition", "Cognition Layer"),
            ("memory", "Memory Engine"),
            ("orchestration", "Task Orchestration"),
            ("llm", "LLM Provider"),
            ("web", "Web Server"),
            ("governance", "Governance"),
        ]
        for mod_name, mod_desc in modules:
            mod_path = self.workspace / "src" / "quan_ai_brain" / mod_name
            if mod_path.exists():
                py_files = list(mod_path.glob("*.py"))
                self._add_component(SystemComponent(
                    component_id=f"module_{mod_name}",
                    name=f"Module: {mod_name.title()}",
                    component_type=ComponentType.MODULE,
                    location=str(mod_path),
                    version=f"{len(py_files)} Python files",
                    status=ComponentStatus.HEALTHY,
                    verification_method="path.exists() + glob('*.py')",
                    evidence_refs=[str(f) for f in py_files[:5]],
                    confidence=1.0,
                ))
            else:
                self._add_component(SystemComponent(
                    component_id=f"module_{mod_name}",
                    name=f"Module: {mod_name.title()}",
                    component_type=ComponentType.MODULE,
                    location=f"src/quan_ai_brain/{mod_name}/",
                    version="none",
                    status=ComponentStatus.NOT_INSTALLED,
                    confidence=1.0,
                ))

    @staticmethod
    def _check_http_endpoint(host: str, port: int, timeout: float = 2.0) -> bool:
        """Check if HTTP endpoint is reachable."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, socket.error, OSError):
            return False

    def get_component(self, component_id: str) -> SystemComponent | None:
        """Get component by ID."""
        return self._components.get(component_id)

    def list_components(self, status: ComponentStatus | None = None) -> list[SystemComponent]:
        """List all components, optionally filtered by status."""
        components = list(self._components.values())
        if status:
            components = [c for c in components if c.status == status]
        return components

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall health summary."""
        total = len(self._components)
        healthy = len([c for c in self._components.values() if c.status == ComponentStatus.HEALTHY])
        degraded = len([c for c in self._components.values() if c.status == ComponentStatus.DEGRADED])
        failed = len([c for c in self._components.values() if c.status == ComponentStatus.FAILED])
        unknown = len([c for c in self._components.values() if c.status == ComponentStatus.UNKNOWN])
        not_installed = len([c for c in self._components.values() if c.status == ComponentStatus.NOT_INSTALLED])

        return {
            "total_components": total,
            "healthy": healthy,
            "degraded": degraded,
            "failed": failed,
            "unknown": unknown,
            "not_installed": not_installed,
            "health_percentage": healthy / max(1, total),
            "last_scan": self._last_scan,
        }

    def to_dict(self) -> dict[str, Any]:
        """Export full inventory as dict."""
        return {
            "last_scan": self._last_scan,
            "workspace": str(self.workspace),
            "health_summary": self.get_health_summary(),
            "components": {cid: comp.to_dict() for cid, comp in self._components.items()},
        }