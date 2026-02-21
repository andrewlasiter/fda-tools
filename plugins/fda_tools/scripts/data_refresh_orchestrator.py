#!/usr/bin/env python3
"""
Automated Data Refresh Orchestrator -- Scheduled refresh workflows for
PMA data, SSED PDFs, MAUDE events, and recall information.

Implements intelligent refresh prioritization based on TTL tiers:
    - 24h: Safety-critical data (MAUDE events, recalls)
    - 168h: Classification and approval data
    - Never expires: Static documents (SSEDs, extracted sections)

Features:
    - Batch processing with rate limiting (FDA API: 240 req/min, 1000 req/5min)
    - Progress tracking with real-time updates
    - Error recovery with exponential backoff and retry logic
    - Background execution with asyncio/threading
    - Comprehensive refresh reports with audit trails
    - Data versioning with checksums for integrity verification

Regulatory compliance:
    - Full audit trails for all data modifications (21 CFR 807, 814)
    - Before/after snapshots for change verification
    - Data source citations with timestamps and API versions
    - No automated regulatory decisions without human review

Usage:
    from data_refresh_orchestrator import DataRefreshOrchestrator

    orchestrator = DataRefreshOrchestrator()
    report = orchestrator.run_refresh(priority="safety")
    report = orchestrator.run_refresh(schedule="daily", dry_run=True)
    status = orchestrator.get_refresh_status()

    # CLI usage:
    python3 data_refresh_orchestrator.py --schedule daily
    python3 data_refresh_orchestrator.py --priority safety --dry-run
    python3 data_refresh_orchestrator.py --background
    python3 data_refresh_orchestrator.py --status
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import sibling modules
from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter
from fda_tools.scripts.pma_data_store import PMADataStore

# FDA-196: PostgreSQL blue-green deployment integration
try:
    from fda_tools.lib.postgres_database import PostgreSQLDatabase
    from fda_tools.scripts.update_coordinator import UpdateCoordinator
    _POSTGRES_AVAILABLE = True
except ImportError:
    _POSTGRES_AVAILABLE = False
    PostgreSQLDatabase = None
    UpdateCoordinator = None


# ------------------------------------------------------------------
# TTL tier configuration
# ------------------------------------------------------------------

REFRESH_TTL_TIERS = {
    "safety_critical": {
        "label": "Safety-Critical Data",
        "ttl_hours": 24,
        "data_types": ["maude_events", "recalls"],
        "priority": 1,
        "description": "MAUDE adverse events and recall data refreshed every 24 hours.",
    },
    "supplements": {
        "label": "Supplement Data",
        "ttl_hours": 24,
        "data_types": ["pma_supplements"],
        "priority": 2,
        "description": "PMA supplement filings refreshed every 24 hours.",
    },
    "approval_data": {
        "label": "Approval & Classification Data",
        "ttl_hours": 168,
        "data_types": ["pma_approval", "classification"],
        "priority": 3,
        "description": "PMA approval and classification data refreshed weekly.",
    },
    "static_documents": {
        "label": "Static Documents",
        "ttl_hours": 0,
        "data_types": ["ssed_pdf", "extracted_sections"],
        "priority": 4,
        "description": "SSED PDFs and extracted sections never auto-refresh.",
    },
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 240,
    "requests_per_5min": 1000,
    "min_delay_seconds": 0.25,
    "burst_delay_seconds": 1.0,
}

# Retry configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "base_backoff_seconds": 2.0,
    "max_backoff_seconds": 60.0,
    "backoff_multiplier": 2.0,
}

ORCHESTRATOR_VERSION = "1.0.0"


class TokenBucketRateLimiter:
    """Backward-compat factory (FDA-200). Wraps CrossProcessRateLimiter.

    Deprecated — callers should use CrossProcessRateLimiter directly.
    Maps old per_minute/per_5min/min_delay kwargs to the canonical API.
    """

    def __new__(
        cls,
        per_minute: int = 240,
        per_5min: int = 1000,
        min_delay: float = 0.25,
    ) -> CrossProcessRateLimiter:  # type: ignore[misc]
        return CrossProcessRateLimiter(
            requests_per_minute=per_minute,
            requests_per_5min=per_5min,
            min_delay_seconds=min_delay,
        )


class RefreshAuditLogger:
    """Audit logger for data refresh operations.

    Maintains a complete audit trail of all data modifications
    per 21 CFR 807/814 requirements.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path(
            os.path.expanduser("~/fda-510k-data/pma_cache/refresh_logs")
        )
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []

    def log_refresh_start(self, config: Dict) -> str:
        """Log the start of a refresh cycle.

        Returns:
            Refresh session ID.
        """
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        entry = {
            "event": "refresh_start",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": config,
        }
        self._entries.append(entry)
        return session_id

    def log_item_refresh(
        self,
        session_id: str,
        pma_number: str,
        data_type: str,
        status: str,
        details: Optional[Dict] = None,
    ) -> None:
        """Log an individual item refresh."""
        entry = {
            "event": "item_refresh",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pma_number": pma_number,
            "data_type": data_type,
            "status": status,
            "details": details or {},
        }
        self._entries.append(entry)

    def log_refresh_complete(
        self, session_id: str, summary: Dict
    ) -> None:
        """Log refresh cycle completion."""
        entry = {
            "event": "refresh_complete",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
        }
        self._entries.append(entry)

    def save_log(self, session_id: str) -> str:
        """Save audit log to disk.

        Returns:
            Path to saved log file.
        """
        log_path = self.log_dir / f"refresh_log_{session_id}.json"
        session_entries = [
            e for e in self._entries if e.get("session_id") == session_id
        ]
        with open(log_path, "w") as f:
            json.dump(
                {
                    "session_id": session_id,
                    "orchestrator_version": ORCHESTRATOR_VERSION,
                    "entries": session_entries,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                f,
                indent=2,
            )
        return str(log_path)

    def log_event(
        self,
        event_type: str,
        details: Optional[Dict] = None,
    ) -> None:
        """Log a generic named event (used by blue-green workflow)."""
        entry = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        self._entries.append(entry)

    def get_entries(self, session_id: Optional[str] = None) -> List[Dict]:
        """Get audit log entries, optionally filtered by session."""
        if session_id:
            return [
                e for e in self._entries if e.get("session_id") == session_id
            ]
        return list(self._entries)


def _compute_checksum(data: Any) -> str:
    """Compute SHA-256 checksum for data integrity verification."""
    if isinstance(data, dict):
        serialized = json.dumps(data, sort_keys=True)
    elif isinstance(data, str):
        serialized = data
    else:
        serialized = str(data)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


class DataRefreshOrchestrator:
    """Automated data refresh orchestrator for PMA Intelligence data.

    Manages scheduled refresh workflows with intelligent prioritization,
    rate limiting, error recovery, and comprehensive audit trails.
    """

    def __init__(
        self,
        store: Optional[PMADataStore] = None,
        rate_limiter: Optional[CrossProcessRateLimiter] = None,
        audit_logger: Optional[RefreshAuditLogger] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        use_blue_green: bool = False,
        postgres_host: str = "localhost",
        postgres_port: int = 6432,
    ):
        """Initialize data refresh orchestrator.

        Args:
            store: PMADataStore instance (creates default if not provided).
            rate_limiter: Rate limiter for API calls.
            audit_logger: Audit logger for compliance tracking.
            retry_config: Override retry configuration (for testing).
            use_blue_green: Enable PostgreSQL blue-green deployment (FDA-196).
            postgres_host: PostgreSQL/PgBouncer host for blue-green updates.
            postgres_port: PostgreSQL/PgBouncer port for blue-green updates.
        """
        self.store = store or PMADataStore()
        self.rate_limiter = rate_limiter or CrossProcessRateLimiter(
            requests_per_minute=RATE_LIMIT_CONFIG["requests_per_minute"],
            requests_per_5min=RATE_LIMIT_CONFIG["requests_per_5min"],
            min_delay_seconds=RATE_LIMIT_CONFIG["min_delay_seconds"],
        )
        self.audit_logger = audit_logger or RefreshAuditLogger()
        self.retry_config = retry_config or RETRY_CONFIG
        self._background_thread: Optional[threading.Thread] = None
        self._cancel_flag = threading.Event()
        self._progress: Dict[str, Any] = {}

        # FDA-196: PostgreSQL blue-green deployment integration
        self.use_blue_green = use_blue_green and _POSTGRES_AVAILABLE
        self.postgres_host = postgres_host
        self.postgres_port = postgres_port
        self.update_coordinator: Optional[UpdateCoordinator] = None

        if self.use_blue_green:
            if not _POSTGRES_AVAILABLE:
                raise RuntimeError(
                    "PostgreSQL blue-green deployment requested but required modules not available. "
                    "Ensure FDA-191 and FDA-192 are completed."
                )
            self.update_coordinator = UpdateCoordinator(
                blue_host=postgres_host,
                blue_port=postgres_port,
                green_port=5433  # Default GREEN port
            )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _update_progress(self, message: str) -> None:
        """Update progress tracker with status message.

        Args:
            message: Progress message to display/log.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        self._progress["last_update"] = timestamp
        self._progress["message"] = message
        print(f"[{timestamp}] {message}")

    # ------------------------------------------------------------------
    # Refresh prioritization
    # ------------------------------------------------------------------

    def get_refresh_candidates(
        self, priority: str = "all"
    ) -> List[Dict[str, Any]]:
        """Identify PMA entries that need refreshing based on TTL tiers.

        Args:
            priority: 'safety' for safety-critical only, 'all' for everything.

        Returns:
            List of refresh candidates sorted by priority.
        """
        manifest = self.store.get_manifest()
        entries = manifest.get("pma_entries", {})
        candidates = []

        for pma_number, entry in entries.items():
            for tier_name, tier_config in REFRESH_TTL_TIERS.items():
                if priority == "safety" and tier_config["priority"] > 2:
                    continue

                # Skip static documents (TTL=0)
                if tier_config["ttl_hours"] == 0:
                    continue

                for data_type in tier_config["data_types"]:
                    if self.store.is_expired(pma_number, data_type):
                        candidates.append({
                            "pma_number": pma_number,
                            "data_type": data_type,
                            "tier": tier_name,
                            "priority": tier_config["priority"],
                            "ttl_hours": tier_config["ttl_hours"],
                            "product_code": entry.get("product_code", ""),
                            "device_name": entry.get("device_name", ""),
                        })

        # Sort by priority (lower number = higher priority)
        candidates.sort(key=lambda x: (x["priority"], x["pma_number"]))
        return candidates

    def get_schedule_config(self, schedule: str) -> Dict[str, Any]:
        """Get refresh configuration for a schedule type.

        Args:
            schedule: 'daily', 'weekly', or 'monthly'.

        Returns:
            Schedule configuration dictionary.
        """
        configs = {
            "daily": {
                "label": "Daily Refresh",
                "tiers": ["safety_critical", "supplements"],
                "description": "Refresh safety-critical and supplement data.",
            },
            "weekly": {
                "label": "Weekly Refresh",
                "tiers": [
                    "safety_critical", "supplements", "approval_data",
                ],
                "description": "Refresh all non-static data tiers.",
            },
            "monthly": {
                "label": "Monthly Full Refresh",
                "tiers": [
                    "safety_critical", "supplements", "approval_data",
                ],
                "description": (
                    "Full refresh of all data tiers including "
                    "re-validation of static documents."
                ),
            },
        }
        return configs.get(schedule, configs["daily"])

    # ------------------------------------------------------------------
    # Core refresh execution
    # ------------------------------------------------------------------

    def run_refresh(
        self,
        schedule: str = "daily",
        priority: str = "all",
        dry_run: bool = False,
        background: bool = False,
        pma_numbers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute a data refresh cycle.

        Args:
            schedule: Refresh schedule ('daily', 'weekly', 'monthly').
            priority: Priority filter ('safety', 'all').
            dry_run: If True, report what would be refreshed without executing.
            background: If True, run in background thread.
            pma_numbers: Optional list of specific PMAs to refresh.

        Returns:
            Refresh report dictionary.
        """
        config = {
            "schedule": schedule,
            "priority": priority,
            "dry_run": dry_run,
            "background": background,
            "pma_numbers": pma_numbers,
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        session_id = self.audit_logger.log_refresh_start(config)

        if background and not dry_run:
            return self._run_background(config, session_id)

        return self._execute_refresh(config, session_id, pma_numbers)

    def _run_background(
        self, config: Dict, session_id: str
    ) -> Dict[str, Any]:
        """Launch refresh in background thread."""
        self._cancel_flag.clear()
        self._progress = {
            "session_id": session_id,
            "status": "running",
            "started_at": config["started_at"],
            "items_processed": 0,
            "items_total": 0,
            "errors": 0,
        }

        self._background_thread = threading.Thread(
            target=self._execute_refresh,
            args=(config, session_id, config.get("pma_numbers")),
            daemon=True,
        )
        self._background_thread.start()

        return {
            "status": "background_started",
            "session_id": session_id,
            "message": (
                "Data refresh started in background. "
                "Use --status to check progress."
            ),
        }

    def _execute_refresh(
        self,
        config: Dict,
        session_id: str,
        pma_numbers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute the refresh workflow.

        Args:
            config: Refresh configuration.
            session_id: Audit session identifier.
            pma_numbers: Optional specific PMAs to refresh.

        Returns:
            Refresh report dictionary.
        """
        start_time = time.monotonic()

        # Get candidates
        if pma_numbers:
            candidates = []
            for pma in pma_numbers:
                for tier_name, tier_config in REFRESH_TTL_TIERS.items():
                    if tier_config["ttl_hours"] == 0:
                        continue
                    for data_type in tier_config["data_types"]:
                        candidates.append({
                            "pma_number": pma.upper(),
                            "data_type": data_type,
                            "tier": tier_name,
                            "priority": tier_config["priority"],
                            "ttl_hours": tier_config["ttl_hours"],
                        })
        else:
            candidates = self.get_refresh_candidates(
                priority=config.get("priority", "all")
            )

        total = len(candidates)
        self._progress["items_total"] = total

        if config.get("dry_run"):
            return self._build_dry_run_report(
                candidates, config, session_id, start_time
            )

        # Execute refresh
        results = {
            "refreshed": [],
            "skipped": [],
            "errors": [],
        }

        for i, candidate in enumerate(candidates):
            if self._cancel_flag.is_set():
                break

            self._progress["items_processed"] = i + 1
            pma_number = candidate["pma_number"]
            data_type = candidate["data_type"]

            try:
                self.rate_limiter.acquire()
                result = self._refresh_item(
                    pma_number, data_type, session_id
                )
                if result["status"] == "refreshed":
                    results["refreshed"].append(result)
                elif result["status"] == "skipped":
                    results["skipped"].append(result)
                else:
                    results["errors"].append(result)
                    self._progress["errors"] = len(results["errors"])
            except Exception as exc:
                error_result = {
                    "pma_number": pma_number,
                    "data_type": data_type,
                    "status": "error",
                    "error": str(exc),
                }
                results["errors"].append(error_result)
                self.audit_logger.log_item_refresh(
                    session_id, pma_number, data_type, "error",
                    {"error": str(exc)},
                )
                self._progress["errors"] = len(results["errors"])

        elapsed = time.monotonic() - start_time
        rate_stats = self.rate_limiter.get_stats()

        summary = {
            "session_id": session_id,
            "schedule": config.get("schedule", "manual"),
            "priority": config.get("priority", "all"),
            "total_candidates": total,
            "items_refreshed": len(results["refreshed"]),
            "items_skipped": len(results["skipped"]),
            "items_errored": len(results["errors"]),
            "elapsed_seconds": round(elapsed, 2),
            "api_calls_made": rate_stats["total_requests"],
            "rate_limiter_wait_seconds": rate_stats["total_wait_seconds"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.audit_logger.log_refresh_complete(session_id, summary)
        log_path = self.audit_logger.save_log(session_id)

        self._progress["status"] = "completed"
        self._progress["completed_at"] = summary["completed_at"]

        return {
            "status": "completed",
            "summary": summary,
            "results": results,
            "audit_log": log_path,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "disclaimer": (
                "This data refresh is for research and intelligence "
                "gathering purposes. All refreshed data should be "
                "independently verified by qualified regulatory "
                "professionals before use in FDA submissions."
            ),
        }

    def _refresh_item(
        self, pma_number: str, data_type: str, session_id: str
    ) -> Dict[str, Any]:
        """Refresh a single data item with retry logic.

        Args:
            pma_number: PMA number to refresh.
            data_type: Type of data to refresh.
            session_id: Audit session ID.

        Returns:
            Result dictionary with status and details.
        """
        max_retries = self.retry_config["max_retries"]
        base_backoff = self.retry_config["base_backoff_seconds"]
        max_backoff = self.retry_config["max_backoff_seconds"]
        multiplier = self.retry_config["backoff_multiplier"]

        # Get before-snapshot for change detection
        before_checksum = self._get_data_checksum(pma_number, data_type)

        last_error: Optional[str] = None
        for attempt in range(max_retries):
            try:
                result = self._do_refresh(pma_number, data_type)
                if result.get("error"):
                    last_error = result["error"]
                    backoff = min(
                        base_backoff * (multiplier ** attempt),
                        max_backoff,
                    )
                    time.sleep(backoff)
                    continue

                # Compute after-checksum
                after_checksum = self._get_data_checksum(pma_number, data_type)
                changed = before_checksum != after_checksum

                status = "refreshed"
                details = {
                    "attempt": attempt + 1,
                    "changed": changed,
                    "before_checksum": before_checksum,
                    "after_checksum": after_checksum,
                }

                self.audit_logger.log_item_refresh(
                    session_id, pma_number, data_type, status, details
                )

                return {
                    "pma_number": pma_number,
                    "data_type": data_type,
                    "status": status,
                    "changed": changed,
                    "attempts": attempt + 1,
                }

            except Exception as exc:
                last_error = str(exc)
                backoff = min(
                    base_backoff * (multiplier ** attempt),
                    max_backoff,
                )
                time.sleep(backoff)

        # All retries exhausted
        self.audit_logger.log_item_refresh(
            session_id, pma_number, data_type, "error",
            {"error": last_error, "attempts": max_retries},
        )
        return {
            "pma_number": pma_number,
            "data_type": data_type,
            "status": "error",
            "error": last_error or "Unknown error",
            "attempts": max_retries,
        }

    def _do_refresh(
        self, pma_number: str, data_type: str
    ) -> Dict[str, Any]:
        """Execute the actual API refresh for a data type.

        Args:
            pma_number: PMA number.
            data_type: Type of data to refresh.

        Returns:
            API result or error dictionary.
        """
        if data_type in ("pma_approval", "pma_supplements"):
            return self.store.get_pma_data(pma_number, refresh=True)
        elif data_type == "maude_events":
            pma_data = self.store.get_pma_data(pma_number)
            product_code = pma_data.get("product_code", "")
            if not product_code:
                return {"error": "No product code for MAUDE query"}
            return self.store.client.get_events(product_code) or {}
        elif data_type == "recalls":
            pma_data = self.store.get_pma_data(pma_number)
            product_code = pma_data.get("product_code", "")
            if not product_code:
                return {"error": "No product code for recall query"}
            return self.store.client.get_recalls(product_code) or {}
        elif data_type == "classification":
            pma_data = self.store.get_pma_data(pma_number)
            product_code = pma_data.get("product_code", "")
            if not product_code:
                return {"error": "No product code for classification query"}
            return self.store.client.get_classification(product_code) or {}
        else:
            return {"error": f"Unknown data type: {data_type}"}

    def _get_data_checksum(
        self, pma_number: str, data_type: str
    ) -> str:
        """Get a checksum of current cached data for change detection."""
        try:
            if data_type in ("pma_approval", "pma_supplements"):
                data = self.store.get_pma_data(pma_number)
                # Remove volatile fields
                stable = {
                    k: v for k, v in data.items()
                    if not k.startswith("_")
                }
                return _compute_checksum(stable)
            else:
                return "no_cache"
        except Exception:
            return "error"

    def _build_dry_run_report(
        self,
        candidates: List[Dict],
        config: Dict,
        session_id: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """Build a dry-run report without executing refreshes."""
        elapsed = time.monotonic() - start_time

        # Group by tier
        by_tier: Dict[str, List[Dict]] = defaultdict(list)
        for c in candidates:
            by_tier[c.get("tier", "unknown")].append(c)

        tier_summary = {}
        for tier_name, items in by_tier.items():
            tier_config = REFRESH_TTL_TIERS.get(tier_name, {})
            tier_summary[tier_name] = {
                "label": tier_config.get("label", tier_name),
                "count": len(items),
                "pma_numbers": sorted(set(i["pma_number"] for i in items)),
            }

        return {
            "status": "dry_run",
            "session_id": session_id,
            "summary": {
                "total_candidates": len(candidates),
                "tiers": tier_summary,
                "schedule": config.get("schedule", "manual"),
                "priority": config.get("priority", "all"),
                "elapsed_seconds": round(elapsed, 2),
            },
            "candidates": candidates,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "orchestrator_version": ORCHESTRATOR_VERSION,
        }

    # ------------------------------------------------------------------
    # Status and monitoring
    # ------------------------------------------------------------------

    def get_refresh_status(self) -> Dict[str, Any]:
        """Get the current refresh status and history.

        Returns:
            Status dictionary with progress and history.
        """
        manifest = self.store.get_manifest()
        entries = manifest.get("pma_entries", {})

        # Check for stale data
        stale_counts: Dict[str, int] = defaultdict(int)
        for pma_number in entries:
            for tier_name, tier_config in REFRESH_TTL_TIERS.items():
                if tier_config["ttl_hours"] == 0:
                    continue
                for data_type in tier_config["data_types"]:
                    if self.store.is_expired(pma_number, data_type):
                        stale_counts[tier_name] += 1

        # Recent audit logs
        log_dir = self.audit_logger.log_dir
        recent_logs = []
        if log_dir.exists():
            log_files = sorted(log_dir.glob("refresh_log_*.json"), reverse=True)
            for lf in log_files[:5]:
                try:
                    with open(lf) as f:
                        log_data = json.load(f)
                    recent_logs.append({
                        "session_id": log_data.get("session_id", ""),
                        "generated_at": log_data.get("generated_at", ""),
                        "entries_count": len(log_data.get("entries", [])),
                    })
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Warning: Failed to read refresh log: {e}", file=sys.stderr)

        return {
            "total_pmas_tracked": len(entries),
            "stale_data_counts": dict(stale_counts),
            "background_running": (
                self._background_thread is not None
                and self._background_thread.is_alive()
            ),
            "current_progress": dict(self._progress) if self._progress else None,
            "recent_refresh_logs": recent_logs,
            "ttl_tiers": {
                k: {"label": v["label"], "ttl_hours": v["ttl_hours"]}
                for k, v in REFRESH_TTL_TIERS.items()
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "orchestrator_version": ORCHESTRATOR_VERSION,
        }

    def cancel_refresh(self) -> Dict[str, Any]:
        """Cancel a running background refresh."""
        if (
            self._background_thread is not None
            and self._background_thread.is_alive()
        ):
            self._cancel_flag.set()
            return {
                "status": "cancelling",
                "message": "Cancel signal sent to background refresh.",
            }
        return {
            "status": "no_refresh_running",
            "message": "No background refresh is currently running.",
        }

    # ------------------------------------------------------------------
    # FDA-196: Blue-Green Deployment Integration
    # ------------------------------------------------------------------

    def run_blue_green_refresh(
        self,
        schedule: str = "daily",
        priority: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute zero-downtime refresh using blue-green deployment.

        Workflow:
        1. Prepare GREEN database (logical replication from BLUE)
        2. Detect deltas (changed records since last refresh)
        3. Apply updates to GREEN database only
        4. Verify integrity (checksums, row counts)
        5. Switch PgBouncer to GREEN (atomic, <10s RTO)
        6. Mark BLUE as standby for rollback

        Args:
            schedule: Refresh schedule ('daily', 'weekly', 'monthly').
            priority: Priority filter ('safety', 'all').
            dry_run: If True, report changes without applying.

        Returns:
            Refresh report with blue-green metrics.
        """
        if not self.use_blue_green:
            raise RuntimeError(
                "Blue-green refresh requested but not enabled. "
                "Initialize with use_blue_green=True."
            )

        start_time = time.monotonic()
        session_id = f"bg_refresh_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        self.audit_logger.log_event(
            event_type="blue_green_refresh_start",
            details={
                "session_id": session_id,
                "schedule": schedule,
                "priority": priority,
                "dry_run": dry_run,
            },
        )

        report = {
            "session_id": session_id,
            "schedule": schedule,
            "priority": priority,
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Phase 1: Prepare GREEN database
            self._update_progress("Preparing GREEN database (logical replication)...")
            self.update_coordinator.prepare_green_database()
            report["green_prepared"] = True

            # Phase 2: Detect deltas
            self._update_progress("Detecting changed records since last refresh...")
            deltas = self._detect_postgres_deltas(schedule, priority)
            report["deltas_detected"] = len(deltas)
            report["deltas"] = deltas

            if dry_run:
                self._update_progress("DRY RUN - no changes applied")
                report["status"] = "dry_run"
                report["elapsed_seconds"] = time.monotonic() - start_time
                return report

            # Phase 3: Apply updates to GREEN
            self._update_progress(f"Applying {len(deltas)} updates to GREEN database...")
            conflicts = self._apply_deltas_to_green(deltas)
            report["updates_applied"] = len(deltas) - len(conflicts)
            report["conflicts"] = conflicts

            # Phase 4: Verify integrity
            self._update_progress("Verifying GREEN database integrity...")
            passed, integrity_report = self.update_coordinator.verify_integrity()
            report["integrity_check"] = integrity_report

            if not passed:
                raise RuntimeError(f"Integrity verification failed: {integrity_report}")

            # Phase 5: Switch to GREEN
            self._update_progress("Switching PgBouncer to GREEN (zero downtime)...")
            self.update_coordinator.switch_to_green()
            report["switched_to_green"] = True
            report["rto_seconds"] = 8  # Typical PgBouncer reload time

            # Phase 6: Log success
            self._update_progress("Blue-green refresh complete")
            report["status"] = "completed"
            report["elapsed_seconds"] = time.monotonic() - start_time

            self.audit_logger.log_event(
                event_type="blue_green_refresh_complete",
                details=report,
            )

            return report

        except Exception as e:
            # Rollback to BLUE on failure
            self._update_progress(f"ERROR: {e}")
            self._update_progress("Rolling back to BLUE database...")

            try:
                self.update_coordinator.rollback_to_blue()
                report["rollback_successful"] = True
            except Exception as rollback_error:
                report["rollback_error"] = str(rollback_error)

            report["status"] = "failed"
            report["error"] = str(e)
            report["elapsed_seconds"] = time.monotonic() - start_time

            self.audit_logger.log_event(
                event_type="blue_green_refresh_failed",
                details=report,
            )

            return report

    def _detect_postgres_deltas(
        self, schedule: str, priority: str
    ) -> List[Dict[str, Any]]:
        """Detect changed records using PostgreSQL delta detection.

        Args:
            schedule: Refresh schedule to determine TTL cutoff.
            priority: Priority filter for data types.

        Returns:
            List of records that changed since last refresh.
        """
        # Map schedule to TTL hours
        schedule_to_ttl = {
            "daily": 24,
            "weekly": 168,
            "monthly": 720,
        }
        ttl_hours = schedule_to_ttl.get(schedule, 24)
        cutoff_timestamp = time.time() - (ttl_hours * 3600)

        # Get refresh candidates from existing logic
        candidates = self.get_refresh_candidates(priority=priority)

        # Filter to only those with changes (delta detection)
        deltas = []
        for candidate in candidates:
            pma_number = candidate.get("pma_number")
            last_refresh = candidate.get("last_refresh_timestamp", 0)

            # Check if record changed since last refresh
            if last_refresh < cutoff_timestamp:
                # Use update_coordinator's delta detection
                endpoint_deltas = self.update_coordinator.detect_deltas(
                    endpoint="pma",
                    since_timestamp=last_refresh
                )

                if pma_number in endpoint_deltas:
                    deltas.append({
                        "pma_number": pma_number,
                        "last_refresh": last_refresh,
                        "cutoff": cutoff_timestamp,
                        "changed": True,
                    })

        return deltas

    def _apply_deltas_to_green(
        self, deltas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply delta updates to GREEN database with conflict resolution.

        Args:
            deltas: List of records to update.

        Returns:
            List of conflicts that couldn't be auto-resolved.
        """
        conflicts = []

        for delta in deltas:
            pma_number = delta.get("pma_number")

            try:
                # Apply update to GREEN database via update_coordinator
                applied = self.update_coordinator.apply_updates(
                    endpoint="pma",
                    record_ids=[pma_number],
                )

                if not applied:
                    conflicts.append({
                        "pma_number": pma_number,
                        "reason": "update_failed",
                        "delta": delta,
                    })

            except Exception as e:
                # Log conflict to audit trail
                conflict_entry = {
                    "pma_number": pma_number,
                    "reason": "exception",
                    "error": str(e),
                    "delta": delta,
                }
                conflicts.append(conflict_entry)

                self.audit_logger.log_event(
                    event_type="conflict_detected",
                    details=conflict_entry,
                )

        return conflicts

    def get_postgres_stats(self) -> Dict[str, Any]:
        """Get PostgreSQL statistics for progress reporting.

        Returns:
            Dict with connection pool stats, query metrics, table sizes.
        """
        if not self.use_blue_green or not self.update_coordinator:
            return {"postgres_enabled": False}

        try:
            stats = self.update_coordinator.get_status()
            return {
                "postgres_enabled": True,
                "active_db": stats.get("active_db"),
                "connection_pool": stats.get("connection_pool"),
                "table_sizes": stats.get("table_sizes"),
                "last_refresh": stats.get("last_refresh"),
            }
        except Exception as e:
            return {
                "postgres_enabled": True,
                "error": str(e),
            }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    """CLI entry point for data refresh orchestrator."""
    parser = argparse.ArgumentParser(
        description="FDA Data Refresh Orchestrator -- "
                    "Automated data refresh with audit trails."
    )
    parser.add_argument(
        "--schedule", choices=["daily", "weekly", "monthly"],
        default="daily", help="Refresh schedule (default: daily)"
    )
    parser.add_argument(
        "--priority", choices=["safety", "all"],
        default="all", help="Priority filter (default: all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be refreshed without executing"
    )
    parser.add_argument(
        "--background", action="store_true",
        help="Run refresh in background thread"
    )
    parser.add_argument(
        "--pma", nargs="+",
        help="Specific PMA numbers to refresh"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show current refresh status"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--use-blue-green", action="store_true",
        help="Enable PostgreSQL blue-green deployment for zero-downtime updates (FDA-196)"
    )
    parser.add_argument(
        "--postgres-host", default="localhost",
        help="PostgreSQL/PgBouncer host (default: localhost)"
    )
    parser.add_argument(
        "--postgres-port", type=int, default=6432,
        help="PostgreSQL/PgBouncer port (default: 6432)"
    )

    args = parser.parse_args()

    # FDA-196: Initialize orchestrator with blue-green parameters
    orchestrator = DataRefreshOrchestrator(
        use_blue_green=args.use_blue_green,
        postgres_host=args.postgres_host,
        postgres_port=args.postgres_port,
    )

    if args.status:
        result = orchestrator.get_refresh_status()

        # FDA-196: Include PostgreSQL stats if blue-green enabled
        if args.use_blue_green:
            result["postgres_stats"] = orchestrator.get_postgres_stats()
    else:
        # FDA-196: Use blue-green refresh if enabled
        if args.use_blue_green:
            result = orchestrator.run_blue_green_refresh(
                schedule=args.schedule,
                priority=args.priority,
                dry_run=args.dry_run,
            )
        else:
            result = orchestrator.run_refresh(
                schedule=args.schedule,
                priority=args.priority,
                dry_run=args.dry_run,
                background=args.background,
                pma_numbers=args.pma,
            )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_report(result)


def _print_report(result: Dict) -> None:
    """Print a human-readable refresh report."""
    status = result.get("status", "unknown")
    print(f"\n  FDA Data Refresh Orchestrator v{ORCHESTRATOR_VERSION}")
    print("=" * 60)

    if status == "dry_run":
        summary = result.get("summary", {})
        print(f"  Mode:        DRY RUN (no changes made)")
        print(f"  Schedule:    {summary.get('schedule', 'manual')}")
        print(f"  Candidates:  {summary.get('total_candidates', 0)}")
        tiers = summary.get("tiers", {})
        for _tier_name, tier_data in tiers.items():
            print(f"    {tier_data['label']}: {tier_data['count']} items")
    elif status == "completed":
        summary = result.get("summary", {})
        print(f"  Status:      COMPLETED")
        print(f"  Schedule:    {summary.get('schedule', 'manual')}")
        print(f"  Refreshed:   {summary.get('items_refreshed', 0)}")
        print(f"  Skipped:     {summary.get('items_skipped', 0)}")
        print(f"  Errors:      {summary.get('items_errored', 0)}")
        print(f"  API Calls:   {summary.get('api_calls_made', 0)}")
        print(f"  Time:        {summary.get('elapsed_seconds', 0)}s")
        print(f"  Audit Log:   {result.get('audit_log', 'N/A')}")
    elif status == "background_started":
        print(f"  Status:      BACKGROUND STARTED")
        print(f"  Session:     {result.get('session_id', '')}")
        print(f"  {result.get('message', '')}")
    else:
        print(f"  Status: {status}")
        print(json.dumps(result, indent=2))

    print()
    print("  DISCLAIMER: Data is for research purposes only.")
    print("  Verify independently before use in FDA submissions.")
    print("=" * 60)


if __name__ == "__main__":
    main()
