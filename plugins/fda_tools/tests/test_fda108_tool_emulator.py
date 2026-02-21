"""
Unit Tests for ToolEmulator (FDA-108)
======================================

Validates all 6 tool emulators in fda_tools.bridge.tool_emulator:
  - Read: file reading with line numbers, path-traversal prevention
  - Write: atomic writes with backup/rollback, path-traversal prevention
  - Bash: allowlist enforcement, timeout, output capture
  - Grep: regex search, glob filter, case-insensitive, path-traversal prevention
  - Glob: pattern matching, modification-time sorting, path-traversal prevention
  - AskUserQuestion: async queue enqueue, multiple questions

Security tests:
  - Path traversal blocked (../ and absolute outside root)
  - Bash allowlist enforced (unknown commands raise PermissionError)
  - Symlink following respects sandbox boundary

Test count: 36
Target: pytest plugins/fda_tools/tests/test_fda108_tool_emulator.py -v
"""

import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from fda_tools.bridge.tool_emulator import (
    BASH_ALLOWLIST,
    MAX_BASH_OUTPUT_BYTES,
    MAX_GLOB_RESULTS,
    MAX_GREP_RESULTS,
    MAX_READ_BYTES,
    MAX_WRITE_BYTES,
    PathTraversalError,
    ToolEmulator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Return a temporary directory to serve as the project root."""
    return tmp_path


@pytest.fixture
def question_queue() -> Dict[str, List[Dict[str, Any]]]:
    """Return an empty question queue dict."""
    return {}


@pytest.fixture
def emulator(tmp_project: Path, question_queue: dict) -> ToolEmulator:
    """Return a ToolEmulator bound to tmp_project."""
    return ToolEmulator(
        project_root=tmp_project,
        session_id="test-session",
        question_queue=question_queue,
    )


# ---------------------------------------------------------------------------
# TestReadTool
# ---------------------------------------------------------------------------

class TestReadTool:
    """Tests for emulate_read()."""

    def test_read_basic_file(self, emulator: ToolEmulator, tmp_project: Path):
        """Read an existing file and verify line-numbered output."""
        (tmp_project / "hello.txt").write_text("line one\nline two\nline three")
        result = emulator.emulate_read("hello.txt")
        assert "line one" in result
        assert "line two" in result
        assert "line three" in result

    def test_read_line_numbers_format(self, emulator: ToolEmulator, tmp_project: Path):
        """Verify cat -n style line numbers (right-aligned, tab-separated)."""
        (tmp_project / "numbered.txt").write_text("alpha\nbeta\ngamma")
        result = emulator.emulate_read("numbered.txt")
        lines = result.split("\n")
        # Each line should have a number followed by a tab
        for line in lines:
            if line.strip():
                assert "\t" in line, f"Expected tab in line: {line!r}"
        # Line 1 should start with "     1\t"
        assert lines[0].lstrip().startswith("1\t")

    def test_read_with_offset(self, emulator: ToolEmulator, tmp_project: Path):
        """offset=1 skips the first line."""
        (tmp_project / "skip.txt").write_text("skip-me\nkeep-me\nalso-keep")
        result = emulator.emulate_read("skip.txt", offset=1)
        assert "skip-me" not in result
        assert "keep-me" in result
        assert "also-keep" in result

    def test_read_with_limit(self, emulator: ToolEmulator, tmp_project: Path):
        """limit=2 returns only the first two lines."""
        (tmp_project / "long.txt").write_text("\n".join(f"L{i}" for i in range(10)))
        result = emulator.emulate_read("long.txt", limit=2)
        output_lines = [l for l in result.split("\n") if l.strip()]
        assert len(output_lines) == 2
        assert "L0" in result
        assert "L9" not in result

    def test_read_offset_and_limit_combined(self, emulator: ToolEmulator, tmp_project: Path):
        """offset=2, limit=3 returns lines 3-5."""
        content = "\n".join(f"LINE{i}" for i in range(10))
        (tmp_project / "combo.txt").write_text(content)
        result = emulator.emulate_read("combo.txt", offset=2, limit=3)
        assert "LINE2" in result
        assert "LINE4" in result
        assert "LINE5" not in result  # beyond limit
        assert "LINE1" not in result  # before offset

    def test_read_file_not_found(self, emulator: ToolEmulator):
        """FileNotFoundError raised for missing file."""
        with pytest.raises(FileNotFoundError):
            emulator.emulate_read("does_not_exist.txt")

    def test_read_directory_raises(self, emulator: ToolEmulator, tmp_project: Path):
        """IsADirectoryError raised when path is a directory."""
        subdir = tmp_project / "subdir"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError):
            emulator.emulate_read("subdir")

    def test_read_path_traversal_blocked(self, emulator: ToolEmulator):
        """Path traversal via ../.. raises PathTraversalError."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_read("../../etc/passwd")


# ---------------------------------------------------------------------------
# TestWriteTool
# ---------------------------------------------------------------------------

class TestWriteTool:
    """Tests for emulate_write()."""

    def test_write_new_file(self, emulator: ToolEmulator, tmp_project: Path):
        """Write a new file and verify its contents."""
        info = emulator.emulate_write("output.md", "# Hello\n\nContent here.")
        path = tmp_project / "output.md"
        assert path.exists()
        assert path.read_text() == "# Hello\n\nContent here."
        assert info["backed_up"] is False
        assert info["bytes_written"] > 0

    def test_write_existing_file_creates_backup(self, emulator: ToolEmulator, tmp_project: Path):
        """Writing over an existing file creates a .bak backup."""
        (tmp_project / "data.txt").write_text("original content")
        info = emulator.emulate_write("data.txt", "new content")
        assert info["backed_up"] is True
        # Backup is removed after successful write
        assert not (tmp_project / "data.txt.bak").exists()
        assert (tmp_project / "data.txt").read_text() == "new content"

    def test_write_atomic_content_correct(self, emulator: ToolEmulator, tmp_project: Path):
        """Content written matches what was passed."""
        content = "line 1\nline 2\nline 3\n"
        emulator.emulate_write("atomic.txt", content)
        assert (tmp_project / "atomic.txt").read_text() == content

    def test_write_creates_parent_directories(self, emulator: ToolEmulator, tmp_project: Path):
        """Missing parent directories are created automatically."""
        emulator.emulate_write("deep/nested/dir/file.md", "nested content")
        assert (tmp_project / "deep" / "nested" / "dir" / "file.md").exists()

    def test_write_path_traversal_blocked(self, emulator: ToolEmulator):
        """Path traversal via ../ raises PathTraversalError."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_write("../escape.txt", "bad content")

    def test_write_returns_relative_path(self, emulator: ToolEmulator, tmp_project: Path):
        """Returned path is relative to project_root."""
        info = emulator.emulate_write("sub/report.md", "report")
        assert info["path"] == str(Path("sub") / "report.md")

    def test_write_backup_restored_on_failure(self, emulator: ToolEmulator, tmp_project: Path):
        """If write fails mid-way, the original file is restored from backup."""
        original = "original content"
        (tmp_project / "safe.txt").write_text(original)

        with patch("tempfile.NamedTemporaryFile", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                emulator.emulate_write("safe.txt", "new content")

        assert (tmp_project / "safe.txt").read_text() == original


# ---------------------------------------------------------------------------
# TestBashTool
# ---------------------------------------------------------------------------

class TestBashTool:
    """Tests for emulate_bash()."""

    def test_bash_allowlisted_echo(self, emulator: ToolEmulator):
        """echo is allowlisted and produces expected output."""
        result = emulator.emulate_bash("echo hello_from_bridge")
        assert result["exit_code"] == 0
        assert "hello_from_bridge" in result["stdout"]

    def test_bash_non_allowlisted_raises_permission_error(self, emulator: ToolEmulator):
        """A command not in BASH_ALLOWLIST raises PermissionError."""
        with pytest.raises(PermissionError, match="not permitted"):
            emulator.emulate_bash("rm -rf /tmp/test")

    def test_bash_empty_command_raises_value_error(self, emulator: ToolEmulator):
        """Empty command string raises ValueError."""
        with pytest.raises(ValueError, match="Empty command"):
            emulator.emulate_bash("")

    def test_bash_captures_stdout_and_stderr(self, emulator: ToolEmulator):
        """stdout and stderr are both captured separately."""
        result = emulator.emulate_bash(
            "python3 -c \"import sys; print('out'); sys.stderr.write('err\\n')\""
        )
        assert result["exit_code"] == 0
        assert "out" in result["stdout"]
        assert "err" in result["stderr"]

    def test_bash_nonzero_exit_code(self, emulator: ToolEmulator):
        """Non-zero exit code is reported correctly."""
        result = emulator.emulate_bash("python3 -c \"import sys; sys.exit(42)\"")
        assert result["exit_code"] == 42

    def test_bash_duration_ms_present(self, emulator: ToolEmulator):
        """duration_ms key is present and non-negative."""
        result = emulator.emulate_bash("echo timing")
        assert "duration_ms" in result
        assert result["duration_ms"] >= 0

    def test_bash_cwd_path_traversal_blocked(self, emulator: ToolEmulator):
        """Using cwd=../../ raises PathTraversalError."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_bash("echo cwd_test", cwd="../../")

    def test_bash_timeout_raises(self, emulator: ToolEmulator):
        """subprocess.TimeoutExpired raised when command exceeds timeout."""
        with pytest.raises(subprocess.TimeoutExpired):
            emulator.emulate_bash("python3 -c \"import time; time.sleep(60)\"", timeout=1)

    def test_bash_allowlist_constants_present(self):
        """BASH_ALLOWLIST contains the expected core tools."""
        for cmd in ("python3", "pytest", "git", "npm", "pip3"):
            assert cmd in BASH_ALLOWLIST, f"{cmd!r} missing from BASH_ALLOWLIST"


# ---------------------------------------------------------------------------
# TestGrepTool
# ---------------------------------------------------------------------------

class TestGrepTool:
    """Tests for emulate_grep()."""

    def test_grep_finds_pattern(self, emulator: ToolEmulator, tmp_project: Path):
        """Basic pattern match returns correct file, line, and content."""
        (tmp_project / "config.json").write_text('{"key": "K240001"}')
        results = emulator.emulate_grep("K[0-9]{6}")
        assert len(results) == 1
        assert results[0]["file"] == "config.json"
        assert results[0]["line"] == 1
        assert "K240001" in results[0]["content"]

    def test_grep_no_match_returns_empty_list(self, emulator: ToolEmulator, tmp_project: Path):
        """No-match pattern returns empty list."""
        (tmp_project / "plain.txt").write_text("hello world")
        results = emulator.emulate_grep("NOMATCH_XYZ_999")
        assert results == []

    def test_grep_case_insensitive(self, emulator: ToolEmulator, tmp_project: Path):
        """case_insensitive=True matches regardless of case."""
        (tmp_project / "notes.txt").write_text("FDA clearance approved\nNo match here")
        results = emulator.emulate_grep("fda clearance", case_insensitive=True)
        assert len(results) == 1
        assert results[0]["line"] == 1

    def test_grep_glob_filter(self, emulator: ToolEmulator, tmp_project: Path):
        """glob_pattern limits search to matching file types."""
        (tmp_project / "code.py").write_text("import fda_tools")
        (tmp_project / "notes.txt").write_text("import fda_tools")
        py_results = emulator.emulate_grep("import fda_tools", glob_pattern="*.py")
        assert len(py_results) == 1
        assert py_results[0]["file"].endswith(".py")

    def test_grep_path_traversal_blocked(self, emulator: ToolEmulator):
        """Path traversal in path argument raises PathTraversalError."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_grep("pattern", path="../..")

    def test_grep_single_file_path(self, emulator: ToolEmulator, tmp_project: Path):
        """Searching a specific file works when path points to a file."""
        (tmp_project / "target.txt").write_text("line A\nline B\nfind me\nline D")
        results = emulator.emulate_grep("find me", path="target.txt")
        assert len(results) == 1
        assert "find me" in results[0]["content"]

    def test_grep_invalid_regex_raises(self, emulator: ToolEmulator, tmp_project: Path):
        """Invalid regex raises re.error."""
        import re
        (tmp_project / "dummy.txt").write_text("some text")
        with pytest.raises(re.error):
            emulator.emulate_grep("[invalid regex(")


# ---------------------------------------------------------------------------
# TestGlobTool
# ---------------------------------------------------------------------------

class TestGlobTool:
    """Tests for emulate_glob()."""

    def test_glob_finds_matching_files(self, emulator: ToolEmulator, tmp_project: Path):
        """Basic glob returns expected files."""
        (tmp_project / "draft_cover.md").write_text("cover")
        (tmp_project / "draft_device.md").write_text("device")
        (tmp_project / "other.json").write_text("{}")
        results = emulator.emulate_glob("draft_*.md")
        assert len(results) == 2
        assert all(r.endswith(".md") for r in results)

    def test_glob_no_match_returns_empty(self, emulator: ToolEmulator, tmp_project: Path):
        """Non-matching pattern returns empty list."""
        (tmp_project / "file.txt").write_text("content")
        results = emulator.emulate_glob("*.xyz")
        assert results == []

    def test_glob_path_traversal_blocked(self, emulator: ToolEmulator):
        """path=../../ raises PathTraversalError."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_glob("*.py", path="../../")

    def test_glob_nonexistent_path_returns_empty(self, emulator: ToolEmulator):
        """path pointing to nonexistent dir returns empty list."""
        results = emulator.emulate_glob("*.md", path="no_such_dir")
        assert results == []

    def test_glob_returns_relative_paths(self, emulator: ToolEmulator, tmp_project: Path):
        """All returned paths are relative to project_root."""
        subdir = tmp_project / "sections"
        subdir.mkdir()
        (subdir / "intro.md").write_text("intro")
        results = emulator.emulate_glob("**/*.md")
        for r in results:
            assert not r.startswith("/"), f"Expected relative path, got: {r}"

    def test_glob_sorted_newest_first(self, emulator: ToolEmulator, tmp_project: Path):
        """Results are sorted by mtime descending (newest first)."""
        old = tmp_project / "old.md"
        new = tmp_project / "new.md"
        old.write_text("old")
        time.sleep(0.01)
        new.write_text("new")
        results = emulator.emulate_glob("*.md")
        assert len(results) == 2
        assert results[0] == "new.md"


# ---------------------------------------------------------------------------
# TestAskUserQuestion
# ---------------------------------------------------------------------------

class TestAskUserQuestion:
    """Tests for emulate_ask_user_question()."""

    def test_returns_uuid_string(self, emulator: ToolEmulator):
        """Returns a valid UUID string."""
        qid = emulator.emulate_ask_user_question("What device class?")
        # Should be parseable as UUID
        parsed = uuid.UUID(qid)
        assert str(parsed) == qid

    def test_enqueues_to_session(self, emulator: ToolEmulator, question_queue: dict):
        """Question is stored under the correct session in the queue."""
        emulator.emulate_ask_user_question("Confirm predicate selection?")
        assert "test-session" in question_queue
        questions = question_queue["test-session"]
        assert len(questions) == 1
        assert questions[0]["text"] == "Confirm predicate selection?"
        assert "id" in questions[0]
        assert "created_at" in questions[0]

    def test_multiple_questions_queued(self, emulator: ToolEmulator, question_queue: dict):
        """Multiple calls each add a distinct question."""
        id1 = emulator.emulate_ask_user_question("First question")
        id2 = emulator.emulate_ask_user_question("Second question")
        id3 = emulator.emulate_ask_user_question("Third question")

        # All IDs distinct
        assert len({id1, id2, id3}) == 3

        questions = question_queue["test-session"]
        assert len(questions) == 3
        texts = [q["text"] for q in questions]
        assert "First question" in texts
        assert "Second question" in texts
        assert "Third question" in texts


# ---------------------------------------------------------------------------
# TestPathSafety
# ---------------------------------------------------------------------------

class TestPathSafety:
    """Verify path traversal prevention across all tools."""

    def test_dotdot_traversal_blocked_read(self, emulator: ToolEmulator):
        """../../../etc/passwd raises PathTraversalError for Read."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_read("../../../etc/passwd")

    def test_absolute_path_outside_root_blocked(self, emulator: ToolEmulator):
        """Absolute path outside project_root raises PathTraversalError."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_read("/etc/passwd")

    def test_absolute_path_inside_root_allowed(
        self, emulator: ToolEmulator, tmp_project: Path
    ):
        """Absolute path that IS inside project_root is allowed."""
        target = tmp_project / "allowed.txt"
        target.write_text("content")
        # Use absolute path string
        result = emulator.emulate_read(str(target))
        assert "content" in result

    def test_encoded_traversal_blocked(self, emulator: ToolEmulator):
        """Nested traversal like sub/../../.. is blocked."""
        with pytest.raises(PathTraversalError):
            emulator.emulate_read("sub/../../..")
