"""Tests for ORCH-009: Continuous monitoring of Linear issue changes.

Covers:
- MonitorState: load/save, get/set/remove, atomic write
- IssueMonitor: register, check (title/description/comment/label changes),
  unregister, watch (once mode)
- CLI: --list, --once, --watch
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from fda_tools.scripts.monitor_service import (
    IssueMonitor,
    IssueRecord,
    MonitorEvent,
    MonitorState,
    _sha256,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_issue(
    issue_id: str = "FDA-42",
    title: str = "My issue",
    description: str = "Some description",
    comment_count: int = 0,
    labels: List[str] = None,
) -> Dict[str, Any]:
    return {
        "id": issue_id,
        "title": title,
        "description": description,
        "comment_count": comment_count,
        "labels": labels or [],
    }


# ---------------------------------------------------------------------------
# MonitorState tests
# ---------------------------------------------------------------------------


class TestMonitorState:
    def _make_record(self, issue_id: str = "FDA-1") -> IssueRecord:
        return IssueRecord(
            issue_id=issue_id,
            registered_at="2026-02-21T00:00:00+00:00",
            last_seen_at="2026-02-21T00:00:00+00:00",
            title_hash=_sha256("title"),
            description_hash=_sha256("desc"),
            comment_count=0,
            labels=[],
        )

    def test_empty_state_has_no_records(self, tmp_path):
        state = MonitorState(tmp_path)
        assert len(state) == 0
        assert state.get("FDA-1") is None

    def test_set_and_get(self, tmp_path):
        state = MonitorState(tmp_path)
        rec = self._make_record("FDA-10")
        state.set(rec)
        assert state.get("FDA-10") is rec

    def test_save_and_reload(self, tmp_path):
        state = MonitorState(tmp_path)
        rec = self._make_record("FDA-20")
        state.set(rec)
        state.save()

        # Reload
        state2 = MonitorState(tmp_path)
        loaded = state2.get("FDA-20")
        assert loaded is not None
        assert loaded.issue_id == "FDA-20"
        assert loaded.title_hash == rec.title_hash
        assert loaded.comment_count == 0

    def test_remove(self, tmp_path):
        state = MonitorState(tmp_path)
        state.set(self._make_record("FDA-30"))
        assert len(state) == 1
        state.remove("FDA-30")
        assert len(state) == 0
        assert state.get("FDA-30") is None

    def test_all_issue_ids(self, tmp_path):
        state = MonitorState(tmp_path)
        state.set(self._make_record("FDA-1"))
        state.set(self._make_record("FDA-2"))
        state.set(self._make_record("FDA-3"))
        assert set(state.all_issue_ids()) == {"FDA-1", "FDA-2", "FDA-3"}

    def test_corrupt_file_starts_fresh(self, tmp_path):
        state_file = tmp_path / "monitor_state.json"
        state_file.write_text("NOT VALID JSON")
        state = MonitorState(tmp_path)
        assert len(state) == 0

    def test_save_is_atomic(self, tmp_path):
        """Save uses a .tmp file then replaces — no .tmp file left after."""
        state = MonitorState(tmp_path)
        state.set(self._make_record("FDA-5"))
        state.save()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp file found: {tmp_files}"
        assert (tmp_path / "monitor_state.json").exists()


# ---------------------------------------------------------------------------
# IssueMonitor.register tests
# ---------------------------------------------------------------------------


class TestIssueMonitorRegister:
    def test_register_creates_record(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-42", "My issue", "Description", comment_count=3)
        ids = monitor.registered_issue_ids()
        assert "FDA-42" in ids

    def test_register_persists_state(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-50", "Issue", "Desc", labels=["Bug"])
        # Reload
        monitor2 = IssueMonitor(data_dir=tmp_path)
        assert "FDA-50" in monitor2.registered_issue_ids()

    def test_register_preserves_registered_at_on_re_register(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-51", "Title", "Desc")
        first_registered = monitor._state.get("FDA-51").registered_at

        # Re-register (e.g. baseline refresh)
        monitor.register("FDA-51", "New Title", "New Desc")
        assert monitor._state.get("FDA-51").registered_at == first_registered

    def test_unregister_removes_issue(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-52", "Title", "Desc")
        monitor.unregister("FDA-52")
        assert "FDA-52" not in monitor.registered_issue_ids()


# ---------------------------------------------------------------------------
# IssueMonitor.check tests
# ---------------------------------------------------------------------------


class TestIssueMonitorCheck:
    def _setup(self, tmp_path, title="Title", desc="Desc", comments=0, labels=None):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-42", title, desc, comment_count=comments, labels=labels)
        return monitor

    def test_no_change_returns_empty(self, tmp_path):
        monitor = self._setup(tmp_path)
        events = monitor.check("FDA-42", "Title", "Desc", 0)
        assert events == []

    def test_title_change_detected(self, tmp_path):
        monitor = self._setup(tmp_path)
        events = monitor.check("FDA-42", "New Title", "Desc", 0)
        assert len(events) == 1
        assert events[0].change_type == "title"
        assert events[0].issue_id == "FDA-42"
        assert events[0].new_value == "New Title"

    def test_description_change_detected(self, tmp_path):
        monitor = self._setup(tmp_path)
        events = monitor.check("FDA-42", "Title", "Different description", 0)
        assert len(events) == 1
        assert events[0].change_type == "description"

    def test_new_comment_detected(self, tmp_path):
        monitor = self._setup(tmp_path, comments=3)
        events = monitor.check("FDA-42", "Title", "Desc", current_comment_count=5)
        assert len(events) == 1
        assert events[0].change_type == "new_comment"
        assert events[0].old_value == "3"
        assert events[0].new_value == "5"

    def test_label_change_detected(self, tmp_path):
        monitor = self._setup(tmp_path, labels=["Bug"])
        events = monitor.check("FDA-42", "Title", "Desc", 0, current_labels=["Bug", "security"])
        assert len(events) == 1
        assert events[0].change_type == "labels"
        assert "security" in events[0].new_value

    def test_multiple_changes_in_one_check(self, tmp_path):
        monitor = self._setup(tmp_path, comments=1)
        events = monitor.check("FDA-42", "New Title", "New Desc", 3)
        change_types = {e.change_type for e in events}
        assert "title" in change_types
        assert "description" in change_types
        assert "new_comment" in change_types

    def test_check_updates_baseline(self, tmp_path):
        """After detecting a change, subsequent check should see no change."""
        monitor = self._setup(tmp_path)
        monitor.check("FDA-42", "New Title", "Desc", 0)
        # Second check with same data → no events
        events = monitor.check("FDA-42", "New Title", "Desc", 0)
        assert events == []

    def test_unregistered_issue_auto_registers(self, tmp_path):
        """check() on an unknown issue registers it as baseline, returns no events."""
        monitor = IssueMonitor(data_dir=tmp_path)
        events = monitor.check("FDA-99", "Title", "Desc", 0)
        assert events == []
        assert "FDA-99" in monitor.registered_issue_ids()

    def test_comment_count_decrease_ignored(self, tmp_path):
        """Comment count decreasing (e.g. deleted comment) does not trigger event."""
        monitor = self._setup(tmp_path, comments=5)
        events = monitor.check("FDA-42", "Title", "Desc", current_comment_count=3)
        assert not any(e.change_type == "new_comment" for e in events)

    def test_labels_sort_order_not_change(self, tmp_path):
        """Different ordering of same labels is not a change."""
        monitor = self._setup(tmp_path, labels=["Bug", "security"])
        events = monitor.check("FDA-42", "Title", "Desc", 0, current_labels=["security", "Bug"])
        assert not any(e.change_type == "labels" for e in events)


# ---------------------------------------------------------------------------
# IssueMonitor.watch tests
# ---------------------------------------------------------------------------


class TestIssueMonitorWatch:
    def test_watch_once_calls_callback(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-10", "Title", "Desc", comment_count=0)

        received: List[list] = []

        def _callback(events):
            received.append(events)

        def _fetch():
            return [_make_issue("FDA-10", "Title", "Desc", comment_count=1)]

        monitor.watch(_fetch, _callback, once=True)

        assert len(received) == 1
        assert len(received[0]) == 1
        assert received[0][0].change_type == "new_comment"

    def test_watch_once_no_changes_empty_callback(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-11", "Title", "Desc")

        received = []
        monitor.watch(
            lambda: [_make_issue("FDA-11", "Title", "Desc", 0)],
            lambda events: received.append(events),
            once=True,
        )
        assert received == [[]]

    def test_watch_specific_issue_filters_others(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-10", "Old Title", "Desc")
        monitor.register("FDA-11", "Old Title", "Desc")

        changed_ids = []

        def _callback(events):
            changed_ids.extend(e.issue_id for e in events)

        def _fetch():
            return [
                _make_issue("FDA-10", "New Title", "Desc"),
                _make_issue("FDA-11", "New Title", "Desc"),
            ]

        monitor.watch(_fetch, _callback, once=True, specific_issue="FDA-10")

        # Only FDA-10 processed
        assert "FDA-10" in changed_ids
        assert "FDA-11" not in changed_ids

    def test_watch_fetch_exception_does_not_crash(self, tmp_path):
        monitor = IssueMonitor(data_dir=tmp_path)
        called = []

        def _bad_fetch():
            raise RuntimeError("Linear API down")

        def _callback(events):
            called.append(events)

        # Should not raise
        monitor.watch(_bad_fetch, _callback, once=True)
        # callback not called because fetch raised
        assert called == []


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    def test_list_no_issues(self, tmp_path, capsys):
        rc = main(["--list", "--data-dir", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No issues" in out

    def test_list_with_issues(self, tmp_path, capsys):
        monitor = IssueMonitor(data_dir=tmp_path)
        monitor.register("FDA-100", "T", "D")
        rc = main(["--list", "--data-dir", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "FDA-100" in out

    def test_once_no_fetch_no_output(self, tmp_path, capsys):
        # --once with empty fetch returns 0
        rc = main(["--once", "--data-dir", str(tmp_path)])
        assert rc == 0

    def test_once_prints_no_changes(self, tmp_path, capsys):
        rc = main(["--once", "--data-dir", str(tmp_path)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No changes" in out
