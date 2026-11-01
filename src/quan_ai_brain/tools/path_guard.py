"""Constrain file paths to a single workspace root."""
from __future__ import annotations

from pathlib import Path, PureWindowsPath


class PathOutsideWorkspaceError(ValueError):
    """Raised when a requested path is not safely inside the workspace."""


class PathGuard:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        if not self.workspace.exists() or not self.workspace.is_dir():
            raise ValueError("Workspace must exist and be a directory")

    def resolve(self, requested_path: str | Path) -> Path:
        raw = str(requested_path)
        windows_path = PureWindowsPath(raw)
        given_path = Path(raw)
        if given_path.is_absolute() or windows_path.drive or raw.startswith(("\\\\", "//")):
            raise PathOutsideWorkspaceError("Absolute paths are not accepted")
        candidate = (self.workspace / given_path).resolve(strict=False)
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise PathOutsideWorkspaceError("Path escapes the QUAN AI BRAIN workspace") from exc
        return candidate
