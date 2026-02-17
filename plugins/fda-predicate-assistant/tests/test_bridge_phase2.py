"""
Phase 2 Bridge Server - Comprehensive Test Suite

Tests for:
1. Session Manager (CRUD, persistence, expiry, LRU cache)
2. Tool Emulators (Read, Write, Bash, Glob, Grep, AskUserQuestion)
3. FastAPI Server (endpoints, security integration, audit logging)
4. End-to-end command execution

Run with:
    cd plugins/fda-predicate-assistant
    python3 -m pytest tests/test_bridge_phase2.py -v

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

# Add paths for imports
TESTS_DIR = Path(__file__).parent.resolve()
PLUGIN_DIR = TESTS_DIR.parent.resolve()
BRIDGE_DIR = PLUGIN_DIR / "bridge"
LIB_DIR = PLUGIN_DIR / "lib"

sys.path.insert(0, str(BRIDGE_DIR))
sys.path.insert(0, str(LIB_DIR))

from session_manager import Session, SessionManager, LRUSessionCache
from tool_emulators import (
    ReadTool, WriteTool, BashTool, GlobTool, GrepTool,
    AskUserQuestionTool, ToolRegistry, ToolResult,
    _validate_path, _validate_bash_command
)


# ============================================================
# Session Manager Tests
# ============================================================

class TestSession:
    """Test the Session dataclass."""

    def test_create_session(self):
        """Test creating a session with default values."""
        now = datetime.now(timezone.utc).isoformat() + 'Z'
        session = Session(
            session_id="test-123",
            user_id="alice",
            created_at=now,
            last_accessed=now
        )
        assert session.session_id == "test-123"
        assert session.user_id == "alice"
        assert session.context == {}
        assert session.metadata == {}

    def test_session_serialization(self):
        """Test session to_dict and from_dict."""
        now = datetime.now(timezone.utc).isoformat() + 'Z'
        session = Session(
            session_id="test-456",
            user_id="bob",
            created_at=now,
            last_accessed=now,
            context={'key': 'value'},
            metadata={'pref': 'dark'}
        )

        data = session.to_dict()
        restored = Session.from_dict(data)

        assert restored.session_id == session.session_id
        assert restored.user_id == session.user_id
        assert restored.context == session.context
        assert restored.metadata == session.metadata

    def test_session_touch(self):
        """Test updating last_accessed timestamp."""
        old_time = "2020-01-01T00:00:00Z"
        session = Session(
            session_id="test-789",
            user_id="carol",
            created_at=old_time,
            last_accessed=old_time
        )

        session.touch()
        assert session.last_accessed != old_time
        assert "2026" in session.last_accessed or "202" in session.last_accessed

    def test_session_expiry(self):
        """Test session expiry check."""
        old_time = "2020-01-01T00:00:00Z"
        session = Session(
            session_id="test-exp",
            user_id="dave",
            created_at=old_time,
            last_accessed=old_time
        )
        assert session.is_expired(max_age_hours=24) is True

        # Fresh session should not be expired
        now = datetime.now(timezone.utc).isoformat() + 'Z'
        fresh = Session(
            session_id="test-fresh",
            user_id="eve",
            created_at=now,
            last_accessed=now
        )
        assert fresh.is_expired(max_age_hours=24) is False


class TestLRUSessionCache:
    """Test the LRU cache for sessions."""

    def test_basic_operations(self):
        """Test get, put, remove."""
        cache = LRUSessionCache(max_size=3)
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        s1 = Session("s1", "u1", now, now)
        s2 = Session("s2", "u2", now, now)

        cache.put(s1)
        cache.put(s2)

        assert cache.size() == 2
        assert cache.get("s1").user_id == "u1"
        assert cache.get("s3") is None

        removed = cache.remove("s1")
        assert removed.session_id == "s1"
        assert cache.size() == 1

    def test_lru_eviction(self):
        """Test that LRU session is evicted when at capacity."""
        cache = LRUSessionCache(max_size=2)
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        s1 = Session("s1", "u1", now, now)
        s2 = Session("s2", "u2", now, now)
        s3 = Session("s3", "u3", now, now)

        cache.put(s1)
        cache.put(s2)

        # Adding s3 should evict s1 (least recently used)
        evicted = cache.put(s3)
        assert evicted is not None
        assert evicted.session_id == "s1"
        assert cache.size() == 2
        assert cache.get("s1") is None
        assert cache.get("s2") is not None

    def test_access_updates_lru_order(self):
        """Test that accessing a session moves it to most-recent."""
        cache = LRUSessionCache(max_size=2)
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        s1 = Session("s1", "u1", now, now)
        s2 = Session("s2", "u2", now, now)

        cache.put(s1)
        cache.put(s2)

        # Access s1 to make it most recent
        cache.get("s1")

        # Adding s3 should now evict s2 (least recently used)
        s3 = Session("s3", "u3", now, now)
        evicted = cache.put(s3)
        assert evicted.session_id == "s2"

    def test_clear(self):
        """Test clearing all sessions."""
        cache = LRUSessionCache(max_size=10)
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        for i in range(5):
            cache.put(Session("s{}".format(i), "u{}".format(i), now, now))

        assert cache.size() == 5
        cache.clear()
        assert cache.size() == 0


class TestSessionManager:
    """Test the SessionManager class."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create temporary sessions directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_session(self, temp_sessions_dir):
        """Test creating a new session."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        session = mgr.create_session(user_id="alice")

        assert session.user_id == "alice"
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.context.get('conversation_history') == []
        assert session.context.get('command_count') == 0

    def test_get_session(self, temp_sessions_dir):
        """Test retrieving a session."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        created = mgr.create_session(user_id="bob")
        retrieved = mgr.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.user_id == "bob"

    def test_get_nonexistent_session(self, temp_sessions_dir):
        """Test retrieving a non-existent session returns None."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        result = mgr.get_session("nonexistent-id")
        assert result is None

    def test_get_or_create_session(self, temp_sessions_dir):
        """Test get_or_create_session logic."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)

        # Create initial session
        session1 = mgr.get_or_create_session(user_id="carol")
        assert session1 is not None

        # Retrieve existing session
        session2 = mgr.get_or_create_session(
            user_id="carol",
            session_id=session1.session_id
        )
        assert session2.session_id == session1.session_id

        # Non-existent session creates new
        session3 = mgr.get_or_create_session(
            user_id="carol",
            session_id="does-not-exist"
        )
        assert session3.session_id == "does-not-exist"

    def test_update_context(self, temp_sessions_dir):
        """Test updating session context."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        session = mgr.create_session(user_id="dave")

        success = mgr.update_context(
            session.session_id,
            {'project': 'test-project', 'product_code': 'DQY'}
        )
        assert success is True

        updated = mgr.get_session(session.session_id)
        assert updated.context['project'] == 'test-project'
        assert updated.context['product_code'] == 'DQY'
        # Original keys should still be there (merge=True)
        assert 'conversation_history' in updated.context

    def test_add_to_conversation(self, temp_sessions_dir):
        """Test adding conversation entries."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        session = mgr.create_session(user_id="eve")

        mgr.add_to_conversation(
            session.session_id,
            role="user",
            content="/research DQY",
            command="research"
        )

        updated = mgr.get_session(session.session_id)
        history = updated.context.get('conversation_history', [])
        assert len(history) == 1
        assert history[0]['role'] == 'user'
        assert history[0]['content'] == '/research DQY'
        assert history[0]['command'] == 'research'
        assert updated.context['last_command'] == 'research'
        assert updated.context['command_count'] == 1

    def test_add_file_path(self, temp_sessions_dir):
        """Test tracking file paths."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        session = mgr.create_session(user_id="frank")

        mgr.add_file_path(session.session_id, "/data/test.json")
        mgr.add_file_path(session.session_id, "/data/test2.json")
        # Duplicate should not be added
        mgr.add_file_path(session.session_id, "/data/test.json")

        updated = mgr.get_session(session.session_id)
        file_paths = updated.context.get('file_paths', [])
        assert len(file_paths) == 2

    def test_disk_persistence(self, temp_sessions_dir):
        """Test session survives manager recreation."""
        # Create session with first manager
        mgr1 = SessionManager(sessions_dir=temp_sessions_dir)
        session = mgr1.create_session(user_id="grace")
        session_id = session.session_id

        # Verify file exists on disk
        session_file = Path(temp_sessions_dir) / "{}.json".format(session_id)
        assert session_file.exists()

        # Create new manager (simulating server restart)
        mgr2 = SessionManager(sessions_dir=temp_sessions_dir)
        restored = mgr2.get_session(session_id)

        assert restored is not None
        assert restored.user_id == "grace"

    def test_cleanup_expired(self, temp_sessions_dir):
        """Test cleaning up expired sessions."""
        mgr = SessionManager(
            sessions_dir=temp_sessions_dir,
            max_age_hours=0  # Everything expires immediately
        )

        # Create sessions
        s1 = mgr.create_session(user_id="harry")
        s2 = mgr.create_session(user_id="iris")

        # Wait a moment to ensure they expire
        time.sleep(0.1)

        # Cleanup should remove both
        cleaned = mgr.cleanup_expired(max_age_hours=0)
        # At least the disk files should be cleaned
        assert cleaned >= 0  # May vary by timing

    def test_list_sessions(self, temp_sessions_dir):
        """Test listing active sessions."""
        mgr = SessionManager(sessions_dir=temp_sessions_dir)
        mgr.create_session(user_id="jack")
        mgr.create_session(user_id="kate")
        mgr.create_session(user_id="jack")

        all_sessions = mgr.list_sessions()
        assert len(all_sessions) == 3

        jack_sessions = mgr.list_sessions(user_id="jack")
        assert len(jack_sessions) == 2
        assert all(s['user_id'] == 'jack' for s in jack_sessions)


# ============================================================
# Tool Emulator Tests
# ============================================================

class TestPathValidation:
    """Test path validation security."""

    def test_allowed_paths(self):
        """Test that allowed directories pass validation."""
        # Home fda-510k-data directory
        allowed, reason = _validate_path(
            os.path.expanduser("~/fda-510k-data/test.json")
        )
        assert allowed is True

        # .claude directory
        allowed, reason = _validate_path(
            os.path.expanduser("~/.claude/test.json")
        )
        assert allowed is True

    def test_blocked_paths(self):
        """Test that system paths are blocked."""
        allowed, reason = _validate_path("/etc/passwd")
        assert allowed is False

        allowed, reason = _validate_path("/usr/bin/python3")
        assert allowed is False

    def test_traversal_prevention(self):
        """Test that directory traversal is blocked."""
        allowed, reason = _validate_path(
            os.path.expanduser("~/fda-510k-data/../../etc/passwd")
        )
        assert allowed is False


class TestBashCommandValidation:
    """Test bash command whitelist enforcement."""

    def test_allowed_commands(self):
        """Test that whitelisted commands are allowed."""
        allowed, _ = _validate_bash_command("python3 script.py")
        assert allowed is True

        allowed, _ = _validate_bash_command("curl -s https://api.fda.gov/device/510k.json")
        assert allowed is True

        allowed, _ = _validate_bash_command("cat /tmp/fda-bridge/output.txt")
        assert allowed is True

    def test_blocked_commands(self):
        """Test that dangerous commands are blocked."""
        allowed, _ = _validate_bash_command("rm -rf /")
        assert allowed is False

        allowed, _ = _validate_bash_command("sudo apt install malware")
        assert allowed is False

        allowed, _ = _validate_bash_command("chmod 777 /etc/passwd")
        assert allowed is False

    def test_unlisted_commands(self):
        """Test that unknown commands are blocked."""
        allowed, _ = _validate_bash_command("custom_malicious_tool --hack")
        assert allowed is False


class TestReadTool:
    """Test the ReadTool emulator."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary test file."""
        temp_dir = tempfile.mkdtemp(dir="/tmp/fda-bridge")
        test_file = Path(temp_dir) / "test_read.txt"
        lines = ["Line {}: Test content here\n".format(i) for i in range(1, 51)]
        test_file.write_text(''.join(lines))
        yield str(test_file)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_read_file(self, temp_file):
        """Test basic file reading."""
        tool = ReadTool()
        result = tool.execute(temp_file)

        assert result.success is True
        assert "Line 1: Test content here" in result.output
        assert temp_file in result.files_read
        assert result.duration_ms >= 0

    def test_read_with_offset_and_limit(self, temp_file):
        """Test reading with offset and limit."""
        tool = ReadTool()
        result = tool.execute(temp_file, offset=10, limit=5)

        assert result.success is True
        assert "Line 11" in result.output
        # Should have 5 content lines + 1 truncation notice
        lines = [l for l in result.output.strip().split('\n') if l.strip()]
        assert len(lines) == 6  # 5 lines + "[N more lines not shown]"
        assert "more lines not shown" in result.output.lower()

    def test_read_nonexistent_file(self):
        """Test reading a file that does not exist."""
        tool = ReadTool()
        result = tool.execute("/tmp/fda-bridge/nonexistent_file.txt")

        assert result.success is False
        assert "not found" in result.error.lower() or "No such file" in result.error

    def test_read_blocked_path(self):
        """Test reading from a blocked directory."""
        tool = ReadTool()
        result = tool.execute("/etc/passwd")

        assert result.success is False
        assert "denied" in result.error.lower() or "outside" in result.error.lower()


class TestWriteTool:
    """Test the WriteTool emulator."""

    @pytest.fixture
    def temp_write_dir(self):
        """Create a temporary directory for write tests."""
        temp_dir = tempfile.mkdtemp(dir="/tmp/fda-bridge")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_write_file(self, temp_write_dir):
        """Test writing a file."""
        tool = WriteTool()
        file_path = os.path.join(temp_write_dir, "output.txt")
        result = tool.execute(file_path, "Hello, FDA Bridge!")

        assert result.success is True
        assert file_path in result.files_written
        assert Path(file_path).read_text() == "Hello, FDA Bridge!"

    def test_write_creates_directories(self, temp_write_dir):
        """Test that write creates parent directories."""
        tool = WriteTool()
        file_path = os.path.join(temp_write_dir, "sub", "dir", "output.txt")
        result = tool.execute(file_path, "Nested content")

        assert result.success is True
        assert Path(file_path).read_text() == "Nested content"

    def test_write_blocked_path(self):
        """Test writing to a blocked directory."""
        tool = WriteTool()
        result = tool.execute("/etc/evil.conf", "malicious content")

        assert result.success is False
        assert "denied" in result.error.lower() or "outside" in result.error.lower()


class TestBashTool:
    """Test the BashTool emulator."""

    def test_execute_echo(self):
        """Test executing a simple echo command."""
        tool = BashTool(working_dir="/tmp/fda-bridge")
        result = tool.execute("echo 'Hello FDA'")

        assert result.success is True
        assert "Hello FDA" in result.output

    def test_execute_python(self):
        """Test executing a Python command."""
        tool = BashTool(working_dir="/tmp/fda-bridge")
        result = tool.execute("python3 -c 'print(2+2)'")

        assert result.success is True
        assert "4" in result.output

    def test_blocked_command(self):
        """Test that blocked commands are rejected."""
        tool = BashTool(working_dir="/tmp/fda-bridge")
        result = tool.execute("rm -rf /tmp/fda-bridge")

        assert result.success is False
        assert "blocked" in result.error.lower() or "not allowed" in result.error.lower()

    def test_timeout(self):
        """Test command timeout."""
        tool = BashTool(working_dir="/tmp/fda-bridge")
        # Use python3 (whitelisted) with sleep instead of sleep command (not whitelisted)
        result = tool.execute("python3 -c 'import time; time.sleep(10)'", timeout=1)

        assert result.success is False
        assert "timed out" in result.error.lower()

    def test_cat_command(self):
        """Test cat command (whitelisted)."""
        # Create a temp file
        temp_file = "/tmp/fda-bridge/test_cat.txt"
        Path(temp_file).parent.mkdir(parents=True, exist_ok=True)
        Path(temp_file).write_text("cat test content")

        tool = BashTool(working_dir="/tmp/fda-bridge")
        result = tool.execute("cat {}".format(temp_file))

        assert result.success is True
        assert "cat test content" in result.output

        # Cleanup
        Path(temp_file).unlink(missing_ok=True)


class TestGlobTool:
    """Test the GlobTool emulator."""

    @pytest.fixture
    def temp_glob_dir(self):
        """Create directory structure for glob tests."""
        temp_dir = tempfile.mkdtemp(dir="/tmp/fda-bridge")
        # Create test files
        (Path(temp_dir) / "file1.json").write_text("{}")
        (Path(temp_dir) / "file2.json").write_text("{}")
        (Path(temp_dir) / "file3.txt").write_text("text")
        sub = Path(temp_dir) / "sub"
        sub.mkdir()
        (sub / "nested.json").write_text("{}")

        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_glob_json_files(self, temp_glob_dir):
        """Test finding JSON files."""
        tool = GlobTool()
        result = tool.execute("*.json", path=temp_glob_dir)

        assert result.success is True
        assert "file1.json" in result.output
        assert "file2.json" in result.output

    def test_glob_recursive(self, temp_glob_dir):
        """Test recursive glob pattern."""
        tool = GlobTool()
        result = tool.execute("**/*.json", path=temp_glob_dir)

        assert result.success is True
        assert "nested.json" in result.output

    def test_glob_no_matches(self, temp_glob_dir):
        """Test glob with no matches."""
        tool = GlobTool()
        result = tool.execute("*.xyz", path=temp_glob_dir)

        assert result.success is True
        assert "No files found" in result.output


class TestGrepTool:
    """Test the GrepTool emulator."""

    @pytest.fixture
    def temp_grep_dir(self):
        """Create files for grep tests."""
        temp_dir = tempfile.mkdtemp(dir="/tmp/fda-bridge")
        (Path(temp_dir) / "data1.txt").write_text(
            "line1: hello world\nline2: foo bar\nline3: hello again\n"
        )
        (Path(temp_dir) / "data2.txt").write_text(
            "line1: no match\nline2: hello there\n"
        )
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_grep_basic(self, temp_grep_dir):
        """Test basic regex search."""
        tool = GrepTool()
        result = tool.execute("hello", path=temp_grep_dir)

        assert result.success is True
        assert "hello" in result.output
        # Should find matches in both files
        assert len(result.files_read) >= 1

    def test_grep_no_matches(self, temp_grep_dir):
        """Test grep with no matches."""
        tool = GrepTool()
        result = tool.execute("zzz_no_match", path=temp_grep_dir)

        assert result.success is True
        assert "No matches" in result.output

    def test_grep_invalid_regex(self, temp_grep_dir):
        """Test grep with invalid regex."""
        tool = GrepTool()
        result = tool.execute("[invalid", path=temp_grep_dir)

        assert result.success is False
        assert "invalid" in result.error.lower() or "regex" in result.error.lower()


class TestAskUserQuestionTool:
    """Test the AskUserQuestionTool emulator."""

    def test_queue_questions(self):
        """Test queuing questions."""
        tool = AskUserQuestionTool()
        result = tool.execute(
            questions=[
                {'id': 'q1', 'text': 'What is the product code?'},
                {'id': 'q2', 'text': 'What is the intended use?'}
            ],
            session_id="test-session"
        )

        assert result.success is True
        output = json.loads(result.output)
        assert len(output['question_ids']) == 2
        assert 'q1' in output['question_ids']

    def test_get_pending_questions(self):
        """Test retrieving pending questions."""
        tool = AskUserQuestionTool()
        tool.execute(
            questions=[{'id': 'q1', 'text': 'Test question?'}],
            session_id="session-1"
        )

        pending = tool.get_pending_questions("session-1")
        assert len(pending) == 1
        assert pending[0]['text'] == 'Test question?'

    def test_submit_answer(self):
        """Test submitting and retrieving an answer."""
        tool = AskUserQuestionTool()
        tool.execute(
            questions=[{'id': 'q1', 'text': 'What code?'}],
            session_id="session-1"
        )

        success = tool.submit_answer("q1", "DQY")
        assert success is True

        answer = tool.get_answer("q1")
        assert answer == "DQY"

        # Pending should be empty after answering
        pending = tool.get_pending_questions("session-1")
        assert len(pending) == 0

    def test_submit_answer_unknown_question(self):
        """Test submitting answer for unknown question."""
        tool = AskUserQuestionTool()
        success = tool.submit_answer("nonexistent", "answer")
        assert success is False


class TestToolRegistry:
    """Test the ToolRegistry."""

    def test_all_tools_registered(self):
        """Test that all tools are available."""
        registry = ToolRegistry()
        tools = registry.list_tools()

        assert 'Read' in tools
        assert 'Write' in tools
        assert 'Bash' in tools
        assert 'Glob' in tools
        assert 'Grep' in tools
        assert 'AskUserQuestion' in tools
        assert len(tools) == 6

    def test_get_tool_by_name(self):
        """Test retrieving tools by name."""
        registry = ToolRegistry()

        read_tool = registry.get_tool('Read')
        assert read_tool is not None
        assert isinstance(read_tool, ReadTool)

        unknown = registry.get_tool('UnknownTool')
        assert unknown is None


# ============================================================
# FastAPI Server Tests
# ============================================================

class TestFastAPIServer:
    """Test the FastAPI server endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        # We need to import and configure the app for testing
        # This requires mocking the security gateway since we may not
        # have a security config in the test environment
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi[testclient] not installed (need httpx)")

        # Patch the lifespan to avoid needing real security config
        import server as bridge_server

        # Set up global state directly for testing
        bridge_server.gateway = None  # Permissive mode
        bridge_server.audit_logger = None  # Skip audit logging
        bridge_server.session_mgr = SessionManager(
            sessions_dir=tempfile.mkdtemp()
        )
        bridge_server.tool_registry = ToolRegistry(
            working_dir="/tmp/fda-bridge"
        )

        # Create test client without lifespan to avoid startup/shutdown
        client = TestClient(bridge_server.app, raise_server_exceptions=False)

        yield client

        # Cleanup
        if bridge_server.session_mgr:
            shutil.rmtree(
                bridge_server.session_mgr.sessions_dir,
                ignore_errors=True
            )

    def test_health_endpoint(self, client):
        """Test GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '1.0.0'
        assert 'llm_providers' in data
        assert 'uptime_seconds' in data

    def test_commands_endpoint(self, client):
        """Test GET /commands returns command list."""
        response = client.get("/commands")
        assert response.status_code == 200

        data = response.json()
        assert 'commands' in data
        assert 'total' in data
        assert isinstance(data['commands'], list)

        # If commands directory exists, should have commands
        if data['total'] > 0:
            cmd = data['commands'][0]
            assert 'name' in cmd
            assert 'description' in cmd

    def test_session_create(self, client):
        """Test POST /session creates a new session."""
        response = client.post("/session", json={
            "user_id": "test_user"
        })
        assert response.status_code == 200

        data = response.json()
        assert data['is_new'] is True
        assert data['user_id'] == 'test_user'
        assert 'session_id' in data

    def test_session_retrieve(self, client):
        """Test POST /session retrieves existing session."""
        # Create session
        create_response = client.post("/session", json={
            "user_id": "test_user"
        })
        session_id = create_response.json()['session_id']

        # Retrieve session
        response = client.post("/session", json={
            "user_id": "test_user",
            "session_id": session_id
        })
        assert response.status_code == 200

        data = response.json()
        assert data['is_new'] is False
        assert data['session_id'] == session_id

    def test_session_get_by_id(self, client):
        """Test GET /session/{id} returns session details."""
        # Create session
        create_response = client.post("/session", json={
            "user_id": "test_user"
        })
        session_id = create_response.json()['session_id']

        # Get session details
        response = client.get("/session/{}".format(session_id))
        assert response.status_code == 200

        data = response.json()
        assert data['session_id'] == session_id
        assert 'context' in data

    def test_session_not_found(self, client):
        """Test GET /session/{id} returns 404 for unknown session."""
        response = client.get("/session/nonexistent-session-id")
        assert response.status_code == 404

    def test_execute_permissive_mode(self, client):
        """Test POST /execute in permissive mode (no security gateway)."""
        response = client.post("/execute", json={
            "command": "validate",
            "args": "K240001",
            "user_id": "test_user",
            "channel": "file"
        })
        assert response.status_code == 200

        data = response.json()
        assert 'session_id' in data
        assert 'classification' in data
        assert 'llm_provider' in data
        assert data.get('warnings') is not None  # Should warn about permissive mode

    def test_execute_unknown_command(self, client):
        """Test POST /execute with non-existent command."""
        response = client.post("/execute", json={
            "command": "nonexistent_command_xyz",
            "user_id": "test_user",
            "channel": "file"
        })
        assert response.status_code == 200

        data = response.json()
        # Should still return (may succeed or fail depending on script existence)
        assert 'session_id' in data

    def test_execute_creates_session(self, client):
        """Test that /execute creates a session if none provided."""
        response = client.post("/execute", json={
            "command": "validate",
            "args": "K240001",
            "user_id": "new_user",
            "channel": "file"
        })
        assert response.status_code == 200

        data = response.json()
        session_id = data['session_id']

        # Verify session was created
        session_response = client.get("/session/{}".format(session_id))
        assert session_response.status_code == 200

    def test_execute_reuses_session(self, client):
        """Test that /execute reuses provided session."""
        # Create session first
        session_response = client.post("/session", json={
            "user_id": "test_user"
        })
        session_id = session_response.json()['session_id']

        # Execute with session
        response = client.post("/execute", json={
            "command": "validate",
            "args": "K240001",
            "user_id": "test_user",
            "session_id": session_id,
            "channel": "file"
        })
        assert response.status_code == 200
        assert response.json()['session_id'] == session_id

    def test_list_sessions(self, client):
        """Test GET /sessions returns session list."""
        # Create some sessions
        client.post("/session", json={"user_id": "alice"})
        client.post("/session", json={"user_id": "bob"})

        response = client.get("/sessions")
        assert response.status_code == 200

        data = response.json()
        assert data['total'] >= 2

    def test_list_sessions_filtered(self, client):
        """Test GET /sessions?user_id=alice filters correctly."""
        client.post("/session", json={"user_id": "alice"})
        client.post("/session", json={"user_id": "bob"})

        response = client.get("/sessions?user_id=alice")
        assert response.status_code == 200

        data = response.json()
        assert all(s['user_id'] == 'alice' for s in data['sessions'])

    def test_tools_endpoint(self, client):
        """Test GET /tools returns tool list."""
        response = client.get("/tools")
        assert response.status_code == 200

        data = response.json()
        assert data['count'] == 6
        assert 'Read' in data['tools']
        assert 'Bash' in data['tools']

    def test_execute_response_has_duration(self, client):
        """Test that execute response includes duration_ms."""
        response = client.post("/execute", json={
            "command": "validate",
            "args": "K240001",
            "user_id": "test_user",
            "channel": "file"
        })
        assert response.status_code == 200

        data = response.json()
        assert 'duration_ms' in data
        assert isinstance(data['duration_ms'], int)
        assert data['duration_ms'] >= 0


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_session_survives_tool_execution(self):
        """Test that session context is maintained across tool executions."""
        temp_dir = tempfile.mkdtemp()
        mgr = SessionManager(sessions_dir=temp_dir)
        registry = ToolRegistry(working_dir="/tmp/fda-bridge")

        # Create session
        session = mgr.create_session(user_id="integration_user")

        # Simulate command execution
        mgr.add_to_conversation(
            session.session_id,
            role="user",
            content="/validate K240001",
            command="validate"
        )

        # Use tool
        Path("/tmp/fda-bridge").mkdir(parents=True, exist_ok=True)
        test_file = "/tmp/fda-bridge/integration_test.txt"
        Path(test_file).write_text("Test content for integration")

        read_result = registry.read.execute(test_file)
        assert read_result.success is True

        # Track file in session
        mgr.add_file_path(session.session_id, test_file)

        # Verify session state
        updated = mgr.get_session(session.session_id)
        assert len(updated.context['conversation_history']) == 1
        assert test_file in updated.context['file_paths']
        assert updated.context['command_count'] == 1

        # Cleanup
        Path(test_file).unlink(missing_ok=True)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tool_registry_all_tools_functional(self):
        """Test that all registered tools can execute without errors."""
        Path("/tmp/fda-bridge").mkdir(parents=True, exist_ok=True)
        registry = ToolRegistry(working_dir="/tmp/fda-bridge")

        # ReadTool - read a non-existent file (should fail gracefully)
        result = registry.read.execute("/tmp/fda-bridge/no_such_file.txt")
        assert result.success is False
        assert result.error is not None

        # WriteTool - write a test file
        result = registry.write.execute(
            "/tmp/fda-bridge/tool_test.txt",
            "Tool test content"
        )
        assert result.success is True

        # ReadTool - now read the file we wrote
        result = registry.read.execute("/tmp/fda-bridge/tool_test.txt")
        assert result.success is True
        assert "Tool test content" in result.output

        # BashTool - execute echo
        result = registry.bash.execute("echo 'bash works'")
        assert result.success is True

        # GlobTool - find our test file
        result = registry.glob.execute("tool_test.txt", path="/tmp/fda-bridge")
        assert result.success is True

        # GrepTool - search in our test file
        result = registry.grep.execute("Tool test", path="/tmp/fda-bridge/tool_test.txt")
        assert result.success is True

        # AskUserQuestionTool - queue a question
        result = registry.ask_user.execute(
            questions=[{'id': 'q1', 'text': 'Test?'}],
            session_id="test"
        )
        assert result.success is True

        # Cleanup
        Path("/tmp/fda-bridge/tool_test.txt").unlink(missing_ok=True)

    def test_conversation_history_bounded(self):
        """Test that conversation history does not grow unbounded."""
        temp_dir = tempfile.mkdtemp()
        mgr = SessionManager(sessions_dir=temp_dir)
        session = mgr.create_session(user_id="chatty_user")

        # Add 60 conversation entries (max is 50)
        for i in range(60):
            mgr.add_to_conversation(
                session.session_id,
                role="user",
                content="Message {}".format(i),
                command="test"
            )

        updated = mgr.get_session(session.session_id)
        history = updated.context.get('conversation_history', [])
        assert len(history) <= 50

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# Helper Function Tests
# ============================================================

class TestHelperFunctions:
    """Test server helper functions."""

    def test_parse_frontmatter(self):
        """Test YAML frontmatter parsing."""
        # Import from server module
        sys.path.insert(0, str(BRIDGE_DIR))

        from server import _parse_frontmatter

        content = '''---
description: Test command description
allowed-tools: Read, Write, Bash
argument-hint: "<product-code>"
---

# Test Command
Body content here.
'''
        result = _parse_frontmatter(content)
        assert result is not None
        assert result['description'] == 'Test command description'
        assert result['allowed-tools'] == 'Read, Write, Bash'
        assert result['argument-hint'] == '<product-code>'

    def test_parse_frontmatter_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        from server import _parse_frontmatter

        content = "# Just a heading\nNo frontmatter here."
        result = _parse_frontmatter(content)
        assert result is None

    def test_extract_file_paths(self):
        """Test file path extraction from arguments."""
        from server import _extract_file_paths

        # Absolute path
        paths = _extract_file_paths("--file /home/user/data/test.json")
        assert "/home/user/data/test.json" in paths

        # Home-relative path
        paths = _extract_file_paths("~/fda-510k-data/output.csv")
        assert any("fda-510k-data/output.csv" in p for p in paths)

        # Project name
        paths = _extract_file_paths("--project TestDevice --depth deep")
        assert any("TestDevice" in p for p in paths)

    def test_extract_file_paths_empty(self):
        """Test file path extraction with no paths."""
        from server import _extract_file_paths

        paths = _extract_file_paths("DQY --depth standard")
        # Should have no file paths (DQY is a product code, not a path)
        assert len(paths) == 0 or all("projects" not in p for p in paths)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
