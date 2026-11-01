"""Merge starter files into an explicitly named workspace without overwriting.

Default mode is dry-run. With --apply, only missing files are copied; conflicting
existing files are skipped and reported. Generated handoff reports, caches, data,
logs, secrets, databases, and virtual environments are never copied.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil

EXCLUDED_DIRS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", "data", "logs", "backups", "crash_dumps", "dist", "build"}
EXCLUDED_NAMES = {".env", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}
EXCLUDED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx", ".log", ".pyc"}
EXCLUDED_NAME_PARTS = ("credential", "secret", "token", "private_key")


def is_sensitive_name(name: str) -> bool:
    lower = name.lower()
    return (
        lower in EXCLUDED_NAMES
        or lower.endswith((".env", ".pem", ".key", ".p12", ".pfx"))
        or Path(lower).suffix in EXCLUDED_SUFFIXES
        or any(part in lower for part in EXCLUDED_NAME_PARTS)
    )


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 128), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def iter_sources(source: Path):
    for current, dirs, files in __import__("os").walk(source):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not is_sensitive_name(d))
        for filename in sorted(files):
            if is_sensitive_name(filename):
                continue
            full = Path(current) / filename
            relative = full.relative_to(source)
            rel_posix = relative.as_posix()
            if rel_posix.startswith("reports/") and filename != "README.md":
                continue
            yield full, relative


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Extracted starter package directory")
    parser.add_argument("--target", required=True, help="Exact QUAN AI BRAIN workspace directory")
    parser.add_argument("--apply", action="store_true", help="Copy missing files; existing files are never overwritten")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not source.is_dir():
        parser.error("--source must be an existing directory")
    if not target.is_dir():
        parser.error("--target must be an existing directory; create/confirm it first")
    if source == target or source in target.parents or target in source.parents:
        parser.error("Source and target must be separate, non-nested directories")

    actions: list[tuple[str, Path, Path]] = []
    counts = {"copy": 0, "identical": 0, "conflict": 0}
    for src, relative in iter_sources(source):
        dst = (target / relative).resolve(strict=False)
        try:
            dst.relative_to(target)
        except ValueError:
            print(f"BLOCKED PATH ESCAPE: {relative}")
            return 2
        if dst.exists():
            if dst.is_file() and src.is_file() and digest(dst) == digest(src):
                counts["identical"] += 1
                actions.append(("IDENTICAL — skip", src, dst))
            else:
                counts["conflict"] += 1
                actions.append(("CONFLICT — not overwritten", src, dst))
        else:
            counts["copy"] += 1
            actions.append(("COPY" if args.apply else "WOULD COPY", src, dst))

    mode = "APPLY (missing files only)" if args.apply else "DRY-RUN (no files changed)"
    print(f"QUAN AI BRAIN starter merge: {mode}")
    print(f"Source: {source}")
    print(f"Target: {target}")
    for action, src, dst in actions:
        print(f"[{action}] {src.relative_to(source)}")
        if action == "COPY":
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print("\nSummary:")
    print(f"- Missing files to copy/copied: {counts['copy']}")
    print(f"- Identical files skipped: {counts['identical']}")
    print(f"- Conflicts skipped without overwrite: {counts['conflict']}")
    if not args.apply:
        print("No files were changed. Review the plan, then rerun with --apply to copy missing files.")
    elif counts["conflict"]:
        print("Some conflicts remain. Review them manually; this script did not overwrite them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
