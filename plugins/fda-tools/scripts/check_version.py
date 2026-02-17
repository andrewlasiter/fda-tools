#!/usr/bin/env python3
"""
Version consistency checker for FDA Tools plugin.

Validates that version strings are consistent across all project files:
- scripts/version.py (source of truth - reads from plugin.json)
- .claude-plugin/plugin.json (actual source)
- CHANGELOG.md (latest entry)
- README.md (if version mentioned)

Exit codes:
    0: All versions match
    1: Version mismatch detected
    2: File not found or parse error
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


class VersionChecker:
    """Checks version consistency across project files."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize version checker.

        Args:
            project_root: Root directory of the project. If None, auto-detect from script location.
        """
        if project_root is None:
            # Auto-detect: scripts/check_version.py -> project root
            self.project_root = Path(__file__).resolve().parent.parent
        else:
            self.project_root = Path(project_root).resolve()

        self.version_sources: Dict[str, Optional[str]] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def check_all(self) -> bool:
        """
        Check version consistency across all files.

        Returns:
            True if all versions match, False otherwise.
        """
        # Extract versions from all sources
        # Note: version.py reads from plugin.json, so we check plugin.json first
        self._check_plugin_json()
        self._check_version_py()
        self._check_changelog()
        self._check_readme()

        # Validate consistency
        return self._validate_consistency()

    def _check_version_py(self) -> None:
        """Extract version from scripts/version.py by importing it."""
        version_file = self.project_root / "scripts" / "version.py"

        if not version_file.exists():
            self.errors.append(f"Version file not found: {version_file}")
            self.version_sources["version.py"] = None
            return

        try:
            # Add parent directory to sys.path to enable import
            import sys
            scripts_dir = str(self.project_root / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            # Import the version module
            import importlib.util
            spec = importlib.util.spec_from_file_location("version", version_file)
            if spec and spec.loader:
                version_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(version_module)
                version = getattr(version_module, "PLUGIN_VERSION", None)

                if version:
                    self.version_sources["version.py"] = version
                else:
                    self.errors.append("Could not extract PLUGIN_VERSION from version.py")
                    self.version_sources["version.py"] = None
            else:
                self.errors.append("Could not load version.py module")
                self.version_sources["version.py"] = None

        except Exception as e:
            self.errors.append(f"Error reading version.py: {e}")
            self.version_sources["version.py"] = None

    def _check_plugin_json(self) -> None:
        """Extract version from .claude-plugin/plugin.json."""
        plugin_file = self.project_root / ".claude-plugin" / "plugin.json"

        if not plugin_file.exists():
            self.errors.append(f"Plugin manifest not found: {plugin_file}")
            self.version_sources["plugin.json"] = None
            return

        try:
            with plugin_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("version")
            if version and isinstance(version, str):
                self.version_sources["plugin.json"] = version.strip()
            else:
                self.errors.append("No 'version' field found in plugin.json")
                self.version_sources["plugin.json"] = None

        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in plugin.json: {e}")
            self.version_sources["plugin.json"] = None
        except Exception as e:
            self.errors.append(f"Error reading plugin.json: {e}")
            self.version_sources["plugin.json"] = None

    def _check_changelog(self) -> None:
        """Extract latest version from CHANGELOG.md."""
        changelog_file = self.project_root / "CHANGELOG.md"

        if not changelog_file.exists():
            self.warnings.append(f"CHANGELOG.md not found: {changelog_file}")
            self.version_sources["CHANGELOG.md"] = None
            return

        try:
            with changelog_file.open("r", encoding="utf-8") as f:
                content = f.read()

            # Match version headers: ## [X.Y.Z] or ## X.Y.Z
            # Look for the first occurrence after the header
            pattern = r'##\s*\[?(\d+\.\d+\.\d+)\]?'
            match = re.search(pattern, content)

            if match:
                self.version_sources["CHANGELOG.md"] = match.group(1)
            else:
                self.warnings.append("No version entry found in CHANGELOG.md")
                self.version_sources["CHANGELOG.md"] = None

        except Exception as e:
            self.errors.append(f"Error reading CHANGELOG.md: {e}")
            self.version_sources["CHANGELOG.md"] = None

    def _check_readme(self) -> None:
        """Extract version from README.md if mentioned."""
        readme_file = self.project_root / "README.md"

        if not readme_file.exists():
            self.warnings.append(f"README.md not found: {readme_file}")
            self.version_sources["README.md"] = None
            return

        try:
            with readme_file.open("r", encoding="utf-8") as f:
                content = f.read()

            # Look for version patterns in README
            # Common patterns: v5.36.0, version 5.36.0, (NEW in v5.26.0)
            patterns = [
                r'version\s+(\d+\.\d+\.\d+)',
                r'v(\d+\.\d+\.\d+)',
                r'\(NEW in v(\d+\.\d+\.\d+)\)',
            ]

            versions_found = set()
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    versions_found.add(match.group(1))

            if len(versions_found) == 0:
                # No version mentioned - this is OK
                self.version_sources["README.md"] = None
            elif len(versions_found) == 1:
                self.version_sources["README.md"] = versions_found.pop()
            else:
                # Multiple versions found - use the most recent one
                sorted_versions = sorted(versions_found, key=lambda v: list(map(int, v.split('.'))))
                self.version_sources["README.md"] = sorted_versions[-1]
                self.warnings.append(
                    f"Multiple versions found in README.md: {sorted(versions_found)}, using latest: {sorted_versions[-1]}"
                )

        except Exception as e:
            self.errors.append(f"Error reading README.md: {e}")
            self.version_sources["README.md"] = None

    def _validate_consistency(self) -> bool:
        """
        Validate that all versions match.

        Returns:
            True if consistent, False otherwise.
        """
        # Get source of truth (plugin.json, since version.py reads from it)
        truth_version = self.version_sources.get("plugin.json")

        if truth_version is None:
            self.errors.append("Cannot determine version from plugin.json (source of truth)")
            return False

        # Verify version.py matches plugin.json
        version_py = self.version_sources.get("version.py")
        if version_py and version_py != truth_version:
            self.errors.append(
                f"version.py returned '{version_py}' but plugin.json has '{truth_version}' (they should match)"
            )
            return False

        # Check all other sources against truth
        mismatches = []
        for source, version in self.version_sources.items():
            if source in ("plugin.json", "version.py"):
                continue  # Already checked
            if version is None:
                continue  # Skip files without version info
            if version != truth_version:
                mismatches.append((source, version, truth_version))

        if mismatches:
            for source, found, expected in mismatches:
                self.errors.append(
                    f"Version mismatch in {source}: found '{found}', expected '{expected}'"
                )
            return False

        return True

    def print_report(self, verbose: bool = False) -> None:
        """
        Print detailed version check report.

        Args:
            verbose: If True, show all details including successful checks.
        """
        print("=" * 70)
        print("FDA Tools Plugin - Version Consistency Report")
        print("=" * 70)
        print()

        # Show all version sources
        truth_version = self.version_sources.get("plugin.json")
        print(f"Source of Truth (plugin.json): {truth_version or 'NOT FOUND'}")
        print()

        if verbose or self.errors or self.warnings:
            print("Version Sources:")
            print("-" * 70)
            for source, version in sorted(self.version_sources.items()):
                status = "✓" if version == truth_version else "✗"
                if version is None:
                    status = "-"
                print(f"  {status} {source:20s} : {version or 'N/A'}")
            print()

        # Show errors
        if self.errors:
            print("Errors:")
            print("-" * 70)
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

        # Show warnings
        if self.warnings:
            print("Warnings:")
            print("-" * 70)
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()

        # Summary
        if not self.errors:
            print("✓ All version checks passed!")
            print(f"✓ Current version: {truth_version}")
        else:
            print("✗ Version consistency check failed!")
            print(f"  Expected version: {truth_version}")
            print(f"  Errors: {len(self.errors)}")
            print(f"  Warnings: {len(self.warnings)}")

        print("=" * 70)


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check version consistency across FDA Tools plugin files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
    0: All versions match
    1: Version mismatch detected
    2: File not found or parse error

Files checked:
    - .claude-plugin/plugin.json (source of truth)
    - scripts/version.py (should read from plugin.json)
    - CHANGELOG.md (latest entry)
    - README.md (if version mentioned)
        """
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including successful checks"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not specified)"
    )

    args = parser.parse_args()

    checker = VersionChecker(project_root=args.project_root)
    is_consistent = checker.check_all()
    checker.print_report(verbose=args.verbose)

    if not is_consistent:
        return 1
    if checker.errors:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
