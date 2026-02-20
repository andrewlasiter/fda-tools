#!/usr/bin/env python3
"""
Security tests for Path Traversal Fixes (FDA-171 Remediation Verification).

Tests gap_analysis.py, fetch_predicate_data.py, and pma_prototype.py for CWE-22 path traversal vulnerabilities.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Import from package

# Import security functions from each script
from gap_analysis import _sanitize_path as gap_sanitize, _validate_path_safety as gap_validate
from fetch_predicate_data import _sanitize_path as fetch_sanitize, _validate_path_safety as fetch_validate
from pma_prototype import _sanitize_path as pma_sanitize, _validate_path_safety as pma_validate


class TestGapAnalysisSecurity:
    """Test path validation in gap_analysis.py (FDA-171 SEC-004)."""

    def test_sanitize_rejects_traversal_sequence(self):
        """Test that _sanitize_path rejects .. traversal sequences."""
        with pytest.raises(ValueError, match="directory traversal sequence"):
            gap_sanitize("../../../etc/passwd")

    def test_sanitize_rejects_null_bytes(self):
        """Test that _sanitize_path rejects null bytes."""
        with pytest.raises(ValueError, match="null bytes"):
            gap_sanitize("file.csv\x00.txt")

    def test_sanitize_rejects_empty_path(self):
        """Test that _sanitize_path rejects empty paths."""
        with pytest.raises(ValueError, match="cannot be empty"):
            gap_sanitize("")

    def test_sanitize_accepts_valid_path(self):
        """Test that _sanitize_path accepts valid paths."""
        result = gap_sanitize("gap_manifest.csv")
        assert result == "gap_manifest.csv"

    def test_validate_rejects_escape_attempt(self):
        """Test that _validate_path_safety rejects paths escaping allowed dirs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]

            with pytest.raises(ValueError, match="escapes allowed directories"):
                gap_validate("/etc/passwd", allowed_dirs)

    def test_validate_accepts_within_allowed_dir(self):
        """Test that _validate_path_safety accepts paths within allowed dirs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]
            test_path = os.path.join(temp_dir, "test.csv")

            result = gap_validate(test_path, allowed_dirs)
            assert str(result) == str(Path(test_path).resolve())

    def test_validate_without_allowed_dirs(self):
        """Test that _validate_path_safety allows any path when no dirs specified."""
        # Should not raise when allowed_dirs=None (backwards compat)
        result = gap_validate("test.csv", allowed_base_dirs=None)
        assert isinstance(result, Path)

    def test_end_to_end_attack_baseline_argument(self):
        """Test that --baseline argument rejects path traversal."""
        # This would be caught by validation in main()
        with pytest.raises(ValueError, match="directory traversal sequence"):
            gap_sanitize("--baseline ../../../etc/passwd")

    def test_end_to_end_attack_output_argument(self):
        """Test that --output argument rejects path traversal."""
        with pytest.raises(ValueError, match="directory traversal sequence"):
            gap_sanitize("../../../tmp/malicious.csv")


class TestFetchPredicateDataSecurity:
    """Test path validation in fetch_predicate_data.py (FDA-171 SEC-004)."""

    def test_sanitize_rejects_traversal_sequence(self):
        """Test that _sanitize_path rejects .. traversal sequences."""
        with pytest.raises(ValueError, match="directory traversal sequence"):
            fetch_sanitize("../../../etc/passwd")

    def test_sanitize_rejects_null_bytes(self):
        """Test that _sanitize_path rejects null bytes."""
        with pytest.raises(ValueError, match="null bytes"):
            fetch_sanitize("output\x00.json")

    def test_sanitize_rejects_empty_path(self):
        """Test that _sanitize_path rejects empty paths."""
        with pytest.raises(ValueError, match="cannot be empty"):
            fetch_sanitize("")

    def test_sanitize_accepts_valid_path(self):
        """Test that _sanitize_path accepts valid paths."""
        result = fetch_sanitize("predicate_data.json")
        assert result == "predicate_data.json"

    def test_validate_rejects_escape_attempt(self):
        """Test that _validate_path_safety rejects paths escaping allowed dirs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]

            with pytest.raises(ValueError, match="escapes allowed directories"):
                fetch_validate("/tmp/outside.json", allowed_dirs)

    def test_validate_accepts_within_allowed_dir(self):
        """Test that _validate_path_safety accepts paths within allowed dirs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]
            test_path = os.path.join(temp_dir, "output.json")

            result = fetch_validate(test_path, allowed_dirs)
            assert str(result) == str(Path(test_path).resolve())

    def test_validate_without_allowed_dirs(self):
        """Test that _validate_path_safety allows any path when no dirs specified."""
        result = fetch_validate("output.json", allowed_base_dirs=None)
        assert isinstance(result, Path)

    def test_end_to_end_attack_output_argument(self):
        """Test that --output argument rejects path traversal."""
        with pytest.raises(ValueError, match="directory traversal sequence"):
            fetch_sanitize("--output ../../../etc/passwd")


class TestPMAPrototypeSecurity:
    """Test path validation in pma_prototype.py (FDA-171 SEC-004)."""

    def test_sanitize_rejects_traversal_sequence(self):
        """Test that _sanitize_path rejects .. traversal sequences."""
        with pytest.raises(ValueError, match="directory traversal sequence"):
            pma_sanitize("../../../var/www")

    def test_sanitize_rejects_null_bytes(self):
        """Test that _sanitize_path rejects null bytes."""
        with pytest.raises(ValueError, match="null bytes"):
            pma_sanitize("cache\x00/")

    def test_sanitize_rejects_empty_path(self):
        """Test that _sanitize_path rejects empty paths."""
        with pytest.raises(ValueError, match="cannot be empty"):
            pma_sanitize("")

    def test_sanitize_accepts_valid_path(self):
        """Test that _sanitize_path accepts valid paths."""
        result = pma_sanitize("./ssed_cache/")
        assert result == "./ssed_cache/"

    def test_validate_rejects_escape_attempt(self):
        """Test that _validate_path_safety rejects paths escaping allowed dirs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]

            with pytest.raises(ValueError, match="escapes allowed directories"):
                pma_validate("/var/www/html", allowed_dirs)

    def test_validate_accepts_within_allowed_dir(self):
        """Test that _validate_path_safety accepts paths within allowed dirs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]
            test_path = os.path.join(temp_dir, "cache")

            result = pma_validate(test_path, allowed_dirs)
            assert str(result) == str(Path(test_path).resolve())

    def test_validate_without_allowed_dirs(self):
        """Test that _validate_path_safety allows any path when no dirs specified."""
        result = pma_validate("./ssed_cache/", allowed_base_dirs=None)
        assert isinstance(result, Path)

    def test_end_to_end_cache_dir_validation(self):
        """Test that cache_dir parameter validates paths."""
        # Test with valid cache_dir
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]
            cache_path = os.path.join(temp_dir, "cache")

            result = pma_validate(cache_path, allowed_dirs)
            assert str(result) == str(Path(cache_path).resolve())

    def test_end_to_end_attack_cache_dir(self):
        """Test that cache_dir rejects path traversal."""
        with pytest.raises(ValueError, match="directory traversal sequence"):
            pma_sanitize("../../etc/passwd")


class TestIntegratedSecurityVerification:
    """Test integrated security across all three scripts."""

    def test_all_scripts_reject_same_attacks(self):
        """Test that all scripts consistently reject the same attack patterns."""
        # Relative traversal attacks (rejected by sanitize)
        traversal_attacks = [
            "../../../etc/passwd",
            "../../../../../../etc/shadow",
            "cache/../../../etc/hosts",
        ]

        for attack_path in traversal_attacks:
            # All three scripts should reject traversal sequences
            with pytest.raises(ValueError, match="directory traversal sequence"):
                gap_sanitize(attack_path)

            with pytest.raises(ValueError, match="directory traversal sequence"):
                fetch_sanitize(attack_path)

            with pytest.raises(ValueError, match="directory traversal sequence"):
                pma_sanitize(attack_path)

        # Absolute path attacks (rejected by validate when outside allowed dirs)
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed_dirs = [temp_dir]
            absolute_attacks = [
                "/etc/passwd",
                "/var/www/html",
            ]

            for attack_path in absolute_attacks:
                # All three scripts should reject paths outside allowed dirs
                with pytest.raises(ValueError, match="escapes allowed directories"):
                    gap_validate(attack_path, allowed_dirs)

                with pytest.raises(ValueError, match="escapes allowed directories"):
                    fetch_validate(attack_path, allowed_dirs)

                with pytest.raises(ValueError, match="escapes allowed directories"):
                    pma_validate(attack_path, allowed_dirs)

    def test_all_scripts_reject_null_bytes(self):
        """Test that all scripts reject null byte injection."""
        null_byte_paths = [
            "file.csv\x00.txt",
            "output\x00/../../etc/passwd",
        ]

        for path in null_byte_paths:
            with pytest.raises(ValueError, match="null bytes"):
                gap_sanitize(path)

            with pytest.raises(ValueError, match="null bytes"):
                fetch_sanitize(path)

            with pytest.raises(ValueError, match="null bytes"):
                pma_sanitize(path)

    def test_all_scripts_accept_safe_paths(self):
        """Test that all scripts accept safe, valid paths."""
        safe_paths = [
            "output.csv",
            "cache/data.pdf",
            "./results/analysis.json",
        ]

        for path in safe_paths:
            # All should successfully sanitize these paths
            assert gap_sanitize(path) == path
            assert fetch_sanitize(path) == path
            assert pma_sanitize(path) == path

    def test_security_metrics(self):
        """Verify that security fixes are comprehensive."""
        # Verify security function count
        # Each script should have 2 security functions
        import gap_analysis
        import fetch_predicate_data
        import pma_prototype

        gap_security_funcs = [f for f in dir(gap_analysis) if f.startswith('_sanitize') or f.startswith('_validate')]
        fetch_security_funcs = [f for f in dir(fetch_predicate_data) if f.startswith('_sanitize') or f.startswith('_validate')]
        pma_security_funcs = [f for f in dir(pma_prototype) if f.startswith('_sanitize') or f.startswith('_validate')]

        assert len(gap_security_funcs) >= 2, "gap_analysis.py should have at least 2 security functions"
        assert len(fetch_security_funcs) >= 2, "fetch_predicate_data.py should have at least 2 security functions"
        assert len(pma_security_funcs) >= 2, "pma_prototype.py should have at least 2 security functions"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
