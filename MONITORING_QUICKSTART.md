# FDA Tools Monitoring - Quick Start Guide

Get production monitoring up and running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- FDA Tools application running
- Ports available: 3000 (Grafana), 9090 (Prometheus)

## Step 1: Configure Environment (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Edit Grafana password (required)
nano .env
# Set: GRAFANA_PASSWORD=your_secure_password_here
```

## Step 2: Start Monitoring Stack (2 minutes)

```bash
# Start core monitoring (Prometheus + Grafana)
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f prometheus grafana
```

## Step 3: Access Dashboards (1 minute)

Open in your browser:

- **Grafana:** http://localhost:3000
  - Login: `admin` / `your_secure_password_here`
  - Go to Dashboards → FDA Tools Overview

- **Prometheus:** http://localhost:9090
  - Check Targets: Status → Targets
  - Verify FDA Tools target is UP

## Step 4: Verify Metrics (1 minute)

```bash
# Check metrics endpoint
curl http://localhost:8080/metrics | head -20

# Check health endpoint
curl http://localhost:8080/health | jq

# Run verification script
bash scripts/verify_monitoring_setup.sh
```

## Available Dashboards

1. **FDA Tools Overview** (`/d/fda-tools-overview`)
   - Service health and performance
   - Request rates and error rates
   - Latency percentiles
   - Resource usage

2. **SLO & Error Budget** (`/d/fda-tools-slo`)
   - 99.9% availability SLO
   - Error budget tracking
   - Burn rate monitoring
   - Compliance status

## Common Commands

```bash
# View metrics in Prometheus format
curl http://localhost:8080/metrics

# View metrics in JSON format
curl http://localhost:8080/metrics/json | jq

# Check SLO compliance
curl http://localhost:8080/metrics/slo | jq

# Run health check
python3 plugins/fda-tools/scripts/check_health.py --verbose

# View Prometheus alerts
curl http://localhost:9090/api/v1/alerts | jq

# Stop monitoring stack
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml down
```

## Optional: Enable Alerting

```bash
# Edit Alertmanager config
nano monitoring/alertmanager.yml
# Configure email/Slack/PagerDuty

# Start with alerting
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile alerting up -d

# Access Alertmanager
open http://localhost:9093
```

## Optional: Advanced Metrics

```bash
# Start with all metric exporters
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile exporters up -d

# This adds:
# - Node Exporter (host metrics)
# - cAdvisor (container metrics)
# - Postgres Exporter (database metrics)
# - Redis Exporter (cache metrics)
```

## Troubleshooting

### Grafana shows "No data"
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify FDA Tools is exposing metrics
curl http://localhost:8080/metrics

# Check Prometheus logs
docker logs fda-tools-prometheus
```

### Metrics not updating
```bash
# Check scrape interval (default: 15s)
# Wait at least 30 seconds for data to appear

# Verify Prometheus can reach FDA Tools
docker exec fda-tools-prometheus wget -O- http://fda-tools:8080/metrics
```

### Dashboard import failed
```bash
# Dashboards are auto-provisioned from:
# monitoring/grafana/dashboards/*.json

# Verify files exist
ls -la monitoring/grafana/dashboards/

# Restart Grafana to re-provision
docker-compose restart grafana
```

## Next Steps

1. **Read full documentation:** [docs/MONITORING_GUIDE.md](docs/MONITORING_GUIDE.md)
2. **Configure alerts:** Edit `monitoring/alertmanager.yml`
3. **Customize dashboards:** Create custom panels in Grafana
4. **Set up notifications:** Configure Slack/Email/PagerDuty
5. **Review SLOs:** Adjust targets in `lib/metrics.py`

## Key Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Availability | 99.9% | < 99.9% |
| P95 Latency | < 500ms | > 750ms |
| P99 Latency | < 1000ms | > 1500ms |
| Error Rate | < 1% | > 2% |
| Cache Hit Rate | > 80% | < 70% |
| CPU Usage | - | > 80% |
| Memory Usage | - | > 75% |

## Support

- **Documentation:** [docs/MONITORING_GUIDE.md](docs/MONITORING_GUIDE.md)
- **Implementation Details:** [FDA-178_MONITORING_IMPLEMENTATION.md](FDA-178_MONITORING_IMPLEMENTATION.md)
- **Issues:** GitHub Issues
- **Tests:** `pytest plugins/fda-tools/tests/test_monitoring_integration.py -v`

---

**Task:** FDA-178 (DEVOPS-004)
**Last Updated:** 2024-02-20
