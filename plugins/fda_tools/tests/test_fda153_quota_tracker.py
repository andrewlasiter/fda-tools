"""
OpenFDA Quota Tracker Tests (FDA-153).
========================================

Verifies that QuotaTracker provides accurate multi-window quota visibility
and returns correct degradation levels for the openFDA API rate limits.

Tests cover:
  - QuotaStatus dataclass helpers
  - QuotaTracker initialisation (with/without API key, custom limit)
  - record_request() persists timestamps to the state file
  - check_status() returns NORMAL when quota is low
  - check_status() returns WARNING at >= 70% utilisation
  - check_status() returns THROTTLED at >= 85% utilisation
  - check_status() returns BLOCKED at >= 100% utilisation
  - Multi-window counts (last minute / last hour / last day)
  - Timestamps older than 60 s are excluded from minute count
  - reset() clears all recorded timestamps
  - Corrupt state file falls back to empty (no crash)
  - QuotaLevel enum values match expected strings

Test count: 16
Target: pytest plugins/fda_tools/tests/test_fda153_quota_tracker.py -v
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fda_tools.lib.quota_tracker import (
    DEFAULT_LIMIT_WITH_KEY,
    DEFAULT_LIMIT_WITHOUT_KEY,
    THRESHOLD_THROTTLED,
    THRESHOLD_WARNING,
    QuotaLevel,
    QuotaStatus,
    QuotaTracker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tracker(tmp_path: Path, minute_limit: int = 10) -> QuotaTracker:
    """Return a QuotaTracker backed by a tmp directory."""
    return QuotaTracker(data_dir=str(tmp_path), minute_limit=minute_limit)


def _inject_timestamps(tmp_path: Path, timestamps: list[float]) -> None:
    """Write timestamps directly to the state file, bypassing the tracker."""
    state_path = tmp_path / ".quota_state.json"
    with open(state_path, "w") as f:
        json.dump({"timestamps": timestamps}, f)


# ---------------------------------------------------------------------------
# TestQuotaStatusDataclass
# ---------------------------------------------------------------------------


class TestQuotaStatusDataclass:
    def test_is_degraded_false_for_normal(self):
        s = QuotaStatus(
            level=QuotaLevel.NORMAL,
            requests_last_minute=1,
            requests_last_hour=1,
            requests_last_day=1,
            minute_limit=100,
            utilization_pct=0.01,
            available_this_minute=99,
            suggested_delay_seconds=0.0,
            message="ok",
        )
        assert s.is_degraded() is False

    def test_is_degraded_true_for_warning(self):
        s = QuotaStatus(
            level=QuotaLevel.WARNING,
            requests_last_minute=75,
            requests_last_hour=75,
            requests_last_day=75,
            minute_limit=100,
            utilization_pct=0.75,
            available_this_minute=25,
            suggested_delay_seconds=0.0,
            message="warning",
        )
        assert s.is_degraded() is True

    def test_as_dict_returns_level_string(self):
        s = QuotaStatus(
            level=QuotaLevel.THROTTLED,
            requests_last_minute=90,
            requests_last_hour=90,
            requests_last_day=90,
            minute_limit=100,
            utilization_pct=0.90,
            available_this_minute=10,
            suggested_delay_seconds=2.0,
            message="throttled",
        )
        d = s.as_dict()
        assert d["level"] == "THROTTLED"
        assert d["utilization_pct"] == 90.0


# ---------------------------------------------------------------------------
# TestQuotaTrackerInit
# ---------------------------------------------------------------------------


class TestQuotaTrackerInit:
    def test_default_limit_with_key(self, tmp_path):
        t = QuotaTracker(has_api_key=True, data_dir=str(tmp_path))
        assert t.minute_limit == DEFAULT_LIMIT_WITH_KEY

    def test_default_limit_without_key(self, tmp_path):
        t = QuotaTracker(has_api_key=False, data_dir=str(tmp_path))
        assert t.minute_limit == DEFAULT_LIMIT_WITHOUT_KEY

    def test_custom_limit_overrides_key_flag(self, tmp_path):
        t = QuotaTracker(has_api_key=True, data_dir=str(tmp_path), minute_limit=50)
        assert t.minute_limit == 50


# ---------------------------------------------------------------------------
# TestRecordRequest
# ---------------------------------------------------------------------------


class TestRecordRequest:
    def test_record_creates_state_file(self, tmp_path):
        t = _tracker(tmp_path)
        t.record_request()
        state_file = tmp_path / ".quota_state.json"
        assert state_file.exists()

    def test_record_increases_count(self, tmp_path):
        t = _tracker(tmp_path)
        t.record_request()
        t.record_request()
        status = t.check_status()
        assert status.requests_last_minute == 2

    def test_record_multiple_calls(self, tmp_path):
        t = _tracker(tmp_path, minute_limit=100)
        for _ in range(5):
            t.record_request()
        status = t.check_status()
        assert status.requests_last_minute == 5


# ---------------------------------------------------------------------------
# TestCheckStatus
# ---------------------------------------------------------------------------


class TestCheckStatus:
    def test_empty_state_is_normal(self, tmp_path):
        t = _tracker(tmp_path)
        status = t.check_status()
        assert status.level == QuotaLevel.NORMAL
        assert status.requests_last_minute == 0

    def test_normal_level_below_warning(self, tmp_path):
        # Use 60% of limit → NORMAL (below 70% threshold)
        limit = 10
        t = _tracker(tmp_path, minute_limit=limit)
        now = time.time()
        _inject_timestamps(tmp_path, [now - 5] * 6)  # 6/10 = 60%
        status = t.check_status()
        assert status.level == QuotaLevel.NORMAL
        assert status.suggested_delay_seconds == 0.0

    def test_warning_level_at_threshold(self, tmp_path):
        limit = 10
        t = _tracker(tmp_path, minute_limit=limit)
        # 70% of 10 = 7 requests
        count = int(THRESHOLD_WARNING * limit)
        now = time.time()
        _inject_timestamps(tmp_path, [now - 5] * count)
        status = t.check_status()
        assert status.level == QuotaLevel.WARNING

    def test_throttled_level_at_threshold(self, tmp_path):
        limit = 20
        t = _tracker(tmp_path, minute_limit=limit)
        # 85% of 20 = 17 requests
        count = int(THRESHOLD_THROTTLED * limit)
        now = time.time()
        _inject_timestamps(tmp_path, [now - 5] * count)
        status = t.check_status()
        assert status.level == QuotaLevel.THROTTLED
        assert status.suggested_delay_seconds > 0

    def test_blocked_level_at_limit(self, tmp_path):
        limit = 10
        t = _tracker(tmp_path, minute_limit=limit)
        now = time.time()
        _inject_timestamps(tmp_path, [now - 5] * limit)  # 100%
        status = t.check_status()
        assert status.level == QuotaLevel.BLOCKED
        assert status.suggested_delay_seconds > 0

    def test_available_decreases_as_requests_added(self, tmp_path):
        t = _tracker(tmp_path, minute_limit=10)
        for _ in range(3):
            t.record_request()
        status = t.check_status()
        assert status.available_this_minute == 7


# ---------------------------------------------------------------------------
# TestMultiWindowCounts
# ---------------------------------------------------------------------------


class TestMultiWindowCounts:
    def test_old_timestamps_excluded_from_minute_count(self, tmp_path):
        t = _tracker(tmp_path, minute_limit=100)
        now = time.time()
        # 5 old (> 60s ago), 3 recent
        _inject_timestamps(tmp_path, [now - 90] * 5 + [now - 10] * 3)
        status = t.check_status()
        assert status.requests_last_minute == 3

    def test_last_hour_includes_old_minute_timestamps(self, tmp_path):
        t = _tracker(tmp_path, minute_limit=100)
        now = time.time()
        # 4 at 30-min ago, 3 at 10s ago
        _inject_timestamps(tmp_path, [now - 1800] * 4 + [now - 10] * 3)
        status = t.check_status()
        assert status.requests_last_minute == 3
        assert status.requests_last_hour == 7

    def test_last_day_count(self, tmp_path):
        t = _tracker(tmp_path, minute_limit=100)
        now = time.time()
        # 2 at 12h ago, 2 at 1h ago, 2 at 10s ago
        _inject_timestamps(
            tmp_path,
            [now - 43200] * 2 + [now - 3600] * 2 + [now - 10] * 2,
        )
        status = t.check_status()
        assert status.requests_last_day == 6


# ---------------------------------------------------------------------------
# TestResetAndCorruption
# ---------------------------------------------------------------------------


class TestResetAndCorruption:
    def test_reset_clears_all_timestamps(self, tmp_path):
        t = _tracker(tmp_path, minute_limit=10)
        for _ in range(5):
            t.record_request()
        t.reset()
        status = t.check_status()
        assert status.requests_last_minute == 0
        assert status.requests_last_day == 0

    def test_corrupt_state_file_falls_back_gracefully(self, tmp_path):
        state_file = tmp_path / ".quota_state.json"
        state_file.write_text("not valid json{{{{")
        t = _tracker(tmp_path, minute_limit=10)
        status = t.check_status()
        assert status.level == QuotaLevel.NORMAL
        assert status.requests_last_minute == 0


# ---------------------------------------------------------------------------
# TestQuotaLevelEnum
# ---------------------------------------------------------------------------


class TestQuotaLevelEnum:
    def test_enum_string_values(self):
        assert QuotaLevel.NORMAL == "NORMAL"
        assert QuotaLevel.WARNING == "WARNING"
        assert QuotaLevel.THROTTLED == "THROTTLED"
        assert QuotaLevel.BLOCKED == "BLOCKED"

    def test_all_levels_in_enum(self):
        levels = {l.value for l in QuotaLevel}
        assert levels == {"NORMAL", "WARNING", "THROTTLED", "BLOCKED"}
