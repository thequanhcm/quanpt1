"""Tool registry and tool definition contracts for QUAN AI BRAIN."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from quan_ai_brain.governance.policy import RiskLevel


@dataclass(frozen=True)
class ToolDefinition:
    """Explicit declarative contract for an authorized tool in QUAN AI BRAIN."""

    tool_id: str
    description: str
    action_type: str  # "read", "analysis", "write"
    risk_level: RiskLevel
    handler: Callable[[dict[str, Any]], Any]
    input_schema: dict[str, Any] = field(default_factory=dict)
    allowed_resource_scope: str = "workspace"
    side_effects: bool = False
    requires_owner_approval: bool = True
    supports_dry_run: bool = False
    tool_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.tool_id or not self.tool_id.strip():
            raise ValueError("tool_id must not be empty")
        if not self.description or not self.description.strip():
            raise ValueError("description must not be empty")
        if not callable(self.handler):
            raise TypeError("handler must be a callable")
        if not isinstance(self.risk_level, RiskLevel):
            raise TypeError("risk_level must be an instance of RiskLevel IntEnum")


class ToolRegistry:
    """In-memory registry of authorized tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition. Duplicate IDs are rejected to prevent hijacking."""
        if not isinstance(tool, ToolDefinition):
            raise TypeError("tool must be a ToolDefinition instance")
        if tool.tool_id in self._tools:
            raise ValueError(f"Tool with id '{tool.tool_id}' is already registered")
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def has_tool(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def validate_params(self, tool_id: str, params: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate parameters against the tool's input schema if defined."""
        tool = self.get(tool_id)
        if not tool:
            return False, f"Tool '{tool_id}' is not registered"

        if not isinstance(params, dict):
            return False, "Parameters must be provided as a dictionary"

        required_keys = tool.input_schema.get("required", [])
        for req in required_keys:
            if req not in params:
                return False, f"Missing required parameter '{req}'"

        types_spec = tool.input_schema.get("types", {})
        for key, expected_type in types_spec.items():
            if key in params and not isinstance(params[key], expected_type):
                expected_name = expected_type.__name__ if hasattr(expected_type, "__name__") else str(expected_type)
                actual_name = type(params[key]).__name__
                return False, f"Parameter '{key}' must be {expected_name}, got {actual_name}"

        return True, None
