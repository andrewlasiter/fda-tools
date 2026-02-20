#!/usr/bin/env python3
"""
FDA Data Manifest Migration Utility -- Schema Version Migration for data_manifest.json.

Handles migration of data_manifest.json files from older schema versions to
the current schema version. Supports batch migration across multiple projects.

Migration Support:
    - Legacy (no schema_version) → 1.0.0: Add schema_version, validate structure
    - Future migrations: 1.0.0 → 1.1.0, 1.1.0 → 2.0.0, etc.

Usage:
    # Migrate a single project
    python3 migrate_manifest.py --project my_project

    # Migrate all projects
    python3 migrate_manifest.py --all-projects

    # Dry-run mode (preview changes without saving)
    python3 migrate_manifest.py --project my_project --dry-run

    # Backup before migration (default: creates .bak file)
    python3 migrate_manifest.py --project my_project --backup

    # Migrate PMA cache manifest
    python3 migrate_manifest.py --pma-cache

    # Direct file migration
    python3 migrate_manifest.py --file /path/to/data_manifest.json
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add parent directory to path for imports

try:
    from manifest_validator import (  # type: ignore
        validate_manifest,
        get_schema_version,
        CURRENT_SCHEMA_VERSION,
        ValidationError,
    )
    _VALIDATOR_AVAILABLE = True
except ImportError:
    _VALIDATOR_AVAILABLE = False
    CURRENT_SCHEMA_VERSION = "1.0.0"


# Migration functions for each version transition
# Format: "from_version->to_version": migration_function

def migrate_legacy_to_1_0_0(manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Migrate a legacy manifest (no schema_version) to version 1.0.0.

    Args:
        manifest: Legacy manifest dictionary.

    Returns:
        Tuple of (migrated_manifest, changes_log).
    """
    changes = []
    migrated = manifest.copy()

    # Add schema_version
    migrated["schema_version"] = "1.0.0"
    changes.append("Added schema_version field (1.0.0)")

    # Ensure timestamps exist and are in correct format
    now = datetime.now(timezone.utc).isoformat()

    if "created_at" not in migrated:
        migrated["created_at"] = now
        changes.append("Added created_at timestamp")
    else:
        # Validate/fix timestamp format
        if not migrated["created_at"].endswith(("Z", "+00:00")):
            # Try to parse and reformat
            try:
                dt = datetime.fromisoformat(migrated["created_at"].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                migrated["created_at"] = dt.isoformat()
                changes.append("Fixed created_at timestamp format (added timezone)")
            except (ValueError, AttributeError):
                migrated["created_at"] = now
                changes.append("Replaced invalid created_at timestamp")

    if "last_updated" not in migrated:
        migrated["last_updated"] = now
        changes.append("Added last_updated timestamp")
    else:
        # Fix timezone if missing
        if not migrated["last_updated"].endswith(("Z", "+00:00")):
            try:
                dt = datetime.fromisoformat(migrated["last_updated"].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                migrated["last_updated"] = dt.isoformat()
                changes.append("Fixed last_updated timestamp format (added timezone)")
            except (ValueError, AttributeError):
                migrated["last_updated"] = now
                changes.append("Replaced invalid last_updated timestamp")

    # Ensure required fields exist
    if "product_codes" not in migrated:
        migrated["product_codes"] = []
        changes.append("Added product_codes array")

    if "queries" not in migrated:
        migrated["queries"] = {}
        changes.append("Added queries object")

    # Normalize product codes to uppercase
    if isinstance(migrated.get("product_codes"), list):
        original_codes = migrated["product_codes"]
        normalized_codes = [code.upper() for code in original_codes if isinstance(code, str)]
        if normalized_codes != original_codes:
            migrated["product_codes"] = normalized_codes
            changes.append("Normalized product codes to uppercase")

    # Fix query entry timestamps
    query_fixes = 0
    for query_key, query_entry in migrated.get("queries", {}).items():
        if isinstance(query_entry, dict):
            fetched_at = query_entry.get("fetched_at", "")
            if fetched_at and not fetched_at.endswith(("Z", "+00:00")):
                try:
                    dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    query_entry["fetched_at"] = dt.isoformat()
                    query_fixes += 1
                except (ValueError, AttributeError):
                    pass  # Keep original if we can't parse it

    if query_fixes > 0:
        changes.append(f"Fixed {query_fixes} query timestamp(s) to include timezone")

    # Fix fingerprint timestamps
    fingerprint_fixes = 0
    for product_code, fingerprint in migrated.get("fingerprints", {}).items():
        if isinstance(fingerprint, dict):
            last_updated = fingerprint.get("last_updated", "")
            if last_updated and not last_updated.endswith(("Z", "+00:00")):
                try:
                    dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    fingerprint["last_updated"] = dt.isoformat()
                    fingerprint_fixes += 1
                except (ValueError, AttributeError):
                    pass

    if fingerprint_fixes > 0:
        changes.append(f"Fixed {fingerprint_fixes} fingerprint timestamp(s)")

    # Fix PMA entry timestamps
    pma_fixes = 0
    for pma_number, pma_entry in migrated.get("pma_entries", {}).items():
        if isinstance(pma_entry, dict):
            timestamp_fields = [
                "first_cached_at", "last_updated", "pma_approval_fetched_at",
                "pma_supplements_fetched_at", "ssed_downloaded_at", "sections_extracted_at"
            ]
            for field in timestamp_fields:
                ts = pma_entry.get(field, "")
                if ts and not ts.endswith(("Z", "+00:00")):
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        pma_entry[field] = dt.isoformat()
                        pma_fixes += 1
                    except (ValueError, AttributeError):
                        pass

    if pma_fixes > 0:
        changes.append(f"Fixed {pma_fixes} PMA entry timestamp(s)")

    return migrated, changes


# Migration registry: maps version transitions to migration functions
MIGRATIONS = {
    "legacy->1.0.0": migrate_legacy_to_1_0_0,
    # Future migrations will be added here:
    # "1.0.0->1.1.0": migrate_1_0_0_to_1_1_0,
    # "1.1.0->2.0.0": migrate_1_1_0_to_2_0_0,
}


def get_migration_path(from_version: Optional[str], to_version: str) -> List[str]:
    """Determine the migration path from one version to another.

    Args:
        from_version: Starting version (None for legacy manifests).
        to_version: Target version.

    Returns:
        List of migration keys to apply in order (e.g., ["legacy->1.0.0", "1.0.0->1.1.0"]).
    """
    if from_version is None:
        from_version = "legacy"

    if from_version == to_version:
        return []

    # For now, only support direct migrations
    # Future: implement multi-step migration path finding
    migration_key = f"{from_version}->{to_version}"
    if migration_key in MIGRATIONS:
        return [migration_key]

    # Try legacy path
    if from_version == "legacy" and to_version == CURRENT_SCHEMA_VERSION:
        return ["legacy->1.0.0"]

    return []


def migrate_manifest(
    manifest: Dict[str, Any],
    target_version: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Migrate a manifest to a target schema version.

    Args:
        manifest: Manifest dictionary to migrate.
        target_version: Target schema version (default: CURRENT_SCHEMA_VERSION).

    Returns:
        Tuple of (migrated_manifest, changes_log).

    Raises:
        ValueError: If no migration path exists from current to target version.
    """
    if target_version is None:
        target_version = CURRENT_SCHEMA_VERSION

    current_version = get_schema_version(manifest) if _VALIDATOR_AVAILABLE else None
    all_changes = []

    if current_version == target_version:
        return manifest, ["No migration needed (already at target version)"]

    # Get migration path
    migration_path = get_migration_path(current_version, target_version)

    if not migration_path:
        raise ValueError(
            f"No migration path found from version {current_version or 'legacy'} "
            f"to {target_version}"
        )

    # Apply migrations in sequence
    migrated = manifest.copy()
    for migration_key in migration_path:
        migration_func = MIGRATIONS[migration_key]
        migrated, changes = migration_func(migrated)
        all_changes.extend(changes)

    return migrated, all_changes


def migrate_manifest_file(
    manifest_path: str,
    backup: bool = True,
    dry_run: bool = False,
) -> Tuple[bool, List[str]]:
    """Migrate a data_manifest.json file in-place.

    Args:
        manifest_path: Path to the manifest file.
        backup: If True, create a .bak backup before migrating.
        dry_run: If True, preview changes without saving.

    Returns:
        Tuple of (success: bool, changes_log: List[str]).
    """
    path = Path(manifest_path)
    if not path.exists():
        return False, [f"ERROR: File not found: {manifest_path}"]

    changes = []

    # Load manifest
    try:
        with open(path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"ERROR: Invalid JSON: {e}"]

    # Get current version
    current_version = get_schema_version(manifest) if _VALIDATOR_AVAILABLE else None
    changes.append(f"Current schema version: {current_version or 'legacy (no version)'}")
    changes.append(f"Target schema version: {CURRENT_SCHEMA_VERSION}")

    # Migrate
    try:
        migrated, migration_changes = migrate_manifest(manifest)
    except ValueError as e:
        return False, [f"ERROR: {e}"]

    changes.extend(migration_changes)

    # Validate migrated manifest
    if _VALIDATOR_AVAILABLE:
        try:
            validate_manifest(migrated, strict=True)
            changes.append("✓ Migrated manifest passes schema validation")
        except ValidationError as e:
            return False, changes + [
                f"ERROR: Migrated manifest failed validation: {e}",
                "  Migration was not saved due to validation failure.",
            ]

    # Dry-run mode: show changes but don't save
    if dry_run:
        changes.append("\n[DRY-RUN] Changes preview (not saved):")
        return True, changes

    # Create backup
    if backup:
        backup_path = path.with_suffix(".json.bak")
        shutil.copy2(path, backup_path)
        changes.append(f"Created backup: {backup_path}")

    # Write migrated manifest (atomic write)
    tmp_path = path.with_suffix(".json.tmp")
    try:
        with open(tmp_path, "w") as f:
            json.dump(migrated, f, indent=2)
        tmp_path.replace(path)
        changes.append(f"✓ Migrated manifest saved: {path}")
    except OSError as e:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return False, changes + [f"ERROR: Failed to save migrated manifest: {e}"]

    return True, changes


def find_all_manifests(base_dir: str) -> List[str]:
    """Find all data_manifest.json files in a directory tree.

    Args:
        base_dir: Base directory to search.

    Returns:
        List of absolute paths to data_manifest.json files.
    """
    manifests = []
    for root, dirs, files in os.walk(base_dir):
        if "data_manifest.json" in files:
            manifests.append(os.path.join(root, "data_manifest.json"))
    return manifests


def get_projects_dir() -> str:
    """Determine the projects directory from settings or default."""
    import re

    settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r"projects_dir:\s*(.+)", f.read())
            if m:
                return os.path.expanduser(m.group(1).strip())
    return os.path.expanduser("~/fda-510k-data/projects")


def get_pma_cache_dir() -> str:
    """Determine the PMA cache directory from settings or default."""
    import re

    settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r"pma_cache_dir:\s*(.+)", f.read())
            if m:
                return os.path.expanduser(m.group(1).strip())
    return os.path.expanduser("~/fda-510k-data/pma_cache")


def main():
    """CLI interface for manifest migration."""
    parser = argparse.ArgumentParser(
        description="Migrate FDA data manifest files to current schema version"
    )

    # Input selection (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--project",
        help="Project name (will look in projects_dir/PROJECT_NAME/data_manifest.json)",
    )
    input_group.add_argument(
        "--all-projects",
        action="store_true",
        dest="all_projects",
        help="Migrate all projects in projects_dir",
    )
    input_group.add_argument(
        "--pma-cache",
        action="store_true",
        dest="pma_cache",
        help="Migrate PMA cache manifest (pma_cache_dir/data_manifest.json)",
    )
    input_group.add_argument(
        "--file",
        help="Direct path to data_manifest.json file",
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Preview changes without saving",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        dest="no_backup",
        help="Skip creating .bak backup files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed migration logs",
    )

    args = parser.parse_args()

    # Determine manifest path(s)
    manifest_paths = []

    if args.project:
        projects_dir = get_projects_dir()
        manifest_path = os.path.join(projects_dir, args.project, "data_manifest.json")
        if not os.path.exists(manifest_path):
            print(f"ERROR: Manifest not found for project '{args.project}': {manifest_path}", file=sys.stderr)
            sys.exit(1)
        manifest_paths = [manifest_path]

    elif args.all_projects:
        projects_dir = get_projects_dir()
        if not os.path.exists(projects_dir):
            print(f"ERROR: Projects directory not found: {projects_dir}", file=sys.stderr)
            sys.exit(1)
        manifest_paths = find_all_manifests(projects_dir)
        if not manifest_paths:
            print(f"No data_manifest.json files found in {projects_dir}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(manifest_paths)} manifest(s) to migrate")

    elif args.pma_cache:
        pma_cache_dir = get_pma_cache_dir()
        manifest_path = os.path.join(pma_cache_dir, "data_manifest.json")
        if not os.path.exists(manifest_path):
            print(f"ERROR: PMA cache manifest not found: {manifest_path}", file=sys.stderr)
            sys.exit(1)
        manifest_paths = [manifest_path]

    elif args.file:
        if not os.path.exists(args.file):
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        manifest_paths = [args.file]

    # Migrate each manifest
    success_count = 0
    failure_count = 0

    for manifest_path in manifest_paths:
        print(f"\n{'='*70}")
        print(f"Migrating: {manifest_path}")
        print(f"{'='*70}")

        success, changes = migrate_manifest_file(
            manifest_path,
            backup=not args.no_backup,
            dry_run=args.dry_run,
        )

        if args.verbose or not success:
            for change in changes:
                print(change)

        if success:
            success_count += 1
            if not args.verbose:
                print("✓ Migration successful")
        else:
            failure_count += 1
            print("✗ Migration failed", file=sys.stderr)

    # Summary
    print(f"\n{'='*70}")
    print(f"Migration summary: {success_count} succeeded, {failure_count} failed")
    print(f"{'='*70}")

    sys.exit(0 if failure_count == 0 else 1)


if __name__ == "__main__":
    main()
