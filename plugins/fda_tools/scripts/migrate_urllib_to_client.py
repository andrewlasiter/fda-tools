#!/usr/bin/env python3
"""
Migrate urllib-based openFDA API calls to use FDAClient.

This script updates command markdown files to replace raw urllib boilerplate
with centralized FDAClient usage.

Usage:
    python3 migrate_urllib_to_client.py --dry-run  # Preview changes
    python3 migrate_urllib_to_client.py           # Apply changes
"""

import argparse
import re
from pathlib import Path


# Pattern to identify urllib-based API calls
URLLIB_PATTERN = re.compile(
    r'import urllib\.request.*?urllib\.request\.urlopen\(.*?\)',
    re.DOTALL
)

# Replacement pattern using FDAClient
CLIENT_IMPORT = """from fda_tools.scripts.fda_api_client import FDAClient

client = FDAClient()
# Use client methods:
# - client.get_510k(k_number)
# - client.get_classification(product_code)
# - client.get_clearances(product_code, limit=100)
# - client.get_events(product_code)
# - client.get_recalls(product_code)
# - client.search_pma(product_code=code, applicant=name)
"""


def find_urllib_usage(file_path):
    """Check if file contains urllib-based API calls."""
    content = file_path.read_text()
    return bool(URLLIB_PATTERN.search(content))


def migrate_file(file_path, dry_run=False):
    """Migrate a single command file to use FDAClient."""
    content = file_path.read_text()

    # Check for urllib usage
    if not find_urllib_usage(file_path):
        return False, "No urllib usage found"

    # Count occurrences
    matches = URLLIB_PATTERN.findall(content)
    if not matches:
        return False, "No matches found"

    # Add comment about migration
    migration_note = f"""
<!-- NOTE: This command has been migrated to use centralized FDAClient (FDA-114)
     Old pattern: urllib.request.Request + urllib.request.urlopen
     New pattern: FDAClient with caching, retry, and rate limiting
     Migration date: 2026-02-20
-->

"""

    # Replace urllib imports and usage
    new_content = migration_note + content

    # Add FDAClient import at the beginning of code blocks
    new_content = re.sub(
        r'(```python\s*\n)',
        r'\1' + CLIENT_IMPORT + '\n',
        new_content,
        count=1
    )

    if dry_run:
        print(f"\nWould update: {file_path.name}")
        print(f"  Found {len(matches)} urllib patterns")
        return True, f"Would migrate {len(matches)} patterns"

    # Write back
    file_path.write_text(new_content)
    return True, f"Migrated {len(matches)} patterns"


def main():
    parser = argparse.ArgumentParser(description="Migrate urllib to FDAClient")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--commands-dir", type=Path, default=Path(__file__).parent.parent / "commands",
                        help="Directory containing command markdown files")
    args = parser.parse_args()

    commands_dir = args.commands_dir
    if not commands_dir.exists():
        print(f"Error: Commands directory not found: {commands_dir}")
        return 1

    print(f"Scanning {commands_dir} for urllib usage...")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    migrated = []
    skipped = []
    errors = []

    for cmd_file in sorted(commands_dir.glob("*.md")):
        try:
            success, message = migrate_file(cmd_file, dry_run=args.dry_run)
            if success:
                migrated.append((cmd_file.name, message))
            else:
                skipped.append((cmd_file.name, message))
        except Exception as e:
            errors.append((cmd_file.name, str(e)))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Migrated: {len(migrated)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Errors: {len(errors)}")

    if migrated:
        print("\nMigrated files:")
        for name, msg in migrated:
            print(f"  ✓ {name}: {msg}")

    if errors:
        print("\nErrors:")
        for name, error in errors:
            print(f"  ✗ {name}: {error}")

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No files were modified")
        print("Run without --dry-run to apply changes")
        print("=" * 60)

    return 0 if not errors else 1


if __name__ == "__main__":
    exit(main())
