#!/usr/bin/env python3
"""
Metrics Exporter for Prometheus Integration.

Exports FDA Tools metrics in Prometheus format via:
- HTTP endpoint (/metrics) for Prometheus scraping
- File export for debugging
- Push gateway integration (optional)

Usage:
    # Start HTTP server for Prometheus scraping
    python3 export_metrics.py --port 9090

    # Export to file
    python3 export_metrics.py --output metrics.txt

    # Push to Prometheus push gateway
    python3 export_metrics.py --push-gateway http://pushgateway:9091
"""

import argparse
import logging
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

# Add parent directory to path for lib imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:

from fda_tools.lib.monitoring import get_metrics_collector
from fda_tools.lib.logging_config import setup_logging, add_logging_args

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP Server for Prometheus Scraping
# ---------------------------------------------------------------------------

class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves Prometheus metrics."""

    def do_GET(self):
        """Handle GET requests for metrics."""
        if self.path == "/metrics":
            try:
                metrics = get_metrics_collector()
                output = metrics.export_prometheus()

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(output)))
                self.end_headers()
                self.wfile.write(output.encode("utf-8"))

            except Exception as e:
                logger.error("Error exporting metrics: %s", e)
                self.send_error(500, f"Internal Server Error: {e}")

        elif self.path == "/health":
            # Simple health check
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK\n")

        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - - [%s] %s",
                   self.address_string(),
                   self.log_date_time_string(),
                   format % args)


def run_http_server(port: int = 9090, host: str = "0.0.0.0") -> None:
    """Run HTTP server to expose metrics for Prometheus scraping.

    Args:
        port: Port to listen on
        host: Host to bind to (default: all interfaces)
    """
    server = HTTPServer((host, port), MetricsHandler)

    logger.info("Starting metrics HTTP server on %s:%d", host, port)
    logger.info("Prometheus scrape endpoint: http://%s:%d/metrics", host, port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server")
        server.shutdown()


# ---------------------------------------------------------------------------
# File Export
# ---------------------------------------------------------------------------

def export_to_file(output_path: str) -> None:
    """Export metrics to a file.

    Args:
        output_path: Path to output file
    """
    metrics = get_metrics_collector()
    output = metrics.export_prometheus()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    logger.info("Metrics exported to: %s", output_path)
    logger.info("Total size: %d bytes", len(output))


# ---------------------------------------------------------------------------
# Push Gateway Integration
# ---------------------------------------------------------------------------

def push_to_gateway(gateway_url: str, job_name: str = "fda_tools") -> None:
    """Push metrics to Prometheus Push Gateway.

    Args:
        gateway_url: URL of push gateway (e.g., http://pushgateway:9091)
        job_name: Job name for the metrics
    """
    import urllib.request
    import urllib.error

    metrics = get_metrics_collector()
    output = metrics.export_prometheus()

    # Construct push URL
    url = f"{gateway_url.rstrip('/')}/metrics/job/{job_name}"

    try:
        req = urllib.request.Request(
            url,
            data=output.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "text/plain; version=0.0.4"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info("Successfully pushed metrics to gateway: %s", gateway_url)
            else:
                logger.error("Failed to push metrics: HTTP %d", response.status)

    except urllib.error.URLError as e:
        logger.error("Failed to push metrics to gateway: %s", e)
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export FDA Tools metrics in Prometheus format"
    )

    # Add logging args
    add_logging_args(parser)

    # Export mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--serve",
        action="store_true",
        help="Run HTTP server for Prometheus scraping"
    )
    mode_group.add_argument(
        "--output",
        metavar="FILE",
        help="Export metrics to file"
    )
    mode_group.add_argument(
        "--push-gateway",
        metavar="URL",
        help="Push metrics to Prometheus push gateway"
    )

    # Server options
    parser.add_argument(
        "--port",
        type=int,
        default=9090,
        help="HTTP server port (default: 9090)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP server host (default: 0.0.0.0)"
    )

    # Push gateway options
    parser.add_argument(
        "--job-name",
        default="fda_tools",
        help="Job name for push gateway (default: fda_tools)"
    )

    # Continuous push mode
    parser.add_argument(
        "--interval",
        type=int,
        metavar="SECONDS",
        help="Push metrics at interval (for push gateway mode)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        if args.serve:
            # Run HTTP server
            run_http_server(port=args.port, host=args.host)

        elif args.output:
            # Export to file
            export_to_file(args.output)

        elif args.push_gateway:
            # Push to gateway
            if args.interval:
                # Continuous push mode
                logger.info("Starting continuous push every %d seconds", args.interval)
                try:
                    while True:
                        push_to_gateway(args.push_gateway, args.job_name)
                        time.sleep(args.interval)
                except KeyboardInterrupt:
                    logger.info("Stopping continuous push")
            else:
                # Single push
                push_to_gateway(args.push_gateway, args.job_name)

    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
