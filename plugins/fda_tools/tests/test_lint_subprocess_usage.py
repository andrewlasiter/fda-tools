#!/usr/bin/env python3
"""
Tests for subprocess usage linter (FDA-129)

Verifies that the linter correctly detects prohibited subprocess patterns
and allows secure subprocess_helpers usage.

SECURITY NOTE: This test file contains code strings with os.system() calls
as test fixtures to verify the linter detects them. These are NOT executed -
they are string literals used for testing the linter's detection capabilities.
"""

import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path for import
import sys
from pathlib import Path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from lint_subprocess_usage import (
    lint_file,
    is_allowed_file,
    SubprocessUsageVisitor,
)


class TestSubprocessLinter:
    """Test subprocess usage linter functionality."""

    def test_detect_import_subprocess(self, tmp_path):
        """Test detection of direct subprocess import."""
        # Use non-test filename to avoid allowlist
        test_file = tmp_path / "production_code.py"
        test_file.write_text("import subprocess\n")

        violations = lint_file(test_file)
        assert len(violations) == 1
        assert violations[0][1] == "import"
        assert "subprocess_helpers" in violations[0][2]

    def test_detect_from_subprocess_import(self, tmp_path):
        """Test detection of from subprocess import."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text("from subprocess import run\n")

        violations = lint_file(test_file)
        assert len(violations) == 1
        assert violations[0][1] == "import"

    def test_detect_subprocess_run(self, tmp_path):
        """Test detection of subprocess.run() call."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text(
            """
import subprocess
result = subprocess.run(['ls', '-l'])
"""
        )

        violations = lint_file(test_file)
        # Should have both import violation and call violation
        assert len(violations) >= 2
        call_violations = [v for v in violations if v[1] == "call"]
        assert len(call_violations) == 1
        assert "subprocess.run()" in call_violations[0][2]

    def test_detect_subprocess_popen(self, tmp_path):
        """Test detection of subprocess.Popen() call."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text(
            """
import subprocess
process = subprocess.Popen(['cat'])
"""
        )

        violations = lint_file(test_file)
        call_violations = [v for v in violations if v[1] == "call"]
        assert len(call_violations) == 1
        assert "subprocess.Popen()" in call_violations[0][2]

    def test_detect_shell_true(self, tmp_path):
        """Test detection of shell=True parameter."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text(
            """
import subprocess
result = subprocess.run(['ls'], shell=True)
"""
        )

        violations = lint_file(test_file)
        shell_violations = [v for v in violations if v[1] == "shell"]
        assert len(shell_violations) == 1
        assert "shell=True" in shell_violations[0][2]

    def test_detect_os_system(self, tmp_path):
        """Test detection of os.system() call.

        SECURITY NOTE: This test writes a string containing os.system() to a temp
        file to verify the linter detects it. The os.system() call is NOT executed.
        """
        test_file = tmp_path / "production_code.py"
        # NOTE: This string contains os.system() for testing detection only
        test_file.write_text(
            """
import os
os.system('ls -l')
"""
        )

        violations = lint_file(test_file)
        call_violations = [v for v in violations if v[1] == "call"]
        assert len(call_violations) == 1
        assert "os.system()" in call_violations[0][2]

    def test_allow_subprocess_helpers_usage(self, tmp_path):
        """Test that subprocess_helpers usage is allowed."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text(
            """
from fda_tools.lib.subprocess_helpers import run_command

result = run_command(['ls', '-l'])
"""
        )

        violations = lint_file(test_file)
        assert len(violations) == 0

    def test_allow_subprocess_helpers_module(self, tmp_path):
        """Test that subprocess_helpers.py itself is allowed."""
        # Create file with allowed name
        test_file = tmp_path / "subprocess_helpers.py"
        test_file.write_text(
            """
import subprocess  # Allowed in this module

def run_command(cmd):
    return subprocess.run(cmd)
"""
        )

        # Should be allowed due to filename
        violations = lint_file(test_file)
        assert len(violations) == 0

    def test_allow_test_files(self, tmp_path):
        """Test that test files are allowed to use subprocess."""
        test_file = tmp_path / "test_something.py"
        test_file.write_text(
            """
import subprocess  # Allowed in test files

def test_subprocess():
    result = subprocess.run(['echo', 'test'])
    assert result.returncode == 0
"""
        )

        violations = lint_file(test_file)
        assert len(violations) == 0

    def test_is_allowed_file_subprocess_helpers(self):
        """Test allowlist checking for subprocess_helpers.py."""
        assert is_allowed_file(Path("lib/subprocess_helpers.py"))
        assert is_allowed_file(Path("subprocess_utils.py"))

    def test_is_allowed_file_test_pattern(self):
        """Test allowlist checking for test files."""
        assert is_allowed_file(Path("test_foo.py"))
        assert is_allowed_file(Path("foo_test.py"))
        assert is_allowed_file(Path("tests/test_bar.py"))

    def test_is_allowed_file_linter(self):
        """Test that the linter itself is allowed."""
        assert is_allowed_file(Path("scripts/lint_subprocess_usage.py"))

    def test_is_not_allowed_file_regular(self):
        """Test that regular files are not allowed."""
        assert not is_allowed_file(Path("lib/ecopy_exporter.py"))
        assert not is_allowed_file(Path("scripts/run_audit.py"))

    def test_multiple_violations_same_file(self, tmp_path):
        """Test detection of multiple violations in same file."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text(
            """
import subprocess
import os

result1 = subprocess.run(['ls'])
result2 = subprocess.Popen(['cat'])
os.system('echo test')
subprocess.call(['pwd'])
"""
        )

        violations = lint_file(test_file)
        # Should detect: import subprocess, 3 subprocess calls, 1 os.system
        assert len(violations) >= 5

    def test_syntax_error_handling(self, tmp_path):
        """Test graceful handling of files with syntax errors."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text("import subprocess\nif True\n  print('bad')")

        # Should not raise exception, just return empty violations
        violations = lint_file(test_file)
        assert violations == []

    def test_file_not_found_handling(self, tmp_path):
        """Test graceful handling of missing files."""
        test_file = tmp_path / "nonexistent.py"

        # Should not raise exception
        violations = lint_file(test_file)
        assert violations == []

    def test_visitor_line_numbers(self, tmp_path):
        """Test that violations include correct line numbers."""
        test_file = tmp_path / "production_code.py"
        test_file.write_text(
            """# Line 1
# Line 2
import subprocess  # Line 3
# Line 4
result = subprocess.run(['ls'])  # Line 5
"""
        )

        violations = lint_file(test_file)

        # Import violation should be on line 3
        import_violations = [v for v in violations if v[1] == "import"]
        assert len(import_violations) == 1
        assert import_violations[0][0] == 3

        # Call violation should be on line 5
        call_violations = [v for v in violations if v[1] == "call"]
        assert len(call_violations) == 1
        assert call_violations[0][0] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
