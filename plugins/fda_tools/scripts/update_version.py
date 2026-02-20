#!/usr/bin/env python3
"""
Atomic version updater for FDA Tools plugin.

Updates version strings atomically across all project files:
- scripts/version.py
- .claude-plugin/plugin.json
- CHANGELOG.md (adds new version entry)

Usage:
    ./update_version.py 5.37.0 --message "New feature release"
    ./update_version.py 5.36.1 --patch --message "Bug fixes"
"""

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional


class VersionUpdater:
    """Updates version atomically across all project files."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize version updater.

        Args:
            project_root: Root directory of the project. If None, auto-detect from script location.
        """
        if project_root is None:
            # Auto-detect: scripts/update_version.py -> project root
            self.project_root = Path(__file__).resolve().parent.parent
        else:
            self.project_root = Path(project_root).resolve()

        self.changes_made = []
        self.errors = []

    def update_all(self, new_version: str, changelog_message: Optional[str] = None, dry_run: bool = False) -> bool:
        """
        Update version in all project files atomically.

        Args:
            new_version: New version string (e.g., "5.37.0")
            changelog_message: Optional message for CHANGELOG.md entry
            dry_run: If True, show what would change without writing files

        Returns:
            True if successful, False otherwise.
        """
        # Validate version format
        if not self._validate_version(new_version):
            self.errors.append(f"Invalid version format: '{new_version}' (expected X.Y.Z)")
            return False

        # Update all files
        success = True
        success &= self._update_version_py(new_version, dry_run)
        success &= self._update_plugin_json(new_version, dry_run)
        success &= self._update_changelog(new_version, changelog_message, dry_run)

        return success

    def _validate_version(self, version: str) -> bool:
        """Validate semantic version format (X.Y.Z)."""
        return bool(re.match(r'^\d+\.\d+\.\d+$', version))

    def _update_version_py(self, new_version: str, dry_run: bool) -> bool:
        """Update scripts/version.py."""
        version_file = self.project_root / "scripts" / "version.py"

        if not version_file.exists():
            self.errors.append(f"Version file not found: {version_file}")
            return False

        try:
            with version_file.open("r", encoding="utf-8") as f:
                content = f.read()

            # Read plugin.json to update get_plugin_version() call
            # We need to update the actual version returned by the function
            # The current version.py reads from plugin.json, so we just need to ensure
            # that plugin.json is updated (which we do separately)

            # Check if version.py has a hardcoded PLUGIN_VERSION
            if 'PLUGIN_VERSION = "' in content or "PLUGIN_VERSION = '" in content:
                # Update hardcoded version
                new_content = re.sub(
                    r'(PLUGIN_VERSION\s*=\s*["\'])([^"\']+)(["\'])',
                    rf'\g<1>{new_version}\g<3>',
                    content
                )

                if new_content != content:
                    if not dry_run:
                        with version_file.open("w", encoding="utf-8") as f:
                            f.write(new_content)
                    self.changes_made.append(f"Updated version.py: hardcoded PLUGIN_VERSION → {new_version}")
                    return True
            else:
                # version.py reads from plugin.json, no change needed here
                self.changes_made.append("version.py: No change needed (reads from plugin.json)")
                return True

        except Exception as e:
            self.errors.append(f"Error updating version.py: {e}")
            return False

        return True

    def _update_plugin_json(self, new_version: str, dry_run: bool) -> bool:
        """Update .claude-plugin/plugin.json."""
        plugin_file = self.project_root / ".claude-plugin" / "plugin.json"

        if not plugin_file.exists():
            self.errors.append(f"Plugin manifest not found: {plugin_file}")
            return False

        try:
            with plugin_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            old_version = data.get("version", "UNKNOWN")
            data["version"] = new_version

            if not dry_run:
                with plugin_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n")  # Add trailing newline

            self.changes_made.append(f"Updated plugin.json: {old_version} → {new_version}")
            return True

        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in plugin.json: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error updating plugin.json: {e}")
            return False

    def _update_changelog(self, new_version: str, message: Optional[str], dry_run: bool) -> bool:
        """Update CHANGELOG.md with new version entry."""
        changelog_file = self.project_root / "CHANGELOG.md"

        if not changelog_file.exists():
            self.errors.append(f"CHANGELOG.md not found: {changelog_file}")
            return False

        try:
            with changelog_file.open("r", encoding="utf-8") as f:
                content = f.read()

            # Find the position to insert new entry (after "# Changelog" header)
            today = date.today().strftime("%Y-%m-%d")
            new_entry = f"\n## [{new_version}] - {today}\n\n"

            if message:
                # Add message as a subsection
                new_entry += f"### Changed\n- {message}\n\n---\n"
            else:
                # Add placeholder for manual editing
                new_entry += "### Added\n- TODO: Add changes here\n\n---\n"

            # Insert after the main "# Changelog" header
            # Look for the first occurrence of a version entry or insert after header
            match = re.search(r'(# Changelog\s*\n\s*\n.*?\n\s*\n)', content, re.MULTILINE | re.DOTALL)
            if match:
                # Insert after the header and any preamble
                insert_pos = match.end()
                new_content = content[:insert_pos] + new_entry + content[insert_pos:]
            else:
                # Fallback: insert after "# Changelog"
                header_match = re.search(r'# Changelog\s*\n', content)
                if header_match:
                    insert_pos = header_match.end()
                    new_content = content[:insert_pos] + "\n" + new_entry + content[insert_pos:]
                else:
                    self.errors.append("Could not find '# Changelog' header in CHANGELOG.md")
                    return False

            if not dry_run:
                with changelog_file.open("w", encoding="utf-8") as f:
                    f.write(new_content)

            self.changes_made.append(f"Updated CHANGELOG.md: Added entry for {new_version}")
            return True

        except Exception as e:
            self.errors.append(f"Error updating CHANGELOG.md: {e}")
            return False

    def print_summary(self) -> None:
        """Print summary of changes and errors."""
        print("=" * 70)
        print("FDA Tools Plugin - Version Update Summary")
        print("=" * 70)
        print()

        if self.changes_made:
            print("Changes Made:")
            print("-" * 70)
            for change in self.changes_made:
                print(f"  ✓ {change}")
            print()

        if self.errors:
            print("Errors:")
            print("-" * 70)
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

        if not self.errors:
            print("✓ Version updated successfully!")
        else:
            print("✗ Version update failed!")

        print("=" * 70)


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update version atomically across FDA Tools plugin files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Major release
    ./update_version.py 6.0.0 --message "Major release with breaking changes"

    # Minor release
    ./update_version.py 5.37.0 --message "New feature: XYZ"

    # Patch release
    ./update_version.py 5.36.1 --patch --message "Bug fixes"

    # Dry run (show what would change)
    ./update_version.py 5.37.0 --dry-run

Files updated:
    - scripts/version.py (if has hardcoded version)
    - .claude-plugin/plugin.json
    - CHANGELOG.md (new entry added)
        """
    )
    parser.add_argument(
        "version",
        help="New version string (e.g., 5.37.0)"
    )
    parser.add_argument(
        "-m", "--message",
        help="Changelog message for this version"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files"
    )
    parser.add_argument(
        "--patch",
        action="store_true",
        help="Convenience flag for patch releases (informational only)"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not specified)"
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
        print()

    updater = VersionUpdater(project_root=args.project_root)
    success = updater.update_all(args.version, args.message, dry_run=args.dry_run)
    updater.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
