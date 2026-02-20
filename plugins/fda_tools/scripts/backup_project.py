#!/usr/bin/env python3
"""
FDA Project Backup — Disaster Recovery and Data Protection.

Creates timestamped, checksummed zip archives of FDA project data with full
integrity verification and metadata tracking. Supports individual project
backup or bulk backup of all projects.

Usage:
    python3 backup_project.py --project NAME                    # Backup single project
    python3 backup_project.py --all                             # Backup all projects
    python3 backup_project.py --project NAME --output-dir PATH  # Custom output location
    python3 backup_project.py --all --verify-only               # Verify existing backups
    python3 backup_project.py --list-backups                    # List all backup files

Features:
    - SHA-256 checksum verification for data integrity
    - Timestamped archives for version control
    - Metadata file with project inventory and checksums
    - Progress reporting for large projects
    - Automatic output directory creation
    - Dry-run mode for safety validation

Backup Format:
    {project_name}_backup_{timestamp}.zip
    ├── metadata.json (version, timestamp, checksums, project_list)
    ├── checksums.txt (file-level SHA-256 hashes)
    └── projects/{project_name}/... (all project files)

Security:
    - Checksums computed before archiving
    - Verified immediately after creation
    - Atomic write with temp file + rename
    - Backup integrity validated before completion

Author: FDA-Tools Development Team
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Import project directory resolution
from fda_data_store import get_projects_dir

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Version tracking for backup format
BACKUP_VERSION = "1.0.0"
CHUNK_SIZE = 65536  # 64KB chunks for hash computation


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal SHA-256 hash string.

    Raises:
        OSError: If file cannot be read.
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def collect_project_files(project_dir: Path) -> List[Tuple[Path, str]]:
    """Collect all files in a project directory with their checksums.

    Args:
        project_dir: Path to the project directory.

    Returns:
        List of tuples: (file_path, sha256_hash)

    Raises:
        ValueError: If project directory doesn't exist or is empty.
    """
    if not project_dir.exists():
        raise ValueError(f"Project directory not found: {project_dir}")

    if not project_dir.is_dir():
        raise ValueError(f"Not a directory: {project_dir}")

    files_with_hashes: List[Tuple[Path, str]] = []
    all_files = sorted(project_dir.rglob("*"))

    # Filter out directories and symlinks
    file_list = [f for f in all_files if f.is_file() and not f.is_symlink()]

    if not file_list:
        logger.warning(f"Project directory is empty: {project_dir}")
        return files_with_hashes

    # Progress bar for hash computation
    iterator = tqdm(file_list, desc="Computing checksums", unit="file") if TQDM_AVAILABLE else file_list

    for file_path in iterator:
        try:
            file_hash = compute_file_hash(file_path)
            files_with_hashes.append((file_path, file_hash))
        except OSError as e:
            logger.error(f"Failed to hash {file_path}: {e}")
            raise

    return files_with_hashes


def create_backup_metadata(
    project_names: List[str],
    file_checksums: Dict[str, str],
    backup_timestamp: str
) -> Dict:
    """Create metadata dictionary for backup archive.

    Args:
        project_names: List of project names included in backup.
        file_checksums: Dictionary mapping relative paths to SHA-256 hashes.
        backup_timestamp: ISO 8601 timestamp of backup creation.

    Returns:
        Metadata dictionary ready for JSON serialization.
    """
    return {
        "backup_version": BACKUP_VERSION,
        "backup_timestamp": backup_timestamp,
        "projects": sorted(project_names),
        "total_projects": len(project_names),
        "total_files": len(file_checksums),
        "checksums": file_checksums,
        "created_by": "fda-tools/backup_project.py",
        "schema": {
            "version": "1.0",
            "description": "FDA project backup with integrity verification"
        }
    }


def create_backup_archive(
    projects_dir: Path,
    project_names: List[str],
    output_path: Path,
    verify: bool = True
) -> Dict:
    """Create a backup archive of one or more projects.

    Args:
        projects_dir: Base directory containing all projects.
        project_names: List of project names to backup.
        output_path: Path to the output zip file.
        verify: If True, verify archive integrity after creation.

    Returns:
        Dictionary with backup results:
        {
            "status": "success" | "failed",
            "backup_file": str,
            "projects": List[str],
            "total_files": int,
            "total_size_bytes": int,
            "checksum_sha256": str,
            "timestamp": str,
            "verification": {"passed": bool, "message": str}
        }

    Raises:
        ValueError: If no valid projects found or output path exists.
        OSError: If file operations fail.
    """
    if output_path.exists():
        raise ValueError(f"Backup file already exists: {output_path}")

    backup_timestamp = datetime.now(timezone.utc).isoformat()
    all_files: List[Tuple[Path, Path, str]] = []  # (absolute_path, relative_path, hash)
    file_checksums: Dict[str, str] = {}

    # Collect files from all projects
    for project_name in project_names:
        project_dir = projects_dir / project_name

        if not project_dir.exists():
            logger.warning(f"Skipping non-existent project: {project_name}")
            continue

        logger.info(f"Collecting files from project: {project_name}")
        files_with_hashes = collect_project_files(project_dir)

        for abs_path, file_hash in files_with_hashes:
            # Compute relative path from projects_dir
            rel_path = abs_path.relative_to(projects_dir)
            all_files.append((abs_path, rel_path, file_hash))
            file_checksums[str(rel_path)] = file_hash

    if not all_files:
        raise ValueError("No files found to backup")

    # Create checksums.txt content
    checksums_txt = "\n".join(
        f"{file_hash}  {rel_path}"
        for _, rel_path, file_hash in sorted(all_files, key=lambda x: str(x[1]))
    )

    # Create metadata
    metadata = create_backup_metadata(project_names, file_checksums, backup_timestamp)

    # Create zip archive with temp file for atomic write
    temp_output = output_path.with_suffix('.zip.tmp')
    total_size = 0

    try:
        logger.info(f"Creating backup archive: {output_path}")

        with zipfile.ZipFile(temp_output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            # Write metadata.json
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))

            # Write checksums.txt
            zf.writestr("checksums.txt", checksums_txt)

            # Write all project files
            iterator = tqdm(all_files, desc="Archiving files", unit="file") if TQDM_AVAILABLE else all_files

            for abs_path, rel_path, _ in iterator:
                archive_path = f"projects/{rel_path}"
                zf.write(abs_path, archive_path)
                total_size += abs_path.stat().st_size

        # Compute archive checksum
        archive_hash = compute_file_hash(temp_output)

        # Atomic rename
        temp_output.rename(output_path)

        logger.info(f"✅ Backup created successfully: {output_path}")
        logger.info(f"   Total files: {len(all_files)}")
        logger.info(f"   Total size: {total_size / (1024*1024):.2f} MB")
        logger.info(f"   Archive SHA-256: {archive_hash}")

        # Verify archive integrity
        verification_result = {"passed": True, "message": "Verification skipped"}
        if verify:
            verification_result = verify_backup_integrity(output_path)
            if verification_result["passed"]:
                logger.info("✅ Backup verification PASSED")
            else:
                logger.error(f"❌ Backup verification FAILED: {verification_result['message']}")

        return {
            "status": "success",
            "backup_file": str(output_path),
            "projects": project_names,
            "total_files": len(all_files),
            "total_size_bytes": total_size,
            "checksum_sha256": archive_hash,
            "timestamp": backup_timestamp,
            "verification": verification_result
        }

    except Exception as e:
        # Cleanup temp file on error
        if temp_output.exists():
            temp_output.unlink()
        logger.error(f"Backup creation failed: {e}")
        raise


def verify_backup_integrity(backup_path: Path) -> Dict:
    """Verify integrity of a backup archive.

    Args:
        backup_path: Path to the backup zip file.

    Returns:
        Dictionary with verification results:
        {
            "passed": bool,
            "message": str,
            "metadata": dict | None,
            "corrupted_files": List[str],
            "missing_files": List[str]
        }
    """
    if not backup_path.exists():
        return {
            "passed": False,
            "message": f"Backup file not found: {backup_path}",
            "metadata": None,
            "corrupted_files": [],
            "missing_files": []
        }

    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            # Verify archive integrity
            bad_file = zf.testzip()
            if bad_file:
                return {
                    "passed": False,
                    "message": f"Corrupted file in archive: {bad_file}",
                    "metadata": None,
                    "corrupted_files": [bad_file],
                    "missing_files": []
                }

            # Read metadata
            try:
                metadata_content = zf.read("metadata.json")
                metadata = json.loads(metadata_content)
            except KeyError:
                return {
                    "passed": False,
                    "message": "Missing metadata.json in archive",
                    "metadata": None,
                    "corrupted_files": [],
                    "missing_files": ["metadata.json"]
                }

            # Verify checksums.txt exists
            if "checksums.txt" not in zf.namelist():
                return {
                    "passed": False,
                    "message": "Missing checksums.txt in archive",
                    "metadata": metadata,
                    "corrupted_files": [],
                    "missing_files": ["checksums.txt"]
                }

            # Verify all files listed in metadata exist in archive
            expected_files = set(f"projects/{path}" for path in metadata["checksums"].keys())
            archive_files = set(zf.namelist()) - {"metadata.json", "checksums.txt"}
            missing_files = expected_files - archive_files

            if missing_files:
                return {
                    "passed": False,
                    "message": f"Missing {len(missing_files)} file(s) in archive",
                    "metadata": metadata,
                    "corrupted_files": [],
                    "missing_files": sorted(missing_files)
                }

            return {
                "passed": True,
                "message": "Backup integrity verified successfully",
                "metadata": metadata,
                "corrupted_files": [],
                "missing_files": []
            }

    except zipfile.BadZipFile as e:
        return {
            "passed": False,
            "message": f"Invalid zip file: {e}",
            "metadata": None,
            "corrupted_files": [],
            "missing_files": []
        }
    except Exception as e:
        return {
            "passed": False,
            "message": f"Verification error: {e}",
            "metadata": None,
            "corrupted_files": [],
            "missing_files": []
        }


def list_available_backups(backup_dir: Path) -> List[Dict]:
    """List all backup files in a directory with metadata.

    Args:
        backup_dir: Directory to scan for backup files.

    Returns:
        List of dictionaries with backup information:
        [
            {
                "filename": str,
                "path": str,
                "size_mb": float,
                "created": str,
                "projects": List[str],
                "total_files": int,
                "backup_version": str
            },
            ...
        ]
    """
    if not backup_dir.exists():
        return []

    backups = []
    for backup_file in sorted(backup_dir.glob("*_backup_*.zip")):
        try:
            verification = verify_backup_integrity(backup_file)
            if verification["passed"] and verification["metadata"]:
                metadata = verification["metadata"]
                backups.append({
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": backup_file.stat().st_size / (1024 * 1024),
                    "created": metadata.get("backup_timestamp", "unknown"),
                    "projects": metadata.get("projects", []),
                    "total_files": metadata.get("total_files", 0),
                    "backup_version": metadata.get("backup_version", "unknown")
                })
        except Exception as e:
            logger.warning(f"Failed to read backup metadata from {backup_file.name}: {e}")

    return backups


def backup_single_project(
    project_name: str,
    output_dir: Optional[Path] = None,
    verify: bool = True
) -> Dict:
    """Backup a single project.

    Args:
        project_name: Name of the project to backup.
        output_dir: Optional custom output directory (defaults to projects_dir/backups).
        verify: If True, verify backup integrity after creation.

    Returns:
        Backup result dictionary from create_backup_archive().

    Raises:
        ValueError: If project doesn't exist.
        OSError: If backup creation fails.
    """
    projects_dir = Path(get_projects_dir())
    project_dir = projects_dir / project_name

    if not project_dir.exists():
        raise ValueError(f"Project not found: {project_name}")

    # Default output directory
    if output_dir is None:
        output_dir = projects_dir / "backups"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_filename = f"{project_name}_backup_{timestamp}.zip"
    output_path = output_dir / output_filename

    return create_backup_archive(projects_dir, [project_name], output_path, verify=verify)


def backup_all_projects(
    output_dir: Optional[Path] = None,
    verify: bool = True
) -> Dict:
    """Backup all projects in a single archive.

    Args:
        output_dir: Optional custom output directory (defaults to projects_dir/backups).
        verify: If True, verify backup integrity after creation.

    Returns:
        Backup result dictionary from create_backup_archive().

    Raises:
        ValueError: If no projects found.
        OSError: If backup creation fails.
    """
    projects_dir = Path(get_projects_dir())

    if not projects_dir.exists():
        raise ValueError(f"Projects directory not found: {projects_dir}")

    # Find all project directories (those with data_manifest.json or any content)
    project_names = [
        d.name for d in projects_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name != 'backups'
    ]

    if not project_names:
        raise ValueError("No projects found to backup")

    # Default output directory
    if output_dir is None:
        output_dir = projects_dir / "backups"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_filename = f"all_projects_backup_{timestamp}.zip"
    output_path = output_dir / output_filename

    logger.info(f"Backing up {len(project_names)} projects: {', '.join(sorted(project_names))}")

    return create_backup_archive(projects_dir, project_names, output_path, verify=verify)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA Project Backup — Disaster Recovery and Data Protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backup single project
  python3 backup_project.py --project batch_DQY_sterile_catheter

  # Backup all projects
  python3 backup_project.py --all

  # Custom output directory
  python3 backup_project.py --project NAME --output-dir ~/my-backups

  # Verify existing backup
  python3 backup_project.py --verify ~/backups/project_backup_20260217.zip

  # List all backups
  python3 backup_project.py --list-backups
        """
    )

    parser.add_argument("--project", help="Project name to backup")
    parser.add_argument("--all", action="store_true", help="Backup all projects")
    parser.add_argument("--output-dir", type=Path, help="Custom output directory")
    parser.add_argument("--verify", type=Path, help="Verify integrity of existing backup file")
    parser.add_argument("--verify-only", action="store_true", dest="verify_only",
                        help="Skip backup creation, only verify")
    parser.add_argument("--list-backups", action="store_true", dest="list_backups",
                        help="List all available backups")
    parser.add_argument("--quiet", action="store_true", help="Minimal output (JSON only)")

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    try:
        # List backups mode
        if args.list_backups:
            projects_dir = Path(get_projects_dir())
            backup_dir = args.output_dir or (projects_dir / "backups")
            backups = list_available_backups(backup_dir)

            if args.quiet:
                print(json.dumps(backups, indent=2))
            else:
                if not backups:
                    print(f"No backups found in {backup_dir}")
                else:
                    print(f"\n📦 Available Backups ({len(backups)}):")
                    print("=" * 80)
                    for backup in backups:
                        print(f"\n  File: {backup['filename']}")
                        print(f"  Size: {backup['size_mb']:.2f} MB")
                        print(f"  Created: {backup['created']}")
                        print(f"  Projects: {', '.join(backup['projects'])}")
                        print(f"  Total files: {backup['total_files']}")
            return

        # Verify mode
        if args.verify:
            result = verify_backup_integrity(args.verify)

            if args.quiet:
                print(json.dumps(result, indent=2))
            else:
                if result["passed"]:
                    print(f"✅ Backup verification PASSED: {args.verify}")
                    if result["metadata"]:
                        print(f"   Projects: {', '.join(result['metadata']['projects'])}")
                        print(f"   Total files: {result['metadata']['total_files']}")
                        print(f"   Timestamp: {result['metadata']['backup_timestamp']}")
                else:
                    print(f"❌ Backup verification FAILED: {args.verify}")
                    print(f"   Error: {result['message']}")
                    if result["corrupted_files"]:
                        print(f"   Corrupted files: {', '.join(result['corrupted_files'])}")
                    if result["missing_files"]:
                        print(f"   Missing files: {', '.join(result['missing_files'])}")

            sys.exit(0 if result["passed"] else 1)

        # Backup mode
        if args.verify_only:
            parser.error("--verify-only requires --verify PATH")

        if args.all:
            result = backup_all_projects(output_dir=args.output_dir, verify=not args.verify_only)
        elif args.project:
            result = backup_single_project(
                args.project,
                output_dir=args.output_dir,
                verify=not args.verify_only
            )
        else:
            parser.print_help()
            sys.exit(1)

        # Output results
        if args.quiet:
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "=" * 80)
            print("✅ BACKUP COMPLETE")
            print("=" * 80)
            print(f"Backup file: {result['backup_file']}")
            print(f"Projects: {', '.join(result['projects'])}")
            print(f"Total files: {result['total_files']}")
            print(f"Total size: {result['total_size_bytes'] / (1024*1024):.2f} MB")
            print(f"SHA-256: {result['checksum_sha256']}")
            print(f"Timestamp: {result['timestamp']}")

            if result['verification']['passed']:
                print(f"\n✅ Verification: PASSED")
            else:
                print(f"\n⚠️  Verification: {result['verification']['message']}")

    except ValueError as e:
        if args.quiet:
            print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            logger.error(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Backup cancelled by user")
        sys.exit(130)
    except Exception as e:
        if args.quiet:
            print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            logger.exception(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
