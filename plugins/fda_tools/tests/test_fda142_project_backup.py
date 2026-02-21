"""
Project Backup and Recovery Tests (FDA-142)
===========================================

Verifies that ProjectBackup correctly:

  - Creates gzip archives of a single project directory
  - Creates gzip archives of all projects at once
  - Embeds a manifest.json inside each archive
  - Restores files back to a target directory
  - Lists all backups (newest first)
  - Prunes archives older than retention_days
  - Handles empty / missing directories gracefully

Test count: 18
Target: pytest plugins/fda_tools/tests/test_fda142_project_backup.py -v
"""

from __future__ import annotations

import json
import tarfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from fda_tools.lib.project_backup import ProjectBackup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_backup(tmp_path: Path) -> ProjectBackup:
    projects = tmp_path / "projects"
    backups = tmp_path / "backups"
    projects.mkdir()
    backups.mkdir()
    return ProjectBackup(projects_dir=str(projects), backup_dir=str(backups))


def _seed_project(projects_dir: Path, name: str) -> Path:
    """Create a project directory with sample files."""
    d = projects_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "device_profile.json").write_text('{"k_number": "K241335"}')
    (d / "review.json").write_text('{"predicates": []}')
    (d / "se_comparison.md").write_text("# Substantial Equivalence")
    return d


# ---------------------------------------------------------------------------
# TestCreateBackup
# ---------------------------------------------------------------------------


class TestCreateBackup:
    """Tests for ProjectBackup.create_backup()."""

    def test_creates_archive_file(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        assert info.path.exists()
        assert info.path.suffix == ".gz"

    def test_returned_info_has_correct_metadata(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        assert info.project_name == "proj1"
        assert info.file_count == 3
        assert info.size_bytes > 0

    def test_all_projects_backup_when_no_name(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        _seed_project(tmp_path / "projects", "proj2")
        info = bk.create_backup()  # no project_name → all projects
        assert info.project_name is None
        assert info.file_count == 6  # 3 files × 2 projects

    def test_archive_is_valid_tar_gz(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        assert tarfile.is_tarfile(str(info.path))

    def test_archive_contains_manifest(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        with tarfile.open(info.path, "r:gz") as tar:
            names = tar.getnames()
        assert "manifest.json" in names

    def test_missing_project_raises_file_not_found(self, tmp_path):
        bk = _make_backup(tmp_path)
        with pytest.raises(FileNotFoundError):
            bk.create_backup("nonexistent")

    def test_backup_dir_created_if_missing(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        _seed_project(projects, "proj1")
        new_backup_dir = tmp_path / "new_backups"
        # new_backup_dir does not exist yet
        bk = ProjectBackup(projects_dir=str(projects), backup_dir=str(new_backup_dir))
        bk.create_backup("proj1")
        assert new_backup_dir.exists()


# ---------------------------------------------------------------------------
# TestReadManifest
# ---------------------------------------------------------------------------


class TestReadManifest:
    """Tests for ProjectBackup.read_manifest()."""

    def test_manifest_contains_expected_keys(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        manifest = bk.read_manifest(info.path)
        assert "created_at" in manifest
        assert "project_name" in manifest
        assert "file_count" in manifest
        assert "files" in manifest

    def test_manifest_project_name_matches(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "testproj")
        info = bk.create_backup("testproj")
        manifest = bk.read_manifest(info.path)
        assert manifest["project_name"] == "testproj"

    def test_read_manifest_raises_for_missing_file(self, tmp_path):
        bk = _make_backup(tmp_path)
        with pytest.raises(FileNotFoundError):
            bk.read_manifest(tmp_path / "nonexistent.tar.gz")


# ---------------------------------------------------------------------------
# TestRestoreBackup
# ---------------------------------------------------------------------------


class TestRestoreBackup:
    """Tests for ProjectBackup.restore_backup()."""

    def test_restore_recreates_files(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")

        restore_dir = tmp_path / "restore_target"
        result = bk.restore_backup(info.path, target_dir=restore_dir)

        assert result.files_restored == 3
        assert result.success
        assert (restore_dir / "proj1" / "device_profile.json").exists()

    def test_restore_returns_result_with_correct_count(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        restore_dir = tmp_path / "restore2"
        result = bk.restore_backup(info.path, target_dir=restore_dir)
        assert result.files_restored == 3

    def test_restore_raises_for_missing_archive(self, tmp_path):
        bk = _make_backup(tmp_path)
        with pytest.raises(FileNotFoundError):
            bk.restore_backup(tmp_path / "missing.tar.gz")


# ---------------------------------------------------------------------------
# TestListBackups
# ---------------------------------------------------------------------------


class TestListBackups:
    """Tests for ProjectBackup.list_backups()."""

    def test_empty_backup_dir_returns_empty_list(self, tmp_path):
        bk = _make_backup(tmp_path)
        assert bk.list_backups() == []

    def test_returns_one_entry_per_archive(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        bk.create_backup("proj1")
        bk.create_backup("proj1")
        assert len(bk.list_backups()) == 2

    def test_list_is_sorted_newest_first(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info1 = bk.create_backup("proj1")
        time.sleep(0.05)  # ensure different timestamps
        info2 = bk.create_backup("proj1")
        listed = bk.list_backups()
        assert listed[0].path == info2.path
        assert listed[1].path == info1.path


# ---------------------------------------------------------------------------
# TestCleanupOld
# ---------------------------------------------------------------------------


class TestCleanupOld:
    """Tests for ProjectBackup.cleanup_old()."""

    def test_fresh_backup_not_deleted(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")
        result = bk.cleanup_old(retention_days=30)
        assert result.archives_removed == 0
        assert info.path.exists()

    def test_stale_backup_is_deleted(self, tmp_path):
        bk = _make_backup(tmp_path)
        _seed_project(tmp_path / "projects", "proj1")
        info = bk.create_backup("proj1")

        # Manually age the archive by altering mtime to 31 days ago
        old_ts = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()
        import os
        os.utime(info.path, (old_ts, old_ts))

        # Patch the manifest so list_backups() reads old date
        # Rebuild the archive with an old created_at in the manifest
        _patch_manifest_date(info.path, timedelta(days=31))

        result = bk.cleanup_old(retention_days=30)
        assert result.archives_removed == 1
        assert not info.path.exists()

    def test_cleanup_empty_dir_returns_zero(self, tmp_path):
        bk = _make_backup(tmp_path)
        result = bk.cleanup_old(retention_days=30)
        assert result.archives_removed == 0
        assert result.errors == []


# ---------------------------------------------------------------------------
# Helper: patch manifest date (for aging tests)
# ---------------------------------------------------------------------------


def _patch_manifest_date(archive_path: Path, age: timedelta) -> None:
    """Rewrite the manifest inside an archive with an older created_at."""
    import io
    import shutil

    old_time = (datetime.now(timezone.utc) - age).isoformat()
    tmp = archive_path.with_suffix(".tmp.tar.gz")
    with tarfile.open(archive_path, "r:gz") as src, tarfile.open(tmp, "w:gz") as dst:
        for member in src.getmembers():
            if member.name == "manifest.json":
                raw = src.extractfile(member)
                data = json.loads(raw.read())
                data["created_at"] = old_time
                new_bytes = json.dumps(data).encode()
                new_member = tarfile.TarInfo(name="manifest.json")
                new_member.size = len(new_bytes)
                dst.addfile(new_member, io.BytesIO(new_bytes))
            else:
                f = src.extractfile(member)
                if f is not None:
                    dst.addfile(member, f)
                else:
                    dst.addfile(member)
    shutil.move(str(tmp), str(archive_path))
