#!/usr/bin/env python3
"""
Tests for version consistency checker and updater.

Tests both check_version.py and update_version.py functionality.
"""

import json
import re
import sys
import tempfile
from pathlib import Path

import pytest


# Add scripts directory to path for imports
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from check_version import VersionChecker
from update_version import VersionUpdater


class TestVersionChecker:
    """Tests for VersionChecker class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure for testing."""
        # Create directory structure
        (tmp_path / "scripts").mkdir()
        (tmp_path / ".claude-plugin").mkdir()

        # Create plugin.json with version
        plugin_data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin"
        }
        with (tmp_path / ".claude-plugin" / "plugin.json").open("w") as f:
            json.dump(plugin_data, f, indent=2)

        # Create version.py that reads from plugin.json
        version_py_content = '''
import json
from pathlib import Path

def get_plugin_version(default="0.0.0"):
    plugin_json = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        with plugin_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except Exception as e:
        print(f"Warning: Could not read plugin version: {e}")
    return default

PLUGIN_VERSION = get_plugin_version()
'''
        with (tmp_path / "scripts" / "version.py").open("w") as f:
            f.write(version_py_content)

        # Create CHANGELOG.md
        changelog_content = """# Changelog

All notable changes will be documented in this file.

## [1.0.0] - 2024-01-01

### Added
- Initial release
"""
        with (tmp_path / "CHANGELOG.md").open("w") as f:
            f.write(changelog_content)

        # Create README.md
        readme_content = """# Test Plugin

Version 1.0.0 released!

(NEW in v1.0.0) - Initial features
"""
        with (tmp_path / "README.md").open("w") as f:
            f.write(readme_content)

        return tmp_path

    def test_checker_all_versions_match(self, temp_project):
        """Test checker when all versions are consistent."""
        checker = VersionChecker(project_root=temp_project)
        result = checker.check_all()

        assert result is True, "All versions should match"
        assert len(checker.errors) == 0, "Should have no errors"
        assert checker.version_sources["plugin.json"] == "1.0.0"
        assert checker.version_sources["version.py"] == "1.0.0"
        assert checker.version_sources["CHANGELOG.md"] == "1.0.0"
        assert checker.version_sources["README.md"] == "1.0.0"

    def test_checker_detects_plugin_json_mismatch(self, temp_project):
        """Test checker detects mismatch in plugin.json."""
        # Update plugin.json to different version
        with (temp_project / ".claude-plugin" / "plugin.json").open("r") as f:
            data = json.load(f)
        data["version"] = "2.0.0"
        with (temp_project / ".claude-plugin" / "plugin.json").open("w") as f:
            json.dump(data, f, indent=2)

        checker = VersionChecker(project_root=temp_project)
        result = checker.check_all()

        assert result is False, "Should detect version mismatch"
        assert len(checker.errors) > 0, "Should have errors"
        # Check that version.py now returns 2.0.0 (since it reads from plugin.json)
        assert checker.version_sources["plugin.json"] == "2.0.0"
        assert checker.version_sources["version.py"] == "2.0.0"

    def test_checker_detects_changelog_mismatch(self, temp_project):
        """Test checker detects mismatch in CHANGELOG.md."""
        # Update CHANGELOG to different version
        changelog_content = """# Changelog

## [2.0.0] - 2024-02-01

### Changed
- Updated version

## [1.0.0] - 2024-01-01

### Added
- Initial release
"""
        with (temp_project / "CHANGELOG.md").open("w") as f:
            f.write(changelog_content)

        checker = VersionChecker(project_root=temp_project)
        result = checker.check_all()

        assert result is False, "Should detect CHANGELOG mismatch"
        assert any("CHANGELOG.md" in error for error in checker.errors)
        assert checker.version_sources["CHANGELOG.md"] == "2.0.0"
        assert checker.version_sources["plugin.json"] == "1.0.0"

    def test_checker_detects_readme_mismatch(self, temp_project):
        """Test checker detects mismatch in README.md."""
        # Update README to different version
        readme_content = """# Test Plugin

Version 2.0.0 released!

(NEW in v2.0.0) - New features
"""
        with (temp_project / "README.md").open("w") as f:
            f.write(readme_content)

        checker = VersionChecker(project_root=temp_project)
        result = checker.check_all()

        assert result is False, "Should detect README mismatch"
        assert any("README.md" in error for error in checker.errors)
        assert checker.version_sources["README.md"] == "2.0.0"
        assert checker.version_sources["plugin.json"] == "1.0.0"

    def test_checker_handles_missing_files(self, temp_project):
        """Test checker handles missing files gracefully."""
        # Remove CHANGELOG and README
        (temp_project / "CHANGELOG.md").unlink()
        (temp_project / "README.md").unlink()

        checker = VersionChecker(project_root=temp_project)
        result = checker.check_all()

        # Should still pass if core files (plugin.json, version.py) are consistent
        assert result is True, "Should pass with missing optional files"
        assert len(checker.warnings) >= 2, "Should warn about missing files"

    def test_checker_invalid_version_format(self, temp_project):
        """Test checker with invalid version format."""
        # Update plugin.json to invalid version
        with (temp_project / ".claude-plugin" / "plugin.json").open("r") as f:
            data = json.load(f)
        data["version"] = "invalid"
        with (temp_project / ".claude-plugin" / "plugin.json").open("w") as f:
            json.dump(data, f, indent=2)

        checker = VersionChecker(project_root=temp_project)
        result = checker.check_all()

        # Should detect mismatch (invalid != 1.0.0)
        assert result is False


class TestVersionUpdater:
    """Tests for VersionUpdater class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure for testing."""
        # Create directory structure
        (tmp_path / "scripts").mkdir()
        (tmp_path / ".claude-plugin").mkdir()

        # Create plugin.json
        plugin_data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin"
        }
        with (tmp_path / ".claude-plugin" / "plugin.json").open("w") as f:
            json.dump(plugin_data, f, indent=2)

        # Create version.py
        version_py_content = '''
import json
from pathlib import Path

def get_plugin_version(default="0.0.0"):
    plugin_json = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        with plugin_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except Exception:
        pass
    return default

PLUGIN_VERSION = get_plugin_version()
'''
        with (tmp_path / "scripts" / "version.py").open("w") as f:
            f.write(version_py_content)

        # Create CHANGELOG.md
        changelog_content = """# Changelog

All notable changes will be documented in this file.

## [1.0.0] - 2024-01-01

### Added
- Initial release
"""
        with (tmp_path / "CHANGELOG.md").open("w") as f:
            f.write(changelog_content)

        return tmp_path

    def test_updater_updates_plugin_json(self, temp_project):
        """Test updater updates plugin.json correctly."""
        updater = VersionUpdater(project_root=temp_project)
        result = updater.update_all("2.0.0", dry_run=False)

        assert result is True, "Update should succeed"
        assert len(updater.errors) == 0, "Should have no errors"

        # Verify plugin.json was updated
        with (temp_project / ".claude-plugin" / "plugin.json").open("r") as f:
            data = json.load(f)
        assert data["version"] == "2.0.0"

    def test_updater_updates_changelog(self, temp_project):
        """Test updater adds new entry to CHANGELOG.md."""
        updater = VersionUpdater(project_root=temp_project)
        result = updater.update_all("2.0.0", changelog_message="New features", dry_run=False)

        assert result is True, "Update should succeed"

        # Verify CHANGELOG was updated
        with (temp_project / "CHANGELOG.md").open("r") as f:
            content = f.read()

        assert "## [2.0.0]" in content
        assert "New features" in content
        # Old version should still be there
        assert "## [1.0.0]" in content

    def test_updater_dry_run(self, temp_project):
        """Test updater dry run doesn't modify files."""
        updater = VersionUpdater(project_root=temp_project)
        result = updater.update_all("2.0.0", dry_run=True)

        assert result is True, "Dry run should succeed"

        # Verify plugin.json was NOT updated
        with (temp_project / ".claude-plugin" / "plugin.json").open("r") as f:
            data = json.load(f)
        assert data["version"] == "1.0.0", "Dry run should not modify files"

    def test_updater_rejects_invalid_version(self, temp_project):
        """Test updater rejects invalid version format."""
        updater = VersionUpdater(project_root=temp_project)
        result = updater.update_all("invalid", dry_run=False)

        assert result is False, "Should reject invalid version"
        assert len(updater.errors) > 0, "Should have errors"

    def test_updater_atomic_update(self, temp_project):
        """Test that updater updates all files atomically."""
        updater = VersionUpdater(project_root=temp_project)
        result = updater.update_all("3.0.0", changelog_message="Major release", dry_run=False)

        assert result is True, "Update should succeed"

        # Verify all files have the new version
        with (temp_project / ".claude-plugin" / "plugin.json").open("r") as f:
            data = json.load(f)
        assert data["version"] == "3.0.0"

        with (temp_project / "CHANGELOG.md").open("r") as f:
            content = f.read()
        assert "## [3.0.0]" in content


class TestVersionConsistency:
    """Integration tests for version consistency across real files."""

    def test_real_project_version_consistency(self):
        """Test version consistency in the actual project."""
        # Use the real project root
        checker = VersionChecker(project_root=PLUGIN_ROOT)
        checker.check_all()

        # Print report for debugging
        checker.print_report(verbose=True)

        # Should at least have plugin.json and version.py
        assert checker.version_sources["plugin.json"] is not None
        assert checker.version_sources["version.py"] is not None

        # version.py should match plugin.json (since it reads from it)
        if checker.version_sources["version.py"]:
            assert checker.version_sources["version.py"] == checker.version_sources["plugin.json"]

    def test_version_format_validity(self):
        """Test that current version follows semver format."""
        checker = VersionChecker(project_root=PLUGIN_ROOT)
        checker.check_all()

        version = checker.version_sources.get("plugin.json")
        assert version is not None, "Should find version in plugin.json"

        # Check semver format: X.Y.Z
        pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(pattern, version), f"Version '{version}' should follow semver (X.Y.Z)"


@pytest.mark.integration
class TestVersionWorkflow:
    """Integration tests for version update workflow."""

    def test_update_then_check_workflow(self, tmp_path):
        """Test complete workflow: update version, then check consistency."""
        # Create project
        (tmp_path / "scripts").mkdir()
        (tmp_path / ".claude-plugin").mkdir()

        plugin_data = {"name": "test", "version": "1.0.0"}
        with (tmp_path / ".claude-plugin" / "plugin.json").open("w") as f:
            json.dump(plugin_data, f)

        version_py = '''
import json
from pathlib import Path

def get_plugin_version(default="0.0.0"):
    plugin_json = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    with plugin_json.open("r") as f:
        data = json.load(f)
    return data.get("version", default)

PLUGIN_VERSION = get_plugin_version()
'''
        with (tmp_path / "scripts" / "version.py").open("w") as f:
            f.write(version_py)

        changelog = """# Changelog

## [1.0.0] - 2024-01-01
- Initial
"""
        with (tmp_path / "CHANGELOG.md").open("w") as f:
            f.write(changelog)

        # Step 1: Update version
        updater = VersionUpdater(project_root=tmp_path)
        update_result = updater.update_all("2.0.0", changelog_message="New release")

        assert update_result is True, "Update should succeed"

        # Step 2: Check consistency
        checker = VersionChecker(project_root=tmp_path)
        check_result = checker.check_all()

        assert check_result is True, "All versions should be consistent after update"
        assert checker.version_sources["plugin.json"] == "2.0.0"
        assert checker.version_sources["version.py"] == "2.0.0"
        assert checker.version_sources["CHANGELOG.md"] == "2.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
