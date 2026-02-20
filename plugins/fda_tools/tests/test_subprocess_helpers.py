"""
Unit tests for subprocess_helpers module.

Tests:
1. Basic command execution
2. Timeout enforcement
3. Retry logic for transient errors
4. Allowlist validation
5. Error callbacks
6. Environment variable merging
"""

import os
import pytest
import subprocess
import time
from pathlib import Path

from fda_tools.lib.subprocess_helpers import (
    run_command,
    SubprocessTimeoutError,
    SubprocessAllowlistError,
    _is_transient_error,
)


def test_basic_execution():
    """Test basic command execution with success."""
    result = run_command(
        ["python3", "-c", "print('hello')"],
        allowlist=["python3"],
    )
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_timeout_enforcement():
    """Test that timeout is enforced."""
    with pytest.raises(SubprocessTimeoutError):
        run_command(
            ["python3", "-c", "import time; time.sleep(10)"],
            timeout=1,
            allowlist=["python3"],
        )


def test_allowlist_validation():
    """Test that commands are validated against allowlist."""
    with pytest.raises(SubprocessAllowlistError) as exc_info:
        run_command(
            ["rm", "-rf", "/"],
            allowlist=["python3", "git"],
        )
    assert "not in allowlist" in str(exc_info.value)


def test_allowlist_bypass_with_shell():
    """Test that shell=True bypasses allowlist check."""
    # Should NOT raise allowlist error with shell=True
    result = run_command(
        "echo test",
        shell=True,
        allowlist=["python3"],  # echo not in allowlist
    )
    assert result.returncode == 0


def test_error_callback():
    """Test that error callback is called on failure."""
    error_called = []

    def on_error(e):
        error_called.append(e)

    with pytest.raises(SubprocessTimeoutError):
        run_command(
            ["python3", "-c", "import time; time.sleep(10)"],
            timeout=1,
            allowlist=["python3"],
            on_error=on_error,
        )

    assert len(error_called) == 1
    assert isinstance(error_called[0], SubprocessTimeoutError)


def test_timeout_callback():
    """Test that timeout callback is called on timeout."""
    timeout_called = []

    def on_timeout():
        timeout_called.append(True)

    with pytest.raises(SubprocessTimeoutError):
        run_command(
            ["python3", "-c", "import time; time.sleep(10)"],
            timeout=1,
            allowlist=["python3"],
            on_timeout=on_timeout,
        )

    assert timeout_called == [True]


def test_retry_logic():
    """Test retry logic for transient errors."""
    # Create a script that fails twice then succeeds
    script = """
import sys
import os
attempt_file = '/tmp/test_retry_attempt.txt'
if not os.path.exists(attempt_file):
    with open(attempt_file, 'w') as f:
        f.write('1')
    sys.exit(124)  # Transient error code
else:
    with open(attempt_file, 'r+') as f:
        count = int(f.read())
        if count < 2:
            f.seek(0)
            f.write(str(count + 1))
            sys.exit(124)  # Transient error
        else:
            f.seek(0)
            f.write('0')
            print('success')
            sys.exit(0)
"""

    # Clean up from previous runs
    if os.path.exists('/tmp/test_retry_attempt.txt'):
        os.remove('/tmp/test_retry_attempt.txt')

    result = run_command(
        ["python3", "-c", script],
        retry_count=3,
        retry_delay=0.1,
        allowlist=["python3"],
    )

    assert result.returncode == 0
    assert "success" in result.stdout

    # Clean up
    if os.path.exists('/tmp/test_retry_attempt.txt'):
        os.remove('/tmp/test_retry_attempt.txt')


def test_environment_merging():
    """Test that environment variables are merged correctly."""
    result = run_command(
        ["python3", "-c", "import os; print(os.environ.get('TEST_VAR'))"],
        env={"TEST_VAR": "test_value"},
        allowlist=["python3"],
    )
    assert result.returncode == 0
    assert "test_value" in result.stdout


def test_working_directory():
    """Test that working directory is set correctly."""
    result = run_command(
        ["python3", "-c", "import os; print(os.getcwd())"],
        cwd=Path("/tmp"),
        allowlist=["python3"],
    )
    assert result.returncode == 0
    assert "/tmp" in result.stdout


def test_check_flag():
    """Test that check=True raises CalledProcessError."""
    with pytest.raises(subprocess.CalledProcessError):
        run_command(
            ["python3", "-c", "import sys; sys.exit(1)"],
            check=True,
            allowlist=["python3"],
        )


def test_non_zero_exit_without_check():
    """Test that non-zero exit code doesn't raise without check=True."""
    result = run_command(
        ["python3", "-c", "import sys; sys.exit(42)"],
        check=False,
        allowlist=["python3"],
    )
    assert result.returncode == 42


def test_is_transient_error():
    """Test transient error classification."""
    assert _is_transient_error(124) is True  # Timeout
    assert _is_transient_error(111) is True  # Connection refused
    assert _is_transient_error(75) is True   # Temporary failure
    assert _is_transient_error(11) is True   # Resource unavailable

    assert _is_transient_error(1) is False   # Generic error
    assert _is_transient_error(127) is False # Command not found
    assert _is_transient_error(2) is False   # Misuse of shell builtin


def test_capture_output_false():
    """Test that output can be disabled."""
    result = run_command(
        ["python3", "-c", "print('test')"],
        capture_output=False,
        allowlist=["python3"],
    )
    # When capture_output=False, stdout/stderr are None
    assert result.stdout is None
    assert result.stderr is None
