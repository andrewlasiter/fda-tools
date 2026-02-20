"""
Tests for FDA-53: Telemetry/Usage Analytics.

Tests the UsageAnalytics class which provides opt-in local usage tracking.
All tests use temporary directories to avoid polluting real analytics data.

Covers:
    - Enable/disable functionality
    - Event tracking and recording
    - Context manager auto-timing
    - Summary generation
    - Data export and clearing
    - Privacy guarantees (no PII collection)
    - Metadata filtering (safe keys only)
"""

import json
import time

import pytest

from usage_analytics import UsageAnalytics, PRIVACY_POLICY  # type: ignore


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def analytics(tmp_path):
    """Create a UsageAnalytics instance with a temporary directory."""
    return UsageAnalytics(
        analytics_dir=str(tmp_path / ".analytics"),
        session_id="test-session",
    )


@pytest.fixture
def enabled_analytics(analytics):
    """Create an enabled UsageAnalytics instance."""
    analytics.enable()
    return analytics


# ===================================================================
# Tests: Enable/Disable
# ===================================================================


class TestEnableDisable:
    """Tests for analytics enable/disable functionality."""

    def test_disabled_by_default(self, analytics):
        """Analytics is disabled by default (opt-in required)."""
        assert analytics.is_enabled() is False

    def test_enable(self, analytics):
        """Enabling analytics sets enabled=True in config."""
        analytics.enable()
        assert analytics.is_enabled() is True

    def test_disable_after_enable(self, analytics):
        """Disabling analytics after enabling sets enabled=False."""
        analytics.enable()
        assert analytics.is_enabled() is True

        analytics.disable()
        assert analytics.is_enabled() is False

    def test_enable_creates_config_file(self, analytics):
        """Enabling analytics creates the config file."""
        analytics.enable()
        assert analytics.config_file.exists()

        with open(analytics.config_file) as f:
            config = json.load(f)
        assert config["enabled"] is True
        assert "enabled_at" in config

    def test_enable_persists_across_instances(self, tmp_path):
        """Enabled state persists when creating a new instance."""
        dir_path = str(tmp_path / ".analytics")

        a1 = UsageAnalytics(analytics_dir=dir_path)
        a1.enable()

        a2 = UsageAnalytics(analytics_dir=dir_path)
        assert a2.is_enabled() is True


# ===================================================================
# Tests: Event Tracking
# ===================================================================


class TestEventTracking:
    """Tests for recording usage events."""

    def test_track_when_disabled_returns_false(self, analytics):
        """Tracking when disabled does not record and returns False."""
        result = analytics.track_command("batchfetch", execution_time_ms=100, success=True)
        assert result is False
        assert not analytics.usage_file.exists()

    def test_track_when_enabled_returns_true(self, enabled_analytics):
        """Tracking when enabled records event and returns True."""
        result = enabled_analytics.track_command(
            "batchfetch",
            execution_time_ms=1500,
            success=True,
            product_code_count=3,
        )
        assert result is True
        assert enabled_analytics.usage_file.exists()

    def test_tracked_event_structure(self, enabled_analytics):
        """Tracked event has all required fields."""
        enabled_analytics.track_command(
            "extract",
            execution_time_ms=2000,
            success=True,
            product_code_count=5,
        )

        events = enabled_analytics.load_events()
        assert len(events) == 1

        event = events[0]
        assert event["command_name"] == "extract"
        assert event["execution_time_ms"] == 2000
        assert event["success"] is True
        assert event["product_code_count"] == 5
        assert "timestamp" in event
        assert "session_id" in event
        assert event["session_id"] == "test-session"
        assert "plugin_version" in event

    def test_multiple_events_appended(self, enabled_analytics):
        """Multiple events are appended to the JSONL file."""
        enabled_analytics.track_command("batchfetch", execution_time_ms=100)
        enabled_analytics.track_command("extract", execution_time_ms=200)
        enabled_analytics.track_command("review", execution_time_ms=300)

        events = enabled_analytics.load_events()
        assert len(events) == 3
        assert events[0]["command_name"] == "batchfetch"
        assert events[1]["command_name"] == "extract"
        assert events[2]["command_name"] == "review"

    def test_failed_command_tracked(self, enabled_analytics):
        """Failed command is tracked with success=False."""
        enabled_analytics.track_command("draft", execution_time_ms=500, success=False)

        events = enabled_analytics.load_events()
        assert len(events) == 1
        assert events[0]["success"] is False

    def test_metadata_safe_keys_only(self, enabled_analytics):
        """Only safe metadata keys are recorded."""
        enabled_analytics.track_command(
            "batchfetch",
            metadata={
                "query_type": "classification",  # safe
                "cache_hit": True,  # safe
                "api_key": "SECRET123",  # unsafe - should be filtered
                "user_name": "John",  # unsafe - should be filtered
                "project_name": "my_project",  # unsafe - should be filtered
            }
        )

        events = enabled_analytics.load_events()
        meta = events[0].get("metadata", {})
        assert "query_type" in meta
        assert "cache_hit" in meta
        assert "api_key" not in meta
        assert "user_name" not in meta
        assert "project_name" not in meta


# ===================================================================
# Tests: Context Manager
# ===================================================================


class TestContextManager:
    """Tests for the track() context manager."""

    def test_context_manager_records_event(self, enabled_analytics):
        """Context manager records an event with timing."""
        with enabled_analytics.track("test_cmd", product_code_count=2):
            time.sleep(0.01)  # Small delay for measurable timing

        events = enabled_analytics.load_events()
        assert len(events) == 1
        assert events[0]["command_name"] == "test_cmd"
        assert events[0]["product_code_count"] == 2
        assert events[0]["execution_time_ms"] >= 5  # At least some time elapsed
        assert events[0]["success"] is True

    def test_context_manager_failure(self, enabled_analytics):
        """Context manager records failure when exception occurs."""
        with pytest.raises(ValueError):
            with enabled_analytics.track("failing_cmd"):
                raise ValueError("test error")

        events = enabled_analytics.load_events()
        assert len(events) == 1
        assert events[0]["success"] is False

    def test_context_manager_with_metadata(self, enabled_analytics):
        """Context manager updates metadata from ctx dict."""
        with enabled_analytics.track("cmd", metadata={"mode": "batch"}) as ctx:
            ctx["result_count"] = 42

        events = enabled_analytics.load_events()
        meta = events[0].get("metadata", {})
        assert meta.get("mode") == "batch"
        assert meta.get("result_count") == 42


# ===================================================================
# Tests: Summary
# ===================================================================


class TestSummary:
    """Tests for usage summary generation."""

    def test_empty_summary(self, analytics):
        """Summary with no events returns zero counts."""
        summary = analytics.get_summary(days=30)
        assert summary["total_events"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["commands"] == {}

    def test_summary_with_events(self, enabled_analytics):
        """Summary correctly aggregates events."""
        enabled_analytics.track_command("batchfetch", execution_time_ms=1000, success=True, product_code_count=3)
        enabled_analytics.track_command("batchfetch", execution_time_ms=2000, success=True, product_code_count=5)
        enabled_analytics.track_command("extract", execution_time_ms=500, success=False, product_code_count=1)

        summary = enabled_analytics.get_summary(days=30)

        assert summary["total_events"] == 3
        assert summary["unique_sessions"] == 1  # Same session_id
        assert summary["total_product_codes"] == 9

        # Command breakdown
        assert "batchfetch" in summary["commands"]
        bf = summary["commands"]["batchfetch"]
        assert bf["count"] == 2
        assert bf["avg_ms"] == 1500
        assert bf["success_rate"] == 1.0

        assert "extract" in summary["commands"]
        ext = summary["commands"]["extract"]
        assert ext["count"] == 1
        assert ext["success_rate"] == 0.0

    def test_success_rate_calculation(self, enabled_analytics):
        """Overall success rate is calculated correctly."""
        enabled_analytics.track_command("a", success=True)
        enabled_analytics.track_command("b", success=True)
        enabled_analytics.track_command("c", success=False)

        summary = enabled_analytics.get_summary()
        assert abs(summary["success_rate"] - 0.667) < 0.01

    def test_top_commands_sorted(self, enabled_analytics):
        """Top commands are sorted by frequency."""
        for _ in range(5):
            enabled_analytics.track_command("popular")
        for _ in range(3):
            enabled_analytics.track_command("medium")
        enabled_analytics.track_command("rare")

        summary = enabled_analytics.get_summary()
        top = summary["top_commands"]
        assert top[0] == ("popular", 5)
        assert top[1] == ("medium", 3)
        assert top[2] == ("rare", 1)


# ===================================================================
# Tests: Export and Clear
# ===================================================================


class TestExportClear:
    """Tests for data export and clearing."""

    def test_export_all_events(self, enabled_analytics):
        """Export returns all events as a list."""
        enabled_analytics.track_command("a", execution_time_ms=100)
        enabled_analytics.track_command("b", execution_time_ms=200)

        events = enabled_analytics.export()
        assert len(events) == 2

    def test_clear_deletes_data(self, enabled_analytics):
        """Clear deletes the usage file."""
        enabled_analytics.track_command("test")
        assert enabled_analytics.usage_file.exists()

        result = enabled_analytics.clear()
        assert result is True
        assert not enabled_analytics.usage_file.exists()

    def test_clear_when_no_data(self, analytics):
        """Clear returns False when no data exists."""
        result = analytics.clear()
        assert result is False

    def test_events_empty_after_clear(self, enabled_analytics):
        """After clearing, load_events returns empty list."""
        enabled_analytics.track_command("test")
        enabled_analytics.clear()

        events = enabled_analytics.load_events()
        assert events == []


# ===================================================================
# Tests: Privacy Guarantees
# ===================================================================


class TestPrivacy:
    """Tests verifying privacy guarantees."""

    def test_no_pii_in_events(self, enabled_analytics):
        """Events do not contain PII fields."""
        enabled_analytics.track_command(
            "batchfetch",
            execution_time_ms=1000,
            product_code_count=3,
        )

        events = enabled_analytics.load_events()
        event = events[0]

        # Verify no PII fields
        pii_fields = {"user", "email", "api_key", "project_name", "file_path",
                       "device_name", "k_number", "product_code", "ip_address"}
        for field in pii_fields:
            assert field not in event, f"PII field '{field}' found in event"

    def test_session_id_is_anonymous(self, enabled_analytics):
        """Session ID is a short random string, not tied to identity."""
        enabled_analytics.track_command("test")
        events = enabled_analytics.load_events()
        session_id = events[0]["session_id"]

        # Should be a short UUID fragment
        assert len(session_id) <= 36
        assert session_id == "test-session"  # Our fixture value

    def test_privacy_policy_exists(self):
        """Privacy policy text is defined and non-empty."""
        assert len(PRIVACY_POLICY) > 100
        assert "DATA COLLECTED" in PRIVACY_POLICY
        assert "DATA NOT COLLECTED" in PRIVACY_POLICY
        assert "NEVER transmitted" in PRIVACY_POLICY

    def test_disabled_by_default_privacy(self, tmp_path):
        """Fresh analytics instance is disabled (privacy by default)."""
        fresh = UsageAnalytics(analytics_dir=str(tmp_path / "new_analytics"))
        assert fresh.is_enabled() is False
