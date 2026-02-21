"""Tests for LinearIssueWatcher (FDA-213 / ORCH-009).

Coverage:
- SubstanceDetector: classifies comments as substantial vs informational
- LinearIssueWatcher._check_issue: detects changes, ignores no-change
- LinearIssueWatcher state persistence: load / save round-trip
- LinearIssueWatcher.watch: yields updates, stops on shutdown flag
- post_rereview_comment: formats comment correctly, raises on non-substantial
- _parse_iso: handles Z suffix, offset notation, naive datetimes
"""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from fda_tools.scripts.linear_issue_watcher import (
    IssueUpdate,
    LinearIssueWatcher,
    SubstanceDetector,
    _parse_iso,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_update(
    issue_id: str = "FDA-83",
    updated_at: str = "2026-02-21T10:00:00Z",
    comments: list | None = None,
    description_changed: bool = False,
) -> IssueUpdate:
    """Build a minimal IssueUpdate for testing."""
    return IssueUpdate(
        issue_id=issue_id,
        updated_at=_parse_iso(updated_at),
        new_comments=comments or [],
        description_changed=description_changed,
    )


def _make_watcher(tmp_path: Path, responses: dict | None = None) -> LinearIssueWatcher:
    """Build a watcher with a fake linear client backed by *responses* dict.

    *responses* maps issue_id → data dict returned by the client.
    Missing keys → stub (no change).
    """
    responses = responses or {}

    def fake_client(issue_id: str) -> dict:
        return responses.get(
            issue_id,
            {"updatedAt": "", "comments": [], "descriptionChanged": False, "statusChanged": False},
        )

    return LinearIssueWatcher(
        poll_interval_seconds=60,
        state_dir=tmp_path,
        linear_client=fake_client,
    )


# ---------------------------------------------------------------------------
# SubstanceDetector
# ---------------------------------------------------------------------------


class TestSubstanceDetector:
    """Tests for SubstanceDetector.classify()."""

    def setup_method(self):
        self.detector = SubstanceDetector()

    def _classify(self, comment: str, description_changed: bool = False) -> IssueUpdate:
        upd = _make_update(comments=[comment], description_changed=description_changed)
        return self.detector.classify(upd)

    # Substantial signals ---------------------------------------------------

    def test_pr_link_is_substantial(self):
        upd = self._classify("See https://github.com/owner/repo/pull/123 for the fix")
        assert upd.is_substantial

    def test_pr_hashtag_is_substantial(self):
        upd = self._classify("Addressed in PR #456")
        assert upd.is_substantial

    def test_fixed_keyword_is_substantial(self):
        upd = self._classify("Fixed the issue in commit abc1234")
        assert upd.is_substantial

    def test_implemented_keyword_is_substantial(self):
        upd = self._classify("Implemented the retry logic in api_client.py")
        assert upd.is_substantial

    def test_resolved_keyword_is_substantial(self):
        upd = self._classify("This is now resolved.")
        assert upd.is_substantial

    def test_merged_keyword_is_substantial(self):
        upd = self._classify("Branch merged to main.")
        assert upd.is_substantial

    def test_ready_for_review_is_substantial(self):
        upd = self._classify("Ready for review — all tests pass.")
        assert upd.is_substantial

    def test_commit_hash_is_substantial(self):
        upd = self._classify("commit a1b2c3d4e5f6 addresses the issue")
        assert upd.is_substantial

    def test_description_changed_is_substantial(self):
        upd = self._classify("", description_changed=True)
        assert upd.is_substantial

    # Informational signals -------------------------------------------------

    def test_fyi_comment_is_informational(self):
        upd = self._classify("FYI, I'm looking into this.")
        assert not upd.is_substantial

    def test_blocked_comment_is_informational(self):
        upd = self._classify("Still blocked by the API key issue.")
        assert not upd.is_substantial

    def test_in_progress_is_informational(self):
        upd = self._classify("This is in progress, will update tomorrow.")
        assert not upd.is_substantial

    def test_empty_comment_is_informational(self):
        upd = self._classify("")
        assert not upd.is_substantial

    def test_will_do_is_informational(self):
        upd = self._classify("Will do, thanks for the reminder.")
        assert not upd.is_substantial

    # Substance reason field ------------------------------------------------

    def test_reason_populated_for_substantial(self):
        upd = self._classify("Fixed the bug in auth.py")
        assert upd.is_substantial
        assert upd.substance_reason  # non-empty

    def test_reason_is_no_signal_for_empty_update(self):
        upd = _make_update()
        self.detector.classify(upd)
        assert upd.substance_reason == "no signal"


# ---------------------------------------------------------------------------
# LinearIssueWatcher._check_issue
# ---------------------------------------------------------------------------


class TestCheckIssue:
    """Tests for the _check_issue polling helper."""

    def test_no_change_returns_empty(self, tmp_path):
        watcher = _make_watcher(tmp_path, responses={
            "FDA-83": {"updatedAt": "2026-02-21T09:00:00Z", "comments": [], "descriptionChanged": False, "statusChanged": False},
        })
        # Prime last_seen to the same timestamp.
        watcher._last_seen["FDA-83"] = "2026-02-21T09:00:00Z"
        updates = watcher._check_issue("FDA-83")
        assert updates == []

    def test_new_timestamp_returns_update(self, tmp_path):
        watcher = _make_watcher(tmp_path, responses={
            "FDA-83": {
                "updatedAt": "2026-02-21T10:00:00Z",
                "comments": [{"body": "Fixed in PR #7", "createdAt": "2026-02-21T10:00:00Z"}],
                "descriptionChanged": False,
                "statusChanged": False,
            },
        })
        watcher._last_seen["FDA-83"] = "2026-02-21T09:00:00Z"
        updates = watcher._check_issue("FDA-83")
        assert len(updates) == 1
        assert updates[0].issue_id == "FDA-83"

    def test_first_poll_with_no_prior_state_returns_update(self, tmp_path):
        watcher = _make_watcher(tmp_path, responses={
            "FDA-96": {
                "updatedAt": "2026-02-21T08:00:00Z",
                "comments": [],
                "descriptionChanged": False,
                "statusChanged": False,
            },
        })
        # No prior state for FDA-96 → any non-empty updatedAt triggers update.
        updates = watcher._check_issue("FDA-96")
        assert len(updates) == 1

    def test_last_seen_updated_after_detection(self, tmp_path):
        watcher = _make_watcher(tmp_path, responses={
            "FDA-83": {
                "updatedAt": "2026-02-21T11:00:00Z",
                "comments": [],
                "descriptionChanged": True,
                "statusChanged": False,
            },
        })
        watcher._last_seen["FDA-83"] = "2026-02-21T09:00:00Z"
        watcher._check_issue("FDA-83")
        assert watcher._last_seen["FDA-83"] == "2026-02-21T11:00:00Z"

    def test_substantial_update_classified(self, tmp_path):
        watcher = _make_watcher(tmp_path, responses={
            "FDA-83": {
                "updatedAt": "2026-02-21T12:00:00Z",
                "comments": [{"body": "Merged PR #9", "createdAt": "2026-02-21T12:00:00Z"}],
                "descriptionChanged": False,
                "statusChanged": False,
            },
        })
        updates = watcher._check_issue("FDA-83")
        assert updates[0].is_substantial

    def test_informational_update_classified(self, tmp_path):
        watcher = _make_watcher(tmp_path, responses={
            "FDA-83": {
                "updatedAt": "2026-02-21T12:00:00Z",
                "comments": [{"body": "FYI, I'm looking at this.", "createdAt": "2026-02-21T12:00:00Z"}],
                "descriptionChanged": False,
                "statusChanged": False,
            },
        })
        updates = watcher._check_issue("FDA-83")
        assert not updates[0].is_substantial


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """Tests for load/save round-trip of last_seen timestamps."""

    def test_save_and_reload(self, tmp_path):
        watcher = _make_watcher(tmp_path)
        watcher._last_seen = {"FDA-83": "2026-02-21T10:00:00Z", "FDA-96": "2026-02-21T09:00:00Z"}
        watcher._save_state()

        watcher2 = _make_watcher(tmp_path)
        assert watcher2._last_seen["FDA-83"] == "2026-02-21T10:00:00Z"
        assert watcher2._last_seen["FDA-96"] == "2026-02-21T09:00:00Z"

    def test_corrupted_state_file_returns_empty(self, tmp_path):
        state_file = tmp_path / "linear_watcher_state.json"
        state_file.write_text("not json", encoding="utf-8")
        watcher = _make_watcher(tmp_path)
        assert watcher._last_seen == {}

    def test_missing_state_file_returns_empty(self, tmp_path):
        watcher = _make_watcher(tmp_path)
        assert watcher._last_seen == {}

    def test_atomic_write_uses_tmp_file(self, tmp_path):
        """_save_state should write via a .tmp file to avoid partial writes."""
        watcher = _make_watcher(tmp_path)
        watcher._last_seen = {"FDA-83": "2026-02-21T10:00:00Z"}
        watcher._save_state()
        # After save, only the final file should exist.
        tmp_file = tmp_path / "linear_watcher_state.tmp"
        assert not tmp_file.exists()
        state_file = tmp_path / "linear_watcher_state.json"
        assert state_file.exists()


# ---------------------------------------------------------------------------
# post_rereview_comment
# ---------------------------------------------------------------------------


class TestPostRereviewComment:
    """Tests for re-review comment formatting."""

    def test_raises_on_non_substantial_update(self, tmp_path):
        watcher = _make_watcher(tmp_path)
        upd = _make_update(comments=["FYI, noted."])
        SubstanceDetector().classify(upd)
        assert not upd.is_substantial
        with pytest.raises(ValueError):
            watcher.post_rereview_comment(upd)

    def test_comment_contains_rereview_tag(self, tmp_path):
        watcher = _make_watcher(tmp_path)
        upd = _make_update(comments=["Fixed in PR #42"])
        SubstanceDetector().classify(upd)
        comment = watcher.post_rereview_comment(upd)
        assert "[Re-review" in comment

    def test_comment_contains_issue_id(self, tmp_path):
        watcher = _make_watcher(tmp_path)
        upd = _make_update(issue_id="FDA-96", comments=["Resolved and merged."])
        SubstanceDetector().classify(upd)
        comment = watcher.post_rereview_comment(upd)
        assert "FDA-96" in comment

    def test_comment_contains_substance_reason(self, tmp_path):
        watcher = _make_watcher(tmp_path)
        upd = _make_update(comments=["Ready for review — tests pass"])
        SubstanceDetector().classify(upd)
        comment = watcher.post_rereview_comment(upd)
        assert upd.substance_reason in comment

    def test_custom_orchestrator_output_included(self, tmp_path):
        def my_orchestrator(_issue_id, _context):
            return "**No critical findings.**"

        watcher = LinearIssueWatcher(
            poll_interval_seconds=60,
            state_dir=tmp_path,
            orchestrator=my_orchestrator,
        )
        upd = _make_update(comments=["Implemented the retry logic."])
        SubstanceDetector().classify(upd)
        comment = watcher.post_rereview_comment(upd)
        assert "**No critical findings.**" in comment


# ---------------------------------------------------------------------------
# watch() generator — early shutdown
# ---------------------------------------------------------------------------


class TestWatchGenerator:
    """Tests for the watch() generator behaviour."""

    def test_watch_yields_updates_then_stops(self, tmp_path):
        """watch() yields one update then stops when _shutdown is set."""
        call_count = 0

        def counting_client(issue_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {
                "updatedAt": f"2026-02-21T10:0{call_count}:00Z",
                "comments": [],
                "descriptionChanged": False,
                "statusChanged": False,
            }

        watcher = LinearIssueWatcher(
            poll_interval_seconds=0,  # No sleep so test runs fast.
            state_dir=tmp_path,
            linear_client=counting_client,
        )

        collected = []

        def _run():
            for upd in watcher.watch(["FDA-83"]):
                collected.append(upd)
                watcher._shutdown = True  # Stop after first update.

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=5.0)
        assert not t.is_alive(), "watch() did not stop within timeout"
        assert len(collected) == 1
        assert collected[0].issue_id == "FDA-83"

    def test_watch_skips_unchanged_issues(self, tmp_path):
        """watch() yields nothing when all issues report the same updatedAt."""
        watcher = _make_watcher(tmp_path, responses={
            "FDA-83": {"updatedAt": "2026-02-21T09:00:00Z", "comments": [], "descriptionChanged": False, "statusChanged": False},
        })
        watcher._last_seen["FDA-83"] = "2026-02-21T09:00:00Z"  # Already seen.

        collected = []

        def _run():
            for upd in watcher.watch(["FDA-83"]):
                collected.append(upd)
            # Generator won't exit on its own without a shutdown; set flag.

        # Trigger shutdown after one poll cycle completes.
        def _stopper():
            time.sleep(0.2)
            watcher._shutdown = True

        t_run = threading.Thread(target=_run)
        t_stop = threading.Thread(target=_stopper)
        t_run.start()
        t_stop.start()
        t_run.join(timeout=5.0)
        t_stop.join(timeout=1.0)

        assert len(collected) == 0


# ---------------------------------------------------------------------------
# _parse_iso helper
# ---------------------------------------------------------------------------


class TestParseIso:
    """Tests for ISO-8601 parsing helper."""

    def test_z_suffix(self):
        dt = _parse_iso("2026-02-21T10:00:00Z")
        assert dt.tzinfo is not None
        assert dt.year == 2026

    def test_offset_notation(self):
        dt = _parse_iso("2026-02-21T10:00:00+00:00")
        assert dt.tzinfo is not None

    def test_naive_gets_utc(self):
        dt = _parse_iso("2026-02-21T10:00:00")
        assert dt.tzinfo == timezone.utc

    def test_invalid_raises(self):
        with pytest.raises((ValueError, TypeError)):
            _parse_iso("not-a-date")
