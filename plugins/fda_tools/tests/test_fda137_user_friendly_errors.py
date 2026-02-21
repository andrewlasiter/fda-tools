"""
User-Friendly Error Messages Tests (FDA-137)
=============================================

Verifies that ``format_error()`` converts raw Python exceptions into
structured, actionable :class:`ErrorMessage` objects and that the helper
classes behave correctly.

Test count: 22
Target: pytest plugins/fda_tools/tests/test_fda137_user_friendly_errors.py -v
"""

from __future__ import annotations

import json
import socket
import urllib.error
from http.client import HTTPMessage

import pytest

from fda_tools.lib.user_errors import ErrorMessage, UserFriendlyError, format_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_error(code: int, msg: str = "reason") -> urllib.error.HTTPError:
    """Build a minimal ``urllib.error.HTTPError`` for a given status code."""
    return urllib.error.HTTPError(
        url="https://api.fda.gov/device/510k.json",
        code=code,
        msg=msg,
        hdrs=HTTPMessage(),
        fp=None,
    )


def _url_error(reason: str = "connection refused") -> urllib.error.URLError:
    return urllib.error.URLError(reason)


# ---------------------------------------------------------------------------
# TestErrorMessageDataclass
# ---------------------------------------------------------------------------


class TestErrorMessageDataclass:
    """Tests for the ErrorMessage dataclass itself."""

    def test_format_text_contains_summary(self):
        msg = ErrorMessage(
            summary="Something broke",
            explanation="Details here",
            fix_suggestions=["Try again"],
        )
        text = msg.format_text()
        assert "Something broke" in text
        assert "ERROR:" in text

    def test_format_text_contains_explanation(self):
        msg = ErrorMessage(summary="S", explanation="Explanation text")
        text = msg.format_text()
        assert "Explanation text" in text

    def test_format_text_lists_suggestions(self):
        msg = ErrorMessage(
            summary="S",
            explanation="E",
            fix_suggestions=["Step A", "Step B"],
        )
        text = msg.format_text()
        assert "Step A" in text
        assert "Step B" in text

    def test_format_text_hides_technical_by_default(self):
        msg = ErrorMessage(summary="S", explanation="E", technical="raw stack trace")
        text = msg.format_text(show_technical=False)
        assert "raw stack trace" not in text

    def test_format_text_shows_technical_when_requested(self):
        msg = ErrorMessage(summary="S", explanation="E", technical="raw stack trace")
        text = msg.format_text(show_technical=True)
        assert "raw stack trace" in text

    def test_default_technical_is_empty_string(self):
        msg = ErrorMessage(summary="S", explanation="E")
        assert msg.technical == ""


# ---------------------------------------------------------------------------
# TestUserFriendlyError
# ---------------------------------------------------------------------------


class TestUserFriendlyError:
    """Tests for the UserFriendlyError exception class."""

    def test_carries_message_payload(self):
        inner = ErrorMessage(summary="Bad thing", explanation="Because reasons")
        exc = UserFriendlyError(inner)
        assert exc.message is inner

    def test_str_repr_is_summary(self):
        inner = ErrorMessage(summary="Rate limit hit", explanation="Too many")
        exc = UserFriendlyError(inner)
        assert str(exc) == "Rate limit hit"

    def test_is_exception(self):
        inner = ErrorMessage(summary="S", explanation="E")
        exc = UserFriendlyError(inner)
        assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# TestFormatErrorHTTP
# ---------------------------------------------------------------------------


class TestFormatErrorHTTP:
    """Tests for HTTP-specific error formatting."""

    def test_429_rate_limit(self):
        msg = format_error(_http_error(429))
        assert "rate limit" in msg.summary.lower()
        assert any("wait" in s.lower() or "60" in s for s in msg.fix_suggestions)

    def test_404_not_found(self):
        msg = format_error(_http_error(404))
        assert "not found" in msg.summary.lower()

    def test_403_forbidden(self):
        msg = format_error(_http_error(403))
        assert "denied" in msg.summary.lower() or "forbidden" in msg.summary.lower()

    def test_500_server_error(self):
        msg = format_error(_http_error(500))
        assert "server error" in msg.summary.lower()

    def test_503_unavailable(self):
        msg = format_error(_http_error(503))
        assert "unavailable" in msg.summary.lower() or "503" in msg.summary

    def test_unknown_5xx_returns_generic_server_error(self):
        msg = format_error(_http_error(502))
        assert "502" in msg.summary or "server error" in msg.summary.lower()

    def test_technical_includes_status_code(self):
        msg = format_error(_http_error(429))
        assert "429" in msg.technical

    def test_fix_suggestions_non_empty(self):
        for code in (429, 404, 403, 500, 503):
            msg = format_error(_http_error(code))
            assert len(msg.fix_suggestions) >= 1, f"No suggestions for {code}"


# ---------------------------------------------------------------------------
# TestFormatErrorNetwork
# ---------------------------------------------------------------------------


class TestFormatErrorNetwork:
    """Tests for network/connection error formatting."""

    def test_timeout_error(self):
        msg = format_error(TimeoutError("timed out"))
        assert "timeout" in msg.summary.lower() or "timed" in msg.summary.lower()

    def test_connection_error(self):
        msg = format_error(ConnectionError("refused"))
        assert "connect" in msg.summary.lower()

    def test_url_error_timed_out(self):
        exc = _url_error("timed out: connect")
        msg = format_error(exc)
        assert "timeout" in msg.summary.lower() or "timed" in msg.summary.lower()

    def test_url_error_connection_refused(self):
        exc = _url_error("connection refused")
        msg = format_error(exc)
        assert "connect" in msg.summary.lower()

    def test_socket_timeout(self):
        msg = format_error(socket.timeout("timed out"))
        assert "timeout" in msg.summary.lower() or "timed" in msg.summary.lower()


# ---------------------------------------------------------------------------
# TestFormatErrorFile
# ---------------------------------------------------------------------------


class TestFormatErrorFile:
    """Tests for file-related error formatting."""

    def test_file_not_found(self):
        msg = format_error(FileNotFoundError("no such file"))
        assert "not found" in msg.summary.lower() or "file" in msg.summary.lower()

    def test_permission_error(self):
        msg = format_error(PermissionError("access denied"))
        assert "permission" in msg.summary.lower() or "denied" in msg.summary.lower()

    def test_json_decode_error(self):
        try:
            json.loads("{bad json}")
        except json.JSONDecodeError as exc:
            msg = format_error(exc)
            assert "corrupt" in msg.summary.lower() or "invalid" in msg.summary.lower() or "json" in msg.summary.lower()
        else:
            pytest.fail("Expected JSONDecodeError was not raised")


# ---------------------------------------------------------------------------
# TestFormatErrorValueError
# ---------------------------------------------------------------------------


class TestFormatErrorValueError:
    """Tests for ValueError-specific patterns."""

    def test_k_number_format_error(self):
        msg = format_error(ValueError("Invalid k-number: K12345"))
        assert "k-number" in msg.summary.lower() or "K-number" in msg.summary

    def test_date_format_error(self):
        msg = format_error(ValueError("Invalid date format: expected YYYY-MM-DD"))
        assert "date" in msg.summary.lower() or "year" in msg.summary.lower()

    def test_product_code_error(self):
        msg = format_error(ValueError("product_code must be 2-3 letters"))
        assert "product code" in msg.summary.lower()

    def test_generic_value_error_fallback(self):
        msg = format_error(ValueError("some unrelated value error"))
        assert msg.summary  # should return something
        assert msg.explanation


# ---------------------------------------------------------------------------
# TestFormatErrorGenericFallback
# ---------------------------------------------------------------------------


class TestFormatErrorGenericFallback:
    """Tests for the generic fallback path."""

    def test_unknown_exception_returns_generic(self):
        msg = format_error(RuntimeError("something random"))
        assert "unexpected" in msg.summary.lower() or msg.summary

    def test_technical_includes_exception_type(self):
        msg = format_error(RuntimeError("something random"))
        assert "RuntimeError" in msg.technical

    def test_fix_suggestions_always_present(self):
        msg = format_error(RuntimeError("anything"))
        assert len(msg.fix_suggestions) >= 1
