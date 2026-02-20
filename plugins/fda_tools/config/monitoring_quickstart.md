# Monitoring Quick Start Guide

Fast setup guide for FDA Tools production monitoring.

## 5-Minute Quick Start

### 1. Install Dependencies

```bash
pip3 install psutil
```

### 2. Start Metrics Exporter

```bash
# Terminal 1: Start metrics HTTP server
python3 scripts/export_metrics.py --serve --port 9090
```

### 3. Verify Health

```bash
# Terminal 2: Check health
python3 scripts/check_health.py --verbose

# Should output:
# ✓ Overall Status: HEALTHY
# ✓ CPU: normal
# ✓ MEMORY: normal
# ✓ DISK: normal
# ✓ PROCESS: healthy
```

### 4. View Metrics

```bash
# Get Prometheus metrics
curl http://localhost:9090/metrics

# Export to file
python3 scripts/export_metrics.py --output /tmp/metrics.txt
```

### 5. Generate Dashboard

```bash
# Create Grafana dashboard JSON
python3 scripts/generate_dashboard.py --output dashboard.json
```

## Integration with Your Code

### Basic Monitoring

```python
from lib.monitoring import get_metrics_collector, get_health_checker

# Initialize
metrics = get_metrics_collector()
health = get_health_checker()

# Track requests
with metrics.track_request("my_endpoint"):
    do_work()

# Check health
status = health.check()
print(status.status)  # "healthy", "degraded", or "unhealthy"
```

### Structured Logging

```python
from lib.logger import get_structured_logger, set_correlation_id

logger = get_structured_logger(__name__)

# Set correlation ID for request tracing
set_correlation_id("req-abc123")

# Log with context
logger.info("Processing request", extra={
    "user_id": "12345",
    "action": "fetch_data"
})

# Sensitive data is automatically redacted
logger.info("API call", extra={
    "api_key": "secret-key",  # → [REDACTED]
    "endpoint": "/api/data"
})
```

## Kubernetes Integration

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 9090
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

Or using script:

```yaml
livenessProbe:
  exec:
    command:
    - python3
    - scripts/check_health.py
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe

```yaml
readinessProbe:
  exec:
    command:
    - python3
    - scripts/check_health.py
    - --readiness
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
```

### Prometheus Scraping

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fda-tools
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
    prometheus.io/path: "/metrics"
spec:
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
```

## Prometheus Configuration

Minimal `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fda_tools'
    static_configs:
      - targets: ['localhost:9090']
```

## Alert Rules

Copy to Prometheus:

```bash
cp config/prometheus_alerts.yml /etc/prometheus/alerts/fda_tools.yml
```

Add to `prometheus.yml`:

```yaml
rule_files:
  - 'alerts/fda_tools.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

## Grafana Dashboard

### Import via UI

1. Open Grafana → Dashboards → Import
2. Upload `dashboard.json`
3. Select Prometheus data source

### Import via API

```bash
python3 scripts/generate_dashboard.py \
  --grafana-url http://localhost:3000 \
  --api-key <your-api-key>
```

## Common Commands

```bash
# Health checks
python3 scripts/check_health.py                    # Basic check
python3 scripts/check_health.py --readiness        # Readiness
python3 scripts/check_health.py --json             # JSON output
python3 scripts/check_health.py --monitor          # Continuous

# Metrics
python3 scripts/export_metrics.py --serve          # HTTP server
python3 scripts/export_metrics.py --output file    # Export to file
python3 scripts/export_metrics.py --push-gateway URL  # Push to gateway

# Dashboard
python3 scripts/generate_dashboard.py --output dashboard.json
```

## Testing

```bash
# Run monitoring tests
pytest tests/test_monitoring.py -v

# Should show: 27 passed
```

## Troubleshooting

### Metrics not updating

Check metrics collector is initialized:

```python
from lib.monitoring import get_metrics_collector
metrics = get_metrics_collector()
# Should start background monitoring automatically
```

### Health check fails

Run verbose check to see which component failed:

```bash
python3 scripts/check_health.py --verbose
```

Common issues:
- High CPU/memory/disk usage
- Missing data directory: `~/fda-510k-data`

### No logs appearing

Ensure logging is configured:

```python
from lib.logging_config import setup_logging
setup_logging(verbose=True)
```

## Next Steps

1. Review full documentation: `MONITORING_README.md`
2. Configure alerts: `config/alertmanager.yml`
3. Set up Grafana dashboards
4. Integrate with incident management (PagerDuty, Slack)
5. Define SLO targets for your service

---

**Quick Reference:**
- Metrics: `/lib/monitoring.py`
- Logging: `/lib/logger.py`
- Scripts: `/scripts/export_metrics.py`, `/scripts/check_health.py`
- Config: `/config/prometheus_alerts.yml`, `/config/alertmanager.yml`
- Tests: `/tests/test_monitoring.py`
