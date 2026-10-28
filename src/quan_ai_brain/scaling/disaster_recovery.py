"""
Disaster Recovery Module (V30.3) — file-based backup/restore SIMULATION.

Provides:
- DisasterRecovery: backup (snapshot manifest + copy files into a
  caller-specified backup directory), verify (existence + SHA-256),
  restore (dry-run and real restore into a caller-specified target dir)
- RTO/RPO computed from manifest timestamps (planning numbers only —
  infrastructure is NOT verified; see completion report)
- Failover state machine: primary -> failover -> promote -> failback

SIMULATION SCOPE (per V30 plan constraints):
- File copying into caller-provided directories only (tests use tmp_path).
- NEVER touches brain.db or real data/ directories — the caller chooses
  every source and target path.
- No replication daemons, no network, no external storage.

Version: V30.3
"""

import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FailoverState(Enum):
    """Failover state machine states."""
    PRIMARY = "primary"
    FAILOVER = "failover"      # failover in progress
    PROMOTED = "promoted"      # replica promoted as new primary
    FAILBACK = "failback"      # failing back to original primary
    RECONCILED = "reconciled"  # original primary restored


class FailoverError(Exception):
    """Invalid state transition in the failover machine."""


@dataclass
class BackupManifest:
    """Manifest describing one snapshot."""
    backup_id: str
    created_at: str  # ISO-8601 UTC
    source_dir: str
    files: List[Dict[str, Any]] = field(default_factory=list)
    # each entry: {path, size, sha256, mtime}
    total_bytes: int = 0
    status: str = "created"  # created | verified | failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at,
            "source_dir": self.source_dir,
            "files": [dict(f) for f in self.files],
            "total_bytes": self.total_bytes,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BackupManifest":
        return cls(
            backup_id=d["backup_id"],
            created_at=d["created_at"],
            source_dir=d["source_dir"],
            files=[dict(f) for f in d.get("files", [])],
            total_bytes=d.get("total_bytes", 0),
            status=d.get("status", "created"),
        )


@dataclass
class VerifyResult:
    """Result of backup verification."""
    backup_id: str
    valid: bool
    missing_files: List[str] = field(default_factory=list)
    hash_mismatches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "valid": self.valid,
            "missing_files": list(self.missing_files),
            "hash_mismatches": list(self.hash_mismatches),
        }


@dataclass
class RestoreResult:
    """Result of a restore operation."""
    backup_id: str
    dry_run: bool
    restored_files: List[str]
    skipped_files: List[str]
    target_dir: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "dry_run": self.dry_run,
            "restored_files": list(self.restored_files),
            "skipped_files": list(self.skipped_files),
            "target_dir": self.target_dir,
        }


@dataclass
class RtoRpo:
    """Planning RTO/RPO numbers derived from manifest timestamps.

    These are PLANNING numbers computed from recorded timestamps —
    they do not certify real infrastructure behaviour.
    """
    backup_id: str
    rto_seconds: float  # estimated restore duration
    rpo_seconds: float  # data-loss window = now - newest backup timestamp
    newest_backup_at: str
    computed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "rto_seconds": self.rto_seconds,
            "rpo_seconds": self.rpo_seconds,
            "newest_backup_at": self.newest_backup_at,
            "computed_at": self.computed_at,
        }


def _sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class DisasterRecovery:
    """File-based backup/verify/restore + failover state machine (simulated)."""

    def __init__(self, backup_root: Optional[Path] = None) -> None:
        self.backup_root = Path(backup_root) if backup_root else None
        self._manifests: Dict[str, BackupManifest] = {}
        self._failover_state = FailoverState.PRIMARY
        self._failover_history: List[Dict[str, str]] = []

    # ---------------- backup ----------------

    def create_backup(self, source_dir: Path, backup_dir: Path,
                      backup_id: Optional[str] = None) -> BackupManifest:
        """Snapshot all regular files under source_dir into backup_dir."""
        source = Path(source_dir)
        if not source.is_dir():
            raise FileNotFoundError(f"source dir does not exist: {source}")
        dest = Path(backup_dir)
        dest.mkdir(parents=True, exist_ok=True)
        bid = backup_id or f"backup-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        manifest = BackupManifest(
            backup_id=bid,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_dir=str(source),
        )
        for p in sorted(source.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(source)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            digest = _sha256_file(p)
            stat = p.stat()
            manifest.files.append({
                "path": str(rel).replace("\\", "/"),
                "size": stat.st_size,
                "sha256": digest,
                "mtime": stat.st_mtime,
            })
            manifest.total_bytes += stat.st_size
        self._manifests[bid] = manifest
        return manifest

    # ---------------- verify ----------------

    def verify_backup(self, backup_dir: Path, manifest: BackupManifest) -> VerifyResult:
        """Check each manifest file exists in backup_dir with matching SHA-256."""
        dest = Path(backup_dir)
        missing: List[str] = []
        mismatch: List[str] = []
        for entry in manifest.files:
            fpath = dest / entry["path"]
            if not fpath.is_file():
                missing.append(entry["path"])
                continue
            if _sha256_file(fpath) != entry["sha256"]:
                mismatch.append(entry["path"])
        valid = not missing and not mismatch
        if valid:
            manifest.status = "verified"
        else:
            manifest.status = "failed"
        return VerifyResult(
            backup_id=manifest.backup_id,
            valid=valid,
            missing_files=missing,
            hash_mismatches=mismatch,
        )

    # ---------------- restore ----------------

    def plan_restore(self, backup_dir: Path, manifest: BackupManifest) -> List[Dict[str, Any]]:
        """Dry-run: list planned restore actions without writing anything."""
        dest = Path(backup_dir)
        actions: List[Dict[str, Any]] = []
        for entry in manifest.files:
            fpath = dest / entry["path"]
            actions.append({
                "path": entry["path"],
                "exists_in_backup": fpath.is_file(),
                "action": "restore" if fpath.is_file() else "skip_missing",
            })
        return actions

    def restore_backup(self, backup_dir: Path, manifest: BackupManifest,
                       target_dir: Path, dry_run: bool = False) -> RestoreResult:
        """Restore manifest files into target_dir (real copy when not dry-run)."""
        dest = Path(backup_dir)
        target = Path(target_dir)
        if not dry_run:
            target.mkdir(parents=True, exist_ok=True)
        restored: List[str] = []
        skipped: List[str] = []
        for entry in manifest.files:
            fpath = dest / entry["path"]
            if not fpath.is_file():
                skipped.append(entry["path"])
                continue
            if dry_run:
                restored.append(entry["path"])
                continue
            out = target / entry["path"]
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fpath, out)
            restored.append(entry["path"])
        return RestoreResult(
            backup_id=manifest.backup_id,
            dry_run=dry_run,
            restored_files=restored,
            skipped_files=skipped,
            target_dir=str(target),
        )

    # ---------------- RTO / RPO ----------------

    def compute_rto_rpo(self, backup_dir: Path, manifest: BackupManifest,
                        now: Optional[datetime] = None) -> RtoRpo:
        """
        Planning numbers from manifest timestamps.
        RTO: proportional estimate from bytes copied (throughput assumption).
        RPO: now - newest backup created_at.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        created = datetime.fromisoformat(manifest.created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        # Assume 100 MB/s restore throughput (planning assumption, not measured)
        THROUGHPUT = 100 * 1024 * 1024
        rto = manifest.total_bytes / THROUGHPUT
        rpo = max(0.0, (now - created).total_seconds())
        return RtoRpo(
            backup_id=manifest.backup_id,
            rto_seconds=rto,
            rpo_seconds=rpo,
            newest_backup_at=manifest.created_at,
            computed_at=now.isoformat(),
        )

    def compute_rpo_from_manifests(self, manifests: List[BackupManifest],
                                   now: Optional[datetime] = None) -> float:
        """RPO across several backups = now - newest manifest timestamp."""
        if not manifests:
            return float("inf")
        if now is None:
            now = datetime.now(timezone.utc)
        now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        newest = max(datetime.fromisoformat(m.created_at) for m in manifests)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        return max(0.0, (now - newest).total_seconds())

    # ---------------- failover state machine ----------------

    @property
    def failover_state(self) -> FailoverState:
        return self._failover_state

    def _transition(self, new_state: FailoverState, note: str = "") -> None:
        self._failover_history.append({
            "from": self._failover_state.value,
            "to": new_state.value,
            "at": datetime.now(timezone.utc).isoformat(),
            "note": note,
        })
        self._failover_state = new_state

    def start_failover(self) -> FailoverState:
        if self._failover_state != FailoverState.PRIMARY:
            raise FailoverError(
                f"failover only allowed from PRIMARY (current: {self._failover_state.value})")
        self._transition(FailoverState.FAILOVER, note="primary degraded")
        return self._failover_state

    def promote_replica(self) -> FailoverState:
        if self._failover_state != FailoverState.FAILOVER:
            raise FailoverError(
                f"promote only allowed from FAILOVER (current: {self._failover_state.value})")
        self._transition(FailoverState.PROMOTED, note="replica promoted")
        return self._failover_state

    def start_failback(self) -> FailoverState:
        if self._failover_state != FailoverState.PROMOTED:
            raise FailoverError(
                f"failback only allowed from PROMOTED (current: {self._failover_state.value})")
        self._transition(FailoverState.FAILBACK, note="returning to original primary")
        return self._failover_state

    def complete_failback(self) -> FailoverState:
        if self._failover_state != FailoverState.FAILBACK:
            raise FailoverError(
                f"complete only allowed from FAILBACK (current: {self._failover_state.value})")
        self._transition(FailoverState.RECONCILED, note="original primary restored")
        return self._failover_state

    def failover_history(self) -> List[Dict[str, str]]:
        return [dict(h) for h in self._failover_history]

    # ---------------- misc ----------------

    def manifest(self, backup_id: str) -> Optional[BackupManifest]:
        return self._manifests.get(backup_id)

    def manifests(self) -> List[BackupManifest]:
        return list(self._manifests.values())

    def serialize_manifest(self, backup_id: str) -> str:
        import json
        m = self._manifests.get(backup_id)
        if m is None:
            raise KeyError(backup_id)
        return json.dumps(m.to_dict(), indent=2)
