#!/usr/bin/env python3
"""
Integration tests for monitoring and observability infrastructure.

Tests the monitoring stack including:
- Metrics collection and export
- Health checks
- SLO tracking
- Alert thresholds

Usage:
    pytest tests/test_monitoring_integration.py -v
"""

import pytest
import time
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Test Metrics Collection
# ---------------------------------------------------------------------------

def test_metrics_collector_initialization():
    """Test that metrics collector initializes correctly."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Verify core metrics are registered
    assert "fda_requests_total" in metrics._counters
    assert "fda_request_duration_seconds" in metrics._histograms
    assert "fda_cpu_usage_percent" in metrics._gauges
    assert "fda_memory_usage_percent" in metrics._gauges


def test_counter_tracking():
    """Test counter metric tracking."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Reset counter
    initial_value = metrics._counters["fda_requests_total"].value

    # Increment counter
    metrics.increment_counter("fda_requests_total", amount=5.0)

    # Verify increment
    new_value = metrics._counters["fda_requests_total"].value
    assert new_value == initial_value + 5.0


def test_counter_with_labels():
    """Test counter with labels."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Increment with labels
    metrics.increment_counter("fda_requests_total",
                            labels={"endpoint": "test", "method": "GET"})

    # Verify labeled value
    value = metrics._counters["fda_requests_total"].get(
        labels={"endpoint": "test", "method": "GET"}
    )
    assert value > 0


def test_histogram_tracking():
    """Test histogram metric tracking."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Record observations
    metrics.record_histogram("fda_request_duration_seconds", 0.1)
    metrics.record_histogram("fda_request_duration_seconds", 0.5)
    metrics.record_histogram("fda_request_duration_seconds", 1.0)

    # Get histogram
    histogram = metrics._histograms["fda_request_duration_seconds"]

    # Verify count
    assert histogram.get_count() >= 3

    # Verify percentiles
    p50 = histogram.get_percentile(50)
    assert p50 > 0


def test_request_tracking_context_manager():
    """Test request tracking context manager."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Get count with labels
    initial_count = metrics._counters["fda_requests_total"].get(
        labels={"endpoint": "test_endpoint"}
    )

    # Track request
    with metrics.track_request("test_endpoint"):
        time.sleep(0.01)  # Simulate work

    # Verify counter incremented with labels
    new_count = metrics._counters["fda_requests_total"].get(
        labels={"endpoint": "test_endpoint"}
    )
    assert new_count > initial_count


def test_cache_tracking():
    """Test cache hit/miss tracking."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Track cache access
    metrics.track_cache_access(hit=True, cache_name="test")
    metrics.track_cache_access(hit=True, cache_name="test")
    metrics.track_cache_access(hit=False, cache_name="test")

    # Calculate hit rate
    hit_rate = metrics.get_cache_hit_rate(cache_name="test")
    assert 60 < hit_rate < 70  # 2/3 = 66.67%


def test_prometheus_export():
    """Test Prometheus format export."""
from fda_tools.lib.monitoring import get_metrics_collector

    metrics = get_metrics_collector()

    # Export metrics
    prometheus_text = metrics.export_prometheus()

    # Verify format
    assert "# HELP fda_requests_total" in prometheus_text
    assert "# TYPE fda_requests_total counter" in prometheus_text
    assert "fda_requests_total" in prometheus_text


# ---------------------------------------------------------------------------
# Test Metrics Reporter
# ---------------------------------------------------------------------------

def test_metrics_reporter_initialization():
    """Test that metrics reporter initializes correctly."""
from fda_tools.lib.metrics import get_metrics_reporter

    reporter = get_metrics_reporter()

    # Verify business metrics tracking
    assert reporter._business_counters is not None


def test_business_metric_tracking():
    """Test business metric tracking."""
from fda_tools.lib.metrics import track_business_metric

    # Track business metric
    track_business_metric("510k_submissions_analyzed", value=1,
                         labels={"product_code": "DQY"})

    track_business_metric("predicates_identified", value=5)

    # Verify tracking
from fda_tools.lib.metrics import get_metrics_reporter
    reporter = get_metrics_reporter()
    metrics = reporter.get_business_metrics()

    assert "510k_submissions_analyzed:product_code=DQY" in metrics
    assert "predicates_identified" in metrics


def test_sli_values():
    """Test SLI value calculation."""
from fda_tools.lib.metrics import get_metrics_reporter

    reporter = get_metrics_reporter()

    # Get SLI values
    sli_values = reporter.get_sli_values()

    # Verify SLIs exist
    assert "availability" in sli_values
    assert "api_latency_p95" in sli_values
    assert "api_latency_p99" in sli_values
    assert "error_rate" in sli_values
    assert "cache_hit_rate" in sli_values


def test_slo_compliance_check():
    """Test SLO compliance checking."""
from fda_tools.lib.metrics import get_metrics_reporter

    reporter = get_metrics_reporter()

    # Check compliance
    compliance = reporter.check_slo_compliance()

    # Verify structure
    assert "availability" in compliance
    assert "api_latency_p95" in compliance

    # Verify compliance fields
    for sli_name, status in compliance.items():
        assert "actual_value" in status
        assert "target" in status
        assert "compliant" in status
        assert "budget_remaining" in status


def test_metric_snapshot():
    """Test metric snapshot functionality."""
from fda_tools.lib.metrics import get_metrics_reporter

    reporter = get_metrics_reporter()

    # Take snapshot
    snapshot = reporter.take_snapshot()

    # Verify snapshot structure
    assert snapshot.timestamp is not None
    assert snapshot.business_metrics is not None
    assert snapshot.performance_metrics is not None
    assert snapshot.sli_metrics is not None
    assert snapshot.resource_metrics is not None


def test_json_export():
    """Test JSON metrics export."""
from fda_tools.lib.metrics import get_metrics_reporter
    import json

    reporter = get_metrics_reporter()

    # Export as JSON
    metrics_json = reporter.export_metrics_json()

    # Verify valid JSON
    data = json.loads(metrics_json)
    assert "timestamp" in data
    assert "business_metrics" in data
    assert "sli_values" in data
    assert "performance" in data


# ---------------------------------------------------------------------------
# Test Health Checks
# ---------------------------------------------------------------------------

def test_health_checker_initialization():
    """Test health checker initialization."""
from fda_tools.lib.monitoring import get_health_checker

    health = get_health_checker()

    # Verify checks registered
    assert health._checks is not None
    assert "cpu" in health._checks
    assert "memory" in health._checks
    assert "disk" in health._checks


def test_health_check_execution():
    """Test health check execution."""
from fda_tools.lib.monitoring import get_health_checker

    health = get_health_checker()

    # Run health check
    result = health.check()

    # Verify result structure
    assert result.status in ("healthy", "degraded", "unhealthy")
    assert result.checks is not None
    assert result.timestamp is not None

    # Verify individual checks
    assert "cpu" in result.checks
    assert "memory" in result.checks
    assert "process" in result.checks


def test_readiness_check():
    """Test readiness probe."""
from fda_tools.lib.monitoring import get_health_checker

    health = get_health_checker()

    # Run readiness check
    result = health.check_readiness()

    # Verify result
    assert result.status in ("healthy", "degraded", "unhealthy")


def test_health_check_result_to_dict():
    """Test health check result serialization."""
from fda_tools.lib.monitoring import get_health_checker

    health = get_health_checker()
    result = health.check()

    # Convert to dict
    result_dict = result.to_dict()

    # Verify structure
    assert "status" in result_dict
    assert "timestamp" in result_dict
    assert "checks" in result_dict


# ---------------------------------------------------------------------------
# Test SLO Tracking
# ---------------------------------------------------------------------------

def test_slo_definitions():
    """Test SLO definitions are properly configured."""
from fda_tools.lib.metrics import SLI_DEFINITIONS

    # Verify all expected SLIs are defined
    assert "availability" in SLI_DEFINITIONS
    assert "api_latency_p95" in SLI_DEFINITIONS
    assert "api_latency_p99" in SLI_DEFINITIONS
    assert "error_rate" in SLI_DEFINITIONS
    assert "cache_hit_rate" in SLI_DEFINITIONS

    # Verify structure
    for sli_name, definition in SLI_DEFINITIONS.items():
        assert "name" in definition
        assert "target" in definition
        assert "unit" in definition
        assert "description" in definition


def test_slo_violation_recording():
    """Test SLO violation recording."""
from fda_tools.lib.metrics import get_metrics_reporter

    reporter = get_metrics_reporter()

    initial_violations = len(reporter._slo_violations)

    # Record violation
    reporter._record_slo_violation("test_sli", 50.0, 99.9)

    # Verify recorded
    violations = reporter.get_slo_violations()
    assert len(violations) > initial_violations


# ---------------------------------------------------------------------------
# Test Alert Thresholds
# ---------------------------------------------------------------------------

def test_alert_thresholds_configured():
    """Test alert thresholds are properly configured."""
from fda_tools.lib.metrics import ALERT_THRESHOLDS

    # Verify thresholds exist
    assert "cpu_percent" in ALERT_THRESHOLDS
    assert "memory_percent" in ALERT_THRESHOLDS
    assert "error_rate_percent" in ALERT_THRESHOLDS

    # Verify structure
    for metric, thresholds in ALERT_THRESHOLDS.items():
        assert "warning" in thresholds
        assert "critical" in thresholds
        # Critical should be higher than warning (for usage metrics)
        if "rate" not in metric:  # For usage metrics
            assert thresholds["critical"] >= thresholds["warning"]


# ---------------------------------------------------------------------------
# Test Integration
# ---------------------------------------------------------------------------

def test_end_to_end_monitoring_flow():
    """Test complete monitoring flow."""
from fda_tools.lib.monitoring import get_metrics_collector
from fda_tools.lib.metrics import get_metrics_reporter, track_business_metric

    metrics = get_metrics_collector()
    reporter = get_metrics_reporter()

    # Simulate some application activity
    with metrics.track_request("e2e_test"):
        time.sleep(0.01)

    metrics.track_cache_access(hit=True)
    track_business_metric("test_metric", value=1)

    # Take snapshot
    snapshot = reporter.take_snapshot()

    # Export metrics
    prometheus_export = metrics.export_prometheus()
    json_export = reporter.export_metrics_json()

    # Check SLO compliance
    compliance = reporter.check_slo_compliance()

    # Verify all components working
    assert prometheus_export is not None
    assert json_export is not None
    assert compliance is not None
    assert snapshot is not None


def test_performance_overhead():
    """Test that monitoring has minimal performance overhead."""
from fda_tools.lib.monitoring import get_metrics_collector
    import time

    metrics = get_metrics_collector()

    # Measure overhead
    iterations = 1000
    start = time.time()

    for i in range(iterations):
        with metrics.track_request("perf_test"):
            pass  # No actual work

    duration = time.time() - start
    avg_overhead = (duration / iterations) * 1000  # ms per request

    # Overhead should be < 1ms per request
    assert avg_overhead < 1.0, f"Monitoring overhead too high: {avg_overhead:.2f}ms"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
