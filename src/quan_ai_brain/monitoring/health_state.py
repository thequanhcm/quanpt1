"""Health State Machine — phân loại trạng thái hệ thống (M1.4).

Đầu vào: số liệu đo thật từ PC Health Collector / Pi5 Collector.
Đầu ra: trạng thái NORMAL/WARNING/CRITICAL/UNKNOWN/MAINTENANCE kèm lý do
(fail-honest: khi thiếu dữ liệu → UNKNOWN, KHÔNG đoán).

Nguyên tắc (AGENTS.md): không claim HEALTHY nếu chưa đo; UNKNOWN là trạng
thái hợp lệ và phải được hiển thị trung thực.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Trạng thái hợp lệ
NORMAL = "NORMAL"
WARNING = "WARNING"
CRITICAL = "CRITICAL"
UNKNOWN = "UNKNOWN"
MAINTENANCE = "MAINTENANCE"
_VALID = {NORMAL, WARNING, CRITICAL, UNKNOWN, MAINTENANCE}


@dataclass(frozen=True)
class CheckResult:
    """Kết quả một phép đo đơn lẻ."""

    check_id: str
    value: Any
    status: str
    reason: str
    measured_at: str  # ISO UTC


@dataclass
class ComponentState:
    """Trạng thái tổng hợp của một thành phần (PC, Pi5, NetChat, LLM...)."""

    component_id: str
    status: str = UNKNOWN
    checks: dict[str, CheckResult] = field(default_factory=dict)
    reason: str = ""
    updated_at: str = ""

    def apply(self, result: CheckResult, thresholds: dict[str, str]) -> None:
        """Áp kết quả đo + bảng ngưỡng {check_id: status} để tổng hợp.

        thresholds: {check_id: "NORMAL"|"WARNING"|"CRITICAL"} — người gọi
        quyết định ngưỡng; module này chỉ tổng hợp theo quy tắc xấu nhất
        thắng (worst-wins) và UNKNOWN khi không có đo.
        """
        self.checks[result.check_id] = result
        measured = {
            cid: thresholds.get(cid, UNKNOWN)
            for cid in self.checks
        }
        statuses = list(measured.values())
        if not statuses:
            self.status = UNKNOWN
            self.reason = "no_data_measured"
        else:
            self.status = _worst(statuses)
            bad = [cid for cid, st in measured.items() if st in (WARNING, CRITICAL)]
            self.reason = ",".join(bad) if bad else "all_normal"
        self.updated_at = datetime.now(timezone.utc).isoformat()


def _worst(statuses: list[str]) -> str:
    """Trạng thái xấu nhất thắng; UNKNOWN chiếm ưu thế chỉ khi toàn UNKNOWN.

    Thứ tự nghiêm trọng: CRITICAL > WARNING > UNKNOWN > NORMAL.
    (UNKNOWN đứng trên NORMAL vì thiếu dữ liệu là rủi ro cần thấy, nhưng
    không nghiêm trọng bằng đo thấy vấn đề thật.)
    """
    if CRITICAL in statuses:
        return CRITICAL
    if WARNING in statuses:
        return WARNING
    if UNKNOWN in statuses:
        return UNKNOWN
    return NORMAL


def overall_status(components: dict[str, "ComponentState"]) -> str:
    """Trạng thái tổng thể = xấu nhất trong các thành phần có dữ liệu.

    Không thành phần nào có dữ liệu → UNKNOWN (fail-honest).
    """
    statuses = [c.status for c in components.values() if c.checks]
    if not statuses:
        return UNKNOWN
    return _worst(statuses)
