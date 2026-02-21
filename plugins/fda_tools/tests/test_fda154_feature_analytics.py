"""
Feature Analytics Tests (FDA-154).
=====================================

Verifies that FeatureAnalytics provides privacy-preserving, opt-in tracking
of command invocations, errors, and workflow funnel steps.

Tests cover:
  - EventType enum string values
  - FeatureEvent.as_dict() serialisation
  - Enable / disable / is_enabled lifecycle
  - record_command() no-op when disabled
  - record_command() writes event when enabled (success and failure)
  - record_error() writes error_type; does not record message text
  - record_workflow_step() writes workflow_id and step
  - Metadata filtered to SAFE_META_KEYS only
  - top_commands() returns most-used commands sorted by count
  - error_summary() groups errors by type and command
  - workflow_funnels() counts step completions for a workflow_id
  - get_events() returns events within the day window
  - clear() removes all events
  - Events outside the day window are excluded from analysis

Test count: 21
Target: pytest plugins/fda_tools/tests/test_fda154_feature_analytics.py -v
"""

from __future__ import annotations

from pathlib import Path

from fda_tools.lib.feature_analytics import (
    EventType,
    FeatureAnalytics,
    FeatureEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fa(tmp_path: Path) -> FeatureAnalytics:
    """Return an enabled FeatureAnalytics backed by a tmp directory."""
    fa = FeatureAnalytics(analytics_dir=str(tmp_path / ".analytics"))
    fa.enable()
    return fa


# ---------------------------------------------------------------------------
# TestEventTypeEnum
# ---------------------------------------------------------------------------


class TestEventTypeEnum:
    def test_command_succeeded_value(self):
        assert EventType.COMMAND_SUCCEEDED == "command_succeeded"

    def test_command_failed_value(self):
        assert EventType.COMMAND_FAILED == "command_failed"

    def test_error_occurred_value(self):
        assert EventType.ERROR_OCCURRED == "error_occurred"

    def test_workflow_step_completed_value(self):
        assert EventType.WORKFLOW_STEP_COMPLETED == "workflow_step_completed"

    def test_all_six_types_defined(self):
        assert len(EventType) == 6


# ---------------------------------------------------------------------------
# TestFeatureEventSerialization
# ---------------------------------------------------------------------------


class TestFeatureEventSerialization:
    def test_as_dict_contains_required_keys(self):
        ev = FeatureEvent(
            event_type=EventType.COMMAND_SUCCEEDED,
            command="batchfetch",
            session_id="sess-1",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        d = ev.as_dict()
        assert d["event_type"] == "command_succeeded"
        assert d["command"] == "batchfetch"
        assert d["session_id"] == "sess-1"

    def test_optional_fields_omitted_when_none(self):
        ev = FeatureEvent(
            event_type=EventType.COMMAND_SUCCEEDED,
            command="batchfetch",
            session_id="sess-1",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        d = ev.as_dict()
        assert "duration_ms" not in d
        assert "workflow_id" not in d
        assert "error_type" not in d

    def test_duration_ms_rounded(self):
        ev = FeatureEvent(
            event_type=EventType.COMMAND_SUCCEEDED,
            command="cmd",
            session_id="s",
            timestamp="2026-01-01T00:00:00+00:00",
            duration_ms=123.456789,
        )
        assert ev.as_dict()["duration_ms"] == 123.46


# ---------------------------------------------------------------------------
# TestEnableDisable
# ---------------------------------------------------------------------------


class TestEnableDisable:
    def test_disabled_by_default(self, tmp_path):
        fa = FeatureAnalytics(analytics_dir=str(tmp_path / ".analytics"))
        assert fa.is_enabled() is False

    def test_enable_sets_enabled(self, tmp_path):
        fa = FeatureAnalytics(analytics_dir=str(tmp_path / ".analytics"))
        fa.enable()
        assert fa.is_enabled() is True

    def test_disable_clears_enabled(self, tmp_path):
        fa = FeatureAnalytics(analytics_dir=str(tmp_path / ".analytics"))
        fa.enable()
        fa.disable()
        assert fa.is_enabled() is False


# ---------------------------------------------------------------------------
# TestRecordCommand
# ---------------------------------------------------------------------------


class TestRecordCommand:
    def test_no_op_when_disabled(self, tmp_path):
        fa = FeatureAnalytics(analytics_dir=str(tmp_path / ".analytics"))
        fa.record_command("batchfetch", success=True, duration_ms=100)
        assert fa.get_events() == []

    def test_success_event_written(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_command("batchfetch", success=True, duration_ms=200)
        events = fa.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "command_succeeded"
        assert events[0]["command"] == "batchfetch"

    def test_failure_event_type(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_command("batchfetch", success=False)
        events = fa.get_events()
        assert events[0]["event_type"] == "command_failed"

    def test_unsafe_metadata_filtered_out(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_command(
            "search",
            success=True,
            user_email="user@example.com",   # unsafe — must be dropped
            product_code_count=5,            # safe — must be kept
        )
        meta = fa.get_events()[0].get("metadata", {})
        assert "user_email" not in meta
        assert meta.get("product_code_count") == 5


# ---------------------------------------------------------------------------
# TestRecordError
# ---------------------------------------------------------------------------


class TestRecordError:
    def test_error_event_written(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_error("batchfetch", error_type="TimeoutError")
        events = fa.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "error_occurred"
        assert events[0]["error_type"] == "TimeoutError"

    def test_no_message_text_stored(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_error("batchfetch", error_type="HTTPError")
        ev = fa.get_events()[0]
        assert "message" not in ev
        # error_type is a class name string, not message text
        assert ev["error_type"] == "HTTPError"

    def test_no_op_when_disabled(self, tmp_path):
        fa = FeatureAnalytics(analytics_dir=str(tmp_path / ".analytics"))
        fa.record_error("cmd", error_type="ValueError")
        assert fa.get_events() == []


# ---------------------------------------------------------------------------
# TestRecordWorkflowStep
# ---------------------------------------------------------------------------


class TestRecordWorkflowStep:
    def test_workflow_step_written(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_workflow_step("wf-1", step="predicate_search", command="batchfetch")
        events = fa.get_events()
        assert events[0]["event_type"] == "workflow_step_completed"
        assert events[0]["workflow_id"] == "wf-1"
        assert events[0]["workflow_step"] == "predicate_search"


# ---------------------------------------------------------------------------
# TestTopCommands
# ---------------------------------------------------------------------------


class TestTopCommands:
    def test_top_commands_sorted_by_count(self, tmp_path):
        fa = _fa(tmp_path)
        for _ in range(3):
            fa.record_command("batchfetch", success=True)
        for _ in range(2):
            fa.record_command("search", success=True)
        fa.record_command("extract", success=True)

        top = fa.top_commands(n=3)
        assert top[0]["command"] == "batchfetch"
        assert top[0]["count"] == 3
        assert top[1]["command"] == "search"

    def test_top_commands_respects_n(self, tmp_path):
        fa = _fa(tmp_path)
        for cmd in ["a", "b", "c", "d"]:
            fa.record_command(cmd, success=True)
        assert len(fa.top_commands(n=2)) == 2


# ---------------------------------------------------------------------------
# TestErrorSummary
# ---------------------------------------------------------------------------


class TestErrorSummary:
    def test_error_summary_groups_by_type(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_error("batchfetch", error_type="TimeoutError")
        fa.record_error("batchfetch", error_type="TimeoutError")
        fa.record_error("search", error_type="HTTPError")

        summary = fa.error_summary()
        assert summary["TimeoutError"]["total"] == 2
        assert summary["HTTPError"]["total"] == 1
        assert summary["TimeoutError"]["by_command"]["batchfetch"] == 2


# ---------------------------------------------------------------------------
# TestWorkflowFunnels
# ---------------------------------------------------------------------------


class TestWorkflowFunnels:
    def test_funnel_counts_steps(self, tmp_path):
        fa = _fa(tmp_path)
        for _ in range(3):
            fa.record_workflow_step("wf-1", step="search", command="batchfetch")
        for _ in range(2):
            fa.record_workflow_step("wf-1", step="analyze", command="extract")

        funnel = fa.workflow_funnels("wf-1")
        assert funnel["search"] == 3
        assert funnel["analyze"] == 2

    def test_funnel_excludes_other_workflow_ids(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_workflow_step("wf-1", step="step-a", command="cmd")
        fa.record_workflow_step("wf-2", step="step-a", command="cmd")

        funnel = fa.workflow_funnels("wf-1")
        assert funnel.get("step-a") == 1


# ---------------------------------------------------------------------------
# TestClear
# ---------------------------------------------------------------------------


class TestClear:
    def test_clear_removes_all_events(self, tmp_path):
        fa = _fa(tmp_path)
        fa.record_command("cmd", success=True)
        fa.record_error("cmd", error_type="ValueError")
        fa.clear()
        assert fa.get_events() == []
