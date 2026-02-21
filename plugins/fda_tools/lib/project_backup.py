"""
Project Data Backup and Recovery — FDA-142
==========================================

Provides point-in-time backup and restore for FDA project data files
stored under ``~/fda-510k-data/projects/``.

Each backup is a gzip-compressed tar archive with an embedded
``manifest.json`` describing its contents and creation time.

Usage
-----
    from fda_tools.lib.project_backup import ProjectBackup

    bk = ProjectBackup()

    # Backup a single project
    info = bk.create_backup("K241335_DQY")

    # Backup all projects at once
    info = bk.create_backup()

    # List available backups (newest first)
    for b in bk.list_backups():
        print(b.filename, b.created_at, b.size_mb)

    # Restore a backup
    bk.restore_backup(info.path, target_dir=Path("~/fda-510k-data/projects"))

    # Prune backups older than 30 days
    bk.cleanup_old(retention_days=30)
"""

from __future__ import annotations

import json
import os
import tarfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BackupInfo:
    """Metadata for a single backup archive."""
    path: Path
    created_at: datetime
    project_name: Optional[str]  # None means full (all-projects) backup
    file_count: int
    size_bytes: int

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def age_days(self) -> float:
        now = datetime.now(timezone.utc)
        return (now - self.created_at).total_seconds() / 86400


@dataclass
class RestoreResult:
    """Result of a restore operation."""
    backup_path: Path
    target_dir: Path
    files_restored: int
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    archives_removed: int
    bytes_freed: int
    errors: List[str] = field(default_factory=list)

    @property
    def mb_freed(self) -> float:
        return self.bytes_freed / (1024 * 1024)


# ---------------------------------------------------------------------------
# ProjectBackup
# ---------------------------------------------------------------------------

_MANIFEST_NAME = "manifest.json"
_BACKUP_PREFIX = "fda_backup_"
_BACKUP_SUFFIX = ".tar.gz"


class ProjectBackup:
    """Backup and restore FDA project data files.

    Args:
        projects_dir: Base directory containing project subdirectories.
            Default: ``~/fda-510k-data/projects``.
        backup_dir: Directory where backup archives are stored.
            Default: ``~/fda-510k-data/backups``.
    """

    def __init__(
        self,
        projects_dir: Optional[str] = None,
        backup_dir: Optional[str] = None,
    ) -> None:
        base = Path(os.path.expanduser("~/.claude/fda-510k-data"))
        self.projects_dir = Path(projects_dir) if projects_dir else (base / "projects")
        self.backup_dir = Path(backup_dir) if backup_dir else (base / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_backup(
        self,
        project_name: Optional[str] = None,
        *,
        source_dir: Optional[Path] = None,
    ) -> BackupInfo:
        """Create a compressed backup archive.

        Args:
            project_name: Name of a single project directory to back up.
                If ``None``, all projects under :attr:`projects_dir` are archived.
            source_dir: Override the source directory (useful for testing).
                Ignored when *project_name* is provided.

        Returns:
            :class:`BackupInfo` describing the created archive.

        Raises:
            FileNotFoundError: If the specified project directory does not exist.
            OSError: If the archive cannot be created.
        """
        ts = datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y%m%d_%H%M%S_%f")

        # Determine what to archive
        if project_name:
            source = self.projects_dir / project_name
            if not source.exists():
                raise FileNotFoundError(
                    f"Project directory not found: {source}"
                )
            archive_label = project_name.replace(os.sep, "_")
        else:
            source = source_dir or self.projects_dir
            archive_label = "all_projects"

        archive_name = f"{_BACKUP_PREFIX}{archive_label}_{ts_str}{_BACKUP_SUFFIX}"
        archive_path = self.backup_dir / archive_name

        # Collect files
        files = self._collect_files(source)
        file_count = len(files)

        # Write archive
        with tarfile.open(archive_path, "w:gz") as tar:
            # Add files
            for abs_path in files:
                arcname = str(abs_path.relative_to(source.parent))
                tar.add(str(abs_path), arcname=arcname)

            # Embed manifest
            manifest = {
                "created_at": ts.isoformat(),
                "project_name": project_name,
                "source_dir": str(source),
                "file_count": file_count,
                "files": [str(f.relative_to(source.parent)) for f in files],
            }
            manifest_bytes = json.dumps(manifest, indent=2).encode()
            import io
            info = tarfile.TarInfo(name=_MANIFEST_NAME)
            info.size = len(manifest_bytes)
            info.mtime = int(time.time())
            tar.addfile(info, io.BytesIO(manifest_bytes))

        size = archive_path.stat().st_size
        return BackupInfo(
            path=archive_path,
            created_at=ts,
            project_name=project_name,
            file_count=file_count,
            size_bytes=size,
        )

    def restore_backup(
        self,
        backup_path: Path,
        target_dir: Optional[Path] = None,
    ) -> RestoreResult:
        """Restore files from a backup archive.

        Args:
            backup_path: Path to the ``.tar.gz`` archive.
            target_dir: Directory to extract into.
                Default: parent of :attr:`projects_dir` (same layout as during backup).

        Returns:
            :class:`RestoreResult` describing what was restored.

        Raises:
            FileNotFoundError: If *backup_path* does not exist.
            tarfile.TarError: If the archive is malformed.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        if target_dir is None:
            target_dir = self.projects_dir.parent

        target_dir.mkdir(parents=True, exist_ok=True)
        errors: List[str] = []
        files_restored = 0

        with tarfile.open(backup_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name == _MANIFEST_NAME:
                    continue  # Skip embedded manifest
                try:
                    tar.extract(member, path=str(target_dir))
                    files_restored += 1
                except (tarfile.TarError, OSError) as e:
                    errors.append(f"{member.name}: {e}")

        return RestoreResult(
            backup_path=backup_path,
            target_dir=target_dir,
            files_restored=files_restored,
            errors=errors,
        )

    def list_backups(self) -> List[BackupInfo]:
        """Return all backup archives, newest first.

        Returns:
            List of :class:`BackupInfo` objects sorted by creation time descending.
        """
        infos: List[BackupInfo] = []
        pattern = f"{_BACKUP_PREFIX}*{_BACKUP_SUFFIX}"
        for archive_path in self.backup_dir.glob(pattern):
            info = self._read_backup_info(archive_path)
            if info:
                infos.append(info)
        infos.sort(key=lambda b: b.created_at, reverse=True)
        return infos

    def cleanup_old(self, retention_days: int = 30) -> CleanupResult:
        """Remove backup archives older than *retention_days*.

        Args:
            retention_days: Minimum age (in days) for a backup to be deleted.

        Returns:
            :class:`CleanupResult` describing what was removed.
        """
        result = CleanupResult(archives_removed=0, bytes_freed=0)
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        for info in self.list_backups():
            if info.created_at < cutoff:
                try:
                    size = info.path.stat().st_size
                    info.path.unlink()
                    result.archives_removed += 1
                    result.bytes_freed += size
                except OSError as e:
                    result.errors.append(f"{info.path}: {e}")

        return result

    def read_manifest(self, backup_path: Path) -> Dict:
        """Return the manifest embedded in a backup archive.

        Args:
            backup_path: Path to the ``.tar.gz`` archive.

        Returns:
            Manifest dict with keys ``created_at``, ``project_name``,
            ``source_dir``, ``file_count``, ``files``.

        Raises:
            FileNotFoundError: If the archive does not exist.
            KeyError: If the archive has no embedded manifest.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        with tarfile.open(backup_path, "r:gz") as tar:
            try:
                member = tar.getmember(_MANIFEST_NAME)
            except KeyError:
                raise KeyError(f"No manifest found in {backup_path.name}")
            f = tar.extractfile(member)
            if f is None:
                raise KeyError(f"Cannot read manifest from {backup_path.name}")
            return json.loads(f.read())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_files(self, directory: Path) -> List[Path]:
        """Recursively collect all files under *directory*."""
        files: List[Path] = []
        if not directory.exists():
            return files
        for p in directory.rglob("*"):
            if p.is_file():
                files.append(p)
        return sorted(files)

    def _read_backup_info(self, archive_path: Path) -> Optional[BackupInfo]:
        """Parse backup metadata from an archive without full extraction."""
        try:
            manifest = self.read_manifest(archive_path)
            created_at = datetime.fromisoformat(manifest["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return BackupInfo(
                path=archive_path,
                created_at=created_at,
                project_name=manifest.get("project_name"),
                file_count=manifest.get("file_count", 0),
                size_bytes=archive_path.stat().st_size,
            )
        except (KeyError, OSError, json.JSONDecodeError, ValueError):
            return None
