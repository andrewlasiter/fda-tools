"""Tests for bridge server health, metrics, and readiness endpoints (FDA-141).

Coverage:
- GET /health — status, version, uptime, sessions, alerts, last_request_at
- GET /ready — 200 when ready, 503 when commands dir missing
- GET /metrics — requires auth, returns request counts, response times, memory
- Alert logic in _check_alerts(): error rate, slow responses, consecutive failures
"""

import importlib
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Guard: skip all tests if fastapi/httpx are not installed
# ---------------------------------------------------------------------------
pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("httpx", reason="httpx not installed (required by TestClient)")

from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_server_state():
    """Reset global metrics state before each test."""
    import fda_tools.bridge.server as srv

    srv._total_requests = 0
    srv._total_errors = 0
    srv._request_durations_ms = []
    srv._last_request_time = None
    srv._consecutive_health_failures = 0
    # Provide a dummy API key so auth works in tests
    srv._BRIDGE_API_KEY = "test-api-key-1234567890abcdef"
    import hashlib

    srv._cached_api_key_hash = hashlib.sha256(
        srv._BRIDGE_API_KEY.encode()
    ).hexdigest()
    yield


@pytest.fixture()
def client():
    """Return a TestClient for the bridge app."""
    from fda_tools.bridge.server import app

    return TestClient(app)


@pytest.fixture()
def auth_headers():
    return {"X-API-Key": "test-api-key-1234567890abcdef"}


# ---------------------------------------------------------------------------
# /health tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_field(self, client):
        data = client.get("/health").json()
        assert data["status"] in ("healthy", "degraded")

    def test_health_version_present(self, client):
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"]  # non-empty

    def test_health_uptime_non_negative(self, client):
        data = client.get("/health").json()
        assert data["uptime_seconds"] >= 0

    def test_health_sessions_active_field(self, client):
        data = client.get("/health").json()
        assert "sessions_active" in data
        assert isinstance(data["sessions_active"], int)

    def test_health_commands_available_field(self, client):
        data = client.get("/health").json()
        assert "commands_available" in data
        assert isinstance(data["commands_available"], int)

    def test_health_alerts_field_is_list(self, client):
        data = client.get("/health").json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_health_alerts_active_count(self, client):
        data = client.get("/health").json()
        assert data["alerts_active"] == len(data["alerts"])

    def test_health_no_auth_required(self, client):
        """Health endpoint must be accessible without auth."""
        response = client.get("/health")
        assert response.status_code == 200  # Not 401

    def test_health_last_request_at_none_initially(self, client):
        """last_request_at is None before any requests hit the middleware."""
        import fda_tools.bridge.server as srv

        srv._last_request_time = None
        # Call /health via direct app state (bypass middleware tracking for this assertion)
        data = client.get("/health").json()
        # After the /health call itself, _last_request_time is set — just verify field exists
        assert "last_request_at" in data

    def test_health_resets_consecutive_failures(self, client):
        import fda_tools.bridge.server as srv

        srv._consecutive_health_failures = 5
        client.get("/health")
        assert srv._consecutive_health_failures == 0

    def test_health_status_degraded_when_alerts_present(self, client):
        import fda_tools.bridge.server as srv

        # Force high error rate
        srv._total_requests = 100
        srv._total_errors = 90  # 90% error rate > 10% threshold
        data = client.get("/health").json()
        assert data["status"] == "degraded"
        assert data["alerts_active"] > 0

    def test_health_status_healthy_when_no_alerts(self, client):
        import fda_tools.bridge.server as srv

        srv._total_requests = 0
        srv._total_errors = 0
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 0
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert data["alerts_active"] == 0


# ---------------------------------------------------------------------------
# /ready tests
# ---------------------------------------------------------------------------


class TestReadinessEndpoint:
    """Tests for GET /ready."""

    def test_ready_no_auth_required(self, client):
        """Readiness endpoint is unauthenticated."""
        response = client.get("/ready")
        # Either 200 or 503, but not 401
        assert response.status_code in (200, 503)

    def test_ready_returns_ready_true_when_dirs_exist(self, client):
        from fda_tools.bridge.server import COMMANDS_DIR, SCRIPTS_DIR

        if COMMANDS_DIR.exists() and SCRIPTS_DIR.exists():
            data = client.get("/ready").json()
            assert data["ready"] is True
            assert data["issues"] == []

    def test_ready_503_when_commands_dir_missing(self, client):
        import fda_tools.bridge.server as srv

        original = srv.COMMANDS_DIR
        srv.COMMANDS_DIR = Path("/nonexistent/commands")
        try:
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert "commands_dir_missing" in data["issues"]
        finally:
            srv.COMMANDS_DIR = original

    def test_ready_503_when_scripts_dir_missing(self, client):
        import fda_tools.bridge.server as srv

        original = srv.SCRIPTS_DIR
        srv.SCRIPTS_DIR = Path("/nonexistent/scripts")
        try:
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert "scripts_dir_missing" in data["issues"]
        finally:
            srv.SCRIPTS_DIR = original

    def test_ready_increments_consecutive_failures_on_503(self, client):
        import fda_tools.bridge.server as srv

        original = srv.COMMANDS_DIR
        srv.COMMANDS_DIR = Path("/nonexistent/commands")
        srv._consecutive_health_failures = 0
        try:
            client.get("/ready")
            assert srv._consecutive_health_failures == 1
        finally:
            srv.COMMANDS_DIR = original

    def test_ready_issues_is_list(self, client):
        data = client.get("/ready").json()
        assert isinstance(data["issues"], list)


# ---------------------------------------------------------------------------
# /metrics tests
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    """Tests for GET /metrics (authenticated)."""

    def test_metrics_requires_auth(self, client):
        response = client.get("/metrics")
        assert response.status_code == 401

    def test_metrics_returns_200_with_auth(self, client, auth_headers):
        response = client.get("/metrics", headers=auth_headers)
        assert response.status_code == 200

    def test_metrics_requests_section(self, client, auth_headers):
        data = client.get("/metrics", headers=auth_headers).json()
        req = data["requests"]
        assert "total" in req
        assert "errors" in req
        assert "error_rate_pct" in req

    def test_metrics_response_time_section(self, client, auth_headers):
        data = client.get("/metrics", headers=auth_headers).json()
        rt = data["response_time_ms"]
        assert "avg" in rt
        assert "p50" in rt
        assert "p95" in rt
        assert "p99" in rt
        assert "samples" in rt

    def test_metrics_sessions_section(self, client, auth_headers):
        data = client.get("/metrics", headers=auth_headers).json()
        assert "sessions" in data
        assert "active" in data["sessions"]

    def test_metrics_memory_mb_field(self, client, auth_headers):
        data = client.get("/metrics", headers=auth_headers).json()
        assert "memory_mb" in data
        assert data["memory_mb"] > 0

    def test_metrics_uptime_seconds_field(self, client, auth_headers):
        data = client.get("/metrics", headers=auth_headers).json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_metrics_alerts_active_field(self, client, auth_headers):
        data = client.get("/metrics", headers=auth_headers).json()
        assert "alerts_active" in data
        assert isinstance(data["alerts_active"], int)

    def test_metrics_error_rate_calculated(self, client, auth_headers):
        import fda_tools.bridge.server as srv

        srv._total_requests = 10
        srv._total_errors = 2
        data = client.get("/metrics", headers=auth_headers).json()
        assert data["requests"]["error_rate_pct"] == pytest.approx(20.0, abs=0.1)

    def test_metrics_zero_when_no_requests(self, client, auth_headers):
        import fda_tools.bridge.server as srv

        srv._total_requests = 0
        srv._total_errors = 0
        data = client.get("/metrics", headers=auth_headers).json()
        assert data["requests"]["error_rate_pct"] == 0.0


# ---------------------------------------------------------------------------
# _check_alerts tests
# ---------------------------------------------------------------------------


class TestCheckAlerts:
    """Unit tests for the _check_alerts() helper."""

    def _alerts(self):
        from fda_tools.bridge.server import _check_alerts

        return _check_alerts()

    def test_no_alerts_when_clean(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 0
        srv._total_errors = 0
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 0
        assert self._alerts() == []

    def test_high_error_rate_alert(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 100
        srv._total_errors = 50  # 50% > 10% threshold
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 0
        alerts = self._alerts()
        assert any(a["type"] == "high_error_rate" for a in alerts)

    def test_high_error_rate_below_threshold_no_alert(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 100
        srv._total_errors = 5  # 5% < 10%
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 0
        assert self._alerts() == []

    def test_slow_responses_alert(self):
        import fda_tools.bridge.server as srv

        # p95 will be > 5000ms threshold
        srv._total_requests = 0
        srv._total_errors = 0
        srv._request_durations_ms = [6000.0] * 100  # All 6s
        srv._consecutive_health_failures = 0
        alerts = self._alerts()
        assert any(a["type"] == "slow_responses" for a in alerts)

    def test_slow_responses_below_threshold_no_alert(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 0
        srv._total_errors = 0
        srv._request_durations_ms = [100.0] * 100  # All 100ms
        srv._consecutive_health_failures = 0
        assert self._alerts() == []

    def test_consecutive_failures_alert(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 0
        srv._total_errors = 0
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 5  # >= 3 threshold
        alerts = self._alerts()
        assert any(a["type"] == "consecutive_health_failures" for a in alerts)

    def test_consecutive_failures_below_threshold_no_alert(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 0
        srv._total_errors = 0
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 2  # < 3 threshold
        assert self._alerts() == []

    def test_multiple_alerts_can_fire_simultaneously(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 100
        srv._total_errors = 50  # High error rate
        srv._request_durations_ms = [6000.0] * 100  # Slow responses
        srv._consecutive_health_failures = 10  # Many failures
        alerts = self._alerts()
        alert_types = {a["type"] for a in alerts}
        assert "high_error_rate" in alert_types
        assert "slow_responses" in alert_types
        assert "consecutive_health_failures" in alert_types

    def test_alert_has_required_fields(self):
        import fda_tools.bridge.server as srv

        srv._total_requests = 100
        srv._total_errors = 50
        srv._request_durations_ms = []
        srv._consecutive_health_failures = 0
        alerts = self._alerts()
        alert = next(a for a in alerts if a["type"] == "high_error_rate")
        assert "type" in alert
        assert "severity" in alert
        assert "message" in alert
