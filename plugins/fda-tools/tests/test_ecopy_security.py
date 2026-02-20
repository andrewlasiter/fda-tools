#!/usr/bin/env python3
"""
Security tests for eCopy Exporter (FDA-198 Remediation Verification).

Tests path traversal prevention, input sanitization, and file size validation.
"""

import pytest
from pathlib import Path
import tempfile
import os

# Import from package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.ecopy_exporter import eCopyExporter


class TestPathSanitization:
    """Test path sanitization to prevent traversal attacks (FDA-198 CRITICAL-1)."""

    def setup_method(self):
        """Create temporary project directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "project"
        self.project_path.mkdir()
        self.exporter = eCopyExporter(str(self.project_path))

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_path_rejects_parent_references(self):
        """Test that parent directory references are rejected."""
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            self.exporter._sanitize_path("../../etc/passwd")

    def test_sanitize_path_rejects_absolute_paths(self):
        """Test that absolute paths are rejected."""
        with pytest.raises(ValueError, match="Absolute paths not allowed"):
            self.exporter._sanitize_path("/etc/passwd")

    def test_sanitize_path_rejects_null_bytes(self):
        """Test that null bytes are rejected (path truncation attack)."""
        with pytest.raises(ValueError, match="Null bytes not allowed"):
            self.exporter._sanitize_path("file\x00.txt")

    def test_sanitize_path_rejects_directory_separators_in_filenames(self):
        """Test that directory separators are rejected in filenames."""
        with pytest.raises(ValueError, match="Directory separators not allowed"):
            self.exporter._sanitize_path("subdir/file.txt", context="file")

    def test_sanitize_path_accepts_valid_filename(self):
        """Test that valid filenames are accepted."""
        result = self.exporter._sanitize_path("draft_cover-letter.md", context="file")
        assert result == "draft_cover-letter.md"

    def test_validate_path_in_project_rejects_escaping(self):
        """Test that paths escaping project directory are rejected."""
        malicious_path = self.project_path / ".." / ".." / "etc" / "passwd"
        with pytest.raises(ValueError, match="Path escapes project directory"):
            self.exporter._validate_path_in_project(malicious_path)

    def test_validate_path_in_project_accepts_valid_path(self):
        """Test that valid paths within project are accepted."""
        valid_path = self.project_path / "drafts" / "file.md"
        result = self.exporter._validate_path_in_project(valid_path)
        # Should resolve to absolute path within project
        assert str(result).startswith(str(self.project_path.resolve()))


class TestFileSizeValidation:
    """Test file size validation to prevent DoS attacks (FDA-198 HIGH-4)."""

    def setup_method(self):
        """Create temporary project directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "project"
        self.project_path.mkdir()
        self.exporter = eCopyExporter(str(self.project_path))

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_file_size_rejects_oversized_file(self):
        """Test that files exceeding size limit are rejected."""
        # Create a 101 MB file (exceeds 100 MB limit)
        large_file = self.project_path / "large.pdf"
        with open(large_file, 'wb') as f:
            f.write(b'\x00' * (101 * 1024 * 1024))  # 101 MB of zeros

        with pytest.raises(ValueError, match="File size .* exceeds limit"):
            self.exporter._validate_file_size(large_file)

    def test_validate_file_size_accepts_small_file(self):
        """Test that files within size limit are accepted."""
        # Create a 1 MB file (well under 100 MB limit)
        small_file = self.project_path / "small.pdf"
        with open(small_file, 'wb') as f:
            f.write(b'\x00' * (1 * 1024 * 1024))  # 1 MB

        # Should not raise exception
        self.exporter._validate_file_size(small_file)

    def test_validate_file_size_skips_nonexistent_file(self):
        """Test that validation skips files that don't exist yet."""
        nonexistent = self.project_path / "nonexistent.pdf"
        # Should not raise exception
        self.exporter._validate_file_size(nonexistent)


class TestSectionNameSanitization:
    """Test section name sanitization (FDA-198 HIGH-3)."""

    def setup_method(self):
        """Create temporary project directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "project"
        self.project_path.mkdir()
        self.exporter = eCopyExporter(str(self.project_path))

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_section_name_rejects_special_chars(self):
        """Test that section names with special characters are rejected."""
        with pytest.raises(ValueError, match="invalid characters"):
            self.exporter._sanitize_section_name("Section; DROP TABLE")

    def test_sanitize_section_name_rejects_long_names(self):
        """Test that excessively long section names are rejected."""
        long_name = "A" * 65  # 65 characters (limit is 64)
        with pytest.raises(ValueError, match="too long"):
            self.exporter._sanitize_section_name(long_name)

    def test_sanitize_section_name_accepts_valid_name(self):
        """Test that valid section names are accepted."""
        valid_names = [
            "Cover Letter",
            "Administrative",
            "510k Summary",
            "Device-Description",
            "EMC-123",
        ]
        for name in valid_names:
            result = self.exporter._sanitize_section_name(name)
            assert result == name


class TestIntegratedSecurity:
    """Test integrated security in export workflow."""

    def setup_method(self):
        """Create temporary project with malicious configuration."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "project"
        self.project_path.mkdir()
        (self.project_path / "drafts").mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_handles_malicious_draft_file_path(self):
        """Test that export() gracefully handles malicious draft file paths."""
        # Create exporter with malicious configuration
        exporter = eCopyExporter(str(self.project_path))

        # Add malicious draft_file to section 01 (keep other sections intact)
        exporter.ECOPY_SECTIONS["01"]["draft_file"] = "../../../etc/passwd"

        # Export should handle gracefully without crashing
        result = exporter.export()

        # Should report the security violation as a conversion error
        assert "Security validation failed" in str(result.get("conversion_errors", []))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
