# FDA Tools Production Monitoring and Observability

Comprehensive monitoring, logging, and observability infrastructure for FDA Tools in production environments.

**Implements:** FDA-190 (DEVOPS-004) - Production Monitoring and Observability
**Status:** Production Ready
**Version:** 1.0.0
**Last Updated:** 2026-02-20

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Key Metrics](#key-metrics)
- [SLI/SLO Definitions](#slislo-definitions)
- [Setup Guide](#setup-guide)
- [Monitoring Components](#monitoring-components)
- [Alert Rules](#alert-rules)
- [Dashboard Guide](#dashboard-guide)
- [Troubleshooting](#troubleshooting)
- [Runbooks](#runbooks)

## Overview

This monitoring infrastructure provides comprehensive observability for FDA Tools production deployments through:

- **Metrics Collection:** Prometheus-compatible metrics for requests, errors, latency, and resources
- **Health Checks:** Liveness and readiness probes for Kubernetes and load balancers
- **Structured Logging:** JSON logs with correlation IDs and sensitive data redaction
- **Alerting:** Automated alerts for SLO violations and critical issues
- **Dashboards:** Pre-built Grafana dashboards for visualization
- **SLO Tracking:** Error budget monitoring and compliance reporting

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FDA Tools Application                    │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Metrics        │  │ Health Checker  │  │ Structured   │ │
│  │ Collector      │  │                 │  │ Logger       │ │
│  └────────┬───────┘  └────────┬────────┘  └──────┬───────┘ │
└───────────┼──────────────────┼─────────────────┼───────────┘
            │                  │                 │
            │                  │                 │
    ┌───────▼───────┐  ┌───────▼────────┐  ┌───▼──────────┐
    │ Prometheus    │  │ Load Balancer  │  │ Log          │
    │ (Scrape :9090)│  │ (Health Check) │  │ Aggregation  │
    └───────┬───────┘  └────────────────┘  └───┬──────────┘
            │                                   │
    ┌───────▼────────┐                   ┌─────▼──────────┐
    │ Grafana        │                   │ ELK / Splunk / │
    │ Dashboards     │                   │ CloudWatch     │
    └───────┬────────┘                   └────────────────┘
            │
    ┌───────▼────────┐
    │ Alertmanager   │
    │ (Notifications)│
    └────────────────┘
```

## Key Metrics

### Request Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `fda_requests_total` | Counter | Total API requests | `endpoint` |
| `fda_requests_errors_total` | Counter | Failed API requests | `endpoint` |
| `fda_request_duration_seconds` | Histogram | Request latency | `endpoint` |

### Cache Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `fda_cache_hits_total` | Counter | Cache hits | `cache` |
| `fda_cache_misses_total` | Counter | Cache misses | `cache` |
| `fda_cache_size_bytes` | Gauge | Cache size | `cache` |

### External API Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `fda_external_api_calls_total` | Counter | External API calls | `api` |
| `fda_external_api_errors_total` | Counter | Failed external calls | `api` |
| `fda_external_api_duration_seconds` | Histogram | External API latency | `api` |

### Resource Utilization

| Metric | Type | Description |
|--------|------|-------------|
| `fda_cpu_usage_percent` | Gauge | CPU usage percentage |
| `fda_memory_usage_percent` | Gauge | Memory usage percentage |
| `fda_memory_usage_bytes` | Gauge | Memory usage in bytes |
| `fda_disk_usage_percent` | Gauge | Disk usage percentage |
| `fda_open_file_descriptors` | Gauge | Open file descriptors |

### Background Jobs

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `fda_background_jobs_queued` | Gauge | Jobs in queue | `queue` |
| `fda_background_jobs_active` | Gauge | Active jobs | `queue` |
| `fda_background_jobs_completed_total` | Counter | Completed jobs | `queue` |
| `fda_background_jobs_failed_total` | Counter | Failed jobs | `queue` |

## SLI/SLO Definitions

### Service Level Indicators (SLIs)

1. **Availability:** Percentage of successful requests
2. **Latency:** Request duration (p95, p99)
3. **Error Rate:** Percentage of failed requests
4. **Cache Performance:** Cache hit rate percentage

### Service Level Objectives (SLOs)

| SLO | Target | Measurement Window |
|-----|--------|-------------------|
| API Latency (p95) | < 500ms | 5 minutes |
| API Latency (p99) | < 1000ms | 5 minutes |
| Error Rate | < 1% | 5 minutes |
| Cache Hit Rate | > 80% | 5 minutes |
| Service Availability | > 99.9% (3 nines) | 30 days |

### Error Budget

- **Monthly Error Budget:** 0.1% downtime = ~43 minutes per month
- **Budget Tracking:** Real-time via `error_budget_remaining` metric
- **Policy:** Feature freeze when error budget < 10% remaining

## Setup Guide

### 1. Install Dependencies

```bash
# Python dependencies (psutil for resource monitoring)
pip3 install psutil

# Prometheus (for metrics collection)
# Docker:
docker run -d -p 9090:9090 -v $PWD/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

# Grafana (for dashboards)
# Docker:
docker run -d -p 3000:3000 grafana/grafana
```

### 2. Start Metrics Exporter

```bash
# Start HTTP server for Prometheus scraping
python3 plugins/fda-tools/scripts/export_metrics.py --serve --port 9090

# Or push to Prometheus push gateway
python3 plugins/fda-tools/scripts/export_metrics.py \
    --push-gateway http://pushgateway:9091 \
    --interval 30
```

### 3. Configure Prometheus

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'fda_tools'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: /metrics
```

### 4. Setup Grafana Dashboard

```bash
# Generate dashboard JSON
python3 plugins/fda-tools/scripts/generate_dashboard.py \
    --output fda_tools_dashboard.json

# Upload to Grafana
python3 plugins/fda-tools/scripts/generate_dashboard.py \
    --grafana-url http://localhost:3000 \
    --api-key <your-api-key>
```

### 5. Configure Alerting

See [Alert Rules](#alert-rules) section below.

## Monitoring Components

### Metrics Collector

**Location:** `lib/monitoring.py`

**Usage:**

```python
from lib.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Track requests
with metrics.track_request("api_510k_fetch"):
    result = fetch_510k_data(k_number)

# Track cache
metrics.track_cache_access(hit=True, cache_name="predicates")

# Custom metrics
metrics.increment_counter("custom_counter", labels={"type": "special"})
metrics.set_gauge("queue_depth", 42)
metrics.record_histogram("processing_time", 1.25)
```

### Health Checker

**Location:** `lib/monitoring.py`

**Usage:**

```python
from lib.monitoring import get_health_checker

health = get_health_checker()

# Liveness check
result = health.check()
print(result.status)  # "healthy", "degraded", or "unhealthy"

# Readiness check (stricter)
result = health.check_readiness()

# Custom health check
def check_database():
    return True, "Database connected", {"connections": 5}

health.register_check("database", check_database)
```

**CLI:**

```bash
# Basic health check
python3 scripts/check_health.py

# JSON output
python3 scripts/check_health.py --json

# Continuous monitoring
python3 scripts/check_health.py --monitor --interval 30
```

### Structured Logger

**Location:** `lib/logger.py`

**Usage:**

```python
from lib.logger import get_structured_logger, set_correlation_id

logger = get_structured_logger(__name__)

# Set correlation ID for request tracing
set_correlation_id("req-12345")

# Structured logging with context
logger.info("Processing device", extra={
    "device_code": "OVE",
    "k_number": "K241335",
    "action": "fetch_predicates",
})

# Convenience methods
logger.log_api_call("openFDA", method="GET", status_code=200, duration_ms=123)
logger.log_database_query("select_predicates", duration_ms=45, row_count=10)
logger.log_cache_access("redis", hit=True)

# Automatic sensitive data redaction
logger.info("API response", extra={
    "api_key": "secret-123",  # Automatically redacted
    "data_size": 1024,
})
```

## Alert Rules

### Critical Alerts (PagerDuty)

#### High Error Rate

```yaml
- alert: HighErrorRate
  expr: rate(fda_requests_errors_total[5m]) / rate(fda_requests_total[5m]) > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value | humanizePercentage }} (threshold: 1%)"
    runbook: "#runbook-high-error-rate"
```

#### High Latency

```yaml
- alert: HighLatencyP99
  expr: histogram_quantile(0.99, rate(fda_request_duration_seconds_bucket[5m])) > 1.0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High p99 latency detected"
    description: "p99 latency is {{ $value }}s (threshold: 1s)"
    runbook: "#runbook-high-latency"
```

#### Service Unavailable

```yaml
- alert: ServiceUnavailable
  expr: up{job="fda_tools"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "FDA Tools service is down"
    description: "Service has been unavailable for 2 minutes"
    runbook: "#runbook-service-down"
```

### Warning Alerts (Slack)

#### Elevated Error Rate

```yaml
- alert: ElevatedErrorRate
  expr: rate(fda_requests_errors_total[5m]) / rate(fda_requests_total[5m]) > 0.005
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Elevated error rate detected"
    description: "Error rate is {{ $value | humanizePercentage }} (threshold: 0.5%)"
```

#### Low Cache Hit Rate

```yaml
- alert: LowCacheHitRate
  expr: rate(fda_cache_hits_total[5m]) / (rate(fda_cache_hits_total[5m]) + rate(fda_cache_misses_total[5m])) < 0.7
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Cache hit rate is low"
    description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 70%)"
```

#### High Resource Usage

```yaml
- alert: HighCPUUsage
  expr: fda_cpu_usage_percent > 80
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High CPU usage"
    description: "CPU usage is {{ $value }}% (threshold: 80%)"

- alert: HighMemoryUsage
  expr: fda_memory_usage_percent > 75
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High memory usage"
    description: "Memory usage is {{ $value }}% (threshold: 75%)"
```

## Dashboard Guide

### Overview Dashboard

**Panels:**

1. **Request Latency (p50, p95, p99)** - Line graph showing latency percentiles over time
2. **Request Rate** - Requests per second by endpoint
3. **Error Rate** - Percentage of failed requests
4. **Cache Hit Rate** - Cache performance gauge
5. **CPU Usage** - CPU utilization gauge with thresholds
6. **Memory Usage** - Memory utilization gauge with thresholds
7. **Disk Usage** - Disk space utilization gauge
8. **SLO Compliance** - Table showing SLO compliance status
9. **Error Budget** - Remaining error budget for the month

### Accessing Dashboards

1. Navigate to Grafana: `http://<grafana-host>:3000`
2. Login with credentials
3. Go to Dashboards → FDA Tools Production Monitoring
4. Set time range (default: Last 6 hours)
5. Refresh rate: 30 seconds

## Troubleshooting

### Common Issues

#### Metrics Not Appearing in Prometheus

**Symptoms:** Prometheus shows "No data" for FDA metrics

**Diagnosis:**

```bash
# Check if metrics exporter is running
curl http://localhost:9090/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

**Resolution:**

1. Ensure metrics exporter is running: `python3 scripts/export_metrics.py --serve`
2. Verify Prometheus scrape config points to correct endpoint
3. Check firewall rules allow access to port 9090

#### Health Check Failing

**Symptoms:** Health check returns "unhealthy" status

**Diagnosis:**

```bash
# Run verbose health check
python3 scripts/check_health.py --verbose

# Check specific component
python3 scripts/check_health.py --check cpu --check memory
```

**Resolution:**

1. Check resource usage (CPU, memory, disk)
2. Verify external dependencies are accessible
3. Review logs for errors: `~/fda-510k-data/logs/fda_tools.log`

#### High Memory Usage

**Symptoms:** Memory usage consistently above 75%

**Diagnosis:**

```bash
# Check memory metrics
curl http://localhost:9090/metrics | grep fda_memory

# Inspect cache size
curl http://localhost:9090/metrics | grep fda_cache_size
```

**Resolution:**

1. Reduce cache size limits in configuration
2. Increase available memory
3. Check for memory leaks in application code
4. Review cache eviction policies

## Runbooks

### Runbook: High Error Rate

**Trigger:** Error rate > 1% for 5 minutes

**Steps:**

1. **Identify affected endpoints:**
   ```promql
   topk(5, rate(fda_requests_errors_total[5m]))
   ```

2. **Check error logs:**
   ```bash
   tail -f ~/fda-510k-data/logs/fda_tools.log | grep ERROR
   ```

3. **Investigate common errors:**
   - External API failures (FDA API, Linear)
   - Database connection issues
   - Rate limiting exhaustion

4. **Mitigation:**
   - Enable degraded mode if external APIs are down
   - Increase rate limits if approaching limits
   - Restart service if necessary

5. **Communication:**
   - Post incident update to #incidents channel
   - Update status page

### Runbook: High Latency

**Trigger:** p99 latency > 1s for 5 minutes

**Steps:**

1. **Identify slow endpoints:**
   ```promql
   topk(5, histogram_quantile(0.99, rate(fda_request_duration_seconds_bucket[5m])))
   ```

2. **Check resource utilization:**
   - CPU > 80%? Scale horizontally
   - Memory > 90%? Clear caches
   - Disk I/O bottleneck? Optimize queries

3. **Profile slow operations:**
   - Database queries (check `fda_db_query_duration_seconds`)
   - External API calls (check `fda_external_api_duration_seconds`)
   - Cache misses (check cache hit rate)

4. **Mitigation:**
   - Add caching for frequently accessed data
   - Optimize database queries
   - Add read replicas if database is bottleneck
   - Implement circuit breakers for slow external APIs

### Runbook: Service Down

**Trigger:** Service unreachable for 2 minutes

**Steps:**

1. **Verify service status:**
   ```bash
   python3 scripts/check_health.py
   ```

2. **Check process status:**
   ```bash
   ps aux | grep fda
   ```

3. **Review recent logs:**
   ```bash
   tail -100 ~/fda-510k-data/logs/fda_tools.log
   ```

4. **Restart service:**
   ```bash
   # Restart application
   systemctl restart fda-tools

   # Or for Docker
   docker restart fda-tools
   ```

5. **Verify recovery:**
   ```bash
   python3 scripts/check_health.py --readiness
   ```

6. **Post-incident:**
   - Write postmortem (template: `docs/postmortem_template.md`)
   - Update runbook with learnings
   - Implement preventive measures

## Additional Resources

- **Metrics Reference:** Full list of available metrics in `lib/monitoring.py`
- **API Documentation:** Health check API at `/health` endpoint
- **Source Code:** `lib/monitoring.py`, `lib/logger.py`
- **Scripts:** `scripts/export_metrics.py`, `scripts/check_health.py`, `scripts/generate_dashboard.py`
- **Tests:** `tests/test_monitoring.py`

## Support

For issues or questions:

1. Check logs: `~/fda-510k-data/logs/fda_tools.log`
2. Run diagnostics: `python3 scripts/check_health.py --verbose`
3. Review metrics: `curl http://localhost:9090/metrics`
4. Consult runbooks above

---

**Last Updated:** 2026-02-20
**Version:** 1.0.0
**Maintained By:** SRE Team
