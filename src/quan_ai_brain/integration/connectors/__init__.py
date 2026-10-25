"""Standard and specialized software connectors for QUAN AI BRAIN."""
from __future__ import annotations

from quan_ai_brain.integration.connectors.mock_service import MockServiceConnector
from quan_ai_brain.integration.connectors.system_telemetry import SystemTelemetryConnector

__all__ = ["SystemTelemetryConnector", "MockServiceConnector"]
