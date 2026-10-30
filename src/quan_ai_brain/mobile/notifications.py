"""
Push Notification Service (V24.5) — QUAN AI BRAIN.

SIMULATED: FCM/APNs are in-memory mock push senders; no network, no
Firebase/Redis/PostgreSQL as sketched in the V24 plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Device registry
# ---------------------------------------------------------------------------

@dataclass
class Device:
    device_id: str
    user_id: str
    platform: str          # 'android' | 'ios'
    token: str
    registered_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "platform": self.platform,
            "token": self.token,
            "registered_at": self.registered_at,
        }


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@dataclass
class Notification:
    notif_id: str
    user_id: str
    title: str
    body: str
    priority: int = 2                # 1=low, 2=normal, 3=high, 4=critical
    idempotency_key: str = ""
    created_at: str = ""
    deep_link: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notif_id": self.notif_id,
            "user_id": self.user_id,
            "title": self.title,
            "body": self.body,
            "priority": self.priority,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
            "deep_link": self.deep_link,
            "data": dict(self.data),
        }


class TemplateEngine:
    """Renders `{placeholder}` templates against a context dict."""

    _VAR_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

    def render(self, template: str, context: Dict[str, Any]) -> str:
        def repl(match: "re.Match[str]") -> str:
            key = match.group(1)
            return str(context.get(key, match.group(0)))

        return self._VAR_RE.sub(repl, template)

    def missing_keys(self, template: str, context: Dict[str, Any]) -> List[str]:
        return [m.group(1) for m in self._VAR_RE.finditer(template)
                if m.group(1) not in context]


@dataclass
class QueuedNotification:
    """Notification wrapper carrying its enqueue order for stable sorting."""
    order: int
    notification: Notification

    def sort_key(self) -> tuple:
        # higher priority first; FIFO within the same priority
        return (-self.notification.priority, self.order)


class MockPushSender:
    """In-memory stand-in for FCM/APNs. Records every delivered payload."""

    def __init__(self) -> None:
        self.sent: List[Dict[str, Any]] = []

    def send(self, device: Device, notification: Notification) -> Dict[str, Any]:
        payload = {
            "device_id": device.device_id,
            "platform": device.platform,
            "token": device.token,
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority,
            "deep_link": notification.deep_link,
        }
        self.sent.append(payload)
        return {"ok": True, "device_id": device.device_id}


class NotificationService:
    """Register devices, render templates, enqueue with priority + dedupe,
    respecting quiet hours for low/normal priority notifications.

    SIMULATED push: MockPushSender records deliveries in memory.
    """

    PRIORITIES = {"low": 1, "normal": 2, "high": 3, "critical": 4}

    def __init__(self, sender: Optional[MockPushSender] = None,
                 clock: Optional[Any] = None) -> None:
        self.sender = sender or MockPushSender()
        self._clock = clock or (lambda: datetime.now())
        self.devices: Dict[str, Device] = {}
        self.templates: Dict[str, str] = {}
        self.queue: List[QueuedNotification] = []
        self.delivered: List[Notification] = []
        self.suppressed: List[Dict[str, Any]] = []
        self._idempotency_seen: Dict[str, str] = {}
        self._enqueue_order = 0
        self.quiet_start = dtime(22, 0)   # 22:00
        self.quiet_end = dtime(7, 0)      # 07:00

    # -- devices ---------------------------------------------------------------

    def register_device(self, device_id: str, user_id: str, platform: str,
                        token: str) -> Device:
        if platform not in ("android", "ios"):
            raise ValueError(f"unsupported platform: {platform}")
        device = Device(
            device_id=device_id,
            user_id=user_id,
            platform=platform,
            token=token,
            registered_at=self._clock().isoformat(),
        )
        self.devices[device_id] = device
        return device

    def devices_for_user(self, user_id: str) -> List[Device]:
        return [d for d in self.devices.values() if d.user_id == user_id]

    # -- templates ---------------------------------------------------------------

    def add_template(self, name: str, template: str) -> str:
        self.templates[name] = template
        return name

    def render_template(self, name: str, context: Dict[str, Any]) -> Notification:
        if name not in self.templates:
            raise KeyError(f"template not found: {name}")
        rendered = self.templates[name]
        title = self._render_part(rendered, "title", context)
        body = self._render_part(rendered, "body", context)
        prio = context.get("priority", "normal")
        if isinstance(prio, str):
            prio = self.PRIORITIES.get(prio, 2)
        return Notification(
            notif_id=f"n{self._enqueue_order + 1}",
            user_id=context.get("user_id", ""),
            title=title,
            body=body,
            priority=prio,
            idempotency_key=context.get("idempotency_key", ""),
            deep_link=context.get("deep_link", ""),
            data={k: v for k, v in context.items()
                  if k not in ("title", "body", "priority", "user_id",
                               "idempotency_key", "deep_link")},
        )

    def _render_part(self, template: str, part: str,
                     context: Dict[str, Any]) -> str:
        # template format: "title=... | body=..." or a bare body text
        for chunk in template.split("|"):
            chunk = chunk.strip()
            if chunk.lower().startswith(f"{part}="):
                return TemplateEngine().render(chunk[len(part) + 1:], context)
        # fallback: treat whole template as body
        return TemplateEngine().render(template, context)

    # -- quiet hours -----------------------------------------------------------

    def _in_quiet_hours(self, when: datetime) -> bool:
        t = when.time()
        if self.quiet_start <= self.quiet_end:
            return self.quiet_start <= t <= self.quiet_end
        # wraps midnight (22:00 -> 07:00)
        return t >= self.quiet_start or t <= self.quiet_end

    # -- enqueue + flush -----------------------------------------------------------

    def enqueue(self, notification: Notification) -> Optional[str]:
        """Dedupe by idempotency key, then add to the priority queue.

        Returns notification id, or None when suppressed as duplicate.
        """
        if notification.idempotency_key:
            if notification.idempotency_key in self._idempotency_seen:
                self.suppressed.append({
                    "reason": "duplicate",
                    "idempotency_key": notification.idempotency_key,
                    "first_notif_id": self._idempotency_seen[notification.idempotency_key],
                })
                return None
            self._idempotency_seen[notification.idempotency_key] = notification.notif_id
        self._enqueue_order += 1
        notification.created_at = self._clock().isoformat()
        self.queue.append(QueuedNotification(
            order=self._enqueue_order, notification=notification))
        return notification.notif_id

    def flush(self) -> List[Dict[str, Any]]:
        """Deliver queued notifications in priority order, honoring quiet hours.

        High/critical priorities bypass quiet hours; low/normal are deferred
        (kept in queue) until quiet hours end.
        """
        self.queue.sort(key=lambda q: q.sort_key())
        delivered_payloads: List[Dict[str, Any]] = []
        remaining: List[QueuedNotification] = []
        now = self._clock()
        quiet = self._in_quiet_hours(now)

        for qn in self.queue:
            n = qn.notification
            if quiet and n.priority < 3:
                self.suppressed.append({
                    "reason": "quiet_hours",
                    "notif_id": n.notif_id,
                })
                remaining.append(qn)
                continue
            for device in self.devices_for_user(n.user_id):
                self.sender.send(device, n)
            self.delivered.append(n)
            delivered_payloads.append(n.to_dict())

        self.queue = remaining
        return delivered_payloads

    def pending_count(self) -> int:
        return len(self.queue)

    def badge_count(self, user_id: str) -> int:
        return sum(1 for n in self.delivered if n.user_id == user_id)
