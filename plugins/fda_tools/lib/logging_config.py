#!/usr/bin/env python3
"""
Centralized Logging Configuration for FDA Tools Plugin.

Provides standardized logging setup with:
- Console and file output handlers
- Log rotation with configurable retention
- Structured JSON audit logging for regulatory events
- CLI flag integration (--verbose, --quiet)
- Separate audit log for FDA regulatory events

Created as part of FDA-18 (GAP-014) to replace print() diagnostic output.

Usage:
from fda_tools.lib.logging_config import setup_logging, get_logger, get_audit_logger

    # Basic setup (INFO level to console)
    setup_logging()

    # With CLI flags
    setup_logging(verbose=True)        # DEBUG level
    setup_logging(quiet=True)          # WARNING level only
    setup_logging(log_file="run.log")  # Also write to file

    # Get a module-specific logger
    logger = get_logger(__name__)
    logger.info("Processing device %s", device_code)
    logger.debug("Cache hit for key %s", cache_key)
    logger.warning("API rate limit approaching")
    logger.error("Failed to fetch device data: %s", error)

    # Audit logging for regulatory events
    audit = get_audit_logger()
    audit.log_event(
        action="predicate_accepted",
        subject="K241335",
        details={"confidence": 85, "rationale": "Same product code"}
    )

    # Add --verbose/--quiet to argparse
from fda_tools.lib.logging_config import add_logging_args
    add_logging_args(parser)
    args = parser.parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)
"""

import argparse
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default log directory
DEFAULT_LOG_DIR = os.path.expanduser("~/fda-510k-data/logs")

# Default log file names
DEFAULT_LOG_FILE = "fda_tools.log"
AUDIT_LOG_FILE = "fda_audit.jsonl"

# Rotation settings
MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB per log file
BACKUP_COUNT = 5                   # Keep 5 rotated files

# Formatting
CONSOLE_FORMAT = "%(levelname)-8s %(name)s: %(message)s"
CONSOLE_FORMAT_VERBOSE = (
    "%(asctime)s %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
)
FILE_FORMAT = (
    "%(asctime)s %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level state
_configured = False
_root_logger_level = logging.INFO


# ---------------------------------------------------------------------------
# Custom Formatter for Audit Logs (JSON Lines)
# ---------------------------------------------------------------------------

class JSONAuditFormatter(logging.Formatter):
    """Formats log records as JSON lines for structured audit logging.

    Each log entry includes:
    - timestamp (ISO 8601 UTC)
    - level
    - logger name
    - message
    - Any extra fields passed via the `extra` dict
    """

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra audit fields if present
        for key in ("action", "subject", "details", "user", "session_id",
                     "data_sources", "confidence", "decision_type",
                     "project", "command"):
            value = getattr(record, key, None)
            if value is not None:
                entry[key] = value

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Console Filter (suppress overly verbose third-party loggers)
# ---------------------------------------------------------------------------

class FDAToolsFilter(logging.Filter):
    """Filter that allows FDA tools loggers and suppresses noisy third-party loggers."""

    # Third-party loggers that should be at WARNING or above
    SUPPRESSED_PREFIXES = (
        "urllib3",
        "requests",
        "chardet",
        "PIL",
        "matplotlib",
        "numba",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        for prefix in self.SUPPRESSED_PREFIXES:
            if record.name.startswith(prefix) and record.levelno < logging.WARNING:
                return False
        return True


# ---------------------------------------------------------------------------
# Core Setup Functions
# ---------------------------------------------------------------------------

def setup_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_level: Optional[int] = None,
    enable_audit: bool = True,
    enable_file: bool = True,
    console_output: bool = True,
    max_bytes: int = MAX_LOG_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    """Configure the root logger for the FDA Tools plugin.

    This function is idempotent -- calling it multiple times reconfigures
    the logging system without creating duplicate handlers.

    Args:
        verbose: If True, set level to DEBUG with detailed format.
        quiet: If True, set level to WARNING (suppresses INFO).
        log_file: Optional path to a specific log file. If not provided
                  and enable_file is True, uses default location.
        log_dir: Directory for log files. Default: ~/fda-510k-data/logs/
        log_level: Explicit log level (overrides verbose/quiet).
        enable_audit: If True, enable structured audit logging to JSONL file.
        enable_file: If True, enable file-based logging with rotation.
        console_output: If True, add console (stderr) handler.
        max_bytes: Maximum size per log file before rotation.
        backup_count: Number of rotated backup files to keep.

    Returns:
        The configured root logger.
    """
    global _configured, _root_logger_level

    # Determine log level
    if log_level is not None:
        level = log_level
    elif verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    _root_logger_level = level

    # Get the root logger for fda namespace
    root = logging.getLogger()

    # Remove existing handlers to prevent duplicates on reconfiguration
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    root.setLevel(level)

    # --- Console Handler ---
    if console_output:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(level)

        fmt = CONSOLE_FORMAT_VERBOSE if verbose else CONSOLE_FORMAT
        console.setFormatter(logging.Formatter(fmt, datefmt=DATE_FORMAT))
        console.addFilter(FDAToolsFilter())
        root.addHandler(console)

    # --- File Handler (with rotation) ---
    if enable_file:
        log_directory = Path(log_dir or DEFAULT_LOG_DIR)
        log_directory.mkdir(parents=True, exist_ok=True)

        file_path = Path(log_file) if log_file else log_directory / DEFAULT_LOG_FILE

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            str(file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # File always captures DEBUG
        file_handler.setFormatter(
            logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT)
        )
        root.addHandler(file_handler)

    # --- Audit Log Handler (JSON Lines) ---
    if enable_audit:
        log_directory = Path(log_dir or DEFAULT_LOG_DIR)
        log_directory.mkdir(parents=True, exist_ok=True)

        audit_path = log_directory / AUDIT_LOG_FILE

        audit_handler = logging.handlers.RotatingFileHandler(
            str(audit_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(JSONAuditFormatter())

        # Only attach to the audit logger namespace
        audit_logger = logging.getLogger("fda.audit")
        # Remove old handlers from audit logger too
        for handler in audit_logger.handlers[:]:
            audit_logger.removeHandler(handler)
            handler.close()
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
        # Prevent audit messages from propagating to root (avoid console duplication)
        audit_logger.propagate = False

    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Get a named logger within the FDA tools namespace.

    If logging has not been configured yet, applies a basic configuration
    to avoid "No handler" warnings.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    if not _configured:
        # Apply minimal config to prevent "No handler" warnings
        logging.basicConfig(
            level=logging.INFO,
            format=CONSOLE_FORMAT,
            stream=sys.stderr,
        )

    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------

class AuditLogger:
    """Structured audit logger for FDA regulatory events.

    Writes JSON-formatted entries to the audit log file for:
    - API calls and data retrievals
    - User actions and decisions
    - Data modifications and exports
    - Pipeline step completions

    Each entry includes a UTC timestamp, action type, subject,
    and arbitrary detail fields.

    Usage:
        audit = get_audit_logger()
        audit.log_event(
            action="predicate_accepted",
            subject="K241335",
            details={"score": 85}
        )
        audit.log_api_call("openFDA 510k", params={"k_number": "K241335"})
        audit.log_data_modification("device_profile.json", "Updated specs")
    """

    def __init__(self, logger_name: str = "fda.audit"):
        self._logger = logging.getLogger(logger_name)

    def log_event(
        self,
        action: str,
        subject: str = "",
        details: Optional[Dict[str, Any]] = None,
        *,
        project: str = "",
        command: str = "",
        confidence: Optional[float] = None,
        decision_type: str = "",
        data_sources: Optional[list] = None,
        level: int = logging.INFO,
    ) -> None:
        """Log a structured audit event.

        Args:
            action: The action type (e.g., "predicate_accepted", "api_call").
            subject: The entity acted upon (e.g., K-number, product code).
            details: Additional structured data for the event.
            project: Project name context.
            command: Command that triggered the event.
            confidence: Confidence score (0-100) if applicable.
            decision_type: "auto", "manual", or "deferred".
            data_sources: List of data sources consulted.
            level: Log level (default: INFO).
        """
        extra = {
            "action": action,
            "subject": subject,
            "details": details or {},
            "project": project,
            "command": command,
        }
        if confidence is not None:
            extra["confidence"] = confidence
        if decision_type:
            extra["decision_type"] = decision_type
        if data_sources:
            extra["data_sources"] = data_sources

        self._logger.log(
            level,
            "AUDIT: %s on %s",
            action,
            subject or "(no subject)",
            extra=extra,
        )

    def log_api_call(
        self,
        endpoint: str,
        *,
        params: Optional[Dict] = None,
        status: str = "success",
        response_time_ms: Optional[float] = None,
        project: str = "",
    ) -> None:
        """Log an API call for audit trail.

        Args:
            endpoint: API endpoint called.
            params: Request parameters (sanitized -- no API keys).
            status: "success", "error", "cached", "rate_limited".
            response_time_ms: Response time in milliseconds.
            project: Project name context.
        """
        details = {
            "endpoint": endpoint,
            "params": params or {},
            "status": status,
        }
        if response_time_ms is not None:
            details["response_time_ms"] = response_time_ms

        self.log_event(
            action="api_call",
            subject=endpoint,
            details=details,
            project=project,
        )

    def log_data_modification(
        self,
        file_path: str,
        description: str,
        *,
        project: str = "",
        command: str = "",
    ) -> None:
        """Log a data modification for audit trail.

        Args:
            file_path: Path of the modified file.
            description: What was changed.
            project: Project name context.
            command: Command that triggered the change.
        """
        self.log_event(
            action="data_modification",
            subject=file_path,
            details={"description": description},
            project=project,
            command=command,
        )

    def log_export(
        self,
        export_type: str,
        file_path: str,
        *,
        record_count: int = 0,
        project: str = "",
    ) -> None:
        """Log an export operation.

        Args:
            export_type: Type of export (e.g., "csv", "html", "json", "pdf").
            file_path: Output file path.
            record_count: Number of records exported.
            project: Project name context.
        """
        self.log_event(
            action="data_export",
            subject=file_path,
            details={
                "export_type": export_type,
                "record_count": record_count,
            },
            project=project,
        )


# Module-level singleton
_audit_logger_instance: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton AuditLogger instance.

    Returns:
        The AuditLogger singleton.
    """
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()
    return _audit_logger_instance


# ---------------------------------------------------------------------------
# CLI Integration
# ---------------------------------------------------------------------------

def add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add --verbose and --quiet flags to an argparse parser.

    Creates a mutually exclusive group so that --verbose and --quiet
    cannot be used together.

    Args:
        parser: The argparse.ArgumentParser to augment.

    Usage:
        parser = argparse.ArgumentParser()
        add_logging_args(parser)
        args = parser.parse_args()
        setup_logging(verbose=args.verbose, quiet=args.quiet)
    """

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG) logging output",
    )
    group.add_argument(
        "-q", "--quiet",
        action="store_true",
        default=False,
        help="Suppress informational messages (WARNING and above only)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to log file (default: ~/fda-510k-data/logs/fda_tools.log)",
    )


def apply_logging_args(args: argparse.Namespace) -> logging.Logger:
    """Apply parsed CLI args to configure logging.

    Convenience function that reads verbose/quiet/log_file from
    parsed argparse namespace and calls setup_logging().

    Args:
        args: Parsed argparse namespace with verbose, quiet, log_file attrs.

    Returns:
        The configured root logger.
    """
    return setup_logging(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
        log_file=getattr(args, "log_file", None),
    )


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def reset_logging() -> None:
    """Reset logging configuration to unconfigured state.

    Primarily used in testing to ensure clean state between tests.
    Removes all handlers from the root logger and resets the
    configured flag.
    """
    global _configured, _audit_logger_instance

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    # Also reset the audit logger
    audit = logging.getLogger("fda.audit")
    for handler in audit.handlers[:]:
        audit.removeHandler(handler)
        handler.close()

    _configured = False
    _audit_logger_instance = None


def get_log_dir() -> str:
    """Get the current log directory path.

    Returns:
        Absolute path to the log directory.
    """
    return DEFAULT_LOG_DIR


__all__ = [
    "setup_logging",
    "get_logger",
    "get_audit_logger",
    "AuditLogger",
    "add_logging_args",
    "apply_logging_args",
    "reset_logging",
    "get_log_dir",
    "JSONAuditFormatter",
    "FDAToolsFilter",
]
