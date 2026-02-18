#!/usr/bin/env python3
"""
Subprocess Utilities — Shared subprocess execution helpers.

Provides standardized subprocess execution with consistent error handling,
timeout management, and user-friendly error messages across FDA tools.

Usage:
    from subprocess_utils import run_subprocess

    result = run_subprocess(
        cmd=["python3", "script.py", "--arg"],
        step_name="script execution",
        timeout_seconds=300,
        cwd="/path/to/working/dir",
        verbose=True
    )

    if result["status"] == "success":
        print("Output:", result["output"])
    elif result["status"] == "timeout":
        print("Timed out:", result["output"])
    else:
        print("Error:", result["error"])
"""

import subprocess
from typing import Any, Dict, List


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
