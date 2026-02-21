"""
User-Friendly Error Messages — FDA-137
=======================================

Converts raw Python exceptions into structured, actionable messages
suitable for non-developer users of the FDA plugin CLI.

Usage
-----
    from fda_tools.lib.user_errors import format_error, UserFriendlyError

    try:
        response = urllib.request.urlopen(req)
    except Exception as e:
        msg = format_error(e)
        print(msg.summary)         # One-line headline
        print(msg.explanation)     # What happened
        print(msg.fix_suggestions) # List of actionable steps
        if debug:
            print(msg.technical)   # Full exception text

    # Or raise a pre-formatted error:
    raise UserFriendlyError("K-number format invalid", ...)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ErrorMessage:
    """Structured user-friendly error message."""
    summary: str
    explanation: str
    fix_suggestions: List[str] = field(default_factory=list)
    technical: str = ""

    def format_text(self, show_technical: bool = False) -> str:
        """Return a formatted multi-line string for CLI output."""
        lines = [
            f"ERROR: {self.summary}",
            "",
            f"What happened: {self.explanation}",
        ]
        if self.fix_suggestions:
            lines.append("")
            lines.append("How to fix:")
            for suggestion in self.fix_suggestions:
                lines.append(f"  • {suggestion}")
        if show_technical and self.technical:
            lines.append("")
            lines.append(f"Technical details: {self.technical}")
        return "\n".join(lines)


class UserFriendlyError(Exception):
    """Exception that carries a :class:`ErrorMessage` payload."""

    def __init__(self, message: ErrorMessage) -> None:
        self.message = message
        super().__init__(message.summary)


# ---------------------------------------------------------------------------
# HTTP status → user message
# ---------------------------------------------------------------------------

_HTTP_TEMPLATES = {
    429: ErrorMessage(
        summary="API rate limit exceeded",
        explanation="Too many requests were sent to the FDA API in a short period.",
        fix_suggestions=[
            "Wait 60 seconds and try again",
            "Reduce the date range with --years flag",
            "Add an FDA API key for higher limits (1 000 req/min vs 240)",
        ],
        technical="HTTP 429 Too Many Requests",
    ),
    404: ErrorMessage(
        summary="Resource not found on FDA server",
        explanation="The requested FDA data could not be found. The product code or K-number may be incorrect.",
        fix_suggestions=[
            "Verify the product code or K-number is correct",
            "Check the FDA 510(k) database at accessdata.fda.gov",
            "Try a broader search with fewer filters",
        ],
        technical="HTTP 404 Not Found",
    ),
    403: ErrorMessage(
        summary="Access denied by FDA server",
        explanation="The request was rejected. Your API key may be invalid or expired.",
        fix_suggestions=[
            "Check your FDA API key with --list-keys or fda auth check",
            "Re-authenticate with fda auth login",
            "Contact support if the issue persists",
        ],
        technical="HTTP 403 Forbidden",
    ),
    500: ErrorMessage(
        summary="FDA server error (temporary)",
        explanation="The FDA API returned an internal server error. This is usually temporary.",
        fix_suggestions=[
            "Wait a few minutes and try again",
            "Check https://open.fda.gov for API status",
            "Try the request with --offline-only to use cached data",
        ],
        technical="HTTP 500 Internal Server Error",
    ),
    503: ErrorMessage(
        summary="FDA API temporarily unavailable",
        explanation="The FDA API is down for maintenance or overloaded.",
        fix_suggestions=[
            "Wait 5–10 minutes and try again",
            "Use cached data with --offline-only flag",
            "Check https://open.fda.gov for maintenance windows",
        ],
        technical="HTTP 503 Service Unavailable",
    ),
}


def _http_error_message(status_code: int, technical: str) -> ErrorMessage:
    """Return a user-friendly message for an HTTP status code."""
    if status_code in _HTTP_TEMPLATES:
        template = _HTTP_TEMPLATES[status_code]
        return ErrorMessage(
            summary=template.summary,
            explanation=template.explanation,
            fix_suggestions=list(template.fix_suggestions),
            technical=technical or template.technical,
        )
    if 500 <= status_code < 600:
        return ErrorMessage(
            summary=f"FDA server error ({status_code})",
            explanation="The FDA API returned an unexpected server error.",
            fix_suggestions=[
                "Wait a few minutes and try again",
                "Check https://open.fda.gov for API status",
            ],
            technical=technical,
        )
    return ErrorMessage(
        summary=f"HTTP error {status_code}",
        explanation="An unexpected HTTP error occurred while contacting the FDA API.",
        fix_suggestions=["Check your network connection and retry"],
        technical=technical,
    )


# ---------------------------------------------------------------------------
# Exception type → user message
# ---------------------------------------------------------------------------

_TIMEOUT_MESSAGE = ErrorMessage(
    summary="Request timed out",
    explanation="The FDA API did not respond within the timeout period.",
    fix_suggestions=[
        "Check your internet connection",
        "Try again — the FDA API may be slow",
        "Increase the timeout with --timeout <seconds>",
    ],
)

_CONNECTION_MESSAGE = ErrorMessage(
    summary="Cannot connect to FDA API",
    explanation="No network connection could be established to the FDA servers.",
    fix_suggestions=[
        "Check your internet connection",
        "Verify you are not behind a firewall blocking api.fda.gov",
        "Use cached data with --offline-only flag",
    ],
)

_FILE_NOT_FOUND_MESSAGE = ErrorMessage(
    summary="Required file not found",
    explanation="A file needed to complete this operation could not be located.",
    fix_suggestions=[
        "Run the project setup step first (e.g. fda research)",
        "Check that the project directory exists",
        "Re-run the command from the correct project directory",
    ],
)

_PERMISSION_MESSAGE = ErrorMessage(
    summary="Permission denied",
    explanation="The plugin cannot read or write a required file.",
    fix_suggestions=[
        "Check file permissions on the project directory",
        "Run the command as a user with write access",
    ],
)

_JSON_DECODE_MESSAGE = ErrorMessage(
    summary="Data file is corrupted",
    explanation="A project data file contains invalid JSON and cannot be read.",
    fix_suggestions=[
        "Re-run the data collection step to rebuild the file",
        "Delete the corrupted file and start fresh",
    ],
)


def format_error(exc: BaseException) -> ErrorMessage:
    """Convert *exc* into a :class:`ErrorMessage` with user-friendly text.

    Handles:
    - ``urllib.error.HTTPError`` (HTTP status-specific messages)
    - ``urllib.error.URLError`` / ``ConnectionError`` (network errors)
    - ``TimeoutError`` / ``socket.timeout``
    - ``FileNotFoundError``
    - ``PermissionError``
    - ``json.JSONDecodeError``
    - ``ValueError`` with K-number / date patterns

    Falls back to a generic message for unrecognised exceptions.
    """
    exc_type = type(exc).__name__
    exc_str = str(exc)
    technical = f"{exc_type}: {exc_str}"

    # ---- urllib.error.HTTPError ----------------------------------------
    try:
        import urllib.error
        if isinstance(exc, urllib.error.HTTPError):
            return _http_error_message(exc.code, technical)
    except ImportError:
        pass

    # ---- requests.HTTPError / httpx.HTTPStatusError ----------------------
    # Extract status code from common message patterns like "429 Too Many..."
    m = re.search(r"\b(4\d\d|5\d\d)\b", exc_str)
    if m and ("HTTP" in exc_type or "Status" in exc_type or "Response" in exc_type):
        return _http_error_message(int(m.group(1)), technical)

    # ---- Network / connection errors -------------------------------------
    if isinstance(exc, (TimeoutError, ConnectionError, ConnectionRefusedError,
                        ConnectionResetError, BrokenPipeError)):
        if isinstance(exc, TimeoutError):
            return ErrorMessage(**{**_TIMEOUT_MESSAGE.__dict__, "technical": technical})
        return ErrorMessage(**{**_CONNECTION_MESSAGE.__dict__, "technical": technical})

    try:
        import urllib.error
        if isinstance(exc, urllib.error.URLError):
            if "timed out" in exc_str.lower():
                return ErrorMessage(**{**_TIMEOUT_MESSAGE.__dict__, "technical": technical})
            return ErrorMessage(**{**_CONNECTION_MESSAGE.__dict__, "technical": technical})
    except ImportError:
        pass

    try:
        import socket
        if isinstance(exc, socket.timeout):
            return ErrorMessage(**{**_TIMEOUT_MESSAGE.__dict__, "technical": technical})
    except ImportError:
        pass

    # ---- File errors -----------------------------------------------------
    if isinstance(exc, FileNotFoundError):
        return ErrorMessage(**{**_FILE_NOT_FOUND_MESSAGE.__dict__, "technical": technical})

    if isinstance(exc, PermissionError):
        return ErrorMessage(**{**_PERMISSION_MESSAGE.__dict__, "technical": technical})

    # ---- JSON decode error -----------------------------------------------
    import json
    if isinstance(exc, json.JSONDecodeError):
        return ErrorMessage(**{**_JSON_DECODE_MESSAGE.__dict__, "technical": technical})

    # ---- ValueError: K-number or date validation -------------------------
    if isinstance(exc, ValueError):
        msg_lower = exc_str.lower()
        if "k-number" in msg_lower or re.search(r"\bk\d{6}\b", exc_str, re.IGNORECASE):
            return ErrorMessage(
                summary="Invalid K-number format",
                explanation="K-numbers must be in the format K followed by 6 digits (e.g. K241335).",
                fix_suggestions=[
                    "Use format K######  (capital K, 6 digits)",
                    "Look up the K-number at accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm",
                ],
                technical=technical,
            )
        if any(w in msg_lower for w in ("date", "year", "yyyy")):
            return ErrorMessage(
                summary="Invalid date or year format",
                explanation="The date or year value provided is not in the expected format.",
                fix_suggestions=[
                    "Use four-digit years: --years 2024",
                    "Use date range format: --years 2020-2024",
                ],
                technical=technical,
            )
        if "product code" in msg_lower or "product_code" in msg_lower:
            return ErrorMessage(
                summary="Invalid product code",
                explanation="The product code must be a 2–3 letter FDA device classification code.",
                fix_suggestions=[
                    "Product codes are 2–3 uppercase letters (e.g. DQY, OVE)",
                    "Look up product codes at accessdata.fda.gov/scripts/cdrh/cfdocs/cfpcd/classification.cfm",
                ],
                technical=technical,
            )

    # ---- Generic fallback ------------------------------------------------
    return ErrorMessage(
        summary="An unexpected error occurred",
        explanation=exc_str or "No details available.",
        fix_suggestions=[
            "Try the command again",
            "Run with --debug for full error details",
            "Contact support if the issue persists",
        ],
        technical=technical,
    )
