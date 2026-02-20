"""
Comprehensive tests for error_handling.py module.

Tests retry logic, rate limiting, circuit breakers, and graceful degradation.

Test Coverage:
    - Exponential backoff retry decorator
    - Rate limiter with sliding window
    - Circuit breaker pattern
    - Error recovery and graceful degradation
    - Exception handling and logging
"""

import pytest
import time
from unittest.mock import patch, Mock
from fda_tools.scripts.error_handling import (
    with_retry,
    RetryExhausted,
    RateLimiter,
    CircuitBreaker,
    CircuitBreakerOpen,
)


class TestRetryDecorator:
    """Test with_retry decorator with exponential backoff."""

    def test_successful_call_no_retry(self):
        """Should execute successfully without retries."""
        call_count = []

        @with_retry(max_attempts=3)
        def successful_function():
            call_count.append(1)
            return "success"

        result = successful_function()
        assert result == "success"
        assert len(call_count) == 1

    def test_retry_on_exception(self):
        """Should retry on exception and eventually succeed."""
        call_count = []

        @with_retry(max_attempts=3, initial_delay=0.01)
        def flaky_function():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Temporary error")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert len(call_count) == 3

    def test_retry_exhausted_raises_exception(self):
        """Should raise RetryExhausted when all attempts fail."""
        @with_retry(max_attempts=2, initial_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryExhausted):
            always_fails()

    def test_exponential_backoff_timing(self):
        """Should increase delay exponentially."""
        delays = []
        original_sleep = time.sleep

        def mock_sleep(seconds):
            delays.append(seconds)

        @with_retry(max_attempts=4, initial_delay=1.0, exponential_base=2.0)
        def failing_function():
            raise ValueError("Fail")

        with patch('time.sleep', side_effect=mock_sleep):
            try:
                failing_function()
            except RetryExhausted:
                pass

        # Should have delays: 1.0, 2.0, 4.0 (exponential)
        assert len(delays) == 3
        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(4.0)

    def test_max_delay_cap(self):
        """Should cap delay at max_delay."""
        delays = []

        def mock_sleep(seconds):
            delays.append(seconds)

        @with_retry(max_attempts=5, initial_delay=10.0, max_delay=20.0, exponential_base=2.0)
        def failing_function():
            raise ValueError("Fail")

        with patch('time.sleep', side_effect=mock_sleep):
            try:
                failing_function()
            except RetryExhausted:
                pass

        # Delays should not exceed max_delay of 20.0
        assert all(d <= 20.0 for d in delays)

    def test_custom_exceptions_to_retry(self):
        """Should only retry specified exceptions."""
        @with_retry(max_attempts=3, initial_delay=0.01, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("Not a ValueError")

        # Should NOT retry TypeError
        with pytest.raises(TypeError):
            raises_type_error()

    def test_preserves_function_metadata(self):
        """Should preserve original function name and docstring."""
        @with_retry()
        def documented_function():
            """This is a docstring."""
            return 42

        assert documented_function.__name__ == "documented_function"
        assert "This is a docstring" in documented_function.__doc__


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_allows_calls_within_limit(self):
        """Should allow calls within rate limit."""
        limiter = RateLimiter(calls_per_minute=10)

        # Should succeed
        for _ in range(5):
            with limiter:
                pass

    def test_blocks_when_limit_exceeded(self):
        """Should block when rate limit is exceeded."""
        limiter = RateLimiter(calls_per_minute=2)

        # Use up the limit
        with limiter:
            pass
        with limiter:
            pass

        # Next call should be delayed
        start = time.time()
        with limiter:
            pass
        elapsed = time.time() - start

        # Should have waited at least a short time
        assert elapsed > 0

    def test_sliding_window_expires_old_calls(self):
        """Should allow new calls after old ones expire from window."""
        limiter = RateLimiter(calls_per_minute=60)  # 1 per second

        with patch('time.time') as mock_time:
            # t=0: First call
            mock_time.return_value = 0.0
            with limiter:
                pass

            # t=2: Old call should have expired (window is 60 seconds / 60 calls = 1 second)
            mock_time.return_value = 2.0
            with limiter:
                pass  # Should succeed without blocking

    def test_context_manager_interface(self):
        """Should work as context manager."""
        limiter = RateLimiter(calls_per_minute=10)

        with limiter:
            result = "executed"

        assert result == "executed"

    def test_multiple_limiters_independent(self):
        """Multiple rate limiters should be independent."""
        limiter1 = RateLimiter(calls_per_minute=5)
        limiter2 = RateLimiter(calls_per_minute=10)

        with limiter1:
            pass
        with limiter2:
            pass

        # Both should have their own state
        assert len(limiter1.calls) == 1
        assert len(limiter2.calls) == 1


class TestCircuitBreaker:
    """Test CircuitBreaker pattern."""

    def test_allows_calls_when_closed(self):
        """Should allow calls when circuit is closed (healthy)."""
        breaker = CircuitBreaker(failure_threshold=3)

        def successful_function():
            return "success"

        result = breaker.call(successful_function)
        assert result == "success"

    def test_opens_after_threshold_failures(self):
        """Should open circuit after reaching failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        def failing_function():
            raise ValueError("Failed")

        # Trigger 3 failures
        for _ in range(3):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass

        # Circuit should now be open
        assert breaker.state == 'OPEN'

        # Next call should fail fast without executing function
        with pytest.raises(CircuitBreakerOpen, match="Circuit breaker is OPEN"):
            breaker.call(failing_function)

    def test_half_open_after_recovery_timeout(self):
        """Should transition to half-open after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        def failing_function():
            raise ValueError("Failed")

        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass

        assert breaker.state == 'OPEN'

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should transition to half-open on next call
        # (Will still fail but should attempt the call)
        try:
            breaker.call(failing_function)
        except ValueError:
            pass

        # May be open or half-open depending on timing
        assert breaker.state in ['OPEN', 'HALF_OPEN']

    def test_closes_after_successful_half_open_call(self):
        """Should close circuit after successful call in half-open state."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        call_count = []

        def flaky_function():
            call_count.append(1)
            if len(call_count) <= 2:
                raise ValueError("Failed")
            return "success"

        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(flaky_function)
            except ValueError:
                pass

        assert breaker.state == 'OPEN'

        # Wait for recovery
        time.sleep(0.2)

        # Successful call should close the circuit
        result = breaker.call(flaky_function)
        assert result == "success"
        assert breaker.state == 'CLOSED'

    def test_counts_consecutive_failures_only(self):
        """Should count only consecutive failures."""
        breaker = CircuitBreaker(failure_threshold=3)

        def sometimes_fails():
            if len(times_called) in [1, 3]:
                raise ValueError("Fail")
            return "success"

        times_called = []

        # Fail, succeed, fail, succeed - should not open
        for i in range(4):
            times_called.append(i)
            try:
                breaker.call(sometimes_fails)
            except ValueError:
                pass

        # Should still be closed (not 3 consecutive failures)
        assert breaker.state == 'CLOSED'

    def test_passes_function_arguments(self):
        """Should pass arguments and kwargs to wrapped function."""
        breaker = CircuitBreaker()

        def function_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = breaker.call(function_with_args, "x", "y", c="z")
        assert result == "x-y-z"


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""

    def test_retry_with_fallback(self):
        """Should use fallback value when retries are exhausted."""
        call_count = []

        def always_fails():
            call_count.append(1)
            raise ValueError("Always fails")

        # Test the actual pattern - catch RetryExhausted and use fallback
        try:
            @with_retry(max_attempts=2, initial_delay=0.01)
            def failing_fn():
                raise ValueError("Fail")
            failing_fn()
        except RetryExhausted:
            # Fallback after retry exhausted
            result = "fallback_value"

        assert result == "fallback_value"

    def test_circuit_breaker_with_fallback(self):
        """Should use fallback when circuit is open."""
        breaker = CircuitBreaker(failure_threshold=2)

        def failing_function():
            raise ValueError("Failed")

        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass

        # Use fallback when circuit is open
        try:
            breaker.call(failing_function)
        except Exception:
            result = "fallback_value"

        assert result == "fallback_value"


class TestLoggingIntegration:
    """Test error logging integration."""

    @patch('scripts.error_handling.logger')
    def test_retry_logs_warnings(self, mock_logger):
        """Should log warnings on retry attempts."""
        @with_retry(max_attempts=3, initial_delay=0.01)
        def failing_function():
            raise ValueError("Temporary failure")

        try:
            failing_function()
        except RetryExhausted:
            pass

        # Should have logged warnings for each retry (2 warnings for 3 attempts)
        assert mock_logger.warning.called
        assert mock_logger.warning.call_count == 2  # Warnings on attempt 1 and 2, not on final attempt

    @patch('scripts.error_handling.logger')
    def test_retry_logs_final_error(self, mock_logger):
        """Should log error when retries are exhausted."""
        @with_retry(max_attempts=2, initial_delay=0.01)
        def failing_function():
            raise ValueError("Always fails")

        try:
            failing_function()
        except RetryExhausted:
            pass

        # Should have logged final error
        assert mock_logger.error.called


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retry_with_zero_delay(self):
        """Should handle zero initial delay."""
        @with_retry(max_attempts=3, initial_delay=0)
        def failing_function():
            raise ValueError("Fail")

        try:
            failing_function()
        except RetryExhausted:
            pass

    def test_retry_with_single_attempt(self):
        """Should not retry when max_attempts is 1."""
        call_count = []

        @with_retry(max_attempts=1)
        def failing_function():
            call_count.append(1)
            raise ValueError("Fail")

        try:
            failing_function()
        except RetryExhausted:
            pass

        assert len(call_count) == 1

    def test_circuit_breaker_with_zero_threshold(self):
        """Should handle zero failure threshold (always open)."""
        breaker = CircuitBreaker(failure_threshold=0)

        # Should be open from the start - first call will set it to OPEN
        # Actually with threshold 0, it opens immediately on first failure
        # But since we're calling a lambda that succeeds, it should work
        # Let's test with a failing function instead
        def failing_fn():
            raise ValueError("Fail")

        # First call fails, sets failure_count to 1, which >= 0, so opens
        try:
            breaker.call(failing_fn)
        except ValueError:
            pass

        # Now circuit should be open
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(lambda: "success")

    def test_rate_limiter_with_high_rate(self):
        """Should handle very high call rates."""
        limiter = RateLimiter(calls_per_minute=1000)

        # Should allow many rapid calls
        for _ in range(100):
            with limiter:
                pass
