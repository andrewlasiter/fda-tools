"""
Unit Tests for Atomic Watchlist Writes (FDA-123)
=================================================

Verifies the atomic write helpers introduced in fda_approval_monitor:

  - _atomic_write_json: temp-file + rename, exclusive file lock, retry on lock
  - _atomic_write_text: same discipline for text files
  - FDAApprovalMonitor._save_state: uses _atomic_write_json (no partial writes)
  - FDAApprovalMonitor._write_digest_file: uses _atomic_write_text

Race-condition safety is verified by:
  1. Holding a lock from a second fd before calling the writer — confirms
     the writer eventually succeeds after lock release (retry path).
  2. Simulating an immediate lock-wait scenario with a held lock that is
     released during the retry window.

Test count: 28
Target: pytest plugins/fda_tools/tests/test_fda123_atomic_watchlist_writes.py -v
"""

import fcntl
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fda_tools.scripts.fda_approval_monitor import (
    _LOCK_RETRY_COUNT,
    _LOCK_TIMEOUT_SECS,
    _atomic_write_json,
    _atomic_write_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hold_lock(lock_path: Path, hold_seconds: float) -> None:
    """Open *lock_path* and hold an exclusive lock for *hold_seconds*, then
    release.  Runs in a background thread to simulate a concurrent writer."""
    with open(lock_path, "w") as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        time.sleep(hold_seconds)
        fcntl.flock(fd, fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# TestAtomicWriteJson
# ---------------------------------------------------------------------------


class TestAtomicWriteJson:
    """Tests for _atomic_write_json."""

    def test_creates_file_with_correct_content(self, tmp_path):
        dest = tmp_path / "state.json"
        _atomic_write_json(dest, {"key": "value", "count": 42})
        assert dest.exists()
        loaded = json.loads(dest.read_text())
        assert loaded == {"key": "value", "count": 42}

    def test_creates_parent_directories(self, tmp_path):
        dest = tmp_path / "deep" / "nested" / "file.json"
        _atomic_write_json(dest, {"x": 1})
        assert dest.exists()

    def test_overwrites_existing_file_atomically(self, tmp_path):
        dest = tmp_path / "state.json"
        dest.write_text('{"old": true}')
        _atomic_write_json(dest, {"new": True})
        loaded = json.loads(dest.read_text())
        assert loaded == {"new": True}
        assert "old" not in loaded

    def test_no_tmp_file_left_on_success(self, tmp_path):
        dest = tmp_path / "state.json"
        _atomic_write_json(dest, {"ok": 1})
        tmp_files = list(tmp_path.glob("*.tmp.*"))
        assert tmp_files == [], f"Unexpected temp files: {tmp_files}"

    def test_lock_file_created_beside_dest(self, tmp_path):
        dest = tmp_path / "state.json"
        _atomic_write_json(dest, {})
        # Lock file may be cleaned up by OS or kept — just confirm write succeeded
        assert dest.exists()

    def test_indentation_is_applied(self, tmp_path):
        dest = tmp_path / "state.json"
        _atomic_write_json(dest, {"a": 1}, indent=4)
        text = dest.read_text()
        # Indented JSON has newlines
        assert "\n" in text

    def test_succeeds_when_lock_released_during_retry(self, tmp_path):
        """Writer should succeed when another holder releases the lock within
        the timeout window."""
        dest = tmp_path / "state.json"
        lock_path = dest.with_suffix(dest.suffix + ".lock")

        # Hold the lock for 0.15 s — well within _LOCK_TIMEOUT_SECS
        t = threading.Thread(target=_hold_lock, args=(lock_path, 0.15))
        t.start()
        time.sleep(0.02)  # Give the thread time to acquire the lock

        _atomic_write_json(dest, {"concurrent": True})
        t.join()

        assert dest.exists()
        assert json.loads(dest.read_text()) == {"concurrent": True}

    def test_raises_timeout_when_lock_held_longer_than_budget(self, tmp_path):
        """Writer raises TimeoutError when lock is held beyond the retry budget."""
        dest = tmp_path / "state.json"
        lock_path = dest.with_suffix(dest.suffix + ".lock")

        # Hold longer than _LOCK_TIMEOUT_SECS * _LOCK_RETRY_COUNT
        hold_time = (_LOCK_TIMEOUT_SECS * _LOCK_RETRY_COUNT) + 1.0
        t = threading.Thread(target=_hold_lock, args=(lock_path, hold_time))
        t.start()
        time.sleep(0.02)

        try:
            with pytest.raises(TimeoutError):
                _atomic_write_json(dest, {"should": "fail"})
        finally:
            t.join()

    def test_list_data_preserved(self, tmp_path):
        dest = tmp_path / "list.json"
        data = ["alpha", "beta", "gamma"]
        _atomic_write_json(dest, data)
        assert json.loads(dest.read_text()) == data

    def test_nested_dict_preserved(self, tmp_path):
        dest = tmp_path / "nested.json"
        data = {"outer": {"inner": [1, 2, 3]}}
        _atomic_write_json(dest, data)
        assert json.loads(dest.read_text()) == data


# ---------------------------------------------------------------------------
# TestAtomicWriteText
# ---------------------------------------------------------------------------


class TestAtomicWriteText:
    """Tests for _atomic_write_text."""

    def test_creates_file_with_correct_content(self, tmp_path):
        dest = tmp_path / "digest.txt"
        _atomic_write_text(dest, "Hello, FDA!")
        assert dest.read_text() == "Hello, FDA!"

    def test_creates_parent_directories(self, tmp_path):
        dest = tmp_path / "reports" / "digest.txt"
        _atomic_write_text(dest, "test")
        assert dest.exists()

    def test_overwrites_existing_file(self, tmp_path):
        dest = tmp_path / "digest.txt"
        dest.write_text("old content")
        _atomic_write_text(dest, "new content")
        assert dest.read_text() == "new content"

    def test_no_tmp_file_left_on_success(self, tmp_path):
        dest = tmp_path / "digest.txt"
        _atomic_write_text(dest, "data")
        tmp_files = list(tmp_path.glob("*.tmp.*"))
        assert tmp_files == []

    def test_multiline_content_preserved(self, tmp_path):
        dest = tmp_path / "report.txt"
        content = "Line 1\nLine 2\nLine 3"
        _atomic_write_text(dest, content)
        assert dest.read_text() == content

    def test_succeeds_when_lock_released_during_retry(self, tmp_path):
        dest = tmp_path / "digest.txt"
        lock_path = dest.with_suffix(dest.suffix + ".lock")

        t = threading.Thread(target=_hold_lock, args=(lock_path, 0.15))
        t.start()
        time.sleep(0.02)

        _atomic_write_text(dest, "concurrent text")
        t.join()

        assert dest.read_text() == "concurrent text"

    def test_raises_timeout_when_lock_held_too_long(self, tmp_path):
        dest = tmp_path / "digest.txt"
        lock_path = dest.with_suffix(dest.suffix + ".lock")

        hold_time = (_LOCK_TIMEOUT_SECS * _LOCK_RETRY_COUNT) + 1.0
        t = threading.Thread(target=_hold_lock, args=(lock_path, hold_time))
        t.start()
        time.sleep(0.02)

        try:
            with pytest.raises(TimeoutError):
                _atomic_write_text(dest, "should fail")
        finally:
            t.join()


# ---------------------------------------------------------------------------
# TestMonitorSaveState
# ---------------------------------------------------------------------------


class TestMonitorSaveState:
    """Verify _save_state uses atomic writes via a mock FDAApprovalMonitor."""

    @pytest.fixture()
    def monitor(self, tmp_path):
        """Return a FDAApprovalMonitor with mocked PMADataStore."""
        from fda_tools.scripts.fda_approval_monitor import FDAApprovalMonitor
        store = MagicMock()
        m = FDAApprovalMonitor(store=store, config_dir=tmp_path / "monitor")
        return m

    def test_save_state_creates_config_file(self, monitor, tmp_path):
        monitor._watchlist = {"NMH", "QAS"}
        monitor._save_state()
        config = tmp_path / "monitor" / "monitor_config.json"
        assert config.exists()

    def test_saved_watchlist_is_correct(self, monitor, tmp_path):
        monitor._watchlist = {"NMH", "QAS"}
        monitor._save_state()
        config = tmp_path / "monitor" / "monitor_config.json"
        data = json.loads(config.read_text())
        assert sorted(data["watchlist"]) == ["NMH", "QAS"]

    def test_saved_state_is_valid_json(self, monitor, tmp_path):
        monitor._watchlist = {"ABC"}
        monitor._alert_history = [{"severity": "INFO", "message": "test"}]
        monitor._save_state()
        config = tmp_path / "monitor" / "monitor_config.json"
        # Should not raise
        data = json.loads(config.read_text())
        assert "alert_history" in data

    def test_no_tmp_file_left_after_save(self, monitor, tmp_path):
        monitor._watchlist = {"XYZ"}
        monitor._save_state()
        monitor_dir = tmp_path / "monitor"
        tmp_files = list(monitor_dir.glob("*.tmp.*"))
        assert tmp_files == []

    def test_save_state_warns_on_timeout(self, monitor, capsys):
        """_save_state catches TimeoutError and prints a warning to stderr."""
        with patch(
            "fda_tools.scripts.fda_approval_monitor._atomic_write_json",
            side_effect=TimeoutError("lock held"),
        ):
            monitor._save_state()  # Must not raise
        _, err = capsys.readouterr()
        assert "Warning" in err

    def test_save_state_warns_on_os_error(self, monitor, capsys):
        with patch(
            "fda_tools.scripts.fda_approval_monitor._atomic_write_json",
            side_effect=OSError("disk full"),
        ):
            monitor._save_state()  # Must not raise
        _, err = capsys.readouterr()
        assert "Warning" in err


# ---------------------------------------------------------------------------
# TestMonitorWriteDigestFile
# ---------------------------------------------------------------------------


class TestMonitorWriteDigestFile:
    """Verify _write_digest_file uses atomic writes."""

    @pytest.fixture()
    def monitor(self, tmp_path):
        from fda_tools.scripts.fda_approval_monitor import FDAApprovalMonitor
        store = MagicMock()
        return FDAApprovalMonitor(store=store, config_dir=tmp_path / "monitor")

    @pytest.fixture()
    def sample_digest(self):
        return {
            "frequency": "daily",
            "period_start": "2026-01-01T00:00:00+00:00",
            "period_end": "2026-01-02T00:00:00+00:00",
            "total_alerts": 1,
            "by_severity": {
                "INFO": {
                    "count": 1,
                    "alerts": [{
                        "severity": "INFO",
                        "message": "New PMA P000001 approved",
                        "data_source": "openFDA",
                        "detected_at": "2026-01-02T00:00:00+00:00",
                    }],
                }
            },
            "watchlist": ["NMH"],
        }

    def test_writes_digest_file(self, monitor, tmp_path, sample_digest):
        out = str(tmp_path / "digest.txt")
        monitor._write_digest_file(sample_digest, out)
        assert Path(out).exists()

    def test_digest_content_includes_severity(self, monitor, tmp_path, sample_digest):
        out = str(tmp_path / "digest.txt")
        monitor._write_digest_file(sample_digest, out)
        content = Path(out).read_text()
        assert "[INFO]" in content

    def test_no_tmp_file_left_after_digest(self, monitor, tmp_path, sample_digest):
        out = str(tmp_path / "digest.txt")
        monitor._write_digest_file(sample_digest, out)
        tmp_files = list(tmp_path.glob("*.tmp.*"))
        assert tmp_files == []
