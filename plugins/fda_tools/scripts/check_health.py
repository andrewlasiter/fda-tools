#!/usr/bin/env python3
"""
Health Check Utility for FDA Tools.

Performs comprehensive health and readiness checks, suitable for:
- Kubernetes liveness/readiness probes
- Load balancer health checks
- CI/CD pipeline verification
- Monitoring system integration

Usage:
    # Basic health check (exit 0 if healthy, 1 if unhealthy)
    python3 check_health.py

    # Readiness check (stricter than liveness)
    python3 check_health.py --readiness

    # JSON output for monitoring systems
    python3 check_health.py --json

    # Detailed output
    python3 check_health.py --verbose

    # Check specific components
    python3 check_health.py --check cpu --check memory

    # Continuous monitoring
    python3 check_health.py --monitor --interval 30
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for lib imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:

from fda_tools.lib.monitoring import get_health_checker, HealthCheckResult
from fda_tools.lib.logging_config import setup_logging, add_logging_args

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Formatters
# ---------------------------------------------------------------------------

def format_text_output(result: HealthCheckResult, verbose: bool = False) -> str:
    """Format health check result as human-readable text.

    Args:
        result: Health check result
        verbose: Include detailed information

    Returns:
        Formatted text output
    """
    lines = []

    # Overall status
    status_symbol = {
        "healthy": "✓",
        "degraded": "⚠",
        "unhealthy": "✗",
    }.get(result.status, "?")

    lines.append(f"\n{status_symbol} Overall Status: {result.status.upper()}")
    lines.append(f"Timestamp: {result.timestamp.isoformat()}")
    lines.append("")

    # Individual checks
    lines.append("Component Health Checks:")
    lines.append("-" * 60)

    for name, check_result in result.checks.items():
        check_symbol = "✓" if check_result["healthy"] else "✗"
        lines.append(f"{check_symbol} {name.upper()}: {check_result['message']}")

        if verbose and check_result.get("details"):
            details = check_result["details"]
            for key, value in details.items():
                if isinstance(value, float):
                    lines.append(f"    {key}: {value:.2f}")
                else:
                    lines.append(f"    {key}: {value}")
            lines.append("")

    return "\n".join(lines)


def format_json_output(result: HealthCheckResult) -> str:
    """Format health check result as JSON.

    Args:
        result: Health check result

    Returns:
        JSON string
    """
    return json.dumps(result.to_dict(), indent=2, default=str)


def format_prometheus_output(result: HealthCheckResult) -> str:
    """Format health check result as Prometheus metrics.

    Args:
        result: Health check result

    Returns:
        Prometheus format metrics
    """
    lines = []

    # Overall health status (1 = healthy, 0 = unhealthy)
    health_value = 1 if result.status == "healthy" else 0
    lines.append(f"# HELP fda_health_status Overall health status (1=healthy, 0=unhealthy)")
    lines.append(f"# TYPE fda_health_status gauge")
    lines.append(f"fda_health_status {health_value}")
    lines.append("")

    # Individual component health
    lines.append(f"# HELP fda_component_health Component health status (1=healthy, 0=unhealthy)")
    lines.append(f"# TYPE fda_component_health gauge")

    for name, check_result in result.checks.items():
        health = 1 if check_result["healthy"] else 0
        lines.append(f'fda_component_health{{component="{name}"}} {health}')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Health Check Runner
# ---------------------------------------------------------------------------

def run_health_check(
    readiness: bool = False,
    specific_checks: Optional[List[str]] = None,
) -> HealthCheckResult:
    """Run health checks.

    Args:
        readiness: Run readiness check instead of health check
        specific_checks: List of specific checks to run (None = all)

    Returns:
        HealthCheckResult
    """
    health_checker = get_health_checker()

    if readiness:
        result = health_checker.check_readiness()
    else:
        result = health_checker.check()

    # Filter to specific checks if requested
    if specific_checks:
        result.checks = {
            name: check
            for name, check in result.checks.items()
            if name in specific_checks
        }

        # Recalculate overall status
        if all(check["healthy"] for check in result.checks.values()):
            result.status = "healthy"
        elif any(not check["healthy"] for check in result.checks.values()):
            result.status = "unhealthy"
        else:
            result.status = "degraded"

    return result


# ---------------------------------------------------------------------------
# Continuous Monitoring
# ---------------------------------------------------------------------------

def monitor_health(interval: int = 30, output_format: str = "text") -> None:
    """Continuously monitor health and print status.

    Args:
        interval: Check interval in seconds
        output_format: Output format (text, json, prometheus)
    """
    logger.info("Starting continuous health monitoring (interval: %d seconds)", interval)

    try:
        while True:
            result = run_health_check()

            # Clear screen for text output
            if output_format == "text":
                print("\033[2J\033[H")  # ANSI escape to clear screen

            # Print result
            if output_format == "json":
                print(format_json_output(result))
            elif output_format == "prometheus":
                print(format_prometheus_output(result))
            else:
                print(format_text_output(result, verbose=True))

            # Wait for next check
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Stopping health monitoring")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Health check utility for FDA Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic health check
  %(prog)s

  # Readiness check (stricter)
  %(prog)s --readiness

  # JSON output for monitoring
  %(prog)s --json

  # Check specific components
  %(prog)s --check cpu --check memory

  # Continuous monitoring
  %(prog)s --monitor --interval 30

Exit codes:
  0 - Healthy
  1 - Unhealthy or degraded
  2 - Error running check
        """
    )

    # Add logging args
    add_logging_args(parser)

    # Check type
    parser.add_argument(
        "--readiness",
        action="store_true",
        help="Run readiness check (stricter than liveness)"
    )

    # Specific checks
    parser.add_argument(
        "--check",
        action="append",
        metavar="NAME",
        dest="checks",
        help="Run specific check(s) only (can be repeated)"
    )

    # Output format
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Output as JSON"
    )
    format_group.add_argument(
        "--prometheus",
        action="store_const",
        const="prometheus",
        dest="format",
        help="Output as Prometheus metrics"
    )
    parser.set_defaults(format="text")

    # Monitoring mode
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Continuously monitor health"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Monitoring interval in seconds (default: 30)"
    )

    # Exit on failure
    parser.add_argument(
        "--fail-on-degraded",
        action="store_true",
        help="Exit with code 1 if status is degraded (not just unhealthy)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(
        verbose=args.verbose,
        quiet=args.quiet if not args.monitor else True,  # Quiet for monitor mode
    )

    try:
        if args.monitor:
            # Continuous monitoring mode
            monitor_health(interval=args.interval, output_format=args.format)
            return 0

        else:
            # Single check
            result = run_health_check(
                readiness=args.readiness,
                specific_checks=args.checks,
            )

            # Output result
            if args.format == "json":
                print(format_json_output(result))
            elif args.format == "prometheus":
                print(format_prometheus_output(result))
            else:
                print(format_text_output(result, verbose=args.verbose))

            # Determine exit code
            if result.status == "healthy":
                return 0
            elif result.status == "degraded" and not args.fail_on_degraded:
                return 0
            else:
                return 1

    except Exception as e:
        logger.error("Health check failed with error: %s", e, exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
