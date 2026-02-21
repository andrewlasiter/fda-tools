"""
Refresh Checkpoint / Rollback Tests (FDA-152).
================================================

Verifies that RefreshCheckpoint provides reliable point-in-time snapshots
of a data directory so that a failed or corrupted data refresh can be
rolled back.

Tests cover:
  - CheckpointInfo.age_hours() computation
  - RefreshCheckpoint initialises and creates checkpoint directory
  - create() archives files and returns valid CheckpointInfo
  - create() embeds a readable manifest in the archive
  - Checkpoints directory is excluded from archives (no recursion)
  - rollback() restores files from the archive
  - rollback() returns success=False for unknown checkpoint_id
  - list_checkpoints() returns newest-first
  - cleanup() removes checkpoints older than max_age_hours
  - cleanup() retains checkpoints within max_age_hours
  - RollbackResult dataclass fields
  - CleanupResult dataclass fields

Test count: 17
Target: pytest plugins/fda_tools/tests/test_fda152_refresh_checkpoint.py -v
"""

from __future__ import annotations

import json
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

from fda_tools.lib.refresh_checkpoint import (
    CheckpointInfo,
    CleanupResult,
    RefreshCheckpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cp(tmp_path: Path) -> RefreshCheckpoint:
    """Return a RefreshCheckpoint backed by tmp directories."""
    return RefreshCheckpoint(
        source_dir=str(tmp_path / "data"),
        checkpoint_dir=str(tmp_path / "checkpoints"),
    )


def _populate_data(tmp_path: Path) -> None:
    """Create a small set of files in the data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "cache.json").write_text('{"k": "v"}')
    (data_dir / "sub" / "nested.json").mkdir(parents=True, exist_ok=True)
    (data_dir / "sub" / "nested.json").rmdir()
    (data_dir / "sub").mkdir(exist_ok=True)
    (data_dir / "sub" / "nested.json").write_text('{"nested": true}')


# ---------------------------------------------------------------------------
# TestCheckpointInfoHelpers
# ---------------------------------------------------------------------------


class TestCheckpointInfoHelpers:
    def test_age_hours_recent_is_near_zero(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        cp = CheckpointInfo(
            checkpoint_id="test-id",
            label="test",
            source_dir="/tmp",
            created_at=now_iso,
            file_count=0,
            archive_path=Path("/tmp/fake.tar.gz"),
        )
        assert cp.age_hours() < 0.1

    def test_age_hours_old_timestamp(self):
        old_iso = "2000-01-01T00:00:00+00:00"
        cp = CheckpointInfo(
            checkpoint_id="old-id",
            label="old",
            source_dir="/tmp",
            created_at=old_iso,
            file_count=0,
            archive_path=Path("/tmp/fake.tar.gz"),
        )
        assert cp.age_hours() > 1000  # more than 1000 hours old


# ---------------------------------------------------------------------------
# TestRefreshCheckpointInit
# ---------------------------------------------------------------------------


class TestRefreshCheckpointInit:
    def test_init_creates_checkpoint_dir(self, tmp_path):
        cp_dir = tmp_path / "checkpoints"
        assert not cp_dir.exists()
        RefreshCheckpoint(
            source_dir=str(tmp_path / "data"),
            checkpoint_dir=str(cp_dir),
        )
        assert cp_dir.exists()

    def test_init_accepts_nonexistent_source_dir(self, tmp_path):
        # Should not raise even if source_dir doesn't exist yet
        rcp = RefreshCheckpoint(
            source_dir=str(tmp_path / "does_not_exist"),
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )
        assert rcp is not None


# ---------------------------------------------------------------------------
# TestCreate
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_returns_checkpoint_info(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("pre-refresh")
        assert isinstance(info, CheckpointInfo)
        assert info.label == "pre-refresh"
        assert info.file_count == 2
        assert info.archive_path.exists()

    def test_create_archive_contains_files(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("test")
        with tarfile.open(info.archive_path, "r:gz") as tar:
            names = tar.getnames()
        assert "cache.json" in names
        assert any("nested.json" in n for n in names)

    def test_create_archive_has_manifest(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("test")
        manifest = rcp.read_manifest(info.archive_path)
        assert manifest["label"] == "test"
        assert manifest["file_count"] == 2

    def test_create_excludes_checkpoint_dir(self, tmp_path):
        """The checkpoints/ directory itself must not appear in the archive."""
        _populate_data(tmp_path)
        # Pre-create a checkpoint so the dir has content
        rcp = _make_cp(tmp_path)
        rcp.create("first")
        info = rcp.create("second")
        with tarfile.open(info.archive_path, "r:gz") as tar:
            names = tar.getnames()
        assert not any("checkpoint_" in n for n in names if n != "manifest.json")

    def test_create_on_empty_source_dir(self, tmp_path):
        (tmp_path / "data").mkdir()
        rcp = _make_cp(tmp_path)
        info = rcp.create("empty")
        assert info.file_count == 0
        assert info.archive_path.exists()

    def test_checkpoint_id_contains_label_slug(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("daily refresh!")
        assert "daily-refresh" in info.checkpoint_id


# ---------------------------------------------------------------------------
# TestRollback
# ---------------------------------------------------------------------------


class TestRollback:
    def test_rollback_restores_files(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("pre-refresh")

        # Corrupt the data
        (tmp_path / "data" / "cache.json").write_text("CORRUPTED")

        result = rcp.rollback(info.checkpoint_id)
        assert result.success is True
        assert result.files_restored == 2

        restored = (tmp_path / "data" / "cache.json").read_text()
        assert restored == '{"k": "v"}'

    def test_rollback_unknown_id_returns_failure(self, tmp_path):
        rcp = _make_cp(tmp_path)
        result = rcp.rollback("nonexistent-checkpoint-id")
        assert result.success is False
        assert result.files_restored == 0
        assert result.errors

    def test_rollback_result_has_checkpoint_id(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("test")
        result = rcp.rollback(info.checkpoint_id)
        assert result.checkpoint_id == info.checkpoint_id


# ---------------------------------------------------------------------------
# TestListCheckpoints
# ---------------------------------------------------------------------------


class TestListCheckpoints:
    def test_list_returns_empty_for_new_dir(self, tmp_path):
        rcp = _make_cp(tmp_path)
        assert rcp.list_checkpoints() == []

    def test_list_returns_newest_first(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        rcp.create("first")
        time.sleep(0.01)
        rcp.create("second")
        checkpoints = rcp.list_checkpoints()
        assert len(checkpoints) == 2
        assert checkpoints[0].label == "second"

    def test_list_count_matches_create_calls(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        for i in range(3):
            rcp.create(f"cp-{i}")
        assert len(rcp.list_checkpoints()) == 3


# ---------------------------------------------------------------------------
# TestCleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_removes_old_checkpoints(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        info = rcp.create("old")
        # Patch created_at to simulate an old checkpoint
        manifest = rcp.read_manifest(info.archive_path)
        manifest["created_at"] = "2000-01-01T00:00:00+00:00"
        # Rewrite the archive with the patched manifest
        _rewrite_manifest(info.archive_path, manifest)

        result = rcp.cleanup(max_age_hours=1)
        assert result.removed_count == 1
        assert result.retained_count == 0

    def test_cleanup_retains_recent_checkpoints(self, tmp_path):
        _populate_data(tmp_path)
        rcp = _make_cp(tmp_path)
        rcp.create("recent")
        result = rcp.cleanup(max_age_hours=24)
        assert result.removed_count == 0
        assert result.retained_count == 1

    def test_cleanup_returns_cleanup_result(self, tmp_path):
        rcp = _make_cp(tmp_path)
        result = rcp.cleanup()
        assert isinstance(result, CleanupResult)


# ---------------------------------------------------------------------------
# Helpers for test manipulation
# ---------------------------------------------------------------------------


def _rewrite_manifest(archive_path: Path, new_manifest: dict) -> None:
    """Replace manifest.json in an existing archive with new_manifest."""
    import io

    tmp = archive_path.with_suffix(".tmp.tar.gz")
    manifest_bytes = json.dumps(new_manifest, indent=2).encode()

    with tarfile.open(archive_path, "r:gz") as src, tarfile.open(tmp, "w:gz") as dst:
        for member in src.getmembers():
            if member.name == "manifest.json":
                info = tarfile.TarInfo(name="manifest.json")
                info.size = len(manifest_bytes)
                dst.addfile(info, io.BytesIO(manifest_bytes))
            else:
                f = src.extractfile(member)
                if f is not None:
                    dst.addfile(member, f)
                else:
                    dst.addfile(member)

    tmp.replace(archive_path)
