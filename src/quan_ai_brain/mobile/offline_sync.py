"""
Offline Sync Engine (V24.4) — QUAN AI BRAIN.

SIMULATED: the server is an in-memory stub (ServerStub); the local op log
is an append-only JSONL file on disk (local persistence), not SQLite.
No network calls — push/pull are direct Python method calls.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Server stub (simulated remote)
# ---------------------------------------------------------------------------

class ServerStub:
    """In-memory stand-in for the sync server. SIMULATED, no HTTP."""

    def __init__(self) -> None:
        # key -> {"value": ..., "updated_at": iso, "device_id": str}
        self.store: Dict[str, Dict[str, Any]] = {}

    def pull(self, since: str) -> Dict[str, Dict[str, Any]]:
        """Return server entries updated after `since` (ISO-8601 compare)."""
        return {k: dict(v) for k, v in self.store.items()
                if v.get("updated_at", "") > since}

    def push(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply client entries; server always records latest writer."""
        applied = 0
        for e in entries:
            key = e["key"]
            self.store[key] = {
                "value": e["value"],
                "updated_at": e["updated_at"],
                "device_id": e["device_id"],
            }
            applied += 1
        return {"applied": applied, "rejected": len(entries) - applied}


# ---------------------------------------------------------------------------
# Op log (append-only local journal)
# ---------------------------------------------------------------------------

@dataclass
class OpEntry:
    """One local offline operation."""
    op_id: str
    op_type: str            # 'set' | 'delete'
    key: str
    value: Any = None
    updated_at: str = ""    # local ISO timestamp
    device_id: str = "local"
    checkpointed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_id": self.op_id,
            "op_type": self.op_type,
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at,
            "device_id": self.device_id,
            "checkpointed": self.checkpointed,
        }


@dataclass
class Conflict:
    """Same key written with different values on client and server."""
    key: str
    local_value: Any
    server_value: Any
    local_updated_at: str
    server_updated_at: str
    resolution: str = ""      # '', 'local_wins', 'server_wins', 'rollback'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "local_value": self.local_value,
            "server_value": self.server_value,
            "local_updated_at": self.local_updated_at,
            "server_updated_at": self.server_updated_at,
            "resolution": self.resolution,
        }


@dataclass
class SyncReport:
    """Outcome of one sync() run."""
    pushed: int = 0
    pulled: int = 0
    conflicts: List[Conflict] = field(default_factory=list)
    rolled_back: List[str] = field(default_factory=list)
    checkpoints: int = 0
    completed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pushed": self.pushed,
            "pulled": self.pulled,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "rolled_back": list(self.rolled_back),
            "checkpoints": self.checkpoints,
            "completed": self.completed,
            "error": self.error,
        }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OfflineSyncEngine:
    """Local-first sync with append-only op log, push/pull, LWW conflicts.

    Design:
    - Local ops are appended to a JSONL op log (append-only file).
    - Local materialized state is kept in memory (`state` dict).
    - sync(): pull server changes since last checkpoint, detect conflicts
      (same key, different value), resolve last-writer-wins by comparing
      updated_at timestamps, push local pending ops, checkpoint.
    - rollback: failed sync restores local state from the pre-sync snapshot.
    - checkpoint/resume: pending (non-checkpointed) ops survive process
      restart because the op log file is re-read on init.
    """

    def __init__(self, server: ServerStub, op_log_path: str,
                 device_id: str = "local", clock: Optional[Any] = None) -> None:
        self.server = server
        self.op_log_path = op_log_path
        self.device_id = device_id
        self._clock = clock or _utcnow_iso
        self.state: Dict[str, Any] = {}
        self._ops: List[OpEntry] = []
        self.last_checkpoint: str = ""
        self._load_log()
        self._materialize()

    # -- persistence ----------------------------------------------------------

    def _load_log(self) -> None:
        if not os.path.exists(self.op_log_path):
            return
        with open(self.op_log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                self._ops.append(OpEntry(
                    op_id=d["op_id"],
                    op_type=d["op_type"],
                    key=d["key"],
                    value=d.get("value"),
                    updated_at=d.get("updated_at", ""),
                    device_id=d.get("device_id", "local"),
                    checkpointed=bool(d.get("checkpointed", False)),
                ))

    def _append(self, entry: OpEntry) -> None:
        self._ops.append(entry)
        with open(self.op_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def _materialize(self) -> None:
        """Rebuild in-memory state by replaying the op log in order."""
        state: Dict[str, Any] = {}
        for op in self._ops:
            if op.op_type == "set":
                state[op.key] = op.value
            elif op.op_type == "delete":
                state.pop(op.key, None)
        self.state = state

    # -- local operations (offline-first) --------------------------------------

    def local_set(self, key: str, value: Any) -> OpEntry:
        entry = OpEntry(
            op_id=f"{self.device_id}-{len(self._ops) + 1}",
            op_type="set",
            key=key,
            value=value,
            updated_at=self._clock(),
            device_id=self.device_id,
        )
        self._append(entry)
        self.state[key] = value
        return entry

    def local_delete(self, key: str) -> OpEntry:
        entry = OpEntry(
            op_id=f"{self.device_id}-{len(self._ops) + 1}",
            op_type="delete",
            key=key,
            value=None,
            updated_at=self._clock(),
            device_id=self.device_id,
        )
        self._append(entry)
        self.state.pop(key, None)
        return entry

    def pending_ops(self) -> List[OpEntry]:
        """Ops not yet acknowledged by a checkpoint (resume surface)."""
        return [op for op in self._ops if not op.checkpointed]

    # -- conflict handling -------------------------------------------------------

    def _detect_conflicts(self, server_entries: Dict[str, Dict[str, Any]]) -> List[Conflict]:
        conflicts: List[Conflict] = []
        for op in self.pending_ops():
            if op.op_type != "set":
                continue
            srv = server_entries.get(op.key)
            if srv is None:
                continue
            if srv["value"] != op.value:  # same key, different value
                conflicts.append(Conflict(
                    key=op.key,
                    local_value=op.value,
                    server_value=srv["value"],
                    local_updated_at=op.updated_at,
                    server_updated_at=srv.get("updated_at", ""),
                ))
        return conflicts

    def _resolve_lww(self, conflict: Conflict) -> str:
        """Last-writer-wins: compare ISO timestamps lexicographically."""
        if conflict.local_updated_at >= conflict.server_updated_at:
            return "local_wins"
        return "server_wins"

    # -- sync ---------------------------------------------------------------------

    def sync(self, resolution: str = "lww") -> SyncReport:
        """One full push/pull cycle with conflict resolution + checkpoint.

        resolution: 'lww' (default) or 'rollback' (always roll local back).
        """
        report = SyncReport()
        pre_sync_state = dict(self.state)

        try:
            server_entries = self.server.pull(self.last_checkpoint)

            # 1. detect conflicts between pending local ops and server state
            conflicts = self._detect_conflicts(server_entries)
            report.conflicts = conflicts

            rolled_back: List[str] = []
            for c in conflicts:
                if resolution == "rollback":
                    c.resolution = "rollback"
                    rolled_back.append(c.key)
                elif self._resolve_lww(c) == "server_wins":
                    c.resolution = "server_wins"
                    # adopt server value locally
                    self.state[c.key] = c.server_value
                    rolled_back.append(c.key)
                else:
                    c.resolution = "local_wins"
            report.rolled_back = rolled_back

            # 2. push local pending ops that were not overridden
            push_entries: List[Dict[str, Any]] = []
            for op in self.pending_ops():
                conflict_for_key = next(
                    (c for c in conflicts if c.key == op.key), None)
                if conflict_for_key and conflict_for_key.resolution != "local_wins":
                    continue  # server won; local op is discarded
                if op.op_type == "set":
                    push_entries.append({
                        "key": op.key,
                        "value": op.value,
                        "updated_at": op.updated_at,
                        "device_id": op.device_id,
                    })
                elif op.op_type == "delete":
                    # deletion is represented as a tombstone value
                    push_entries.append({
                        "key": op.key,
                        "value": None,
                        "updated_at": op.updated_at,
                        "device_id": op.device_id,
                    })
            push_result = self.server.push(push_entries)
            report.pushed = push_result["applied"]

            # 3. apply server-side changes to local state
            pulled = 0
            for key, srv in server_entries.items():
                winner = next((c for c in conflicts if c.key == key), None)
                if winner and winner.resolution == "local_wins":
                    continue
                if key not in self.state or self.state[key] != srv["value"]:
                    self.state[key] = srv["value"]
                    pulled += 1
            report.pulled = pulled

            # 4. checkpoint: mark all ops as acknowledged
            for op in self._ops:
                op.checkpointed = True
            report.checkpoints = 1
            self.last_checkpoint = self._clock()
            report.completed = True
            return report

        except Exception as exc:  # rollback path
            self.state = pre_sync_state
            report.error = str(exc)
            report.completed = False
            return report
