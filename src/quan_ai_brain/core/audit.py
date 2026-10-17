"""Append-only JSONL audit logger scoped to the project workspace."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.tools.path_guard import PathGuard


class AuditLogger:
    def __init__(self, workspace: str | Path, relative_log_path: str = "logs/audit.jsonl") -> None:
        self.workspace = Path(workspace).resolve()
        self.guard = PathGuard(self.workspace)
        self.log_path = self.guard.resolve(relative_log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, details: dict[str, Any] | None = None) -> None:
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event_type": redact_value(event_type),
            "details": redact_value(details or {}),
        }
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
