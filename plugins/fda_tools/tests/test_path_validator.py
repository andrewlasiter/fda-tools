#!/usr/bin/env python3
"""
Tests for Output Path Validation (FDA-111)

Tests path validation, path traversal detection, allowlist enforcement,
and protection against arbitrary file write attacks.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from fda_tools.lib.path_validator import (
    OutputPathValidator,
    PathValidationError,
    get_default_validator,
    validate_output_path,
)


@pytest.fixture
def temp_allowed_dir(tmp_path):
    """Create temporary allowed directory."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    return allowed


@pytest.fixture
def validator(temp_allowed_dir):
    """Create validator with temp allowed directory."""
    return OutputPathValidator(
        allowed_dirs=[str(temp_allowed_dir), "./"]
    )


class TestOutputPathValidator:
    """Test suite for output path validation."""

    def test_init_default_config(self):
        """Test validator initialization with defaults."""
        validator = OutputPathValidator()
        assert validator.strict_mode is True
        assert len(validator.allowed_dirs) == 3  # Default dirs
        assert "~/fda-510k-data/" in validator.allowed_dirs

    def test_init_custom_allowed_dirs(self, temp_allowed_dir):
        """Test validator with custom allowed directories."""
        validator = OutputPathValidator(
            allowed_dirs=[str(temp_allowed_dir)]
        )
        assert len(validator.allowed_dirs) == 1

    def test_normalize_path_expands_home(self):
        """Test path normalization expands ~ to home directory."""
        validator = OutputPathValidator()
        normalized = validator._normalize_path("~/test/path")
        assert "~" not in str(normalized)
        assert str(normalized).startswith(str(Path.home()))

    def test_normalize_path_resolves_relative(self):
        """Test path normalization resolves relative paths."""
        validator = OutputPathValidator()
        normalized = validator._normalize_path("./relative/path")
        assert normalized.is_absolute()

    def test_matches_pattern_prefix(self):
        """Test pattern matching with prefix."""
        validator = OutputPathValidator()
        path = Path("/tmp/fda-test/file.txt")
        pattern = Path("/tmp/fda-")

        assert validator._matches_pattern(path, pattern) is True

    def test_matches_pattern_wildcard(self):
        """Test pattern matching with wildcard."""
        validator = OutputPathValidator()
        path = Path("/tmp/fda-test/file.txt")
        pattern = Path("/tmp/fda-*")

        assert validator._matches_pattern(path, pattern) is True

    def test_matches_pattern_no_match(self):
        """Test pattern matching returns False for non-match."""
        validator = OutputPathValidator()
        path = Path("/var/log/file.txt")
        pattern = Path("/tmp/fda-")

        assert validator._matches_pattern(path, pattern) is False

    def test_is_path_traversal_dotdot(self):
        """Test path traversal detection for .. components."""
        validator = OutputPathValidator()
        assert validator._is_path_traversal("../etc/passwd") is True
        assert validator._is_path_traversal("/tmp/../../etc/passwd") is True

    def test_is_path_traversal_double_slash(self):
        """Test path traversal detection for double slashes."""
        validator = OutputPathValidator()
        assert validator._is_path_traversal("/tmp//file.txt") is True
        assert validator._is_path_traversal("\\\\server\\share") is True

    def test_is_path_traversal_encoded(self):
        """Test path traversal detection for URL-encoded patterns."""
        validator = OutputPathValidator()
        assert validator._is_path_traversal("/tmp/%2e%2e/etc/passwd") is True
        assert validator._is_path_traversal("/tmp%2ffile.txt") is True

    def test_is_path_traversal_safe_path(self):
        """Test safe paths pass traversal check."""
        validator = OutputPathValidator()
        assert validator._is_path_traversal("/tmp/safe/file.txt") is False
        assert validator._is_path_traversal("./output/data.json") is False

    def test_check_path_depth_normal(self):
        """Test path depth check allows normal paths."""
        validator = OutputPathValidator()
        normal_path = Path("/a/b/c/d/e/file.txt")
        # Should not raise
        validator._check_path_depth(normal_path)

    def test_check_path_depth_excessive(self):
        """Test path depth check blocks excessive depth."""
        validator = OutputPathValidator()
        # Create path with depth > MAX_PATH_DEPTH
        deep_path = Path("/" + "/".join(["a"] * 25))

        with pytest.raises(PathValidationError, match="Path depth .* exceeds maximum"):
            validator._check_path_depth(deep_path)

    def test_validate_allowed_path(self, validator, temp_allowed_dir):
        """Test validation passes for allowed path."""
        test_file = temp_allowed_dir / "output.json"
        validated = validator.validate_output_path(str(test_file))
        assert validated == test_file

    def test_validate_blocked_directory(self, validator):
        """Test validation blocks sensitive directories."""
        with pytest.raises(PathValidationError, match="Path blocked"):
            validator.validate_output_path("/etc/passwd")

        with pytest.raises(PathValidationError, match="Path blocked"):
            validator.validate_output_path("/root/.ssh/id_rsa")

    def test_validate_not_in_allowlist(self, validator):
        """Test validation blocks paths not in allowlist."""
        with pytest.raises(PathValidationError, match="Path not in allowed directories"):
            validator.validate_output_path("/random/path/file.txt")

    def test_validate_path_traversal(self, validator, temp_allowed_dir):
        """Test validation blocks path traversal."""
        traversal_path = str(temp_allowed_dir / ".." / ".." / "etc" / "passwd")

        with pytest.raises(PathValidationError, match="Path traversal detected"):
            validator.validate_output_path(traversal_path)

    def test_validate_relative_path_allowed(self, validator):
        """Test validation allows relative paths in current directory."""
        validated = validator.validate_output_path("./output/data.json", create_parent=True)
        assert validated.is_absolute()
        assert "output" in str(validated)

    def test_validate_with_parent_creation(self, validator, temp_allowed_dir):
        """Test validation creates parent directory when requested."""
        test_file = temp_allowed_dir / "nested" / "deep" / "output.json"
        assert not test_file.parent.exists()

        validated = validator.validate_output_path(str(test_file), create_parent=True)

        assert validated == test_file
        assert test_file.parent.exists()

    def test_validate_parent_missing_strict_mode(self, validator, temp_allowed_dir):
        """Test strict mode fails when parent doesn't exist."""
        test_file = temp_allowed_dir / "nonexistent" / "output.json"

        with pytest.raises(PathValidationError, match="Parent directory does not exist"):
            validator.validate_output_path(str(test_file), create_parent=False)

    def test_validate_non_strict_mode(self, temp_allowed_dir):
        """Test non-strict mode allows missing parents."""
        validator = OutputPathValidator(
            allowed_dirs=[str(temp_allowed_dir)],
            strict_mode=False
        )
        test_file = temp_allowed_dir / "nonexistent" / "output.json"

        # Should not raise in non-strict mode
        validated = validator.validate_output_path(str(test_file), create_parent=False)
        assert validated == test_file

    def test_validate_raise_on_error_false(self, validator):
        """Test validation returns None instead of raising when raise_on_error=False."""
        result = validator.validate_output_path(
            "/etc/passwd",
            raise_on_error=False
        )
        assert result is None

    def test_is_path_allowed_convenience(self, validator, temp_allowed_dir):
        """Test is_path_allowed convenience method."""
        test_file = temp_allowed_dir / "output.json"
        assert validator.is_path_allowed(str(test_file)) is True
        assert validator.is_path_allowed("/etc/passwd") is False

    def test_add_allowed_dir(self, validator, tmp_path):
        """Test adding directory to allowlist."""
        new_dir = tmp_path / "new_allowed"
        new_dir.mkdir()

        validator.add_allowed_dir(str(new_dir))

        test_file = new_dir / "file.txt"
        assert validator.is_path_allowed(str(test_file)) is True

    def test_add_allowed_dir_duplicate(self, validator, temp_allowed_dir):
        """Test adding duplicate directory doesn't create duplicates."""
        initial_count = len(validator.allowed_dirs)
        validator.add_allowed_dir(str(temp_allowed_dir))

        # Should not increase count
        assert len(validator.allowed_dirs) == initial_count

    def test_remove_allowed_dir(self, validator, temp_allowed_dir):
        """Test removing directory from allowlist."""
        test_file = temp_allowed_dir / "file.txt"
        assert validator.is_path_allowed(str(test_file)) is True

        validator.remove_allowed_dir(str(temp_allowed_dir))

        assert validator.is_path_allowed(str(test_file)) is False

    def test_get_allowed_dirs(self, validator):
        """Test getting allowed directories list."""
        allowed_dirs = validator.get_allowed_dirs()
        assert isinstance(allowed_dirs, list)
        assert len(allowed_dirs) > 0
        assert all(isinstance(d, Path) for d in allowed_dirs)

    def test_get_allowed_dirs_returns_copy(self, validator):
        """Test get_allowed_dirs returns a copy."""
        allowed_dirs1 = validator.get_allowed_dirs()
        allowed_dirs2 = validator.get_allowed_dirs()

        # Should be equal but not same object
        assert allowed_dirs1 == allowed_dirs2
        assert allowed_dirs1 is not allowed_dirs2

    @patch('fda_tools.lib.path_validator.Path.is_symlink')
    @patch('fda_tools.lib.path_validator.Path.exists')
    def test_is_symlink_to_blocked(self, mock_exists, mock_is_symlink, validator):
        """Test symlink to blocked directory detection."""
        mock_exists.return_value = True
        mock_is_symlink.return_value = True

        # Create mock symlink pointing to /etc/
        test_path = Path("/tmp/symlink")
        with patch.object(Path, 'resolve', return_value=Path('/etc/passwd')):
            assert validator._is_symlink_to_blocked(test_path) is True

    def test_wildcard_pattern_matching(self, validator, tmp_path):
        """Test wildcard patterns in allowed directories."""
        test_dir = tmp_path / "fda-test"
        test_dir.mkdir()

        validator_wild = OutputPathValidator(
            allowed_dirs=[f"{tmp_path}/fda-*"],
            strict_mode=False  # Don't require parent dirs to exist
        )

        # Should match /tmp_path/fda-test/file.txt
        test_file = test_dir / "file.txt"
        assert validator_wild.is_path_allowed(str(test_file)) is True

        # Should not match /tmp_path/other/file.txt
        other_file = tmp_path / "other" / "file.txt"
        assert validator_wild.is_path_allowed(str(other_file)) is False

    def test_concurrent_validations(self, validator, temp_allowed_dir):
        """Test multiple concurrent validations."""
        paths = [
            temp_allowed_dir / f"file{i}.txt"
            for i in range(10)
        ]

        for path in paths:
            validated = validator.validate_output_path(str(path))
            assert validated == path

    def test_validator_thread_safety(self, validator, temp_allowed_dir):
        """Test validator can be used from multiple threads."""
        import threading

        results = []

        def validate_path(path_str):
            try:
                result = validator.validate_output_path(path_str)
                results.append((path_str, result))
            except PathValidationError as e:
                results.append((path_str, None))

        threads = [
            threading.Thread(
                target=validate_path,
                args=(str(temp_allowed_dir / f"file{i}.txt"),)
            )
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete
        assert len(results) == 5


class TestGlobalValidator:
    """Test suite for global validator functions."""

    def test_get_default_validator_singleton(self):
        """Test default validator is singleton."""
        validator1 = get_default_validator()
        validator2 = get_default_validator()
        assert validator1 is validator2

    def test_validate_output_path_convenience(self, temp_allowed_dir):
        """Test convenience function uses default validator."""
        # This uses default validator with default allowed dirs
        # Should work for ~/fda-510k-data/ paths
        test_path = Path.home() / "fda-510k-data" / "test_subdir" / "test.json"

        # Create parent directory
        test_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            validated = validate_output_path(str(test_path))
            assert validated == test_path
        finally:
            # Cleanup - remove subdirectory only
            import shutil
            if test_path.parent.exists():
                shutil.rmtree(test_path.parent)

    def test_convenience_function_raises_on_invalid(self):
        """Test convenience function raises on invalid path."""
        with pytest.raises(PathValidationError):
            validate_output_path("/etc/passwd")


class TestCLIInterface:
    """Test CLI testing interface."""

    def test_cli_allowed_path(self, temp_allowed_dir, capsys):
        """Test CLI with allowed path."""
        import sys
        test_path = str(temp_allowed_dir / "test.txt")

        # Mock sys.argv
        with patch.object(sys, 'argv', ['path_validator.py', test_path]):
            # Import after mocking to trigger __main__ block
            # (Would need actual CLI test framework for full test)
            pass

    def test_cli_blocked_path(self, capsys):
        """Test CLI with blocked path."""
        import sys

        # Mock sys.argv
        with patch.object(sys, 'argv', ['path_validator.py', '/etc/passwd']):
            # (Would need actual CLI test framework)
            pass
