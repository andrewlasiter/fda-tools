#!/usr/bin/env python3
"""
Error Handling Utilities - Retry logic, rate limiting, circuit breakers

Provides robust error handling for external service calls including:
1. Exponential backoff retry logic
2. Rate limiting
3. Circuit breaker pattern
4. Graceful degradation
5. Comprehensive logging

Usage:
    from error_handling import with_retry, RateLimiter, CircuitBreaker

    # Retry with exponential backoff
    @with_retry(max_attempts=3, initial_delay=1.0)
    def call_external_api():
        ...

    # Rate limiting
    rate_limiter = RateLimiter(calls_per_minute=100)
    with rate_limiter:
        api_call()

    # Circuit breaker
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    result = circuit_breaker.call(api_function, *args, **kwargs)
"""

import threading
import time
import logging
from functools import wraps
from typing import Callable, Any, Optional, TypeVar, cast
from datetime import datetime, timedelta
from collections import deque

try:
    from fda_tools.lib.cross_process_rate_limiter import (
        CrossProcessRateLimiter as _CrossProcessRateLimiter,
    )
    _CROSS_PROCESS_AVAILABLE = True
except ImportError:
    _CROSS_PROCESS_AVAILABLE = False
    _CrossProcessRateLimiter = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ==================================================================
# Retry Logic with Exponential Backoff
# ==================================================================

class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""
    pass


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @with_retry(max_attempts=3, initial_delay=1.0)
        def call_api():
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            "Retry exhausted after %d attempts: %s",
                            max_attempts, e
                        )
                        break

                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt, max_attempts, e, delay
                    )
                    time.sleep(delay)

                    # Exponential backoff
                    delay = min(delay * exponential_base, max_delay)

            # All retries exhausted
            raise RetryExhausted(
                f"Failed after {max_attempts} attempts. Last error: {last_exception}"
            ) from last_exception

        return wrapper
    return decorator


# ==================================================================
# Rate Limiter
# ==================================================================

class _FallbackRateLimiter:
    """Rate limiter using sliding window algorithm (in-process only).

    Used as a fallback when CrossProcessRateLimiter is unavailable.
    New code should use CrossProcessRateLimiter directly.

    Example:
        rate_limiter = _FallbackRateLimiter(calls_per_minute=100)

        # Use as context manager
        with rate_limiter:
            api_call()

        # Or call directly
        rate_limiter.wait_if_needed()
    """

    def __init__(self, calls_per_minute: int = 100, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls per minute
            window_seconds: Time window in seconds
        """
        self.max_calls = calls_per_minute
        self.window = window_seconds
        self.calls: deque = deque()
        self._lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded (thread-safe)."""
        while True:
            with self._lock:
                now = time.time()
                # Remove calls outside the window
                while self.calls and self.calls[0] < now - self.window:
                    self.calls.popleft()
                # Under limit: record this call and return
                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return
                # At limit: compute sleep time, release lock before sleeping
                sleep_time = self.calls[0] + self.window - now + 0.001

            if sleep_time > 0:
                logger.debug(
                    "Rate limit reached. Waiting %.1f seconds...",
                    sleep_time
                )
                time.sleep(sleep_time)
            # Re-check after waking (loop)

    def __enter__(self):
        """Context manager entry."""
        self.wait_if_needed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False


# Backward-compat alias: uses cross-process-safe limiter when available.
# New code should import CrossProcessRateLimiter directly.
RateLimiter = _CrossProcessRateLimiter if _CROSS_PROCESS_AVAILABLE else _FallbackRateLimiter


# ==================================================================
# Circuit Breaker Pattern
# ==================================================================

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker pattern for failing fast.

    Prevents cascading failures by opening the circuit after a threshold
    of failures, and attempting recovery after a timeout.

    States:
        CLOSED: Normal operation, calls go through
        OPEN: Failures exceeded threshold, calls are blocked
        HALF_OPEN: Testing if service recovered, single call allowed

    Example:
        circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        result = circuit_breaker.call(api_function, arg1, arg2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exceptions: Exceptions that count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function through circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        # Check/update circuit state under lock (don't hold lock during func call)
        with self._lock:
            if self.state == "OPEN":
                if (self.last_failure_time and
                    time.time() - self.last_failure_time >= self.recovery_timeout):
                    logger.info("Circuit breaker attempting recovery (HALF_OPEN)")
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker is OPEN (failures: {self.failure_count})"
                    )

        try:
            result = func(*args, **kwargs)

            # Success - reset failure count under lock
            with self._lock:
                if self.state == "HALF_OPEN":
                    logger.info("Circuit breaker recovered (CLOSED)")
                    self.state = "CLOSED"
                    self.failure_count = 0

            return result

        except self.expected_exceptions:
            self._record_failure()
            raise

    def _record_failure(self):
        """Record a failure and potentially open the circuit."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                logger.error(
                    "Circuit breaker OPEN (failures: %d >= threshold: %d)",
                    self.failure_count, self.failure_threshold
                )
                self.state = "OPEN"
            else:
                logger.warning(
                    "Circuit breaker failure %d/%d",
                    self.failure_count, self.failure_threshold
                )


# ==================================================================
# Graceful Degradation Helpers
# ==================================================================

def with_fallback(fallback_value: Any):
    """Decorator to provide fallback value on exception.

    Example:
        @with_fallback([])
        def fetch_data():
            return api.get_data()  # Returns [] if API fails
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "Function %s failed, using fallback: %s",
                    func.__name__, e
                )
                return cast(T, fallback_value)
        return wrapper
    return decorator


def timeout(seconds: int):
    """Decorator to add timeout to function calls.

    Note: This is a simplified version. For production use,
    consider using signal.alarm() on Unix or threading.Timer.

    Args:
        seconds: Timeout in seconds
    """
    import signal

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def _timeout_handler(signum, frame):
            raise TimeoutError(f"Function call exceeded {seconds} seconds")

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Set the signal handler and a timeout alarm
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper
    return decorator


# ==================================================================
# Combined Error Handling
# ==================================================================

class RobustAPIClient:
    """Combined error handling for API clients.

    Combines retry logic, rate limiting, and circuit breaker pattern
    for robust external API calls.

    Example:
        client = RobustAPIClient(
            max_retries=3,
            calls_per_minute=100,
            failure_threshold=5
        )

        result = client.call(api.get_data, param1, param2)
    """

    def __init__(
        self,
        max_retries: int = 3,
        calls_per_minute: int = 100,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """Initialize robust API client.

        Args:
            max_retries: Maximum retry attempts
            calls_per_minute: Rate limit
            failure_threshold: Circuit breaker threshold
            recovery_timeout: Circuit breaker recovery time
        """
        if _CROSS_PROCESS_AVAILABLE:
            self.rate_limiter: Any = _CrossProcessRateLimiter(  # type: ignore[call-arg]
                requests_per_minute=calls_per_minute
            )
        else:
            self.rate_limiter = _FallbackRateLimiter(calls_per_minute=calls_per_minute)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        self.max_retries = max_retries

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function with all error handling.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        @with_retry(max_attempts=self.max_retries)
        def _call_with_retry():
            with self.rate_limiter:
                return self.circuit_breaker.call(func, *args, **kwargs)

        return _call_with_retry()
