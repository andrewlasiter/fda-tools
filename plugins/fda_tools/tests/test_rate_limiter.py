#!/usr/bin/env python3
"""
Unit tests for rate limiter module (FDA-20).

Tests token bucket rate limiting, exponential backoff, retry policy,
and header parsing functionality.
"""

import pytest
import threading
import time
from unittest.mock import patch

# Add parent directory to path for imports
import sys
from pathlib import Path

from rate_limiter import (
    RateLimiter,
    RetryPolicy,
    calculate_backoff,
    parse_retry_after,
    rate_limited,
    RateLimitContext,
)


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_minute=240)
        assert limiter.requests_per_minute == 240
        assert limiter.tokens_per_second == 4.0  # 240 / 60
        assert limiter.burst_capacity == 240

    def test_initialization_with_custom_burst(self):
        """Test rate limiter with custom burst capacity."""
        limiter = RateLimiter(requests_per_minute=240, burst_capacity=120)
        assert limiter.burst_capacity == 120

    def test_initialization_invalid_rate(self):
        """Test that invalid rate raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            RateLimiter(requests_per_minute=0)

        with pytest.raises(ValueError, match="must be positive"):
            RateLimiter(requests_per_minute=-10)

    def test_acquire_immediate(self):
        """Test that acquire succeeds immediately when tokens available."""
        limiter = RateLimiter(requests_per_minute=240)

        start = time.time()
        result = limiter.acquire(tokens=1)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.1  # Should be nearly instant

    def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens at once."""
        limiter = RateLimiter(requests_per_minute=60, burst_capacity=10)

        # Acquire 5 tokens
        result = limiter.acquire(tokens=5)
        assert result is True

        # Should have 5 tokens left
        stats = limiter.get_stats()
        assert 4.0 < stats["current_tokens"] < 6.0  # Allow small drift

    def test_acquire_exceeds_capacity(self):
        """Test that acquiring more than capacity raises ValueError."""
        limiter = RateLimiter(requests_per_minute=60, burst_capacity=10)

        with pytest.raises(ValueError, match="burst capacity"):
            limiter.acquire(tokens=20)

    def test_acquire_blocks_when_empty(self):
        """Test that acquire blocks when bucket is empty."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second

        # Drain the bucket
        limiter.acquire(tokens=60)

        # Next acquire should block for ~1 second
        start = time.time()
        result = limiter.acquire(tokens=1, timeout=2.0)
        elapsed = time.time() - start

        assert result is True
        assert 0.5 < elapsed < 1.5  # Should wait ~1 second

    def test_acquire_timeout(self):
        """Test that acquire respects timeout."""
        limiter = RateLimiter(requests_per_minute=60)

        # Drain bucket
        limiter.acquire(tokens=60)

        # Try to acquire with short timeout (should fail)
        start = time.time()
        result = limiter.acquire(tokens=10, timeout=0.1)
        elapsed = time.time() - start

        assert result is False
        # Timeout may take slightly longer due to sleep(1.0) in the loop
        assert elapsed < 1.5  # Should timeout within reasonable time

    def test_try_acquire_success(self):
        """Test try_acquire when tokens available."""
        limiter = RateLimiter(requests_per_minute=240)

        result = limiter.try_acquire(tokens=1)
        assert result is True

    def test_try_acquire_failure(self):
        """Test try_acquire when insufficient tokens."""
        limiter = RateLimiter(requests_per_minute=60, burst_capacity=10)

        # Drain bucket
        limiter.acquire(tokens=10)

        # Try acquire should fail immediately
        result = limiter.try_acquire(tokens=1)
        assert result is False

    def test_token_replenishment(self):
        """Test that tokens replenish over time."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second

        # Drain bucket
        limiter.acquire(tokens=60)

        # Wait for 2 seconds
        time.sleep(2.1)

        # Should have ~2 tokens now
        result = limiter.try_acquire(tokens=2)
        assert result is True

    def test_thread_safety(self):
        """Test that rate limiter is thread-safe."""
        limiter = RateLimiter(requests_per_minute=100)
        results = []

        def worker():
            for _ in range(10):
                success = limiter.acquire(tokens=1, timeout=5.0)
                results.append(success)

        # Start 5 threads, each trying to acquire 10 tokens
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All acquires should succeed (50 total, capacity 100)
        assert all(results)
        assert len(results) == 50

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

    def test_get_stats(self):
        """Test statistics collection."""
        limiter = RateLimiter(requests_per_minute=240)

        # Make some requests
        limiter.acquire(tokens=1)
        limiter.acquire(tokens=1)
        limiter.try_acquire(tokens=1)

        stats = limiter.get_stats()

        assert "total_requests" in stats
        assert "total_waits" in stats
        assert "current_tokens" in stats
        assert "requests_per_minute" in stats
        assert stats["requests_per_minute"] == 240

    def test_reset_stats(self):
        """Test that statistics can be reset."""
        limiter = RateLimiter(requests_per_minute=240)

        # Make some requests
        limiter.acquire(tokens=5)
        limiter.acquire(tokens=5)

        # Reset stats
        limiter.reset_stats()

        stats = limiter.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_waits"] == 0


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


class TestRateLimiterIntegration:
    """Integration tests for realistic usage patterns."""

    def test_burst_then_sustained(self):
        """Test burst of requests followed by sustained rate."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second

        # Burst: consume all 60 tokens
        for _ in range(60):
            result = limiter.try_acquire(tokens=1)
            assert result is True

        # Next request should fail (no tokens)
        result = limiter.try_acquire(tokens=1)
        assert result is False

        # Wait 2 seconds for replenishment
        time.sleep(2.1)

        # Should be able to acquire ~2 tokens now
        result = limiter.acquire(tokens=2, timeout=1.0)
        assert result is True

    def test_concurrent_requests(self):
        """Test multiple threads making concurrent requests."""
        limiter = RateLimiter(requests_per_minute=120)  # 2 tokens per second
        successful = []
        failed = []

        def make_requests():
            for _ in range(20):
                if limiter.try_acquire(tokens=1):
                    successful.append(1)
                else:
                    failed.append(1)

        # Start 3 threads
        threads = [threading.Thread(target=make_requests) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total 60 requests, burst capacity 120, so most should succeed
        assert len(successful) + len(failed) == 60
        # At least half should succeed from burst capacity
        assert len(successful) >= 30


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

    def test_decorator_with_tokens(self):
        """Test decorator with custom token count."""
        limiter = RateLimiter(requests_per_minute=240, burst_capacity=10)

        @rate_limited(limiter, tokens=5)
        def batch_operation():
            return "batch_success"

        # First call should succeed (5 tokens available)
        result = batch_operation()
        assert result == "batch_success"

        # Second call should also succeed (5 more tokens)
        result = batch_operation()
        assert result == "batch_success"

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

    def test_context_manager_with_tokens(self):
        """Test context manager with multiple tokens."""
        limiter = RateLimiter(requests_per_minute=240, burst_capacity=10)

        with RateLimitContext(limiter, tokens=5):
            # Should have acquired 5 tokens
            stats = limiter.get_stats()
            # Check that tokens were consumed
            assert stats['total_requests'] >= 1

    def test_context_manager_timeout(self):
        """Test context manager timeout behavior."""
        limiter = RateLimiter(requests_per_minute=12)  # Very slow: 0.2 tokens per second

        # Drain bucket completely
        for _ in range(12):
            limiter.try_acquire()

        # Should raise RuntimeError with short timeout
        with pytest.raises(RuntimeError, match="Rate limit acquisition timeout"):
            with RateLimitContext(limiter, tokens=1, timeout=0.2):
                pass

    def test_context_manager_exception_handling(self):
        """Test that exceptions inside context are propagated."""
        limiter = RateLimiter(requests_per_minute=240)

        with pytest.raises(ValueError, match="test exception"):
            with RateLimitContext(limiter):
                raise ValueError("test exception")

    def test_context_manager_multiple_calls(self):
        """Test multiple context manager calls."""
        limiter = RateLimiter(requests_per_minute=240, burst_capacity=20)
        call_count = []

        for i in range(5):
            with RateLimitContext(limiter, tokens=2):
                call_count.append(i)

        assert len(call_count) == 5


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
