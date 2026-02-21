#!/usr/bin/env python3
"""
Unit tests for rate limiter module (FDA-20).

Tests token bucket rate limiting, exponential backoff, retry policy,
and header parsing functionality.
"""

import pytest
from unittest.mock import patch

# Add parent directory to path for imports
from fda_tools.lib.rate_limiter import (
    RateLimiter,
    RetryPolicy,
    calculate_backoff,
    parse_retry_after,
    rate_limited,
    RateLimitContext,
)


class TestRateLimiter:
    """Test RateLimiter (CrossProcessRateLimiter) via backward-compat shim."""

    def test_initialization_with_custom_burst(self):
        """Test rate limiter with custom burst capacity."""
        limiter = RateLimiter(requests_per_minute=240, burst_capacity=120)
        assert limiter.burst_capacity == 120

    def test_update_from_headers_basic(self):
        """Test parsing rate limit headers."""
        limiter = RateLimiter(requests_per_minute=240)

        headers = {
            "X-RateLimit-Limit": "240",
            "X-RateLimit-Remaining": "200",
        }

        # Should not raise, just log
        limiter.update_from_headers(headers)

    def test_update_from_headers_case_insensitive(self):
        """Test that header parsing is case-insensitive."""
        limiter = RateLimiter(requests_per_minute=240)

        headers = {
            "x-ratelimit-limit": "240",
            "X-RATELIMIT-REMAINING": "200",
        }

        # Should not raise
        limiter.update_from_headers(headers)

    def test_update_from_headers_warning_threshold(self):
        """Test that warnings are issued when approaching limit."""
        limiter = RateLimiter(requests_per_minute=240)

        # Only 5 requests remaining (< 10% of 240)
        headers = {
            "X-RateLimit-Limit": "240",
            "X-RateLimit-Remaining": "5",
        }

        limiter.update_from_headers(headers, warn_threshold=0.1)

        stats = limiter.get_stats()
        assert stats["rate_limit_warnings"] == 1

    def test_update_from_headers_missing(self):
        """Test that missing headers are handled gracefully."""
        limiter = RateLimiter(requests_per_minute=240)

        # Empty headers should not raise
        limiter.update_from_headers({})

        # Partial headers should not raise
        limiter.update_from_headers({"X-RateLimit-Limit": "240"})

    def test_update_from_headers_invalid(self):
        """Test that invalid header values are handled gracefully."""
        limiter = RateLimiter(requests_per_minute=240)

        headers = {
            "X-RateLimit-Limit": "invalid",
            "X-RateLimit-Remaining": "not-a-number",
        }

        # Should log warning but not raise
        limiter.update_from_headers(headers)

class TestRetryPolicy:
    """Test RetryPolicy class."""

    def test_initialization(self):
        """Test retry policy initialization."""
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=60.0)
        assert policy.max_attempts == 5
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0

    def test_get_retry_delay_exponential(self):
        """Test exponential backoff delays."""
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=False)

        delay0 = policy.get_retry_delay(0)
        delay1 = policy.get_retry_delay(1)
        delay2 = policy.get_retry_delay(2)

        assert delay0 == 1.0  # 2^0 = 1
        assert delay1 == 2.0  # 2^1 = 2
        assert delay2 == 4.0  # 2^2 = 4

    def test_get_retry_delay_max_attempts(self):
        """Test that max attempts is respected."""
        policy = RetryPolicy(max_attempts=3)

        # Attempts 0, 1, 2 should succeed
        assert policy.get_retry_delay(0) is not None
        assert policy.get_retry_delay(1) is not None
        assert policy.get_retry_delay(2) is not None

        # Attempt 3 should fail (max_attempts=3 means 0,1,2 are valid)
        assert policy.get_retry_delay(3) is None

    def test_get_retry_delay_max_delay(self):
        """Test that delays are capped at max_delay."""
        policy = RetryPolicy(max_attempts=10, base_delay=1.0, max_delay=10.0, jitter=False)

        # Attempt 5 would be 2^5 = 32 seconds, but capped at 10
        delay = policy.get_retry_delay(5)
        assert delay == 10.0

    def test_get_retry_delay_with_jitter(self):
        """Test that jitter adds randomness."""
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=True)

        # Get multiple delays for same attempt
        delays = [policy.get_retry_delay(2) for _ in range(10)]

        # With jitter, delays should vary
        # Base delay for attempt 2 is 4.0s, jitter makes it [2.0, 4.0]
        assert all(2.0 <= d <= 4.0 for d in delays)
        # Should have some variation (not all identical)
        assert len(set(delays)) > 1

    def test_get_retry_delay_respects_retry_after_header(self):
        """Test that Retry-After header is respected."""
        policy = RetryPolicy(max_attempts=5)

        headers = {"Retry-After": "10"}
        delay = policy.get_retry_delay(0, headers)

        assert delay == 10.0

    def test_get_retry_delay_retry_after_invalid(self):
        """Test that invalid Retry-After falls back to exponential."""
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=False)

        headers = {"Retry-After": "invalid"}
        delay = policy.get_retry_delay(0, headers)

        # Should fall back to exponential (2^0 = 1.0)
        assert delay == 1.0


class TestCalculateBackoff:
    """Test calculate_backoff utility function."""

    def test_exponential_growth(self):
        """Test exponential backoff growth."""
        assert calculate_backoff(0, base_delay=1.0, jitter=False) == 1.0
        assert calculate_backoff(1, base_delay=1.0, jitter=False) == 2.0
        assert calculate_backoff(2, base_delay=1.0, jitter=False) == 4.0
        assert calculate_backoff(3, base_delay=1.0, jitter=False) == 8.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delay = calculate_backoff(10, base_delay=1.0, max_delay=30.0, jitter=False)
        assert delay == 30.0  # Would be 1024 without cap

    def test_custom_base_delay(self):
        """Test custom base delay."""
        delay = calculate_backoff(2, base_delay=2.0, jitter=False)
        assert delay == 8.0  # 2.0 * 2^2 = 8.0

    def test_jitter_range(self):
        """Test that jitter produces values in expected range."""
        # For attempt 2, base delay 1.0: exponential gives 4.0
        # With jitter: [0.5 * 4.0, 1.0 * 4.0] = [2.0, 4.0]
        delays = [calculate_backoff(2, base_delay=1.0, jitter=True) for _ in range(100)]

        assert all(2.0 <= d <= 4.0 for d in delays)
        # With 100 samples, should have good spread
        assert max(delays) - min(delays) > 0.5


class TestParseRetryAfter:
    """Test parse_retry_after utility function."""

    def test_parse_integer_seconds(self):
        """Test parsing integer seconds."""
        assert parse_retry_after("60") == 60.0
        assert parse_retry_after("120") == 120.0
        assert parse_retry_after("0") == 0.0

    def test_parse_float_seconds(self):
        """Test parsing float seconds."""
        assert parse_retry_after("30.5") == 30.5

    def test_parse_http_date(self):
        """Test parsing HTTP date format."""
        # This is tricky because we need a future date
        # For now, just test that it doesn't crash
        result = parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT")
        # Result will be negative (past date), which is fine
        assert result is not None

    def test_parse_none(self):
        """Test parsing None."""
        assert parse_retry_after(None) is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        assert parse_retry_after("") is None

    def test_parse_invalid(self):
        """Test parsing invalid string."""
        assert parse_retry_after("invalid") is None
        assert parse_retry_after("not-a-number") is None


class TestRateLimitedDecorator:
    """Test rate_limited decorator (CODE-001)."""

    def test_decorator_basic(self):
        """Test basic decorator usage."""
        limiter = RateLimiter(requests_per_minute=240)
        call_count = []

        @rate_limited(limiter)
        def test_function():
            call_count.append(1)
            return "success"

        result = test_function()
        assert result == "success"
        assert len(call_count) == 1

    def test_decorator_with_timeout(self):
        """Test decorator timeout behavior."""
        limiter = RateLimiter(requests_per_minute=12)  # Very slow: 0.2 tokens per second

        # Drain bucket completely
        for _ in range(12):
            limiter.try_acquire()

        @rate_limited(limiter, timeout=0.2)
        def slow_function():
            return "should_not_execute"

        # Should raise RuntimeError due to timeout
        with pytest.raises(RuntimeError, match="Rate limit acquisition timeout"):
            slow_function()

    def test_decorator_preserves_metadata(self):
        """Test that decorator preserves function metadata."""
        limiter = RateLimiter(requests_per_minute=240)

        @rate_limited(limiter)
        def documented_function():
            """This is a docstring."""
            return 42

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a docstring."

    def test_decorator_with_arguments(self):
        """Test decorated function with arguments."""
        limiter = RateLimiter(requests_per_minute=240)

        @rate_limited(limiter)
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

        result = add(a=10, b=20)
        assert result == 30


class TestRateLimitContext:
    """Test RateLimitContext context manager (CODE-001)."""

    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        limiter = RateLimiter(requests_per_minute=240)
        executed = []

        with RateLimitContext(limiter):
            executed.append(1)

        assert len(executed) == 1

    def test_context_manager_exception_handling(self):
        """Test that exceptions inside context are propagated."""
        limiter = RateLimiter(requests_per_minute=240)

        with pytest.raises(ValueError, match="test exception"):
            with RateLimitContext(limiter):
                raise ValueError("test exception")


class TestIntegrationWithConfig:
    """Test integration with centralized config system (CODE-001)."""

    def test_load_from_config(self):
        """Test loading rate limit settings from config."""
        # This test assumes config.toml is available
        try:
            from fda_tools.lib.config import get_config

            config = get_config()
            rate_limit = config.get_int('rate_limiting.rate_limit_openfda', 240)

            limiter = RateLimiter(requests_per_minute=rate_limit)
            assert limiter.requests_per_minute == rate_limit
        except ImportError:
            pytest.skip("Config module not available")

    def test_per_endpoint_configuration(self):
        """Test configuring different limits per endpoint."""
        # Simulating endpoint-specific rate limits
        limits = {
            'openfda': 240,
            'pubmed': 180,  # 3 req/sec
            'pdf_download': 2,
        }

        limiters = {
            name: RateLimiter(requests_per_minute=limit)
            for name, limit in limits.items()
        }

        assert limiters['openfda'].requests_per_minute == 240
        assert limiters['pubmed'].requests_per_minute == 180
        assert limiters['pdf_download'].requests_per_minute == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
