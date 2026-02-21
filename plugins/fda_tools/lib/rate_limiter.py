#!/usr/bin/env python3
"""
DEPRECATED: fda_tools.lib.rate_limiter is superseded by fda_tools.lib.cross_process_rate_limiter.

This module is a thin re-export shim retained for backward compatibility (FDA-200).
All symbols are re-exported from the canonical implementation.

Migration guide:
    # Before:
    from fda_tools.lib.rate_limiter import RateLimiter, RetryPolicy

    # After:
    from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter, RetryPolicy

Remove this file after all callers have been updated to import from cross_process_rate_limiter.
"""

import warnings

warnings.warn(
    "fda_tools.lib.rate_limiter is deprecated. "
    "Import from fda_tools.lib.cross_process_rate_limiter instead.",
    DeprecationWarning,
    stacklevel=2,
)

from fda_tools.lib.cross_process_rate_limiter import (  # noqa: F401, E402
    CrossProcessRateLimiter as RateLimiter,
    CrossProcessRateLimiter,
    RetryPolicy,
    RateLimitContext,
    rate_limited,
    calculate_backoff,
    parse_retry_after,
    validate_rate_limit,
    VALID_RATE_LIMIT_PERIODS,
    MIN_RATE_LIMIT,
    MAX_RATE_LIMIT,
    RATE_LIMIT_WITH_KEY,
    RATE_LIMIT_WITHOUT_KEY,
    WINDOW_SIZE_SECONDS,
)
