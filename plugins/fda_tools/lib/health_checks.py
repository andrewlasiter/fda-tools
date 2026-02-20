#!/usr/bin/env python3
"""
Health Check Endpoints and Probes for FDA Tools.

Provides FastAPI-compatible health check endpoints for:
- Kubernetes liveness and readiness probes
- Load balancer health checks
- Monitoring system integration
- Dependency health verification

Usage:
    from fastapi import FastAPI
from fda_tools.lib.health_checks import register_health_endpoints

    app = FastAPI()
    register_health_endpoints(app)

    # Now available:
    # GET /health - Basic health check
    # GET /health/live - Liveness probe
    # GET /health/ready - Readiness probe
    # GET /health/startup - Startup probe
    # GET /metrics - Prometheus metrics endpoint
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    from fastapi import APIRouter, Response, status
    from fastapi.responses import PlainTextResponse
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    logger = logging.getLogger(__name__)
    logger.warning("FastAPI not available - health check endpoints disabled")

from .monitoring import get_health_checker, get_metrics_collector
from .metrics import get_metrics_reporter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Health Check Router
# ---------------------------------------------------------------------------

if _HAS_FASTAPI:
    router = APIRouter(tags=["Health & Monitoring"])

    @router.get("/health", summary="Basic health check")
    async def health_check():
        """Basic health check endpoint.

        Returns overall service health status with component details.
        Suitable for monitoring systems and manual checks.

        Returns:
            200 OK: Service is healthy or degraded
            503 Service Unavailable: Service is unhealthy
        """
        checker = get_health_checker()
        result = checker.check()

        status_code = status.HTTP_200_OK
        if result.status == "unhealthy":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            content=result.to_dict(),
            status_code=status_code,
            media_type="application/json"
        )

    @router.get("/health/live", summary="Liveness probe")
    async def liveness_probe():
        """Kubernetes liveness probe endpoint.

        Indicates whether the application is running.
        Kubernetes will restart the pod if this fails.

        This is a lightweight check that only verifies the process is alive.

        Returns:
            200 OK: Application is alive
            503 Service Unavailable: Application should be restarted
        """
        try:
            # Very basic check - just verify we can respond
            # Don't fail on degraded performance, only on critical failures
            checker = get_health_checker()
            result = checker.check()

            # Only fail if critically unhealthy (memory/disk issues)
            critical_checks = ["memory", "disk", "process"]
            critical_failures = any(
                not result.checks.get(check, {}).get("healthy", False)
                for check in critical_checks
                if check in result.checks
            )

            if critical_failures:
                return Response(
                    content={"status": "unhealthy", "message": "Critical system failure"},
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    media_type="application/json"
                )

            return {
                "status": "alive",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("Liveness probe failed: %s", e)
            return Response(
                content={"status": "error", "message": str(e)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json"
            )

    @router.get("/health/ready", summary="Readiness probe")
    async def readiness_probe():
        """Kubernetes readiness probe endpoint.

        Indicates whether the application is ready to accept traffic.
        Kubernetes will remove the pod from service if this fails.

        This is a more comprehensive check than liveness.

        Returns:
            200 OK: Application is ready to serve traffic
            503 Service Unavailable: Application is not ready
        """
        try:
            checker = get_health_checker()
            result = checker.check_readiness()

            if result.status == "unhealthy":
                return Response(
                    content=result.to_dict(),
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    media_type="application/json"
                )

            return {
                "status": result.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": result.checks,
            }

        except Exception as e:
            logger.error("Readiness probe failed: %s", e)
            return Response(
                content={"status": "error", "message": str(e)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json"
            )

    @router.get("/health/startup", summary="Startup probe")
    async def startup_probe():
        """Kubernetes startup probe endpoint.

        Indicates whether the application has finished starting up.
        Kubernetes will wait for this before running liveness/readiness probes.

        Returns:
            200 OK: Application has started successfully
            503 Service Unavailable: Application is still starting
        """
        # For now, same as liveness probe
        # In a real application, you might check:
        # - Database migrations completed
        # - Cache warmup finished
        # - Configuration loaded
        return await liveness_probe()

    @router.get("/metrics", summary="Prometheus metrics endpoint", response_class=PlainTextResponse)
    async def metrics_endpoint():
        """Prometheus metrics endpoint.

        Exposes all collected metrics in Prometheus text format.
        Prometheus scrapes this endpoint to collect metrics.

        Returns:
            200 OK: Metrics in Prometheus text format
        """
        try:
            collector = get_metrics_collector()
            metrics_text = collector.export_prometheus()

            return PlainTextResponse(
                content=metrics_text,
                status_code=status.HTTP_200_OK,
                media_type="text/plain; version=0.0.4"
            )

        except Exception as e:
            logger.error("Failed to export metrics: %s", e)
            return PlainTextResponse(
                content=f"# Error exporting metrics: {e}\n",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @router.get("/metrics/json", summary="Metrics in JSON format")
    async def metrics_json_endpoint():
        """Metrics endpoint in JSON format.

        Provides metrics in JSON format for custom dashboards and integrations.

        Returns:
            200 OK: Metrics as JSON
        """
        try:
            reporter = get_metrics_reporter()
            metrics_json = reporter.export_metrics_json()

            return Response(
                content=metrics_json,
                status_code=status.HTTP_200_OK,
                media_type="application/json"
            )

        except Exception as e:
            logger.error("Failed to export JSON metrics: %s", e)
            return Response(
                content={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )

    @router.get("/metrics/slo", summary="SLO compliance report")
    async def slo_report_endpoint():
        """SLO compliance report endpoint.

        Provides detailed SLO compliance status and recent violations.

        Returns:
            200 OK: SLO report
        """
        try:
            reporter = get_metrics_reporter()
            slo_report = reporter.generate_slo_report()

            return Response(
                content=slo_report,
                status_code=status.HTTP_200_OK,
                media_type="application/json"
            )

        except Exception as e:
            logger.error("Failed to generate SLO report: %s", e)
            return Response(
                content={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )


# ---------------------------------------------------------------------------
# Registration Function
# ---------------------------------------------------------------------------

def register_health_endpoints(app) -> None:
    """Register health check endpoints with a FastAPI app.

    Args:
        app: FastAPI application instance
    """
    if not _HAS_FASTAPI:
        logger.warning("Cannot register health endpoints - FastAPI not available")
        return

    app.include_router(router)
    logger.info("Health check endpoints registered: /health, /health/live, /health/ready, /metrics")


# ---------------------------------------------------------------------------
# Standalone Health Check Server
# ---------------------------------------------------------------------------

def create_health_check_server(port: int = 8080, host: str = "0.0.0.0") -> Any:
    """Create a standalone health check server.

    Useful for sidecar containers or dedicated health check services.

    Args:
        port: Port to listen on
        host: Host to bind to

    Returns:
        FastAPI application instance
    """
    if not _HAS_FASTAPI:
        raise ImportError("FastAPI is required to create health check server")

    from fastapi import FastAPI

    app = FastAPI(
        title="FDA Tools Health Check Server",
        description="Health check and metrics endpoints for FDA Tools",
        version="1.0.0",
    )

    register_health_endpoints(app)

    return app


def run_health_check_server(port: int = 8080, host: str = "0.0.0.0") -> None:
    """Run standalone health check server.

    Args:
        port: Port to listen on
        host: Host to bind to
    """
    try:
        import uvicorn
    except ImportError:
        raise ImportError("uvicorn is required to run health check server")

    app = create_health_check_server(port, host)

    logger.info("Starting health check server on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "register_health_endpoints",
    "create_health_check_server",
    "run_health_check_server",
]

if _HAS_FASTAPI:
    __all__.append("router")
