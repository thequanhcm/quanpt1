"""UAIIF-S4 (GĐ1): Agent Discovery Workflow — 7 bước khảo sát agent mới.

Master prompt UAIIF v1.0 mục IV: DISCOVERY → IDENTIFICATION →
ARCHITECTURE_INSPECTION → CAPABILITY_MAPPING → BEHAVIOR_OBSERVATION →
SECURITY_ASSESSMENT → KNOWLEDGE_CONSOLIDATION.

NGUYÊN TẮC TRUNG THỰC (mục IV): không kết luận cấu trúc bên trong nếu chưa có
tài liệu/API/telemetry đủ tin cậy — chỉ quan sát từ ngoài thì ghi rõ
"External Behavioral Assessment", không phải "Internal Architecture Inspection".
Mỗi bước trả {step, status, evidence[], notes[]}; fail-honest.
"""
from __future__ import annotations

import socket
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

# Kết quả bước
DONE = "DONE"
PARTIAL = "PARTIAL"          # làm được 1 phần, ghi rõ phần thiếu
NOT_ACCESSIBLE = "NOT_ACCESSIBLE"
SKIPPED = "SKIPPED"
STEP_STATUSES = (DONE, PARTIAL, NOT_ACCESSIBLE, SKIPPED)

STEPS = (
    "DISCOVERY", "IDENTIFICATION", "ARCHITECTURE_INSPECTION",
    "CAPABILITY_MAPPING", "BEHAVIOR_OBSERVATION", "SECURITY_ASSESSMENT",
    "KNOWLEDGE_CONSOLIDATION",
)

VN_TZ = timezone(timedelta(hours=7))

# Nhóm dịch vụ quen thuộc (chỉ để hint khi cổng mở — không kết luận vội)
_PORT_HINTS = {
    22: "SSH", 80: "HTTP", 443: "HTTPS", 1883: "MQTT", 8765: "QUAN-AI-dash",
    8766: "QUAN-AI-core", 8768: "edge-kiosk", 5000: "HTTP-alt", 8000: "HTTP-alt",
    8080: "HTTP-alt", 4747: "netdata?",
}


def _now() -> str:
    return datetime.now(VN_TZ).isoformat()


def _tcp_probe(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class AgentDiscoveryWorkflow:
    """7 bước khảo sát — mỗi bước phải có bằng chứng, không suy diễn."""

    def __init__(self, profile_store: Any, knowledge: Any,
                 node_registry: Any = None) -> None:
        self.profiles = profile_store
        self.knowledge = knowledge
        self.nodes = node_registry

    # ------------------------------------------------------------------
    def _step(self, name: str, status: str, evidence: list[str],
              notes: list[str] | None = None) -> dict[str, Any]:
        return {"step": name, "status": status,
                "evidence": evidence, "notes": notes or [],
                "assessed_at": _now()}

    def run(self, target: str, *, label: str = "", ports: tuple[int, ...] = (
            22, 80, 443, 1883, 5000, 8000, 8080, 8765, 8766, 8768)) -> dict[str, Any]:
        """Khảo sát 1 target (host/IP hoặc agent đã biết). Trả kết quả 7 bước."""
        results: list[dict[str, Any]] = []
        ev: list[str] = []
        notes: list[str] = []

        # STEP 1 — DISCOVERY: tồn tại ở đâu, cổng nào, tài liệu gì
        pingable = False
        node = None
        if self.nodes is not None:
            try:
                node = next((n for n in self.nodes.list_nodes()
                             if getattr(n, "host", "") == target), None)
            except Exception:
                node = None
        if node is not None:
            pingable = node.status == "REACHABLE"
            ev.append(f"nút liên bang {node.node_id} trạng thái {node.status}")
        else:
            pingable = self._ping(target)
            ev.append(f"ping {target}: {'phản hồi' if pingable else 'KHÔNG phản hồi'}")
        open_ports = [p for p in ports if _tcp_probe(target, p)]
        ev.append(f"cổng mở: {open_ports or '(không có trong danh sách quét)'}")
        results.append(self._step(STEPS[0],
                                  DONE if pingable or open_ports else NOT_ACCESSIBLE,
                                  ev))

        # STEP 2 — IDENTIFICATION: danh tính từ bằng chứng, không đoán
        ev, notes = [], []
        ident_fields: dict[str, tuple[str, str]] = {}
        if node is not None:
            ident_fields["Agent_Name"] = (node.label, "Observed")
            ident_fields["Provider"] = ("QUAN AI BRAIN federation", "Verified")
            ev.append(f"khớp nút liên bang: {node.node_id} ({node.kind})")
            id_status = DONE
        elif pingable:
            ident_fields["Agent_Name"] = (label or target, "Observed")
            ev.append("chỉ xác định được theo địa chỉ mạng — chưa có danh tính ứng dụng")
            notes.append("External Behavioral Assessment — chưa có tài liệu/API")
            id_status = PARTIAL
        else:
            ev.append("không tiếp cận được — không xác định danh tính")
            id_status = NOT_ACCESSIBLE
        results.append(self._step(STEPS[1], id_status, ev, notes))

        # STEP 3 — ARCHITECTURE INSPECTION: cần tài liệu/API/telemetry
        ev, notes = [], []
        if open_ports:
            arch_status = PARTIAL
            ev.append(f"quan sát được dịch vụ mạng ở cổng {open_ports} "
                      f"(hint: {', '.join(_PORT_HINTS.get(p, '?') for p in open_ports)})")
            notes.append("External Behavioral Assessment — chưa inspect bên trong được "
                         "(cần API docs/telemetry/mã nguồn được cấp quyền)")
        else:
            arch_status = NOT_ACCESSIBLE
            ev.append("không có cổng/dịch vụ nào để inspect")
        results.append(self._step(STEPS[2], arch_status, ev, notes))

        # STEP 4 — CAPABILITY MAPPING: tool/endpoint công khai thì map được
        ev, notes = [], []
        caps: list[str] = []
        if node is not None:
            caps = list(getattr(node, "capabilities", []) or [])
            ev.append(f"capabilities khai báo tại nút liên bang: {caps or '(trống)'}")
            cap_status = DONE if caps else PARTIAL
        elif open_ports:
            cap_status = PARTIAL
            ev.append(f"cổng {open_ports} gợi ý khả năng nhưng chưa có endpoint công khai để map")
            notes.append("cần API endpoint/capability manifest để map chính xác")
        else:
            cap_status = NOT_ACCESSIBLE
            ev.append("không có dữ liệu khả năng")
        results.append(self._step(STEPS[3], cap_status, ev, notes))

        # STEP 5 — BEHAVIOR OBSERVATION: cần quan sát thời gian thực
        ev, notes = [], []
        if pingable or open_ports:
            beh_status = PARTIAL
            ev.append("chưa quan sát phiên làm việc thật — cần cycle giám sát (SEC-S1/S3)")
            notes.append("hồ sơ hành vi sẽ dày lên qua các chu kỳ watchdog")
        else:
            beh_status = NOT_ACCESSIBLE
            ev.append("không quan sát được")
        results.append(self._step(STEPS[4], beh_status, ev, notes))

        # STEP 6 — SECURITY ASSESSMENT: dựa SENTINEL có sẵn
        ev, notes = [], []
        if node is not None:
            ev.append("thuộc liên bang đã đăng ký — trust/score theo SENTINEL AgentIdentityRegistry")
            sec_status = DONE
        else:
            ev.append("chưa đăng ký → phân loại UNKNOWN theo SENTINEL; "
                      "không mặc định là độc hại (mục 4 master prompt SENTINEL)")
            notes.append("mời đăng ký/audit trước khi can thiệp")
            sec_status = PARTIAL
        results.append(self._step(STEPS[5], sec_status, ev, notes))

        # STEP 7 — KNOWLEDGE CONSOLIDATION: lưu profile + kiến thức
        ev, notes = [], []
        try:
            profile_id = self.profiles.create_from_discovery(target, results, ident_fields)
            ev.append(f"Universal Agent Profile tạo/cập nhật: {profile_id}")
            con_status = DONE
        except Exception as exc:
            profile_id = None
            ev.append(f"không lưu được profile: {exc}")
            con_status = PARTIAL
        results.append(self._step(STEPS[6], con_status, ev, notes))

        return {"target": target, "label": label or target, "steps": results,
                "profile_id": profile_id,
                "assessment_type": ("Internal Architecture Inspection"
                                    if (node is not None and arch_status == DONE)
                                    else "External Behavioral Assessment")}

    @staticmethod
    def _ping(host: str) -> bool:
        # TCP ping vào cổng phổ quát trước, ICMP bằng subprocess nếu thất bại
        if _tcp_probe(host, 80, 0.8) or _tcp_probe(host, 443, 0.8):
            return True
        import subprocess

        try:
            r = subprocess.run(["ping", "-n", "1", "-w", "900", host],
                               capture_output=True, text=True, timeout=3)
            return "ttl=" in (r.stdout or "").lower()
        except Exception:
            return False
