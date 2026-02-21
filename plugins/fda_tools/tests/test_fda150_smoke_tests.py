"""
Smoke Tests for Critical Workflows (FDA-150).
===============================================

Fast, non-network checks that verify the most important paths through the
FDA tools plugin are functional.  These tests run on every CI push and act
as a first-pass gate: if any smoke test fails, the build is considered
broken regardless of unit-test results.

Scope: imports, class instantiation, config wiring, and constant sanity
checks.  No network calls, no external services, no slow I/O.

Critical workflows covered:
  1. Config loading               -- get_config() returns a valid Config
  2. Bridge server port           -- SERVER_PORT is a valid TCP port
  3. FDA API client               -- FDAClient imports cleanly; rate-limit
                                     constants are positive ints
  4. Cross-process rate limiter   -- CrossProcessRateLimiter() initialises
  5. Quota tracker                -- QuotaTracker() initialises and returns
                                     a well-formed QuotaStatus
  6. Cache manager                -- CacheManager() initialises
  7. User-friendly errors         -- format_error() handles an exception
  8. Project backup               -- ProjectBackup() initialises with
                                     a custom directory
  9. Structured logger            -- get_structured_logger() returns a logger
  10. Bulk lib module import      -- all public lib modules importable

Test count: 22
Target: pytest plugins/fda_tools/tests/test_fda150_smoke_tests.py -v
"""

from __future__ import annotations

import importlib


# ---------------------------------------------------------------------------
# Smoke 1: Config loading
# ---------------------------------------------------------------------------


class TestConfigSmoke:
    """Config loads and exposes expected keys."""

    def test_get_config_returns_config_object(self):
        from fda_tools.lib.config import Config, get_config

        cfg = get_config()
        assert isinstance(cfg, Config)

    def test_config_bridge_server_port_positive(self):
        from fda_tools.lib.config import get_config

        cfg = get_config()
        port = cfg.get_int("api.bridge_server_port", default=0)
        assert port > 0

    def test_config_rate_limit_openfda_positive(self):
        from fda_tools.lib.config import get_config

        cfg = get_config()
        limit = cfg.get_int("rate_limiting.rate_limit_openfda", default=0)
        assert limit > 0

    def test_config_rate_limit_authenticated_positive(self):
        from fda_tools.lib.config import get_config

        cfg = get_config()
        limit = cfg.get_int("rate_limiting.rate_limit_openfda_authenticated", default=0)
        assert limit > 0


# ---------------------------------------------------------------------------
# Smoke 2: Bridge server
# ---------------------------------------------------------------------------


class TestBridgeServerSmoke:
    """Bridge server module loads and exposes a valid port."""

    def test_server_port_is_valid_tcp_port(self):
        from fda_tools.bridge import server

        assert isinstance(server.SERVER_PORT, int)
        assert 1 <= server.SERVER_PORT <= 65535

    def test_server_port_matches_config(self):
        from fda_tools.bridge import server
        from fda_tools.lib.config import get_config

        cfg = get_config()
        expected = cfg.get_int("api.bridge_server_port", default=18790)
        assert server.SERVER_PORT == expected


# ---------------------------------------------------------------------------
# Smoke 3: FDA API client
# ---------------------------------------------------------------------------


class TestFDAClientSmoke:
    """FDAClient imports and exposes positive rate-limit constants."""

    def test_fda_client_class_importable(self):
        from fda_tools.scripts.fda_api_client import FDAClient

        assert FDAClient is not None

    def test_unauthenticated_rate_limit_positive(self):
        from fda_tools.scripts.fda_api_client import UNAUTHENTICATED_RATE_LIMIT

        assert isinstance(UNAUTHENTICATED_RATE_LIMIT, int)
        assert UNAUTHENTICATED_RATE_LIMIT >= 1

    def test_authenticated_rate_limit_positive(self):
        from fda_tools.scripts.fda_api_client import AUTHENTICATED_RATE_LIMIT

        assert isinstance(AUTHENTICATED_RATE_LIMIT, int)
        assert AUTHENTICATED_RATE_LIMIT >= 1

    def test_authenticated_limit_exceeds_unauthenticated(self):
        from fda_tools.scripts.fda_api_client import (
            AUTHENTICATED_RATE_LIMIT,
            UNAUTHENTICATED_RATE_LIMIT,
        )

        assert AUTHENTICATED_RATE_LIMIT > UNAUTHENTICATED_RATE_LIMIT


# ---------------------------------------------------------------------------
# Smoke 4: Cross-process rate limiter
# ---------------------------------------------------------------------------


class TestRateLimiterSmoke:
    """CrossProcessRateLimiter initialises without errors."""

    def test_rate_limiter_init(self, tmp_path):
        from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter

        limiter = CrossProcessRateLimiter(has_api_key=True, data_dir=str(tmp_path))
        assert limiter.requests_per_minute > 0

    def test_rate_limiter_get_status_returns_dict(self, tmp_path):
        from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter

        limiter = CrossProcessRateLimiter(has_api_key=True, data_dir=str(tmp_path))
        status = limiter.get_status()
        assert isinstance(status, dict)
        assert "requests_last_minute" in status
        assert "utilization_percent" in status


# ---------------------------------------------------------------------------
# Smoke 5: Quota tracker
# ---------------------------------------------------------------------------


class TestQuotaTrackerSmoke:
    """QuotaTracker initialises and returns a well-formed QuotaStatus."""

    def test_quota_tracker_init(self, tmp_path):
        from fda_tools.lib.quota_tracker import QuotaTracker

        tracker = QuotaTracker(has_api_key=True, data_dir=str(tmp_path))
        assert tracker.minute_limit > 0

    def test_check_status_returns_quota_status(self, tmp_path):
        from fda_tools.lib.quota_tracker import QuotaLevel, QuotaStatus, QuotaTracker

        tracker = QuotaTracker(has_api_key=True, data_dir=str(tmp_path))
        status = tracker.check_status()
        assert isinstance(status, QuotaStatus)
        assert status.level == QuotaLevel.NORMAL
        assert status.requests_last_minute == 0


# ---------------------------------------------------------------------------
# Smoke 6: Cache manager
# ---------------------------------------------------------------------------


class TestCacheManagerSmoke:
    """CacheManager initialises without errors."""

    def test_cache_manager_init(self, tmp_path):
        from fda_tools.lib.cache_manager import CacheManager

        cm = CacheManager(base_dir=str(tmp_path))
        assert cm is not None

    def test_cache_manager_has_expected_methods(self, tmp_path):
        from fda_tools.lib.cache_manager import CacheManager

        cm = CacheManager(base_dir=str(tmp_path))
        assert callable(getattr(cm, "get_stats", None))
        assert callable(getattr(cm, "purge_stale", None))


# ---------------------------------------------------------------------------
# Smoke 7: User-friendly errors
# ---------------------------------------------------------------------------


class TestUserErrorsSmoke:
    """format_error() handles common exceptions without raising."""

    def test_format_error_on_connection_error(self):
        from fda_tools.lib.user_errors import ErrorMessage, format_error

        result = format_error(ConnectionError("network down"))
        assert isinstance(result, ErrorMessage)
        assert result.summary

    def test_format_error_on_timeout(self):
        from fda_tools.lib.user_errors import ErrorMessage, format_error

        result = format_error(TimeoutError("timed out"))
        assert isinstance(result, ErrorMessage)

    def test_format_error_on_generic_exception(self):
        from fda_tools.lib.user_errors import ErrorMessage, format_error

        result = format_error(RuntimeError("unexpected"))
        assert isinstance(result, ErrorMessage)


# ---------------------------------------------------------------------------
# Smoke 8: Project backup
# ---------------------------------------------------------------------------


class TestProjectBackupSmoke:
    """ProjectBackup initialises with a custom data directory."""

    def test_project_backup_init(self, tmp_path):
        from fda_tools.lib.project_backup import ProjectBackup

        pb = ProjectBackup(
            projects_dir=str(tmp_path / "projects"),
            backup_dir=str(tmp_path / "backups"),
        )
        assert pb is not None

    def test_list_backups_empty_on_new_dir(self, tmp_path):
        from fda_tools.lib.project_backup import ProjectBackup

        pb = ProjectBackup(
            projects_dir=str(tmp_path / "projects"),
            backup_dir=str(tmp_path / "backups"),
        )
        assert pb.list_backups() == []


# ---------------------------------------------------------------------------
# Smoke 9: Structured logger
# ---------------------------------------------------------------------------


class TestStructuredLoggerSmoke:
    """get_structured_logger() returns a usable logger."""

    def test_get_structured_logger_returns_instance(self):
        from fda_tools.lib.logger import StructuredLogger, get_structured_logger

        logger = get_structured_logger("smoke.test")
        assert isinstance(logger, StructuredLogger)

    def test_logger_info_does_not_raise(self):
        from fda_tools.lib.logger import get_structured_logger

        logger = get_structured_logger("smoke.test.info")
        logger.info("smoke test message")  # must not raise


# ---------------------------------------------------------------------------
# Smoke 10: Bulk lib module import
# ---------------------------------------------------------------------------


class TestBulkLibImportSmoke:
    """All public lib modules are importable without side-effect errors."""

    CRITICAL_MODULES = [
        "fda_tools.lib.config",
        "fda_tools.lib.cache_manager",
        "fda_tools.lib.cross_process_rate_limiter",
        "fda_tools.lib.quota_tracker",
        "fda_tools.lib.user_errors",
        "fda_tools.lib.project_backup",
        "fda_tools.lib.logger",
        "fda_tools.lib.logging_config",
        "fda_tools.lib.auth",
        "fda_tools.lib.path_validator",
        "fda_tools.lib.subprocess_helpers",
        "fda_tools.lib.combination_detector",
        "fda_tools.bridge.server",
    ]

    def test_all_critical_modules_importable(self):
        """Every module in CRITICAL_MODULES must import without exception."""
        failed: list[str] = []
        for mod_name in self.CRITICAL_MODULES:
            try:
                importlib.import_module(mod_name)
            except Exception as exc:
                failed.append(f"{mod_name}: {exc}")

        assert not failed, "Critical module(s) failed to import:\n" + "\n".join(failed)
