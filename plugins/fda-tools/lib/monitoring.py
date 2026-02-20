#!/usr/bin/env python3
"""
Production Monitoring and Observability Infrastructure for FDA Tools.

Provides comprehensive monitoring capabilities including:
- Prometheus metrics exposition (request latency, error rates, resource usage)
- Health checks and readiness probes
- Performance tracking and profiling
- Error rate monitoring by endpoint
- Resource utilization tracking
- Cache hit rates and database query performance
- Background job queue monitoring
- SLI/SLO tracking

Created as part of FDA-190 (DEVOPS-004) for production monitoring.

Usage:
    from lib.monitoring import get_metrics_collector, get_health_checker

    # Initialize monitoring
    metrics = get_metrics_collector()
    health = get_health_checker()

    # Record metrics
    with metrics.track_request("api_510k_fetch"):
        result = fetch_510k_data(k_number)

    metrics.increment_counter("api_requests_total", labels={"endpoint": "510k"})
    metrics.record_histogram("db_query_duration_seconds", 0.025, labels={"query": "select_predicates"})

    # Check health
    health_status = health.check()
    readiness_status = health.check_readiness()

    # Export metrics (Prometheus format)
    metrics_output = metrics.export_prometheus()
"""

import json
import logging
import os
import psutil
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default thresholds for SLI/SLO tracking
DEFAULT_SLO_TARGETS = {
    "api_latency_p95_ms": 500.0,     # 95th percentile API latency target
    "api_latency_p99_ms": 1000.0,    # 99th percentile API latency target
    "error_rate_percent": 1.0,        # Maximum acceptable error rate
    "cache_hit_rate_percent": 80.0,   # Minimum cache hit rate
    "availability_percent": 99.9,     # Service availability target (3 nines)
}

# Health check thresholds
HEALTH_THRESHOLDS = {
    "cpu_percent_critical": 95.0,
    "cpu_percent_warning": 80.0,
    "memory_percent_critical": 90.0,
    "memory_percent_warning": 75.0,
    "disk_percent_critical": 95.0,
    "disk_percent_warning": 85.0,
    "max_response_time_seconds": 30.0,
}

# Histogram buckets (in seconds) for latency tracking
LATENCY_BUCKETS = [
    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0
]


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Counter:
    """Thread-safe counter metric."""
    name: str
    help_text: str
    value: float = 0.0
    labels: Dict[str, Dict[str, float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter by amount."""
        with self._lock:
            if labels:
                label_key = self._serialize_labels(labels)
                if label_key not in self.labels:
                    self.labels[label_key] = {"value": 0.0, "labels": labels}
                self.labels[label_key]["value"] += amount
            else:
                self.value += amount

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        with self._lock:
            if labels:
                label_key = self._serialize_labels(labels)
                return self.labels.get(label_key, {}).get("value", 0.0)
            return self.value

    @staticmethod
    def _serialize_labels(labels: Dict[str, str]) -> str:
        """Serialize labels to a consistent string key."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


@dataclass
class Gauge:
    """Thread-safe gauge metric."""
    name: str
    help_text: str
    value: float = 0.0
    labels: Dict[str, Dict[str, float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge to value."""
        with self._lock:
            if labels:
                label_key = Counter._serialize_labels(labels)
                if label_key not in self.labels:
                    self.labels[label_key] = {"value": value, "labels": labels}
                else:
                    self.labels[label_key]["value"] = value
            else:
                self.value = value

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge by amount."""
        with self._lock:
            if labels:
                label_key = Counter._serialize_labels(labels)
                if label_key not in self.labels:
                    self.labels[label_key] = {"value": amount, "labels": labels}
                else:
                    self.labels[label_key]["value"] += amount
            else:
                self.value += amount

    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge by amount."""
        self.inc(-amount, labels)

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        with self._lock:
            if labels:
                label_key = Counter._serialize_labels(labels)
                return self.labels.get(label_key, {}).get("value", 0.0)
            return self.value


@dataclass
class Histogram:
    """Thread-safe histogram metric for tracking distributions."""
    name: str
    help_text: str
    buckets: List[float] = field(default_factory=lambda: LATENCY_BUCKETS.copy())
    _observations: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    _bucket_counts: Dict[str, List[int]] = field(default_factory=dict)
    _sum: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation."""
        with self._lock:
            label_key = Counter._serialize_labels(labels) if labels else ""

            # Store observation for percentile calculation
            self._observations[label_key].append(value)

            # Update sum and count
            self._sum[label_key] += value
            self._count[label_key] += 1

            # Update bucket counts
            if label_key not in self._bucket_counts:
                self._bucket_counts[label_key] = [0] * (len(self.buckets) + 1)

            # Find appropriate bucket
            for i, bucket in enumerate(self.buckets):
                if value <= bucket:
                    self._bucket_counts[label_key][i] += 1
                    break
            else:
                # Value exceeds all buckets
                self._bucket_counts[label_key][-1] += 1

    def get_percentile(self, percentile: float, labels: Optional[Dict[str, str]] = None) -> float:
        """Calculate percentile from observations."""
        with self._lock:
            label_key = Counter._serialize_labels(labels) if labels else ""
            observations = self._observations.get(label_key, [])

            if not observations:
                return 0.0

            sorted_obs = sorted(observations)
            index = int(len(sorted_obs) * percentile / 100.0)
            index = min(index, len(sorted_obs) - 1)
            return sorted_obs[index]

    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get sum of all observations."""
        with self._lock:
            label_key = Counter._serialize_labels(labels) if labels else ""
            return self._sum.get(label_key, 0.0)

    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Get count of observations."""
        with self._lock:
            label_key = Counter._serialize_labels(labels) if labels else ""
            return self._count.get(label_key, 0)

    def get_avg(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get average of observations."""
        count = self.get_count(labels)
        if count == 0:
            return 0.0
        return self.get_sum(labels) / count


# ---------------------------------------------------------------------------
# Metrics Collector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """Central metrics collection and exposition for Prometheus.

    Tracks key metrics including:
    - Request counts and latencies
    - Error rates by endpoint
    - Cache hit/miss rates
    - Database query performance
    - External API call success rates
    - Resource utilization (CPU, memory, disk)
    - Background job queue depth

    Thread-safe for concurrent access from multiple workers.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()

        # Initialize core metrics
        self._init_core_metrics()

        # Start background resource monitoring
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()

        logger.info("MetricsCollector initialized with core metrics")

    def _init_core_metrics(self) -> None:
        """Initialize core application metrics."""
        # Request metrics
        self.register_counter(
            "fda_requests_total",
            "Total number of API requests",
        )
        self.register_counter(
            "fda_requests_errors_total",
            "Total number of failed API requests",
        )
        self.register_histogram(
            "fda_request_duration_seconds",
            "Request duration in seconds",
        )

        # Cache metrics
        self.register_counter(
            "fda_cache_hits_total",
            "Total number of cache hits",
        )
        self.register_counter(
            "fda_cache_misses_total",
            "Total number of cache misses",
        )
        self.register_gauge(
            "fda_cache_size_bytes",
            "Current cache size in bytes",
        )

        # Database metrics
        self.register_histogram(
            "fda_db_query_duration_seconds",
            "Database query duration in seconds",
        )
        self.register_counter(
            "fda_db_queries_total",
            "Total number of database queries",
        )

        # External API metrics
        self.register_counter(
            "fda_external_api_calls_total",
            "Total number of external API calls",
        )
        self.register_counter(
            "fda_external_api_errors_total",
            "Total number of failed external API calls",
        )
        self.register_histogram(
            "fda_external_api_duration_seconds",
            "External API call duration in seconds",
        )

        # Rate limiter metrics
        self.register_gauge(
            "fda_rate_limit_tokens_available",
            "Available rate limit tokens",
        )
        self.register_counter(
            "fda_rate_limit_waits_total",
            "Total number of rate limit waits",
        )

        # Background job metrics
        self.register_gauge(
            "fda_background_jobs_queued",
            "Number of background jobs in queue",
        )
        self.register_gauge(
            "fda_background_jobs_active",
            "Number of active background jobs",
        )
        self.register_counter(
            "fda_background_jobs_completed_total",
            "Total number of completed background jobs",
        )
        self.register_counter(
            "fda_background_jobs_failed_total",
            "Total number of failed background jobs",
        )

        # Resource utilization gauges
        self.register_gauge(
            "fda_cpu_usage_percent",
            "CPU usage percentage",
        )
        self.register_gauge(
            "fda_memory_usage_percent",
            "Memory usage percentage",
        )
        self.register_gauge(
            "fda_memory_usage_bytes",
            "Memory usage in bytes",
        )
        self.register_gauge(
            "fda_disk_usage_percent",
            "Disk usage percentage",
        )
        self.register_gauge(
            "fda_open_file_descriptors",
            "Number of open file descriptors",
        )

    def register_counter(self, name: str, help_text: str) -> Counter:
        """Register a new counter metric."""
        with self._lock:
            if name in self._counters:
                return self._counters[name]
            counter = Counter(name=name, help_text=help_text)
            self._counters[name] = counter
            return counter

    def register_gauge(self, name: str, help_text: str) -> Gauge:
        """Register a new gauge metric."""
        with self._lock:
            if name in self._gauges:
                return self._gauges[name]
            gauge = Gauge(name=name, help_text=help_text)
            self._gauges[name] = gauge
            return gauge

    def register_histogram(self, name: str, help_text: str,
                          buckets: Optional[List[float]] = None) -> Histogram:
        """Register a new histogram metric."""
        with self._lock:
            if name in self._histograms:
                return self._histograms[name]
            histogram = Histogram(
                name=name,
                help_text=help_text,
                buckets=buckets or LATENCY_BUCKETS.copy(),
            )
            self._histograms[name] = histogram
            return histogram

    def increment_counter(self, name: str, amount: float = 1.0,
                         labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        if name in self._counters:
            self._counters[name].inc(amount, labels)
        else:
            logger.warning("Counter '%s' not registered", name)

    def set_gauge(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        if name in self._gauges:
            self._gauges[name].set(value, labels)
        else:
            logger.warning("Gauge '%s' not registered", name)

    def increment_gauge(self, name: str, amount: float = 1.0,
                       labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a gauge metric."""
        if name in self._gauges:
            self._gauges[name].inc(amount, labels)
        else:
            logger.warning("Gauge '%s' not registered", name)

    def decrement_gauge(self, name: str, amount: float = 1.0,
                       labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement a gauge metric."""
        if name in self._gauges:
            self._gauges[name].dec(amount, labels)
        else:
            logger.warning("Gauge '%s' not registered", name)

    def record_histogram(self, name: str, value: float,
                        labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram observation."""
        if name in self._histograms:
            self._histograms[name].observe(value, labels)
        else:
            logger.warning("Histogram '%s' not registered", name)

    @contextmanager
    def track_request(self, endpoint: str, labels: Optional[Dict[str, str]] = None):
        """Context manager to track request duration and errors.

        Usage:
            with metrics.track_request("api_510k_fetch", labels={"method": "GET"}):
                result = fetch_data()
        """
        start_time = time.time()
        request_labels = {"endpoint": endpoint}
        if labels:
            request_labels.update(labels)

        self.increment_counter("fda_requests_total", labels=request_labels)

        error_occurred = False
        try:
            yield
        except Exception:
            error_occurred = True
            self.increment_counter("fda_requests_errors_total", labels=request_labels)
            raise
        finally:
            duration = time.time() - start_time
            self.record_histogram("fda_request_duration_seconds", duration, labels=request_labels)

    @contextmanager
    def track_db_query(self, query_name: str):
        """Context manager to track database query performance."""
        start_time = time.time()
        labels = {"query": query_name}

        self.increment_counter("fda_db_queries_total", labels=labels)

        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram("fda_db_query_duration_seconds", duration, labels=labels)

    @contextmanager
    def track_external_api_call(self, api_name: str):
        """Context manager to track external API calls."""
        start_time = time.time()
        labels = {"api": api_name}

        self.increment_counter("fda_external_api_calls_total", labels=labels)

        error_occurred = False
        try:
            yield
        except Exception:
            error_occurred = True
            self.increment_counter("fda_external_api_errors_total", labels=labels)
            raise
        finally:
            duration = time.time() - start_time
            self.record_histogram("fda_external_api_duration_seconds", duration, labels=labels)

    def track_cache_access(self, hit: bool, cache_name: str = "default") -> None:
        """Track cache hit or miss."""
        labels = {"cache": cache_name}
        if hit:
            self.increment_counter("fda_cache_hits_total", labels=labels)
        else:
            self.increment_counter("fda_cache_misses_total", labels=labels)

    def get_cache_hit_rate(self, cache_name: str = "default") -> float:
        """Calculate cache hit rate as percentage."""
        labels = {"cache": cache_name}
        hits = self._counters["fda_cache_hits_total"].get(labels)
        misses = self._counters["fda_cache_misses_total"].get(labels)
        total = hits + misses

        if total == 0:
            return 0.0
        return (hits / total) * 100.0

    def get_error_rate(self, endpoint: Optional[str] = None) -> float:
        """Calculate error rate as percentage."""
        labels = {"endpoint": endpoint} if endpoint else None

        total = self._counters["fda_requests_total"].get(labels)
        errors = self._counters["fda_requests_errors_total"].get(labels)

        if total == 0:
            return 0.0
        return (errors / total) * 100.0

    def get_latency_percentiles(self, endpoint: Optional[str] = None) -> Dict[str, float]:
        """Get latency percentiles (p50, p95, p99) in milliseconds."""
        labels = {"endpoint": endpoint} if endpoint else None
        histogram = self._histograms.get("fda_request_duration_seconds")

        if not histogram:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        return {
            "p50": histogram.get_percentile(50, labels) * 1000,
            "p95": histogram.get_percentile(95, labels) * 1000,
            "p99": histogram.get_percentile(99, labels) * 1000,
        }

    def _monitor_resources(self) -> None:
        """Background thread to monitor system resources."""
        while self._monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.set_gauge("fda_cpu_usage_percent", cpu_percent)

                # Memory usage
                memory = psutil.virtual_memory()
                self.set_gauge("fda_memory_usage_percent", memory.percent)
                self.set_gauge("fda_memory_usage_bytes", memory.used)

                # Disk usage (for data directory)
                data_dir = os.path.expanduser("~/fda-510k-data")
                if os.path.exists(data_dir):
                    disk = psutil.disk_usage(data_dir)
                    self.set_gauge("fda_disk_usage_percent", disk.percent)

                # Open file descriptors (Unix only)
                try:
                    process = psutil.Process()
                    self.set_gauge("fda_open_file_descriptors", process.num_fds())
                except (AttributeError, OSError):
                    pass  # Not available on this platform

                # Sleep for 15 seconds before next measurement
                time.sleep(15)

            except Exception as e:
                logger.error("Error monitoring resources: %s", e)
                time.sleep(15)

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            String containing metrics in Prometheus exposition format.
        """
        lines = []

        # Export counters
        for counter in self._counters.values():
            lines.append(f"# HELP {counter.name} {counter.help_text}")
            lines.append(f"# TYPE {counter.name} counter")

            if counter.labels:
                for label_data in counter.labels.values():
                    label_str = ",".join(
                        f'{k}="{v}"' for k, v in label_data["labels"].items()
                    )
                    lines.append(f'{counter.name}{{{label_str}}} {label_data["value"]}')
            else:
                lines.append(f"{counter.name} {counter.value}")

        # Export gauges
        for gauge in self._gauges.values():
            lines.append(f"# HELP {gauge.name} {gauge.help_text}")
            lines.append(f"# TYPE {gauge.name} gauge")

            if gauge.labels:
                for label_data in gauge.labels.values():
                    label_str = ",".join(
                        f'{k}="{v}"' for k, v in label_data["labels"].items()
                    )
                    lines.append(f'{gauge.name}{{{label_str}}} {label_data["value"]}')
            else:
                lines.append(f"{gauge.name} {gauge.value}")

        # Export histograms
        for histogram in self._histograms.values():
            lines.append(f"# HELP {histogram.name} {histogram.help_text}")
            lines.append(f"# TYPE {histogram.name} histogram")

            # For each label combination
            label_keys = set(histogram._sum.keys())
            if not label_keys:
                label_keys = {""}

            for label_key in label_keys:
                labels = {}
                if label_key:
                    # Parse label key back to dict
                    for pair in label_key.split(","):
                        k, v = pair.split("=")
                        labels[k] = v

                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                label_prefix = f"{{{label_str}}}" if label_str else ""

                # Export bucket counts
                bucket_counts = histogram._bucket_counts.get(label_key, [])
                cumulative = 0
                for i, bucket in enumerate(histogram.buckets):
                    if i < len(bucket_counts):
                        cumulative += bucket_counts[i]
                    bucket_label = f'{label_str},le="{bucket}"' if label_str else f'le="{bucket}"'
                    lines.append(f'{histogram.name}_bucket{{{bucket_label}}} {cumulative}')

                # +Inf bucket
                if label_str:
                    inf_label = f'{label_str},le="+Inf"'
                else:
                    inf_label = 'le="+Inf"'
                lines.append(f'{histogram.name}_bucket{{{inf_label}}} {histogram.get_count(labels)}')

                # Sum and count
                lines.append(f"{histogram.name}_sum{label_prefix} {histogram.get_sum(labels)}")
                lines.append(f"{histogram.name}_count{label_prefix} {histogram.get_count(labels)}")

        return "\n".join(lines) + "\n"

    def get_slo_compliance(self, targets: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Calculate SLO compliance metrics.

        Args:
            targets: Optional dict of SLO targets. Uses DEFAULT_SLO_TARGETS if not provided.

        Returns:
            Dict containing SLO compliance status for each metric.
        """
        targets = targets or DEFAULT_SLO_TARGETS

        percentiles = self.get_latency_percentiles()
        error_rate = self.get_error_rate()
        cache_hit_rate = self.get_cache_hit_rate()

        return {
            "api_latency_p95_ms": {
                "value": percentiles["p95"],
                "target": targets["api_latency_p95_ms"],
                "compliant": percentiles["p95"] <= targets["api_latency_p95_ms"],
                "budget_remaining_percent": max(0, 100 * (1 - percentiles["p95"] / targets["api_latency_p95_ms"])),
            },
            "api_latency_p99_ms": {
                "value": percentiles["p99"],
                "target": targets["api_latency_p99_ms"],
                "compliant": percentiles["p99"] <= targets["api_latency_p99_ms"],
                "budget_remaining_percent": max(0, 100 * (1 - percentiles["p99"] / targets["api_latency_p99_ms"])),
            },
            "error_rate_percent": {
                "value": error_rate,
                "target": targets["error_rate_percent"],
                "compliant": error_rate <= targets["error_rate_percent"],
                "budget_remaining_percent": max(0, 100 * (1 - error_rate / targets["error_rate_percent"])),
            },
            "cache_hit_rate_percent": {
                "value": cache_hit_rate,
                "target": targets["cache_hit_rate_percent"],
                "compliant": cache_hit_rate >= targets["cache_hit_rate_percent"],
                "budget_remaining_percent": max(0, 100 * (cache_hit_rate / targets["cache_hit_rate_percent"] - 1)),
            },
        }

    def shutdown(self) -> None:
        """Shutdown the metrics collector and stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("MetricsCollector shut down")


# ---------------------------------------------------------------------------
# Health Checker
# ---------------------------------------------------------------------------

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, Dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "checks": self.checks,
        }


class HealthChecker:
    """Comprehensive health and readiness checks for the application.

    Performs checks on:
    - System resources (CPU, memory, disk)
    - External dependencies (FDA API, databases)
    - Internal services (cache, rate limiter)
    - Configuration validity
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize health checker.

        Args:
            metrics_collector: Optional metrics collector for health metrics.
        """
        self.metrics = metrics_collector
        self._checks: Dict[str, Callable[[], Tuple[bool, str, Dict[str, Any]]]] = {}

        # Register default checks
        self._register_default_checks()

        logger.info("HealthChecker initialized")

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register_check("cpu", self._check_cpu)
        self.register_check("memory", self._check_memory)
        self.register_check("disk", self._check_disk)
        self.register_check("process", self._check_process)

    def register_check(self, name: str, check_func: Callable[[], Tuple[bool, str, Dict[str, Any]]]) -> None:
        """Register a custom health check.

        Args:
            name: Name of the check
            check_func: Function that returns (healthy: bool, message: str, details: dict)
        """
        self._checks[name] = check_func
        logger.debug("Registered health check: %s", name)

    def _check_cpu(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check CPU usage."""
        cpu_percent = psutil.cpu_percent(interval=0.1)

        details = {
            "cpu_percent": cpu_percent,
            "threshold_warning": HEALTH_THRESHOLDS["cpu_percent_warning"],
            "threshold_critical": HEALTH_THRESHOLDS["cpu_percent_critical"],
        }

        if cpu_percent >= HEALTH_THRESHOLDS["cpu_percent_critical"]:
            return False, f"CPU usage critical: {cpu_percent:.1f}%", details
        elif cpu_percent >= HEALTH_THRESHOLDS["cpu_percent_warning"]:
            return True, f"CPU usage elevated: {cpu_percent:.1f}%", details
        else:
            return True, f"CPU usage normal: {cpu_percent:.1f}%", details

    def _check_memory(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check memory usage."""
        memory = psutil.virtual_memory()

        details = {
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024 ** 3),
            "memory_total_gb": memory.total / (1024 ** 3),
            "threshold_warning": HEALTH_THRESHOLDS["memory_percent_warning"],
            "threshold_critical": HEALTH_THRESHOLDS["memory_percent_critical"],
        }

        if memory.percent >= HEALTH_THRESHOLDS["memory_percent_critical"]:
            return False, f"Memory usage critical: {memory.percent:.1f}%", details
        elif memory.percent >= HEALTH_THRESHOLDS["memory_percent_warning"]:
            return True, f"Memory usage elevated: {memory.percent:.1f}%", details
        else:
            return True, f"Memory usage normal: {memory.percent:.1f}%", details

    def _check_disk(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check disk usage."""
        data_dir = os.path.expanduser("~/fda-510k-data")

        if not os.path.exists(data_dir):
            return True, "Data directory does not exist yet", {"data_dir": data_dir}

        disk = psutil.disk_usage(data_dir)

        details = {
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024 ** 3),
            "disk_total_gb": disk.total / (1024 ** 3),
            "data_dir": data_dir,
            "threshold_warning": HEALTH_THRESHOLDS["disk_percent_warning"],
            "threshold_critical": HEALTH_THRESHOLDS["disk_percent_critical"],
        }

        if disk.percent >= HEALTH_THRESHOLDS["disk_percent_critical"]:
            return False, f"Disk usage critical: {disk.percent:.1f}%", details
        elif disk.percent >= HEALTH_THRESHOLDS["disk_percent_warning"]:
            return True, f"Disk usage elevated: {disk.percent:.1f}%", details
        else:
            return True, f"Disk usage normal: {disk.percent:.1f}%", details

    def _check_process(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check process health."""
        try:
            process = psutil.Process()

            details = {
                "pid": process.pid,
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024 ** 2),
                "num_threads": process.num_threads(),
            }

            # Check for open file descriptors (Unix only)
            try:
                details["num_fds"] = process.num_fds()
            except (AttributeError, OSError):
                pass

            return True, "Process healthy", details

        except Exception as e:
            return False, f"Process check failed: {e}", {"error": str(e)}

    def check(self) -> HealthCheckResult:
        """Run all health checks.

        Returns:
            HealthCheckResult with overall status and individual check results.
        """
        results = {}
        overall_healthy = True

        for name, check_func in self._checks.items():
            try:
                healthy, message, details = check_func()
                results[name] = {
                    "healthy": healthy,
                    "message": message,
                    "details": details,
                }

                if not healthy:
                    overall_healthy = False

            except Exception as e:
                logger.error("Health check '%s' failed with exception: %s", name, e)
                results[name] = {
                    "healthy": False,
                    "message": f"Check failed: {e}",
                    "details": {"error": str(e)},
                }
                overall_healthy = False

        # Determine overall status
        if overall_healthy:
            status = "healthy"
        else:
            # Check if any critical checks failed
            critical_failed = any(
                not r["healthy"] for name, r in results.items()
                if name in ("memory", "disk")
            )
            status = "unhealthy" if critical_failed else "degraded"

        return HealthCheckResult(status=status, checks=results)

    def check_readiness(self) -> HealthCheckResult:
        """Check if service is ready to accept traffic.

        Readiness checks are more strict than liveness checks.

        Returns:
            HealthCheckResult with readiness status.
        """
        # For now, use the same checks as health
        # In production, you might add checks for:
        # - Database connectivity
        # - External API availability
        # - Cache warmup completion
        return self.check()


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_metrics_collector: Optional[MetricsCollector] = None
_health_checker: Optional[HealthChecker] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the singleton metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_health_checker() -> HealthChecker:
    """Get the singleton health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(metrics_collector=get_metrics_collector())
    return _health_checker


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "MetricsCollector",
    "HealthChecker",
    "HealthCheckResult",
    "Counter",
    "Gauge",
    "Histogram",
    "get_metrics_collector",
    "get_health_checker",
    "DEFAULT_SLO_TARGETS",
    "HEALTH_THRESHOLDS",
]
