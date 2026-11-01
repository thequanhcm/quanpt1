"""Minimal health snapshot for future supervisor integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
import sys


@dataclass(frozen=True)
class HealthSnapshot:
    status: str
    timestamp_utc: str
    python_version: str
    process_id: int
    note: str


def get_health_snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        status="ok",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version.split()[0],
        process_id=os.getpid(),
        note="Health-only skeleton; daemon supervision is not implemented.",
    )


def health_as_dict() -> dict[str, object]:
    return asdict(get_health_snapshot())
