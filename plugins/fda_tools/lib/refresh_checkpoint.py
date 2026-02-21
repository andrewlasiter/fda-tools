#!/usr/bin/env python3
"""
Rollback Checkpoints for Data Refresh Operations (FDA-152).

Provides point-in-time snapshots of a data directory so that a failed or
corrupted refresh can be rolled back automatically.

Workflow::

    from fda_tools.lib.refresh_checkpoint import RefreshCheckpoint

    cp = RefreshCheckpoint()

    # 1. Snapshot before refresh
    info = cp.create("daily-refresh")

    try:
        run_my_refresh()          # may corrupt data
    except Exception:
        cp.rollback(info.checkpoint_id)
        raise

    # 2. Keep recent checkpoints; discard older ones
    cp.cleanup(max_age_hours=48)

Checkpoint archives are stored as gzipped tarballs in
``~/.claude/fda-510k-data/checkpoints/`` with an embedded ``manifest.json``
that records the checkpoint label, timestamp, source directory, and file list.

Only the target directory's *files* are archived; subdirectories are
preserved by path.  Symlinks are followed.

Args and defaults mirror :class:`ProjectBackup` but the retention model is
time-based (hours) rather than count-based, since refresh checkpoints
accumulate quickly.
"""

from __future__ import annotations

import io
import json
import os
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = os.path.expanduser("~/fda-510k-data")
DEFAULT_CHECKPOINT_DIR = os.path.join(DEFAULT_DATA_DIR, "checkpoints")

# Default retention: keep checkpoints for 48 hours
DEFAULT_RETENTION_HOURS = 48


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class CheckpointInfo:
    """Metadata about a single checkpoint archive.

    Attributes:
        checkpoint_id: Unique identifier (timestamp + label slug).
        label: Human-readable label supplied at creation time.
        source_dir: Absolute path of the directory that was archived.
        created_at: ISO-8601 UTC timestamp.
        file_count: Number of files archived.
        archive_path: Path to the ``.tar.gz`` archive on disk.
    """

    checkpoint_id: str
    label: str
    source_dir: str
    created_at: str
    file_count: int
    archive_path: Path

    def age_hours(self) -> float:
        """Return how many hours old this checkpoint is."""
        try:
            dt = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - dt).total_seconds() / 3_600
        except (ValueError, TypeError):
            return 0.0


@dataclass
class RollbackResult:
    """Result of a rollback operation.

    Attributes:
        success: Whether the rollback completed without errors.
        checkpoint_id: ID of the checkpoint that was restored.
        target_dir: Directory that was restored.
        files_restored: Number of files written.
        errors: Any non-fatal error messages encountered.
    """

    success: bool
    checkpoint_id: str
    target_dir: str
    files_restored: int
    errors: List[str] = field(default_factory=list)


@dataclass
class CleanupResult:
    """Result of a cleanup operation.

    Attributes:
        removed_count: Number of archive files deleted.
        retained_count: Number of archive files kept.
        freed_bytes: Total bytes freed.
    """

    removed_count: int
    retained_count: int
    freed_bytes: int


# ---------------------------------------------------------------------------
# RefreshCheckpoint
# ---------------------------------------------------------------------------


class RefreshCheckpoint:
    """Point-in-time snapshot manager for data refresh rollback.

    Args:
        source_dir: Directory to snapshot on :meth:`create`.
            Defaults to ``~/fda-510k-data``.
        checkpoint_dir: Directory where checkpoint archives are stored.
            Defaults to ``~/fda-510k-data/checkpoints``.
    """

    def __init__(
        self,
        source_dir: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
    ) -> None:
        self.source_dir = Path(source_dir or DEFAULT_DATA_DIR).expanduser()
        self.checkpoint_dir = Path(
            checkpoint_dir or DEFAULT_CHECKPOINT_DIR
        ).expanduser()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, label: str = "checkpoint") -> CheckpointInfo:
        """Archive *source_dir* and return a :class:`CheckpointInfo`.

        The archive is a gzipped tarball named
        ``checkpoint_<label>_<YYYYMMDD_HHMMSSffffff>.tar.gz``.

        Args:
            label: Short human-readable description (e.g. ``"pre-daily-refresh"``).
                Non-alphanumeric characters are replaced with ``-``.

        Returns:
            CheckpointInfo for the newly created checkpoint.
        """
        slug = "".join(c if c.isalnum() else "-" for c in label).strip("-") or "cp"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        checkpoint_id = f"{ts}_{slug}"
        archive_name = f"checkpoint_{slug}_{ts}.tar.gz"
        archive_path = self.checkpoint_dir / archive_name

        created_at = datetime.now(timezone.utc).isoformat()
        files: List[str] = []

        with tarfile.open(archive_path, "w:gz") as tar:
            if self.source_dir.exists():
                for path in sorted(self.source_dir.rglob("*")):
                    # Skip the checkpoints directory itself to avoid recursion
                    if self.checkpoint_dir in path.parents or path == self.checkpoint_dir:
                        continue
                    if path.is_file():
                        rel = str(path.relative_to(self.source_dir))
                        tar.add(str(path), arcname=rel)
                        files.append(rel)

            manifest = {
                "checkpoint_id": checkpoint_id,
                "label": label,
                "source_dir": str(self.source_dir),
                "created_at": created_at,
                "file_count": len(files),
                "files": files,
            }
            manifest_bytes = json.dumps(manifest, indent=2).encode()
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest_bytes)
            tar.addfile(info, io.BytesIO(manifest_bytes))

        return CheckpointInfo(
            checkpoint_id=checkpoint_id,
            label=label,
            source_dir=str(self.source_dir),
            created_at=created_at,
            file_count=len(files),
            archive_path=archive_path,
        )

    def rollback(self, checkpoint_id: str) -> RollbackResult:
        """Restore *source_dir* from the checkpoint with the given ID.

        Existing files in *source_dir* that were present in the checkpoint
        are overwritten.  Files created after the checkpoint are left in
        place (they are not deleted).

        Args:
            checkpoint_id: The :attr:`CheckpointInfo.checkpoint_id` to restore.

        Returns:
            :class:`RollbackResult` with success status and counts.
        """
        archive_path = self._find_archive(checkpoint_id)
        if archive_path is None:
            return RollbackResult(
                success=False,
                checkpoint_id=checkpoint_id,
                target_dir=str(self.source_dir),
                files_restored=0,
                errors=[f"Checkpoint not found: {checkpoint_id}"],
            )

        errors: List[str] = []
        files_restored = 0

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name == "manifest.json":
                        continue
                    dest = self.source_dir / member.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        f = tar.extractfile(member)
                        if f is not None:
                            dest.write_bytes(f.read())
                            files_restored += 1
                    except Exception as exc:
                        errors.append(f"{member.name}: {exc}")
        except Exception as exc:
            return RollbackResult(
                success=False,
                checkpoint_id=checkpoint_id,
                target_dir=str(self.source_dir),
                files_restored=files_restored,
                errors=[str(exc)],
            )

        return RollbackResult(
            success=not errors,
            checkpoint_id=checkpoint_id,
            target_dir=str(self.source_dir),
            files_restored=files_restored,
            errors=errors,
        )

    def list_checkpoints(self) -> List[CheckpointInfo]:
        """Return all checkpoints sorted newest-first.

        Returns:
            List of :class:`CheckpointInfo` objects.
        """
        infos: List[CheckpointInfo] = []
        for archive_path in sorted(self.checkpoint_dir.glob("checkpoint_*.tar.gz")):
            manifest = self._read_manifest(archive_path)
            if manifest:
                infos.append(
                    CheckpointInfo(
                        checkpoint_id=manifest.get("checkpoint_id", archive_path.stem),
                        label=manifest.get("label", ""),
                        source_dir=manifest.get("source_dir", ""),
                        created_at=manifest.get("created_at", ""),
                        file_count=manifest.get("file_count", 0),
                        archive_path=archive_path,
                    )
                )

        return sorted(infos, key=lambda c: c.created_at, reverse=True)

    def cleanup(self, max_age_hours: float = DEFAULT_RETENTION_HOURS) -> CleanupResult:
        """Delete checkpoints older than *max_age_hours*.

        Args:
            max_age_hours: Maximum age in hours.  Checkpoints older than
                this are deleted.  Default: 48 hours.

        Returns:
            :class:`CleanupResult` with counts and bytes freed.
        """
        removed = 0
        retained = 0
        freed = 0

        for cp in self.list_checkpoints():
            if cp.age_hours() > max_age_hours:
                freed += cp.archive_path.stat().st_size if cp.archive_path.exists() else 0
                cp.archive_path.unlink(missing_ok=True)
                removed += 1
            else:
                retained += 1

        return CleanupResult(
            removed_count=removed,
            retained_count=retained,
            freed_bytes=freed,
        )

    def read_manifest(self, archive_path: Path) -> Dict:
        """Read the manifest from a checkpoint archive without extraction.

        Args:
            archive_path: Path to the ``.tar.gz`` archive.

        Returns:
            Manifest dictionary, or empty dict on error.
        """
        return self._read_manifest(archive_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_archive(self, checkpoint_id: str) -> Optional[Path]:
        """Return the archive path for *checkpoint_id*, or None."""
        for cp in self.list_checkpoints():
            if cp.checkpoint_id == checkpoint_id:
                return cp.archive_path
        return None

    def _read_manifest(self, archive_path: Path) -> Dict:
        """Extract and parse manifest.json from an archive."""
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                try:
                    f = tar.extractfile("manifest.json")
                    if f is not None:
                        return json.loads(f.read().decode())
                except KeyError:
                    pass
        except (OSError, tarfile.TarError):
            pass
        return {}
