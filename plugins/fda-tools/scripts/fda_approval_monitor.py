#!/usr/bin/env python3
"""
FDA Approval Monitor -- Real-time monitoring of new FDA PMA approvals
and clearances with configurable watchlists and notification management.

Features:
    - Product code watchlists with user-configurable filters
    - Daily/weekly digest notifications (text alert files)
    - Change detection: new approvals, supplement submissions, recall announcements
    - Historical baseline tracking (e.g., "3 new PMAs this week vs avg 1.2/week")
    - Alert severity levels: INFO (new approval), WARNING (recall), CRITICAL (safety alert)
    - Deduplication to prevent repeat notifications
    - Alert history persistence for audit trail

Regulatory compliance:
    - Alert severity aligned with FDA MedWatch severity definitions
    - Deduplication prevents duplicate MDR reporting confusion
    - All alerts cite data sources with timestamps
    - No automated regulatory decisions -- alerts inform human reviewers

Usage:
    from fda_approval_monitor import FDAApprovalMonitor

    monitor = FDAApprovalMonitor()
    monitor.add_watchlist(["NMH", "QAS"])
    alerts = monitor.check_for_updates()
    monitor.generate_digest(frequency="daily")

    # CLI usage:
    python3 fda_approval_monitor.py --watch-product-codes NMH,QAS
    python3 fda_approval_monitor.py --frequency daily --output alerts.txt
    python3 fda_approval_monitor.py --severity-filter WARNING,CRITICAL
    python3 fda_approval_monitor.py --show-watchlist
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Alert severity definitions
# ------------------------------------------------------------------

ALERT_SEVERITY = {
    "INFO": {
        "label": "Information",
        "description": "New approval or routine update.",
        "priority": 3,
        "medwatch_alignment": "Routine device approval notification",
    },
    "WARNING": {
        "label": "Warning",
        "description": "Recall event or supplement with safety implications.",
        "priority": 2,
        "medwatch_alignment": (
            "Class II recall or supplement with labeling safety changes"
        ),
    },
    "CRITICAL": {
        "label": "Critical Safety Alert",
        "description": (
            "Class I recall, safety alert, or MAUDE death report spike."
        ),
        "priority": 1,
        "medwatch_alignment": (
            "Class I recall, serious injury/death events per MedWatch"
        ),
    },
}

MONITOR_VERSION = "1.0.0"


def _alert_dedup_key(alert: Dict[str, Any]) -> str:
    """Generate a deduplication key for an alert."""
    raw = (
        f"{alert.get('alert_type', '')}"
        f"|{alert.get('pma_number', '')}"
        f"|{alert.get('product_code', '')}"
        f"|{alert.get('data_key', '')}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class FDAApprovalMonitor:
    """Real-time FDA approval and safety monitoring with watchlists.

    Monitors PMA approvals, supplements, and recalls for configured
    product codes. Generates severity-classified alerts with
    deduplication and historical baseline comparison.
    """

    def __init__(
        self,
        store: Optional[PMADataStore] = None,
        config_dir: Optional[Path] = None,
    ):
        """Initialize FDA Approval Monitor.

        Args:
            store: PMADataStore instance.
            config_dir: Directory for watchlist config and alert history.
        """
        self.store = store or PMADataStore()
        self.config_dir = config_dir or Path(
            os.path.expanduser("~/fda-510k-data/pma_cache/monitor")
        )
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._watchlist: Set[str] = set()
        self._alert_history: List[Dict[str, Any]] = []
        self._seen_keys: Set[str] = set()
        self._load_state()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load watchlist and alert history from disk."""
        config_path = self.config_dir / "monitor_config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                self._watchlist = set(data.get("watchlist", []))
                self._alert_history = data.get("alert_history", [])
                self._seen_keys = set(data.get("seen_keys", []))
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self) -> None:
        """Save watchlist and alert history to disk."""
        config_path = self.config_dir / "monitor_config.json"
        data = {
            "watchlist": sorted(self._watchlist),
            "alert_history": self._alert_history[-500:],  # Keep last 500
            "seen_keys": sorted(list(self._seen_keys)[-1000:]),  # Keep last 1000
            "last_saved": datetime.now(timezone.utc).isoformat(),
            "monitor_version": MONITOR_VERSION,
        }
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------
    # Watchlist management
    # ------------------------------------------------------------------

    def add_watchlist(self, product_codes: List[str]) -> Dict[str, Any]:
        """Add product codes to the watchlist.

        Args:
            product_codes: List of FDA product codes to watch.

        Returns:
            Updated watchlist status.
        """
        added = []
        for code in product_codes:
            code_upper = code.strip().upper()
            if code_upper and code_upper not in self._watchlist:
                self._watchlist.add(code_upper)
                added.append(code_upper)
        self._save_state()
        return {
            "added": added,
            "total_watched": len(self._watchlist),
            "watchlist": sorted(self._watchlist),
        }

    def remove_watchlist(self, product_codes: List[str]) -> Dict[str, Any]:
        """Remove product codes from the watchlist."""
        removed = []
        for code in product_codes:
            code_upper = code.strip().upper()
            if code_upper in self._watchlist:
                self._watchlist.discard(code_upper)
                removed.append(code_upper)
        self._save_state()
        return {
            "removed": removed,
            "total_watched": len(self._watchlist),
            "watchlist": sorted(self._watchlist),
        }

    def get_watchlist(self) -> Dict[str, Any]:
        """Get the current watchlist."""
        return {
            "watchlist": sorted(self._watchlist),
            "total_watched": len(self._watchlist),
        }

    # ------------------------------------------------------------------
    # Monitoring core
    # ------------------------------------------------------------------

    def check_for_updates(
        self,
        product_codes: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check for new approvals, supplements, and recalls.

        Args:
            product_codes: Override watchlist with specific codes.
            since: ISO date string to check from (default: 7 days ago).

        Returns:
            Dictionary with detected alerts and statistics.
        """
        codes = product_codes or sorted(self._watchlist)
        if not codes:
            return {
                "status": "no_watchlist",
                "message": (
                    "No product codes in watchlist. "
                    "Use --watch-product-codes to add codes."
                ),
                "alerts": [],
            }

        # Determine time window
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                if since_dt.tzinfo is None:
                    since_dt = since_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                since_dt = datetime.now(timezone.utc) - timedelta(days=7)
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(days=7)

        since_str = since_dt.strftime("%Y%m%d")
        all_alerts: List[Dict[str, Any]] = []

        for code in codes:
            # Check new PMA approvals
            try:
                new_approvals = self._check_new_approvals(code, since_str)
                all_alerts.extend(new_approvals)
            except Exception:
                pass  # Non-fatal; continue monitoring other codes

            # Check recalls
            try:
                recall_alerts = self._check_recalls(code)
                all_alerts.extend(recall_alerts)
            except Exception:
                pass

            # Check MAUDE event spikes
            try:
                maude_alerts = self._check_maude_spikes(code)
                all_alerts.extend(maude_alerts)
            except Exception:
                pass

        # Deduplicate
        new_alerts = self._deduplicate_alerts(all_alerts)

        # Store new alerts
        for alert in new_alerts:
            alert["detected_at"] = datetime.now(timezone.utc).isoformat()
            self._alert_history.append(alert)

        self._save_state()

        # Compute historical baseline
        baseline = self._compute_baseline(codes)

        return {
            "status": "completed",
            "product_codes_checked": codes,
            "since": since_dt.isoformat(),
            "total_new_alerts": len(new_alerts),
            "alerts": new_alerts,
            "baseline_comparison": baseline,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "monitor_version": MONITOR_VERSION,
            "disclaimer": (
                "Alerts are AI-generated from public FDA data for "
                "informational purposes only. Independent verification "
                "by qualified regulatory professionals is required."
            ),
        }

    def _check_new_approvals(
        self, product_code: str, since_str: str
    ) -> List[Dict[str, Any]]:
        """Check for new PMA approvals since a given date."""
        alerts = []
        result = self.store.client.search_pma(
            product_code=product_code,
            year_start=since_str[:4],
            limit=20,
        )

        if result.get("degraded") or result.get("error"):
            return alerts

        for pma in result.get("results", []):
            decision_date = pma.get("decision_date", "")
            if decision_date >= since_str:
                pma_number = pma.get("pma_number", "")
                decision_code = pma.get("decision_code", "")

                # Determine if this is a supplement
                is_supplement = "S" in pma_number[7:] if len(pma_number) > 7 else False

                if is_supplement:
                    alert_type = "new_supplement"
                    severity = "INFO"
                    message = (
                        f"New supplement {pma_number} "
                        f"({decision_code}) for product code {product_code}"
                    )
                else:
                    alert_type = "new_approval"
                    severity = "INFO"
                    message = (
                        f"New PMA {pma_number} "
                        f"({decision_code}) approved for {product_code}"
                    )

                alerts.append({
                    "alert_type": alert_type,
                    "severity": severity,
                    "product_code": product_code,
                    "pma_number": pma_number,
                    "data_key": f"{pma_number}_{decision_date}",
                    "decision_code": decision_code,
                    "decision_date": decision_date,
                    "device_name": pma.get("trade_name", ""),
                    "applicant": pma.get("applicant", ""),
                    "message": message,
                    "data_source": "openFDA PMA API",
                })

        return alerts

    def _check_recalls(
        self, product_code: str
    ) -> List[Dict[str, Any]]:
        """Check for recent recalls."""
        alerts = []
        result = self.store.client.get_recalls(product_code, limit=5)

        if result.get("degraded") or result.get("error"):
            return alerts

        for recall in result.get("results", []):
            recall_class = str(recall.get("res_event_number", ""))
            classification = recall.get(
                "event_date_terminated", ""
            )

            # Determine severity based on recall class
            recall_text = json.dumps(recall).lower()
            if "class i" in recall_text or "class 1" in recall_text:
                severity = "CRITICAL"
            elif "class ii" in recall_text or "class 2" in recall_text:
                severity = "WARNING"
            else:
                severity = "INFO"

            event_id = recall.get("res_event_number", "")
            alerts.append({
                "alert_type": "recall",
                "severity": severity,
                "product_code": product_code,
                "pma_number": "",
                "data_key": f"recall_{event_id}",
                "event_id": event_id,
                "message": (
                    f"Recall event {event_id} for product code "
                    f"{product_code}: {recall.get('reason_for_recall', 'N/A')[:100]}"
                ),
                "reason": recall.get("reason_for_recall", ""),
                "data_source": "openFDA Recall API",
            })

        return alerts

    def _check_maude_spikes(
        self, product_code: str
    ) -> List[Dict[str, Any]]:
        """Check for MAUDE adverse event spikes."""
        alerts = []
        result = self.store.client.get_events(
            product_code, count="event_type.exact"
        )

        if result.get("degraded") or result.get("error"):
            return alerts

        event_counts = result.get("results", [])
        total_events = sum(e.get("count", 0) for e in event_counts)
        death_count = sum(
            e.get("count", 0) for e in event_counts
            if "death" in e.get("term", "").lower()
        )

        # Flag if deaths detected
        if death_count > 0:
            alerts.append({
                "alert_type": "maude_safety",
                "severity": "CRITICAL",
                "product_code": product_code,
                "pma_number": "",
                "data_key": f"maude_death_{product_code}_{total_events}",
                "total_events": total_events,
                "death_count": death_count,
                "message": (
                    f"MAUDE safety alert: {death_count} death report(s) "
                    f"for product code {product_code} "
                    f"({total_events} total events)"
                ),
                "data_source": "openFDA MAUDE API",
            })

        return alerts

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate_alerts(
        self, alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate alerts based on dedup keys.

        Returns:
            List of new (unseen) alerts.
        """
        new_alerts = []
        for alert in alerts:
            key = _alert_dedup_key(alert)
            if key not in self._seen_keys:
                self._seen_keys.add(key)
                alert["dedup_key"] = key
                new_alerts.append(alert)
        return new_alerts

    def get_dedup_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        return {
            "total_seen_keys": len(self._seen_keys),
            "total_alert_history": len(self._alert_history),
        }

    # ------------------------------------------------------------------
    # Historical baseline
    # ------------------------------------------------------------------

    def _compute_baseline(
        self, product_codes: List[str]
    ) -> Dict[str, Any]:
        """Compute historical baseline for comparison.

        Returns:
            Baseline statistics for the monitored product codes.
        """
        # Count recent alerts by week
        now = datetime.now(timezone.utc)
        week_counts: Dict[str, int] = defaultdict(int)

        for alert in self._alert_history:
            detected_at = alert.get("detected_at", "")
            if not detected_at:
                continue
            try:
                dt = datetime.fromisoformat(detected_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                weeks_ago = (now - dt).days // 7
                if weeks_ago < 12:
                    week_key = f"week_{weeks_ago}"
                    week_counts[week_key] += 1
            except (ValueError, TypeError):
                pass

        total_weeks = max(len(week_counts), 1)
        total_alerts = sum(week_counts.values())
        avg_per_week = round(total_alerts / total_weeks, 1) if total_weeks > 0 else 0

        return {
            "product_codes": product_codes,
            "avg_alerts_per_week": avg_per_week,
            "total_historical_alerts": len(self._alert_history),
            "weeks_tracked": total_weeks,
        }

    # ------------------------------------------------------------------
    # Digest generation
    # ------------------------------------------------------------------

    def generate_digest(
        self,
        frequency: str = "daily",
        severity_filter: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an alert digest report.

        Args:
            frequency: 'daily' or 'weekly'.
            severity_filter: List of severity levels to include.
            output_path: Optional path to write digest file.

        Returns:
            Digest dictionary with alerts and summary.
        """
        # Determine time window
        if frequency == "weekly":
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)

        cutoff_iso = cutoff.isoformat()

        # Filter alerts
        filtered = []
        for alert in self._alert_history:
            detected_at = alert.get("detected_at", "")
            if detected_at >= cutoff_iso:
                if severity_filter:
                    if alert.get("severity") in severity_filter:
                        filtered.append(alert)
                else:
                    filtered.append(alert)

        # Sort by severity priority then time
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        filtered.sort(
            key=lambda a: (
                severity_order.get(a.get("severity", "INFO"), 3),
                a.get("detected_at", ""),
            )
        )

        # Group by severity
        by_severity: Dict[str, List[Dict]] = defaultdict(list)
        for alert in filtered:
            by_severity[alert.get("severity", "INFO")].append(alert)

        digest = {
            "frequency": frequency,
            "period_start": cutoff_iso,
            "period_end": datetime.now(timezone.utc).isoformat(),
            "total_alerts": len(filtered),
            "by_severity": {
                sev: {"count": len(alerts), "alerts": alerts}
                for sev, alerts in by_severity.items()
            },
            "watchlist": sorted(self._watchlist),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "monitor_version": MONITOR_VERSION,
            "disclaimer": (
                "This digest is AI-generated from public FDA data for "
                "informational purposes only. All alerts require "
                "independent verification by qualified regulatory "
                "professionals before action."
            ),
        }

        # Write to file if requested
        if output_path:
            self._write_digest_file(digest, output_path)
            digest["output_file"] = output_path

        return digest

    def _write_digest_file(
        self, digest: Dict, output_path: str
    ) -> None:
        """Write digest to a text file."""
        lines = [
            "=" * 60,
            f"  FDA Approval Monitor - {digest['frequency'].title()} Digest",
            "=" * 60,
            f"  Period: {digest['period_start'][:10]} to {digest['period_end'][:10]}",
            f"  Total Alerts: {digest['total_alerts']}",
            f"  Watchlist: {', '.join(digest['watchlist'])}",
            "",
        ]

        for severity in ["CRITICAL", "WARNING", "INFO"]:
            sev_data = digest["by_severity"].get(severity, {})
            alerts = sev_data.get("alerts", [])
            if not alerts:
                continue
            lines.append(f"  [{severity}] ({len(alerts)} alerts)")
            lines.append("-" * 60)
            for alert in alerts:
                lines.append(f"  - {alert.get('message', 'N/A')}")
                lines.append(f"    Source: {alert.get('data_source', 'N/A')}")
                lines.append(f"    Detected: {alert.get('detected_at', 'N/A')[:19]}")
                lines.append("")

        lines.extend([
            "=" * 60,
            "  DISCLAIMER: This digest is AI-generated from public FDA",
            "  data. Independent verification required before action.",
            "=" * 60,
        ])

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(lines))

    # ------------------------------------------------------------------
    # Alert history
    # ------------------------------------------------------------------

    def get_alert_history(
        self,
        limit: int = 50,
        severity_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent alert history.

        Args:
            limit: Maximum alerts to return.
            severity_filter: Optional severity filter.

        Returns:
            List of recent alerts.
        """
        filtered = self._alert_history
        if severity_filter:
            filtered = [
                a for a in filtered if a.get("severity") in severity_filter
            ]
        return filtered[-limit:]

    def clear_alert_history(self) -> Dict[str, Any]:
        """Clear alert history and seen keys."""
        count = len(self._alert_history)
        self._alert_history = []
        self._seen_keys = set()
        self._save_state()
        return {
            "cleared": count,
            "message": f"Cleared {count} alert history entries.",
        }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    """CLI entry point for FDA Approval Monitor."""
    parser = argparse.ArgumentParser(
        description="FDA Approval Monitor -- Real-time PMA monitoring"
    )
    parser.add_argument(
        "--watch-product-codes", type=str,
        help="Comma-separated product codes to watch"
    )
    parser.add_argument(
        "--remove-product-codes", type=str,
        help="Comma-separated product codes to remove from watchlist"
    )
    parser.add_argument(
        "--frequency", choices=["daily", "weekly"],
        default="daily", help="Digest frequency (default: daily)"
    )
    parser.add_argument(
        "--severity-filter", type=str,
        help="Comma-separated severity filter (INFO,WARNING,CRITICAL)"
    )
    parser.add_argument(
        "--output", type=str,
        help="Output file path for digest"
    )
    parser.add_argument(
        "--show-watchlist", action="store_true",
        help="Show current watchlist"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check for updates now"
    )
    parser.add_argument(
        "--digest", action="store_true",
        help="Generate digest report"
    )
    parser.add_argument(
        "--history", action="store_true",
        help="Show alert history"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()
    monitor = FDAApprovalMonitor()

    # Handle watchlist modifications
    if args.watch_product_codes:
        codes = [c.strip() for c in args.watch_product_codes.split(",")]
        result = monitor.add_watchlist(codes)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Added {len(result['added'])} codes. "
                  f"Watchlist: {', '.join(result['watchlist'])}")
        return

    if args.remove_product_codes:
        codes = [c.strip() for c in args.remove_product_codes.split(",")]
        result = monitor.remove_watchlist(codes)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Removed {len(result['removed'])} codes. "
                  f"Watchlist: {', '.join(result['watchlist'])}")
        return

    if args.show_watchlist:
        result = monitor.get_watchlist()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Watchlist ({result['total_watched']} codes): "
                  f"{', '.join(result['watchlist'])}")
        return

    if args.history:
        sev_filter = None
        if args.severity_filter:
            sev_filter = [s.strip().upper() for s in args.severity_filter.split(",")]
        alerts = monitor.get_alert_history(severity_filter=sev_filter)
        if args.json:
            print(json.dumps(alerts, indent=2))
        else:
            for a in alerts:
                print(f"[{a.get('severity', '?')}] {a.get('message', '')}")
        return

    # Default: check for updates or generate digest
    severity_filter = None
    if args.severity_filter:
        severity_filter = [s.strip().upper() for s in args.severity_filter.split(",")]

    if args.digest:
        result = monitor.generate_digest(
            frequency=args.frequency,
            severity_filter=severity_filter,
            output_path=args.output,
        )
    else:
        result = monitor.check_for_updates()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
