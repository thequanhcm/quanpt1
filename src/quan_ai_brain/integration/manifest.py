"""Connector Manifest and Contract Models for Universal Software Integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from quan_ai_brain.governance.policy import RiskLevel


class ConnectorType(str, Enum):
    """Supported connector categories under Universal Connector Architecture."""
    REST_API = "REST_API"
    GRAPHQL = "GRAPHQL"
    MCP_SERVER = "MCP_SERVER"
    DATABASE = "DATABASE"
    CLI_SDK = "CLI_SDK"
    UI_AUTOMATION = "UI_AUTOMATION"
    EDGE_SYSTEM = "EDGE_SYSTEM"
    SYSTEM_TELEMETRY = "SYSTEM_TELEMETRY"


class AuthType(str, Enum):
    """Authentication protocols supported by connectors."""
    NONE = "NONE"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    HMAC_SHA256 = "HMAC_SHA256"
    MUTUAL_TLS = "MUTUAL_TLS"


class AutonomyLevelScope(str, Enum):
    """Bounded autonomy levels defined in Master Prompt V6 Section VI."""
    A0_OBSERVE = "A0_OBSERVE"                  # Read status, metrics, zero state changes
    A1_RECOMMEND = "A1_RECOMMEND"              # Analyze, diagnose, prepare plan, no execution
    A2_DELEGATED = "A2_DELEGATED"              # Execute specifically delegated, reversible actions
    A3_OWNER_APPROVAL = "A3_OWNER_APPROVAL"    # Impactful or R4 operations requiring owner approval


@dataclass(frozen=True)
class ConnectorOperation:
    """Explicit declarative contract for an operation exposed by a software connector."""
    operation_id: str
    name: str
    description: str
    action_type: str  # "read", "analysis", "write"
    risk_level: RiskLevel
    autonomy_level: AutonomyLevelScope
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    side_effects: bool = False
    requires_approval: bool = True
    supports_dry_run: bool = True
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.operation_id or not self.operation_id.strip():
            raise ValueError("operation_id must not be empty")
        if not self.name or not self.name.strip():
            raise ValueError("name must not be empty")
        if not isinstance(self.risk_level, RiskLevel):
            raise TypeError("risk_level must be an instance of RiskLevel IntEnum")
        if not isinstance(self.autonomy_level, AutonomyLevelScope):
            raise TypeError("autonomy_level must be an instance of AutonomyLevelScope")

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "risk_level": int(self.risk_level),
            "risk_name": self.risk_level.name,
            "autonomy_level": self.autonomy_level.value,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "side_effects": self.side_effects,
            "requires_approval": self.requires_approval,
            "supports_dry_run": self.supports_dry_run,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class ConnectorManifest:
    """Declarative manifest describing an authorized external software integration."""
    system_id: str
    system_name: str
    system_type: ConnectorType
    version: str
    description: str
    auth_type: AuthType
    base_endpoint: str
    operations: list[ConnectorOperation] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    timeout_seconds: float = 15.0
    read_only_default: bool = True
    environment: str = "local"  # "local", "staging", "production"
    owner_signoff_required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.system_id or not self.system_id.strip():
            raise ValueError("system_id must not be empty")
        if not self.system_name or not self.system_name.strip():
            raise ValueError("system_name must not be empty")
        if not isinstance(self.system_type, ConnectorType):
            raise TypeError("system_type must be an instance of ConnectorType")
        if not isinstance(self.auth_type, AuthType):
            raise TypeError("auth_type must be an instance of AuthType")

    def get_operation(self, operation_id: str) -> ConnectorOperation | None:
        for op in self.operations:
            if op.operation_id == operation_id:
                return op
        return None

    def validate(self) -> tuple[bool, str | None]:
        """Validate manifest structure, operation IDs uniqueness, and safety boundaries."""
        if self.rate_limit_per_minute <= 0:
            return False, "rate_limit_per_minute must be greater than 0"
        if self.timeout_seconds <= 0:
            return False, "timeout_seconds must be greater than 0"

        seen_op_ids: set[str] = set()
        for op in self.operations:
            if op.operation_id in seen_op_ids:
                return False, f"Duplicate operation_id '{op.operation_id}' in manifest"
            seen_op_ids.add(op.operation_id)

            # R5 operations are unconditionally rejected
            if int(op.risk_level) >= int(RiskLevel.R5):
                return False, f"Operation '{op.operation_id}' declared R5, which is strictly prohibited"

            # In read-only mode, side_effects or write actions must not be permitted
            if self.read_only_default and (op.side_effects or op.action_type == "write"):
                return False, f"Operation '{op.operation_id}' has side effects but connector is read-only"

        return True, None

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "system_name": self.system_name,
            "system_type": self.system_type.value,
            "version": self.version,
            "description": self.description,
            "auth_type": self.auth_type.value,
            "base_endpoint": self.base_endpoint,
            "operations": [op.to_dict() for op in self.operations],
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "timeout_seconds": self.timeout_seconds,
            "read_only_default": self.read_only_default,
            "environment": self.environment,
            "owner_signoff_required": self.owner_signoff_required,
            "metadata": self.metadata,
        }
