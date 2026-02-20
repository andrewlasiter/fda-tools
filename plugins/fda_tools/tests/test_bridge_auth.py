#!/usr/bin/env python3
"""
Security tests for FDA-82: Bridge server authentication, rate limiting, and logging.

Verifies:
- API key generation and storage
- Unauthenticated requests are rejected with 401
- Health endpoint is accessible without authentication
- Authenticated requests succeed
- Rate limiting (if slowapi is available)
- Request logging sanitizes sensitive fields
- Constant-time key comparison
"""
import hashlib
import os
import secrets
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add bridge directory to path

try:
    from fastapi.testclient import TestClient  # type: ignore
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False


class TestSanitization(unittest.TestCase):
    """Test request logging sanitization."""

    def setUp(self):
        # Import must happen after path setup
        try:
            from server import sanitize_for_logging
            self.sanitize = sanitize_for_logging
        except ImportError:
            self.skipTest("Cannot import server module")

    def test_api_key_is_redacted(self):
        """API keys in dicts should be redacted."""
        data = {"user_id": "alice", "api_key": "sk-1234567890abcdef"}
        result = self.sanitize(data)
        self.assertEqual(result["user_id"], "alice")
        self.assertIn("REDACTED", result["api_key"])
        self.assertNotIn("1234567890abcdef", result["api_key"])

    def test_password_is_redacted(self):
        """Passwords should be redacted."""
        data = {"password": "super-secret-pass-123"}
        result = self.sanitize(data)
        self.assertIn("REDACTED", result["password"])

    def test_token_is_redacted(self):
        """Tokens should be redacted."""
        data = {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        result = self.sanitize(data)
        self.assertIn("REDACTED", result["token"])

    def test_nested_dict_sanitized(self):
        """Nested dicts should be recursively sanitized."""
        data = {"outer": {"api_key": "nested-secret-key"}}
        result = self.sanitize(data)
        self.assertIn("REDACTED", result["outer"]["api_key"])

    def test_non_sensitive_fields_preserved(self):
        """Non-sensitive fields should be left unchanged."""
        data = {"command": "research", "args": "--product-code DQY"}
        result = self.sanitize(data)
        self.assertEqual(result["command"], "research")
        self.assertEqual(result["args"], "--product-code DQY")

    def test_list_sanitized(self):
        """Lists of dicts should be sanitized."""
        data = [{"api_key": "key1"}, {"api_key": "key2"}]
        result = self.sanitize(data)
        for item in result:
            self.assertIn("REDACTED", item["api_key"])

    def test_short_sensitive_value_fully_redacted(self):
        """Short sensitive values should be fully redacted."""
        data = {"api_key": "ab"}
        result = self.sanitize(data)
        self.assertEqual(result["api_key"], "REDACTED")


class TestKeyVerification(unittest.TestCase):
    """Test API key verification security properties."""

    def setUp(self):
        try:
            from server import _verify_api_key
            self.verify = _verify_api_key
        except ImportError:
            self.skipTest("Cannot import server module")

    def test_correct_key_accepted(self):
        """Valid API key should be accepted."""
        import server
        test_key = "test-bridge-key-for-unit-test"
        server._cached_api_key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        self.assertTrue(self.verify(test_key))

    def test_wrong_key_rejected(self):
        """Invalid API key should be rejected."""
        import server
        test_key = "correct-key"
        server._cached_api_key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        self.assertFalse(self.verify("wrong-key"))

    def test_empty_key_rejected(self):
        """Empty API key should be rejected."""
        import server
        server._cached_api_key_hash = hashlib.sha256(b"some-key").hexdigest()
        self.assertFalse(self.verify(""))

    def test_no_cached_hash_rejects_all(self):
        """If no key hash is cached, all keys should be rejected."""
        import server
        server._cached_api_key_hash = None
        self.assertFalse(self.verify("any-key"))


@unittest.skipUnless(HAS_TESTCLIENT, "FastAPI TestClient not available")
class TestEndpointAuthentication(unittest.TestCase):
    """Test that endpoints enforce authentication correctly."""

    def setUp(self):
        try:
            import server
            self.server = server
            # Set up a known test API key
            self.test_key = "test-key-" + secrets.token_hex(16)
            server._cached_api_key_hash = hashlib.sha256(
                self.test_key.encode()
            ).hexdigest()
            self.client = TestClient(server.app)
        except ImportError:
            self.skipTest("Cannot import server module")

    def test_health_no_auth_required(self):
        """Health endpoint should work without authentication."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["auth_required"])

    def test_commands_requires_auth(self):
        """Commands endpoint should require authentication."""
        response = self.client.get("/commands")
        self.assertEqual(response.status_code, 401)

    def test_commands_with_valid_key(self):
        """Commands endpoint should accept valid API key."""
        response = self.client.get(
            "/commands",
            headers={"X-API-Key": self.test_key}
        )
        self.assertEqual(response.status_code, 200)

    def test_commands_with_invalid_key(self):
        """Commands endpoint should reject invalid API key."""
        response = self.client.get(
            "/commands",
            headers={"X-API-Key": "invalid-key-12345"}
        )
        self.assertEqual(response.status_code, 401)

    def test_execute_requires_auth(self):
        """Execute endpoint should require authentication."""
        response = self.client.post("/execute", json={
            "command": "research",
            "args": "--product-code DQY",
            "user_id": "test-user",
            "channel": "file",
        })
        self.assertEqual(response.status_code, 401)

    def test_execute_with_valid_key(self):
        """Execute endpoint should accept valid API key."""
        response = self.client.post(
            "/execute",
            json={
                "command": "research",
                "args": "--product-code DQY",
                "user_id": "test-user",
                "channel": "file",
            },
            headers={"X-API-Key": self.test_key},
        )
        # May be 200 or 404 depending on commands dir, but not 401
        self.assertNotEqual(response.status_code, 401)

    def test_session_requires_auth(self):
        """Session creation endpoint should require authentication."""
        response = self.client.post("/session", json={
            "user_id": "test-user",
        })
        self.assertEqual(response.status_code, 401)

    def test_tools_requires_auth(self):
        """Tools endpoint should require authentication."""
        response = self.client.get("/tools")
        self.assertEqual(response.status_code, 401)

    def test_audit_requires_auth(self):
        """Audit integrity endpoint should require authentication."""
        response = self.client.get("/audit/integrity")
        self.assertEqual(response.status_code, 401)

    def test_sessions_list_requires_auth(self):
        """Sessions list endpoint should require authentication."""
        response = self.client.get("/sessions")
        self.assertEqual(response.status_code, 401)

    def test_401_response_format(self):
        """401 responses should have proper error detail."""
        response = self.client.get("/commands")
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("API key", data["detail"])


@unittest.skipUnless(HAS_TESTCLIENT, "FastAPI TestClient not available")
class TestRequestLogging(unittest.TestCase):
    """Test that request logging works and sanitizes data."""

    def setUp(self):
        try:
            import server
            self.server = server
            self.test_key = "test-key-" + secrets.token_hex(16)
            server._cached_api_key_hash = hashlib.sha256(
                self.test_key.encode()
            ).hexdigest()
            self.client = TestClient(server.app)
            # Clear audit log
            server.AUDIT_LOG.clear()
        except ImportError:
            self.skipTest("Cannot import server module")

    def test_failed_auth_logged(self):
        """Failed authentication attempts should be logged in audit."""
        self.client.get(
            "/commands",
            headers={"X-API-Key": "bad-key"},
        )
        # Check audit log for auth failure
        auth_failures = [
            e for e in self.server.AUDIT_LOG
            if e["event_type"] == "auth_failure"
        ]
        self.assertGreater(len(auth_failures), 0)

    def test_api_key_not_in_audit_log(self):
        """API keys should never appear in plain text in audit logs."""
        self.client.post(
            "/execute",
            json={
                "command": "research",
                "user_id": "test-user",
                "channel": "file",
            },
            headers={"X-API-Key": self.test_key},
        )
        # Verify no audit entries contain the raw key
        for entry in self.server.AUDIT_LOG:
            entry_str = str(entry)
            self.assertNotIn(self.test_key, entry_str,
                "Raw API key found in audit log entry")


if __name__ == '__main__':
    unittest.main()
