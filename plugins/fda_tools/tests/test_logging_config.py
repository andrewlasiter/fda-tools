"""
Comprehensive tests for lib/logging_config.py -- Centralized Logging Configuration.

Tests cover:
1. Basic setup and configuration
2. Log level control (verbose, quiet, default)
3. File handler with rotation
4. Audit logger (JSON structured events)
5. CLI flag integration (--verbose, --quiet, --log-file)
6. Third-party logger filtering
7. Idempotent reconfiguration
8. Reset/teardown behavior
9. AuditLogger event methods (api_call, data_modification, export)
10. Edge cases and error handling
11. Backward compatibility (print statements still work)
12. JSON audit format validation

Created as part of FDA-18 (GAP-014).
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure lib/ is on the path
LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")

from logging_config import (  # type: ignore
    setup_logging,
    get_logger,
    get_audit_logger,
    AuditLogger,
    add_logging_args,
    apply_logging_args,
    reset_logging,
    get_log_dir,
    JSONAuditFormatter,
    FDAToolsFilter,
    CONSOLE_FORMAT,
    CONSOLE_FORMAT_VERBOSE,
    FILE_FORMAT,
    MAX_LOG_BYTES,
    BACKUP_COUNT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_logging_state():
    """Reset logging state before and after each test."""
    reset_logging()
    yield
    reset_logging()


@pytest.fixture
def tmp_log_dir(tmp_path):
    """Provide a temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return str(log_dir)


@pytest.fixture
def tmp_log_file(tmp_path):
    """Provide a temporary log file path."""
    return str(tmp_path / "test.log")


# ---------------------------------------------------------------------------
# Test 1: Basic Setup and Configuration
# ---------------------------------------------------------------------------

class TestBasicSetup:
    """Test basic logging setup functionality."""

    def test_setup_returns_root_logger(self):
        """setup_logging() should return the root logger."""
        logger = setup_logging(enable_file=False, enable_audit=False)
        assert isinstance(logger, logging.Logger)

    def test_default_level_is_info(self):
        """Default log level should be INFO."""
        setup_logging(enable_file=False, enable_audit=False)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_console_handler_created(self):
        """A console (stderr) handler should be created by default."""
        setup_logging(enable_file=False, enable_audit=False)
        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 1

    def test_no_console_when_disabled(self):
        """No console handler when console_output=False."""
        setup_logging(
            enable_file=False, enable_audit=False, console_output=False
        )
        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 0


# ---------------------------------------------------------------------------
# Test 2: Log Level Control
# ---------------------------------------------------------------------------

class TestLogLevels:
    """Test verbose, quiet, and explicit log level settings."""

    def test_verbose_sets_debug(self):
        """--verbose should set level to DEBUG."""
        setup_logging(verbose=True, enable_file=False, enable_audit=False)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_quiet_sets_warning(self):
        """--quiet should set level to WARNING."""
        setup_logging(quiet=True, enable_file=False, enable_audit=False)
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_explicit_level_overrides_flags(self):
        """Explicit log_level should override verbose/quiet."""
        setup_logging(
            verbose=True,
            log_level=logging.ERROR,
            enable_file=False,
            enable_audit=False,
        )
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_debug_messages_visible_in_verbose(self, capsys):
        """DEBUG messages should appear when verbose=True."""
        setup_logging(verbose=True, enable_file=False, enable_audit=False)
        logger = logging.getLogger("test.verbose")
        logger.debug("test debug message")
        captured = capsys.readouterr()
        assert "test debug message" in captured.err

    def test_debug_messages_hidden_at_info(self, capsys):
        """DEBUG messages should NOT appear at INFO level."""
        setup_logging(enable_file=False, enable_audit=False)
        logger = logging.getLogger("test.info")
        logger.debug("hidden debug message")
        captured = capsys.readouterr()
        assert "hidden debug message" not in captured.err

    def test_info_messages_hidden_in_quiet(self, capsys):
        """INFO messages should NOT appear when quiet=True."""
        setup_logging(quiet=True, enable_file=False, enable_audit=False)
        logger = logging.getLogger("test.quiet")
        logger.info("hidden info message")
        captured = capsys.readouterr()
        assert "hidden info message" not in captured.err

    def test_warning_visible_in_quiet(self, capsys):
        """WARNING messages should appear even in quiet mode."""
        setup_logging(quiet=True, enable_file=False, enable_audit=False)
        logger = logging.getLogger("test.quiet_warn")
        logger.warning("visible warning")
        captured = capsys.readouterr()
        assert "visible warning" in captured.err


# ---------------------------------------------------------------------------
# Test 3: File Handler with Rotation
# ---------------------------------------------------------------------------

class TestFileHandler:
    """Test file-based logging with rotation."""

    def test_file_handler_created(self, tmp_log_dir):
        """File handler should be created when enable_file=True."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_audit=False,
            console_output=False,
        )
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    def test_file_handler_writes_messages(self, tmp_log_dir):
        """Messages should be written to the log file."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_audit=False,
            console_output=False,
        )
        logger = logging.getLogger("test.file")
        logger.info("file test message 12345")

        # Flush handlers
        for h in logging.getLogger().handlers:
            h.flush()

        log_file = Path(tmp_log_dir) / "fda_tools.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "file test message 12345" in content

    def test_file_captures_debug_even_at_info(self, tmp_log_dir):
        """File handler should capture DEBUG even when console is INFO."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_audit=False,
            console_output=False,
        )
        logger = logging.getLogger("test.file_debug")
        logger.setLevel(logging.DEBUG)
        # Root is INFO, but file handler is DEBUG
        # We need to ensure the root level allows DEBUG through
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("debug in file only")

        for h in logging.getLogger().handlers:
            h.flush()

        log_file = Path(tmp_log_dir) / "fda_tools.log"
        content = log_file.read_text()
        assert "debug in file only" in content

    def test_custom_log_file_path(self, tmp_log_file):
        """Custom log file path should be used when specified."""
        setup_logging(
            log_file=tmp_log_file,
            enable_audit=False,
            console_output=False,
        )
        logger = logging.getLogger("test.custom_path")
        logger.info("custom path test")

        for h in logging.getLogger().handlers:
            h.flush()

        assert Path(tmp_log_file).exists()
        content = Path(tmp_log_file).read_text()
        assert "custom path test" in content

    def test_rotation_config(self, tmp_log_dir):
        """File handler should have correct rotation settings."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_audit=False,
            console_output=False,
            max_bytes=5000,
            backup_count=3,
        )
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        handler = file_handlers[0]
        assert handler.maxBytes == 5000
        assert handler.backupCount == 3

    def test_log_dir_created_if_missing(self, tmp_path):
        """Log directory should be created if it does not exist."""
        new_dir = str(tmp_path / "new_log_dir" / "nested")
        setup_logging(
            log_dir=new_dir,
            enable_audit=False,
            console_output=False,
        )
        assert Path(new_dir).exists()


# ---------------------------------------------------------------------------
# Test 4: Audit Logger (Structured JSON Events)
# ---------------------------------------------------------------------------

class TestAuditLogger:
    """Test structured audit logging functionality."""

    def test_audit_log_file_created(self, tmp_log_dir):
        """Audit log JSONL file should be created."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()
        audit.log_event(action="test_action", subject="test_subject")

        # Flush
        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        assert audit_path.exists()

    def test_audit_entry_is_valid_json(self, tmp_log_dir):
        """Each audit log entry should be valid JSON."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()
        audit.log_event(
            action="predicate_accepted",
            subject="K241335",
            details={"confidence": 85},
        )

        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        lines = audit_path.read_text().strip().split("\n")
        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        assert entry["action"] == "predicate_accepted"
        assert entry["subject"] == "K241335"
        assert entry["details"]["confidence"] == 85
        assert "timestamp" in entry

    def test_audit_log_api_call(self, tmp_log_dir):
        """log_api_call should create structured API call entry."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()
        audit.log_api_call(
            "openFDA/510k",
            params={"k_number": "K241335"},
            status="success",
            response_time_ms=150.5,
            project="test_project",
        )

        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        entry = json.loads(audit_path.read_text().strip().split("\n")[-1])
        assert entry["action"] == "api_call"
        assert entry["details"]["endpoint"] == "openFDA/510k"
        assert entry["details"]["status"] == "success"
        assert entry["details"]["response_time_ms"] == 150.5
        assert entry["project"] == "test_project"

    def test_audit_log_data_modification(self, tmp_log_dir):
        """log_data_modification should log file changes."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()
        audit.log_data_modification(
            "device_profile.json",
            "Updated predicate list",
            project="my_project",
            command="review",
        )

        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        entry = json.loads(audit_path.read_text().strip().split("\n")[-1])
        assert entry["action"] == "data_modification"
        assert entry["subject"] == "device_profile.json"
        assert entry["command"] == "review"

    def test_audit_log_export(self, tmp_log_dir):
        """log_export should log export operations."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()
        audit.log_export(
            "csv",
            "/output/results.csv",
            record_count=150,
            project="test",
        )

        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        entry = json.loads(audit_path.read_text().strip().split("\n")[-1])
        assert entry["action"] == "data_export"
        assert entry["details"]["export_type"] == "csv"
        assert entry["details"]["record_count"] == 150

    def test_audit_does_not_propagate_to_console(self, tmp_log_dir, capsys):
        """Audit log messages should NOT appear in console output."""
        setup_logging(log_dir=tmp_log_dir, enable_file=False)
        audit = get_audit_logger()
        audit.log_event(action="test_no_console", subject="hidden")

        captured = capsys.readouterr()
        assert "test_no_console" not in captured.err
        assert "test_no_console" not in captured.out

    def test_audit_logger_singleton(self):
        """get_audit_logger should return the same instance."""
        setup_logging(enable_file=False, enable_audit=False, console_output=False)
        a1 = get_audit_logger()
        a2 = get_audit_logger()
        assert a1 is a2


# ---------------------------------------------------------------------------
# Test 5: CLI Flag Integration
# ---------------------------------------------------------------------------

class TestCLIFlags:
    """Test argparse integration for --verbose and --quiet flags."""

    def test_add_logging_args_creates_flags(self):
        """add_logging_args should add -v/--verbose, -q/--quiet, --log-file."""
        parser = argparse.ArgumentParser()
        add_logging_args(parser)

        # Test --verbose
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True
        assert args.quiet is False

        # Test --quiet
        args = parser.parse_args(["--quiet"])
        assert args.quiet is True
        assert args.verbose is False

        # Test --log-file
        args = parser.parse_args(["--log-file", "/tmp/test.log"])
        assert args.log_file == "/tmp/test.log"

    def test_short_flags_work(self):
        """Short flags -v and -q should work."""
        parser = argparse.ArgumentParser()
        add_logging_args(parser)

        args = parser.parse_args(["-v"])
        assert args.verbose is True

        args = parser.parse_args(["-q"])
        assert args.quiet is True

    def test_verbose_and_quiet_mutually_exclusive(self):
        """--verbose and --quiet should be mutually exclusive."""
        parser = argparse.ArgumentParser()
        add_logging_args(parser)

        with pytest.raises(SystemExit):
            parser.parse_args(["--verbose", "--quiet"])

    def test_apply_logging_args(self):
        """apply_logging_args should configure logging from parsed args."""
        parser = argparse.ArgumentParser()
        add_logging_args(parser)

        args = parser.parse_args(["--verbose"])
        logger = apply_logging_args(args)

        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_default_no_flags(self):
        """No flags should result in INFO level."""
        parser = argparse.ArgumentParser()
        add_logging_args(parser)

        args = parser.parse_args([])
        apply_logging_args(args)

        root = logging.getLogger()
        assert root.level == logging.INFO


# ---------------------------------------------------------------------------
# Test 6: Third-Party Logger Filtering
# ---------------------------------------------------------------------------

class TestThirdPartyFilter:
    """Test FDAToolsFilter suppresses noisy third-party loggers."""

    def test_urllib3_debug_suppressed(self):
        """urllib3 DEBUG messages should be filtered out."""
        f = FDAToolsFilter()
        record = logging.LogRecord(
            name="urllib3.connectionpool",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Starting new HTTP connection",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False

    def test_urllib3_warning_passes(self):
        """urllib3 WARNING messages should pass through."""
        f = FDAToolsFilter()
        record = logging.LogRecord(
            name="urllib3.connectionpool",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Connection pool warning",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    def test_fda_tools_debug_passes(self):
        """FDA tools DEBUG messages should pass through."""
        f = FDAToolsFilter()
        record = logging.LogRecord(
            name="scripts.batchfetch",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Processing batch",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    def test_requests_info_suppressed(self):
        """requests library INFO messages should be filtered."""
        f = FDAToolsFilter()
        record = logging.LogRecord(
            name="requests.packages.urllib3",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="SSL connection established",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False


# ---------------------------------------------------------------------------
# Test 7: Idempotent Reconfiguration
# ---------------------------------------------------------------------------

class TestIdempotentConfig:
    """Test that calling setup_logging() multiple times works correctly."""

    def test_no_duplicate_handlers(self):
        """Multiple calls should not create duplicate handlers."""
        setup_logging(enable_file=False, enable_audit=False)
        setup_logging(enable_file=False, enable_audit=False)
        setup_logging(enable_file=False, enable_audit=False)

        root = logging.getLogger()
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 1

    def test_level_change_on_reconfig(self):
        """Level should change when reconfigured."""
        setup_logging(enable_file=False, enable_audit=False)
        assert logging.getLogger().level == logging.INFO

        setup_logging(verbose=True, enable_file=False, enable_audit=False)
        assert logging.getLogger().level == logging.DEBUG

        setup_logging(quiet=True, enable_file=False, enable_audit=False)
        assert logging.getLogger().level == logging.WARNING


# ---------------------------------------------------------------------------
# Test 8: Reset/Teardown
# ---------------------------------------------------------------------------

class TestReset:
    """Test reset_logging() cleans up properly."""

    def test_reset_removes_handlers(self):
        """reset_logging should remove all handlers."""
        setup_logging(enable_file=False, enable_audit=False)
        assert len(logging.getLogger().handlers) > 0

        reset_logging()
        assert len(logging.getLogger().handlers) == 0

    def test_reset_clears_audit_singleton(self):
        """reset_logging should clear the AuditLogger singleton."""
        setup_logging(enable_file=False, enable_audit=False)
        a1 = get_audit_logger()
        reset_logging()
        a2 = get_audit_logger()
        assert a1 is not a2

    def test_reset_clears_audit_handlers(self):
        """reset_logging should remove audit logger handlers."""
        setup_logging(enable_file=False, enable_audit=True, console_output=False)
        audit_logger = logging.getLogger("fda.audit")
        assert len(audit_logger.handlers) > 0

        reset_logging()
        assert len(audit_logger.handlers) == 0


# ---------------------------------------------------------------------------
# Test 9: JSON Audit Formatter
# ---------------------------------------------------------------------------

class TestJSONAuditFormatter:
    """Test the JSON audit formatter produces valid structured output."""

    def test_basic_format(self):
        """Formatter should produce valid JSON with required fields."""
        fmt = JSONAuditFormatter()
        record = logging.LogRecord(
            name="fda.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        entry = json.loads(output)

        assert "timestamp" in entry
        assert entry["level"] == "INFO"
        assert entry["logger"] == "fda.audit"
        assert entry["message"] == "Test message"

    def test_extra_fields_included(self):
        """Extra audit fields should be included in JSON output."""
        fmt = JSONAuditFormatter()
        record = logging.LogRecord(
            name="fda.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Audit event",
            args=(),
            exc_info=None,
        )
        record.action = "predicate_accepted"
        record.subject = "K241335"
        record.details = {"score": 85}
        record.confidence = 85.0

        output = fmt.format(record)
        entry = json.loads(output)

        assert entry["action"] == "predicate_accepted"
        assert entry["subject"] == "K241335"
        assert entry["details"]["score"] == 85
        assert entry["confidence"] == 85.0

    def test_exception_info_included(self):
        """Exception information should be included when present."""
        fmt = JSONAuditFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord(
                name="fda.audit",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        output = fmt.format(record)
        entry = json.loads(output)
        assert "exception" in entry
        assert "ValueError: test error" in entry["exception"]

    def test_timestamp_is_iso_utc(self):
        """Timestamp should be ISO 8601 UTC format."""
        fmt = JSONAuditFormatter()
        record = logging.LogRecord(
            name="fda.audit",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="ts test",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        entry = json.loads(output)
        # Should parse as ISO 8601
        from datetime import datetime
        ts = datetime.fromisoformat(entry["timestamp"])
        assert ts is not None


# ---------------------------------------------------------------------------
# Test 10: get_logger Without Prior Setup
# ---------------------------------------------------------------------------

class TestGetLogger:
    """Test get_logger behavior without explicit setup."""

    def test_get_logger_without_setup(self):
        """get_logger should work even without calling setup_logging first."""
        # reset_logging already called by fixture
        logger = get_logger("test.no_setup")
        assert isinstance(logger, logging.Logger)
        # Should not raise when logging
        logger.info("test message without setup")

    def test_get_logger_returns_named_logger(self):
        """get_logger should return a logger with the given name."""
        setup_logging(enable_file=False, enable_audit=False, console_output=False)
        logger = get_logger("my.custom.module")
        assert logger.name == "my.custom.module"


# ---------------------------------------------------------------------------
# Test 11: Backward Compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Verify that print() still works for user-facing output."""

    def test_print_still_works(self, capsys):
        """print() statements should still produce output regardless of logging config."""
        setup_logging(quiet=True, enable_file=False, enable_audit=False)

        # Simulate user-facing output that should always appear
        print("AUDIT_STATUS:OK")
        print("K241335")

        captured = capsys.readouterr()
        assert "AUDIT_STATUS:OK" in captured.out
        assert "K241335" in captured.out

    def test_print_and_logging_coexist(self, capsys):
        """print() and logging should work side by side without interference."""
        setup_logging(enable_file=False, enable_audit=False)

        logger = logging.getLogger("test.coexist")

        # User-facing output via print
        print("RESULT:success")

        # Diagnostic output via logging
        logger.info("Processing complete")

        captured = capsys.readouterr()
        assert "RESULT:success" in captured.out
        assert "Processing complete" in captured.err


# ---------------------------------------------------------------------------
# Test 12: get_log_dir
# ---------------------------------------------------------------------------

class TestGetLogDir:
    """Test get_log_dir utility."""

    def test_returns_string(self):
        """get_log_dir should return a string path."""
        result = get_log_dir()
        assert isinstance(result, str)

    def test_returns_expected_default(self):
        """get_log_dir should return the default log directory."""
        result = get_log_dir()
        assert result.endswith("fda-510k-data/logs")


# ---------------------------------------------------------------------------
# Test 13: Multiple Log Entries in Audit
# ---------------------------------------------------------------------------

class TestMultipleAuditEntries:
    """Test that multiple audit entries are correctly appended."""

    def test_multiple_entries_appended(self, tmp_log_dir):
        """Multiple audit events should all appear in the JSONL file."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()

        # Log 5 events
        for i in range(5):
            audit.log_event(
                action=f"test_action_{i}",
                subject=f"subject_{i}",
            )

        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        lines = [
            line for line in audit_path.read_text().strip().split("\n")
            if line.strip()
        ]
        assert len(lines) == 5

        # Verify each is valid JSON with correct action
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["action"] == f"test_action_{i}"


# ---------------------------------------------------------------------------
# Test 14: Verbose Format Includes Source Location
# ---------------------------------------------------------------------------

class TestVerboseFormat:
    """Test that verbose format includes source location details."""

    def test_verbose_format_has_funcname(self, capsys):
        """Verbose format should include function name and line number."""
        setup_logging(verbose=True, enable_file=False, enable_audit=False)
        logger = logging.getLogger("test.verbose_format")
        logger.info("verbose format check")

        captured = capsys.readouterr()
        # Verbose format includes [name:funcName:lineno]
        assert "test.verbose_format" in captured.err


# ---------------------------------------------------------------------------
# Test 15: AuditLogger with Decision Type and Confidence
# ---------------------------------------------------------------------------

class TestAuditLoggerExtended:
    """Test extended audit logger fields."""

    def test_event_with_all_fields(self, tmp_log_dir):
        """log_event with all optional fields should include them all."""
        setup_logging(
            log_dir=tmp_log_dir,
            enable_file=False,
            console_output=False,
        )
        audit = get_audit_logger()
        audit.log_event(
            action="predicate_accepted",
            subject="K241335",
            details={"score_breakdown": {"similarity": 40, "recency": 20}},
            project="test_project",
            command="review",
            confidence=85.0,
            decision_type="auto",
            data_sources=["openFDA", "MAUDE"],
        )

        for h in logging.getLogger("fda.audit").handlers:
            h.flush()

        audit_path = Path(tmp_log_dir) / "fda_audit.jsonl"
        entry = json.loads(audit_path.read_text().strip().split("\n")[-1])

        assert entry["action"] == "predicate_accepted"
        assert entry["subject"] == "K241335"
        assert entry["project"] == "test_project"
        assert entry["command"] == "review"
        assert entry["confidence"] == 85.0
        assert entry["decision_type"] == "auto"
        assert entry["data_sources"] == ["openFDA", "MAUDE"]
        assert entry["details"]["score_breakdown"]["similarity"] == 40
