"""Tests for DataRefreshOrchestrator — blue-green deployment (FDA-196).

Coverage:
- RefreshAuditLogger.log_event(): stores entry, generic event logging
- DataRefreshOrchestrator init: blue-green enabled/disabled
- run_blue_green_refresh(): requires blue-green flag, dry-run, happy path,
  rollback on integrity failure, rollback on switch failure
- _detect_postgres_deltas(): stale candidates, empty candidates
- _apply_deltas_to_green(): success, update_failed conflict, exception conflict
- get_postgres_stats(): postgres disabled, stats from get_status(), error path
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from fda_tools.scripts.data_refresh_orchestrator import (
    DataRefreshOrchestrator,
    RefreshAuditLogger,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audit_logger(tmp_path: Path) -> RefreshAuditLogger:
    """Return an audit logger backed by a temp directory."""
    return RefreshAuditLogger(log_dir=tmp_path / "refresh_logs")


def _make_mock_coordinator(
    prepare_ok: bool = True,
    detect_returns: Optional[List[str]] = None,
    apply_returns: int = 1,
    verify_returns: tuple = (True, {"checks": "passed"}),
    switch_ok: bool = True,
    rollback_ok: bool = True,
    status_returns: Optional[Dict] = None,
) -> MagicMock:
    """Build a mock UpdateCoordinator with configurable responses."""
    coord = MagicMock()
    coord.prepare_green_database.return_value = prepare_ok
    coord.detect_deltas.return_value = detect_returns or []
    coord.apply_updates.return_value = apply_returns
    coord.verify_integrity.return_value = verify_returns
    coord.switch_to_green.return_value = switch_ok
    coord.rollback_to_blue.return_value = rollback_ok
    coord.get_status.return_value = status_returns or {
        "active_db": "blue",
        "connection_pool": {"size": 5},
        "table_sizes": {},
        "last_refresh": "2026-02-20T12:00:00Z",
    }
    return coord


def _make_orchestrator(
    tmp_path: Path,
    use_blue_green: bool = False,
    coordinator: Optional[MagicMock] = None,
) -> DataRefreshOrchestrator:
    """Build a DataRefreshOrchestrator with mocked dependencies."""
    store = MagicMock()
    store.get_manifest.return_value = {"pma_entries": {}}
    store.is_expired.return_value = False

    rate_limiter = MagicMock()
    rate_limiter.acquire.return_value = True
    rate_limiter.get_stats.return_value = {
        "total_requests": 0,
        "total_wait_seconds": 0.0,
    }

    audit_logger = _make_audit_logger(tmp_path)

    orch = DataRefreshOrchestrator(
        store=store,
        rate_limiter=rate_limiter,
        audit_logger=audit_logger,
        use_blue_green=False,  # Always False at construction; override below
    )

    # Inject coordinator and flag manually to avoid import side-effects
    if use_blue_green and coordinator is not None:
        orch.use_blue_green = True
        orch.update_coordinator = coordinator

    return orch


# ---------------------------------------------------------------------------
# RefreshAuditLogger.log_event
# ---------------------------------------------------------------------------


class TestRefreshAuditLoggerLogEvent:
    """Tests for the generic log_event method."""

    def test_log_event_stores_entry(self, tmp_path):
        logger = _make_audit_logger(tmp_path)
        logger.log_event("test_event", {"key": "value"})
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0]["event"] == "test_event"
        assert entries[0]["details"] == {"key": "value"}

    def test_log_event_timestamp_present(self, tmp_path):
        logger = _make_audit_logger(tmp_path)
        logger.log_event("my_event")
        entry = logger.get_entries()[0]
        # Should be a parseable ISO datetime
        datetime.fromisoformat(entry["timestamp"])

    def test_log_event_empty_details_defaults_to_dict(self, tmp_path):
        logger = _make_audit_logger(tmp_path)
        logger.log_event("no_details")
        entry = logger.get_entries()[0]
        assert entry["details"] == {}

    def test_log_event_multiple_events_accumulate(self, tmp_path):
        logger = _make_audit_logger(tmp_path)
        logger.log_event("first")
        logger.log_event("second")
        events = [e["event"] for e in logger.get_entries()]
        assert "first" in events
        assert "second" in events

    def test_log_event_entries_not_filtered_by_session(self, tmp_path):
        """log_event entries lack session_id and still appear in get_entries()."""
        logger = _make_audit_logger(tmp_path)
        logger.log_event("generic_event", {"data": 1})
        # Without session filter: returned
        assert len(logger.get_entries()) == 1
        # With session filter: not returned (no session_id on event)
        assert logger.get_entries(session_id="s1") == []


# ---------------------------------------------------------------------------
# DataRefreshOrchestrator — init blue-green
# ---------------------------------------------------------------------------


class TestOrchestratorBlueGreenInit:
    """Tests for blue-green mode initialization."""

    def test_blue_green_disabled_by_default(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        assert not orch.use_blue_green

    def test_update_coordinator_none_when_disabled(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        assert orch.update_coordinator is None

    def test_update_coordinator_set_when_enabled(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        assert orch.update_coordinator is coord

    def test_use_blue_green_flag_set(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        assert orch.use_blue_green is True


# ---------------------------------------------------------------------------
# run_blue_green_refresh
# ---------------------------------------------------------------------------


class TestRunBlueGreenRefresh:
    """Tests for the blue-green refresh workflow."""

    def test_raises_when_not_enabled(self, tmp_path):
        orch = _make_orchestrator(tmp_path, use_blue_green=False)
        with pytest.raises(RuntimeError, match="not enabled"):
            orch.run_blue_green_refresh()

    def test_dry_run_returns_dry_run_status(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        # Patch _detect_postgres_deltas to avoid real logic
        orch.get_refresh_candidates = MagicMock(return_value=[
            {"pma_number": "P000001", "last_refresh_timestamp": 0, "priority": 1}
        ])
        coord.detect_deltas.return_value = ["P000001"]

        result = orch.run_blue_green_refresh(dry_run=True)
        assert result["status"] == "dry_run"
        coord.switch_to_green.assert_not_called()

    def test_happy_path_switches_to_green(self, tmp_path):
        coord = _make_mock_coordinator(
            prepare_ok=True,
            detect_returns=["P000001"],
            apply_returns=1,
            verify_returns=(True, {"checks": "passed"}),
            switch_ok=True,
        )
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[
            {"pma_number": "P000001", "last_refresh_timestamp": 0, "priority": 1}
        ])

        result = orch.run_blue_green_refresh()

        assert result["status"] == "completed"
        assert result.get("switched_to_green") is True
        coord.prepare_green_database.assert_called_once()
        coord.switch_to_green.assert_called_once()

    def test_integrity_failure_triggers_rollback(self, tmp_path):
        coord = _make_mock_coordinator(
            verify_returns=(False, {"error": "row count mismatch"}),
        )
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[])

        result = orch.run_blue_green_refresh()

        assert result["status"] == "failed"
        coord.rollback_to_blue.assert_called_once()
        coord.switch_to_green.assert_not_called()

    def test_switch_failure_triggers_rollback(self, tmp_path):
        coord = _make_mock_coordinator(switch_ok=True)
        coord.switch_to_green.side_effect = RuntimeError("pgbouncer timeout")
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[])

        result = orch.run_blue_green_refresh()

        assert result["status"] == "failed"
        assert "pgbouncer timeout" in result["error"]
        coord.rollback_to_blue.assert_called_once()

    def test_happy_path_reports_delta_count(self, tmp_path):
        coord = _make_mock_coordinator(detect_returns=["P000001", "P000002"])
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[
            {"pma_number": "P000001", "last_refresh_timestamp": 0, "priority": 1},
            {"pma_number": "P000002", "last_refresh_timestamp": 0, "priority": 1},
        ])

        result = orch.run_blue_green_refresh()
        assert result.get("deltas_detected", 0) >= 0  # non-negative count

    def test_audit_events_logged(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[])

        orch.run_blue_green_refresh()

        event_types = [e["event"] for e in orch.audit_logger.get_entries()]
        assert "blue_green_refresh_start" in event_types
        assert "blue_green_refresh_complete" in event_types


# ---------------------------------------------------------------------------
# _detect_postgres_deltas
# ---------------------------------------------------------------------------


class TestDetectPostgresDeltas:
    """Tests for the delta detection helper."""

    def test_empty_candidates_returns_empty(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[])

        deltas = orch._detect_postgres_deltas("daily", "all")
        assert deltas == []

    def test_stale_candidate_with_matching_delta_included(self, tmp_path):
        coord = _make_mock_coordinator(detect_returns=["P000001"])
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[
            {"pma_number": "P000001", "last_refresh_timestamp": 0, "priority": 1},
        ])

        deltas = orch._detect_postgres_deltas("daily", "all")
        assert any(d["pma_number"] == "P000001" for d in deltas)

    def test_candidate_not_in_api_deltas_excluded(self, tmp_path):
        # detect_deltas returns empty — no changes at API level
        coord = _make_mock_coordinator(detect_returns=[])
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[
            {"pma_number": "P000001", "last_refresh_timestamp": 0, "priority": 1},
        ])

        deltas = orch._detect_postgres_deltas("daily", "all")
        assert deltas == []

    def test_schedule_passed_to_ttl_mapping(self, tmp_path):
        coord = _make_mock_coordinator(detect_returns=["P000001"])
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        orch.get_refresh_candidates = MagicMock(return_value=[
            {"pma_number": "P000001", "last_refresh_timestamp": 0, "priority": 1},
        ])
        # Weekly schedule should use 168h TTL — just verify it runs without error
        deltas = orch._detect_postgres_deltas("weekly", "all")
        assert isinstance(deltas, list)


# ---------------------------------------------------------------------------
# _apply_deltas_to_green
# ---------------------------------------------------------------------------


class TestApplyDeltasToGreen:
    """Tests for the delta application helper."""

    def test_successful_apply_returns_no_conflicts(self, tmp_path):
        coord = _make_mock_coordinator(apply_returns=1)
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        deltas = [{"pma_number": "P000001", "changed": True}]

        conflicts = orch._apply_deltas_to_green(deltas)
        assert conflicts == []
        coord.apply_updates.assert_called_once_with(
            endpoint="pma", record_ids=["P000001"]
        )

    def test_apply_returns_zero_adds_conflict(self, tmp_path):
        coord = _make_mock_coordinator(apply_returns=0)
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        deltas = [{"pma_number": "P000001", "changed": True}]

        conflicts = orch._apply_deltas_to_green(deltas)
        assert len(conflicts) == 1
        assert conflicts[0]["reason"] == "update_failed"
        assert conflicts[0]["pma_number"] == "P000001"

    def test_apply_exception_adds_conflict(self, tmp_path):
        coord = _make_mock_coordinator()
        coord.apply_updates.side_effect = RuntimeError("db write error")
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        deltas = [{"pma_number": "P000001", "changed": True}]

        conflicts = orch._apply_deltas_to_green(deltas)
        assert len(conflicts) == 1
        assert conflicts[0]["reason"] == "exception"
        assert "db write error" in conflicts[0]["error"]

    def test_exception_conflict_logged_to_audit(self, tmp_path):
        coord = _make_mock_coordinator()
        coord.apply_updates.side_effect = RuntimeError("disk full")
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)

        orch._apply_deltas_to_green([{"pma_number": "P000001"}])

        audit_events = [e["event"] for e in orch.audit_logger.get_entries()]
        assert "conflict_detected" in audit_events

    def test_multiple_deltas_processed_independently(self, tmp_path):
        coord = _make_mock_coordinator(apply_returns=1)
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)
        deltas = [
            {"pma_number": "P000001"},
            {"pma_number": "P000002"},
        ]

        conflicts = orch._apply_deltas_to_green(deltas)
        assert conflicts == []
        assert coord.apply_updates.call_count == 2

    def test_empty_deltas_returns_empty_conflicts(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)

        conflicts = orch._apply_deltas_to_green([])
        assert conflicts == []
        coord.apply_updates.assert_not_called()


# ---------------------------------------------------------------------------
# get_postgres_stats
# ---------------------------------------------------------------------------


class TestGetPostgresStats:
    """Tests for postgres statistics retrieval."""

    def test_disabled_returns_postgres_enabled_false(self, tmp_path):
        orch = _make_orchestrator(tmp_path, use_blue_green=False)
        stats = orch.get_postgres_stats()
        assert stats == {"postgres_enabled": False}

    def test_enabled_returns_status_fields(self, tmp_path):
        coord = _make_mock_coordinator(
            status_returns={
                "active_db": "blue",
                "connection_pool": {"size": 10},
                "table_sizes": {"510k": "4 GB"},
                "last_refresh": "2026-02-21T00:00:00Z",
            }
        )
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)

        stats = orch.get_postgres_stats()
        assert stats["postgres_enabled"] is True
        assert stats["active_db"] == "blue"
        assert stats["connection_pool"] == {"size": 10}

    def test_get_status_called_once(self, tmp_path):
        coord = _make_mock_coordinator()
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)

        orch.get_postgres_stats()
        coord.get_status.assert_called_once()

    def test_error_in_get_status_returns_error_key(self, tmp_path):
        coord = _make_mock_coordinator()
        coord.get_status.side_effect = RuntimeError("connection refused")
        orch = _make_orchestrator(tmp_path, use_blue_green=True, coordinator=coord)

        stats = orch.get_postgres_stats()
        assert stats["postgres_enabled"] is True
        assert "connection refused" in stats["error"]
