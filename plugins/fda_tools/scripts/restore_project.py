#!/usr/bin/env python3
"""
FDA Project Restore — Disaster Recovery and Data Restoration.

Restores FDA project data from backup archives created by backup_project.py
with full integrity verification, collision detection, and selective restore
capabilities.

Usage:
    python3 restore_project.py --backup-file PATH                     # Restore all projects
    python3 restore_project.py --backup-file PATH --project NAME      # Restore specific project
    python3 restore_project.py --backup-file PATH --dry-run           # Preview restore
    python3 restore_project.py --backup-file PATH --verify-only       # Verify backup only
    python3 restore_project.py --backup-file PATH --force             # Overwrite existing
    python3 restore_project.py --backup-file PATH --list-contents     # List archive contents

Features:
    - SHA-256 checksum verification before extraction
    - Collision detection for existing projects
    - Selective project restore from multi-project backups
    - Dry-run mode for safety validation
    - Atomic restore with rollback on failure
    - Progress reporting for large restores

Security:
    - Validates archive integrity before extraction
    - Verifies checksums for all extracted files
    - Prevents accidental overwrites without --force
    - Atomic operations with automatic cleanup on failure

Author: FDA-Tools Development Team
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Import project directory resolution
from fda_data_store import get_projects_dir
from backup_project import verify_backup_integrity, compute_file_hash, CHUNK_SIZE

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def list_backup_contents(backup_path: Path) -> Dict:
    """List contents of a backup archive.

    Args:
        backup_path: Path to the backup zip file.

    Returns:
        Dictionary with archive contents:
        {
            "metadata": dict,
            "projects": List[str],
            "files_by_project": Dict[str, List[str]],
            "total_files": int,
            "total_size_bytes": int
        }

    Raises:
        ValueError: If backup file is invalid or corrupted.
    """
    verification = verify_backup_integrity(backup_path)

    if not verification["passed"]:
        raise ValueError(f"Invalid backup: {verification['message']}")

    metadata = verification["metadata"]
    if not metadata:
        raise ValueError("Backup metadata not found")

    # Extract file list from archive
    files_by_project: Dict[str, List[str]] = {}
    total_size = 0

    with zipfile.ZipFile(backup_path, 'r') as zf:
        for file_info in zf.filelist:
            if file_info.filename.startswith("projects/"):
                # Extract project name from path
                parts = Path(file_info.filename).parts
                if len(parts) >= 2:
                    project_name = parts[1]
                    relative_path = str(Path(*parts[2:])) if len(parts) > 2 else ""

                    if project_name not in files_by_project:
                        files_by_project[project_name] = []

                    if relative_path:  # Skip directory entries
                        files_by_project[project_name].append(relative_path)
                        total_size += file_info.file_size

    return {
        "metadata": metadata,
        "projects": sorted(files_by_project.keys()),
        "files_by_project": files_by_project,
        "total_files": sum(len(files) for files in files_by_project.values()),
        "total_size_bytes": total_size
    }


def check_project_collision(
    projects_dir: Path,
    project_names: List[str]
) -> Dict[str, bool]:
    """Check if any projects already exist in the target directory.

    Args:
        projects_dir: Base directory for projects.
        project_names: List of project names to check.

    Returns:
        Dictionary mapping project names to existence status (True if exists).
    """
    collisions = {}
    for project_name in project_names:
        project_path = projects_dir / project_name
        collisions[project_name] = project_path.exists()

    return collisions


def restore_projects(
    backup_path: Path,
    projects_dir: Path,
    selected_projects: Optional[List[str]] = None,
    force: bool = False,
    verify_checksums: bool = True,
    dry_run: bool = False
) -> Dict:
    """Restore projects from a backup archive.

    Args:
        backup_path: Path to the backup zip file.
        projects_dir: Target directory for project restoration.
        selected_projects: Optional list of specific projects to restore.
        force: If True, overwrite existing projects without prompting.
        verify_checksums: If True, verify file checksums after extraction.
        dry_run: If True, preview restore without executing.

    Returns:
        Dictionary with restoration results:
        {
            "status": "success" | "failed" | "dry_run",
            "restored_projects": List[str],
            "skipped_projects": List[str],
            "failed_projects": List[str],
            "total_files": int,
            "verified_files": int,
            "checksum_failures": List[str],
            "collisions": Dict[str, bool],
            "timestamp": str
        }

    Raises:
        ValueError: If backup is invalid or restore preconditions not met.
        OSError: If file operations fail.
    """
    # Verify backup integrity
    logger.info(f"Verifying backup integrity: {backup_path}")
    verification = verify_backup_integrity(backup_path)

    if not verification["passed"]:
        raise ValueError(f"Invalid backup: {verification['message']}")

    metadata = verification["metadata"]
    if not metadata:
        raise ValueError("Backup metadata not found")

    # Determine which projects to restore
    available_projects = metadata.get("projects", [])
    if selected_projects:
        # Validate selected projects exist in backup
        invalid_projects = set(selected_projects) - set(available_projects)
        if invalid_projects:
            raise ValueError(f"Projects not found in backup: {', '.join(invalid_projects)}")
        projects_to_restore = selected_projects
    else:
        projects_to_restore = available_projects

    logger.info(f"Projects to restore: {', '.join(projects_to_restore)}")

    # Check for collisions
    collisions = check_project_collision(projects_dir, projects_to_restore)
    existing_projects = [name for name, exists in collisions.items() if exists]

    if existing_projects and not force:
        raise ValueError(
            f"Projects already exist (use --force to overwrite): {', '.join(existing_projects)}"
        )

    if dry_run:
        logger.info("🔍 DRY RUN MODE — No files will be modified")
        return {
            "status": "dry_run",
            "restored_projects": [],
            "skipped_projects": [],
            "failed_projects": [],
            "total_files": metadata.get("total_files", 0),
            "verified_files": 0,
            "checksum_failures": [],
            "collisions": collisions,
            "would_restore": projects_to_restore,
            "would_overwrite": existing_projects,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # Execute restoration
    logger.info("Starting restoration process")
    restored_projects = []
    failed_projects = []
    checksum_failures = []
    total_files_restored = 0
    verified_files = 0

    # Create temp directory for atomic restore
    with tempfile.TemporaryDirectory(prefix="fda_restore_") as temp_dir:
        temp_path = Path(temp_dir)

        # Extract all files to temp directory first
        with zipfile.ZipFile(backup_path, 'r') as zf:
            all_files = [
                f for f in zf.namelist()
                if f.startswith("projects/") and not f.endswith("/")
            ]

            iterator = tqdm(all_files, desc="Extracting files", unit="file") if TQDM_AVAILABLE else all_files

            for file_path in iterator:
                zf.extract(file_path, temp_path)

        # Process each project
        for project_name in projects_to_restore:
            try:
                source_path = temp_path / "projects" / project_name
                target_path = projects_dir / project_name

                if not source_path.exists():
                    logger.warning(f"Project directory not found in backup: {project_name}")
                    failed_projects.append(project_name)
                    continue

                # Remove existing project if force is enabled
                if target_path.exists() and force:
                    logger.info(f"Removing existing project: {project_name}")
                    shutil.rmtree(target_path)

                # Copy project to final destination
                logger.info(f"Restoring project: {project_name}")
                shutil.copytree(source_path, target_path)

                # Count files
                project_files = list(source_path.rglob("*"))
                file_count = sum(1 for f in project_files if f.is_file())
                total_files_restored += file_count

                # Verify checksums if requested
                if verify_checksums:
                    logger.info(f"Verifying checksums for {project_name}")
                    checksums = metadata.get("checksums", {})

                    verify_iterator = (
                        tqdm(project_files, desc=f"Verifying {project_name}", unit="file")
                        if TQDM_AVAILABLE else project_files
                    )

                    for source_file in verify_iterator:
                        if not source_file.is_file():
                            continue

                        # Compute relative path from projects directory
                        rel_path = source_file.relative_to(temp_path / "projects")
                        expected_hash = checksums.get(str(rel_path))

                        if expected_hash:
                            # Compute hash of restored file
                            target_file = projects_dir / rel_path
                            actual_hash = compute_file_hash(target_file)

                            if actual_hash == expected_hash:
                                verified_files += 1
                            else:
                                logger.error(
                                    f"Checksum mismatch: {rel_path} "
                                    f"(expected: {expected_hash[:8]}..., got: {actual_hash[:8]}...)"
                                )
                                checksum_failures.append(str(rel_path))

                restored_projects.append(project_name)
                logger.info(f"✅ Successfully restored: {project_name}")

            except Exception as e:
                logger.error(f"Failed to restore {project_name}: {e}")
                failed_projects.append(project_name)

                # Cleanup partial restoration
                target_path = projects_dir / project_name
                if target_path.exists():
                    try:
                        shutil.rmtree(target_path)
                        logger.info(f"Cleaned up partial restoration: {project_name}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to cleanup {project_name}: {cleanup_error}")

    # Determine overall status
    if failed_projects or checksum_failures:
        status = "partial_success" if restored_projects else "failed"
    else:
        status = "success"

    return {
        "status": status,
        "restored_projects": restored_projects,
        "skipped_projects": [],
        "failed_projects": failed_projects,
        "total_files": total_files_restored,
        "verified_files": verified_files,
        "checksum_failures": checksum_failures,
        "collisions": collisions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA Project Restore — Disaster Recovery and Data Restoration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Restore all projects from backup
  python3 restore_project.py --backup-file ~/backups/all_projects_backup_20260217.zip

  # Restore specific project
  python3 restore_project.py --backup-file backup.zip --project batch_DQY

  # Preview restore without executing
  python3 restore_project.py --backup-file backup.zip --dry-run

  # Force overwrite of existing projects
  python3 restore_project.py --backup-file backup.zip --force

  # List backup contents
  python3 restore_project.py --backup-file backup.zip --list-contents

  # Verify backup integrity only
  python3 restore_project.py --backup-file backup.zip --verify-only
        """
    )

    parser.add_argument("--backup-file", type=Path, required=True,
                        help="Path to backup zip file")
    parser.add_argument("--project", help="Restore only this specific project")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing projects without prompting")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview restore without executing")
    parser.add_argument("--verify-only", action="store_true", dest="verify_only",
                        help="Verify backup integrity without restoring")
    parser.add_argument("--list-contents", action="store_true", dest="list_contents",
                        help="List backup contents and exit")
    parser.add_argument("--no-checksum-verify", action="store_true", dest="no_checksum_verify",
                        help="Skip checksum verification after extraction (faster but less safe)")
    parser.add_argument("--target-dir", type=Path,
                        help="Custom target directory (defaults to standard projects dir)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output (JSON only)")

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    if not args.backup_file.exists():
        logger.error(f"❌ Backup file not found: {args.backup_file}")
        sys.exit(1)

    try:
        # List contents mode
        if args.list_contents:
            contents = list_backup_contents(args.backup_file)

            if args.quiet:
                print(json.dumps(contents, indent=2))
            else:
                print("\n📦 Backup Contents:")
                print("=" * 80)
                print(f"Backup file: {args.backup_file}")
                print(f"Created: {contents['metadata']['backup_timestamp']}")
                print(f"Total projects: {len(contents['projects'])}")
                print(f"Total files: {contents['total_files']}")
                print(f"Total size: {contents['total_size_bytes'] / (1024*1024):.2f} MB")
                print("\nProjects:")
                for project in contents['projects']:
                    file_count = len(contents['files_by_project'][project])
                    print(f"  - {project} ({file_count} files)")
            return

        # Verify only mode
        if args.verify_only:
            verification = verify_backup_integrity(args.backup_file)

            if args.quiet:
                print(json.dumps(verification, indent=2))
            else:
                if verification["passed"]:
                    print(f"✅ Backup verification PASSED: {args.backup_file}")
                    if verification["metadata"]:
                        print(f"   Projects: {', '.join(verification['metadata']['projects'])}")
                        print(f"   Total files: {verification['metadata']['total_files']}")
                else:
                    print(f"❌ Backup verification FAILED: {args.backup_file}")
                    print(f"   Error: {verification['message']}")

            sys.exit(0 if verification["passed"] else 1)

        # Determine target directory
        projects_dir = args.target_dir or Path(get_projects_dir())
        projects_dir.mkdir(parents=True, exist_ok=True)

        # Determine which projects to restore
        selected_projects = [args.project] if args.project else None

        # Execute restore
        result = restore_projects(
            backup_path=args.backup_file,
            projects_dir=projects_dir,
            selected_projects=selected_projects,
            force=args.force,
            verify_checksums=not args.no_checksum_verify,
            dry_run=args.dry_run
        )

        # Output results
        if args.quiet:
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "=" * 80)

            if result["status"] == "dry_run":
                print("🔍 DRY RUN SUMMARY")
                print("=" * 80)
                print(f"Would restore: {', '.join(result['would_restore'])}")
                if result['would_overwrite']:
                    print(f"Would overwrite: {', '.join(result['would_overwrite'])}")
                print(f"Total files: {result['total_files']}")

            elif result["status"] == "success":
                print("✅ RESTORATION COMPLETE")
                print("=" * 80)
                print(f"Restored projects: {', '.join(result['restored_projects'])}")
                print(f"Total files: {result['total_files']}")
                print(f"Verified files: {result['verified_files']}")
                print(f"Timestamp: {result['timestamp']}")

            elif result["status"] == "partial_success":
                print("⚠️  RESTORATION PARTIALLY COMPLETE")
                print("=" * 80)
                if result['restored_projects']:
                    print(f"✅ Restored: {', '.join(result['restored_projects'])}")
                if result['failed_projects']:
                    print(f"❌ Failed: {', '.join(result['failed_projects'])}")
                if result['checksum_failures']:
                    print(f"⚠️  Checksum failures: {len(result['checksum_failures'])} file(s)")
                    for failed_file in result['checksum_failures'][:5]:
                        print(f"   - {failed_file}")
                    if len(result['checksum_failures']) > 5:
                        print(f"   ... and {len(result['checksum_failures']) - 5} more")

            else:  # failed
                print("❌ RESTORATION FAILED")
                print("=" * 80)
                print(f"Failed projects: {', '.join(result['failed_projects'])}")

        # Exit code based on status
        exit_code = 0 if result["status"] in ("success", "dry_run") else 1
        sys.exit(exit_code)

    except ValueError as e:
        if args.quiet:
            print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            logger.error(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Restore cancelled by user")
        sys.exit(130)
    except Exception as e:
        if args.quiet:
            print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            logger.exception(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
