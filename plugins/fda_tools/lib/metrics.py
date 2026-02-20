#!/usr/bin/env python3
"""
Metrics Collection and Reporting Module for FDA Tools.

Provides high-level metrics tracking and reporting capabilities including:
- Business metrics (510k submissions tracked, predicates analyzed, etc.)
- Performance metrics (API latency, throughput, cache efficiency)
- SLO/SLI tracking and alerting
- Custom metric definitions
- Metrics aggregation and reporting

Built on top of lib/monitoring.py for low-level metric collection.

Usage:
from fda_tools.lib.metrics import get_metrics_reporter, track_business_metric

    # Track business metrics
    track_business_metric("510k_submissions_analyzed", value=1,
                          labels={"product_code": "DQY"})

    # Generate SLO compliance report
    reporter = get_metrics_reporter()
    slo_report = reporter.generate_slo_report()

    # Export metrics for dashboards
    metrics_json = reporter.export_metrics_json()
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .monitoring import get_metrics_collector, MetricsCollector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Business metric definitions
BUSINESS_METRICS = {
    "510k_submissions_analyzed": "Number of 510(k) submissions analyzed",
    "predicates_identified": "Number of predicates identified",
    "standards_mapped": "Number of standards mapped to devices",
    "regulatory_gaps_detected": "Number of regulatory gaps detected",
    "reports_generated": "Number of reports generated",
    "api_calls_openfda": "Number of OpenFDA API calls made",
    "cache_savings_hours": "Estimated hours saved through caching",
}

# SLI definitions (Service Level Indicators)
SLI_DEFINITIONS = {
    "availability": {
        "name": "Service Availability",
        "target": 99.9,  # 99.9% uptime
        "unit": "percent",
        "description": "Percentage of time service is available",
    },
    "api_latency_p95": {
        "name": "API Latency (P95)",
        "target": 500,  # 500ms
        "unit": "milliseconds",
        "description": "95th percentile API response time",
    },
    "api_latency_p99": {
        "name": "API Latency (P99)",
        "target": 1000,  # 1000ms
        "unit": "milliseconds",
        "description": "99th percentile API response time",
    },
    "error_rate": {
        "name": "Error Rate",
        "target": 1.0,  # 1% max error rate
        "unit": "percent",
        "description": "Percentage of requests that result in errors",
    },
    "cache_hit_rate": {
        "name": "Cache Hit Rate",
        "target": 80.0,  # 80% minimum
        "unit": "percent",
        "description": "Percentage of requests served from cache",
    },
}

# Alert thresholds
ALERT_THRESHOLDS = {
    "cpu_percent": {"warning": 80, "critical": 95},
    "memory_percent": {"warning": 75, "critical": 90},
    "disk_percent": {"warning": 85, "critical": 95},
    "error_rate_percent": {"warning": 2.0, "critical": 5.0},
    "latency_p95_ms": {"warning": 750, "critical": 1500},
    "cache_hit_rate_percent": {"warning": 70, "critical": 50},
}


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: datetime
    business_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    sli_metrics: Dict[str, float]
    resource_metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "business_metrics": self.business_metrics,
            "performance_metrics": self.performance_metrics,
            "sli_metrics": self.sli_metrics,
            "resource_metrics": self.resource_metrics,
        }


@dataclass
class SLOViolation:
    """Record of an SLO violation."""
    timestamp: datetime
    sli_name: str
    actual_value: float
    target_value: float
    severity: str  # "warning" or "critical"
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "sli_name": self.sli_name,
            "actual_value": self.actual_value,
            "target_value": self.target_value,
            "severity": self.severity,
            "duration_seconds": self.duration_seconds,
        }


# ---------------------------------------------------------------------------
# Metrics Reporter
# ---------------------------------------------------------------------------

class MetricsReporter:
    """High-level metrics reporting and SLO tracking.

    Aggregates metrics from MetricsCollector and provides business-focused
    reporting, SLO compliance tracking, and alerting capabilities.
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize metrics reporter.

        Args:
            metrics_collector: Optional MetricsCollector instance
        """
        self.collector = metrics_collector or get_metrics_collector()

        # Business metrics tracking
        self._business_counters: Dict[str, float] = defaultdict(float)
        self._business_lock = threading.Lock()

        # SLO violation tracking
        self._slo_violations: deque = deque(maxlen=1000)  # Keep last 1000 violations
        self._violation_lock = threading.Lock()

        # Snapshot history (for trend analysis)
        self._snapshot_history: deque = deque(maxlen=288)  # 24 hours at 5-min intervals
        self._snapshot_lock = threading.Lock()

        # Alert state tracking
        self._active_alerts: Dict[str, datetime] = {}
        self._alert_lock = threading.Lock()

        # Start background SLO monitoring
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_slos, daemon=True)
        self._monitor_thread.start()

        logger.info("MetricsReporter initialized")

    def track_business_metric(self, metric_name: str, value: float = 1.0,
                             labels: Optional[Dict[str, str]] = None) -> None:
        """Track a business metric.

        Args:
            metric_name: Name of the metric to track
            value: Metric value (default 1.0 for counters)
            labels: Optional labels for metric segmentation
        """
        with self._business_lock:
            key = metric_name
            if labels:
                label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
                key = f"{metric_name}:{label_str}"

            self._business_counters[key] += value

        # Also track in underlying metrics collector
        counter_name = f"fda_business_{metric_name}"
        if counter_name not in self.collector._counters:
            self.collector.register_counter(counter_name, BUSINESS_METRICS.get(metric_name, metric_name))

        self.collector.increment_counter(counter_name, value, labels)

    def get_business_metrics(self) -> Dict[str, float]:
        """Get current business metrics.

        Returns:
            Dictionary of business metric names and values
        """
        with self._business_lock:
            return dict(self._business_counters)

    def get_sli_values(self) -> Dict[str, float]:
        """Get current SLI values.

        Returns:
            Dictionary of SLI names and current values
        """
        sli_values = {}

        # Availability (based on error rate and health checks)
        error_rate = self.collector.get_error_rate()
        sli_values["availability"] = max(0, 100 - error_rate)

        # API latency percentiles
        percentiles = self.collector.get_latency_percentiles()
        sli_values["api_latency_p95"] = percentiles["p95"]
        sli_values["api_latency_p99"] = percentiles["p99"]

        # Error rate
        sli_values["error_rate"] = error_rate

        # Cache hit rate
        sli_values["cache_hit_rate"] = self.collector.get_cache_hit_rate()

        return sli_values

    def check_slo_compliance(self) -> Dict[str, Any]:
        """Check SLO compliance for all SLIs.

        Returns:
            Dictionary with compliance status for each SLI
        """
        sli_values = self.get_sli_values()
        compliance_report = {}

        for sli_name, definition in SLI_DEFINITIONS.items():
            actual_value = sli_values.get(sli_name, 0)
            target = definition["target"]

            # Determine compliance (some SLIs are "higher is better", some are "lower is better")
            if sli_name in ("availability", "cache_hit_rate"):
                compliant = actual_value >= target
                budget_remaining = actual_value - target
            else:
                compliant = actual_value <= target
                budget_remaining = target - actual_value

            compliance_report[sli_name] = {
                "name": definition["name"],
                "actual_value": actual_value,
                "target": target,
                "unit": definition["unit"],
                "compliant": compliant,
                "budget_remaining": budget_remaining,
                "budget_remaining_percent": (budget_remaining / target * 100) if target > 0 else 0,
            }

            # Track violations
            if not compliant:
                self._record_slo_violation(sli_name, actual_value, target)

        return compliance_report

    def _record_slo_violation(self, sli_name: str, actual_value: float,
                             target_value: float) -> None:
        """Record an SLO violation.

        Args:
            sli_name: Name of the SLI that violated SLO
            actual_value: Actual measured value
            target_value: Target SLO value
        """
        # Determine severity based on how far off target we are
        deviation_percent = abs((actual_value - target_value) / target_value * 100)
        severity = "critical" if deviation_percent > 50 else "warning"

        violation = SLOViolation(
            timestamp=datetime.now(timezone.utc),
            sli_name=sli_name,
            actual_value=actual_value,
            target_value=target_value,
            severity=severity,
        )

        with self._violation_lock:
            self._slo_violations.append(violation)

        logger.warning(
            "SLO violation: %s - actual: %.2f, target: %.2f, severity: %s",
            sli_name, actual_value, target_value, severity
        )

    def get_slo_violations(self, since: Optional[datetime] = None) -> List[SLOViolation]:
        """Get SLO violations since a given time.

        Args:
            since: Optional datetime to filter violations (default: all)

        Returns:
            List of SLOViolation objects
        """
        with self._violation_lock:
            if since:
                return [v for v in self._slo_violations if v.timestamp >= since]
            return list(self._slo_violations)

    def take_snapshot(self) -> MetricSnapshot:
        """Take a snapshot of current metrics.

        Returns:
            MetricSnapshot with current metric values
        """
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc),
            business_metrics=self.get_business_metrics(),
            performance_metrics={
                "requests_total": self.collector._counters["fda_requests_total"].value,
                "errors_total": self.collector._counters["fda_requests_errors_total"].value,
                "cache_hits_total": self.collector._counters["fda_cache_hits_total"].value,
                "cache_misses_total": self.collector._counters["fda_cache_misses_total"].value,
            },
            sli_metrics=self.get_sli_values(),
            resource_metrics={
                "cpu_percent": self.collector._gauges["fda_cpu_usage_percent"].value,
                "memory_percent": self.collector._gauges["fda_memory_usage_percent"].value,
                "disk_percent": self.collector._gauges.get("fda_disk_usage_percent", type("G", (), {"value": 0})).value,
            },
        )

        # Store in history
        with self._snapshot_lock:
            self._snapshot_history.append(snapshot)

        return snapshot

    def get_snapshot_history(self, duration_minutes: int = 60) -> List[MetricSnapshot]:
        """Get snapshot history for the specified duration.

        Args:
            duration_minutes: Number of minutes of history to return

        Returns:
            List of MetricSnapshot objects
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)

        with self._snapshot_lock:
            return [s for s in self._snapshot_history if s.timestamp >= cutoff]

    def generate_slo_report(self) -> Dict[str, Any]:
        """Generate comprehensive SLO compliance report.

        Returns:
            Dictionary with SLO report data
        """
        compliance = self.check_slo_compliance()

        # Calculate overall compliance
        total_slis = len(compliance)
        compliant_slis = sum(1 for sli in compliance.values() if sli["compliant"])
        overall_compliance_percent = (compliant_slis / total_slis * 100) if total_slis > 0 else 0

        # Get recent violations
        recent_violations = self.get_slo_violations(
            since=datetime.now(timezone.utc) - timedelta(hours=24)
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_compliance_percent": overall_compliance_percent,
            "compliant_slis": compliant_slis,
            "total_slis": total_slis,
            "sli_compliance": compliance,
            "recent_violations_24h": len(recent_violations),
            "violations": [v.to_dict() for v in recent_violations[-10:]],  # Last 10
        }

    def export_metrics_json(self) -> str:
        """Export all metrics as JSON for dashboards.

        Returns:
            JSON string with all metrics
        """
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_metrics": self.get_business_metrics(),
            "sli_values": self.get_sli_values(),
            "slo_compliance": self.check_slo_compliance(),
            "performance": {
                "latency_percentiles": self.collector.get_latency_percentiles(),
                "error_rate": self.collector.get_error_rate(),
                "cache_hit_rate": self.collector.get_cache_hit_rate(),
            },
            "resource_usage": {
                "cpu_percent": self.collector._gauges["fda_cpu_usage_percent"].value,
                "memory_percent": self.collector._gauges["fda_memory_usage_percent"].value,
                "memory_bytes": self.collector._gauges["fda_memory_usage_bytes"].value,
            },
        }

        return json.dumps(data, indent=2, default=str)

    def _monitor_slos(self) -> None:
        """Background thread to monitor SLOs and take periodic snapshots."""
        while self._monitoring:
            try:
                # Check SLO compliance
                self.check_slo_compliance()

                # Take snapshot every 5 minutes
                self.take_snapshot()

                # Sleep for 5 minutes
                time.sleep(300)

            except Exception as e:
                logger.error("Error in SLO monitoring: %s", e)
                time.sleep(300)

    def shutdown(self) -> None:
        """Shutdown the metrics reporter."""
        self._monitoring = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("MetricsReporter shut down")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_metrics_reporter: Optional[MetricsReporter] = None


def get_metrics_reporter() -> MetricsReporter:
    """Get the singleton metrics reporter instance."""
    global _metrics_reporter
    if _metrics_reporter is None:
        _metrics_reporter = MetricsReporter()
    return _metrics_reporter


def track_business_metric(metric_name: str, value: float = 1.0,
                         labels: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to track a business metric.

    Args:
        metric_name: Name of the metric
        value: Metric value
        labels: Optional labels
    """
    reporter = get_metrics_reporter()
    reporter.track_business_metric(metric_name, value, labels)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "MetricsReporter",
    "MetricSnapshot",
    "SLOViolation",
    "get_metrics_reporter",
    "track_business_metric",
    "BUSINESS_METRICS",
    "SLI_DEFINITIONS",
    "ALERT_THRESHOLDS",
]
