#!/usr/bin/env python3
"""
Enhanced Structured Logging for FDA Tools Production.

Extends the existing logging_config.py with:
- JSON structured logging for production environments
- Correlation ID tracking for request tracing
- Sensitive data redaction (API keys, PHI, PII)
- Context propagation across threads
- Integration with monitoring and alerting

Created as part of FDA-190 (DEVOPS-004) for production observability.

Usage:
from fda_tools.lib.logger import get_structured_logger, set_correlation_id

    # Get structured logger
    logger = get_structured_logger(__name__)

    # Set correlation ID for request tracing
    set_correlation_id("req-12345")

    # Log with structured context
    logger.info("Processing device data", extra={
        "device_code": "OVE",
        "k_number": "K241335",
        "action": "fetch_predicates",
    })

    # Automatic sensitive data redaction
    logger.info("API response", extra={
        "api_key": "secret-key-12345",  # Will be redacted
        "response_size": 1024,
    })

    # Error logging with context
    try:
        process_data()
    except Exception as e:
        logger.error("Processing failed", exc_info=True, extra={
            "device_code": "OVE",
            "step": "enrichment",
        })
"""

import contextvars
import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

# Context variable for correlation ID (thread-safe, async-safe)
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Patterns for sensitive data redaction
SENSITIVE_PATTERNS = {
    # API keys and tokens
    "api_key": re.compile(r'\b(api[_-]?key|apikey|token|bearer|authorization)\b', re.IGNORECASE),
    "api_key_value": re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Long alphanumeric strings

    # Credentials
    "password": re.compile(r'\b(password|passwd|pwd|secret)\b', re.IGNORECASE),

    # Personal Identifiable Information (PII)
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # Social Security Number
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone": re.compile(r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b'),

    # Protected Health Information (PHI)
    "mrn": re.compile(r'\b(mrn|medical[_-]?record[_-]?number)\b', re.IGNORECASE),
    "dob": re.compile(r'\b(date[_-]?of[_-]?birth|dob)\b', re.IGNORECASE),
}

# Keys that should be redacted if they appear in log context
SENSITIVE_KEYS = {
    "api_key", "apikey", "token", "bearer", "authorization",
    "password", "passwd", "pwd", "secret", "private_key",
    "ssn", "social_security", "email", "phone", "mobile",
    "mrn", "medical_record", "dob", "date_of_birth",
    "credit_card", "card_number", "cvv", "account_number",
}

# Fields to always include in structured logs
STANDARD_FIELDS = {
    "timestamp", "level", "logger", "message", "correlation_id",
    "thread_id", "process_id", "function", "line_number",
}


# ---------------------------------------------------------------------------
# Sensitive Data Redaction
# ---------------------------------------------------------------------------

def redact_sensitive_data(data: Any, redact_keys: bool = True) -> Any:
    """Redact sensitive information from data.

    Args:
        data: Data to redact (str, dict, list, or primitive)
        redact_keys: If True, also redact based on key names

    Returns:
        Redacted copy of the data
    """
    if isinstance(data, dict):
        return {
            k: redact_sensitive_data(v, redact_keys=redact_keys)
            if not (redact_keys and k.lower() in SENSITIVE_KEYS)
            else "[REDACTED]"
            for k, v in data.items()
        }

    elif isinstance(data, (list, tuple)):
        return type(data)(redact_sensitive_data(item, redact_keys=redact_keys) for item in data)

    elif isinstance(data, str):
        # Redact sensitive patterns in strings
        redacted = data

        # Check for API keys
        if SENSITIVE_PATTERNS["api_key"].search(redacted):
            redacted = SENSITIVE_PATTERNS["api_key_value"].sub("[REDACTED]", redacted)

        # Redact passwords
        if SENSITIVE_PATTERNS["password"].search(redacted):
            redacted = re.sub(r'(password|passwd|pwd|secret)\s*[:=]\s*\S+',
                            r'\1=[REDACTED]', redacted, flags=re.IGNORECASE)

        # Redact SSN
        redacted = SENSITIVE_PATTERNS["ssn"].sub("[REDACTED-SSN]", redacted)

        # Redact email (partial - keep domain for debugging)
        redacted = re.sub(
            r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
            r'[REDACTED]@\2',
            redacted
        )

        # Redact phone numbers
        redacted = SENSITIVE_PATTERNS["phone"].sub("[REDACTED-PHONE]", redacted)

        return redacted

    else:
        # Primitives (int, float, bool, None) pass through
        return data


# ---------------------------------------------------------------------------
# Correlation ID Management
# ---------------------------------------------------------------------------

def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for the current context.

    Args:
        correlation_id: Optional correlation ID. If not provided, generates a new UUID.

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = f"req-{uuid.uuid4().hex[:12]}"

    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID.

    Returns:
        Current correlation ID or None if not set
    """
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)


# ---------------------------------------------------------------------------
# JSON Structured Formatter
# ---------------------------------------------------------------------------

class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging with correlation IDs and context.

    Formats log records as single-line JSON with:
    - Standard fields (timestamp, level, logger, message)
    - Correlation ID for request tracing
    - Thread/process information
    - Source location (function, line number)
    - Extra context fields
    - Exception information
    - Automatic sensitive data redaction
    """

    def __init__(
        self,
        *args,
        redact_sensitive: bool = True,
        include_thread_info: bool = True,
        **kwargs
    ):
        """Initialize the formatter.

        Args:
            redact_sensitive: If True, redact sensitive data in logs
            include_thread_info: If True, include thread/process IDs
        """
        super().__init__(*args, **kwargs)
        self.redact_sensitive = redact_sensitive
        self.include_thread_info = include_thread_info

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add thread/process info if enabled
        if self.include_thread_info:
            log_entry["thread_id"] = record.thread
            log_entry["thread_name"] = record.threadName
            log_entry["process_id"] = record.process

        # Add source location
        log_entry["function"] = record.funcName
        log_entry["line_number"] = record.lineno
        log_entry["pathname"] = record.pathname

        # Add extra context fields (from `extra` dict)
        for key, value in record.__dict__.items():
            # Skip standard LogRecord attributes and our known fields
            if (
                not key.startswith("_")
                and key not in STANDARD_FIELDS
                and key not in dir(logging.LogRecord("", 0, "", 0, "", (), None))
            ):
                log_entry[key] = value

        # Add exception information if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Redact sensitive data if enabled
        if self.redact_sensitive:
            log_entry = redact_sensitive_data(log_entry, redact_keys=True)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Structured Logger Wrapper
# ---------------------------------------------------------------------------

class StructuredLogger:
    """Wrapper around standard logger that ensures structured context.

    Provides convenience methods for adding structured context to logs
    and ensures correlation ID is always included.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize structured logger.

        Args:
            logger: Underlying logging.Logger instance
        """
        self._logger = logger

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Internal log method that adds correlation ID."""
        extra = kwargs.get("extra", {})

        # Add correlation ID if not already present
        if "correlation_id" not in extra:
            correlation_id = get_correlation_id()
            if correlation_id:
                extra["correlation_id"] = correlation_id

        kwargs["extra"] = extra
        self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message with structured context."""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message with structured context."""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message with structured context."""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message with structured context."""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log critical message with structured context."""
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log exception with traceback and structured context."""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)

    # Convenience methods for common operations

    def log_api_call(
        self,
        endpoint: str,
        method: str = "GET",
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **context
    ) -> None:
        """Log an API call with structured context.

        Args:
            endpoint: API endpoint called
            method: HTTP method
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            **context: Additional context fields
        """
        extra = {
            "event_type": "api_call",
            "endpoint": endpoint,
            "method": method,
            **context,
        }

        if status_code is not None:
            extra["status_code"] = status_code

        if duration_ms is not None:
            extra["duration_ms"] = duration_ms

        level = logging.INFO if status_code and status_code < 400 else logging.WARNING
        self._log(level, f"API call: {method} {endpoint}", extra=extra)

    def log_database_query(
        self,
        query_name: str,
        duration_ms: Optional[float] = None,
        row_count: Optional[int] = None,
        **context
    ) -> None:
        """Log a database query with structured context.

        Args:
            query_name: Name/description of the query
            duration_ms: Query duration in milliseconds
            row_count: Number of rows returned
            **context: Additional context fields
        """
        extra = {
            "event_type": "db_query",
            "query_name": query_name,
            **context,
        }

        if duration_ms is not None:
            extra["duration_ms"] = duration_ms

        if row_count is not None:
            extra["row_count"] = row_count

        self._log(logging.DEBUG, f"Database query: {query_name}", extra=extra)

    def log_cache_access(
        self,
        cache_name: str,
        hit: bool,
        key: Optional[str] = None,
        **context
    ) -> None:
        """Log a cache access with structured context.

        Args:
            cache_name: Name of the cache
            hit: Whether it was a cache hit
            key: Cache key (will be hashed in logs)
            **context: Additional context fields
        """
        extra = {
            "event_type": "cache_access",
            "cache_name": cache_name,
            "hit": hit,
            **context,
        }

        if key:
            # Hash the key for privacy
            import hashlib
            extra["key_hash"] = hashlib.sha256(key.encode()).hexdigest()[:16]

        self._log(
            logging.DEBUG,
            f"Cache {'HIT' if hit else 'MISS'}: {cache_name}",
            extra=extra
        )

    def log_business_event(
        self,
        event_type: str,
        event_name: str,
        **context
    ) -> None:
        """Log a business event with structured context.

        Args:
            event_type: Type of business event (e.g., "predicate_selected")
            event_name: Human-readable event name
            **context: Additional context fields
        """
        extra = {
            "event_type": event_type,
            **context,
        }

        self._log(logging.INFO, f"Business event: {event_name}", extra=extra)


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------

def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    logger = logging.getLogger(name)
    return StructuredLogger(logger)


def configure_json_logging(
    log_file: str,
    level: int = logging.INFO,
    redact_sensitive: bool = True,
) -> None:
    """Configure JSON structured logging to a file.

    This is separate from the console logging configured in logging_config.py.
    Use this for production JSON logs that will be ingested by log aggregation
    systems (e.g., ELK, Splunk, CloudWatch).

    Args:
        log_file: Path to JSON log file
        level: Log level
        redact_sensitive: Whether to redact sensitive data
    """
    # Create JSON formatter
    formatter = StructuredJSONFormatter(redact_sensitive=redact_sensitive)

    # Create file handler
    from pathlib import Path
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(formatter)

    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    logging.info("JSON structured logging configured: %s", log_file)


# ---------------------------------------------------------------------------
# Log Sampling (for high-volume logs)
# ---------------------------------------------------------------------------

class SamplingFilter(logging.Filter):
    """Filter that samples logs to reduce volume.

    Useful for high-frequency logs (e.g., cache hits) to prevent
    overwhelming the logging system.
    """

    def __init__(self, sample_rate: float = 0.1):
        """Initialize sampling filter.

        Args:
            sample_rate: Fraction of logs to keep (0.0 to 1.0)
        """
        super().__init__()
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")

        self.sample_rate = sample_rate
        self._counter = 0
        self._lock = threading.Lock()

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record based on sample rate."""
        if self.sample_rate >= 1.0:
            return True  # Always pass through

        with self._lock:
            self._counter += 1
            # Deterministic sampling based on counter
            return (self._counter % int(1 / self.sample_rate)) == 0


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "StructuredLogger",
    "StructuredJSONFormatter",
    "SamplingFilter",
    "get_structured_logger",
    "configure_json_logging",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "redact_sensitive_data",
    "SENSITIVE_PATTERNS",
    "SENSITIVE_KEYS",
]
