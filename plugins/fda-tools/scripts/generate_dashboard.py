#!/usr/bin/env python3
"""
Grafana Dashboard Generator for FDA Tools.

Generates Grafana dashboard JSON for FDA Tools monitoring with:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Cache hit rates
- External API performance
- Resource utilization (CPU, memory, disk)
- SLO compliance tracking

Usage:
    # Generate dashboard JSON
    python3 generate_dashboard.py --output fda_tools_dashboard.json

    # Import to Grafana via API
    python3 generate_dashboard.py --grafana-url http://localhost:3000 --api-key <key>
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from lib.logging_config import setup_logging, add_logging_args

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dashboard Configuration
# ---------------------------------------------------------------------------

def create_dashboard() -> Dict[str, Any]:
    """Create Grafana dashboard configuration.

    Returns:
        Dashboard JSON structure
    """
    dashboard = {
        "dashboard": {
            "title": "FDA Tools Production Monitoring",
            "tags": ["fda-tools", "production", "sre"],
            "timezone": "utc",
            "schemaVersion": 16,
            "version": 0,
            "refresh": "30s",
            "time": {
                "from": "now-6h",
                "to": "now"
            },
            "panels": [],
        },
        "overwrite": True,
    }

    # Panel positions (grid layout)
    y_pos = 0
    panel_id = 1

    # Row 1: Request Metrics
    dashboard["dashboard"]["panels"].extend([
        create_row_panel("Request Metrics", y_pos, panel_id),
    ])
    y_pos += 1
    panel_id += 1

    dashboard["dashboard"]["panels"].extend([
        create_latency_panel(y_pos, 0, panel_id),
        create_request_rate_panel(y_pos, 8, panel_id + 1),
        create_error_rate_panel(y_pos, 16, panel_id + 2),
    ])
    y_pos += 8
    panel_id += 3

    # Row 2: External Dependencies
    dashboard["dashboard"]["panels"].extend([
        create_row_panel("External Dependencies", y_pos, panel_id),
    ])
    y_pos += 1
    panel_id += 1

    dashboard["dashboard"]["panels"].extend([
        create_external_api_panel(y_pos, 0, panel_id),
        create_cache_hit_rate_panel(y_pos, 12, panel_id + 1),
    ])
    y_pos += 8
    panel_id += 2

    # Row 3: Resource Utilization
    dashboard["dashboard"]["panels"].extend([
        create_row_panel("Resource Utilization", y_pos, panel_id),
    ])
    y_pos += 1
    panel_id += 1

    dashboard["dashboard"]["panels"].extend([
        create_cpu_panel(y_pos, 0, panel_id),
        create_memory_panel(y_pos, 8, panel_id + 1),
        create_disk_panel(y_pos, 16, panel_id + 2),
    ])
    y_pos += 8
    panel_id += 3

    # Row 4: SLO Compliance
    dashboard["dashboard"]["panels"].extend([
        create_row_panel("SLO Compliance", y_pos, panel_id),
    ])
    y_pos += 1
    panel_id += 1

    dashboard["dashboard"]["panels"].extend([
        create_slo_panel(y_pos, 0, panel_id),
        create_error_budget_panel(y_pos, 12, panel_id + 1),
    ])

    return dashboard


# ---------------------------------------------------------------------------
# Panel Creators
# ---------------------------------------------------------------------------

def create_row_panel(title: str, y: int, panel_id: int) -> Dict[str, Any]:
    """Create a row panel for grouping."""
    return {
        "id": panel_id,
        "type": "row",
        "title": title,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "collapsed": False,
    }


def create_latency_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create latency percentiles panel."""
    return {
        "id": panel_id,
        "title": "Request Latency (p50, p95, p99)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 8, "x": x, "y": y},
        "targets": [
            {
                "expr": 'histogram_quantile(0.50, rate(fda_request_duration_seconds_bucket[5m]))',
                "legendFormat": "p50",
                "refId": "A",
            },
            {
                "expr": 'histogram_quantile(0.95, rate(fda_request_duration_seconds_bucket[5m]))',
                "legendFormat": "p95",
                "refId": "B",
            },
            {
                "expr": 'histogram_quantile(0.99, rate(fda_request_duration_seconds_bucket[5m]))',
                "legendFormat": "p99",
                "refId": "C",
            },
        ],
        "yaxes": [
            {"format": "s", "label": "Latency"},
            {"format": "short"},
        ],
        "thresholds": [
            {"value": 0.5, "colorMode": "critical", "op": "gt", "fill": True, "line": True},
        ],
    }


def create_request_rate_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create request rate panel."""
    return {
        "id": panel_id,
        "title": "Request Rate (req/s)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 8, "x": x, "y": y},
        "targets": [
            {
                "expr": 'rate(fda_requests_total[5m])',
                "legendFormat": "{{endpoint}}",
                "refId": "A",
            },
        ],
        "yaxes": [
            {"format": "reqps", "label": "Requests/sec"},
            {"format": "short"},
        ],
    }


def create_error_rate_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create error rate panel."""
    return {
        "id": panel_id,
        "title": "Error Rate (%)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 8, "x": x, "y": y},
        "targets": [
            {
                "expr": 'rate(fda_requests_errors_total[5m]) / rate(fda_requests_total[5m]) * 100',
                "legendFormat": "{{endpoint}}",
                "refId": "A",
            },
        ],
        "yaxes": [
            {"format": "percent", "label": "Error Rate", "max": 100},
            {"format": "short"},
        ],
        "thresholds": [
            {"value": 1.0, "colorMode": "critical", "op": "gt", "fill": True, "line": True},
        ],
        "alert": {
            "name": "High Error Rate",
            "conditions": [
                {
                    "evaluator": {"params": [1.0], "type": "gt"},
                    "operator": {"type": "and"},
                    "query": {"params": ["A", "5m", "now"]},
                    "reducer": {"params": [], "type": "avg"},
                    "type": "query",
                }
            ],
            "frequency": "1m",
            "handler": 1,
            "message": "Error rate exceeded 1% for FDA Tools",
            "noDataState": "no_data",
            "executionErrorState": "alerting",
        },
    }


def create_external_api_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create external API performance panel."""
    return {
        "id": panel_id,
        "title": "External API Calls (Success/Error)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
        "targets": [
            {
                "expr": 'rate(fda_external_api_calls_total[5m])',
                "legendFormat": "{{api}} - total",
                "refId": "A",
            },
            {
                "expr": 'rate(fda_external_api_errors_total[5m])',
                "legendFormat": "{{api}} - errors",
                "refId": "B",
            },
        ],
        "yaxes": [
            {"format": "reqps", "label": "Calls/sec"},
            {"format": "short"},
        ],
    }


def create_cache_hit_rate_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create cache hit rate panel."""
    return {
        "id": panel_id,
        "title": "Cache Hit Rate (%)",
        "type": "stat",
        "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
        "targets": [
            {
                "expr": 'rate(fda_cache_hits_total[5m]) / (rate(fda_cache_hits_total[5m]) + rate(fda_cache_misses_total[5m])) * 100',
                "legendFormat": "{{cache}}",
                "refId": "A",
            },
        ],
        "options": {
            "orientation": "auto",
            "textMode": "value_and_name",
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
        },
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": 0, "color": "red"},
                        {"value": 80, "color": "yellow"},
                        {"value": 90, "color": "green"},
                    ],
                },
            },
        },
    }


def create_cpu_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create CPU usage panel."""
    return {
        "id": panel_id,
        "title": "CPU Usage (%)",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 8, "x": x, "y": y},
        "targets": [
            {
                "expr": 'fda_cpu_usage_percent',
                "refId": "A",
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 80, "color": "yellow"},
                        {"value": 95, "color": "red"},
                    ],
                },
            },
        },
    }


def create_memory_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create memory usage panel."""
    return {
        "id": panel_id,
        "title": "Memory Usage (%)",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 8, "x": x, "y": y},
        "targets": [
            {
                "expr": 'fda_memory_usage_percent',
                "refId": "A",
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 75, "color": "yellow"},
                        {"value": 90, "color": "red"},
                    ],
                },
            },
        },
    }


def create_disk_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create disk usage panel."""
    return {
        "id": panel_id,
        "title": "Disk Usage (%)",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 8, "x": x, "y": y},
        "targets": [
            {
                "expr": 'fda_disk_usage_percent',
                "refId": "A",
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": 0, "color": "green"},
                        {"value": 85, "color": "yellow"},
                        {"value": 95, "color": "red"},
                    ],
                },
            },
        },
    }


def create_slo_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create SLO compliance panel."""
    return {
        "id": panel_id,
        "title": "SLO Compliance",
        "type": "table",
        "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
        "targets": [
            {
                "expr": 'histogram_quantile(0.95, rate(fda_request_duration_seconds_bucket[5m])) < 0.5',
                "legendFormat": "Latency p95 < 500ms",
                "refId": "A",
                "instant": True,
            },
            {
                "expr": 'rate(fda_requests_errors_total[5m]) / rate(fda_requests_total[5m]) < 0.01',
                "legendFormat": "Error rate < 1%",
                "refId": "B",
                "instant": True,
            },
            {
                "expr": 'rate(fda_cache_hits_total[5m]) / (rate(fda_cache_hits_total[5m]) + rate(fda_cache_misses_total[5m])) > 0.8',
                "legendFormat": "Cache hit rate > 80%",
                "refId": "C",
                "instant": True,
            },
        ],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {},
                    "indexByName": {},
                    "renameByName": {
                        "Value": "Compliant",
                    },
                },
            },
        ],
    }


def create_error_budget_panel(y: int, x: int, panel_id: int) -> Dict[str, Any]:
    """Create error budget panel."""
    return {
        "id": panel_id,
        "title": "Error Budget Remaining",
        "type": "stat",
        "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
        "targets": [
            {
                "expr": '(1 - rate(fda_requests_errors_total[30d]) / rate(fda_requests_total[30d])) * 100',
                "legendFormat": "Availability (%)",
                "refId": "A",
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 99.0,
                "max": 100.0,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"value": 99.0, "color": "red"},
                        {"value": 99.9, "color": "yellow"},
                        {"value": 99.95, "color": "green"},
                    ],
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Grafana API Integration
# ---------------------------------------------------------------------------

def upload_dashboard(dashboard: Dict[str, Any], grafana_url: str, api_key: str) -> None:
    """Upload dashboard to Grafana via API.

    Args:
        dashboard: Dashboard JSON
        grafana_url: Grafana base URL
        api_key: Grafana API key
    """
    import urllib.request
    import urllib.error

    url = f"{grafana_url.rstrip('/')}/api/dashboards/db"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(dashboard).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            logger.info("Dashboard uploaded successfully")
            logger.info("Dashboard URL: %s/d/%s", grafana_url, result.get("uid", ""))

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error("Failed to upload dashboard: HTTP %d - %s", e.code, error_body)
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Grafana dashboard for FDA Tools monitoring"
    )

    add_logging_args(parser)

    # Output options
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Output dashboard JSON to file"
    )

    # Grafana API options
    parser.add_argument(
        "--grafana-url",
        metavar="URL",
        help="Grafana base URL (e.g., http://localhost:3000)"
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="Grafana API key"
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        # Generate dashboard
        dashboard = create_dashboard()

        # Output to file
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(dashboard, f, indent=2)
            logger.info("Dashboard written to: %s", args.output)

        # Upload to Grafana
        if args.grafana_url and args.api_key:
            upload_dashboard(dashboard, args.grafana_url, args.api_key)

        # Print to stdout if no output specified
        if not args.output and not args.grafana_url:
            print(json.dumps(dashboard, indent=2))

        return 0

    except Exception as e:
        logger.error("Failed to generate dashboard: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
