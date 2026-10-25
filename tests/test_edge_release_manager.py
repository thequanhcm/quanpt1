"""Unit and Integration Tests for EdgeReleaseManager (U01 - U10).

Verifies:
- U01: Build edge release package.
- U02: Verify manifest structure and SHA-256 file hashes.
- U03: Verify valid cryptographic HMAC-SHA256 signature.
- U04: Reject unsigned or tampered release manifest.
- U05: Reject incompatible protocol or core versions.
- U06: Staging and health check (py_compile verification).
- U07: Simulate health check failure on invalid python syntax.
- U08: Atomic rollback to previous working version.
- U09: Disrupted transfer / staging failure cleanup.
- U10: Ensure previous active version is safely preserved and not prematurely deleted.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import pytest

from quan_ai_brain.edge.models import ReleaseManifest
from quan_ai_brain.edge.release_manager import EdgeReleaseManager


@pytest.fixture
def release_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "release_mgr"
        src_dir = Path(tmpdir) / "pkg_src"
        src_dir.mkdir(parents=True, exist_ok=True)

        # Create valid client files in source
        (src_dir / "client_daemon.py").write_text(
            "def main():\n    print('Edge Client v1.0 running')\n\nif __name__ == '__main__':\n    main()\n",
            encoding="utf-8",
        )
        (src_dir / "avatar_engine.js").write_text(
            "console.log('Avatar Engine Model F ready');\n",
            encoding="utf-8",
        )
        (src_dir / "README.md").write_text("# Edge Client Readme\n", encoding="utf-8")

        mgr = EdgeReleaseManager(
            base_dir=base_dir,
            signing_secret="TEST_SIGNING_SECRET_KEY_999",
        )
        yield mgr, src_dir, base_dir


def test_u01_build_edge_package(release_env):
    """U01: Build edge release package from source directory."""
    mgr, src_dir, base_dir = release_env

    ok, msg, manifest = mgr.build_release(
        source_dir=src_dir,
        version="1.0.0",
        required_protocol_version="1.0",
        required_core_version="0.2.0",
        changelog="Initial edge client release",
    )

    assert ok is True
    assert manifest is not None
    assert manifest.version == "1.0.0"
    assert manifest.status == "SIGNED"
    assert "client_daemon.py" in manifest.files
    assert "avatar_engine.js" in manifest.files


def test_u02_verify_manifest_and_file_hashes(release_env):
    """U02: Verify manifest file entries match actual SHA-256 hashes."""
    mgr, src_dir, base_dir = release_env

    ok, _, manifest = mgr.build_release(source_dir=src_dir, version="1.0.0")
    assert ok is True

    # Check client_daemon.py hash
    raw = (src_dir / "client_daemon.py").read_bytes()
    expected = hashlib.sha256(raw).hexdigest()
    assert manifest.files["client_daemon.py"] == expected


def test_u03_valid_hmac_signature(release_env):
    """U03: Verify package has a valid cryptographic HMAC-SHA256 signature."""
    mgr, src_dir, base_dir = release_env

    ok, _, manifest = mgr.build_release(source_dir=src_dir, version="1.0.0")
    assert ok is True

    valid, msg = mgr.verify_manifest(manifest)
    assert valid is True
    assert "verified" in msg


def test_u04_reject_unsigned_or_tampered_signature(release_env):
    """U04: Reject package with missing or forged signature."""
    mgr, src_dir, base_dir = release_env

    ok, _, manifest = mgr.build_release(source_dir=src_dir, version="1.0.0")

    # Unsigned manifest
    manifest.signature = None
    v1, msg1 = mgr.verify_manifest(manifest)
    assert v1 is False
    assert "unsigned" in msg1

    # Tampered signature
    manifest.signature = "forged_invalid_signature_hex"
    v2, msg2 = mgr.verify_manifest(manifest)
    assert v2 is False
    assert "invalid or tampered" in msg2


def test_u05_reject_incompatible_version(release_env):
    """U05: Reject package if protocol or core semver does not match."""
    mgr, src_dir, base_dir = release_env

    ok, _, manifest = mgr.build_release(
        source_dir=src_dir,
        version="2.0.0",
        required_protocol_version="2.0",
        required_core_version="1.0.0",
    )
    assert ok is True

    # Check against Edge running Protocol 1.0 and Core 0.2.0 -> incompatible
    comp_ok, msg = mgr.check_compatibility(
        manifest,
        edge_protocol_version="1.0",
        core_version="0.2.0",
    )
    assert comp_ok is False
    assert "Protocol version mismatch" in msg


def test_u06_staging_and_health_check_pass(release_env):
    """U06: Staging copies files, verifies hashes, and compiles python files successfully."""
    mgr, src_dir, base_dir = release_env

    ok, _, manifest = mgr.build_release(source_dir=src_dir, version="1.0.0")
    assert ok is True

    stage_ok, stage_msg = mgr.stage_and_verify_package(manifest, src_dir)
    assert stage_ok is True
    assert manifest.status == "STAGED"
    assert (mgr.staging_dir / manifest.release_id / "client_daemon.py").exists()


def test_u07_health_check_fail_on_syntax_error(release_env):
    """U07: Health check fails if a python file contains invalid syntax."""
    mgr, src_dir, base_dir = release_env

    # Inject broken python code
    (src_dir / "broken_script.py").write_text("def broken_syntax(:\n    pass\n", encoding="utf-8")

    ok, _, manifest = mgr.build_release(source_dir=src_dir, version="1.0.1")
    assert ok is True

    stage_ok, stage_msg = mgr.stage_and_verify_package(manifest, src_dir)
    assert stage_ok is False
    assert manifest.status == "FAILED_HEALTH_CHECK"
    assert "syntax validation failed" in stage_msg


def test_u08_atomic_rollback_to_previous_version(release_env):
    """U08: Verify atomic rollback to previous active version."""
    mgr, src_dir, base_dir = release_env

    # Deploy v1.0.0
    ok1, _, m1 = mgr.build_release(source_dir=src_dir, version="1.0.0")
    mgr.stage_and_verify_package(m1, src_dir)
    act1_ok, _ = mgr.activate_release("1.0.0")
    assert act1_ok is True
    assert mgr.get_active_version() == "1.0.0"

    # Modify src to v1.1.0
    (src_dir / "client_daemon.py").write_text("print('v1.1.0')", encoding="utf-8")
    ok2, _, m2 = mgr.build_release(source_dir=src_dir, version="1.1.0")
    mgr.stage_and_verify_package(m2, src_dir)
    act2_ok, _ = mgr.activate_release("1.1.0")
    assert act2_ok is True
    assert mgr.get_active_version() == "1.1.0"

    # Execute rollback
    rb_ok, rb_msg = mgr.rollback()
    assert rb_ok is True
    assert mgr.get_active_version() == "1.0.0"
    assert "Successfully rolled back" in rb_msg

    # Verify active directory content is indeed v1.0.0
    active_content = (mgr.active_dir / "client_daemon.py").read_text(encoding="utf-8")
    assert "Edge Client v1.0 running" in active_content


def test_u09_disrupted_staging_failure(release_env):
    """U09: If a file is missing during staging, staging fails safely."""
    mgr, src_dir, base_dir = release_env

    ok, _, manifest = mgr.build_release(source_dir=src_dir, version="1.0.0")
    # Delete a file from src before staging
    (src_dir / "avatar_engine.js").unlink()

    stage_ok, stage_msg = mgr.stage_and_verify_package(manifest, src_dir)
    assert stage_ok is False
    assert "Missing required file" in stage_msg
    assert manifest.status == "STAGING_FAILED"


def test_u10_preserve_previous_version_in_backup(release_env):
    """U10: Previous version is preserved in backup directory and not deleted prematurely."""
    mgr, src_dir, base_dir = release_env

    # Deploy v1.0.0
    ok1, _, m1 = mgr.build_release(source_dir=src_dir, version="1.0.0")
    mgr.stage_and_verify_package(m1, src_dir)
    mgr.activate_release("1.0.0")

    # Deploy v1.2.0
    (src_dir / "client_daemon.py").write_text("print('v1.2.0')", encoding="utf-8")
    ok2, _, m2 = mgr.build_release(source_dir=src_dir, version="1.2.0")
    mgr.stage_and_verify_package(m2, src_dir)
    mgr.activate_release("1.2.0")

    # Backup directory must contain 1.0.0 intact
    assert (mgr.backup_dir / "1.0.0" / "client_daemon.py").exists()
    assert mgr._previous_version == "1.0.0"
