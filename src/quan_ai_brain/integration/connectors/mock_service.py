"""Mock Software Connector for Adversarial & Governance Acceptance Testing (Section XII)."""
from __future__ import annotations

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


class MockServiceConnector(BaseConnectorAdapter):
    """Configurable mock adapter for testing failure modes, rate limits, timeouts, and state verification."""

    def __init__(
        self,
        system_id: str = "mock_service",
        system_name: str = "Mock Enterprise API Service",
        read_only: bool = True,
    ) -> None:
        ops = [
            ConnectorOperation(
                operation_id="query_records",
                name="Truy Vấn Bản Ghi",
                description="Đọc danh sách bản ghi mô phỏng",
                action_type="read",
                risk_level=RiskLevel.R0,
                autonomy_level=AutonomyLevelScope.A0_OBSERVE,
                input_schema={"types": {"category": str}},
                side_effects=False,
                requires_approval=False,
            ),
            ConnectorOperation(
                operation_id="update_config",
                name="Cập Nhật Cấu Hình",
                description="Cập nhật tham số cấu hình hệ thống (R2)",
                action_type="write" if not read_only else "read",
                risk_level=RiskLevel.R2,
                autonomy_level=AutonomyLevelScope.A2_DELEGATED,
                input_schema={"required": ["key", "value"], "types": {"key": str, "value": str}},
                side_effects=not read_only,
                requires_approval=True,
            ),
        ]
        manifest = ConnectorManifest(
            system_id=system_id,
            system_name=system_name,
            system_type=ConnectorType.REST_API,
            version="2.4.0",
            description="Mock enterprise software service for Section XII test coverage",
            auth_type=AuthType.BEARER_TOKEN,
            base_endpoint="https://api.mock-internal.local/v2",
            operations=ops,
            rate_limit_per_minute=5,  # Low rate limit for testing
            timeout_seconds=2.0,
            read_only_default=read_only,
            environment="staging",
        )
        super().__init__(manifest)

        # Simulation knobs for Section XII scenarios
        self.simulate_auth_failure: bool = False
        self.simulate_timeout: bool = False
        self.simulate_ack_without_state_change: bool = False
        self.simulate_malicious_output: bool = False
        self.target_database: dict[str, Any] = {"status": "ACTIVE", "version": "2.4.0", "records": ["rec_1", "rec_2"]}

    def connect(self) -> bool:
        if self.simulate_auth_failure:
            self._connected = False
            return False
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def health_check(self) -> dict[str, Any]:
        if self.simulate_auth_failure:
            return {"healthy": False, "status": "AUTH_FAILED", "error": "Invalid or expired token"}
        return {"healthy": True, "status": "HEALTHY", "version": self.manifest.version}

    def discover_schema(self) -> dict[str, Any]:
        return {
            "system_id": self.manifest.system_id,
            "version": self.manifest.version,
            "tables": ["users", "configs", "audit_logs"],
            "endpoints": [op.to_dict() for op in self.manifest.operations],
        }

    def execute_operation(self, operation_id: str, params: dict[str, Any]) -> ConnectorResponse:
        t0 = time.perf_counter()

        if self.simulate_timeout:
            return ConnectorResponse(
                success=False,
                data=None,
                error="Operation timed out after 2.0s",
                status_code=504,
                latency_ms=2000.0,
            )

        if self.simulate_auth_failure:
            return ConnectorResponse(
                success=False,
                data=None,
                error="Authentication token expired or rejected (HTTP 401)",
                status_code=401,
            )

        if self.simulate_malicious_output:
            # Contains simulated credential and script injection
            dirty_data = {
                "records": ["rec_1"],
                "api_key": "sk-proj-supersecretkey12345",
                "script": "<script>alert('xss')</script>",
            }
            return ConnectorResponse(success=True, data=dirty_data)

        if operation_id == "query_records":
            category = params.get("category", "all")
            records = [r for r in self.target_database["records"]]
            return ConnectorResponse(
                success=True,
                data={"category": category, "count": len(records), "records": records},
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        elif operation_id == "update_config":
            k = params["key"]
            v = params["value"]
            if not self.simulate_ack_without_state_change:
                # Real state change
                self.target_database[k] = v
            # If simulate_ack_without_state_change is True, we return success ACK but DO NOT update database!
            return ConnectorResponse(
                success=True,
                data={"updated": True, "key": k, "ack": "CONFIG_ACCEPTED"},
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        return ConnectorResponse(success=False, data=None, error=f"Unknown op {operation_id}", status_code=404)

    def verify_target_state(
        self,
        operation_id: str,
        params: dict[str, Any],
        response: ConnectorResponse,
    ) -> VerificationResult:
        if operation_id == "update_config":
            expected_k = params.get("key")
            expected_v = params.get("value")
            actual_v = self.target_database.get(expected_k)
            # Verify actual state in the target database!
            state_matches = (actual_v == expected_v)
            return VerificationResult(
                verified=state_matches,
                method="target_database_state_query",
                target_state_observed=f"{expected_k}={actual_v}",
                evidence_payload={"expected": expected_v, "actual": actual_v},
                notes="State verified in target DB" if state_matches else f"State mismatch: expected '{expected_v}', got '{actual_v}'",
            )

        return VerificationResult(
            verified=response.success,
            method="record_count_verification",
            target_state_observed=response.data,
        )
