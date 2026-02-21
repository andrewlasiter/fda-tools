#!/usr/bin/env python3
"""
OpenFDA API Quota Tracker (FDA-153).

Provides multi-window quota visibility and graceful degradation status for
openFDA API calls. Complements CrossProcessRateLimiter by tracking request
counts over 1-minute, 1-hour, and 24-hour windows and returning structured
warning levels before requests are made.

Unlike CrossProcessRateLimiter (which blocks until it is safe to proceed),
QuotaTracker is a non-blocking observability layer. Callers check the status
to decide how to proceed (slow down, pause, alert) rather than being forced
to wait.

Degradation levels:
    NORMAL     — < 70% of minute quota used
    WARNING    — 70-84% used; consider reducing batch sizes
    THROTTLED  — 85-99% used; add delay between requests
    BLOCKED    — >= 100% used; pause until the window resets

State file: ~/fda-510k-data/.quota_state.json
Lock file:  ~/fda-510k-data/.quota.lock

Usage::

    from fda_tools.lib.quota_tracker import QuotaTracker, QuotaLevel

    tracker = QuotaTracker(has_api_key=True)

    status = tracker.check_status()
    if status.level == QuotaLevel.BLOCKED:
        time.sleep(status.suggested_delay_seconds)
    elif status.level == QuotaLevel.THROTTLED:
        time.sleep(status.suggested_delay_seconds)

    # After making the API call:
    tracker.record_request()
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = os.path.expanduser("~/fda-510k-data")
QUOTA_STATE_FILE = ".quota_state.json"
QUOTA_LOCK_FILE = ".quota.lock"

# Maximum age of timestamps to retain (24 hours)
RETENTION_SECONDS = 86_400

# Default per-minute limits (matches CrossProcessRateLimiter values)
DEFAULT_LIMIT_WITH_KEY = 1000
DEFAULT_LIMIT_WITHOUT_KEY = 240

# Warning thresholds (fraction of the per-minute limit)
THRESHOLD_WARNING = 0.70     # >= 70% → WARNING
THRESHOLD_THROTTLED = 0.85   # >= 85% → THROTTLED
THRESHOLD_BLOCKED = 1.00     # >= 100% → BLOCKED

# How many seconds to suggest waiting when throttled / blocked
THROTTLED_DELAY_SECONDS = 2.0
BLOCKED_DELAY_SECONDS = 10.0


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


class QuotaLevel(str, Enum):
    """Degradation level returned by QuotaTracker.check_status()."""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    THROTTLED = "THROTTLED"
    BLOCKED = "BLOCKED"


@dataclass
class QuotaStatus:
    """Snapshot of current quota utilization.

    Attributes:
        level: Degradation level (NORMAL/WARNING/THROTTLED/BLOCKED).
        requests_last_minute: Requests recorded in the past 60 seconds.
        requests_last_hour: Requests recorded in the past 3600 seconds.
        requests_last_day: Requests recorded in the past 86400 seconds.
        minute_limit: Configured per-minute limit.
        utilization_pct: Fraction of minute_limit used (0.0–1.0+).
        available_this_minute: Remaining requests before limit is reached.
        suggested_delay_seconds: Recommended pause before next request.
        message: Human-readable status message.
    """

    level: QuotaLevel
    requests_last_minute: int
    requests_last_hour: int
    requests_last_day: int
    minute_limit: int
    utilization_pct: float
    available_this_minute: int
    suggested_delay_seconds: float
    message: str

    def is_degraded(self) -> bool:
        """Return True if level is WARNING, THROTTLED, or BLOCKED."""
        return self.level != QuotaLevel.NORMAL

    def as_dict(self) -> Dict:
        """Return a plain dictionary representation."""
        return {
            "level": self.level.value,
            "requests_last_minute": self.requests_last_minute,
            "requests_last_hour": self.requests_last_hour,
            "requests_last_day": self.requests_last_day,
            "minute_limit": self.minute_limit,
            "utilization_pct": round(self.utilization_pct * 100, 1),
            "available_this_minute": self.available_this_minute,
            "suggested_delay_seconds": self.suggested_delay_seconds,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# QuotaTracker
# ---------------------------------------------------------------------------


class QuotaTracker:
    """Non-blocking quota visibility layer for openFDA API calls.

    Records request timestamps to a shared JSON file and computes quota
    utilization over 1-minute, 1-hour, and 24-hour rolling windows.

    File writes are protected by an fcntl exclusive lock so multiple
    concurrent processes share a single, consistent state.

    Args:
        has_api_key: True = 1,000 req/min limit; False = 240 req/min.
        data_dir: Directory for state and lock files.
        minute_limit: Override the per-minute limit.
    """

    def __init__(
        self,
        has_api_key: bool = True,
        data_dir: Optional[str] = None,
        minute_limit: Optional[int] = None,
    ) -> None:
        self._data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._state_path = self._data_dir / QUOTA_STATE_FILE
        self._lock_path = self._data_dir / QUOTA_LOCK_FILE

        if minute_limit is not None:
            self.minute_limit = minute_limit
        elif has_api_key:
            self.minute_limit = DEFAULT_LIMIT_WITH_KEY
        else:
            self.minute_limit = DEFAULT_LIMIT_WITHOUT_KEY

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_request(self) -> None:
        """Record the current timestamp as a completed API request.

        Call this *after* each successful openFDA API call. The timestamp
        is appended to the shared state file under an exclusive file lock.
        """
        try:
            import fcntl  # Unix only; no-op path for non-Unix via except

            with open(self._lock_path, "w") as lf:
                try:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                    self._append_timestamp(time.time())
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        except ImportError:
            # fcntl not available (e.g. Windows) — best-effort write
            self._append_timestamp(time.time())
        except OSError as exc:
            logger.warning("QuotaTracker: failed to record request: %s", exc)

    def check_status(self) -> QuotaStatus:
        """Return the current quota status without blocking.

        Reads the shared state file, counts recent timestamps, and computes
        the degradation level against the configured per-minute limit.

        Returns:
            QuotaStatus snapshot with degradation level and counts.
        """
        timestamps = self._load_timestamps()
        now = time.time()
        last_60s = [t for t in timestamps if now - t <= 60]
        last_hour = [t for t in timestamps if now - t <= 3_600]
        last_day = timestamps  # already pruned to 24 hours

        count = len(last_60s)
        utilization = count / self.minute_limit if self.minute_limit > 0 else 0.0
        available = max(0, self.minute_limit - count)

        level, delay, message = self._compute_level(utilization, available)

        return QuotaStatus(
            level=level,
            requests_last_minute=count,
            requests_last_hour=len(last_hour),
            requests_last_day=len(last_day),
            minute_limit=self.minute_limit,
            utilization_pct=utilization,
            available_this_minute=available,
            suggested_delay_seconds=delay,
            message=message,
        )

    def reset(self) -> None:
        """Clear all recorded timestamps (useful for testing)."""
        try:
            import fcntl

            with open(self._lock_path, "w") as lf:
                try:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                    self._write_timestamps([])
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        except ImportError:
            self._write_timestamps([])
        except OSError as exc:
            logger.warning("QuotaTracker: failed to reset state: %s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_timestamp(self, ts: float) -> None:
        """Append *ts* to state file; prune timestamps older than 24 h."""
        timestamps = self._load_timestamps()
        cutoff = ts - RETENTION_SECONDS
        timestamps = [t for t in timestamps if t >= cutoff]
        timestamps.append(ts)
        self._write_timestamps(timestamps)

    def _load_timestamps(self) -> List[float]:
        """Read and return all timestamps from the state file."""
        if not self._state_path.exists():
            return []
        try:
            with open(self._state_path, "r") as f:
                data = json.load(f)
            timestamps = data.get("timestamps", [])
            now = time.time()
            cutoff = now - RETENTION_SECONDS
            return [float(t) for t in timestamps if float(t) >= cutoff]
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.debug("QuotaTracker: could not read state: %s", exc)
            return []

    def _write_timestamps(self, timestamps: List[float]) -> None:
        """Write timestamps list to the state file atomically."""
        tmp = self._state_path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump({"timestamps": timestamps}, f)
            tmp.replace(self._state_path)
        except OSError as exc:
            logger.warning("QuotaTracker: failed to write state: %s", exc)
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _compute_level(
        utilization: float, available: int
    ) -> tuple[QuotaLevel, float, str]:
        """Map utilization fraction to (level, delay, message)."""
        if utilization >= THRESHOLD_BLOCKED:
            return (
                QuotaLevel.BLOCKED,
                BLOCKED_DELAY_SECONDS,
                f"Quota exhausted ({utilization * 100:.0f}% used). "
                f"Pause {BLOCKED_DELAY_SECONDS:.0f}s before next request.",
            )
        if utilization >= THRESHOLD_THROTTLED:
            return (
                QuotaLevel.THROTTLED,
                THROTTLED_DELAY_SECONDS,
                f"Quota nearly exhausted ({utilization * 100:.0f}% used, "
                f"{available} remaining). Add {THROTTLED_DELAY_SECONDS:.0f}s delay.",
            )
        if utilization >= THRESHOLD_WARNING:
            return (
                QuotaLevel.WARNING,
                0.0,
                f"Quota under pressure ({utilization * 100:.0f}% used, "
                f"{available} remaining). Consider reducing batch size.",
            )
        return (
            QuotaLevel.NORMAL,
            0.0,
            f"Quota healthy ({utilization * 100:.0f}% used, {available} remaining).",
        )
