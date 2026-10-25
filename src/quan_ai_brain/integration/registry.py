"""Integration Registry: Unified Catalog Bridging External Systems with ToolRegistry."""
from __future__ import annotations

from typing import Any, Callable

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.integration.adapter import BaseConnectorAdapter, ConnectorResponse
from quan_ai_brain.integration.health import ConnectorHealthMonitor
from quan_ai_brain.integration.manifest import ConnectorManifest, ConnectorOperation
from quan_ai_brain.integration.policy import IntegrationPolicy
from quan_ai_brain.integration.profile import KnowledgeLevel, SystemKnowledgeProfile
from quan_ai_brain.integration.verifier import ExecutionStage, ResultVerifier, VerificationDossier
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry


class IntegrationRegistry:
    """Central registry for authorized software connectors and their operations."""

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        policy: IntegrationPolicy | None = None,
        health_monitor: ConnectorHealthMonitor | None = None,
        verifier: ResultVerifier | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.tool_registry = tool_registry or ToolRegistry()
        self.policy = policy or IntegrationPolicy()
        self.health_monitor = health_monitor or ConnectorHealthMonitor()
        self.verifier = verifier or ResultVerifier()
        self.audit_logger = audit_logger

        self._adapters: dict[str, BaseConnectorAdapter] = {}
        self._profiles: dict[str, SystemKnowledgeProfile] = {}

    def register_connector(
        self,
        adapter: BaseConnectorAdapter,
        auto_allow: bool = True,
    ) -> tuple[bool, str | None]:
        """Register an adapter, validate its manifest, and bind all operations to ToolRegistry."""
        manifest = adapter.manifest
        valid, err = manifest.validate()
        if not valid:
            return False, f"Manifest validation failed for '{manifest.system_id}': {err}"

        if manifest.system_id in self._adapters:
            return False, f"Connector '{manifest.system_id}' is already registered"

        if auto_allow:
            self.policy.allow_connector(manifest.system_id)

        self._adapters[manifest.system_id] = adapter

        # Compile and register each ConnectorOperation into ToolRegistry
        for op in manifest.operations:
            tool_id = f"{manifest.system_id}__{op.operation_id}"
            handler = self._create_operation_handler(adapter, op)

            tool_def = ToolDefinition(
                tool_id=tool_id,
                description=f"[{manifest.system_name}] {op.description}",
                action_type=op.action_type,
                risk_level=op.risk_level,
                handler=handler,
                input_schema=op.input_schema,
                allowed_resource_scope=manifest.system_id,
                side_effects=op.side_effects,
                requires_owner_approval=op.requires_approval,
                supports_dry_run=op.supports_dry_run,
                tool_version=manifest.version,
            )
            # Safe register without throwing if already present
            if not self.tool_registry.has_tool(tool_id):
                self.tool_registry.register(tool_def)

        # Build initial OBSERVED system knowledge profile
        profile = SystemKnowledgeProfile(
            system_id=manifest.system_id,
            system_name=manifest.system_name,
            version=manifest.version,
            environment=manifest.environment,
            owner_organization=manifest.metadata.get("owner", "Quanpt1"),
            documentation_sources=manifest.metadata.get("docs", []),
            connector_id=manifest.system_id,
            supported_read_ops=[op.operation_id for op in manifest.operations if op.action_type == "read"],
            supported_write_ops=[op.operation_id for op in manifest.operations if op.action_type == "write"],
            forbidden_ops=["R5_PROHIBITED", "BYPASS_APPROVAL"],
            technical_limits={"rate_limit_per_minute": manifest.rate_limit_per_minute, "timeout_seconds": manifest.timeout_seconds},
            verification_status=KnowledgeLevel.OBSERVED,
        )
        self._profiles[manifest.system_id] = profile

        if self.audit_logger:
            self.audit_logger.record(
                "integration.connector_registered",
                {"system_id": manifest.system_id, "operations_count": len(manifest.operations)},
            )

        return True, None

    def get_adapter(self, system_id: str) -> BaseConnectorAdapter | None:
        return self._adapters.get(system_id)

    def get_profile(self, system_id: str) -> SystemKnowledgeProfile | None:
        return self._profiles.get(system_id)

    def list_connectors(self) -> list[ConnectorManifest]:
        return [adapter.manifest for adapter in self._adapters.values()]

    def list_profiles(self) -> list[SystemKnowledgeProfile]:
        return list(self._profiles.values())

    def execute_and_verify(
        self,
        system_id: str,
        operation_id: str,
        params: dict[str, Any],
    ) -> tuple[ConnectorResponse, VerificationDossier]:
        """Direct execution and immediate independent verification pipeline."""
        adapter = self.get_adapter(system_id)
        if not adapter:
            err_resp = ConnectorResponse(success=False, data=None, error=f"Connector '{system_id}' not found")
            dossier = VerificationDossier(
                stage=ExecutionStage.OUTCOME_UNKNOWN,
                verified=False,
                target_system=system_id,
                operation_id=operation_id,
                tool_ack_ok=False,
                target_state_query_ok=False,
                notes=f"Connector '{system_id}' is not registered",
            )
            return err_resp, dossier

        op = adapter.manifest.get_operation(operation_id)
        if not op:
            err_resp = ConnectorResponse(success=False, data=None, error=f"Operation '{operation_id}' not found in '{system_id}'")
            dossier = VerificationDossier(
                stage=ExecutionStage.OUTCOME_UNKNOWN,
                verified=False,
                target_system=system_id,
                operation_id=operation_id,
                tool_ack_ok=False,
                target_state_query_ok=False,
                notes=f"Operation '{operation_id}' is not declared in manifest",
            )
            return err_resp, dossier

        # Policy pre-flight check
        allowed, reason = self.policy.check_operation_authorization(adapter.manifest, op, params)
        if not allowed:
            err_resp = ConnectorResponse(success=False, data=None, error=f"Policy authorization denied: {reason}")
            dossier = VerificationDossier(
                stage=ExecutionStage.OUTCOME_UNKNOWN,
                verified=False,
                target_system=system_id,
                operation_id=operation_id,
                tool_ack_ok=False,
                target_state_query_ok=False,
                notes=f"Policy blocked: {reason}",
            )
            return err_resp, dossier

        # Execute
        raw_resp = adapter.execute_operation(operation_id, params)

        # Sanitize output via Guardrails
        sanitized_data, warnings = self.policy.validate_and_sanitize_output(raw_resp.data)
        clean_resp = ConnectorResponse(
            success=raw_resp.success,
            data=sanitized_data,
            error=raw_resp.error,
            status_code=raw_resp.status_code,
            latency_ms=raw_resp.latency_ms,
            metadata={**raw_resp.metadata, "guardrail_warnings": warnings},
        )

        # Verify
        dossier = self.verifier.verify_operation_result(adapter, operation_id, params, clean_resp)

        # Update profile if verified
        if dossier.verified:
            prof = self._profiles.get(system_id)
            if prof:
                prof.mark_verified(evidence_ref=f"evidence_{system_id}_{operation_id}")

        return clean_resp, dossier

    def _create_operation_handler(
        self,
        adapter: BaseConnectorAdapter,
        op: ConnectorOperation,
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Create a callable handler conforming to ToolRegistry specification."""
        def _handler(params: dict[str, Any]) -> dict[str, Any]:
            # Policy authorization check
            ok, err_msg = self.policy.check_operation_authorization(adapter.manifest, op, params)
            if not ok:
                raise PermissionError(f"Integration policy violation: {err_msg}")

            # Execute via adapter
            resp = adapter.execute_operation(op.operation_id, params)
            if not resp.success:
                raise RuntimeError(f"Connector operation '{op.operation_id}' failed: {resp.error}")

            # Sanitize output
            clean_data, warnings = self.policy.validate_and_sanitize_output(resp.data)
            return {
                "system_id": adapter.manifest.system_id,
                "operation_id": op.operation_id,
                "status_code": resp.status_code,
                "latency_ms": resp.latency_ms,
                "data": clean_data,
                "warnings": warnings,
            }

        return _handler
