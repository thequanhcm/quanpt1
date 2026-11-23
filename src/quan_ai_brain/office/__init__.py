"""CHERRY Office Intelligence — lớp mỏng trên QUAN AI BRAIN (card TASK-OFFICE-S1).

Module trong gói này KHÔNG thay thế Cognitive Core/Memory/Governance — chỉ nối
các năng lực văn phòng (email, lịch, tài liệu) vào nền có sẵn.

(23/11/2026) Sprint 1 VmailConnector — card TASK-VMAIL-S1 đã APPROVED.
"""
from .email_connector import (
    EmailAnalysis,
    EmailCategory10,
    SOAPMailConnector,
    analyze_email,
    sync_and_analyze,
)
from .vmail_connector import (
    StructuredResult,
    VmailConnector,
    VmailConnectorError,
    get_connector,
)

__all__ = [
    "EmailCategory10", "EmailAnalysis", "SOAPMailConnector",
    "analyze_email", "sync_and_analyze",
    "StructuredResult", "VmailConnector", "VmailConnectorError", "get_connector",
]
