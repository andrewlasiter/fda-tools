#!/usr/bin/env python3
"""
Standalone Metrics and Health Check Server for FDA Tools.

Provides dedicated endpoints for monitoring without coupling to the main application.
Useful for sidecar containers, service mesh integration, or standalone monitoring.

Usage:
    # Start metrics server on default port (8080)
    python3 metrics_server.py

    # Start on custom port
    python3 metrics_server.py --port 9090

    # Enable CORS for external access
    python3 metrics_server.py --cors

    # Run in background
    python3 metrics_server.py --daemon
"""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Add parent directory to path for lib imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:

from fda_tools.lib.health_checks import create_health_check_server
from fda_tools.lib.logging_config import setup_logging

logger = logging.getLogger(__name__)


def handle_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received signal %s, shutting down...", signum)
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Standalone metrics and health check server for FDA Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server on default port
  %(prog)s

  # Start on custom port
  %(prog)s --port 9090

  # Enable CORS for external access
  %(prog)s --cors

  # Run in background
  %(prog)s --daemon

Endpoints:
  GET  /health          - Basic health check
  GET  /health/live     - Kubernetes liveness probe
  GET  /health/ready    - Kubernetes readiness probe
  GET  /metrics         - Prometheus metrics (text format)
  GET  /metrics/json    - Metrics in JSON format
  GET  /metrics/slo     - SLO compliance report
        """
    )

    parser.add_argument(
        "--host",
        default=os.getenv("METRICS_SERVER_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("METRICS_SERVER_PORT", "8080")),
        help="Port to listen on (default: 8080)"
    )

    parser.add_argument(
        "--cors",
        action="store_true",
        help="Enable CORS for external access"
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (background process)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Run as daemon if requested
    if args.daemon:
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process exits
                print(f"Metrics server started as daemon (PID: {pid})")
                sys.exit(0)
        except OSError as e:
            logger.error("Failed to fork daemon process: %s", e)
            sys.exit(1)

    # Create and run server
    try:
        logger.info("Starting metrics server on %s:%d", args.host, args.port)

        # Import uvicorn here to avoid import errors if not installed
        try:
            import uvicorn
        except ImportError:
            logger.error("uvicorn is required to run metrics server")
            logger.error("Install with: pip install uvicorn")
            sys.exit(1)

        app = create_health_check_server(port=args.port, host=args.host)

        # Configure CORS if requested
        if args.cors:
            from fastapi.middleware.cors import CORSMiddleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            logger.info("CORS enabled for all origins")

        # Run server
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if args.verbose else "warning",
            access_log=args.verbose,
        )

    except Exception as e:
        logger.error("Failed to start metrics server: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
