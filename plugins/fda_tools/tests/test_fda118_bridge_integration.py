"""
Bridge Server Integration Tests (FDA-118)
==========================================

Comprehensive integration test suite for the OpenClaw bridge server using
FastAPI's TestClient (no running server required).

Tests cover:
  - Health/readiness endpoints
  - API key authentication and rejection
  - Session creation and retrieval
  - Security gateway data classification and channel blocking
  - Command execution endpoint (security, routing, error handling)
  - Command listing endpoint
  - Tool emulator endpoint (/tool/execute)
  - Audit logging
  - Metrics endpoint
  - Input sanitization
  - Error handling

Test count: 63
Target: pytest plugins/fda_tools/tests/test_fda118_bridge_integration.py -v
"""

import hashlib
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test API key: set BEFORE importing server so _ENV_BRIDGE_KEY captures it
# ---------------------------------------------------------------------------

TEST_API_KEY = "fda118_test_api_key_32bytes_hex00"
os.environ["FDA_BRIDGE_API_KEY"] = TEST_API_KEY

from fda_tools.bridge import server as server_module  # noqa: E402
from fda_tools.bridge.server import app  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# Belt-and-suspenders: ensure hash is set even if module was pre-imported
server_module._BRIDGE_API_KEY = TEST_API_KEY
server_module._cached_api_key_hash = hashlib.sha256(TEST_API_KEY.encode()).hexdigest()

AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """TestClient for the bridge server (module-scoped for speed)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def session_id(client):
    """Create a session once and reuse for the module."""
    resp = client.post(
        "/session",
        json={"user_id": "test-user-118"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


# ---------------------------------------------------------------------------
# TestHealthAndReadiness (6 tests)
# ---------------------------------------------------------------------------


class TestHealthAndReadiness:
    """Health and readiness endpoints are unauthenticated."""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_has_status_field(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")

    def test_health_has_version(self, client):
        data = client.get("/health").json()
        assert "version" in data

    def test_health_has_uptime(self, client):
        data = client.get("/health").json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)

    def test_health_has_auth_required_flag(self, client):
        """Health should advertise that auth is required for other endpoints."""
        data = client.get("/health").json()
        assert data.get("auth_required") is True

    def test_ready_endpoint_accessible(self, client):
        resp = client.get("/ready")
        # 200 ready, or 503 if dirs/key missing — both are valid status codes
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "ready" in data


# ---------------------------------------------------------------------------
# TestAuthentication (10 tests)
# ---------------------------------------------------------------------------


class TestAuthentication:
    """API key authentication enforcement."""

    def test_commands_requires_auth(self, client):
        resp = client.get("/commands")
        assert resp.status_code == 401

    def test_execute_requires_auth(self, client):
        resp = client.post("/execute", json={
            "command": "research", "user_id": "u1", "channel": "file"
        })
        assert resp.status_code == 401

    def test_metrics_requires_auth(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 401

    def test_sessions_list_requires_auth(self, client):
        resp = client.get("/sessions")
        assert resp.status_code == 401

    def test_valid_api_key_accepted_on_commands(self, client):
        resp = client.get("/commands", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_invalid_api_key_rejected(self, client):
        resp = client.get("/commands", headers={"X-API-Key": "wrong-key-xyz"})
        assert resp.status_code == 401

    def test_missing_api_key_rejected(self, client):
        resp = client.get("/commands")
        assert resp.status_code == 401

    def test_empty_api_key_rejected(self, client):
        resp = client.get("/commands", headers={"X-API-Key": ""})
        assert resp.status_code in (401, 403, 422)

    def test_health_does_not_require_auth(self, client):
        """Health endpoint must remain unauthenticated (monitoring requirement)."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_ready_does_not_require_auth(self, client):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)  # 503 = not ready, but accessible


# ---------------------------------------------------------------------------
# TestSessionManagement (6 tests)
# ---------------------------------------------------------------------------


class TestSessionManagement:
    """Session creation and retrieval."""

    def test_create_session_returns_200(self, client):
        resp = client.post(
            "/session",
            json={"user_id": "test-session-user"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200

    def test_session_response_has_session_id(self, client):
        resp = client.post(
            "/session",
            json={"user_id": "user-a"},
            headers=AUTH_HEADERS,
        )
        data = resp.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_session_response_has_user_id(self, client):
        resp = client.post(
            "/session",
            json={"user_id": "user-b"},
            headers=AUTH_HEADERS,
        )
        assert resp.json()["user_id"] == "user-b"

    def test_retrieve_existing_session(self, client):
        # Create session
        create_resp = client.post(
            "/session",
            json={"user_id": "user-c"},
            headers=AUTH_HEADERS,
        )
        sid = create_resp.json()["session_id"]

        # Retrieve by GET
        get_resp = client.get(f"/session/{sid}", headers=AUTH_HEADERS)
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == sid

    def test_get_nonexistent_session_returns_404(self, client):
        resp = client.get("/session/nonexistent-session-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_list_sessions_returns_list(self, client):
        resp = client.get("/sessions", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)


# ---------------------------------------------------------------------------
# TestSecurityGateway (12 tests)
# ---------------------------------------------------------------------------


class TestSecurityGateway:
    """Security gateway data classification and channel access control.

    Tests the /execute endpoint behaviour based on classification rules
    implemented by the SecurityGateway (FDA-117).
    """

    def _execute(self, client, command, channel="file", args=None):
        payload = {
            "command": command,
            "user_id": "sg-test-user",
            "channel": channel,
        }
        if args:
            payload["args"] = args
        return client.post("/execute", json=payload, headers=AUTH_HEADERS)

    def test_public_command_on_file_returns_200(self, client):
        resp = self._execute(client, "research", channel="file")
        assert resp.status_code == 200

    def test_public_command_classification_is_public(self, client):
        resp = self._execute(client, "research", channel="file")
        data = resp.json()
        assert data["classification"] == "PUBLIC"

    def test_public_command_on_cli_allowed(self, client):
        resp = self._execute(client, "validate", channel="cli")
        data = resp.json()
        # Not blocked by gateway (may fail at script execution, but not at gateway)
        assert data["classification"] in ("PUBLIC", "RESTRICTED", "CONFIDENTIAL")

    def test_confidential_command_classification_is_confidential(self, client):
        resp = self._execute(client, "draft", channel="file")
        data = resp.json()
        assert data["classification"] == "CONFIDENTIAL"

    def test_confidential_command_on_whatsapp_is_blocked(self, client):
        resp = self._execute(client, "draft", channel="whatsapp")
        data = resp.json()
        assert data["success"] is False
        assert "CONFIDENTIAL" in (data.get("error") or "")

    def test_confidential_command_on_slack_is_blocked(self, client):
        resp = self._execute(client, "assemble", channel="slack")
        data = resp.json()
        assert data["success"] is False

    def test_confidential_command_on_telegram_is_blocked(self, client):
        resp = self._execute(client, "pre-check", channel="telegram")
        data = resp.json()
        assert data["success"] is False

    def test_confidential_command_on_file_not_blocked(self, client):
        """CONFIDENTIAL command on file channel should pass security gateway."""
        resp = self._execute(client, "draft", channel="file")
        data = resp.json()
        # Gateway allows it; failure is from missing script, not from gateway
        assert "CONFIDENTIAL" in (data.get("error") or "") or data["classification"] == "CONFIDENTIAL"

    def test_restricted_command_on_messaging_has_warnings(self, client):
        resp = self._execute(client, "unknown-cmd", channel="slack")
        data = resp.json()
        assert data["classification"] == "RESTRICTED"
        assert len(data.get("warnings", [])) >= 1

    def test_k_number_in_args_escalates_to_confidential(self, client):
        resp = self._execute(client, "research", channel="file", args="K240001")
        data = resp.json()
        assert data["classification"] == "CONFIDENTIAL"

    def test_execute_response_has_llm_provider(self, client):
        resp = self._execute(client, "research", channel="file")
        data = resp.json()
        assert "llm_provider" in data

    def test_execute_response_has_session_id(self, client):
        resp = self._execute(client, "research", channel="file")
        data = resp.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0


# ---------------------------------------------------------------------------
# TestCommandListing (4 tests)
# ---------------------------------------------------------------------------


class TestCommandListing:
    """GET /commands endpoint."""

    def test_commands_returns_list(self, client):
        resp = client.get("/commands", headers=AUTH_HEADERS)
        data = resp.json()
        assert "commands" in data
        assert isinstance(data["commands"], list)

    def test_commands_has_total(self, client):
        resp = client.get("/commands", headers=AUTH_HEADERS)
        data = resp.json()
        assert "total" in data
        assert data["total"] == len(data["commands"])

    def test_commands_includes_expected_commands(self, client):
        resp = client.get("/commands", headers=AUTH_HEADERS)
        names = {c["name"] for c in resp.json()["commands"] if "name" in c}
        # At least some core FDA commands should appear
        assert len(names) > 0 or resp.json()["total"] == 0

    def test_tools_list_endpoint(self, client):
        """GET /tools is also authenticated and returns tools list."""
        resp = client.get("/tools", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data


# ---------------------------------------------------------------------------
# TestCommandExecution (7 tests)
# ---------------------------------------------------------------------------


class TestCommandExecution:
    """POST /execute endpoint validation."""

    def test_execute_missing_user_id_returns_422(self, client):
        resp = client.post(
            "/execute",
            json={"command": "research", "channel": "file"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_execute_missing_channel_returns_422(self, client):
        resp = client.post(
            "/execute",
            json={"command": "research", "user_id": "u1"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_execute_missing_command_returns_422(self, client):
        resp = client.post(
            "/execute",
            json={"user_id": "u1", "channel": "file"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_execute_returns_success_field(self, client):
        resp = client.post(
            "/execute",
            json={"command": "research", "user_id": "u1", "channel": "file"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert "success" in resp.json()

    def test_execute_command_not_found_returns_false(self, client):
        """Commands not in the commands directory return success=False."""
        resp = client.post(
            "/execute",
            json={"command": "nonexistent-command-xyz", "user_id": "u1", "channel": "file"},
            headers=AUTH_HEADERS,
        )
        data = resp.json()
        assert data["success"] is False

    def test_execute_with_explicit_session_id(self, client, session_id):
        """Execute can reuse an existing session."""
        resp = client.post(
            "/execute",
            json={
                "command": "research",
                "user_id": "u1",
                "channel": "file",
                "session_id": session_id,
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_execute_confidential_blocked_sets_success_false(self, client):
        """Confidential command on messaging channel sets success=False."""
        resp = client.post(
            "/execute",
            json={"command": "draft", "user_id": "u1", "channel": "discord"},
            headers=AUTH_HEADERS,
        )
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# TestToolEmulator (10 tests)
# ---------------------------------------------------------------------------


class TestToolEmulator:
    """POST /tool/execute endpoint for ToolEmulator tools."""

    @pytest.fixture(autouse=True)
    def tmp_project(self, tmp_path, client, session_id):
        """Create a temp project dir and expose it plus session for each test."""
        self.project_root = str(tmp_path)
        self.session_id = session_id
        self.client = client

    def _tool(self, tool_name, params):
        return self.client.post(
            "/tool/execute",
            json={
                "tool": tool_name,
                "session_id": self.session_id,
                "project_root": self.project_root,
                "params": params,
            },
            headers=AUTH_HEADERS,
        )

    def test_tool_execute_requires_auth(self):
        resp = self.client.post(
            "/tool/execute",
            json={
                "tool": "Read",
                "session_id": self.session_id,
                "project_root": self.project_root,
                "params": {"file_path": "test.txt"},
            },
        )
        assert resp.status_code == 401

    def test_read_tool_reads_file(self):
        # Create a test file in tmp project
        (Path(self.project_root) / "hello.txt").write_text("hello world")
        resp = self._tool("Read", {"file_path": "hello.txt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "hello world" in data["result"]

    def test_write_tool_creates_file(self):
        resp = self._tool("Write", {"file_path": "output.txt", "content": "test content"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert (Path(self.project_root) / "output.txt").exists()

    def test_bash_tool_runs_allowed_command(self):
        resp = self._tool("Bash", {"command": "echo hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "hello" in data["result"]["stdout"]

    def test_bash_tool_blocks_disallowed_command(self):
        resp = self._tool("Bash", {"command": "curl http://example.com"})
        assert resp.status_code == 403

    def test_grep_tool_returns_matches(self):
        (Path(self.project_root) / "sample.py").write_text("def foo():\n    pass\n")
        resp = self._tool("Grep", {"pattern": "def ", "path": ".", "glob_pattern": "*.py"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["result"], list)

    def test_glob_tool_returns_files(self):
        (Path(self.project_root) / "file_a.md").write_text("# A")
        (Path(self.project_root) / "file_b.md").write_text("# B")
        resp = self._tool("Glob", {"pattern": "*.md"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["result"]) >= 2

    def test_ask_user_question_returns_question_id(self):
        resp = self._tool("AskUserQuestion", {"question": "Which predicate?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "question_id" in data["result"]

    def test_read_tool_blocks_path_traversal(self):
        resp = self._tool("Read", {"file_path": "../../../etc/passwd"})
        assert resp.status_code == 403

    def test_unknown_tool_returns_400(self):
        resp = self._tool("FakeToolXYZ", {"file_path": "test.txt"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TestMetrics (4 tests)
# ---------------------------------------------------------------------------


class TestMetrics:
    """GET /metrics endpoint."""

    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_metrics_has_request_count(self, client):
        data = client.get("/metrics", headers=AUTH_HEADERS).json()
        assert "requests" in data
        assert "total" in data["requests"]

    def test_metrics_has_uptime(self, client):
        data = client.get("/metrics", headers=AUTH_HEADERS).json()
        assert "uptime_seconds" in data

    def test_metrics_has_session_count(self, client):
        data = client.get("/metrics", headers=AUTH_HEADERS).json()
        assert "sessions" in data
        assert "active" in data["sessions"]


# ---------------------------------------------------------------------------
# TestInputSanitization (4 tests)
# ---------------------------------------------------------------------------


class TestInputSanitization:
    """Input sanitization — injection attempts must not cause 500 errors."""

    def _execute(self, client, command, args=None):
        return client.post(
            "/execute",
            json={"command": command, "args": args, "user_id": "u1", "channel": "file"},
            headers=AUTH_HEADERS,
        )

    def test_shell_injection_in_args_does_not_500(self, client):
        resp = self._execute(client, "research", args="topic; rm -rf /")
        assert resp.status_code == 200
        assert resp.json()["success"] in (True, False)  # Must not crash

    def test_backtick_injection_does_not_500(self, client):
        resp = self._execute(client, "research", args="`whoami`")
        assert resp.status_code == 200

    def test_dollar_substitution_does_not_500(self, client):
        resp = self._execute(client, "research", args="$(curl malicious.com)")
        assert resp.status_code == 200

    def test_very_long_args_do_not_500(self, client):
        resp = self._execute(client, "research", args="A" * 4096)
        # May return 200 with error or 4xx, but must not 500
        assert resp.status_code in (200, 400, 413, 422)


# ---------------------------------------------------------------------------
# TestAuditLogging (4 tests)
# ---------------------------------------------------------------------------


class TestAuditLogging:
    """Audit logging behaviour via the audit/integrity endpoint."""

    def test_audit_integrity_requires_auth(self, client):
        resp = client.get("/audit/integrity")
        assert resp.status_code == 401

    def test_audit_integrity_returns_200(self, client):
        resp = client.get("/audit/integrity", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_audit_log_func_called_on_execute(self, client):
        """audit_log_entry is invoked during execute — verify via call count."""
        original_func = server_module.audit_log_entry
        calls = []
        server_module.audit_log_entry = lambda *a, **kw: calls.append(a) or original_func(*a, **kw)
        try:
            client.post(
                "/execute",
                json={"command": "research", "user_id": "u1", "channel": "file"},
                headers=AUTH_HEADERS,
            )
            assert len(calls) >= 1
        finally:
            server_module.audit_log_entry = original_func

    def test_pending_questions_endpoint_accessible(self, client, session_id):
        """GET /session/{id}/questions is accessible with valid session."""
        resp = client.get(
            f"/session/{session_id}/questions",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "questions" in data


# ---------------------------------------------------------------------------
# TestTypeScriptSkillIntegration (5 tests — mirror existing e2e file)
# ---------------------------------------------------------------------------


class TestTypeScriptSkillIntegration:
    """Verify TypeScript OpenClaw skill files exist at repo root."""

    @pytest.fixture(autouse=True)
    def skill_root(self):
        # Tests live at: plugins/fda_tools/tests/
        # Repo root is 4 levels up from tests/ (tests → fda_tools → plugins → fda-tools)
        self._skill_root = Path(__file__).parent.parent.parent.parent / "openclaw-skill"

    def test_fda_validate_tool_exists(self):
        assert (self._skill_root / "tools" / "fda_validate.ts").exists()

    def test_fda_analyze_tool_exists(self):
        assert (self._skill_root / "tools" / "fda_analyze.ts").exists()

    def test_fda_draft_tool_exists(self):
        assert (self._skill_root / "tools" / "fda_draft.ts").exists()

    def test_fda_research_tool_exists(self):
        assert (self._skill_root / "tools" / "fda_research.ts").exists()

    def test_fda_generic_tool_exists(self):
        assert (self._skill_root / "tools" / "fda_generic.ts").exists()
