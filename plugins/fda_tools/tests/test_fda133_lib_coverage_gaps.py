"""
FDA-133: Unit test coverage gaps in lib/ modules.

Targets the specific uncovered branches in:
1. subprocess_helpers.py  (47.83% → 85%+)
   - on_error callback when allowlist rejects a command
   - CalledProcessError retry path (check=True + transient exit code)
   - Generic Exception catch (e.g. FileNotFoundError from bad executable)
   - run_command_with_streaming() — entirely uncovered

2. cross_process_rate_limiter.py  (56.93% → 70%+)
   - try_acquire() — non-blocking acquire
   - update_from_headers() — warning path
   - get_stats() — 5-minute bucket extra fields
   - _check_and_consume_5min_bucket() — token bucket logic
   - calculate_backoff() — with and without jitter
   - parse_retry_after() — integer, date-string, None
   - validate_rate_limit() — valid and all error paths
   - RetryPolicy.get_retry_delay() — with/without Retry-After header
   - rate_limited decorator
   - RateLimitContext context manager
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fda_tools.lib.subprocess_helpers import (
    SubprocessAllowlistError,
    SubprocessTimeoutError,
    run_command,
    run_command_with_streaming,
)
from fda_tools.lib.cross_process_rate_limiter import (
    CrossProcessRateLimiter,
    RetryPolicy,
    RateLimitContext,
    calculate_backoff,
    parse_retry_after,
    rate_limited,
    validate_rate_limit,
    MAX_RATE_LIMIT,
    MIN_RATE_LIMIT,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="fda_test_133_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def limiter(temp_dir):
    return CrossProcessRateLimiter(has_api_key=True, data_dir=temp_dir)


@pytest.fixture
def limiter_5min(temp_dir):
    """Limiter with 5-minute bucket enabled (requests_per_5min=10)."""
    return CrossProcessRateLimiter(
        has_api_key=True,
        data_dir=temp_dir,
        requests_per_5min=10,
    )


# ===========================================================================
# subprocess_helpers — on_error callback on allowlist rejection
# ===========================================================================


class TestOnErrorCallbackOnAllowlistRejection:
    """on_error must be called before raising SubprocessAllowlistError."""

    def test_on_error_called_with_allowlist_error(self):
        captured = []
        with pytest.raises(SubprocessAllowlistError):
            run_command(
                ["rm", "-rf", "/tmp/test"],
                allowlist=["python3", "git"],
                on_error=lambda e: captured.append(e),
            )
        assert len(captured) == 1
        assert isinstance(captured[0], SubprocessAllowlistError)

    def test_on_error_receives_correct_message(self):
        captured = []
        with pytest.raises(SubprocessAllowlistError):
            run_command(
                ["curl", "http://example.com"],
                allowlist=["python3"],
                on_error=lambda e: captured.append(str(e)),
            )
        assert "curl" in captured[0]
        assert "not in allowlist" in captured[0]

    def test_no_on_error_still_raises(self):
        """Allowlist error raises even without on_error callback."""
        with pytest.raises(SubprocessAllowlistError):
            run_command(["wget", "http://x.com"], allowlist=["python3"])


# ===========================================================================
# subprocess_helpers — CalledProcessError retry path
# ===========================================================================


class TestCalledProcessErrorRetry:
    """With check=True + transient exit code, should retry then raise."""

    def test_called_process_error_exhausts_retries(self):
        """check=True + exit 124 (transient) should retry retry_count times then raise."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            run_command(
                ["python3", "-c", "import sys; sys.exit(124)"],
                check=True,
                retry_count=2,
                retry_delay=0.01,
                allowlist=["python3"],
            )
        assert exc_info.value.returncode == 124

    def test_called_process_error_non_transient_raises_immediately(self):
        """check=True + non-transient exit code should raise without retry."""
        attempt_count = []
        original_run = subprocess.run

        def counting_run(*args, **kwargs):
            attempt_count.append(1)
            return original_run(*args, **kwargs)

        with patch("subprocess.run", side_effect=counting_run):
            with pytest.raises(subprocess.CalledProcessError):
                run_command(
                    ["python3", "-c", "import sys; sys.exit(42)"],
                    check=True,
                    retry_count=3,
                    retry_delay=0.01,
                    allowlist=["python3"],
                )
        # Non-transient error (42 not in {11,75,111,124}) → 1 attempt only
        assert attempt_count == [1]

    def test_on_error_called_after_exhausted_retries(self):
        """on_error callback receives the final CalledProcessError."""
        captured = []
        with pytest.raises(subprocess.CalledProcessError):
            run_command(
                ["python3", "-c", "import sys; sys.exit(124)"],
                check=True,
                retry_count=1,
                retry_delay=0.01,
                allowlist=["python3"],
                on_error=lambda e: captured.append(e),
            )
        assert len(captured) == 1
        assert isinstance(captured[0], subprocess.CalledProcessError)


# ===========================================================================
# subprocess_helpers — Generic Exception path
# ===========================================================================


class TestGenericExceptionPath:
    """OSError from a bad executable hits the generic except block."""

    def test_os_error_raises(self):
        """Non-existent/bad executable → OSError subclass → re-raised."""
        with pytest.raises(OSError):
            run_command(
                ["__no_such_cmd_fda133__"],
                allowlist=["__no_such_cmd_fda133__"],
            )

    def test_os_error_calls_on_error(self):
        captured = []
        with pytest.raises(OSError):
            run_command(
                ["__no_such_cmd_fda133__"],
                allowlist=["__no_such_cmd_fda133__"],
                on_error=lambda e: captured.append(e),
            )
        assert len(captured) == 1
        assert isinstance(captured[0], OSError)

    def test_mock_generic_exception(self):
        """Any unexpected exception from subprocess.run is re-raised."""
        with patch("subprocess.run", side_effect=MemoryError("out of memory")):
            with pytest.raises(MemoryError):
                run_command(
                    ["python3", "-c", "pass"],
                    allowlist=["python3"],
                )


# ===========================================================================
# subprocess_helpers — run_command_with_streaming
# ===========================================================================


class TestRunCommandWithStreaming:
    """Full coverage of run_command_with_streaming()."""

    def test_basic_exit_code(self):
        code = run_command_with_streaming(
            ["python3", "-c", "import sys; sys.exit(0)"],
            allowlist=["python3"],
        )
        assert code == 0

    def test_non_zero_exit_code(self):
        code = run_command_with_streaming(
            ["python3", "-c", "import sys; sys.exit(3)"],
            allowlist=["python3"],
        )
        assert code == 3

    def test_stdout_callback(self):
        lines = []
        run_command_with_streaming(
            ["python3", "-c", "print('line1'); print('line2')"],
            allowlist=["python3"],
            on_stdout=lines.append,
        )
        assert "line1" in lines
        assert "line2" in lines

    def test_stderr_callback(self):
        lines = []
        run_command_with_streaming(
            ["python3", "-c", "import sys; sys.stderr.write('err_line\\n')"],
            allowlist=["python3"],
            on_stderr=lines.append,
        )
        assert any("err_line" in ln for ln in lines)

    def test_no_callbacks_runs_silently(self):
        """When no callbacks given, output is silently consumed and exit code returned."""
        code = run_command_with_streaming(
            ["python3", "-c", "print('ignored'); import sys; sys.exit(0)"],
            allowlist=["python3"],
        )
        assert code == 0

    def test_allowlist_rejection(self):
        with pytest.raises(SubprocessAllowlistError) as exc_info:
            run_command_with_streaming(
                ["curl", "http://example.com"],
                allowlist=["python3"],
            )
        assert "curl" in str(exc_info.value)

    def test_allowlist_bypass_with_shell(self):
        code = run_command_with_streaming(
            "echo hello",
            shell=True,
            allowlist=["python3"],  # echo not in allowlist, but shell=True bypasses
        )
        assert code == 0

    def test_env_merging(self):
        lines = []
        run_command_with_streaming(
            ["python3", "-c", "import os; print(os.environ.get('STREAM_TEST_VAR', ''))"],
            allowlist=["python3"],
            env={"STREAM_TEST_VAR": "stream_value"},
            on_stdout=lines.append,
        )
        assert any("stream_value" in ln for ln in lines)

    def test_cwd_respected(self, tmp_path):
        lines = []
        run_command_with_streaming(
            ["python3", "-c", "import os; print(os.getcwd())"],
            allowlist=["python3"],
            cwd=tmp_path,
            on_stdout=lines.append,
        )
        assert any(str(tmp_path) in ln for ln in lines)

    def test_default_allowlist_used_when_none(self):
        """python3 is in DEFAULT_ALLOWLIST — should succeed with allowlist=None."""
        code = run_command_with_streaming(
            ["python3", "-c", "pass"],
            allowlist=None,
        )
        assert code == 0

    def test_timeout_raises_subprocess_timeout_error(self):
        """TimeoutExpired from communicate() is caught and re-raised as SubprocessTimeoutError."""
        mock_proc = MagicMock()
        # poll() returns non-None immediately so the select loop is skipped
        mock_proc.poll.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd=["python3", "-c", "pass"], timeout=1
        )

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(SubprocessTimeoutError):
                run_command_with_streaming(
                    ["python3", "-c", "pass"],
                    allowlist=["python3"],
                    timeout=1,
                )


# ===========================================================================
# cross_process_rate_limiter — try_acquire()
# ===========================================================================


class TestTryAcquire:
    """try_acquire() is non-blocking: True if slot available, False if at limit."""

    def test_try_acquire_returns_true_when_slot_available(self, limiter):
        assert limiter.try_acquire() is True

    def test_try_acquire_increments_request_count(self, limiter):
        limiter.try_acquire()
        stats = limiter.get_stats()
        assert stats["total_requests"] >= 1

    def test_try_acquire_returns_false_at_limit(self, temp_dir):
        """A limiter with limit=1 should return False on second call."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_dir,
            requests_per_minute=1,
        )
        first = limiter.try_acquire()
        second = limiter.try_acquire()
        assert first is True
        assert second is False

    def test_try_acquire_multiple_under_limit(self, limiter):
        results = [limiter.try_acquire() for _ in range(5)]
        assert all(r is True for r in results)

    def test_try_acquire_ioerror_returns_false(self, limiter):
        """OSError during lock → returns False gracefully."""
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = limiter.try_acquire()
        assert result is False


# ===========================================================================
# cross_process_rate_limiter — update_from_headers()
# ===========================================================================


class TestUpdateFromHeaders:
    """update_from_headers() parses X-RateLimit-* headers and logs warnings."""

    def test_no_limit_header_is_no_op(self, limiter):
        """Missing headers should not raise."""
        limiter.update_from_headers({})  # no-op

    def test_valid_headers_no_warning(self, limiter):
        limiter.update_from_headers({
            "X-RateLimit-Limit": "240",
            "X-RateLimit-Remaining": "200",
        })
        stats = limiter.get_stats()
        assert stats["rate_limit_warnings"] == 0

    def test_approaching_limit_increments_warning_count(self, limiter):
        # remaining < 10% of limit → warning
        limiter.update_from_headers({
            "X-RateLimit-Limit": "240",
            "X-RateLimit-Remaining": "5",   # 5/240 ≈ 2% < 10% threshold
        })
        stats = limiter.get_stats()
        assert stats["rate_limit_warnings"] == 1

    def test_multiple_approaching_limit_increments_each_time(self, limiter):
        for _ in range(3):
            limiter.update_from_headers({
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "2",
            })
        stats = limiter.get_stats()
        assert stats["rate_limit_warnings"] == 3

    def test_reset_timestamp_header_accepted(self, limiter):
        future_ts = str(int(time.time()) + 30)
        # Should not raise even when reset timestamp is provided
        limiter.update_from_headers({
            "X-RateLimit-Limit": "240",
            "X-RateLimit-Remaining": "5",
            "X-RateLimit-Reset": future_ts,
        })

    def test_invalid_header_values_no_crash(self, limiter):
        """Non-integer header values are silently ignored."""
        limiter.update_from_headers({
            "X-RateLimit-Limit": "not-a-number",
            "X-RateLimit-Remaining": "abc",
        })

    def test_case_insensitive_headers(self, limiter):
        """Headers are matched case-insensitively."""
        limiter.update_from_headers({
            "x-ratelimit-limit": "240",
            "x-ratelimit-remaining": "5",
        })
        stats = limiter.get_stats()
        assert stats["rate_limit_warnings"] == 1


# ===========================================================================
# cross_process_rate_limiter — get_stats() 5-min bucket fields
# ===========================================================================


class TestGetStatsWith5MinBucket:
    """get_stats() should include 5-min bucket fields when configured."""

    def test_get_stats_without_5min_has_no_bucket_fields(self, limiter):
        stats = limiter.get_stats()
        assert "five_min_tokens_remaining" not in stats
        assert "requests_per_5min" not in stats

    def test_get_stats_with_5min_has_bucket_fields(self, limiter_5min):
        stats = limiter_5min.get_stats()
        assert "five_min_tokens_remaining" in stats
        assert "requests_per_5min" in stats
        assert stats["requests_per_5min"] == 10

    def test_5min_tokens_decrease_on_acquire(self, limiter_5min):
        initial = limiter_5min.get_stats()["five_min_tokens_remaining"]
        limiter_5min.acquire()
        after = limiter_5min.get_stats()["five_min_tokens_remaining"]
        assert after == initial - 1

    def test_get_stats_contains_standard_fields(self, limiter):
        stats = limiter.get_stats()
        for field in ("total_requests", "total_waits", "total_wait_time_seconds",
                      "avg_wait_time_seconds", "wait_percentage", "rate_limit_warnings"):
            assert field in stats, f"missing field: {field}"


# ===========================================================================
# cross_process_rate_limiter — _check_and_consume_5min_bucket()
# ===========================================================================


class TestCheckAndConsume5MinBucket:
    """_check_and_consume_5min_bucket() manages the token bucket."""

    def test_returns_zero_when_tokens_available(self, limiter_5min):
        wait = limiter_5min._check_and_consume_5min_bucket()
        assert wait == 0.0

    def test_returns_nonzero_when_exhausted(self, temp_dir):
        """With only 1 token, second call should return >0."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_dir,
            requests_per_5min=1,
        )
        first = limiter._check_and_consume_5min_bucket()
        second = limiter._check_and_consume_5min_bucket()
        assert first == 0.0
        assert second > 0.0

    def test_no_5min_limit_always_returns_zero(self, limiter):
        """Without 5-min config, always returns 0."""
        assert limiter._check_and_consume_5min_bucket() == 0.0

    def test_token_count_decrements(self, limiter_5min):
        initial = limiter_5min._five_min_tokens
        limiter_5min._check_and_consume_5min_bucket()
        assert limiter_5min._five_min_tokens == initial - 1

    def test_refill_after_elapsed_time(self, temp_dir):
        """Simulate elapsed time to trigger partial refill."""
        limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_dir,
            requests_per_5min=60,
        )
        # Drain all tokens
        for _ in range(60):
            limiter._check_and_consume_5min_bucket()
        assert limiter._five_min_tokens == 0

        # Simulate 60 seconds elapsed → should refill ~12 tokens (60*60/300)
        limiter._five_min_last_refill -= 60
        limiter._check_and_consume_5min_bucket()
        assert limiter._five_min_tokens >= 10  # at least partial refill


# ===========================================================================
# calculate_backoff()
# ===========================================================================


class TestCalculateBackoff:
    """calculate_backoff() exponential backoff with optional jitter."""

    def test_attempt_0_returns_base_delay(self):
        result = calculate_backoff(0, base_delay=1.0, jitter=False)
        assert result == 1.0

    def test_attempt_1_doubles(self):
        result = calculate_backoff(1, base_delay=1.0, jitter=False)
        assert result == 2.0

    def test_attempt_2_quadruples(self):
        result = calculate_backoff(2, base_delay=1.0, jitter=False)
        assert result == 4.0

    def test_max_delay_capped(self):
        result = calculate_backoff(100, base_delay=1.0, max_delay=10.0, jitter=False)
        assert result == 10.0

    def test_custom_base_delay(self):
        result = calculate_backoff(0, base_delay=2.0, jitter=False)
        assert result == 2.0

    def test_jitter_reduces_delay(self):
        """With jitter, delay should be in [0.5 * base, base] range."""
        for _ in range(20):
            result = calculate_backoff(0, base_delay=4.0, jitter=True)
            assert 2.0 <= result <= 4.0

    def test_no_jitter_exact_value(self):
        result = calculate_backoff(3, base_delay=1.0, max_delay=60.0, jitter=False)
        assert result == 8.0


# ===========================================================================
# parse_retry_after()
# ===========================================================================


class TestParseRetryAfter:
    """parse_retry_after() handles integer seconds, date strings, and None."""

    def test_none_returns_none(self):
        assert parse_retry_after(None) is None

    def test_empty_string_returns_none(self):
        assert parse_retry_after("") is None

    def test_integer_string_returns_float(self):
        result = parse_retry_after("30")
        assert result == 30.0

    def test_float_string_returns_float(self):
        result = parse_retry_after("1.5")
        assert result == 1.5

    def test_zero_string_returns_zero(self):
        result = parse_retry_after("0")
        assert result == 0.0

    def test_valid_http_date_string_returns_positive_delay(self):
        """A date in the future should return positive seconds."""
        from email.utils import formatdate
        future_ts = time.time() + 60
        date_str = formatdate(future_ts, usegmt=True)
        result = parse_retry_after(date_str)
        assert result is not None
        assert result > 0

    def test_past_http_date_returns_zero(self):
        """A date in the past should return 0 (max(0, negative))."""
        from email.utils import formatdate
        past_ts = time.time() - 60
        date_str = formatdate(past_ts, usegmt=True)
        result = parse_retry_after(date_str)
        assert result == 0.0

    def test_invalid_string_returns_none(self):
        result = parse_retry_after("not-a-date-or-number")
        assert result is None


# ===========================================================================
# validate_rate_limit()
# ===========================================================================


class TestValidateRateLimit:
    """validate_rate_limit() enforces bounds and valid periods."""

    def test_valid_config_does_not_raise(self):
        validate_rate_limit(100, "minute")  # should not raise

    def test_valid_all_periods(self):
        for period in ("second", "minute", "hour", "day"):
            validate_rate_limit(10, period)  # no exception

    def test_non_integer_limit_raises(self):
        with pytest.raises(ValueError, match="integer"):
            validate_rate_limit(10.5, "minute")  # type: ignore[arg-type]

    def test_limit_too_low_raises(self):
        with pytest.raises(ValueError, match=str(MIN_RATE_LIMIT)):
            validate_rate_limit(0, "minute")

    def test_limit_too_high_raises(self):
        with pytest.raises(ValueError, match=str(MAX_RATE_LIMIT)):
            validate_rate_limit(MAX_RATE_LIMIT + 1, "minute")

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError, match="Invalid rate limit period"):
            validate_rate_limit(100, "week")

    def test_min_valid_limit(self):
        validate_rate_limit(MIN_RATE_LIMIT, "second")  # no exception

    def test_max_valid_limit(self):
        validate_rate_limit(MAX_RATE_LIMIT, "day")  # no exception


# ===========================================================================
# RetryPolicy.get_retry_delay()
# ===========================================================================


class TestRetryPolicyGetRetryDelay:
    """RetryPolicy.get_retry_delay() respects max_attempts and Retry-After."""

    def test_returns_delay_for_first_attempt(self):
        policy = RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        delay = policy.get_retry_delay(0)
        assert delay is not None
        assert delay > 0

    def test_returns_none_when_max_exceeded(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.get_retry_delay(3) is None
        assert policy.get_retry_delay(10) is None

    def test_uses_retry_after_header_when_present(self):
        policy = RetryPolicy(max_attempts=5, jitter=False)
        delay = policy.get_retry_delay(0, headers={"Retry-After": "42"})
        assert delay == 42.0

    def test_falls_back_to_backoff_without_retry_after(self):
        policy = RetryPolicy(max_attempts=5, base_delay=2.0, jitter=False)
        delay = policy.get_retry_delay(0, headers={})
        assert delay == 2.0  # base_delay * 2^0 = 2.0

    def test_exponential_growth_without_jitter(self):
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=False)
        delays = [policy.get_retry_delay(i) for i in range(4)]
        assert delays[1] == pytest.approx(delays[0] * 2)

    def test_no_headers_returns_backoff(self):
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=False)
        delay = policy.get_retry_delay(2, headers=None)
        assert delay == pytest.approx(4.0)  # 1.0 * 2^2

    def test_max_delay_respected(self):
        policy = RetryPolicy(max_attempts=10, base_delay=1.0, max_delay=5.0, jitter=False)
        delay = policy.get_retry_delay(10)  # would be 1024 without cap
        # attempt >= max_attempts(10), so returns None
        assert delay is None

    def test_high_attempt_capped_by_max_delay(self):
        policy = RetryPolicy(max_attempts=20, base_delay=1.0, max_delay=5.0, jitter=False)
        delay = policy.get_retry_delay(10)
        assert delay == pytest.approx(5.0)


# ===========================================================================
# rate_limited decorator
# ===========================================================================


class TestRateLimitedDecorator:
    """rate_limited() decorator acquires a slot before each call."""

    def test_decorated_function_is_called(self, limiter):
        @rate_limited(limiter)
        def my_func():
            return "ok"

        assert my_func() == "ok"

    def test_decorated_function_increments_request_count(self, limiter):
        @rate_limited(limiter)
        def my_func():
            pass

        my_func()
        stats = limiter.get_stats()
        assert stats["total_requests"] >= 1

    def test_decorated_function_passes_args(self, limiter):
        @rate_limited(limiter)
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_raises_runtime_error_on_timeout(self, temp_dir):
        """If acquire times out, RuntimeError is raised."""
        slow_limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_dir,
            requests_per_minute=1,
        )
        # Exhaust the single slot
        slow_limiter.acquire()

        @rate_limited(slow_limiter, timeout=0.01)
        def my_func():
            return "should_not_reach"

        with pytest.raises(RuntimeError, match="timeout"):
            my_func()

    def test_functools_wraps_preserves_name(self, limiter):
        @rate_limited(limiter)
        def special_function():
            pass

        assert special_function.__name__ == "special_function"


# ===========================================================================
# RateLimitContext context manager
# ===========================================================================


class TestRateLimitContext:
    """RateLimitContext acquires a slot on __enter__, no-op on __exit__."""

    def test_context_manager_allows_execution(self, limiter):
        with RateLimitContext(limiter):
            pass  # should not raise

    def test_context_manager_increments_count(self, limiter):
        with RateLimitContext(limiter):
            pass
        assert limiter.get_stats()["total_requests"] >= 1

    def test_context_manager_returns_self(self, limiter):
        ctx = RateLimitContext(limiter)
        result = ctx.__enter__()
        assert result is ctx

    def test_context_manager_raises_on_timeout(self, temp_dir):
        """Timeout during __enter__ raises RuntimeError."""
        slow_limiter = CrossProcessRateLimiter(
            has_api_key=True,
            data_dir=temp_dir,
            requests_per_minute=1,
        )
        slow_limiter.acquire()  # exhaust the single slot

        with pytest.raises(RuntimeError, match="timeout"):
            with RateLimitContext(slow_limiter, timeout=0.01):
                pass

    def test_with_statement_syntax(self, limiter):
        executed = []
        with RateLimitContext(limiter) as ctx:
            executed.append(ctx)
        assert len(executed) == 1

    def test_exception_inside_context_propagates(self, limiter):
        with pytest.raises(ValueError, match="inner error"):
            with RateLimitContext(limiter):
                raise ValueError("inner error")
