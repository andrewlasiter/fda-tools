# FDA Tools Monitoring and Observability Guide

Comprehensive guide to production monitoring, observability, and SRE practices for FDA Tools.

**Version:** 1.0.0
**Task:** FDA-178 (DEVOPS-004)
**Status:** Production Ready

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Metrics](#metrics)
- [Health Checks](#health-checks)
- [Dashboards](#dashboards)
- [Alerting](#alerting)
- [SLO/SLI Tracking](#slosli-tracking)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

The FDA Tools monitoring stack provides comprehensive observability including:

- **Metrics Collection:** Prometheus for time-series metrics
- **Visualization:** Grafana dashboards for real-time monitoring
- **Health Checks:** Kubernetes-compatible liveness/readiness probes
- **Alerting:** Prometheus Alertmanager for alert routing
- **SLO Tracking:** Automated SLO compliance monitoring and error budget tracking
- **Performance Profiling:** Request tracing and latency analysis
- **Resource Monitoring:** CPU, memory, disk, and network metrics

### Key Features

- 🎯 **RED Metrics:** Request rate, Error rate, Duration tracking
- 📊 **SLO Compliance:** 99.9% availability target with error budget
- 🚨 **Smart Alerting:** Context-aware alerts with severity levels
- 📈 **Trend Analysis:** Historical metrics for capacity planning
- 🔍 **Distributed Tracing:** Request correlation across components
- ⚡ **Low Overhead:** < 5% performance impact

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     FDA Tools Application                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   API Layer  │  │  Background  │  │    Bridge    │     │
│  │              │  │     Jobs     │  │    Server    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │ MetricsCollector│                       │
│                   │  (lib/monitoring)│                      │
│                   └────────┬────────┘                       │
└────────────────────────────┼────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   /metrics      │ (Prometheus format)
                    │   /health       │ (Health checks)
                    │   /health/ready │
                    │   /health/live  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────▼───────┐
│   Prometheus   │  │   Health Check  │  │   Grafana    │
│   (Metrics)    │  │   (K8s probes)  │  │ (Dashboards) │
└───────┬────────┘  └─────────────────┘  └──────────────┘
        │
┌───────▼────────┐
│  Alertmanager  │
│   (Alerts)     │
└───────┬────────┘
        │
┌───────▼────────┐
│  Notifications │
│ (Email/Slack)  │
└────────────────┘
```

### Metrics Flow

1. **Application** emits metrics via `lib/monitoring.py`
2. **Prometheus** scrapes `/metrics` endpoint every 15s
3. **Grafana** queries Prometheus for dashboard visualization
4. **Alertmanager** receives alerts from Prometheus and routes notifications

---

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start core services (Prometheus + Grafana)
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Start with alerting
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile alerting up -d

# Start with all exporters (for detailed system metrics)
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile exporters up -d
```

### 2. Access Dashboards

- **Grafana:** http://localhost:3000 (default: admin/admin)
- **Prometheus:** http://localhost:9090
- **Alertmanager:** http://localhost:9093
- **Metrics Endpoint:** http://localhost:8080/metrics
- **Health Check:** http://localhost:8080/health

### 3. Import Dashboards

Pre-built dashboards are automatically loaded from `monitoring/grafana/dashboards/`:

- **FDA Tools Overview:** Service health, request rates, latencies, resources
- **SLO Dashboard:** SLO compliance, error budget, burn rate tracking

---

## Metrics

### Core Metrics

#### Request Metrics (RED)

```python
# Track API requests
from lib.monitoring import get_metrics_collector

metrics = get_metrics_collector()

with metrics.track_request("api_510k_fetch"):
    result = fetch_510k_data(k_number)
```

**Available Metrics:**
- `fda_requests_total` - Total request count (counter)
- `fda_requests_errors_total` - Failed request count (counter)
- `fda_request_duration_seconds` - Request latency (histogram)

#### Cache Metrics

```python
# Track cache performance
metrics.track_cache_access(hit=True, cache_name="predicates")
```

**Available Metrics:**
- `fda_cache_hits_total` - Cache hits (counter)
- `fda_cache_misses_total` - Cache misses (counter)
- `fda_cache_size_bytes` - Cache size (gauge)

#### External API Metrics

```python
# Track external API calls
with metrics.track_external_api_call("openfda"):
    data = call_openfda_api()
```

**Available Metrics:**
- `fda_external_api_calls_total` - API calls (counter)
- `fda_external_api_errors_total` - API errors (counter)
- `fda_external_api_duration_seconds` - API latency (histogram)

#### Resource Metrics (Auto-collected)

- `fda_cpu_usage_percent` - CPU usage percentage (gauge)
- `fda_memory_usage_percent` - Memory usage percentage (gauge)
- `fda_memory_usage_bytes` - Memory usage in bytes (gauge)
- `fda_disk_usage_percent` - Disk usage percentage (gauge)
- `fda_open_file_descriptors` - Open file descriptors (gauge)

### Business Metrics

```python
from lib.metrics import track_business_metric

# Track business KPIs
track_business_metric("510k_submissions_analyzed", value=1,
                     labels={"product_code": "DQY"})

track_business_metric("predicates_identified", value=5)

track_business_metric("standards_mapped", value=3,
                     labels={"standard_type": "ISO"})
```

**Available Business Metrics:**
- `510k_submissions_analyzed` - Submissions analyzed
- `predicates_identified` - Predicates found
- `standards_mapped` - Standards mapped to devices
- `regulatory_gaps_detected` - Gaps detected
- `reports_generated` - Reports created
- `api_calls_openfda` - OpenFDA API usage
- `cache_savings_hours` - Time saved via caching

### Querying Metrics

#### Prometheus Queries

```promql
# Request rate (requests per second)
rate(fda_requests_total[5m])

# Error rate (percentage)
(rate(fda_requests_errors_total[5m]) / rate(fda_requests_total[5m])) * 100

# P95 latency (milliseconds)
histogram_quantile(0.95, rate(fda_request_duration_seconds_bucket[5m])) * 1000

# Cache hit rate (percentage)
(rate(fda_cache_hits_total[5m]) / (rate(fda_cache_hits_total[5m]) + rate(fda_cache_misses_total[5m]))) * 100
```

#### Python API

```python
from lib.metrics import get_metrics_reporter

reporter = get_metrics_reporter()

# Get current SLI values
sli_values = reporter.get_sli_values()
print(f"Availability: {sli_values['availability']}%")
print(f"P95 Latency: {sli_values['api_latency_p95']}ms")

# Check SLO compliance
compliance = reporter.check_slo_compliance()
for sli_name, status in compliance.items():
    print(f"{sli_name}: {'✓' if status['compliant'] else '✗'}")

# Export metrics as JSON
metrics_json = reporter.export_metrics_json()
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose | K8s Probe |
|----------|---------|-----------|
| `/health` | Overall health status | - |
| `/health/live` | Liveness probe | livenessProbe |
| `/health/ready` | Readiness probe | readinessProbe |
| `/health/startup` | Startup probe | startupProbe |

### Health Check Components

- **CPU:** < 95% critical, < 80% warning
- **Memory:** < 90% critical, < 75% warning
- **Disk:** < 95% critical, < 85% warning
- **Process:** Process status and resource usage

### Using Health Checks

#### Manual Check

```bash
# Basic health check
curl http://localhost:8080/health

# JSON output
curl http://localhost:8080/health?format=json

# CLI tool
python3 plugins/fda-tools/scripts/check_health.py --verbose
```

#### Kubernetes Configuration

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  initialDelaySeconds: 0
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 30
```

#### Docker Compose Health Check

```yaml
healthcheck:
  test: ["CMD", "python", "/app/plugins/fda-tools/scripts/check_health.py"]
  interval: 30s
  timeout: 10s
  start_period: 60s
  retries: 3
```

---

## Dashboards

### FDA Tools Overview Dashboard

**Location:** `monitoring/grafana/dashboards/fda-tools-overview.json`

**Panels:**
- Service health status
- Request rate and error rate
- Latency percentiles (P50, P95, P99)
- CPU, memory, disk usage
- Cache performance
- External API calls

**Access:** http://localhost:3000/d/fda-tools-overview

### SLO & Error Budget Dashboard

**Location:** `monitoring/grafana/dashboards/fda-tools-slo.json`

**Panels:**
- 30-day availability SLO compliance
- Error budget remaining
- Error budget burn rate
- Latency SLO compliance (P95, P99)
- Cache hit rate SLO
- SLI summary table
- SLO violation history

**Access:** http://localhost:3000/d/fda-tools-slo

### Custom Dashboards

Create custom dashboards in Grafana using these queries:

```promql
# Business metrics over time
rate(fda_business_510k_submissions_analyzed[1h])

# Top endpoints by request count
topk(10, sum by (endpoint) (rate(fda_requests_total[5m])))

# Error rate by endpoint
sum by (endpoint) (rate(fda_requests_errors_total[5m])) / sum by (endpoint) (rate(fda_requests_total[5m]))
```

---

## Alerting

### Alert Rules

**Location:** `monitoring/alerts.yml`

**Alert Groups:**
1. **Availability** - Service down, high error rate
2. **Performance** - High latency (P95, P99)
3. **Resources** - CPU, memory, disk usage
4. **Cache** - Low cache hit rate
5. **External APIs** - API errors, slow responses
6. **SLO** - SLO violations, error budget exhausted
7. **Background Jobs** - Queue depth, failure rate

### Alert Severity

- **Critical:** Immediate action required (page on-call)
- **Warning:** Should be addressed soon (notify team)

### Configuring Notifications

Edit `monitoring/alertmanager.yml`:

#### Email Notifications

```yaml
global:
  smtp_from: 'alerts@fda-tools.example.com'
  smtp_smarthost: 'smtp.example.com:587'
  smtp_auth_username: 'alerts@fda-tools.example.com'
  smtp_auth_password: 'your-password'

receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@example.com'
        headers:
          Subject: '[CRITICAL] FDA Tools Alert'
```

#### Slack Notifications

```yaml
receivers:
  - name: 'critical-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#fda-tools-alerts'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        send_resolved: true
```

#### PagerDuty Integration

```yaml
receivers:
  - name: 'critical-alerts'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
```

### Testing Alerts

```bash
# Send test alert
curl -X POST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {"alertname": "TestAlert", "severity": "critical"},
  "annotations": {"summary": "Test alert", "description": "Testing alert pipeline"}
}]'

# Verify Alertmanager configuration
docker exec fda-tools-alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# List active alerts
curl http://localhost:9093/api/v1/alerts
```

---

## SLO/SLI Tracking

### Service Level Indicators (SLIs)

| SLI | Target | Unit |
|-----|--------|------|
| Availability | 99.9% | percent |
| API Latency (P95) | 500ms | milliseconds |
| API Latency (P99) | 1000ms | milliseconds |
| Error Rate | < 1% | percent |
| Cache Hit Rate | > 80% | percent |

### Service Level Objectives (SLOs)

**30-day Availability SLO: 99.9%**
- Allows 43 minutes downtime per month
- Error budget: 0.1% of requests can fail

### Error Budget

```python
# Calculate error budget
total_requests = 1,000,000
error_budget = total_requests * 0.001  # 0.1%
# = 1,000 allowed errors per month

# Check error budget status
from lib.metrics import get_metrics_reporter

reporter = get_metrics_reporter()
slo_report = reporter.generate_slo_report()

print(f"Error budget remaining: {slo_report['error_budget_remaining_percent']}%")
```

### Error Budget Policy

**If error budget is exhausted:**
1. Freeze feature releases
2. Focus on reliability improvements
3. Conduct incident retrospectives
4. Restore error budget before new features

**Burn Rate Thresholds:**
- **1h burn rate > 10x:** Page on-call immediately
- **6h burn rate > 5x:** Alert engineering team
- **24h burn rate > 2x:** Warning notification

---

## Troubleshooting

### High Error Rate

```bash
# Check error logs
docker logs fda-tools-main --tail 100 | grep ERROR

# Query error breakdown by endpoint
curl http://localhost:9090/api/v1/query?query=sum+by+%28endpoint%29+%28rate%28fda_requests_errors_total%5B5m%5D%29%29

# Check external API errors
curl http://localhost:9090/api/v1/query?query=rate%28fda_external_api_errors_total%5B5m%5D%29
```

### High Latency

```bash
# Check P99 latency by endpoint
curl http://localhost:9090/api/v1/query?query=histogram_quantile%280.99%2C+rate%28fda_request_duration_seconds_bucket%5B5m%5D%29%29

# Check resource usage
python3 plugins/fda-tools/scripts/check_health.py --verbose

# Profile slow requests
# Enable detailed logging in lib/monitoring.py
```

### Low Cache Hit Rate

```bash
# Check cache hit rate
curl http://localhost:9090/api/v1/query?query=rate%28fda_cache_hits_total%5B5m%5D%29+%2F+%28rate%28fda_cache_hits_total%5B5m%5D%29+%2B+rate%28fda_cache_misses_total%5B5m%5D%29%29

# Check cache size
curl http://localhost:9090/api/v1/query?query=fda_cache_size_bytes

# Investigate cache eviction patterns in logs
```

### Resource Exhaustion

```bash
# Check CPU usage
docker stats fda-tools-main

# Check memory leaks
python3 plugins/fda-tools/scripts/check_health.py --check memory --verbose

# Review resource limits
docker inspect fda-tools-main | grep -A 10 Resources
```

### Metrics Not Appearing

```bash
# Verify metrics endpoint is accessible
curl http://localhost:8080/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify Prometheus scrape config
docker exec fda-tools-prometheus cat /etc/prometheus/prometheus.yml

# Check Prometheus logs
docker logs fda-tools-prometheus --tail 50
```

---

## Best Practices

### Instrumentation

1. **Use Context Managers:** Track requests with `track_request()` context manager
2. **Label Wisely:** Use low-cardinality labels (avoid user IDs, timestamps)
3. **Track Business Metrics:** Monitor KPIs, not just technical metrics
4. **Consistent Naming:** Follow Prometheus naming conventions (`_total`, `_seconds`, etc.)

```python
# Good: Low-cardinality labels
metrics.track_request("api_fetch", labels={"method": "GET", "status": "200"})

# Bad: High-cardinality labels (creates too many time series)
# metrics.track_request("api_fetch", labels={"user_id": "12345", "timestamp": "2024-02-20"})
```

### Alerting

1. **Alert on Symptoms, Not Causes:** Alert on user-facing issues
2. **Reduce Noise:** Use inhibition rules to prevent alert storms
3. **Actionable Alerts:** Every alert should require action
4. **Severity Levels:** Critical for immediate action, Warning for awareness
5. **Clear Runbooks:** Document response procedures

### SLO Management

1. **Start Conservative:** Begin with achievable SLOs, tighten over time
2. **Monitor Error Budget:** Track burn rate continuously
3. **Regular Reviews:** Review SLOs quarterly, adjust based on business needs
4. **Postmortems:** Learn from SLO violations
5. **Balance:** Don't over-optimize (99.999% may not be worth the cost)

### Performance

1. **Sampling:** Sample high-volume metrics if needed
2. **Aggregation:** Pre-aggregate metrics before export
3. **Retention:** Configure appropriate retention periods
4. **Cleanup:** Remove unused metrics and labels

### Monitoring the Monitoring

1. **Monitor Prometheus:** Set up alerts for Prometheus itself
2. **Storage Capacity:** Alert on TSDB storage usage
3. **Scrape Duration:** Monitor scrape times
4. **Query Performance:** Optimize slow PromQL queries

---

## Additional Resources

### Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)

### Related FDA Tools Docs

- [Deployment Guide](./DEPLOYMENT.md) - CI/CD and deployment
- [Docker Guide](./DOCKER.md) - Container orchestration
- [Configuration Guide](./CONFIGURATION.md) - Service configuration

### Support

- **Issues:** [GitHub Issues](https://github.com/your-org/fda-tools/issues)
- **Slack:** #fda-tools-monitoring
- **On-call:** PagerDuty escalation

---

**Last Updated:** 2024-02-20
**Maintained By:** DevOps Team
**Review Cycle:** Quarterly
