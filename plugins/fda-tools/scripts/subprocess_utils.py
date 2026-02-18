#!/usr/bin/env python3
"""
Subprocess Utilities -- Shared subprocess execution helpers.

Provides standardized subprocess execution with consistent error handling,
timeout management, command allowlisting, and user-friendly error messages
across FDA tools.

Security Features:
    - Command allowlisting: Only pre-approved commands can be executed
    - Timeout enforcement: All subprocess calls have mandatory timeouts
    - Shell execution disabled: Commands are passed as lists, not shell strings
    - Output truncation: Prevents memory exhaustion from large outputs

Usage:
    from subprocess_utils import run_subprocess, safe_subprocess

    # Standard execution with all safety features:
    result = run_subprocess(
        cmd=["python3", "script.py", "--arg"],
        step_name="script execution",
        timeout_seconds=300,
        cwd="/path/to/working/dir",
        verbose=True
    )

    # Strict allowlist-enforced execution:
    result = safe_subprocess(
        command=["python3", "my_script.py"],
        allowed_commands={"python3", "node"},
        timeout=30,
    )
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ------------------------------------------------------------------
# Security Constants
# ------------------------------------------------------------------

# Default allowed commands for FDA tools operations.
# Only these executables may be invoked via safe_subprocess().
DEFAULT_ALLOWED_COMMANDS: Set[str] = {
    "python3",
    "node",
    "git",
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    "ls",
    "find",
    "diff",
}

# Maximum file size for safe_read_file (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Maximum subprocess timeout (10 minutes)
MAX_SUBPROCESS_TIMEOUT = 600


# ------------------------------------------------------------------
# Security-Hardened Functions
# ------------------------------------------------------------------

def safe_subprocess(
    command: List[str],
    allowed_commands: Optional[Set[str]] = None,
    timeout: int = 30,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Execute a subprocess with command allowlist enforcement.

    Only commands whose executable name appears in the allowed_commands
    set will be executed. This prevents arbitrary command injection.

    Args:
        command: Command and arguments as a list (e.g., ["python3", "script.py"]).
        allowed_commands: Set of allowed executable names. Defaults to
                         DEFAULT_ALLOWED_COMMANDS if not specified.
        timeout: Maximum seconds before killing the process (default: 30).
                Must be between 1 and MAX_SUBPROCESS_TIMEOUT.
        cwd: Working directory for the subprocess (optional).

    Returns:
        subprocess.CompletedProcess with stdout/stderr captured as text.

    Raises:
        ValueError: If command is empty, executable is not in allowlist,
                    or timeout is out of range.
        subprocess.TimeoutExpired: If the process exceeds the timeout.
        OSError: If the executable cannot be found or executed.
    """
    if allowed_commands is None:
        allowed_commands = DEFAULT_ALLOWED_COMMANDS

    if not command:
        raise ValueError("Command list must not be empty")

    executable = command[0]
    if executable not in allowed_commands:
        raise ValueError(
            f"Command not allowed: '{executable}'. "
            f"Allowed commands: {sorted(allowed_commands)}"
        )

    if not (1 <= timeout <= MAX_SUBPROCESS_TIMEOUT):
        raise ValueError(
            f"Timeout must be between 1 and {MAX_SUBPROCESS_TIMEOUT} seconds, "
            f"got {timeout}"
        )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        cwd=cwd,
    )
    return result


def safe_read_file(path: str, max_size: int = MAX_FILE_SIZE) -> str:
    """Read a file with size limit enforcement.

    Prevents reading excessively large files that could exhaust memory.

    Args:
        path: Path to the file to read (string or Path-like).
        max_size: Maximum allowed file size in bytes (default: 10 MB).

    Returns:
        File contents as a string.

    Raises:
        ValueError: If the file exceeds max_size.
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    stat = file_path.stat()
    if stat.st_size > max_size:
        raise ValueError(
            f"File too large: {stat.st_size:,} bytes "
            f"(limit: {max_size:,} bytes). "
            f"File: {path}"
        )

    return file_path.read_text(encoding="utf-8")


def run_subprocess(
    cmd: List[str],
    step_name: str,
    timeout_seconds: int,
    cwd: str,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run a subprocess with standardized error handling and user-friendly messages.

    Centralizes the try/except pattern for subprocess calls, providing consistent
    timeout messages, error reporting, and verbose output across FDA tools.

    This function is designed to handle common subprocess failure modes:
    1. Command timeout (e.g., slow FDA API, large datasets)
    2. OS errors (e.g., command not found, permission denied)
    3. Non-zero exit codes from the subprocess
    4. Network connectivity issues (API calls)

    Args:
        cmd: Command and arguments to execute as a list.
             Example: ["python3", "script.py", "--arg", "value"]
        step_name: Human-readable name for the step (e.g., "batchfetch", "extraction").
                   Used in log messages and result dictionaries.
        timeout_seconds: Maximum seconds before killing the process.
                         Typical values: 300 (5min) for API calls, 600 (10min) for heavy processing.
        cwd: Working directory for the subprocess (absolute path).
        verbose: If True, print progress information to stdout.

    Returns:
        Dictionary with step result containing one of three status types:

        Success (returncode 0):
        {
            "step": str,              # Same as step_name parameter
            "status": "success",
            "returncode": 0,
            "output": str,            # Last 500 chars of stdout
            "error": str,             # Last 500 chars of stderr (empty if none)
        }

        Error (non-zero returncode):
        {
            "step": str,
            "status": "error",
            "returncode": int,        # Non-zero exit code
            "output": str,            # Last 500 chars of stdout
            "error": str,             # Last 500 chars of stderr
        }

        Timeout (subprocess.TimeoutExpired):
        {
            "step": str,
            "status": "timeout",
            "output": str,            # User-friendly timeout message with suggestions
        }

    Examples:
        >>> # Simple command execution
        >>> result = run_subprocess(
        ...     cmd=["ls", "-la"],
        ...     step_name="list files",
        ...     timeout_seconds=30,
        ...     cwd="/tmp",
        ...     verbose=False
        ... )
        >>> result["status"]
        'success'

        >>> # Handle timeout
        >>> result = run_subprocess(
        ...     cmd=["python3", "slow_script.py"],
        ...     step_name="data processing",
        ...     timeout_seconds=5,
        ...     cwd="/path/to/scripts",
        ...     verbose=True
        ... )
        >>> if result["status"] == "timeout":
        ...     print("Consider increasing timeout_seconds")

        >>> # Check for errors
        >>> result = run_subprocess(
        ...     cmd=["python3", "script.py"],
        ...     step_name="validation",
        ...     timeout_seconds=60,
        ...     cwd="/path",
        ...     verbose=True
        ... )
        >>> if result["status"] == "error":
        ...     print(f"Failed with code {result['returncode']}")
        ...     print(f"Error output: {result['error']}")

    Notes:
        - Output is captured and trimmed to last 500 characters to avoid memory bloat
          with large subprocess outputs (e.g., verbose API responses)
        - Timeout messages include helpful diagnostics for common failure causes
        - OSError is caught to handle command-not-found and permission issues
        - All subprocess output is captured as text (text=True parameter)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=cwd,
        )
        step_result = {
            "step": step_name,
            "status": "success" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "output": result.stdout[-500:] if result.stdout else "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
        if verbose:
            status = "success" if result.returncode == 0 else "error"
            print(f"    {step_name}: {status}")
        return step_result
    except subprocess.TimeoutExpired:
        timeout_minutes = timeout_seconds / 60
        message = (
            f"Process timed out after {timeout_seconds} seconds. "
            f"Possible causes: (1) FDA API may be slow or unreachable -- "
            f"check your internet connection; (2) Large dataset requires "
            f"more time -- consider increasing the timeout; (3) The API "
            f"server may be under maintenance -- try again later."
        )
        step_result = {
            "step": step_name,
            "status": "timeout",
            "output": message,
        }
        if verbose:
            print(f"    {step_name}: TIMEOUT ({timeout_minutes:.0f}min)")
            print(f"      Suggestion: Check API connectivity or retry later.")
        return step_result
    except OSError as e:
        step_result = {
            "step": step_name,
            "status": "error",
            "output": str(e),
        }
        if verbose:
            print(f"    {step_name}: ERROR ({e})")
        return step_result
