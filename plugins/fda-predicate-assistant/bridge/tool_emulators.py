"""
Tool Emulators - Emulate Claude Code Tools for FDA Command Execution

Provides sandboxed implementations of:
1. ReadTool - File reading with line numbers (cat -n format)
2. WriteTool - File writing with path validation
3. BashTool - Command execution with security whitelist
4. GlobTool - File pattern matching
5. GrepTool - Content search
6. AskUserQuestionTool - Async user question queue

Security features:
- Path validation (prevent directory traversal)
- Command whitelist for Bash execution
- Timeout enforcement
- Resource limits (file size, execution time)

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import re
import json
import glob
import shlex
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Queue, Empty


# Maximum file size for read/write operations (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Maximum number of lines to read
MAX_READ_LINES = 2000

# Maximum line length before truncation
MAX_LINE_LENGTH = 2000

# Default Bash timeout in seconds
DEFAULT_BASH_TIMEOUT = 120

# Allowed base directories for file operations
ALLOWED_BASE_DIRS = [
    os.path.expanduser("~/fda-510k-data"),
    os.path.expanduser("~/.claude"),
    os.path.expanduser("~/fda-bridge-output"),
    "/tmp/fda-bridge",
]

# Bash command whitelist (prefix matching)
BASH_COMMAND_WHITELIST = [
    "python3",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "grep",
    "find",
    "ls",
    "stat",
    "file",
    "echo",
    "date",
    "mkdir",
    "cp",
    "mv",
    "curl",       # For FDA API calls
    "jq",         # JSON processing
    "csvtool",    # CSV processing
    "sed",        # Text processing (read-only patterns)
    "awk",        # Text processing
    "diff",       # File comparison
]

# Explicitly blocked commands
BASH_COMMAND_BLOCKLIST = [
    "rm",
    "rmdir",
    "chmod",
    "chown",
    "chgrp",
    "kill",
    "pkill",
    "killall",
    "shutdown",
    "reboot",
    "passwd",
    "su",
    "sudo",
    "mount",
    "umount",
    "mkfs",
    "dd",
    "fdisk",
    "iptables",
    "systemctl",
    "service",
    "apt",
    "yum",
    "dnf",
    "pip",
    "pip3",
    "npm",
    "wget",       # Use curl instead (controlled)
    "nc",
    "ncat",
    "netcat",
    "ssh",
    "scp",
    "sftp",
    "telnet",
    "nmap",
]


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    duration_ms: int = 0


def _validate_path(file_path: str, allow_write: bool = False) -> Tuple[bool, str]:
    """
    Validate that a file path is within allowed directories.

    Args:
        file_path: Path to validate
        allow_write: Whether write access is needed

    Returns:
        Tuple of (allowed, reason)
    """
    try:
        resolved = Path(file_path).resolve()
    except (ValueError, OSError) as e:
        return False, f"Invalid path: {e}"

    # Check for directory traversal
    path_str = str(resolved)

    # Check against allowed base directories
    allowed = False
    for base_dir in ALLOWED_BASE_DIRS:
        try:
            base_resolved = Path(base_dir).resolve()
            if path_str.startswith(str(base_resolved)):
                allowed = True
                break
        except (ValueError, OSError):
            continue

    # Also allow the FDA plugin directory itself (read-only)
    plugin_dir = Path(__file__).parent.parent.resolve()
    if path_str.startswith(str(plugin_dir)):
        if allow_write:
            # Only allow writing to bridge output within plugin dir
            bridge_out = plugin_dir / "bridge" / "output"
            if not path_str.startswith(str(bridge_out)):
                return False, (
                    f"Write access denied: {file_path} "
                    f"(plugin directory is read-only except bridge/output)"
                )
        allowed = True

    if not allowed:
        return False, (
            f"Path outside allowed directories: {file_path}\n"
            f"Allowed: {', '.join(ALLOWED_BASE_DIRS)}"
        )

    return True, "ok"


def _validate_bash_command(command: str) -> Tuple[bool, str]:
    """
    Validate that a bash command is in the whitelist.

    Args:
        command: Shell command to validate

    Returns:
        Tuple of (allowed, reason)
    """
    # Extract the base command (first word)
    try:
        parts = shlex.split(command)
    except ValueError:
        return False, f"Could not parse command: {command}"

    if not parts:
        return False, "Empty command"

    base_cmd = os.path.basename(parts[0])

    # Check blocklist first
    if base_cmd in BASH_COMMAND_BLOCKLIST:
        return False, f"Command blocked: {base_cmd}"

    # Check whitelist
    if base_cmd not in BASH_COMMAND_WHITELIST:
        return False, (
            f"Command not in whitelist: {base_cmd}\n"
            f"Allowed: {', '.join(sorted(BASH_COMMAND_WHITELIST))}"
        )

    # Additional checks for potentially dangerous patterns
    dangerous_patterns = [
        r'>\s*/dev/',          # Writing to devices
        r'>\s*/etc/',          # Writing to system config
        r'>\s*/var/',          # Writing to system dirs
        r'\|.*sh\b',          # Piping to shell
        r'\$\(',              # Command substitution (restricted)
        r'`',                 # Backtick substitution
        r';\s*(rm|chmod|kill|sudo)',  # Chained dangerous commands
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            return False, f"Dangerous pattern detected in command: {pattern}"

    return True, "ok"


class ReadTool:
    """
    Emulate Claude Code Read tool.

    Reads files with line numbers in cat -n format.
    Supports offset and limit parameters.
    Truncates lines longer than 2000 characters.
    """

    def execute(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = MAX_READ_LINES
    ) -> ToolResult:
        """
        Read a file with line numbers.

        Args:
            file_path: Absolute path to file
            offset: Line number to start from (0-based)
            limit: Maximum number of lines to read

        Returns:
            ToolResult with file contents in cat -n format
        """
        start_time = datetime.now(timezone.utc)

        # Validate path
        allowed, reason = _validate_path(file_path, allow_write=False)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: {reason}",
                duration_ms=_elapsed_ms(start_time)
            )

        path = Path(file_path)
        if not path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {file_path}",
                duration_ms=_elapsed_ms(start_time)
            )

        if not path.is_file():
            return ToolResult(
                success=False,
                output="",
                error=f"Not a file: {file_path}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Check file size
        try:
            size = path.stat().st_size
            if size > MAX_FILE_SIZE:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File too large: {size} bytes (max: {MAX_FILE_SIZE})",
                    duration_ms=_elapsed_ms(start_time)
                )
        except OSError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Cannot stat file: {e}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Read file
        try:
            with open(file_path, 'r', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Cannot read file: {e}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Apply offset and limit
        total_lines = len(lines)
        start = max(0, offset)
        end = min(total_lines, start + limit)
        selected_lines = lines[start:end]

        # Format with line numbers (cat -n format)
        output_lines = []
        for i, line in enumerate(selected_lines, start=start + 1):
            # Truncate long lines
            line = line.rstrip('\n')
            if len(line) > MAX_LINE_LENGTH:
                line = line[:MAX_LINE_LENGTH] + '... [truncated]'
            output_lines.append(f"{i:>6}\t{line}")

        output = '\n'.join(output_lines)

        if total_lines > end:
            output += f"\n\n[{total_lines - end} more lines not shown]"

        return ToolResult(
            success=True,
            output=output,
            files_read=[file_path],
            duration_ms=_elapsed_ms(start_time)
        )


class WriteTool:
    """
    Emulate Claude Code Write tool.

    Writes files with path validation and security checks.
    Creates parent directories if needed.
    """

    def execute(self, file_path: str, content: str) -> ToolResult:
        """
        Write content to a file.

        Args:
            file_path: Absolute path to file
            content: Content to write

        Returns:
            ToolResult indicating success/failure
        """
        start_time = datetime.now(timezone.utc)

        # Validate path
        allowed, reason = _validate_path(file_path, allow_write=True)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Write access denied: {reason}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Check content size
        if len(content) > MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                output="",
                error=f"Content too large: {len(content)} bytes (max: {MAX_FILE_SIZE})",
                duration_ms=_elapsed_ms(start_time)
            )

        # Create parent directories
        path = Path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Cannot create directory: {e}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Write file
        try:
            with open(file_path, 'w') as f:
                f.write(content)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Cannot write file: {e}",
                duration_ms=_elapsed_ms(start_time)
            )

        return ToolResult(
            success=True,
            output=f"File written: {file_path} ({len(content)} bytes)",
            files_written=[file_path],
            duration_ms=_elapsed_ms(start_time)
        )


class BashTool:
    """
    Emulate Claude Code Bash tool.

    Executes commands in a sandboxed environment with:
    - Command whitelist enforcement
    - Timeout enforcement
    - Working directory isolation
    - Resource limits
    """

    def __init__(self, working_dir: Optional[str] = None):
        """
        Initialize Bash tool.

        Args:
            working_dir: Default working directory for commands
        """
        self.working_dir = working_dir or os.path.expanduser("~/fda-510k-data")

    def execute(
        self,
        command: str,
        timeout: int = DEFAULT_BASH_TIMEOUT,
        working_dir: Optional[str] = None
    ) -> ToolResult:
        """
        Execute a shell command with security restrictions.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (default: 120)
            working_dir: Override working directory

        Returns:
            ToolResult with command output
        """
        start_time = datetime.now(timezone.utc)

        # Validate command
        allowed, reason = _validate_bash_command(command)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Command not allowed: {reason}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Set working directory
        cwd = working_dir or self.working_dir
        if not Path(cwd).exists():
            try:
                Path(cwd).mkdir(parents=True, exist_ok=True)
            except OSError:
                cwd = "/tmp/fda-bridge"
                Path(cwd).mkdir(parents=True, exist_ok=True)

        # Execute command
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=self._get_safe_env()
            )

            output = result.stdout
            error = result.stderr if result.returncode != 0 else None

            if result.returncode != 0 and not output:
                output = result.stderr

            return ToolResult(
                success=result.returncode == 0,
                output=output or "(no output)",
                error=error,
                duration_ms=_elapsed_ms(start_time)
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}s: {command}",
                duration_ms=_elapsed_ms(start_time)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Command execution failed: {e}",
                duration_ms=_elapsed_ms(start_time)
            )

    def _get_safe_env(self) -> Dict[str, str]:
        """Get a sanitized environment for command execution."""
        safe_env = {}

        # Copy only safe environment variables
        safe_vars = [
            'PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TERM',
            'PYTHONPATH', 'VIRTUAL_ENV',
            'ANTHROPIC_API_KEY', 'OPENAI_API_KEY',  # Needed for FDA API calls
        ]

        for var in safe_vars:
            val = os.environ.get(var)
            if val:
                safe_env[var] = val

        return safe_env


class GlobTool:
    """
    Emulate Claude Code Glob tool.

    Fast file pattern matching within allowed directories.
    """

    def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        max_results: int = 500
    ) -> ToolResult:
        """
        Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base directory to search in
            max_results: Maximum number of results

        Returns:
            ToolResult with matching file paths
        """
        start_time = datetime.now(timezone.utc)

        search_dir = path or os.path.expanduser("~/fda-510k-data")

        # Validate base directory
        allowed, reason = _validate_path(search_dir, allow_write=False)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Search directory not allowed: {reason}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Perform glob search
        try:
            full_pattern = os.path.join(search_dir, pattern)
            matches = sorted(
                glob.glob(full_pattern, recursive=True)
            )[:max_results]

            if matches:
                output = '\n'.join(matches)
            else:
                output = f"No files found matching: {pattern} in {search_dir}"

            return ToolResult(
                success=True,
                output=output,
                files_read=matches,
                duration_ms=_elapsed_ms(start_time)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Glob search failed: {e}",
                duration_ms=_elapsed_ms(start_time)
            )


class GrepTool:
    """
    Emulate Claude Code Grep tool.

    Regex content search within allowed directories.
    """

    def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_glob: Optional[str] = None,
        max_results: int = 100
    ) -> ToolResult:
        """
        Search file contents for a regex pattern.

        Args:
            pattern: Regex pattern to search for
            path: Directory or file to search in
            file_glob: Filter files by glob pattern
            max_results: Maximum number of results

        Returns:
            ToolResult with matching lines
        """
        start_time = datetime.now(timezone.utc)

        search_path = path or os.path.expanduser("~/fda-510k-data")

        # Validate path
        allowed, reason = _validate_path(search_path, allow_write=False)
        if not allowed:
            return ToolResult(
                success=False,
                output="",
                error=f"Search path not allowed: {reason}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Compile regex
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid regex pattern: {e}",
                duration_ms=_elapsed_ms(start_time)
            )

        # Find files to search
        search_dir = Path(search_path)
        if search_dir.is_file():
            files_to_search = [search_dir]
        else:
            glob_pattern = file_glob or "**/*"
            files_to_search = [
                f for f in search_dir.glob(glob_pattern)
                if f.is_file() and f.stat().st_size < MAX_FILE_SIZE
            ]

        # Search files
        matches = []
        files_with_matches = set()

        for filepath in files_to_search:
            if len(matches) >= max_results:
                break

            try:
                with open(filepath, 'r', errors='replace') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append(f"{filepath}:{line_num}: {line.rstrip()}")
                            files_with_matches.add(str(filepath))
                            if len(matches) >= max_results:
                                break
            except (OSError, UnicodeDecodeError):
                continue

        if matches:
            output = '\n'.join(matches)
            if len(matches) >= max_results:
                output += f"\n\n[Results truncated at {max_results}]"
        else:
            output = f"No matches for pattern: {pattern}"

        return ToolResult(
            success=True,
            output=output,
            files_read=list(files_with_matches),
            duration_ms=_elapsed_ms(start_time)
        )


class AskUserQuestionTool:
    """
    Emulate Claude Code AskUserQuestion tool.

    Queues questions for async user response.
    Responses are delivered via polling or webhook.
    """

    def __init__(self):
        """Initialize with question queue."""
        self._pending_questions: Dict[str, Dict[str, Any]] = {}
        self._responses: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

    def execute(
        self,
        questions: List[Dict[str, str]],
        session_id: str,
        timeout: int = 300
    ) -> ToolResult:
        """
        Queue questions for user response.

        Args:
            questions: List of {"id": str, "text": str} question dicts
            session_id: Session that generated the questions
            timeout: Timeout in seconds for user response

        Returns:
            ToolResult with question IDs for polling
        """
        start_time = datetime.now(timezone.utc)

        question_ids = []
        with self._lock:
            for q in questions:
                q_id = q.get('id', f"q_{len(self._pending_questions)}")
                self._pending_questions[q_id] = {
                    'text': q.get('text', ''),
                    'session_id': session_id,
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
                    'timeout': timeout,
                    'answered': False
                }
                question_ids.append(q_id)

        return ToolResult(
            success=True,
            output=json.dumps({
                'status': 'questions_queued',
                'question_ids': question_ids,
                'poll_endpoint': '/session/questions',
                'timeout_seconds': timeout
            }),
            duration_ms=_elapsed_ms(start_time)
        )

    def get_pending_questions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all pending questions for a session."""
        with self._lock:
            return [
                {'id': q_id, **q_data}
                for q_id, q_data in self._pending_questions.items()
                if q_data['session_id'] == session_id and not q_data['answered']
            ]

    def submit_answer(self, question_id: str, answer: str) -> bool:
        """
        Submit an answer to a pending question.

        Args:
            question_id: Question identifier
            answer: User's answer

        Returns:
            True if question found and answered
        """
        with self._lock:
            if question_id in self._pending_questions:
                self._pending_questions[question_id]['answered'] = True
                self._responses[question_id] = {
                    'answer': answer,
                    'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
                }
                return True
        return False

    def get_answer(self, question_id: str) -> Optional[str]:
        """Get the answer for a question, if available."""
        with self._lock:
            response = self._responses.get(question_id)
            return response['answer'] if response else None

    def cleanup_expired(self, max_age_seconds: int = 300) -> int:
        """Remove expired unanswered questions."""
        now = datetime.now(timezone.utc)
        cleaned = 0
        with self._lock:
            expired_ids = []
            for q_id, q_data in self._pending_questions.items():
                q_time = datetime.fromisoformat(
                    q_data['timestamp'].rstrip('Z')
                ).replace(tzinfo=timezone.utc)
                if (now - q_time).total_seconds() > max_age_seconds:
                    expired_ids.append(q_id)

            for q_id in expired_ids:
                del self._pending_questions[q_id]
                self._responses.pop(q_id, None)
                cleaned += 1

        return cleaned


class ToolRegistry:
    """
    Registry of all available tool emulators.

    Provides centralized access to tool instances with
    consistent error handling and audit integration.
    """

    def __init__(self, working_dir: Optional[str] = None):
        """Initialize tool registry with all tool instances."""
        self.read = ReadTool()
        self.write = WriteTool()
        self.bash = BashTool(working_dir=working_dir)
        self.glob = GlobTool()
        self.grep = GrepTool()
        self.ask_user = AskUserQuestionTool()

        self._tools = {
            'Read': self.read,
            'Write': self.write,
            'Bash': self.bash,
            'Glob': self.glob,
            'Grep': self.grep,
            'AskUserQuestion': self.ask_user
        }

    def get_tool(self, name: str) -> Optional[Any]:
        """Get tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List available tool names."""
        return list(self._tools.keys())


def _elapsed_ms(start_time: datetime) -> int:
    """Calculate elapsed milliseconds since start_time."""
    delta = datetime.now(timezone.utc) - start_time
    return int(delta.total_seconds() * 1000)
