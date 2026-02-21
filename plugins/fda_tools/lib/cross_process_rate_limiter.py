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
import functools
import json
import logging
import os
import random
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar('T')

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

# Rate limit validation bounds (Security Hardening - FDA-86)
VALID_RATE_LIMIT_PERIODS = {"second", "minute", "hour", "day"}
MIN_RATE_LIMIT = 1
MAX_RATE_LIMIT = 10000


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
        *,
        requests_per_5min: Optional[int] = None,
        min_delay_seconds: float = 0.0,
        burst_capacity: Optional[int] = None,
    ):
        """Initialize the cross-process rate limiter.

        Args:
            has_api_key: Whether an openFDA API key is configured.
                True = 240 req/min, False = 40 req/min.
            data_dir: Directory for lock and state files.
                Default: ~/fda-510k-data/
            requests_per_minute: Override rate limit. If None, uses
                240 (with key) or 40 (without key).
            requests_per_5min: Optional 5-minute hard limit (dual-bucket).
                When set, acquire() enforces BOTH the per-minute and
                per-5-minute limits simultaneously. The 5-minute bucket
                is per-process (not cross-process) to avoid file I/O overhead.
            min_delay_seconds: Minimum wall-clock delay between successive
                acquire() calls within this process. 0.0 = no forced delay.
                Set to 0.25 to enforce 4 req/sec maximum burst rate.
            burst_capacity: Informational only; stored for stats display.
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

        self.burst_capacity = burst_capacity

        self._pid = os.getpid()

        # Dual-bucket (5-minute) enforcement — in-process memory only
        self._requests_per_5min: Optional[int] = requests_per_5min
        if requests_per_5min is not None:
            self._five_min_tokens: int = requests_per_5min
            self._five_min_last_refill: float = time.monotonic()
            self._five_min_lock = threading.Lock()

        # Minimum inter-request delay enforcement
        self._min_delay_seconds: float = min_delay_seconds
        self._last_acquire_time: float = 0.0
        self._min_delay_lock = threading.Lock()

        # In-process statistics (not cross-process)
        self._total_requests: int = 0
        self._total_waits: int = 0
        self._total_wait_time_seconds: float = 0.0
        self._rate_limit_warnings: int = 0
        self._stats_lock = threading.Lock()

        logger.info(
            "CrossProcessRateLimiter initialized: %d req/min%s, pid=%d, "
            "lock=%s, state=%s",
            self.requests_per_minute,
            f", {requests_per_5min}/5min" if requests_per_5min else "",
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
        timeout expires. Enforces both the per-minute cross-process limit
        and the optional per-5-minute in-process limit.

        Args:
            timeout: Maximum seconds to wait. None defaults to MAX_WAIT_SECONDS.

        Returns:
            True if permission acquired, False if timeout expired.
        """
        timeout = timeout if timeout is not None else MAX_WAIT_SECONDS
        deadline = time.time() + timeout
        acquire_start = time.time()

        while True:
            now = time.time()
            if now >= deadline:
                logger.warning(
                    "CrossProcessRateLimiter: timeout after %.1fs waiting for rate limit",
                    timeout,
                )
                return False

            acquired = False
            try:
                # Open (or create) the lock file
                lock_fd = open(self.lock_path, "w")
                try:
                    # Acquire exclusive file lock (blocks across processes)
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    # Another process holds the lock; wait and retry
                    lock_fd.close()
                    jitter = POLL_INTERVAL * (0.5 + 0.5 * random.random())
                    time.sleep(jitter)
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
                        acquired = True
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
                    # Release file lock before any further waiting
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()

            except OSError as e:
                logger.warning("Lock file error: %s. Retrying.", e)

            if acquired:
                # Per-minute slot acquired; now check 5-minute bucket (in-process)
                wait_5min = self._check_and_consume_5min_bucket()
                while wait_5min > 0:
                    if time.time() >= deadline:
                        return False
                    time.sleep(wait_5min)
                    wait_5min = self._check_and_consume_5min_bucket()

                # Enforce minimum inter-request delay (in-process)
                if self._min_delay_seconds > 0:
                    with self._min_delay_lock:
                        elapsed = time.time() - self._last_acquire_time
                        delay_needed = max(0.0, self._min_delay_seconds - elapsed)
                        self._last_acquire_time = time.time() + delay_needed
                    if delay_needed > 0:
                        time.sleep(delay_needed)

                # Update in-process stats
                wait_time = time.time() - acquire_start
                with self._stats_lock:
                    self._total_requests += 1
                    if wait_time > 0.05:
                        self._total_waits += 1
                        self._total_wait_time_seconds += wait_time
                return True

            # Wait before retrying (with jitter to reduce thundering herd)
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

    def try_acquire(self) -> bool:
        """Non-blocking acquire attempt.

        Returns True immediately if a slot is available in the current
        sliding window. Returns False immediately if at the limit.

        Does NOT enforce the 5-minute bucket or min_delay.

        Returns:
            True if slot acquired, False if at limit.
        """
        try:
            lock_fd = open(self.lock_path, "w")
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lock_fd.close()
                return False

            try:
                now = time.time()
                state = self._read_state()
                timestamps = self._prune_old_timestamps(state["timestamps"], now)
                if len(timestamps) < self.requests_per_minute:
                    timestamps.append(now)
                    state["timestamps"] = timestamps
                    self._write_state(state)
                    with self._stats_lock:
                        self._total_requests += 1
                    return True
                return False
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                lock_fd.close()
        except OSError as e:
            logger.warning("try_acquire lock file error: %s", e)
            return False

    def update_from_headers(
        self,
        headers: Dict[str, str],
        warn_threshold: float = 0.1,
    ) -> None:
        """Parse X-RateLimit-* headers and log warnings when approaching limit.

        Args:
            headers: HTTP response headers dict (case-insensitive lookup).
            warn_threshold: Warn when remaining < threshold * limit (default 10%).

        Supported headers:
            X-RateLimit-Limit: server-reported limit
            X-RateLimit-Remaining: requests remaining in current window
            X-RateLimit-Reset: Unix timestamp when window resets
        """
        headers_lower = {k.lower(): v for k, v in headers.items()}

        limit_str = headers_lower.get("x-ratelimit-limit")
        remaining_str = headers_lower.get("x-ratelimit-remaining")
        reset_str = headers_lower.get("x-ratelimit-reset")

        if not limit_str or not remaining_str:
            return

        try:
            server_limit = int(limit_str)
            remaining = int(remaining_str)
            reset_timestamp = int(reset_str) if reset_str else None
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse rate limit headers: %s", e)
            return

        utilization = ((server_limit - remaining) / server_limit) if server_limit > 0 else 0
        logger.debug(
            "Rate limit status from headers: %d/%d used (%.1f%%), %d remaining",
            server_limit - remaining,
            server_limit,
            utilization * 100,
            remaining,
        )

        if remaining < server_limit * warn_threshold:
            with self._stats_lock:
                self._rate_limit_warnings += 1
            logger.warning(
                "APPROACHING RATE LIMIT: %d/%d requests used (%.1f%%), only %d remaining!",
                server_limit - remaining,
                server_limit,
                utilization * 100,
                remaining,
            )
            if reset_timestamp:
                reset_in = reset_timestamp - time.time()
                if reset_in > 0:
                    logger.warning("Rate limit resets in %.0f seconds", reset_in)

        if abs(server_limit - self.requests_per_minute) > self.requests_per_minute * 0.05:
            logger.info(
                "Server reports rate limit: %d req/min (local config: %d req/min)",
                server_limit,
                self.requests_per_minute,
            )

    def get_stats(self) -> Dict[str, Any]:
        """Return extended rate limit statistics (superset of get_status()).

        Includes all fields from get_status() plus in-process counters.

        Returns:
            Dictionary with all get_status() fields plus:
                - total_requests: Total requests acquired by this instance
                - total_waits: Number of times acquire() had to wait
                - total_wait_time_seconds: Cumulative wait time in seconds
                - total_wait_seconds: Alias for total_wait_time_seconds
                - avg_wait_time_seconds: Average wait time per waited request
                - wait_percentage: Percent of requests that had to wait
                - rate_limit_warnings: Warnings from update_from_headers()
                - five_min_tokens_remaining: Remaining 5-min tokens (if enabled)
                - requests_per_5min: Configured 5-min limit (if enabled)
        """
        status = self.get_status()
        with self._stats_lock:
            total_req = self._total_requests
            total_waits = self._total_waits
            total_wait_time = self._total_wait_time_seconds
            warnings_count = self._rate_limit_warnings

        avg_wait = (total_wait_time / total_waits) if total_waits > 0 else 0.0
        wait_pct = (total_waits / total_req * 100) if total_req > 0 else 0.0

        stats = {
            **status,
            "total_requests": total_req,
            "total_waits": total_waits,
            "total_wait_time_seconds": round(total_wait_time, 3),
            "total_wait_seconds": round(total_wait_time, 3),  # alias for orchestrator compat
            "avg_wait_time_seconds": round(avg_wait, 3),
            "wait_percentage": round(wait_pct, 1),
            "rate_limit_warnings": warnings_count,
        }

        if self._requests_per_5min is not None:
            with self._five_min_lock:
                tokens = self._five_min_tokens
            stats["five_min_tokens_remaining"] = tokens
            stats["requests_per_5min"] = self._requests_per_5min

        return stats

    def __enter__(self) -> "CrossProcessRateLimiter":
        """Context manager entry: acquire a rate limit slot."""
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit: nothing to release."""
        pass

    def _check_and_consume_5min_bucket(self) -> float:
        """Check and consume a token from the 5-minute bucket.

        Returns:
            0.0 if token was available (token consumed), else seconds to wait.
        """
        if self._requests_per_5min is None:
            return 0.0

        with self._five_min_lock:
            now = time.monotonic()
            elapsed = now - self._five_min_last_refill
            if elapsed >= 300:
                self._five_min_tokens = self._requests_per_5min
                self._five_min_last_refill = now
            elif elapsed > 0:
                refill = int(elapsed * self._requests_per_5min / 300)
                self._five_min_tokens = min(
                    self._requests_per_5min,
                    self._five_min_tokens + refill,
                )

            if self._five_min_tokens > 0:
                self._five_min_tokens -= 1
                return 0.0
            else:
                return 1.0  # retry after 1 second


# ===========================================================================
# Module-level Utilities (absorbed from lib/rate_limiter.py — FDA-200)
# ===========================================================================


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay with optional jitter.

    Implements exponential backoff: delay = base_delay * (2 ** attempt),
    with optional jitter to prevent thundering herd.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter: Add random jitter in [0.5*delay, 1.0*delay] (default: True)

    Returns:
        Delay in seconds

    Example:
        attempt=0 -> 1s, attempt=1 -> 2s, attempt=2 -> 4s, attempt=3 -> 8s
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        delay = delay * (0.5 + 0.5 * random.random())
    return delay


def parse_retry_after(retry_after_header: Optional[str]) -> Optional[float]:
    """Parse Retry-After header from HTTP response.

    Retry-After can be either:
    - An integer (delay in seconds)
    - An HTTP date string (absolute timestamp)

    Args:
        retry_after_header: Value of Retry-After header

    Returns:
        Delay in seconds, or None if not parseable.
    """
    if not retry_after_header:
        return None

    try:
        return float(retry_after_header)
    except ValueError:
        pass

    try:
        target_time = parsedate_to_datetime(retry_after_header)
        now = datetime.now(timezone.utc)
        return max(0.0, (target_time - now).total_seconds())
    except (ValueError, TypeError, AttributeError):
        logger.warning("Failed to parse Retry-After header: %s", retry_after_header)
        return None


def validate_rate_limit(limit: int, period: str) -> None:
    """Validate rate limit configuration parameters (Security Hardening - FDA-86).

    Args:
        limit: Number of requests allowed per period (must be 1–10000).
        period: Time period ('second', 'minute', 'hour', or 'day').

    Raises:
        ValueError: If limit is out of bounds or period is invalid.
    """
    if not isinstance(limit, int):
        raise ValueError(
            f"Rate limit must be an integer, got {type(limit).__name__}"
        )
    if not (MIN_RATE_LIMIT <= limit <= MAX_RATE_LIMIT):
        raise ValueError(
            f"Rate limit must be between {MIN_RATE_LIMIT} and {MAX_RATE_LIMIT}, got {limit}"
        )
    if period not in VALID_RATE_LIMIT_PERIODS:
        raise ValueError(
            f"Invalid rate limit period: '{period}'. "
            f"Must be one of: {sorted(VALID_RATE_LIMIT_PERIODS)}"
        )


class RetryPolicy:
    """Retry policy for handling 429 (Too Many Requests) responses.

    Implements exponential backoff with configurable max attempts, respecting
    Retry-After headers when present.

    Usage:
        policy = RetryPolicy(max_attempts=5)

        for attempt in range(policy.max_attempts):
            response = make_request()
            if response.status == 429:
                delay = policy.get_retry_delay(attempt, response.headers)
                if delay is None:
                    break  # Max attempts exceeded
                time.sleep(delay)
            else:
                break
    """

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def get_retry_delay(
        self,
        attempt: int,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Get retry delay for the given attempt.

        Args:
            attempt: Current attempt number (0-indexed).
            headers: HTTP response headers (checked for Retry-After).

        Returns:
            Delay in seconds, or None if max_attempts exceeded.
        """
        if attempt >= self.max_attempts:
            logger.error("Max retry attempts (%d) exceeded", self.max_attempts)
            return None

        if headers:
            retry_after = parse_retry_after(headers.get("Retry-After"))
            if retry_after is not None:
                logger.info(
                    "Retry-After header: %.1fs (attempt %d/%d)",
                    retry_after, attempt + 1, self.max_attempts,
                )
                return retry_after

        delay = calculate_backoff(
            attempt,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            jitter=self.jitter,
        )
        logger.info(
            "Retry attempt %d/%d: waiting %.2fs (exponential backoff)",
            attempt + 1, self.max_attempts, delay,
        )
        return delay


def rate_limited(
    limiter: CrossProcessRateLimiter,
    timeout: Optional[float] = None,
) -> "Callable[[Callable[..., T]], Callable[..., T]]":
    """Decorator to rate-limit function calls via a CrossProcessRateLimiter.

    Args:
        limiter: CrossProcessRateLimiter instance to use.
        timeout: Maximum seconds to wait for a slot. None = MAX_WAIT_SECONDS.

    Returns:
        Decorator that acquires a rate limit slot before each call.

    Raises:
        RuntimeError: If acquisition times out.

    Example:
        limiter = CrossProcessRateLimiter(has_api_key=True)

        @rate_limited(limiter)
        def call_fda_api(endpoint):
            return requests.get(endpoint)
    """
    def decorator(func: "Callable[..., T]") -> "Callable[..., T]":
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> "T":
            acquired = limiter.acquire(timeout=timeout)
            if not acquired:
                raise RuntimeError(
                    f"Rate limit acquisition timeout after {timeout}s "
                    f"for {func.__name__}"
                )
            return func(*args, **kwargs)  # type: ignore[return-value]
        return wrapper  # type: ignore[return-value]
    return decorator  # type: ignore[return-value]


class RateLimitContext:
    """Context manager for rate-limiting a code block.

    Acquires a rate limit slot on entry; nothing to release on exit.

    Example:
        limiter = CrossProcessRateLimiter(has_api_key=True)
        with RateLimitContext(limiter):
            response = requests.get(fda_url)
    """

    def __init__(
        self,
        limiter: CrossProcessRateLimiter,
        timeout: Optional[float] = None,
    ) -> None:
        self.limiter = limiter
        self.timeout = timeout

    def __enter__(self) -> "RateLimitContext":
        acquired = self.limiter.acquire(timeout=self.timeout)
        if not acquired:
            raise RuntimeError(
                f"Rate limit acquisition timeout after {self.timeout}s"
            )
        return self

    def __exit__(self, *_: object) -> None:
        pass
