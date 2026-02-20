#!/usr/bin/env python3
"""Automated version bumping script for FDA Tools.

This script automatically increments the version number in pyproject.toml
according to semantic versioning rules.

Usage:
    python scripts/bump_version.py patch  # 5.36.0 -> 5.36.1
    python scripts/bump_version.py minor  # 5.36.0 -> 5.37.0
    python scripts/bump_version.py major  # 5.36.0 -> 6.0.0
    python scripts/bump_version.py 5.37.0 # Set specific version
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Tuple


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse a semantic version string into (major, minor, patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version tuple as string."""
    return f"{major}.{minor}.{patch}"


def bump_version(current: str, bump_type: str) -> str:
    """Bump version according to semantic versioning.

    Args:
        current: Current version string (e.g., "5.36.0")
        bump_type: One of "major", "minor", "patch", or a specific version

    Returns:
        New version string
    """
    if bump_type not in ["major", "minor", "patch"]:
        # Specific version provided
        try:
            parse_version(bump_type)
            return bump_type
        except ValueError:
            raise ValueError(
                f"Invalid bump type or version: {bump_type}. "
                "Use 'major', 'minor', 'patch', or a specific version like '5.37.0'"
            )

    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return format_version(major + 1, 0, 0)
    elif bump_type == "minor":
        return format_version(major, minor + 1, 0)
    else:  # patch
        return format_version(major, minor, patch + 1)


def get_current_version(pyproject_path: Path) -> str:
    """Extract current version from pyproject.toml."""
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def update_version_in_file(file_path: Path, old_version: str, new_version: str) -> bool:
    """Update version in a file.

    Returns:
        True if file was modified, False otherwise
    """
    content = file_path.read_text()

    # Pattern for pyproject.toml
    new_content = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )

    if new_content == content:
        return False

    file_path.write_text(new_content)
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bump version number in pyproject.toml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s patch       # Bump patch version (5.36.0 -> 5.36.1)
  %(prog)s minor       # Bump minor version (5.36.0 -> 5.37.0)
  %(prog)s major       # Bump major version (5.36.0 -> 6.0.0)
  %(prog)s 5.37.0      # Set specific version

After bumping:
  git add pyproject.toml
  git commit -m "chore: bump version to {new_version}"
  git tag -a v{new_version} -m "Release {new_version}"
  git push origin master --tags
        """,
    )
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        nargs="?",
        help="Version component to bump, or specific version number",
    )
    parser.add_argument(
        "--version",
        "-v",
        help="Specific version to set (alternative to bump_type)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Determine bump type or version
    bump_type = args.version or args.bump_type
    if not bump_type:
        parser.error("Either bump_type or --version must be specified")

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Error: Could not find pyproject.toml at {pyproject_path}", file=sys.stderr)
        return 1

    try:
        # Get current version
        current_version = get_current_version(pyproject_path)
        print(f"Current version: {current_version}")

        # Calculate new version
        new_version = bump_version(current_version, bump_type)
        print(f"New version:     {new_version}")

        if args.dry_run:
            print("\n[DRY RUN] No files were modified")
            return 0

        # Update version in pyproject.toml
        modified = update_version_in_file(pyproject_path, current_version, new_version)

        if modified:
            print(f"\nUpdated: {pyproject_path}")
            print("\nNext steps:")
            print(f"  git add pyproject.toml")
            print(f'  git commit -m "chore: bump version to {new_version}"')
            print(f'  git tag -a v{new_version} -m "Release {new_version}"')
            print(f"  git push origin master --tags")
        else:
            print("\nNo changes made (version already set)")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
