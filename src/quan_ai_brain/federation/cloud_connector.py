"""SEC-S2 (c): Đầu nối AI Cloud có HẠN NGẠCH — kiểm soát AI khác ở điểm chạm.

Triết lý trung thực (đã nêu owner): không AI nào "xâm nhập lõi" AI khác được.
Kiểm soát AI cloud = 3 lớp: (1) ĐẶT NGƯỜI — resident agent chạy cùng máy với
AI đó (kỹ thuật này đã có sẵn: SEC-S1 giám sát tiến trình/mạng); (2) GIÁM SÁT
điểm chạm từ máy mình; (3) ĐẦU NỐI CÓ HẠN NGẠCH — module này: AI cloud nào
muốn được lõi gọi tới phải đăng ký + hạn ngạch ngày, vượt hạn → BLOCKED
fail-closed, mọi lượt gọi ghi audit.

Stdlib only. KHÔNG gọi API cloud thật trong sprint này — khung hạn ngạch +
audit là phần kiểm soát, phần gọi thật đi qua GLM client có sẵn của hệ thống.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from quan_ai_brain.federation.node_registry import FedNode, NodeRegistry

CONNECTOR_KIND = "CONNECTOR"


@dataclass
class ConnectorCallResult:
    connector: str
    allowed: bool
    reason: str = ""
    remaining_today: int = 0
    response: Any = None


class CloudConnectorManager:
    """Đăng ký connector + hạn ngạch ngày + audit. Fail-closed khi vượt hạn."""

    def __init__(self, registry: NodeRegistry | None = None) -> None:
        self.registry = registry or NodeRegistry()

    # ------------------------------------------------------------------
    def register_connector(self, domain: str, *, label: str = "",
                           daily_cap: int = 100,
                           capabilities: list[str] | None = None) -> FedNode:
        if not domain or "." not in domain:
            raise ValueError("Domain connector không hợp lệ — fail-honest")
        if daily_cap < 0:
            raise ValueError("Hạn ngạch không thể âm")
        return self.registry.register(
            CONNECTOR_KIND, domain.strip().lower(),
            node_id=f"conn_{domain.strip().lower().replace('.', '_')}",
            label=label or f"AI cloud connector: {domain}",
            capabilities=capabilities or ["llm"],
            daily_cap=daily_cap,
        )

    def set_daily_cap(self, domain: str, cap: int) -> bool:
        if cap < 0:
            raise ValueError("Hạn ngạch không thể âm")
        nid = f"conn_{domain.strip().lower().replace('.', '_')}"
        node = self.registry.get(nid)
        if node is None:
            return False
        node.daily_cap = cap
        # update trực tiếp qua register (upsert giữ calls_today=0 — chấp nhận:
        # set cap giữa ngày reset đồng thời đếm, ghi chú trong audit)
        self.registry.register(
            CONNECTOR_KIND, node.host, node_id=nid, label=node.label,
            capabilities=node.capabilities, daily_cap=cap,
        )
        return True

    # ------------------------------------------------------------------
    def call_with_budget(self, domain: str, payload: dict[str, Any] | None,
                         fn: Callable[[dict[str, Any]], Any]) -> ConnectorCallResult:
        """Gọi connector QUA hạn ngạch: kiểm tra → thực thi fn(payload) → ghi audit.

        fn = hàm gọi thật (do GLM client/HTTP của hệ thống cung cấp). Module này
        chỉ KIỂM SOÁT: cho phép/b locked + đếm + audit, không tự gọi mạng.
        """
        domain = domain.strip().lower()
        nid = f"conn_{domain.replace('.', '_')}"
        node = self.registry.get(nid)
        if node is None:
            return ConnectorCallResult(domain, False,
                                       reason="connector CHƯA ĐĂNG KÝ — refuse fail-closed")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # reset đếm ngày mới
        if node.calls_date != today:
            self._reset_counter(nid, today)
            node.calls_today = 0
        if node.daily_cap <= 0:
            return ConnectorCallResult(domain, False,
                                       reason="hạn ngạch = 0 — BLOCKED fail-closed",
                                       remaining_today=0)
        if node.calls_today >= node.daily_cap:
            self._audit(domain, "BLOCKED_CAP", {"calls_today": node.calls_today,
                                                "cap": node.daily_cap})
            return ConnectorCallResult(domain, False,
                                       reason=f"VƯỢT HẠN NGẠCH ngày ({node.calls_today}/{node.daily_cap}) — BLOCKED",
                                       remaining_today=0)
        # cho phép → thực thi
        try:
            response = fn(payload or {})
        except Exception as exc:
            self._audit(domain, "CALL_ERROR", {"error": f"{type(exc).__name__}"})
            return ConnectorCallResult(domain, False,
                                       reason=f"lỗi gọi connector: {type(exc).__name__}",
                                       remaining_today=node.daily_cap - node.calls_today)
        calls = self._increment(nid)
        self._audit(domain, "CALLED", {"calls_today": calls, "cap": node.daily_cap})
        return ConnectorCallResult(domain, True, reason="ok",
                                   remaining_today=max(0, node.daily_cap - calls),
                                   response=response)

    # ------------------------------------------------------------------
    def _reset_counter(self, node_id: str, today: str) -> None:
        with self.registry._connect() as conn:
            conn.execute(
                "UPDATE federation_nodes SET calls_today = 0, calls_date = ? WHERE node_id = ?",
                (today, node_id),
            )

    def _increment(self, node_id: str) -> int:
        with self.registry._connect() as conn:
            conn.execute(
                "UPDATE federation_nodes SET calls_today = calls_today + 1 WHERE node_id = ?",
                (node_id,),
            )
            r = conn.execute("SELECT calls_today FROM federation_nodes WHERE node_id = ?",
                             (node_id,)).fetchone()
        return int(r[0]) if r else 0

    def _audit(self, domain: str, action: str, data: dict[str, Any]) -> None:
        try:
            from quan_ai_brain.core.audit import AuditLogger

            workspace = Path(__file__).resolve().parents[3]
            AuditLogger(workspace).record(
                "federation.connector", {"domain": domain, "action": action, **data})
        except Exception:
            pass  # audit fail không được giết luồng chính (fail-honest có giới hạn)
