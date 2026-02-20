#!/usr/bin/env python3
"""
Cross-process rate limiter for FDA API requests (FDA-12).

Uses a file-based lock and shared timestamp log to coordinate rate limiting
across multiple concurrent processes (e.g., batchfetch, change_detector,
data_refresh_orchestrator running simultaneously).

The rate limiter stores request timestamps in a shared JSON file protected by
a file lock (fcntl.flock on Unix). Each process reads the shared state before
making a request to determine if the rate limit would be exceeded.

openFDA rate limits:
    - With API key: 240 requests per minute (4/sec)
    - Without API key: 40 requests per minute (~0.67/sec)

Lock file: ~/fda-510k-data/.rate_limit.lock
State file: ~/fda-510k-data/.rate_limit_state.json

Usage:
from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter

    limiter = CrossProcessRateLimiter(has_api_key=True)
    limiter.acquire()  # Blocks until safe to make a request
    # ... make API request ...

    # Check status:
    status = limiter.get_status()
    print(f"Requests in last minute: {status['requests_last_minute']}")
"""

import fcntl
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_DATA_DIR = os.path.expanduser("~/fda-510k-data")
LOCK_FILE = ".rate_limit.lock"
STATE_FILE = ".rate_limit_state.json"

# openFDA rate limits
RATE_LIMIT_WITH_KEY = 240      # requests per minute with API key
RATE_LIMIT_WITHOUT_KEY = 40    # requests per minute without API key

# Sliding window size in seconds
WINDOW_SIZE_SECONDS = 60

# Maximum wait time before giving up (seconds)
MAX_WAIT_SECONDS = 120

# Polling interval when waiting for rate limit (seconds)
POLL_INTERVAL = 0.25


class CrossProcessRateLimiter:
    """File-based cross-process rate limiter for openFDA API.

    Uses fcntl.flock() for mutual exclusion across processes. Maintains
    a shared JSON state file with recent request timestamps to enforce
    a sliding window rate limit.

    Thread-safety: This class is also thread-safe within a single process
    because file locks work at the OS level.
    """

    def __init__(
        self,
        has_api_key: bool = True,
        data_dir: Optional[str] = None,
        requests_per_minute: Optional[int] = None,
    ):
        """Initialize the cross-process rate limiter.

        Args:
            has_api_key: Whether an openFDA API key is configured.
                True = 240 req/min, False = 40 req/min.
            data_dir: Directory for lock and state files.
                Default: ~/fda-510k-data/
            requests_per_minute: Override rate limit. If None, uses
                240 (with key) or 40 (without key).
        """
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.lock_path = self.data_dir / LOCK_FILE
        self.state_path = self.data_dir / STATE_FILE

        if requests_per_minute is not None:
            self.requests_per_minute = requests_per_minute
        elif has_api_key:
            self.requests_per_minute = RATE_LIMIT_WITH_KEY
        else:
            self.requests_per_minute = RATE_LIMIT_WITHOUT_KEY

        self._pid = os.getpid()

        logger.info(
            "CrossProcessRateLimiter initialized: %d req/min, pid=%d, "
            "lock=%s, state=%s",
            self.requests_per_minute,
            self._pid,
            self.lock_path,
            self.state_path,
        )

    def _read_state(self) -> Dict[str, Any]:
        """Read the shared rate limit state file.

        Must be called while holding the file lock.

        Returns:
            State dictionary with 'timestamps' list and metadata.
        """
        if not self.state_path.exists():
            return {
                "timestamps": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            }

        try:
            with open(self.state_path, "r") as f:
                state = json.load(f)
            if not isinstance(state.get("timestamps"), list):
                state["timestamps"] = []
            return state
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read rate limit state: %s. Resetting.", e)
            return {
                "timestamps": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "reset_reason": str(e),
            }

    def _write_state(self, state: Dict[str, Any]) -> None:
        """Write the shared rate limit state file atomically.

        Must be called while holding the file lock.

        Args:
            state: State dictionary to persist.
        """
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        state["last_pid"] = self._pid

        tmp_path = self.state_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(state, f)
            tmp_path.replace(self.state_path)
        except OSError as e:
            logger.error("Failed to write rate limit state: %s", e)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _prune_old_timestamps(self, timestamps: List[float], now: float) -> List[float]:
        """Remove timestamps outside the sliding window.

        Args:
            timestamps: List of Unix timestamps.
            now: Current time.

        Returns:
            Filtered list containing only timestamps within the last WINDOW_SIZE_SECONDS.
        """
        cutoff = now - WINDOW_SIZE_SECONDS
        return [ts for ts in timestamps if ts > cutoff]

    def _count_in_window(self, timestamps: List[float], now: float) -> int:
        """Count requests in the current sliding window.

        Args:
            timestamps: List of Unix timestamps (should already be pruned).
            now: Current time.

        Returns:
            Number of requests within the last WINDOW_SIZE_SECONDS.
        """
        cutoff = now - WINDOW_SIZE_SECONDS
        return sum(1 for ts in timestamps if ts > cutoff)

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make an API request.

        Blocks until the rate limit allows a new request, or until the
        timeout expires.

        Args:
            timeout: Maximum seconds to wait. None defaults to MAX_WAIT_SECONDS.

        Returns:
            True if permission acquired, False if timeout expired.
        """
        timeout = timeout if timeout is not None else MAX_WAIT_SECONDS
        deadline = time.time() + timeout

        while True:
            now = time.time()
            if now >= deadline:
                logger.warning(
                    "CrossProcessRateLimiter: timeout after %.1fs waiting for rate limit",
                    timeout,
                )
                return False

            try:
                # Open (or create) the lock file
                lock_fd = open(self.lock_path, "w")
                try:
                    # Acquire exclusive file lock (blocks across processes)
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    # Another process holds the lock; wait and retry
                    lock_fd.close()
                    time.sleep(POLL_INTERVAL)
                    continue

                try:
                    state = self._read_state()
                    timestamps = self._prune_old_timestamps(state["timestamps"], now)
                    count = len(timestamps)

                    if count < self.requests_per_minute:
                        # Under the limit: record this request and proceed
                        timestamps.append(now)
                        state["timestamps"] = timestamps
                        self._write_state(state)
                        logger.debug(
                            "Rate limit acquired: %d/%d in window (pid=%d)",
                            count + 1,
                            self.requests_per_minute,
                            self._pid,
                        )
                        return True
                    else:
                        # At the limit: calculate wait time
                        oldest = min(timestamps)
                        wait_until = oldest + WINDOW_SIZE_SECONDS
                        wait_seconds = max(0.1, wait_until - now)
                        logger.debug(
                            "Rate limit full: %d/%d. Waiting %.2fs (pid=%d)",
                            count,
                            self.requests_per_minute,
                            wait_seconds,
                            self._pid,
                        )
                finally:
                    # Release file lock
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()

            except OSError as e:
                logger.warning("Lock file error: %s. Retrying.", e)

            # Wait before retrying
            time.sleep(POLL_INTERVAL)

    def record_request(self) -> None:
        """Record a request timestamp without rate-limit checking.

        Useful when the caller manages its own timing but wants to
        share the request count with other processes.
        """
        try:
            lock_fd = open(self.lock_path, "w")
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                state = self._read_state()
                now = time.time()
                state["timestamps"] = self._prune_old_timestamps(
                    state["timestamps"], now
                )
                state["timestamps"].append(now)
                self._write_state(state)
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
        except OSError as e:
            logger.warning("Failed to record request: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status across all processes.

        Returns:
            Dictionary with:
                - requests_last_minute: Number of requests in sliding window
                - requests_per_minute: Configured limit
                - utilization_percent: Percentage of limit used
                - available: Number of requests still available
                - oldest_request_age_seconds: Age of oldest request in window
                - newest_request_age_seconds: Age of newest request in window
                - state_file: Path to state file
                - lock_file: Path to lock file
                - pid: Current process ID
        """
        try:
            lock_fd = open(self.lock_path, "w")
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                state = self._read_state()
                now = time.time()
                timestamps = self._prune_old_timestamps(state["timestamps"], now)

                count = len(timestamps)
                available = max(0, self.requests_per_minute - count)
                utilization = (count / self.requests_per_minute * 100) if self.requests_per_minute > 0 else 0

                oldest_age = (now - min(timestamps)) if timestamps else 0
                newest_age = (now - max(timestamps)) if timestamps else 0

                return {
                    "requests_last_minute": count,
                    "requests_per_minute": self.requests_per_minute,
                    "utilization_percent": round(utilization, 1),
                    "available": available,
                    "oldest_request_age_seconds": round(oldest_age, 1),
                    "newest_request_age_seconds": round(newest_age, 1),
                    "state_file": str(self.state_path),
                    "lock_file": str(self.lock_path),
                    "pid": self._pid,
                }
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
        except OSError as e:
            logger.error("Failed to get rate limit status: %s", e)
            return {
                "requests_last_minute": -1,
                "requests_per_minute": self.requests_per_minute,
                "utilization_percent": -1,
                "available": -1,
                "error": str(e),
                "pid": self._pid,
            }

    def reset(self) -> None:
        """Reset the shared rate limit state.

        Clears all recorded timestamps. Useful for testing or recovery.
        """
        try:
            lock_fd = open(self.lock_path, "w")
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                state = {
                    "timestamps": [],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "reset_by_pid": self._pid,
                }
                self._write_state(state)
                logger.info("Rate limit state reset by pid=%d", self._pid)
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
        except OSError as e:
            logger.error("Failed to reset rate limit state: %s", e)

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the rate limiter.

        Returns:
            Dictionary with:
                - healthy: True if the rate limiter is functioning
                - status: Current rate limit status
                - lock_exists: Whether the lock file exists
                - state_exists: Whether the state file exists
                - state_readable: Whether the state file is readable
                - warnings: List of any warning messages
        """
        warnings = []
        lock_exists = self.lock_path.exists()
        state_exists = self.state_path.exists()
        state_readable = False

        if not lock_exists:
            warnings.append("Lock file does not exist (will be created on first use)")

        if state_exists:
            try:
                with open(self.state_path) as f:
                    json.load(f)
                state_readable = True
            except (json.JSONDecodeError, OSError):
                warnings.append("State file exists but is not readable/valid JSON")
        else:
            warnings.append("State file does not exist (will be created on first use)")

        status = self.get_status()
        healthy = status.get("requests_last_minute", -1) >= 0

        if status.get("utilization_percent", 0) > 80:
            warnings.append(
                f"Rate limit utilization high: {status['utilization_percent']}%"
            )

        return {
            "healthy": healthy,
            "status": status,
            "lock_exists": lock_exists,
            "state_exists": state_exists,
            "state_readable": state_readable,
            "warnings": warnings,
        }
