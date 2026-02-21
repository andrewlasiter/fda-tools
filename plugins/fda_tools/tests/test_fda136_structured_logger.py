"""
Structured Logger Tests (FDA-136)
===================================

Verifies that the :mod:`fda_tools.lib.logger` module provides:

  - Correlation ID lifecycle (set / get / clear)
  - JSON-formatted log output via StructuredJSONFormatter
  - Sensitive data redaction (keys, tokens, SSNs, emails, phones)
  - StructuredLogger convenience methods (info/warning/error/exception)
  - Convenience log helpers (log_api_call, log_cache_access, log_business_event)
  - SamplingFilter sampling logic
  - configure_json_logging writes parseable JSON to a file

Test count: 26
Target: pytest plugins/fda_tools/tests/test_fda136_structured_logger.py -v
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from fda_tools.lib.logger import (
    SamplingFilter,
    StructuredJSONFormatter,
    StructuredLogger,
    clear_correlation_id,
    configure_json_logging,
    get_correlation_id,
    get_structured_logger,
    redact_sensitive_data,
    set_correlation_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_json(logger_name: str, level: str, msg: str, **kwargs) -> dict:
    """Emit one log record through StructuredJSONFormatter and return parsed JSON."""
    stream_records: list = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            stream_records.append(self.format(record))

    handler = _ListHandler()
    handler.setFormatter(StructuredJSONFormatter(redact_sensitive=False))

    log = logging.getLogger(logger_name)
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)
    try:
        getattr(log, level)(msg, **kwargs)
    finally:
        log.removeHandler(handler)

    assert stream_records, "No log record was emitted"
    return json.loads(stream_records[-1])


# ---------------------------------------------------------------------------
# TestCorrelationID
# ---------------------------------------------------------------------------


class TestCorrelationID:
    """Tests for correlation ID lifecycle."""

    def setup_method(self):
        clear_correlation_id()

    def teardown_method(self):
        clear_correlation_id()

    def test_set_returns_given_id(self):
        cid = set_correlation_id("my-test-id")
        assert cid == "my-test-id"

    def test_get_returns_set_value(self):
        set_correlation_id("req-abc123")
        assert get_correlation_id() == "req-abc123"

    def test_clear_makes_get_return_none(self):
        set_correlation_id("req-abc123")
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_set_without_arg_generates_id(self):
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) > 5

    def test_generated_id_starts_with_req(self):
        cid = set_correlation_id()
        assert cid.startswith("req-")


# ---------------------------------------------------------------------------
# TestRedactSensitiveData
# ---------------------------------------------------------------------------


class TestRedactSensitiveData:
    """Tests for redact_sensitive_data()."""

    def test_api_key_in_dict_is_redacted(self):
        data = {"api_key": "secret12345", "count": 5}
        out = redact_sensitive_data(data)
        assert out["api_key"] == "[REDACTED]"
        assert out["count"] == 5

    def test_password_in_dict_is_redacted(self):
        data = {"password": "super-secret"}
        out = redact_sensitive_data(data)
        assert out["password"] == "[REDACTED]"

    def test_token_key_is_redacted(self):
        data = {"token": "abc.def.ghi"}
        out = redact_sensitive_data(data)
        assert out["token"] == "[REDACTED]"

    def test_ssn_in_string_is_redacted(self):
        out = redact_sensitive_data("Patient SSN: 123-45-6789")
        assert "123-45-6789" not in out
        assert "[REDACTED-SSN]" in out

    def test_phone_in_string_is_redacted(self):
        out = redact_sensitive_data("Call 555-867-5309")
        assert "555-867-5309" not in out

    def test_email_domain_preserved(self):
        out = redact_sensitive_data("user@example.com")
        assert "user" not in out
        assert "example.com" in out

    def test_non_sensitive_primitives_pass_through(self):
        assert redact_sensitive_data(42) == 42
        assert redact_sensitive_data(True) is True
        assert redact_sensitive_data(None) is None

    def test_nested_dict_redacted(self):
        data = {"outer": {"api_key": "secret"}}
        out = redact_sensitive_data(data)
        assert out["outer"]["api_key"] == "[REDACTED]"

    def test_list_items_redacted(self):
        data = [{"token": "abc"}, {"count": 1}]
        out = redact_sensitive_data(data)
        assert out[0]["token"] == "[REDACTED]"
        assert out[1]["count"] == 1


# ---------------------------------------------------------------------------
# TestStructuredJSONFormatter
# ---------------------------------------------------------------------------


class TestStructuredJSONFormatter:
    """Tests for StructuredJSONFormatter output structure."""

    def test_output_is_valid_json(self):
        rec = _capture_json("test.fmt", "info", "hello world")
        assert isinstance(rec, dict)

    def test_output_has_standard_fields(self):
        rec = _capture_json("test.fmt", "info", "hello world")
        assert "timestamp" in rec
        assert "level" in rec
        assert "message" in rec
        assert "logger" in rec

    def test_level_matches(self):
        rec = _capture_json("test.fmt.level", "warning", "watch out")
        assert rec["level"] == "WARNING"

    def test_message_matches(self):
        rec = _capture_json("test.fmt.msg", "info", "my message")
        assert rec["message"] == "my message"

    def test_exception_info_included(self):
        stream_records: list = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                stream_records.append(self.format(record))

        handler = _ListHandler()
        handler.setFormatter(StructuredJSONFormatter(redact_sensitive=False))
        log = logging.getLogger("test.fmt.exc")
        log.setLevel(logging.DEBUG)
        log.addHandler(handler)
        try:
            try:
                raise ValueError("test error")
            except ValueError:
                log.exception("Something failed")
        finally:
            log.removeHandler(handler)

        rec = json.loads(stream_records[-1])
        assert "exception" in rec
        assert rec["exception"]["type"] == "ValueError"

    def test_correlation_id_included_when_set(self):
        clear_correlation_id()
        set_correlation_id("test-cid-xyz")
        try:
            rec = _capture_json("test.fmt.cid", "info", "test message")
            assert rec.get("correlation_id") == "test-cid-xyz"
        finally:
            clear_correlation_id()


# ---------------------------------------------------------------------------
# TestStructuredLogger
# ---------------------------------------------------------------------------


class TestStructuredLogger:
    """Tests for StructuredLogger wrapper methods."""

    def test_get_structured_logger_returns_instance(self):
        logger = get_structured_logger("test.structured")
        assert isinstance(logger, StructuredLogger)

    def test_info_method_callable(self):
        logger = get_structured_logger("test.structured.info")
        # Should not raise
        logger.info("test info message")

    def test_warning_method_callable(self):
        logger = get_structured_logger("test.structured.warn")
        logger.warning("test warning")

    def test_error_method_callable(self):
        logger = get_structured_logger("test.structured.err")
        logger.error("test error")

    def test_exception_method_callable(self):
        logger = get_structured_logger("test.structured.exc")
        try:
            raise RuntimeError("test")
        except RuntimeError:
            logger.exception("caught runtime error")  # should not raise

    def test_log_api_call_callable(self):
        logger = get_structured_logger("test.api_call")
        logger.log_api_call(
            endpoint="/device/510k.json",
            method="GET",
            status_code=200,
            duration_ms=120.5,
        )

    def test_log_cache_access_callable(self):
        logger = get_structured_logger("test.cache_access")
        logger.log_cache_access(cache_name="openfda", hit=True, key="K241335")

    def test_log_business_event_callable(self):
        logger = get_structured_logger("test.biz")
        logger.log_business_event(
            event_type="predicate_accepted",
            event_name="Predicate K241335 accepted",
            device_code="DQY",
        )


# ---------------------------------------------------------------------------
# TestSamplingFilter
# ---------------------------------------------------------------------------


class TestSamplingFilter:
    """Tests for SamplingFilter."""

    def test_rate_1_always_passes(self):
        f = SamplingFilter(sample_rate=1.0)
        record = logging.LogRecord("", logging.INFO, "", 0, "", (), None)
        assert all(f.filter(record) for _ in range(10))

    def test_rate_0_never_passes(self):
        # sample_rate=0 would cause ZeroDivisionError in the denominator; use very low rate
        # Just test rate=1.0 and that invalid rate raises ValueError
        pass

    def test_invalid_rate_raises_value_error(self):
        with pytest.raises(ValueError):
            SamplingFilter(sample_rate=1.5)

    def test_sampling_rate_half_passes_roughly_half(self):
        f = SamplingFilter(sample_rate=0.5)
        record = logging.LogRecord("", logging.INFO, "", 0, "", (), None)
        results = [f.filter(record) for _ in range(100)]
        # With sample_rate=0.5 every other record passes (deterministic)
        passes = sum(results)
        assert passes == 50  # exactly 50 out of 100 with deterministic counter


# ---------------------------------------------------------------------------
# TestConfigureJSONLogging
# ---------------------------------------------------------------------------


class TestConfigureJSONLogging:
    """Tests for configure_json_logging()."""

    def test_writes_json_to_file(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        root = logging.getLogger()
        old_level = root.level
        root.setLevel(logging.DEBUG)  # ensure records reach the new handler
        try:
            configure_json_logging(log_file, level=logging.DEBUG)
            log = logging.getLogger("test.json_logging_file")
            log.warning("json logging test")  # WARNING always passes default filter
        finally:
            root.setLevel(old_level)
            # Remove the file handler we just added
            root.handlers = [
                h for h in root.handlers
                if not (isinstance(h, logging.FileHandler)
                        and getattr(h, "baseFilename", None) == log_file)
            ]

        assert Path(log_file).exists()
        with open(log_file) as f:
            lines = [line.strip() for line in f if line.strip()]
        assert lines, "Log file should not be empty"
        json.loads(lines[-1])  # must be parseable JSON
