"""
Tool Emulator for FDA Tools Bridge Server (FDA-108)
=====================================================

Emulates Claude Code tools (Read, Write, Bash, Grep, Glob, AskUserQuestion)
within bridge sessions. Each tool operates within a sandboxed project directory
with strict path traversal prevention and command allowlisting.

Security Model:
  - Read/Write/Grep/Glob: Restricted to project root (no path traversal)
  - Bash: Command allowlist enforced (pytest, git, npm, python3, pip3, etc.)
  - AskUserQuestion: Async non-blocking queue — never blocks command execution

Usage:
    emulator = ToolEmulator(
        project_root=Path("~/fda-510k-data/projects/my-device"),
        session_id="abc-123",
        question_queue=PENDING_QUESTIONS,  # shared server dict
    )
    content = emulator.emulate_read("device_profile.json")
    emulator.emulate_write("draft_cover.md", "# Cover Letter\\n...")
    results = emulator.emulate_grep("K[0-9]{6}", ".", glob_pattern="*.json")
    files = emulator.emulate_glob("draft_*.md")
    question_id = emulator.emulate_ask_user_question("Which predicate do you prefer?")
"""

import os
import re
import shlex
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Allowlisted bash executables
# ---------------------------------------------------------------------------

BASH_ALLOWLIST: frozenset = frozenset(
    {
        "python3",
        "python",
        "pytest",
        "git",
        "npm",
        "node",
        "pip",
        "pip3",
        "ls",
        "echo",
        "cat",
    }
)

# ---------------------------------------------------------------------------
# Resource limits (prevent accidental exhaustion)
# ---------------------------------------------------------------------------

MAX_READ_BYTES: int = 10 * 1024 * 1024       # 10 MB per read
MAX_WRITE_BYTES: int = 10 * 1024 * 1024      # 10 MB per write
MAX_GREP_RESULTS: int = 1_000                # Max grep matches returned
MAX_GLOB_RESULTS: int = 500                  # Max glob matches returned
MAX_BASH_OUTPUT_BYTES: int = 1 * 1024 * 1024  # 1 MB bash output per stream


# ---------------------------------------------------------------------------
# Exception types
# ---------------------------------------------------------------------------

class PathTraversalError(ValueError):
    """Raised when a file path escapes the project root sandbox."""


# ---------------------------------------------------------------------------
# ToolEmulator
# ---------------------------------------------------------------------------

class ToolEmulator:
    """
    Emulates Claude Code tools within FDA bridge sessions.

    All file operations (Read, Write, Grep, Glob) are sandboxed to
    ``project_root``. The Bash tool enforces a command allowlist.
    AskUserQuestion enqueues questions without blocking.

    Args:
        project_root: Absolute path to the project directory.
            All file operations are sandboxed within this path.
        session_id: Session identifier used for the question queue.
        question_queue: Shared mutable dict (server's PENDING_QUESTIONS).
            Maps session_id → list of pending question dicts.
    """

    def __init__(
        self,
        project_root: Path,
        session_id: str,
        question_queue: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        self.project_root = project_root.resolve()
        self.session_id = session_id
        self.question_queue = question_queue

    # -------------------------------------------------------------------
    # Path safety helper
    # -------------------------------------------------------------------

    def _resolve_safe_path(self, file_path: str) -> Path:
        """Resolve *file_path* relative to ``project_root`` and verify containment.

        Args:
            file_path: Relative or absolute path string.

        Returns:
            Resolved :class:`Path` guaranteed to be under ``project_root``.

        Raises:
            PathTraversalError: If the resolved path escapes ``project_root``.
        """
        candidate = (self.project_root / file_path).resolve()
        # The path is safe if it equals project_root itself OR starts with
        # project_root + separator (prevents "/project_rootX" from matching).
        root_str = str(self.project_root)
        candidate_str = str(candidate)
        if candidate_str != root_str and not candidate_str.startswith(root_str + os.sep):
            raise PathTraversalError(
                f"Path traversal blocked: '{file_path}' resolves outside project root"
            )
        return candidate

    # -------------------------------------------------------------------
    # Read tool
    # -------------------------------------------------------------------

    def emulate_read(
        self,
        file_path: str,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> str:
        """Read a file with ``cat -n`` style line numbers.

        Args:
            file_path: Path relative to ``project_root``.
            offset: 0-based line offset to start reading from.
            limit: Maximum number of lines to return (``None`` = all).

        Returns:
            File contents formatted as ``"    N\\tline"`` per line.

        Raises:
            PathTraversalError: If path escapes ``project_root``.
            FileNotFoundError: If the file does not exist.
            IsADirectoryError: If the path points to a directory.
            ValueError: If the file exceeds ``MAX_READ_BYTES``.
        """
        path = self._resolve_safe_path(file_path)

        if path.is_dir():
            raise IsADirectoryError(f"Path is a directory: {file_path}")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = path.stat()
        if stat.st_size > MAX_READ_BYTES:
            raise ValueError(
                f"File too large: {stat.st_size} bytes (max {MAX_READ_BYTES})"
            )

        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")

        if offset > 0:
            lines = lines[offset:]
        if limit is not None:
            lines = lines[:limit]

        numbered = [
            f"{i + offset + 1:6}\t{line}" for i, line in enumerate(lines)
        ]
        return "\n".join(numbered)

    # -------------------------------------------------------------------
    # Write tool
    # -------------------------------------------------------------------

    def emulate_write(self, file_path: str, content: str) -> Dict[str, Any]:
        """Atomically write a file within the project directory.

        Creates parent directories as needed. If the file already exists,
        a ``.bak`` backup is created before writing. On failure, the backup
        is restored automatically.

        Args:
            file_path: Path relative to ``project_root``.
            content: UTF-8 string content to write.

        Returns:
            Dict with keys:

            - ``path`` (str): Relative path written.
            - ``bytes_written`` (int): Byte count of content.
            - ``backed_up`` (bool): Whether an existing file was backed up.

        Raises:
            PathTraversalError: If path escapes ``project_root``.
            ValueError: If content exceeds ``MAX_WRITE_BYTES``.
        """
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_WRITE_BYTES:
            raise ValueError(
                f"Content too large: {len(encoded)} bytes (max {MAX_WRITE_BYTES})"
            )

        path = self._resolve_safe_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        backup_path: Optional[Path] = None
        backed_up = False

        if path.exists():
            backup_path = path.with_suffix(path.suffix + ".bak")
            path.rename(backup_path)
            backed_up = True

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=path.parent,
                prefix=f"{path.name}.tmp.",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                tmp_name = tmp.name
            Path(tmp_name).replace(path)  # Atomic rename
        except Exception:
            if backup_path and backup_path.exists():
                backup_path.rename(path)
            raise
        else:
            if backup_path and backup_path.exists():
                backup_path.unlink()

        return {
            "path": str(path.relative_to(self.project_root)),
            "bytes_written": len(encoded),
            "backed_up": backed_up,
        }

    # -------------------------------------------------------------------
    # Bash tool
    # -------------------------------------------------------------------

    def emulate_bash(
        self,
        command: str,
        timeout: int = 30,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a shell command from the allowlist with timeout enforcement.

        Args:
            command: Shell command string (parsed via :func:`shlex.split`).
            timeout: Maximum execution time in seconds (default 30).
            cwd: Optional working directory relative to ``project_root``.

        Returns:
            Dict with keys:

            - ``stdout`` (str): Standard output (truncated at 1 MB).
            - ``stderr`` (str): Standard error (truncated at 1 MB).
            - ``exit_code`` (int): Process exit code.
            - ``duration_ms`` (int): Wall-clock duration in milliseconds.

        Raises:
            PathTraversalError: If ``cwd`` escapes ``project_root``.
            PermissionError: If the executable is not in :data:`BASH_ALLOWLIST`.
            ValueError: If ``command`` is empty.
            subprocess.TimeoutExpired: If execution exceeds ``timeout``.
        """
        parts = shlex.split(command)
        if not parts:
            raise ValueError("Empty command string")

        executable = parts[0]
        if executable not in BASH_ALLOWLIST:
            raise PermissionError(
                f"Command not permitted: '{executable}'. "
                f"Allowed executables: {sorted(BASH_ALLOWLIST)}"
            )

        work_dir = self.project_root
        if cwd is not None:
            work_dir = self._resolve_safe_path(cwd)

        start = time.monotonic()
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=work_dir,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        stdout = result.stdout
        stderr = result.stderr

        if len(stdout) > MAX_BASH_OUTPUT_BYTES:
            stdout = stdout[:MAX_BASH_OUTPUT_BYTES] + "\n[TRUNCATED]"
        if len(stderr) > MAX_BASH_OUTPUT_BYTES:
            stderr = stderr[:MAX_BASH_OUTPUT_BYTES] + "\n[TRUNCATED]"

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "duration_ms": duration_ms,
        }

    # -------------------------------------------------------------------
    # Grep tool
    # -------------------------------------------------------------------

    def emulate_grep(
        self,
        pattern: str,
        path: str = ".",
        glob_pattern: Optional[str] = None,
        case_insensitive: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search for a regex pattern in files within the project directory.

        Args:
            pattern: Regular expression pattern to search.
            path: Directory or file path relative to ``project_root``.
            glob_pattern: Optional glob to filter files (e.g., ``"*.py"``).
            case_insensitive: Perform case-insensitive matching.

        Returns:
            List of match dicts with keys:

            - ``file`` (str): Relative file path.
            - ``line`` (int): 1-based line number.
            - ``content`` (str): Matching line content.

            Capped at ``MAX_GREP_RESULTS`` results.

        Raises:
            PathTraversalError: If ``path`` escapes ``project_root``.
            re.error: If ``pattern`` is not a valid regular expression.
        """
        search_path = self._resolve_safe_path(path)
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
        results: List[Dict[str, Any]] = []

        if search_path.is_file():
            files: List[Path] = [search_path]
        elif search_path.is_dir():
            if glob_pattern:
                files = sorted(search_path.glob(glob_pattern))
            else:
                files = sorted(f for f in search_path.rglob("*") if f.is_file())
        else:
            return results

        for file_path in files:
            # Symlink safety: verify file is still inside project_root
            try:
                resolved_file = file_path.resolve()
            except OSError:
                continue
            if not str(resolved_file).startswith(str(self.project_root)):
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for line_num, line in enumerate(text.split("\n"), start=1):
                if regex.search(line):
                    results.append(
                        {
                            "file": str(file_path.relative_to(self.project_root)),
                            "line": line_num,
                            "content": line,
                        }
                    )
                    if len(results) >= MAX_GREP_RESULTS:
                        return results

        return results

    # -------------------------------------------------------------------
    # Glob tool
    # -------------------------------------------------------------------

    def emulate_glob(self, pattern: str, path: str = ".") -> List[str]:
        """Find files matching a glob pattern within the project directory.

        Args:
            pattern: Glob pattern (e.g., ``"**/*.py"``, ``"draft_*.md"``).
            path: Base directory relative to ``project_root``.

        Returns:
            List of paths relative to ``project_root``, sorted newest-first
            by modification time. Capped at ``MAX_GLOB_RESULTS`` results.

        Raises:
            PathTraversalError: If ``path`` escapes ``project_root``.
        """
        search_path = self._resolve_safe_path(path)
        if not search_path.exists():
            return []

        matches: List[Path] = []
        for candidate in search_path.glob(pattern):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if str(resolved).startswith(str(self.project_root)):
                matches.append(candidate)

        # Sort newest-first, cap results
        matches.sort(
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        matches = matches[:MAX_GLOB_RESULTS]

        return [str(p.relative_to(self.project_root)) for p in matches]

    # -------------------------------------------------------------------
    # AskUserQuestion tool
    # -------------------------------------------------------------------

    def emulate_ask_user_question(self, question: str) -> str:
        """Enqueue a question for the user to answer asynchronously.

        The question is stored in the shared ``PENDING_QUESTIONS`` dict,
        retrievable via ``GET /session/{session_id}/questions``. This method
        returns immediately with a ``question_id`` — it does **not** block.

        Args:
            question: The question text to present to the user.

        Returns:
            UUID string ``question_id`` that uniquely identifies the queued
            question. The caller can poll the questions endpoint to check
            whether the user has answered.
        """
        question_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        if self.session_id not in self.question_queue:
            self.question_queue[self.session_id] = []

        self.question_queue[self.session_id].append(
            {
                "id": question_id,
                "text": question,
                "session_id": self.session_id,
                "created_at": now,
            }
        )

        return question_id
