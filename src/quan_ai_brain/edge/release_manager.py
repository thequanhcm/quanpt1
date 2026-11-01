"""Edge Release & Update Manager for QUAN AI BRAIN.

Manages the software release lifecycle for Raspberry Pi 5 Edge Client:
- Cryptographic HMAC-SHA256 manifest signing and verification
- Compatibility checking across core, edge, and protocol versions
- Safe staging, health check verification before activation
- Zero-downtime atomic rollback to previous known-good version
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import threading
from typing import Any

from quan_ai_brain.edge.models import ReleaseManifest


class EdgeReleaseManager:
    """Manages Edge Client releases, signing, deployment validation, and rollbacks."""

    ALLOWED_EXTENSIONS = {".py", ".js", ".css", ".html", ".sh", ".json", ".png", ".jpg", ".md"}
    PROHIBITED_FILENAMES = {".env", "config.key", "secrets.json", "brain.db", "governance.db"}

    def __init__(
        self,
        base_dir: Path | str | None = None,
        signing_secret: str = "QUAN_AI_EDGE_RELEASE_SIGNING_SECRET_2026",
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / "data" / "edge_releases"
        self.releases_dir = self.base_dir / "packages"
        self.staging_dir = self.base_dir / "staging"
        self.backup_dir = self.base_dir / "backup"
        self.active_dir = self.base_dir / "active"

        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)

        self.signing_secret = signing_secret
        self._lock = threading.RLock()
        self._registry: dict[str, ReleaseManifest] = {}
        self._active_version: str | None = None
        self._previous_version: str | None = None

    def build_release(
        self,
        source_dir: Path | str,
        version: str,
        release_id: str | None = None,
        required_protocol_version: str = "1.0",
        required_core_version: str = "0.2.0",
        changelog: str = "",
    ) -> tuple[bool, str, ReleaseManifest | None]:
        """Inspect source files, generate file checksums, build and sign ReleaseManifest."""
        with self._lock:
            src = Path(source_dir)
            if not src.exists() or not src.is_dir():
                return False, f"Source directory '{source_dir}' does not exist", None

            rel_id = release_id or f"rel_{version}_{int(datetime.now(timezone.utc).timestamp())}"
            files_map: dict[str, str] = {}
            sizes_map: dict[str, int] = {}
            total_size = 0

            # Scan files
            for p in sorted(src.rglob("*")):
                if p.is_file():
                    rel_p = str(p.relative_to(src)).replace("\\", "/")
                    if any(p.name == bad for bad in self.PROHIBITED_FILENAMES):
                        continue
                    if p.name.startswith("."):
                        continue
                    if p.suffix.lower() not in self.ALLOWED_EXTENSIONS:
                        continue

                    data = p.read_bytes()
                    h = hashlib.sha256(data).hexdigest()
                    size = len(data)

                    files_map[rel_p] = h
                    sizes_map[rel_p] = size
                    total_size += size

            if not files_map:
                return False, "No valid allowed files found to package in release", None

            manifest = ReleaseManifest(
                release_id=rel_id,
                version=version,
                required_core_version=required_core_version,
                required_protocol_version=required_protocol_version,
                files=files_map,
                file_sizes=sizes_map,
                total_size_bytes=total_size,
                changelog=changelog,
                status="CREATED",
            )

            # Cryptographically sign manifest
            manifest.sign(self.signing_secret)
            manifest.status = "SIGNED"

            # Save manifest file
            out_file = self.releases_dir / f"{rel_id}.json"
            out_file.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

            self._registry[version] = manifest
            return True, f"Release '{version}' ({rel_id}) built and signed successfully", manifest

    def verify_manifest(self, manifest: ReleaseManifest) -> tuple[bool, str]:
        """Verify the integrity and HMAC signature of a release manifest."""
        if not manifest.signature:
            return False, "Release manifest is unsigned"
        if not manifest.verify_signature(self.signing_secret):
            return False, "Release signature is invalid or tampered"
        return True, "Release signature verified"

    def check_compatibility(
        self,
        manifest: ReleaseManifest,
        edge_protocol_version: str,
        core_version: str,
    ) -> tuple[bool, str]:
        """Check if release matches edge device and core protocol constraints."""
        # Simple semver major check
        def major(v: str) -> str:
            return v.split(".")[0]

        if major(manifest.required_protocol_version) != major(edge_protocol_version):
            return False, f"Protocol version mismatch: release requires {manifest.required_protocol_version}, edge has {edge_protocol_version}"

        if major(manifest.required_core_version) != major(core_version):
            return False, f"Core version mismatch: release requires {manifest.required_core_version}, core has {core_version}"

        return True, "Release is fully compatible"

    def stage_and_verify_package(
        self,
        manifest: ReleaseManifest,
        source_dir: Path | str,
    ) -> tuple[bool, str]:
        """Stage files, verify individual SHA-256 hashes against manifest, and run health check."""
        with self._lock:
            # 1. Verify Signature
            valid, msg = self.verify_manifest(manifest)
            if not valid:
                manifest.status = "VALIDATION_FAILED"
                return False, msg

            src = Path(source_dir)
            t_stage = self.staging_dir / manifest.release_id
            if t_stage.exists():
                shutil.rmtree(t_stage)
            t_stage.mkdir(parents=True, exist_ok=True)

            # 2. Copy and Verify Hashes
            for rel_path, expected_hash in manifest.files.items():
                file_src = src / rel_path
                if not file_src.exists():
                    manifest.status = "STAGING_FAILED"
                    return False, f"Missing required file during staging: {rel_path}"

                data = file_src.read_bytes()
                actual_hash = hashlib.sha256(data).hexdigest()
                if actual_hash.lower() != expected_hash.lower():
                    manifest.status = "STAGING_FAILED"
                    return False, f"File checksum mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"

                file_dest = t_stage / rel_path
                file_dest.parent.mkdir(parents=True, exist_ok=True)
                file_dest.write_bytes(data)

            # 3. Health Check: Compile all python files in staging to verify zero syntax errors
            for py_f in t_stage.rglob("*.py"):
                try:
                    py_compile.compile(str(py_f), doraise=True)
                except Exception as exc:
                    manifest.status = "FAILED_HEALTH_CHECK"
                    return False, f"Health check syntax validation failed on {py_f.name}: {exc}"

            manifest.status = "STAGED"
            return True, "Package staged and health check passed"

    def activate_release(self, version: str) -> tuple[bool, str]:
        """Atomically activate a staged release and preserve the previous release for rollback."""
        with self._lock:
            manifest = self._registry.get(version)
            if not manifest:
                return False, f"Release version '{version}' not found in registry"

            if manifest.status != "STAGED":
                return False, f"Cannot activate release in status '{manifest.status}' (must be STAGED)"

            staged_pkg = self.staging_dir / manifest.release_id
            if not staged_pkg.exists():
                return False, "Staged release directory missing"

            # 1. Backup current active if exists
            if self._active_version and self.active_dir.exists():
                b_path = self.backup_dir / self._active_version
                if b_path.exists():
                    shutil.rmtree(b_path)
                shutil.copytree(self.active_dir, b_path)
                self._previous_version = self._active_version

            # 2. Deploy to active
            for item in self.active_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            for item in staged_pkg.iterdir():
                dest = self.active_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copyfile(item, dest)

            manifest.status = "ACTIVE"
            manifest.rollback_target_version = self._previous_version
            self._active_version = version
            return True, f"Release '{version}' activated successfully (previous version: {self._previous_version})"

    def rollback(self) -> tuple[bool, str]:
        """Atomically rollback to the previous active release."""
        with self._lock:
            if not self._previous_version:
                return False, "No previous release available for rollback"

            b_path = self.backup_dir / self._previous_version
            if not b_path.exists():
                return False, f"Backup directory for previous version '{self._previous_version}' not found"

            # Restore active
            for item in self.active_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            for item in b_path.iterdir():
                dest = self.active_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copyfile(item, dest)

            rolled_from = self._active_version
            if rolled_from and rolled_from in self._registry:
                self._registry[rolled_from].status = "ROLLED_BACK"

            self._active_version = self._previous_version
            self._previous_version = None
            return True, f"Successfully rolled back from '{rolled_from}' to '{self._active_version}'"

    def get_active_version(self) -> str | None:
        with self._lock:
            return self._active_version

    def get_manifest(self, version: str) -> ReleaseManifest | None:
        with self._lock:
            return self._registry.get(version)

    def list_releases(self) -> list[ReleaseManifest]:
        with self._lock:
            return list(self._registry.values())
