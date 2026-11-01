"""Mobile platform backend subsystem (V24) for QUAN AI BRAIN.

Offline sync engine + push notifications. SIMULATED: server is an
in-memory stub; no HTTP, no SQLite, no FCM/APNs, no Redis.
"""

from quan_ai_brain.mobile.notifications import NotificationService
from quan_ai_brain.mobile.offline_sync import OfflineSyncEngine

__all__ = ["NotificationService", "OfflineSyncEngine"]
