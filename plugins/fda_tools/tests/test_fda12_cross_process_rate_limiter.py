#!/usr/bin/env python3
"""
Tests for FDA-12: Cross-Process Rate Limit Tracking.

Tests the CrossProcessRateLimiter for:
- Basic rate limiting with file-based lock
- Cross-process coordination via shared state file
- openFDA rate limit configuration (240/min with key, 40/min without)
- Health check output
- Concurrent access from multiple threads (simulating multiple processes)
- State file management (read/write/prune)
- Timeout handling
- Reset functionality
"""

import json
import os
import sys
import tempfile
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add lib directory to path
_lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")

# Add scripts directory to path
_scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")

from cross_process_rate_limiter import (
    CrossProcessRateLimiter,
    RATE_LIMIT_WITH_KEY,
    RATE_LIMIT_WITHOUT_KEY,
    WINDOW_SIZE_SECONDS,
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for rate limiter files."""
    tmpdir = tempfile.mkdtemp(prefix="fda_test_ratelimit_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def limiter(temp_data_dir):
    """Create a CrossProcessRateLimiter with test directory."""
    return CrossProcessRateLimiter(
        has_api_key=True,
        data_dir=temp_data_dir,
    )


@pytest.fixture
def limiter_no_key(temp_data_dir):
    """Create a CrossProcessRateLimiter without API key."""
    return CrossProcessRateLimiter(
        has_api_key=False,
        data_dir=temp_data_dir,
    )


class TestInitialization:
    """Tests for rate limiter initialization."""

    def test_init_with_api_key(self, temp_data_dir):
        """Test initialization with API key uses 240 req/min."""
        limiter = CrossProcessRateLimiter(has_api_key=True, data_dir=temp_data_dir)
        assert limiter.requests_per_minute == RATE_LIMIT_WITH_KEY
        assert limiter.requests_per_minute == 240

    def test_init_without_api_key(self, temp_data_dir):
        """Test initialization without API key uses 40 req/min."""
        limiter = CrossProcessRateLimiter(has_api_key=False, data_dir=temp_data_dir)
        assert limiter.requests_per_minute == RATE_LIMIT_WITHOUT_KEY
        assert limiter.requests_per_minute == 40

    def test_init_custom_rate(self, temp_data_dir):
        """Test initialization with custom rate limit."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=100,
        )
        assert limiter.requests_per_minute == 100

    def test_init_creates_directory(self):
        """Test that init creates the data directory if needed."""
        tmpdir = tempfile.mkdtemp(prefix="fda_test_")
        try:
            subdir = os.path.join(tmpdir, "nested", "dir")
            limiter = CrossProcessRateLimiter(
                has_api_key=True,
                data_dir=subdir,
            )
            assert os.path.exists(subdir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_lock_and_state_paths(self, temp_data_dir):
        """Test lock and state file paths are correctly set."""
        limiter = CrossProcessRateLimiter(has_api_key=True, data_dir=temp_data_dir)
        assert str(limiter.lock_path).endswith(".rate_limit.lock")
        assert str(limiter.state_path).endswith(".rate_limit_state.json")
        assert str(limiter.data_dir) == temp_data_dir


class TestAcquire:
    """Tests for rate limit acquisition."""

    def test_acquire_under_limit(self, limiter):
        """Test acquire succeeds when under the limit."""
        result = limiter.acquire(timeout=5.0)
        assert result is True

    def test_acquire_multiple_under_limit(self, limiter):
        """Test multiple acquires succeed when under limit."""
        for _ in range(10):
            assert limiter.acquire(timeout=5.0) is True

    def test_acquire_records_timestamp(self, limiter):
        """Test that acquire records a timestamp in the state file."""
        limiter.acquire(timeout=5.0)
        status = limiter.get_status()
        assert status["requests_last_minute"] == 1

    def test_acquire_respects_limit(self, temp_data_dir):
        """Test that acquire blocks when at the limit."""
        # Use very low limit for testing
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=3,
        )
        # Fill up the limit
        for _ in range(3):
            assert limiter.acquire(timeout=5.0) is True

        # Next acquire should timeout (limit reached, window not expired)
        result = limiter.acquire(timeout=1.0)
        assert result is False

    def test_acquire_timeout_returns_false(self, temp_data_dir):
        """Test that acquire returns False on timeout."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=1,
        )
        limiter.acquire(timeout=5.0)  # Use the one allowed request
        result = limiter.acquire(timeout=0.5)  # Should timeout
        assert result is False


class TestRecordRequest:
    """Tests for manual request recording."""

    def test_record_request_increments_count(self, limiter):
        """Test that record_request increases the request count."""
        limiter.record_request()
        status = limiter.get_status()
        assert status["requests_last_minute"] == 1

    def test_record_multiple_requests(self, limiter):
        """Test recording multiple requests."""
        for _ in range(5):
            limiter.record_request()
        status = limiter.get_status()
        assert status["requests_last_minute"] == 5


class TestGetStatus:
    """Tests for rate limit status reporting."""

    def test_status_fields(self, limiter):
        """Test that get_status returns all expected fields."""
        status = limiter.get_status()
        assert "requests_last_minute" in status
        assert "requests_per_minute" in status
        assert "utilization_percent" in status
        assert "available" in status
        assert "state_file" in status
        assert "lock_file" in status
        assert "pid" in status

    def test_status_empty_state(self, limiter):
        """Test status on fresh limiter shows zero requests."""
        status = limiter.get_status()
        assert status["requests_last_minute"] == 0
        assert status["utilization_percent"] == 0.0
        assert status["available"] == limiter.requests_per_minute

    def test_status_after_requests(self, limiter):
        """Test status accurately reflects request count."""
        for _ in range(5):
            limiter.acquire(timeout=5.0)
        status = limiter.get_status()
        assert status["requests_last_minute"] == 5
        assert status["available"] == limiter.requests_per_minute - 5

    def test_status_utilization_percentage(self, temp_data_dir):
        """Test utilization percentage calculation."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=100,
        )
        for _ in range(50):
            limiter.record_request()
        status = limiter.get_status()
        assert status["utilization_percent"] == 50.0


class TestHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_fresh(self, limiter):
        """Test health check on fresh limiter."""
        health = limiter.health_check()
        assert health["healthy"] is True
        assert isinstance(health["warnings"], list)

    def test_health_check_after_requests(self, limiter):
        """Test health check after some requests."""
        for _ in range(5):
            limiter.acquire(timeout=5.0)
        health = limiter.health_check()
        assert health["healthy"] is True
        assert health["status"]["requests_last_minute"] == 5

    def test_health_check_high_utilization_warning(self, temp_data_dir):
        """Test health check warns on high utilization."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=10,
        )
        for _ in range(9):
            limiter.record_request()
        health = limiter.health_check()
        assert any("utilization" in w.lower() for w in health["warnings"])

    def test_health_check_shows_file_status(self, limiter):
        """Test health check reports file existence."""
        # Before any operation, state file may not exist
        health = limiter.health_check()
        assert "lock_exists" in health
        assert "state_exists" in health
        assert "state_readable" in health


class TestReset:
    """Tests for state reset."""

    def test_reset_clears_timestamps(self, limiter):
        """Test that reset clears all recorded timestamps."""
        for _ in range(10):
            limiter.record_request()
        status_before = limiter.get_status()
        assert status_before["requests_last_minute"] == 10

        limiter.reset()
        status_after = limiter.get_status()
        assert status_after["requests_last_minute"] == 0


class TestConcurrentAccess:
    """Tests for concurrent access from multiple threads."""

    def test_concurrent_acquires(self, temp_data_dir):
        """Test that concurrent acquires from multiple threads are safe."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=200,
        )

        results = []
        errors = []

        def worker():
            try:
                for _ in range(10):
                    result = limiter.acquire(timeout=10.0)
                    results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Errors in concurrent threads: {errors}"
        assert all(r is True for r in results)
        assert len(results) == 50  # 5 threads * 10 requests

    def test_concurrent_record_and_status(self, temp_data_dir):
        """Test concurrent record_request and get_status calls."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=200,
        )

        errors = []
        request_count = [0]

        def recorder():
            try:
                for _ in range(20):
                    limiter.record_request()
                    request_count[0] += 1
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"recorder: {e}")

        def status_checker():
            try:
                for _ in range(10):
                    status = limiter.get_status()
                    assert "requests_last_minute" in status
                    time.sleep(0.02)
            except Exception as e:
                errors.append(f"checker: {e}")

        threads = [
            threading.Thread(target=recorder),
            threading.Thread(target=recorder),
            threading.Thread(target=status_checker),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Errors: {errors}"

    def test_concurrent_does_not_exceed_limit(self, temp_data_dir):
        """Test that concurrent access respects the rate limit."""
        limit = 20
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_data_dir,
            requests_per_minute=limit,
        )

        acquired_count = [0]
        lock = threading.Lock()

        def worker():
            for _ in range(10):
                if limiter.acquire(timeout=2.0):
                    with lock:
                        acquired_count[0] += 1

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # Total acquired should not exceed the rate limit
        assert acquired_count[0] <= limit


class TestStateFileManagement:
    """Tests for state file read/write/prune operations."""

    def test_state_file_created_on_first_acquire(self, limiter):
        """Test state file is created on first request."""
        assert not limiter.state_path.exists()
        limiter.acquire(timeout=5.0)
        assert limiter.state_path.exists()

    def test_state_file_valid_json(self, limiter):
        """Test state file contains valid JSON."""
        limiter.acquire(timeout=5.0)
        with open(limiter.state_path) as f:
            state = json.load(f)
        assert "timestamps" in state
        assert isinstance(state["timestamps"], list)

    def test_corrupted_state_file_handled(self, limiter):
        """Test that a corrupted state file is handled gracefully."""
        # Write garbage to state file
        limiter.state_path.write_text("NOT VALID JSON {{{")

        # Should still work (resets state)
        result = limiter.acquire(timeout=5.0)
        assert result is True
        status = limiter.get_status()
        assert status["requests_last_minute"] >= 1

    def test_timestamp_pruning(self, limiter):
        """Test that old timestamps are pruned from state."""
        # Manually write old timestamps
        old_time = time.time() - 120  # 2 minutes ago (outside window)
        state = {
            "timestamps": [old_time, old_time + 1, old_time + 2],
            "version": "1.0.0",
        }
        # Write state file directly
        with open(limiter.state_path, "w") as f:
            json.dump(state, f)

        # Acquire should prune old timestamps
        limiter.acquire(timeout=5.0)
        status = limiter.get_status()
        # Only the new request should count (old ones pruned)
        assert status["requests_last_minute"] == 1


class TestIntegrationWithFDAClient:
    """Tests for integration with FDAClient."""

    def test_fda_client_has_cross_process_limiter(self):
        """Test FDAClient creates cross-process limiter when available."""
        try:
            from fda_api_client import FDAClient, _CROSS_PROCESS_LIMITER_AVAILABLE
            if _CROSS_PROCESS_LIMITER_AVAILABLE:
                client = FDAClient()
                assert client._cross_process_limiter is not None
        except ImportError:
            pytest.skip("FDAClient not importable")

    def test_cache_stats_includes_cross_process(self):
        """Test cache_stats includes cross-process rate limit info."""
        try:
            from fda_api_client import FDAClient, _CROSS_PROCESS_LIMITER_AVAILABLE
            if _CROSS_PROCESS_LIMITER_AVAILABLE:
                client = FDAClient()
                stats = client.cache_stats()
                assert "cross_process_rate_limit" in stats
                xp = stats["cross_process_rate_limit"]
                assert "requests_last_minute" in xp
                assert "requests_per_minute" in xp
        except ImportError:
            pytest.skip("FDAClient not importable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
