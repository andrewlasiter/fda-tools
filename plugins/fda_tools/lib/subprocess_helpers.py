"""
Shared subprocess execution utilities for FDA Tools.

Provides centralized subprocess execution with consistent error handling,
timeout enforcement, retry logic, and command allowlisting.

Usage:
    from fda_tools.lib.subprocess_helpers import run_command

    result = run_command(
        ["python3", "script.py", "--arg"],
        timeout=120,
        retry_count=3,
        on_error=lambda e: logger.error(f"Failed: {e}")
    )
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SubprocessError(Exception):
    """Base exception for subprocess execution errors."""
    pass


class SubprocessTimeoutError(SubprocessError):
    """Exception raised when subprocess exceeds timeout."""
    pass


class SubprocessAllowlistError(SubprocessError):
    """Exception raised when command is not in allowlist."""
    pass


# Default command allowlist for security
DEFAULT_ALLOWLIST = [
    "python3",
    "pytest",
    "git",
    "pandoc",
    "tesseract",
    "pdftotext",
    "python",
    "pip",
    # Docker / database infrastructure (FDA-129)
    "docker",
    "docker-compose",
    "gpg",
    "aws",
    "createdb",
    "dropdb",
    "psql",
    "pg_dump",
    "pg_restore",
]

def run_command(
    cmd: Union[List[str], str],
    timeout: Optional[int] = None,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    retry_count: int = 0,
    retry_delay: float = 1.0,
    allowlist: Optional[List[str]] = None,
    on_timeout: Optional[Callable[[], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    shell: bool = False,
    input: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """
    Execute a command with consistent error handling and retry logic.

    Args:
        cmd: Command to execute (list of args or string if shell=True)
        timeout: Maximum execution time in seconds (None for no limit)
        cwd: Working directory for command execution
        env: Environment variables (merged with os.environ if provided)
        capture_output: Whether to capture stdout/stderr
        text: Whether to decode output as text (vs bytes)
        check: Whether to raise exception on non-zero exit code
        retry_count: Number of retries on transient failures (0 = no retries)
        retry_delay: Delay between retries in seconds
        allowlist: List of allowed command names (None = use DEFAULT_ALLOWLIST)
        on_timeout: Callback function called on timeout
        on_error: Callback function called on error (receives exception)
        shell: Whether to execute command through shell
        input: Optional stdin data to pass to the process

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode

    Raises:
        SubprocessTimeoutError: If command exceeds timeout
        SubprocessAllowlistError: If command not in allowlist
        subprocess.CalledProcessError: If check=True and exit code != 0

    Examples:
        # Basic usage
        result = run_command(["python3", "script.py"])
        print(result.stdout)

        # With timeout and retry
        result = run_command(
            ["git", "pull"],
            timeout=30,
            retry_count=3,
            retry_delay=2.0
        )

        # With error callback
        result = run_command(
            ["pytest", "tests/"],
            on_error=lambda e: logger.error(f"Tests failed: {e}")
        )
    """
    # Validate allowlist
    if allowlist is None:
        allowlist = DEFAULT_ALLOWLIST

    if allowlist and not shell:
        cmd_name = cmd[0] if isinstance(cmd, list) else cmd.split()[0]
        if cmd_name not in allowlist:
            error = SubprocessAllowlistError(
                f"Command '{cmd_name}' not in allowlist: {allowlist}"
            )
            if on_error:
                on_error(error)
            raise error

    # Merge environment variables
    if env is not None:
        merged_env = {**os.environ, **env}
    else:
        merged_env = None

    # Retry loop
    last_exception = None
    for attempt in range(retry_count + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
                cwd=str(cwd) if cwd else None,
                env=merged_env,
                shell=shell,
                input=input,
            )

            # Check for transient errors even when check=False
            if result.returncode != 0 and retry_count > 0:
                if attempt < retry_count and _is_transient_error(result.returncode):
                    logger.warning(
                        f"Transient error (exit code {result.returncode}), "
                        f"retrying in {retry_delay}s (attempt {attempt + 1}/{retry_count + 1})"
                    )
                    time.sleep(retry_delay)
                    continue

            # Success or non-retriable failure
            return result

        except subprocess.TimeoutExpired as e:
            last_exception = SubprocessTimeoutError(
                f"Command timed out after {timeout}s: {cmd}"
            )
            if on_timeout:
                on_timeout()
            # Don't retry timeout errors
            break

        except subprocess.CalledProcessError as e:
            last_exception = e
            # Retry transient errors (exit codes suggesting network/resource issues)
            if attempt < retry_count and _is_transient_error(e.returncode):
                logger.warning(
                    f"Transient error (exit code {e.returncode}), "
                    f"retrying in {retry_delay}s (attempt {attempt + 1}/{retry_count + 1})"
                )
                time.sleep(retry_delay)
                continue
            # Non-transient error or out of retries
            break

        except Exception as e:
            last_exception = e
            break

    # All retries exhausted or non-retriable error occurred
    if on_error and last_exception:
        on_error(last_exception)
    raise last_exception


# Backward-compatibility alias — renamed run_subprocess → run_command in FDA-115 (FDA-199)
run_subprocess = run_command


def _is_transient_error(exit_code: int) -> bool:
    """
    Determine if exit code indicates a transient error worth retrying.

    Transient errors include:
    - Network timeouts (exit code 124)
    - Resource unavailable (exit code 11)
    - Connection refused (exit code 111)
    - Temporary failure (exit code 75)

    Args:
        exit_code: Process exit code

    Returns:
        True if error is likely transient
    """
    transient_codes = {11, 75, 111, 124}
    return exit_code in transient_codes


def run_command_with_streaming(
    cmd: Union[List[str], str],
    timeout: Optional[int] = None,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    allowlist: Optional[List[str]] = None,
    on_stdout: Optional[Callable[[str], None]] = None,
    on_stderr: Optional[Callable[[str], None]] = None,
    shell: bool = False,
) -> int:
    """
    Execute a command with line-by-line output streaming.

    Unlike run_command(), this captures output in real-time and calls
    callbacks for each line. Useful for long-running commands.

    Args:
        cmd: Command to execute
        timeout: Maximum execution time in seconds
        cwd: Working directory
        env: Environment variables
        allowlist: List of allowed command names
        on_stdout: Callback for each stdout line
        on_stderr: Callback for each stderr line
        shell: Whether to execute through shell

    Returns:
        Exit code of the process

    Raises:
        SubprocessTimeoutError: If command exceeds timeout
        SubprocessAllowlistError: If command not in allowlist
    """
    # Validate allowlist
    if allowlist is None:
        allowlist = DEFAULT_ALLOWLIST

    if allowlist and not shell:
        cmd_name = cmd[0] if isinstance(cmd, list) else cmd.split()[0]
        if cmd_name not in allowlist:
            raise SubprocessAllowlistError(
                f"Command '{cmd_name}' not in allowlist: {allowlist}"
            )

    # Merge environment
    if env is not None:
        merged_env = {**os.environ, **env}
    else:
        merged_env = None

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            shell=shell,
        )

        # Stream output
        import select

        streams = [process.stdout, process.stderr]
        while process.poll() is None:
            readable, _, _ = select.select(streams, [], [], 0.1)

            for stream in readable:
                line = stream.readline()
                if line:
                    if stream == process.stdout and on_stdout:
                        on_stdout(line.rstrip())
                    elif stream == process.stderr and on_stderr:
                        on_stderr(line.rstrip())

        # Get remaining output
        stdout, stderr = process.communicate(timeout=timeout)
        if stdout and on_stdout:
            for line in stdout.splitlines():
                on_stdout(line)
        if stderr and on_stderr:
            for line in stderr.splitlines():
                on_stderr(line)

        return process.returncode

    except subprocess.TimeoutExpired:
        process.kill()
        raise SubprocessTimeoutError(f"Command timed out after {timeout}s: {cmd}")
