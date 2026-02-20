#!/usr/bin/env python3
"""
Test Suite for Production Monitoring and Observability (FDA-190).

Tests:
- Metrics collection and exposition
- Health checks
- Structured logging
- Alert triggering
- SLO compliance tracking
"""

import json
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:

from fda_tools.lib.monitoring import (
    MetricsCollector,
    HealthChecker,
    Counter,
    Gauge,
    Histogram,
    get_metrics_collector,
    get_health_checker,
)
from fda_tools.lib.logger import (
    StructuredLogger,
    StructuredJSONFormatter,
    SamplingFilter,
    get_structured_logger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    redact_sensitive_data,
)


# ---------------------------------------------------------------------------
# Metrics Collection Tests
# ---------------------------------------------------------------------------

class TestMetricsCollector(unittest.TestCase):
    """Test metrics collection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics = MetricsCollector()

    def tearDown(self):
        """Clean up after tests."""
        self.metrics.shutdown()

    def test_counter_increment(self):
        """Test counter increment."""
        counter = self.metrics.register_counter("test_counter", "Test counter")

        counter.inc(1.0)
        self.assertEqual(counter.get(), 1.0)

        counter.inc(2.5)
        self.assertEqual(counter.get(), 3.5)

    def test_counter_with_labels(self):
        """Test counter with labels."""
        counter = self.metrics.register_counter("test_counter_labels", "Test counter with labels")

        counter.inc(1.0, labels={"method": "GET", "endpoint": "/api"})
        counter.inc(2.0, labels={"method": "POST", "endpoint": "/api"})

        self.assertEqual(counter.get(labels={"method": "GET", "endpoint": "/api"}), 1.0)
        self.assertEqual(counter.get(labels={"method": "POST", "endpoint": "/api"}), 2.0)

    def test_gauge_set_and_increment(self):
        """Test gauge set and increment operations."""
        gauge = self.metrics.register_gauge("test_gauge", "Test gauge")

        gauge.set(10.0)
        self.assertEqual(gauge.get(), 10.0)

        gauge.inc(5.0)
        self.assertEqual(gauge.get(), 15.0)

        gauge.dec(3.0)
        self.assertEqual(gauge.get(), 12.0)

    def test_histogram_observations(self):
        """Test histogram observations and percentiles."""
        histogram = self.metrics.register_histogram("test_histogram", "Test histogram")

        # Record observations
        for value in [0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 5.0]:
            histogram.observe(value)

        # Check statistics
        self.assertEqual(histogram.get_count(), 8)
        self.assertAlmostEqual(histogram.get_sum(), 10.6, places=1)
        self.assertAlmostEqual(histogram.get_avg(), 1.325, places=2)

        # Check percentiles
        p50 = histogram.get_percentile(50)
        self.assertGreater(p50, 0.3)
        self.assertLessEqual(p50, 1.0)  # Allow p50 to equal 1.0 with 8 samples

        p95 = histogram.get_percentile(95)
        self.assertGreaterEqual(p95, 1.5)  # With 8 samples, p95 could equal 1.5

    def test_track_request_context_manager(self):
        """Test track_request context manager."""
        endpoint = "test_endpoint"

        with self.metrics.track_request(endpoint):
            time.sleep(0.01)  # Simulate work

        # Check that metrics were recorded
        total_requests = self.metrics._counters["fda_requests_total"].get(
            labels={"endpoint": endpoint}
        )
        self.assertEqual(total_requests, 1.0)

        # Check that duration was recorded
        histogram = self.metrics._histograms["fda_request_duration_seconds"]
        self.assertGreater(histogram.get_count(labels={"endpoint": endpoint}), 0)

    def test_track_request_with_error(self):
        """Test track_request with exception."""
        endpoint = "test_error_endpoint"

        with self.assertRaises(ValueError):
            with self.metrics.track_request(endpoint):
                raise ValueError("Test error")

        # Check that error was recorded
        error_count = self.metrics._counters["fda_requests_errors_total"].get(
            labels={"endpoint": endpoint}
        )
        self.assertEqual(error_count, 1.0)

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        cache_name = "test_cache"

        # Record hits and misses
        for _ in range(8):
            self.metrics.track_cache_access(hit=True, cache_name=cache_name)
        for _ in range(2):
            self.metrics.track_cache_access(hit=False, cache_name=cache_name)

        # Calculate hit rate
        hit_rate = self.metrics.get_cache_hit_rate(cache_name)
        self.assertAlmostEqual(hit_rate, 80.0, places=1)

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        endpoint = "test_error_rate"

        # Simulate requests
        for _ in range(90):
            with self.metrics.track_request(endpoint):
                pass

        # Simulate errors
        for _ in range(10):
            try:
                with self.metrics.track_request(endpoint):
                    raise RuntimeError("Error")
            except RuntimeError:
                pass

        # Calculate error rate
        error_rate = self.metrics.get_error_rate(endpoint)
        self.assertAlmostEqual(error_rate, 10.0, places=0)

    def test_prometheus_export_format(self):
        """Test Prometheus export format."""
        # Record some metrics
        self.metrics.increment_counter("fda_requests_total", 10.0, labels={"endpoint": "test"})
        self.metrics.set_gauge("fda_cpu_usage_percent", 45.5)

        # Export
        output = self.metrics.export_prometheus()

        # Verify format
        self.assertIn("# HELP fda_requests_total", output)
        self.assertIn("# TYPE fda_requests_total counter", output)
        self.assertIn("fda_cpu_usage_percent 45.5", output)

    def test_slo_compliance(self):
        """Test SLO compliance calculation."""
        # Record metrics that meet SLOs
        endpoint = "test_slo"

        for _ in range(100):
            with self.metrics.track_request(endpoint):
                time.sleep(0.001)  # Very fast requests

        # Only 1 error out of 100 = 1% error rate (meets SLO)
        try:
            with self.metrics.track_request(endpoint):
                raise ValueError("Error")
        except ValueError:
            pass

        # Track cache hits
        for _ in range(85):
            self.metrics.track_cache_access(hit=True)
        for _ in range(15):
            self.metrics.track_cache_access(hit=False)

        # Check SLO compliance
        compliance = self.metrics.get_slo_compliance()

        self.assertTrue(compliance["error_rate_percent"]["compliant"])
        self.assertTrue(compliance["cache_hit_rate_percent"]["compliant"])

    def test_thread_safety(self):
        """Test thread-safe metric updates."""
        counter = self.metrics.register_counter("thread_test_counter", "Thread test")

        def increment_counter():
            for _ in range(100):
                counter.inc(1.0)

        # Start multiple threads
        threads = [threading.Thread(target=increment_counter) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify count
        self.assertEqual(counter.get(), 1000.0)


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------

class TestHealthChecker(unittest.TestCase):
    """Test health check functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.health = HealthChecker()

    def test_basic_health_check(self):
        """Test basic health check."""
        result = self.health.check()

        self.assertIn(result.status, ["healthy", "degraded", "unhealthy"])
        self.assertIn("cpu", result.checks)
        self.assertIn("memory", result.checks)
        self.assertIn("disk", result.checks)
        self.assertIn("process", result.checks)

    def test_health_check_result_to_dict(self):
        """Test health check result serialization."""
        result = self.health.check()
        result_dict = result.to_dict()

        self.assertIn("status", result_dict)
        self.assertIn("timestamp", result_dict)
        self.assertIn("checks", result_dict)

    def test_readiness_check(self):
        """Test readiness check."""
        result = self.health.check_readiness()

        self.assertIsNotNone(result.status)
        self.assertIn("cpu", result.checks)

    def test_custom_health_check(self):
        """Test registering custom health check."""
        def custom_check():
            return True, "Custom check passed", {"detail": "ok"}

        self.health.register_check("custom", custom_check)
        result = self.health.check()

        self.assertIn("custom", result.checks)
        self.assertTrue(result.checks["custom"]["healthy"])
        self.assertEqual(result.checks["custom"]["message"], "Custom check passed")

    def test_failing_health_check(self):
        """Test health check with failure."""
        def failing_check():
            return False, "Check failed", {"error": "Something wrong"}

        self.health.register_check("failing", failing_check)
        result = self.health.check()

        self.assertIn("failing", result.checks)
        self.assertFalse(result.checks["failing"]["healthy"])


# ---------------------------------------------------------------------------
# Structured Logging Tests
# ---------------------------------------------------------------------------

class TestStructuredLogging(unittest.TestCase):
    """Test structured logging functionality."""

    def setUp(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def tearDown(self):
        """Clear correlation ID after each test."""
        clear_correlation_id()

    def test_correlation_id(self):
        """Test correlation ID management."""
        # Initially no correlation ID (after setUp clear)
        self.assertIsNone(get_correlation_id())

        # Set correlation ID
        corr_id = set_correlation_id("test-123")
        self.assertEqual(corr_id, "test-123")
        self.assertEqual(get_correlation_id(), "test-123")

        # Clear correlation ID
        clear_correlation_id()
        self.assertIsNone(get_correlation_id())

    def test_auto_generate_correlation_id(self):
        """Test auto-generation of correlation ID."""
        corr_id = set_correlation_id()

        self.assertIsNotNone(corr_id)
        self.assertTrue(corr_id.startswith("req-"))
        self.assertEqual(get_correlation_id(), corr_id)

    def test_redact_sensitive_keys(self):
        """Test redaction of sensitive data by key name."""
        data = {
            "username": "john_doe",
            "api_key": "secret-key-12345",
            "password": "my-password",
            "email": "user@example.com",
            "device_code": "OVE",
        }

        redacted = redact_sensitive_data(data, redact_keys=True)

        self.assertEqual(redacted["username"], "john_doe")
        self.assertEqual(redacted["device_code"], "OVE")
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["password"], "[REDACTED]")
        self.assertEqual(redacted["email"], "[REDACTED]")

    def test_redact_sensitive_patterns(self):
        """Test redaction of sensitive patterns in strings."""
        data = "User SSN is 123-45-6789 and email is john@example.com"

        redacted = redact_sensitive_data(data, redact_keys=False)

        self.assertNotIn("123-45-6789", redacted)
        self.assertIn("[REDACTED-SSN]", redacted)
        self.assertIn("@example.com", redacted)  # Domain preserved
        self.assertNotIn("john@", redacted)  # Username redacted

    def test_json_formatter(self):
        """Test JSON structured formatter."""
        formatter = StructuredJSONFormatter(redact_sensitive=False)

        # Create log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, __file__, 1,
            "Test message", (), None
        )

        # Format record
        output = formatter.format(record)
        parsed = json.loads(output)

        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["logger"], "test")
        self.assertEqual(parsed["message"], "Test message")
        self.assertIn("timestamp", parsed)

    def test_json_formatter_with_correlation_id(self):
        """Test JSON formatter includes correlation ID."""
        formatter = StructuredJSONFormatter(redact_sensitive=False)

        set_correlation_id("test-correlation-123")

        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, __file__, 1,
            "Test message", (), None
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        self.assertEqual(parsed["correlation_id"], "test-correlation-123")

        clear_correlation_id()

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception info."""
        formatter = StructuredJSONFormatter(redact_sensitive=False)

        logger = logging.getLogger("test")

        try:
            raise ValueError("Test error")
        except ValueError:
            record = logger.makeRecord(
                "test", logging.ERROR, __file__, 1,
                "Error occurred", (), sys.exc_info()
            )

        output = formatter.format(record)
        parsed = json.loads(output)

        self.assertIn("exception", parsed)
        self.assertEqual(parsed["exception"]["type"], "ValueError")
        self.assertIn("Test error", parsed["exception"]["message"])

    def test_structured_logger_convenience_methods(self):
        """Test structured logger convenience methods."""
        logger = get_structured_logger("test")

        # Mock the underlying logger
        logger._logger = Mock()

        # Test API call logging
        logger.log_api_call("test_endpoint", method="POST", status_code=200, duration_ms=123.4)
        logger._logger.log.assert_called()

        # Test database query logging
        logger.log_database_query("select_users", duration_ms=45.6, row_count=10)
        logger._logger.log.assert_called()

        # Test cache access logging
        logger.log_cache_access("redis", hit=True, key="test_key")
        logger._logger.log.assert_called()

    def test_sampling_filter(self):
        """Test log sampling filter."""
        # Sample 50% of logs
        sampling_filter = SamplingFilter(sample_rate=0.5)

        passed = 0
        total = 100

        for _ in range(total):
            record = logging.LogRecord(
                "test", logging.INFO, __file__, 1,
                "Test", (), None
            )
            if sampling_filter.filter(record):
                passed += 1

        # Should be approximately 50% (with some variance)
        self.assertGreater(passed, 35)
        self.assertLess(passed, 65)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestMonitoringIntegration(unittest.TestCase):
    """Test integration between monitoring components."""

    def test_metrics_and_health_integration(self):
        """Test that metrics collector integrates with health checker."""
        metrics = MetricsCollector()
        health = HealthChecker(metrics_collector=metrics)

        # Record some metrics
        with metrics.track_request("test"):
            time.sleep(0.01)

        # Check health
        result = health.check()

        self.assertIsNotNone(result.status)
        metrics.shutdown()

    def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        # Initialize monitoring
        metrics = get_metrics_collector()
        health = get_health_checker()
        logger = get_structured_logger("test")

        # Set correlation ID
        set_correlation_id("integration-test")

        # Simulate API request with monitoring
        endpoint = "integration_test_endpoint"

        with metrics.track_request(endpoint):
            logger.info("Processing request", extra={"endpoint": endpoint})
            time.sleep(0.01)

        # Check metrics
        request_count = metrics._counters["fda_requests_total"].get(
            labels={"endpoint": endpoint}
        )
        self.assertGreater(request_count, 0)

        # Check health
        health_result = health.check()
        self.assertIsNotNone(health_result.status)

        # Export Prometheus metrics
        prom_output = metrics.export_prometheus()
        self.assertIn("fda_requests_total", prom_output)

        clear_correlation_id()


# ---------------------------------------------------------------------------
# Run Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
