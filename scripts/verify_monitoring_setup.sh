#!/bin/bash
#
# Monitoring Setup Verification Script
# Verifies that all monitoring components are properly configured
#
# Usage: ./scripts/verify_monitoring_setup.sh

set -e

echo "========================================="
echo "FDA Tools Monitoring Setup Verification"
echo "========================================="
echo ""

FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python modules
echo "Checking Python monitoring modules..."
cd plugins/fda-tools 2>/dev/null || true
python3 -c "from lib.monitoring import get_metrics_collector, get_health_checker" 2>/dev/null && check_pass "lib/monitoring.py imports successfully" || check_fail "lib/monitoring.py import failed"
python3 -c "from lib.metrics import get_metrics_reporter, track_business_metric" 2>/dev/null && check_pass "lib/metrics.py imports successfully" || check_fail "lib/metrics.py import failed"
python3 -c "from lib.health_checks import register_health_endpoints" 2>/dev/null && check_pass "lib/health_checks.py imports successfully" || check_warn "lib/health_checks.py import failed (FastAPI not installed)"
cd - > /dev/null 2>&1 || true
echo ""

# Check monitoring files
echo "Checking monitoring configuration files..."
test -f monitoring/prometheus.yml && check_pass "prometheus.yml exists" || check_fail "prometheus.yml missing"
test -f monitoring/alerts.yml && check_pass "alerts.yml exists" || check_fail "alerts.yml missing"
test -f monitoring/alertmanager.yml && check_pass "alertmanager.yml exists" || check_fail "alertmanager.yml missing"
test -f monitoring/docker-compose.monitoring.yml && check_pass "docker-compose.monitoring.yml exists" || check_fail "docker-compose.monitoring.yml missing"
echo ""

# Check Grafana dashboards
echo "Checking Grafana dashboards..."
test -f monitoring/grafana/datasources/prometheus.yml && check_pass "Prometheus datasource config exists" || check_fail "Prometheus datasource config missing"
test -f monitoring/grafana/dashboards/dashboard.yml && check_pass "Dashboard provisioning config exists" || check_fail "Dashboard provisioning config missing"
test -f monitoring/grafana/dashboards/fda-tools-overview.json && check_pass "Overview dashboard exists" || check_fail "Overview dashboard missing"
test -f monitoring/grafana/dashboards/fda-tools-slo.json && check_pass "SLO dashboard exists" || check_fail "SLO dashboard missing"
echo ""

# Check scripts
echo "Checking monitoring scripts..."
test -x plugins/fda-tools/scripts/check_health.py && check_pass "check_health.py is executable" || check_fail "check_health.py not executable"
test -x plugins/fda-tools/scripts/metrics_server.py && check_pass "metrics_server.py is executable" || check_fail "metrics_server.py not executable"
echo ""

# Check documentation
echo "Checking documentation..."
test -f docs/MONITORING_GUIDE.md && check_pass "MONITORING_GUIDE.md exists" || check_fail "MONITORING_GUIDE.md missing"
test -f FDA-178_MONITORING_IMPLEMENTATION.md && check_pass "Implementation summary exists" || check_fail "Implementation summary missing"
echo ""

# Run unit tests
echo "Running monitoring integration tests..."
if command -v pytest &> /dev/null; then
    cd plugins/fda-tools
    if pytest tests/test_monitoring_integration.py -q --tb=no 2>&1 | grep -q "22 passed"; then
        check_pass "All 22 integration tests passed"
    else
        check_fail "Some integration tests failed"
    fi
    cd - > /dev/null
else
    check_warn "pytest not installed, skipping tests"
fi
echo ""

# Test metrics collection
echo "Testing metrics collection..."
cd plugins/fda-tools 2>/dev/null || true
python3 -c "
from lib.monitoring import get_metrics_collector
metrics = get_metrics_collector()
with metrics.track_request('test'):
    pass
export = metrics.export_prometheus()
assert 'fda_requests_total' in export
print('Metrics collection working')
" 2>/dev/null && check_pass "Metrics collection functional" || check_fail "Metrics collection failed"
echo ""

# Test health checks
echo "Testing health checks..."
python3 -c "
from lib.monitoring import get_health_checker
health = get_health_checker()
result = health.check()
assert result.status in ('healthy', 'degraded', 'unhealthy')
print('Health checks working')
" 2>/dev/null && check_pass "Health checks functional" || check_fail "Health checks failed"
echo ""

# Test SLO tracking
echo "Testing SLO tracking..."
python3 -c "
from lib.metrics import get_metrics_reporter
reporter = get_metrics_reporter()
compliance = reporter.check_slo_compliance()
assert 'availability' in compliance
assert 'api_latency_p95' in compliance
print('SLO tracking working')
" 2>/dev/null && check_pass "SLO tracking functional" || check_fail "SLO tracking failed"
cd - > /dev/null 2>&1 || true
echo ""

# Check alert rules syntax
echo "Validating Prometheus configuration..."
if command -v promtool &> /dev/null; then
    promtool check config monitoring/prometheus.yml &> /dev/null && check_pass "prometheus.yml syntax valid" || check_fail "prometheus.yml syntax invalid"
    promtool check rules monitoring/alerts.yml &> /dev/null && check_pass "alerts.yml syntax valid" || check_fail "alerts.yml syntax invalid"
else
    check_warn "promtool not installed, skipping Prometheus config validation"
fi
echo ""

# Summary
echo "========================================="
echo "Verification Summary"
echo "========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo ""
    echo "Monitoring setup is complete and functional."
    echo ""
    echo "Next steps:"
    echo "  1. Start monitoring stack: docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d"
    echo "  2. Access Grafana: http://localhost:3000"
    echo "  3. Access Prometheus: http://localhost:9090"
    echo "  4. Check metrics: http://localhost:8080/metrics"
    echo "  5. Check health: http://localhost:8080/health"
    exit 0
else
    echo -e "${RED}$FAILED check(s) failed${NC}"
    echo ""
    echo "Please review the failures above and fix any issues."
    exit 1
fi
