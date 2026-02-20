#!/usr/bin/env python3
"""
Thread-safe token bucket rate limiter for FDA API requests.

Implements a token bucket algorithm with configurable rates, supporting both
authenticated (1000 req/min) and unauthenticated (240 req/min) FDA API limits.

Features:
- Thread-safe token bucket implementation
- Configurable rate limits (requests per minute)
- Blocking wait when tokens exhausted
- Time-based token replenishment
- Rate limit header parsing and dynamic adjustment
- Exponential backoff with jitter for 429 responses
- Comprehensive logging at DEBUG/WARNING/ERROR levels

Usage:
from fda_tools.lib.rate_limiter import RateLimiter

    limiter = RateLimiter(requests_per_minute=240)
    limiter.acquire()  # Blocks until token available
    # Make API request

    # After receiving response with rate limit headers:
    limiter.update_from_headers(response_headers)
"""

import logging
import random
import threading
import time
from typing import Dict, Optional


logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe token bucket rate limiter for API requests.

    Implements the token bucket algorithm where tokens are added at a constant
    rate and consumed by requests. When the bucket is empty, requests block
    until tokens become available.

    Attributes:
        requests_per_minute: Maximum requests allowed per minute
        tokens: Current number of available tokens (protected by lock)
        last_update: Timestamp of last token replenishment
    """

    def __init__(
        self,
        requests_per_minute: int = 240,
        burst_capacity: Optional[int] = None,
    ):
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute (default: 240 for
                unauthenticated FDA API access). Use 1000 for authenticated.
            burst_capacity: Maximum tokens that can accumulate. Defaults to
                requests_per_minute to allow full burst at startup.
        """
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")

        self.requests_per_minute = requests_per_minute
        self.tokens_per_second = requests_per_minute / 60.0
        self.burst_capacity = burst_capacity or requests_per_minute

        # Token bucket state (protected by lock)
        self._lock = threading.Lock()
        self._tokens = float(self.burst_capacity)
        self._last_update = time.time()

        # Statistics for monitoring
        self._stats = {
            "total_requests": 0,
            "total_waits": 0,
            "total_wait_time_seconds": 0.0,
            "rate_limit_warnings": 0,
            "dynamic_adjustments": 0,
        }

        logger.info(
            "RateLimiter initialized: %d req/min (%.2f req/sec), burst capacity: %d",
            requests_per_minute,
            self.tokens_per_second,
            self.burst_capacity,
        )

    def _replenish_tokens(self) -> None:
        """Replenish tokens based on elapsed time.

        Called with lock held. Updates token count based on time elapsed
        since last update, capped at burst_capacity.
        """
        now = time.time()
        elapsed = now - self._last_update

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.tokens_per_second
        self._tokens = min(self._tokens + new_tokens, self.burst_capacity)
        self._last_update = now

        logger.debug(
            "Replenished %.2f tokens (elapsed: %.2fs), current: %.2f / %d",
            new_tokens,
            elapsed,
            self._tokens,
            self.burst_capacity,
        )

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from the bucket, blocking if necessary.

        Blocks until the requested number of tokens becomes available or the
        timeout expires. Updates statistics for monitoring.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum seconds to wait. None means wait forever.

        Returns:
            True if tokens acquired, False if timeout expired

        Raises:
            ValueError: If tokens <= 0 or tokens > burst_capacity
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        if tokens > self.burst_capacity:
            raise ValueError(
                f"Cannot acquire {tokens} tokens (burst capacity: {self.burst_capacity})"
            )

        start_time = time.time()
        deadline = None if timeout is None else start_time + timeout

        with self._lock:
            self._stats["total_requests"] += 1

            while True:
                self._replenish_tokens()

                if self._tokens >= tokens:
                    # Tokens available, acquire them
                    self._tokens -= tokens
                    wait_time = time.time() - start_time

                    if wait_time > 0.001:  # More than 1ms wait
                        self._stats["total_waits"] += 1
                        self._stats["total_wait_time_seconds"] += wait_time
                        logger.debug(
                            "Acquired %d token(s) after %.3fs wait (%.2f remaining)",
                            tokens,
                            wait_time,
                            self._tokens,
                        )
                    else:
                        logger.debug(
                            "Acquired %d token(s) immediately (%.2f remaining)",
                            tokens,
                            self._tokens,
                        )

                    return True

                # Check timeout
                if deadline is not None and time.time() >= deadline:
                    logger.warning(
                        "Rate limit acquisition timed out after %.2fs (needed %d tokens, have %.2f)",
                        timeout,
                        tokens,
                        self._tokens,
                    )
                    return False

                # Calculate wait time until next token
                tokens_needed = tokens - self._tokens
                wait_seconds = tokens_needed / self.tokens_per_second

                # Cap wait at 1 second for responsiveness
                wait_seconds = min(wait_seconds, 1.0)

                # Release lock while sleeping to allow other threads
                # Note: We'll re-check after sleep in case another thread consumed tokens
                self._lock.release()
                try:
                    time.sleep(wait_seconds)
                finally:
                    self._lock.acquire()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Non-blocking version of acquire(). Returns immediately with success
        or failure status.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if insufficient tokens
        """
        with self._lock:
            self._replenish_tokens()

            if self._tokens >= tokens:
                self._tokens -= tokens
                self._stats["total_requests"] += 1
                logger.debug("Try-acquired %d token(s) (%.2f remaining)", tokens, self._tokens)
                return True
            else:
                logger.debug(
                    "Try-acquire failed: need %d tokens, have %.2f",
                    tokens,
                    self._tokens,
                )
                return False

    def update_from_headers(
        self,
        headers: Dict[str, str],
        warn_threshold: float = 0.1,
    ) -> None:
        """Update rate limiter based on API response headers.

        Parses X-RateLimit-* headers from FDA API responses and logs warnings
        when approaching limits. Can dynamically adjust local rate limit if
        server reports different limits.

        Args:
            headers: HTTP response headers dict (case-insensitive)
            warn_threshold: Warn when remaining < (threshold * limit). Default: 0.1 (10%)

        Example headers:
            X-RateLimit-Limit: 240
            X-RateLimit-Remaining: 235
            X-RateLimit-Reset: 1676592000
        """
        # Normalize header keys to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        limit_str = headers_lower.get("x-ratelimit-limit")
        remaining_str = headers_lower.get("x-ratelimit-remaining")
        reset_str = headers_lower.get("x-ratelimit-reset")

        if not limit_str or not remaining_str:
            # Headers not present (not all APIs provide them)
            return

        try:
            server_limit = int(limit_str)
            remaining = int(remaining_str)
            reset_timestamp = int(reset_str) if reset_str else None
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse rate limit headers: %s", e)
            return

        # Log rate limit status
        utilization = ((server_limit - remaining) / server_limit) if server_limit > 0 else 0
        logger.debug(
            "Rate limit status: %d/%d used (%.1f%%), %d remaining",
            server_limit - remaining,
            server_limit,
            utilization * 100,
            remaining,
        )

        # Warn if approaching limit
        if remaining < server_limit * warn_threshold:
            self._stats["rate_limit_warnings"] += 1
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

        # Detect if server reports different limit than our configuration
        # Allow 5% tolerance for rounding differences
        if abs(server_limit - self.requests_per_minute) > self.requests_per_minute * 0.05:
            logger.info(
                "Server reports rate limit: %d req/min (local config: %d req/min)",
                server_limit,
                self.requests_per_minute,
            )

            # Optional: Dynamically adjust to server limit (commented out by default)
            # Uncomment if you want automatic adjustment:
            # with self._lock:
            #     self.requests_per_minute = server_limit
            #     self.tokens_per_second = server_limit / 60.0
            #     self.burst_capacity = server_limit
            #     self._stats["dynamic_adjustments"] += 1
            #     logger.info("Dynamically adjusted rate limit to %d req/min", server_limit)

    def get_stats(self) -> Dict[str, float]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with statistics:
                - total_requests: Total acquire() calls
                - total_waits: Number of times requests had to wait
                - total_wait_time_seconds: Cumulative wait time
                - avg_wait_time_seconds: Average wait time per wait
                - wait_percentage: Percentage of requests that waited
                - rate_limit_warnings: Number of "approaching limit" warnings
                - dynamic_adjustments: Number of times rate limit was adjusted
                - current_tokens: Current token bucket level
                - requests_per_minute: Configured rate limit
        """
        with self._lock:
            self._replenish_tokens()

            stats = dict(self._stats)
            stats["current_tokens"] = self._tokens
            stats["requests_per_minute"] = self.requests_per_minute

            if stats["total_waits"] > 0:
                stats["avg_wait_time_seconds"] = (
                    stats["total_wait_time_seconds"] / stats["total_waits"]
                )
            else:
                stats["avg_wait_time_seconds"] = 0.0

            if stats["total_requests"] > 0:
                stats["wait_percentage"] = (
                    (stats["total_waits"] / stats["total_requests"]) * 100
                )
            else:
                stats["wait_percentage"] = 0.0

            return stats

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats = {
                "total_requests": 0,
                "total_waits": 0,
                "total_wait_time_seconds": 0.0,
                "rate_limit_warnings": 0,
                "dynamic_adjustments": 0,
            }
            logger.info("Rate limiter statistics reset")


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay with optional jitter.

    Implements exponential backoff: delay = base_delay * (2 ** attempt)
    with optional jitter to prevent thundering herd.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter: Add random jitter to prevent thundering herd (default: True)

    Returns:
        Delay in seconds

    Example:
        attempt=0 -> 1s, attempt=1 -> 2s, attempt=2 -> 4s, attempt=3 -> 8s
    """
    # Exponential: 2^attempt
    delay = base_delay * (2 ** attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter: random value in [0.5 * delay, 1.0 * delay]
    if jitter:
        delay = delay * (0.5 + 0.5 * random.random())

    return delay


def parse_retry_after(retry_after_header: Optional[str]) -> Optional[float]:
    """Parse Retry-After header from HTTP response.

    Retry-After can be either:
    - An integer (delay in seconds)
    - An HTTP date (absolute timestamp)

    Args:
        retry_after_header: Value of Retry-After header

    Returns:
        Delay in seconds, or None if header not parseable

    Example:
        parse_retry_after("120") -> 120.0
        parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") -> seconds until that time
    """
    if not retry_after_header:
        return None

    # Try parsing as integer (seconds)
    try:
        return float(retry_after_header)
    except ValueError:
        pass

    # Try parsing as HTTP date
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timezone
    try:
        target_time = parsedate_to_datetime(retry_after_header)
        now = datetime.now(timezone.utc)
        delay = (target_time - now).total_seconds()
        return max(0.0, delay)  # Don't return negative delays
    except (ValueError, TypeError, AttributeError):
        logger.warning("Failed to parse Retry-After header: %s", retry_after_header)
        return None


# ------------------------------------------------------------------
# Rate Limit Validation (Security Hardening - FDA-86)
# ------------------------------------------------------------------

# Valid rate limit periods for validation
VALID_RATE_LIMIT_PERIODS = {"second", "minute", "hour", "day"}

# Rate limit bounds
MIN_RATE_LIMIT = 1
MAX_RATE_LIMIT = 10000


def validate_rate_limit(limit: int, period: str) -> None:
    """Validate rate limit configuration parameters.

    Ensures rate limit values are within acceptable bounds to prevent
    misconfiguration that could lead to API abuse or denial of service.

    Args:
        limit: Number of requests allowed per period.
               Must be between MIN_RATE_LIMIT (1) and MAX_RATE_LIMIT (10000).
        period: Time period for the rate limit.
                Must be one of: 'second', 'minute', 'hour', 'day'.

    Raises:
        ValueError: If limit is out of bounds or period is invalid.

    Examples:
        >>> validate_rate_limit(240, "minute")  # OK: standard FDA API limit
        >>> validate_rate_limit(0, "minute")     # Raises ValueError
        >>> validate_rate_limit(100, "week")     # Raises ValueError
    """
    if not isinstance(limit, int):
        raise ValueError(
            f"Rate limit must be an integer, got {type(limit).__name__}"
        )

    if not (MIN_RATE_LIMIT <= limit <= MAX_RATE_LIMIT):
        raise ValueError(
            f"Rate limit must be between {MIN_RATE_LIMIT} and {MAX_RATE_LIMIT}, "
            f"got {limit}"
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
        """Initialize retry policy.

        Args:
            max_attempts: Maximum retry attempts (default: 5)
            base_delay: Base delay for exponential backoff (default: 1.0s)
            max_delay: Maximum delay between retries (default: 60.0s)
            jitter: Add random jitter to backoff delays (default: True)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

        logger.debug(
            "RetryPolicy initialized: max_attempts=%d, base_delay=%.1fs, max_delay=%.1fs, jitter=%s",
            max_attempts,
            base_delay,
            max_delay,
            jitter,
        )

    def get_retry_delay(
        self,
        attempt: int,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Get retry delay for the given attempt.

        Args:
            attempt: Current attempt number (0-indexed)
            headers: HTTP response headers (to check Retry-After)

        Returns:
            Delay in seconds, or None if max attempts exceeded
        """
        if attempt >= self.max_attempts:
            logger.error("Max retry attempts (%d) exceeded", self.max_attempts)
            return None

        # Check for Retry-After header
        if headers:
            retry_after = parse_retry_after(headers.get("Retry-After"))
            if retry_after is not None:
                logger.info(
                    "Retry-After header present: %.1fs (attempt %d/%d)",
                    retry_after,
                    attempt + 1,
                    self.max_attempts,
                )
                return retry_after

        # Use exponential backoff
        delay = calculate_backoff(
            attempt,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            jitter=self.jitter,
        )

        logger.info(
            "Retry attempt %d/%d: waiting %.2fs (exponential backoff)",
            attempt + 1,
            self.max_attempts,
            delay,
        )

        return delay


# ------------------------------------------------------------------
# Decorator and Context Manager Support (CODE-001)
# ------------------------------------------------------------------

import functools
from typing import Callable, TypeVar, Optional as OptionalType


T = TypeVar('T')


def rate_limited(
    limiter: RateLimiter,
    tokens: int = 1,
    timeout: OptionalType[float] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to rate limit function calls.

    Acquires tokens from the rate limiter before executing the decorated
    function. Useful for wrapping API calls or other rate-limited operations.

    Args:
        limiter: RateLimiter instance to use
        tokens: Number of tokens to acquire per call (default: 1)
        timeout: Maximum seconds to wait for tokens. None = wait forever.

    Returns:
        Decorated function that respects rate limits

    Example:
        >>> limiter = RateLimiter(requests_per_minute=240)
        >>> @rate_limited(limiter)
        ... def make_api_call(endpoint):
        ...     return requests.get(endpoint)
        ...
        >>> make_api_call("https://api.fda.gov/device/510k.json")

    Raises:
        RuntimeError: If rate limit acquisition fails (timeout exceeded)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            acquired = limiter.acquire(tokens=tokens, timeout=timeout)
            if not acquired:
                raise RuntimeError(
                    f"Rate limit acquisition timeout after {timeout}s for {func.__name__}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitContext:
    """Context manager for rate limiting code blocks.

    Acquires tokens on entry and releases them on exit (if configured).
    Useful for wrapping code sections that make rate-limited calls.

    Example:
        >>> limiter = RateLimiter(requests_per_minute=240)
        >>> with RateLimitContext(limiter, tokens=5):
        ...     # Make up to 5 API calls
        ...     for item in items[:5]:
        ...         make_api_call(item)

    Args:
        limiter: RateLimiter instance to use
        tokens: Number of tokens to acquire (default: 1)
        timeout: Maximum seconds to wait. None = wait forever.

    Raises:
        RuntimeError: If rate limit acquisition fails
    """

    def __init__(
        self,
        limiter: RateLimiter,
        tokens: int = 1,
        timeout: OptionalType[float] = None,
    ):
        self.limiter = limiter
        self.tokens = tokens
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        self.acquired = self.limiter.acquire(tokens=self.tokens, timeout=self.timeout)
        if not self.acquired:
            raise RuntimeError(
                f"Rate limit acquisition timeout after {self.timeout}s"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Nothing to release in token bucket implementation
        # (tokens are consumed, not borrowed)
        pass
