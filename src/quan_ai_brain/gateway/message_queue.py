"""
V28.3 — In-Memory Message Broker (stdlib-only)

Provides:
- :class:`InMemoryMessageBroker`: topics, publish/subscribe
- Consumer groups with round-robin dispatch across members
- At-least-once semantics: messages stay in-flight until ack/nack
- nack -> requeue; after ``max_retries`` the message goes to the DLQ
- Lag metrics per subscription / consumer group

IMPORTANT SCOPE NOTE (honesty):
This is an in-memory broker simulation (Kafka/RabbitMQ/SQS semantics in
miniature). There is no persistence, no network, no real cluster. All state
lives in Python dicts/lists and dies with the process. Use it to test event
flow logic, not for production messaging.

Version: V28.3
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "BrokerError",
    "Message",
    "Subscription",
    "InMemoryMessageBroker",
]

_MSG_SEQ = itertools.count(1)


class BrokerError(Exception):
    """Base error for the message broker."""


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """A single broker message."""

    topic: str
    payload: Any
    message_id: str = field(default_factory=lambda: f"m-{next(_MSG_SEQ):08d}")
    published_at: float = field(default_factory=time.time)
    attempt: int = 0          # how many delivery attempts consumed (nacks)
    redelivered: bool = False

    def view(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "payload": self.payload,
            "attempt": self.attempt,
            "redelivered": self.redelivered,
        }


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class Subscription:
    """A subscriber on a topic — either a plain consumer or a consumer group."""

    def __init__(
        self,
        broker: "InMemoryMessageBroker",
        topic: str,
        name: str,
        handler: Optional[Callable[[Message], Any]] = None,
        is_group: bool = False,
    ) -> None:
        self.broker = broker
        self.topic = topic
        self.name = name
        self.handler = handler
        self.is_group = is_group
        self.members: List[str] = []          # for consumer groups
        self.member_index = 0                 # round-robin cursor
        self.pending: List[Message] = []      # in-flight (delivered, unacked)
        self.received: List[str] = []         # message_ids successfully consumed
        self.acked = 0
        self.nacked = 0
        self.requeued = 0
        self.dlq_count = 0
        self.errors: List[str] = []

    # -- accounting ---------------------------------------------------------

    @property
    def lag(self) -> int:
        """Consumer lag: topic backlog messages not yet delivered to this sub.

        (SQS-style semantics: in-flight unacked messages are reported
        separately via ``pending``, not counted in lag.)
        """
        return self.broker.queued_count(self.topic)

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "topic": self.topic,
            "is_group": self.is_group,
            "members": list(self.members),
            "received": len(self.received),
            "acked": self.acked,
            "nacked": self.nacked,
            "requeued": self.requeued,
            "pending": len(self.pending),
            "lag": self.lag,
            "dlq": self.dlq_count,
        }


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------

class InMemoryMessageBroker:
    """In-memory publish/subscribe broker with consumer groups.

    Delivery models:
      - plain subscription with handler: messages are dispatched immediately.
      - pull mode (no handler): messages queue in the topic backlog and are
        consumed explicitly via ``consume`` (at-least-once: they stay
        in-flight in the subscription's ``pending`` list until acked).
      - consumer group: like pull mode, but each message goes to exactly one
        member (round-robin); ack/nack is per member.
    """

    def __init__(self, max_retries: int = 3) -> None:
        if max_retries < 1:
            raise BrokerError("max_retries must be >= 1")
        self.max_retries = int(max_retries)
        self._backlog: Dict[str, List[Message]] = {}
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._dlq: List[Message] = []
        self._published_total = 0
        self._delivered_total = 0

    # -- topics ---------------------------------------------------------------

    def declare_topic(self, topic: str) -> None:
        self._backlog.setdefault(topic, [])
        self._subscriptions.setdefault(topic, [])

    def topic_exists(self, topic: str) -> bool:
        return topic in self._backlog

    def topics(self) -> List[str]:
        return list(self._backlog.keys())

    def queued_count(self, topic: str) -> int:
        return len(self._backlog.get(topic, []))

    # -- publish ---------------------------------------------------------------

    def publish(self, topic: str, payload: Any) -> Message:
        self.declare_topic(topic)
        message = Message(topic=topic, payload=payload)
        self._backlog[topic].append(message)
        self._published_total += 1
        # push to handler-based (non-group) subscribers immediately
        for sub in self._subscriptions.get(topic, []):
            if sub.handler is not None and not sub.is_group:
                self._dispatch_with_retry(sub, message)
        return message

    # -- subscribe ----------------------------------------------------------------

    def subscribe(
        self,
        topic: str,
        name: str,
        handler: Optional[Callable[[Message], Any]] = None,
    ) -> Subscription:
        self.declare_topic(topic)
        sub = Subscription(self, topic, name, handler=handler, is_group=False)
        self._subscriptions[topic].append(sub)
        return sub

    def subscribe_group(
        self,
        topic: str,
        group_name: str,
        members: List[str],
    ) -> Subscription:
        """Create a consumer group; messages round-robin across ``members``."""
        if not members:
            raise BrokerError("consumer group needs at least one member")
        self.declare_topic(topic)
        sub = Subscription(self, topic, group_name, handler=None, is_group=True)
        sub.members = list(members)
        self._subscriptions[topic].append(sub)
        return sub

    def subscriptions(self, topic: str) -> List[Subscription]:
        return list(self._subscriptions.get(topic, []))

    # -- consume / ack / nack --------------------------------------------------------

    def consume(self, topic: str, sub_name: str, max_messages: int = 10) -> List[Message]:
        """Pull up to ``max_messages`` from the backlog into a subscription's pending.

        At-least-once: messages move backlog -> pending. They are NOT removed
        from the system until ack (removed) or DLQ'd after max_retries nacks.
        """
        sub = self._require_subscription(topic, sub_name)
        backlog = self._backlog.get(topic, [])
        taken: List[Message] = []
        while backlog and len(taken) < max_messages:
            message = backlog.pop(0)
            message.redelivered = message.attempt > 0
            sub.pending.append(message)
            taken.append(message)
            self._delivered_total += 1
        return taken

    def ack(self, topic: str, sub_name: str, message_id: str) -> bool:
        sub = self._require_subscription(topic, sub_name)
        for i, message in enumerate(sub.pending):
            if message.message_id == message_id:
                del sub.pending[i]
                sub.acked += 1
                sub.received.append(message_id)
                return True
        return False

    def nack(self, topic: str, sub_name: str, message_id: str) -> bool:
        """Negative ack: increment attempt; requeue or DLQ after max_retries."""
        sub = self._require_subscription(topic, sub_name)
        for i, message in enumerate(sub.pending):
            if message.message_id == message_id:
                del sub.pending[i]
                sub.nacked += 1
                message.attempt += 1
                if message.attempt >= self.max_retries:
                    self._dlq.append(message)
                    sub.dlq_count += 1
                else:
                    # requeue at the FRONT (retry soon) and mark redelivery
                    message.redelivered = True
                    self._backlog[topic].insert(0, message)
                    sub.requeued += 1
                return True
        return False

    # -- consumer-group helpers -------------------------------------------------

    def dispatch_group(self, topic: str, group_name: str) -> Optional[Tuple[str, Message]]:
        """Deliver the next backlog message to the next group member (round-robin)."""
        sub = self._require_subscription(topic, group_name)
        if not sub.is_group:
            raise BrokerError(f"'{group_name}' is not a consumer group")
        backlog = self._backlog.get(topic, [])
        if not backlog:
            return None
        message = backlog.pop(0)
        member = sub.members[sub.member_index % len(sub.members)]
        sub.member_index += 1
        sub.pending.append(message)
        return member, message

    def group_ack(
        self, topic: str, group_name: str, member: str, message_id: str
    ) -> bool:
        if not self.ack(topic, group_name, message_id):
            return False
        return True

    def group_nack(
        self, topic: str, group_name: str, member: str, message_id: str
    ) -> bool:
        return self.nack(topic, group_name, message_id)

    # -- DLQ / metrics -----------------------------------------------------------

    def dead_letter_queue(self) -> List[Message]:
        return list(self._dlq)

    def replay_dlq(self, topic: Optional[str] = None) -> int:
        """Move DLQ messages back to their topic backlog. Returns count moved."""
        moved = 0
        remaining: List[Message] = []
        for message in self._dlq:
            if topic is None or message.topic == topic:
                message.attempt = 0
                message.redelivered = False
                self._backlog.setdefault(message.topic, []).append(message)
                moved += 1
            else:
                remaining.append(message)
        self._dlq = remaining
        return moved

    def lag_report(self) -> Dict[str, Dict[str, Any]]:
        report: Dict[str, Dict[str, Any]] = {}
        for topic, subs in self._subscriptions.items():
            topic_backlog = len(self._backlog.get(topic, []))
            report[topic] = {
                "backlog": topic_backlog,
                "subscriptions": {
                    sub.name: {
                        "pending": len(sub.pending),
                        "lag": sub.lag,
                        "acked": sub.acked,
                        "dlq": sub.dlq_count,
                    }
                    for sub in subs
                },
            }
        return report

    def global_stats(self) -> Dict[str, int]:
        return {
            "published_total": self._published_total,
            "delivered_total": self._delivered_total,
            "dlq_total": len(self._dlq),
            "topics": len(self._backlog),
        }

    # -- internals ---------------------------------------------------------------

    def _require_subscription(self, topic: str, sub_name: str) -> Subscription:
        for sub in self._subscriptions.get(topic, []):
            if sub.name == sub_name:
                return sub
        raise BrokerError(f"no subscription '{sub_name}' on topic '{topic}'")

    def _dispatch_with_retry(self, sub: Subscription, message: Message) -> None:
        """Push-dispatch to a handler subscription with retry -> DLQ."""
        attempts = 0
        while attempts < self.max_retries:
            attempts += 1
            message.attempt = attempts
            message.redelivered = attempts > 1
            try:
                sub.handler(message)  # type: ignore[misc]
                sub.acked += 1
                sub.received.append(message.message_id)
                self._delivered_total += 1
                return
            except Exception as exc:  # noqa: BLE001
                sub.nacked += 1
                sub.errors.append(f"{type(exc).__name__}: {exc}")
        self._dlq.append(message)
        sub.dlq_count += 1
