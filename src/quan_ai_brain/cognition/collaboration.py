"""
Real-Time Collaboration Module (V23.3)

SIMULATED real-time collaboration: sessions, membership (join/leave), a shared
state store merged with a simplified CRDT strategy (last-writer-wins per key +
minimal vector clocks), and conflict callbacks.

SIMULATED COMPONENTS (stdlib only, no network, no WebSockets):
- "Real-time" means synchronous, in-process event dispatch to registered
  callbacks. A production deployment would replace the event bus with
  WebSockets / Redis pub-sub; nothing here performs network I/O.
- The vector clock is a minimal dict-based implementation: sufficient for
  happens-before reasoning in tests, not a production CRDT library.

Version: V23.3
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import logging
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

ConflictCallback = Callable[["ConflictEvent"], None]
EventCallback = Callable[["CollabEvent"], None]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VectorClock:
    """Minimal vector clock (dict of node_id -> logical counter)."""

    def __init__(
        self,
        counts: Optional[Dict[str, int]] = None,
        _counter: Optional["itertools.count"] = None,
    ) -> None:
        self.counts: Dict[str, int] = dict(counts or {})
        self._counter = _counter if _counter is not None else itertools.count(1)

    def tick(self, node_id: str) -> Dict[str, int]:
        """Advance the clock for ``node_id`` and return a snapshot."""
        self.counts[node_id] = self.counts.get(node_id, 0) + 1
        return dict(self.counts)

    def snapshot(self) -> Dict[str, int]:
        return dict(self.counts)

    def update_from(self, other: Dict[str, int]) -> None:
        """Merge another clock's counters (point-wise max)."""
        for node_id, count in other.items():
            if count > self.counts.get(node_id, 0):
                self.counts[node_id] = count

    def compare(self, other: Dict[str, int]) -> str:
        """Return 'equal', 'before', 'after', or 'concurrent'."""
        keys = set(self.counts) | set(other)
        self_le = all(self.counts.get(k, 0) <= other.get(k, 0) for k in keys)
        other_le = all(other.get(k, 0) <= self.counts.get(k, 0) for k in keys)
        if self_le and other_le:
            return "equal"
        if self_le:
            return "before"
        if other_le:
            return "after"
        return "concurrent"

    def next_seq(self) -> int:
        """Monotonic sequence number for event ordering (LWW tie-breaks)."""
        return next(self._counter)


@dataclass
class Participant:
    """A member of a collaboration session."""

    participant_id: str
    display_name: str = ""
    role: str = "member"  # 'owner' | 'member' | 'observer'
    joined_at: str = field(default_factory=_utc_now_iso)
    online: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "display_name": self.display_name,
            "role": self.role,
            "joined_at": self.joined_at,
            "online": self.online,
        }


@dataclass
class StateEntry:
    """One shared-state value with LWW metadata."""

    value: Any
    writer_id: str
    lamport: int  # logical timestamp for last-writer-wins
    clock: Dict[str, int]
    written_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "writer_id": self.writer_id,
            "lamport": self.lamport,
            "clock": dict(self.clock),
            "written_at": self.written_at,
        }


@dataclass
class ConflictEvent:
    """Describes a concurrent-write conflict delivered to conflict callbacks."""

    session_id: str
    key: str
    winner_id: str
    winner_value: Any
    loser_id: str
    loser_value: Any
    resolution: str = "last_writer_wins"
    occurred_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "key": self.key,
            "winner_id": self.winner_id,
            "winner_value": self.winner_value,
            "loser_id": self.loser_id,
            "loser_value": self.loser_value,
            "resolution": self.resolution,
            "occurred_at": self.occurred_at,
        }


@dataclass
class CollabEvent:
    """Session lifecycle / membership event pushed to subscribers."""

    event_type: str  # 'session_created' | 'join' | 'leave' | 'state_update' | 'conflict'
    session_id: str
    participant_id: Optional[str]
    detail: Dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "detail": dict(self.detail),
            "occurred_at": self.occurred_at,
        }


@dataclass
class CollaborationSession:
    """A real-time collaboration session (simulated)."""

    session_id: str
    topic: str = ""
    owner_id: str = ""
    created_at: str = field(default_factory=_utc_now_iso)
    participants: Dict[str, Participant] = field(default_factory=dict)
    state: Dict[str, StateEntry] = field(default_factory=dict)
    clock: VectorClock = field(default_factory=VectorClock)
    events: List[CollabEvent] = field(default_factory=list)
    conflicts: List[ConflictEvent] = field(default_factory=list)
    closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "participants": {
                pid: p.to_dict() for pid, p in self.participants.items()
            },
            "state": {k: e.to_dict() for k, e in self.state.items()},
            "clock": self.clock.snapshot(),
            "closed": self.closed,
        }


class CollaborationManager:
    """Manages sessions, membership, shared state, and conflict callbacks.

    Merge policy: last-writer-wins per key, using a monotonic Lamport counter
    derived from the session's vector clock; exact Lamport ties fall back to a
    session-local monotonic sequence, so every write is totally ordered.
    Concurrent writes (per vector-clock comparison) trigger conflict callbacks.
    """

    def __init__(
        self,
        conflict_callbacks: Optional[Sequence[ConflictCallback]] = None,
        event_callbacks: Optional[Sequence[EventCallback]] = None,
    ) -> None:
        self.sessions: Dict[str, CollaborationSession] = {}
        self.conflict_callbacks: List[ConflictCallback] = list(conflict_callbacks or [])
        self.event_callbacks: List[EventCallback] = list(event_callbacks or [])

    # ---------------------------------------------------------------- sessions
    def create_session(
        self, session_id: str, topic: str = "", owner_id: str = ""
    ) -> CollaborationSession:
        if session_id in self.sessions:
            raise ValueError(f"session already exists: {session_id}")
        session = CollaborationSession(
            session_id=session_id, topic=topic, owner_id=owner_id
        )
        self.sessions[session_id] = session
        self._emit(
            session,
            CollabEvent(
                event_type="session_created",
                session_id=session_id,
                participant_id=owner_id or None,
                detail={"topic": topic},
            ),
        )
        return session

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        return self.sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session is None:
            return False
        session.closed = True
        for participant in session.participants.values():
            participant.online = False
        return True

    # ------------------------------------------------------------- membership
    def join(self, session_id: str, participant_id: str, role: str = "member") -> bool:
        """Join a session; returns False on unknown/closed session or dup join."""
        session = self.sessions.get(session_id)
        if session is None or session.closed:
            return False
        if participant_id in session.participants:
            return False
        if role not in ("owner", "member", "observer"):
            raise ValueError(f"invalid role: {role!r}")
        session.participants[participant_id] = Participant(
            participant_id=participant_id,
            role=role,
        )
        self._emit(
            session,
            CollabEvent(
                event_type="join",
                session_id=session_id,
                participant_id=participant_id,
                detail={"role": role},
            ),
        )
        return True

    def leave(self, session_id: str, participant_id: str) -> bool:
        """Leave a session; returns False if session or participant missing."""
        session = self.sessions.get(session_id)
        if session is None:
            return False
        if participant_id not in session.participants:
            return False
        del session.participants[participant_id]
        self._emit(
            session,
            CollabEvent(
                event_type="leave",
                session_id=session_id,
                participant_id=participant_id,
                detail={},
            ),
        )
        return True

    def list_participants(self, session_id: str) -> List[str]:
        session = self.sessions.get(session_id)
        if session is None:
            return []
        return sorted(session.participants)

    def online_participants(self, session_id: str) -> List[str]:
        session = self.sessions.get(session_id)
        if session is None:
            return []
        return sorted(
            pid for pid, p in session.participants.items() if p.online
        )

    # ------------------------------------------------------------ shared state
    def set_state(
        self,
        session_id: str,
        key: str,
        value: Any,
        writer_id: str,
    ) -> Tuple[bool, Optional[ConflictEvent]]:
        """Write one key with LWW merge.

        Returns (applied, conflict_event). ``conflict_event`` is not None when
        the write raced a concurrent value (vector-clock comparison) — the new
        value still wins by Lamport order, and registered conflict callbacks
        are invoked.
        """
        session = self.sessions.get(session_id)
        if session is None or session.closed:
            return False, None
        if writer_id not in session.participants:
            return False, None

        clock_snapshot = session.clock.tick(writer_id)
        lamport = session.clock.next_seq()
        existing = session.state.get(key)
        conflict: Optional[ConflictEvent] = None

        if existing is not None:
            relation = VectorClock(existing.clock).compare(clock_snapshot)
            if relation == "concurrent":
                conflict = ConflictEvent(
                    session_id=session_id,
                    key=key,
                    winner_id=writer_id,
                    winner_value=value,
                    loser_id=existing.writer_id,
                    loser_value=existing.value,
                )

        session.state[key] = StateEntry(
            value=value,
            writer_id=writer_id,
            lamport=lamport,
            clock=clock_snapshot,
        )
        self._emit(
            session,
            CollabEvent(
                event_type="state_update",
                session_id=session_id,
                participant_id=writer_id,
                detail={"key": key, "lamport": lamport},
            ),
        )
        if conflict is not None:
            session.conflicts.append(conflict)
            self._emit(
                session,
                CollabEvent(
                    event_type="conflict",
                    session_id=session_id,
                    participant_id=writer_id,
                    detail={"key": key, "resolution": conflict.resolution},
                ),
            )
            for callback in self.conflict_callbacks:
                try:
                    callback(conflict)
                except Exception as exc:  # callback fault must not break merge
                    logger.debug("conflict callback failed: %s", exc)
        return True, conflict

    def get_state(self, session_id: str, key: str) -> Optional[Any]:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        entry = session.state.get(key)
        return entry.value if entry is not None else None

    def get_state_entry(self, session_id: str, key: str) -> Optional[StateEntry]:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        return session.state.get(key)

    def all_state(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if session is None:
            return {}
        return {k: e.value for k, e in session.state.items()}

    def merge_remote_state(
        self, session_id: str, remote_state: Dict[str, StateEntry]
    ) -> int:
        """Merge a remote state snapshot (point-wise LWW by lamport)."""
        session = self.sessions.get(session_id)
        if session is None:
            return 0
        merged = 0
        for key, remote_entry in remote_state.items():
            local_entry = session.state.get(key)
            if local_entry is None or remote_entry.lamport > local_entry.lamport:
                session.state[key] = remote_entry
                merged += 1
        session.clock.update_from(
            {
                node: max(
                    (e.clock.get(node, 0) for e in session.state.values()), default=0
                )
                for node in set().union(
                    *(e.clock for e in session.state.values())
                )
            }
            if session.state
            else {}
        )
        return merged

    # ------------------------------------------------------------------ events
    def add_event_callback(self, callback: EventCallback) -> None:
        self.event_callbacks.append(callback)

    def add_conflict_callback(self, callback: ConflictCallback) -> None:
        self.conflict_callbacks.append(callback)

    def _emit(self, session: CollaborationSession, event: CollabEvent) -> None:
        session.events.append(event)
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as exc:  # callback fault must not break session ops
                logger.debug("event callback failed: %s", exc)

    def activity_feed(self, session_id: str) -> List[CollabEvent]:
        session = self.sessions.get(session_id)
        if session is None:
            return []
        return list(session.events)
