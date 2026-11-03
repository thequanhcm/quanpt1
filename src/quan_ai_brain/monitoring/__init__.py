"""QUAN AI BRAIN monitoring package — System Health Intelligence (M1).

Thành phần:
- pc_collector: đo CPU/RAM/disk/process PC bằng psutil (đọc-only).
- pi5_collector: probe Pi5 qua SSH (đọc-only, BatchMode key auth).
- health_state: state machine NORMAL/WARNING/CRITICAL/UNKNOWN (fail-honest).
- alert_engine: phát cảnh báo ngưỡng + DM NetChat chống spam + lịch sử DB.
- aggregator: hợp nhất snapshot + cache TTL cho dashboard.

Tất cả module đọc-only tuyệt đối: không cài đặt, không restart, không đổi
cấu hình. Cảnh báo gửi qua NetChat DM channel chuẩn.
"""
from quan_ai_brain.monitoring.aggregator import HealthAggregator, get_global_aggregator
from quan_ai_brain.monitoring.alert_engine import AlertEngine
from quan_ai_brain.monitoring.health_monitor import HealthMonitor
from quan_ai_brain.monitoring.health_state import (
    CRITICAL,
    MAINTENANCE,
    NORMAL,
    UNKNOWN,
    WARNING,
)

__all__ = [
    "AlertEngine",
    "CRITICAL",
    "MAINTENANCE",
    "HealthAggregator",
    "HealthMonitor",
    "NORMAL",
    "UNKNOWN",
    "WARNING",
    "get_global_aggregator",
]
