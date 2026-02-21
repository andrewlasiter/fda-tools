#!/usr/bin/env python3
"""
Tests for FDA-200: lib/rate_limiter deprecation shim.

Verifies that the shim:
- Emits DeprecationWarning on import
- Re-exports all expected symbols
- Aliases RateLimiter → CrossProcessRateLimiter
"""

import warnings
import pytest


def test_shim_emits_deprecation_warning():
    """Importing rate_limiter should emit DeprecationWarning."""
    import importlib
    import fda_tools.lib.rate_limiter as _mod  # already imported; reload to trigger warning
    # Re-trigger by reloading the module
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(_mod)

    deprecation_warnings = [
        w for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "rate_limiter" in str(w.message).lower()
    ]
    assert len(deprecation_warnings) >= 1, "Expected at least one DeprecationWarning about rate_limiter"


def test_shim_exports_rate_limiter_alias():
    """RateLimiter exported by shim should be CrossProcessRateLimiter."""
    from fda_tools.lib.rate_limiter import RateLimiter
    from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter
    assert RateLimiter is CrossProcessRateLimiter


def test_shim_exports_cross_process_rate_limiter():
    """CrossProcessRateLimiter should be directly importable from shim."""
    from fda_tools.lib.rate_limiter import CrossProcessRateLimiter
    from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter as Canonical
    assert CrossProcessRateLimiter is Canonical


def test_shim_exports_retry_policy():
    """RetryPolicy should be importable from shim."""
    from fda_tools.lib.rate_limiter import RetryPolicy
    assert RetryPolicy is not None
    policy = RetryPolicy(max_attempts=3)
    assert policy.max_attempts == 3


def test_shim_exports_utility_functions():
    """calculate_backoff, parse_retry_after, validate_rate_limit should be importable."""
    from fda_tools.lib.rate_limiter import (
        calculate_backoff,
        parse_retry_after,
        validate_rate_limit,
        rate_limited,
        RateLimitContext,
    )
    assert callable(calculate_backoff)
    assert callable(parse_retry_after)
    assert callable(validate_rate_limit)
    assert callable(rate_limited)
    assert RateLimitContext is not None


def test_shim_exports_constants():
    """Rate limit constants should be importable from shim."""
    from fda_tools.lib.rate_limiter import (
        RATE_LIMIT_WITH_KEY,
        RATE_LIMIT_WITHOUT_KEY,
        WINDOW_SIZE_SECONDS,
        MIN_RATE_LIMIT,
        MAX_RATE_LIMIT,
        VALID_RATE_LIMIT_PERIODS,
    )
    assert RATE_LIMIT_WITH_KEY == 240
    assert RATE_LIMIT_WITHOUT_KEY == 40
    assert WINDOW_SIZE_SECONDS == 60
    assert MIN_RATE_LIMIT >= 1
    assert MAX_RATE_LIMIT > MIN_RATE_LIMIT
    assert "minute" in VALID_RATE_LIMIT_PERIODS


def test_shim_rate_limiter_is_functional(tmp_path):
    """RateLimiter from shim should be usable for basic operations."""
    from fda_tools.lib.rate_limiter import RateLimiter
    limiter = RateLimiter(requests_per_minute=240, data_dir=str(tmp_path))
    result = limiter.acquire(timeout=5.0)
    assert result is True
    status = limiter.get_status()
    assert status["requests_last_minute"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
