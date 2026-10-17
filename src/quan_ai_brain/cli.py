"""Safe local CLI for self-check and explicit memory sandbox operations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from quan_ai_brain.daemon.health import health_as_dict
from quan_ai_brain.memory.sqlite_store import MemoryStore


def _project_root() -> Path:
    # Resolve to the current working directory so user commands operate only when run
    # from the intended project workspace. Do not silently infer an E: drive location.
    return Path.cwd().resolve()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(prog="quan-ai-brain", description="QUAN AI BRAIN Sprint 1 CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-check", help="Report basic runtime health")
    add = sub.add_parser("memory-add", help="Add an episodic record to the local project database")
    add.add_argument("--summary", required=True)
    add.add_argument("--source", default="manual")
    add.add_argument("--kind", default="task")
    list_cmd = sub.add_parser("memory-list", help="List recent episodic records")
    list_cmd.add_argument("--limit", type=int, default=20)

    args = parser.parse_args(argv)
    if args.command == "self-check":
        print(json.dumps(health_as_dict(), ensure_ascii=False, indent=2))
        return 0

    root = _project_root()
    db_path = root / "data" / "brain.db"
    with MemoryStore(db_path, workspace=root) as store:
        if args.command == "memory-add":
            record_id = store.add_episode(
                args.summary,
                kind=args.kind,
                source_ref=args.source,
                metadata={"created_via": "cli"},
            )
            print(f"Episode recorded: {record_id}")
            print(f"Database: {db_path.relative_to(root)}")
            return 0
        if args.command == "memory-list":
            print(json.dumps(store.list_episodes(args.limit), ensure_ascii=False, indent=2))
            return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
