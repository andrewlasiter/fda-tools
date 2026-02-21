"""Tests for subprocess allowlisting enforcement (FDA-129).

Coverage:
- DEFAULT_ALLOWLIST contains required infrastructure commands
- run_command() accepts allowlisted commands
- run_command() rejects commands not in allowlist (SubprocessAllowlistError)
- run_command() accepts input= parameter for stdin piping
- lint_subprocess_usage detects direct subprocess.run() calls
- lint_subprocess_usage passes backup_manager.py, security_audit.py, etc.
- lint_subprocess_usage skips test files and allowed modules
"""

import ast
import sys
import tempfile
from pathlib import Path

import pytest

from fda_tools.lib.subprocess_helpers import (
    DEFAULT_ALLOWLIST,
    SubprocessAllowlistError,
    run_command,
)
from fda_tools.scripts.lint_subprocess_usage import (
    ALLOWED_MODULES,
    is_allowed_file,
    lint_file,
)


# ---------------------------------------------------------------------------
# DEFAULT_ALLOWLIST completeness (FDA-129)
# ---------------------------------------------------------------------------


class TestDefaultAllowlist:
    """DEFAULT_ALLOWLIST must include all required infrastructure commands."""

    def test_contains_docker(self):
        assert "docker" in DEFAULT_ALLOWLIST

    def test_contains_docker_compose(self):
        assert "docker-compose" in DEFAULT_ALLOWLIST

    def test_contains_gpg(self):
        assert "gpg" in DEFAULT_ALLOWLIST

    def test_contains_aws(self):
        assert "aws" in DEFAULT_ALLOWLIST

    def test_contains_psql(self):
        assert "psql" in DEFAULT_ALLOWLIST

    def test_contains_createdb(self):
        assert "createdb" in DEFAULT_ALLOWLIST

    def test_contains_dropdb(self):
        assert "dropdb" in DEFAULT_ALLOWLIST

    def test_contains_pg_dump(self):
        assert "pg_dump" in DEFAULT_ALLOWLIST

    def test_contains_pg_restore(self):
        assert "pg_restore" in DEFAULT_ALLOWLIST

    def test_contains_python3(self):
        assert "python3" in DEFAULT_ALLOWLIST

    def test_contains_git(self):
        assert "git" in DEFAULT_ALLOWLIST


# ---------------------------------------------------------------------------
# run_command allowlist enforcement
# ---------------------------------------------------------------------------


class TestRunCommandAllowlist:
    """Allowlist validation in run_command()."""

    def test_allowed_command_executes(self):
        result = run_command(
            ["python3", "-c", "print('ok')"],
            allowlist=["python3"],
        )
        assert result.returncode == 0

    def test_blocked_command_raises(self):
        with pytest.raises(SubprocessAllowlistError):
            run_command(
                ["curl", "http://example.com"],
                allowlist=["python3"],
            )

    def test_error_message_names_blocked_command(self):
        with pytest.raises(SubprocessAllowlistError, match="curl"):
            run_command(["curl", "--help"], allowlist=["python3"])

    def test_empty_allowlist_skips_check(self):
        """Empty list [] is falsy → allowlist check is skipped (same as None)."""
        result = run_command(["python3", "-c", "pass"], allowlist=[])
        assert result.returncode == 0

    def test_none_allowlist_uses_default(self):
        """None allowlist falls back to DEFAULT_ALLOWLIST (which includes python3)."""
        result = run_command(
            ["python3", "-c", "print('default')"],
            allowlist=None,
        )
        assert result.returncode == 0

    def test_shell_mode_skips_allowlist_check(self):
        """shell=True bypasses allowlist (needed for edge cases)."""
        result = run_command(
            "echo hello",
            shell=True,
            allowlist=["python3"],  # echo is not in list
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# run_command input= parameter (FDA-129)
# ---------------------------------------------------------------------------


class TestRunCommandInput:
    """The input= parameter allows piping stdin to commands."""

    def test_input_param_pipes_stdin(self):
        """python3 -c can read stdin via input=."""
        result = run_command(
            ["python3", "-c", "import sys; data = sys.stdin.read(); print(data.strip())"],
            input="hello from stdin",
            allowlist=["python3"],
        )
        assert result.returncode == 0
        assert "hello from stdin" in result.stdout

    def test_input_none_is_default(self):
        """input=None (default) works for commands that don't read stdin."""
        result = run_command(
            ["python3", "-c", "print('no stdin')"],
            input=None,
            allowlist=["python3"],
        )
        assert result.returncode == 0

    def test_input_multiline(self):
        """Multiline input string is passed correctly."""
        script = "line1\nline2\nline3"
        result = run_command(
            ["python3", "-c", "import sys; lines = sys.stdin.read().splitlines(); print(len(lines))"],
            input=script,
            allowlist=["python3"],
        )
        assert result.returncode == 0
        assert "3" in result.stdout


# ---------------------------------------------------------------------------
# lint_subprocess_usage — violation detection
# ---------------------------------------------------------------------------


class TestLintDetectsViolations:
    """The linter catches direct subprocess usage in non-allowed files."""

    def _lint_code(self, code: str) -> list:
        """Helper: write code to a temp file and lint it."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, prefix="test_fda_") as f:
            f.write(code)
            path = Path(f.name)
        # Rename so it's not a test file (avoid is_allowed_file returning True)
        non_test_path = path.parent / "fda_module_check.py"
        path.rename(non_test_path)
        try:
            return lint_file(non_test_path)
        finally:
            non_test_path.unlink(missing_ok=True)

    def test_detects_import_subprocess(self):
        violations = self._lint_code("import subprocess\n")
        assert len(violations) > 0
        assert any("subprocess" in msg for _, _, msg in violations)

    def test_detects_from_subprocess_import(self):
        violations = self._lint_code("from subprocess import run\n")
        assert len(violations) > 0

    def test_detects_subprocess_run_call(self):
        violations = self._lint_code(
            "import subprocess\nsubprocess.run(['ls'])\n"
        )
        assert len(violations) >= 2  # import + call

    def test_detects_shell_true(self):
        violations = self._lint_code(
            "import subprocess\nsubprocess.run('ls', shell=True)\n"
        )
        # Should detect at least the import and the shell=True
        assert len(violations) >= 2

    def test_clean_code_has_no_violations(self):
        violations = self._lint_code(
            "from fda_tools.lib.subprocess_helpers import run_command\n"
            "run_command(['git', 'status'])\n"
        )
        assert violations == []


# ---------------------------------------------------------------------------
# lint_subprocess_usage — file skipping
# ---------------------------------------------------------------------------


class TestLintAllowedFiles:
    """Files in ALLOWED_MODULES and test files are skipped."""

    def test_subprocess_helpers_is_allowed(self):
        assert "subprocess_helpers.py" in ALLOWED_MODULES

    def test_lint_subprocess_usage_is_allowed(self):
        assert "lint_subprocess_usage.py" in ALLOWED_MODULES

    def test_test_file_is_skipped(self, tmp_path):
        test_file = tmp_path / "test_something.py"
        test_file.write_text("import subprocess\n")
        assert is_allowed_file(test_file) is True

    def test_tests_directory_is_skipped(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "mymodule.py"
        test_file.write_text("import subprocess\n")
        assert is_allowed_file(test_file) is True

    def test_regular_file_not_skipped(self, tmp_path):
        regular_file = tmp_path / "my_module.py"
        regular_file.write_text("import subprocess\n")
        assert is_allowed_file(regular_file) is False


# ---------------------------------------------------------------------------
# Migrated files pass the linter (FDA-129)
# ---------------------------------------------------------------------------


class TestMigratedFilesPassLinter:
    """All files migrated as part of FDA-129 must pass the linter."""

    _PLUGIN_ROOT = Path(__file__).parent.parent

    def _assert_no_violations(self, rel_path: str) -> None:
        path = self._PLUGIN_ROOT / rel_path
        assert path.is_file(), f"File not found: {path}"
        violations = lint_file(path)
        assert violations == [], (
            f"{rel_path} has subprocess violations:\n"
            + "\n".join(f"  line {l}: [{t}] {m}" for l, t, m in violations)
        )

    def test_backup_manager_passes_linter(self):
        self._assert_no_violations("lib/backup_manager.py")

    def test_security_audit_passes_linter(self):
        self._assert_no_violations("scripts/security_audit.py")

    def test_migrate_to_postgres_passes_linter(self):
        self._assert_no_violations("scripts/migrate_to_postgres.py")

    def test_update_coordinator_passes_linter(self):
        self._assert_no_violations("scripts/update_coordinator.py")
