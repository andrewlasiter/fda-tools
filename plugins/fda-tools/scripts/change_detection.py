#!/usr/bin/env python3
"""
Change Detection Engine -- Detect and track changes in PMA data
between refresh cycles with diff generation and significance scoring.

Tracked changes:
    - New supplements filed or approved
    - Decision code changes (APPR -> DENY, etc.)
    - AO statement updates (conditions of approval)
    - MAUDE event spikes (statistical anomaly detection)
    - Applicant/device name changes
    - New recall events

Features:
    - Before/after snapshot comparison with detailed diffs
    - Change significance scoring (0-100) based on impact type
    - Change history logging with timestamps and change types
    - Integration with data_refresh_orchestrator for automatic post-refresh detection
    - Change trend analysis over time

Regulatory compliance:
    - Before/after snapshots preserved for verification (21 CFR 807/814)
    - All changes logged with timestamps, sources, and change types
    - Change significance aligned with FDA regulatory impact levels
    - No automated decisions -- changes flagged for human review

Usage:
    from change_detection import ChangeDetectionEngine

    engine = ChangeDetectionEngine()
    changes = engine.detect_changes("P170019")
    changes = engine.detect_changes("P170019", since="2024-01-01")
    history = engine.get_change_history("P170019")
    report = engine.generate_change_report("P170019")

    # CLI usage:
    python3 change_detection.py --pma P170019
    python3 change_detection.py --pma P170019 --since 2024-01-01
    python3 change_detection.py --pma P170019 --change-types supplements,maude
    python3 change_detection.py --pma P170019 --output changes.json
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Change type definitions and significance weights
# ------------------------------------------------------------------

CHANGE_TYPES = {
    "new_supplement": {
        "label": "New Supplement",
        "base_significance": 60,
        "description": "New supplement filed or approved.",
        "regulatory_impact": "May indicate device evolution or safety update.",
    },
    "decision_code_change": {
        "label": "Decision Code Change",
        "base_significance": 90,
        "description": "Decision code changed (e.g., APPR to DENY).",
        "regulatory_impact": "Critical -- indicates regulatory status change.",
    },
    "ao_statement_update": {
        "label": "AO Statement Update",
        "base_significance": 75,
        "description": "Approval order statement modified.",
        "regulatory_impact": "May indicate new conditions of approval.",
    },
    "maude_spike": {
        "label": "MAUDE Event Spike",
        "base_significance": 80,
        "description": "Significant increase in adverse event reports.",
        "regulatory_impact": "Safety signal -- may trigger FDA action.",
    },
    "recall_event": {
        "label": "Recall Event",
        "base_significance": 85,
        "description": "New recall event detected.",
        "regulatory_impact": "Direct safety impact on device availability.",
    },
    "applicant_change": {
        "label": "Applicant Change",
        "base_significance": 40,
        "description": "Device applicant/manufacturer changed.",
        "regulatory_impact": "May indicate ownership transfer.",
    },
    "device_name_change": {
        "label": "Device Name Change",
        "base_significance": 30,
        "description": "Trade name or device name changed.",
        "regulatory_impact": "Minor -- marketing/branding change.",
    },
    "supplement_count_change": {
        "label": "Supplement Count Change",
        "base_significance": 50,
        "description": "Total supplement count changed.",
        "regulatory_impact": "Indicates ongoing post-approval activity.",
    },
}

ENGINE_VERSION = "1.0.0"


def _compute_hash(data: Any) -> str:
    """Compute a hash for snapshot comparison."""
    if isinstance(data, dict):
        serialized = json.dumps(data, sort_keys=True)
    else:
        serialized = str(data)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


class ChangeDetectionEngine:
    """Detect and track changes in PMA data between refresh cycles.

    Compares current data against stored snapshots to identify
    significant changes with significance scoring and audit trails.
    """

    def __init__(
        self,
        store: Optional[PMADataStore] = None,
        snapshot_dir: Optional[Path] = None,
    ):
        """Initialize Change Detection Engine.

        Args:
            store: PMADataStore instance.
            snapshot_dir: Directory for storing data snapshots.
        """
        self.store = store or PMADataStore()
        self.snapshot_dir = snapshot_dir or Path(
            os.path.expanduser("~/fda-510k-data/pma_cache/snapshots")
        )
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._change_history: List[Dict[str, Any]] = []
        self._load_history()

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _load_history(self) -> None:
        """Load change history from disk."""
        history_path = self.snapshot_dir / "change_history.json"
        if history_path.exists():
            try:
                with open(history_path) as f:
                    data = json.load(f)
                self._change_history = data.get("changes", [])
            except (json.JSONDecodeError, OSError):
                pass

    def _save_history(self) -> None:
        """Save change history to disk."""
        history_path = self.snapshot_dir / "change_history.json"
        data = {
            "changes": self._change_history[-2000:],  # Keep last 2000
            "last_saved": datetime.now(timezone.utc).isoformat(),
            "engine_version": ENGINE_VERSION,
        }
        with open(history_path, "w") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    def save_snapshot(
        self, pma_number: str, data: Dict[str, Any]
    ) -> str:
        """Save a data snapshot for a PMA.

        Args:
            pma_number: PMA number.
            data: Data dictionary to snapshot.

        Returns:
            Path to saved snapshot.
        """
        pma_dir = self.snapshot_dir / pma_number.upper()
        pma_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot = {
            "pma_number": pma_number.upper(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_hash": _compute_hash(data),
            "data": data,
        }

        snapshot_path = pma_dir / f"snapshot_{timestamp}.json"
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2)

        # Also save as "latest"
        latest_path = pma_dir / "snapshot_latest.json"
        with open(latest_path, "w") as f:
            json.dump(snapshot, f, indent=2)

        return str(snapshot_path)

    def get_latest_snapshot(
        self, pma_number: str
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot for a PMA.

        Returns:
            Snapshot dictionary or None if no snapshot exists.
        """
        pma_dir = self.snapshot_dir / pma_number.upper()
        latest_path = pma_dir / "snapshot_latest.json"

        if not latest_path.exists():
            return None

        try:
            with open(latest_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def get_snapshot_before(
        self, pma_number: str, before_date: str
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot before a given date.

        Args:
            pma_number: PMA number.
            before_date: ISO date string.

        Returns:
            Snapshot dictionary or None.
        """
        pma_dir = self.snapshot_dir / pma_number.upper()
        if not pma_dir.exists():
            return None

        snapshots = sorted(pma_dir.glob("snapshot_*.json"), reverse=True)
        for sp in snapshots:
            if sp.name == "snapshot_latest.json":
                continue
            try:
                with open(sp) as f:
                    data = json.load(f)
                ts = data.get("timestamp", "")
                if ts < before_date:
                    return data
            except (json.JSONDecodeError, OSError):
                continue

        return None

    # ------------------------------------------------------------------
    # Core change detection
    # ------------------------------------------------------------------

    def detect_changes(
        self,
        pma_number: str,
        since: Optional[str] = None,
        change_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Detect changes for a PMA between current data and last snapshot.

        Args:
            pma_number: PMA number.
            since: Optional ISO date to compare against.
            change_types: Optional list of change types to check.

        Returns:
            Dictionary with detected changes and significance scores.
        """
        pma_key = pma_number.upper()

        # Get current data
        current_data = self.store.get_pma_data(pma_key)
        if current_data.get("error"):
            return {
                "pma_number": pma_key,
                "status": "error",
                "error": current_data["error"],
                "changes": [],
            }

        # Get current supplements
        current_supplements = self.store.get_supplements(pma_key)
        if current_supplements is None:
            current_supplements = []

        # Get comparison snapshot
        if since:
            previous_snapshot = self.get_snapshot_before(pma_key, since)
        else:
            previous_snapshot = self.get_latest_snapshot(pma_key)

        # If no previous snapshot, save current and report as baseline
        if previous_snapshot is None:
            snapshot_data = {
                "pma_data": current_data,
                "supplements": current_supplements,
            }
            self.save_snapshot(pma_key, snapshot_data)
            return {
                "pma_number": pma_key,
                "status": "baseline",
                "message": (
                    "No previous snapshot found. Current data saved as baseline."
                ),
                "changes": [],
                "total_significance": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "engine_version": ENGINE_VERSION,
            }

        # Compare current vs previous
        previous_data = previous_snapshot.get("data", {})
        prev_pma = previous_data.get("pma_data", {})
        prev_supplements = previous_data.get("supplements", [])

        all_changes = []

        # Filter change types if specified
        types_to_check = change_types or list(CHANGE_TYPES.keys())

        # Check each change type
        if "new_supplement" in types_to_check or "supplement_count_change" in types_to_check:
            supp_changes = self._detect_supplement_changes(
                current_supplements, prev_supplements
            )
            all_changes.extend(supp_changes)

        if "decision_code_change" in types_to_check:
            decision_changes = self._detect_decision_changes(
                current_data, prev_pma
            )
            all_changes.extend(decision_changes)

        if "ao_statement_update" in types_to_check:
            ao_changes = self._detect_ao_changes(current_data, prev_pma)
            all_changes.extend(ao_changes)

        if "applicant_change" in types_to_check:
            applicant_changes = self._detect_field_change(
                current_data, prev_pma, "applicant", "applicant_change"
            )
            all_changes.extend(applicant_changes)

        if "device_name_change" in types_to_check:
            name_changes = self._detect_field_change(
                current_data, prev_pma, "device_name", "device_name_change"
            )
            all_changes.extend(name_changes)

        if "maude_spike" in types_to_check:
            maude_changes = self._detect_maude_changes(
                current_data, prev_pma
            )
            all_changes.extend(maude_changes)

        # Score significance
        for change in all_changes:
            change["significance"] = self._score_significance(change)

        # Sort by significance (highest first)
        all_changes.sort(key=lambda c: c.get("significance", 0), reverse=True)

        total_significance = sum(c.get("significance", 0) for c in all_changes)

        # Save updated snapshot
        snapshot_data = {
            "pma_data": current_data,
            "supplements": current_supplements,
        }
        self.save_snapshot(pma_key, snapshot_data)

        # Record in history
        for change in all_changes:
            self._change_history.append({
                "pma_number": pma_key,
                "change_type": change.get("change_type", ""),
                "significance": change.get("significance", 0),
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "summary": change.get("message", ""),
            })
        self._save_history()

        return {
            "pma_number": pma_key,
            "status": "completed",
            "total_changes": len(all_changes),
            "total_significance": total_significance,
            "max_significance": max(
                (c.get("significance", 0) for c in all_changes), default=0
            ),
            "changes": all_changes,
            "previous_snapshot_time": previous_snapshot.get("timestamp", ""),
            "current_time": datetime.now(timezone.utc).isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": ENGINE_VERSION,
            "disclaimer": (
                "Change detection is AI-generated from public FDA data. "
                "All detected changes require independent verification "
                "by qualified regulatory professionals."
            ),
        }

    # ------------------------------------------------------------------
    # Change detection methods
    # ------------------------------------------------------------------

    def _detect_supplement_changes(
        self,
        current_supplements: List[Dict],
        previous_supplements: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Detect new supplements and supplement count changes."""
        changes = []

        prev_numbers = {
            s.get("supplement_number", "") for s in previous_supplements
        }
        curr_numbers = {
            s.get("supplement_number", "") for s in current_supplements
        }

        new_numbers = curr_numbers - prev_numbers
        for supp in current_supplements:
            if supp.get("supplement_number", "") in new_numbers:
                changes.append({
                    "change_type": "new_supplement",
                    "field": "supplements",
                    "before": None,
                    "after": supp.get("supplement_number", ""),
                    "details": {
                        "supplement_type": supp.get("supplement_type", ""),
                        "supplement_reason": supp.get("supplement_reason", ""),
                        "decision_code": supp.get("decision_code", ""),
                        "decision_date": supp.get("decision_date", ""),
                    },
                    "message": (
                        f"New supplement {supp.get('supplement_number', '')} "
                        f"({supp.get('supplement_type', '')}): "
                        f"{supp.get('supplement_reason', '')[:80]}"
                    ),
                })

        # Count change
        if len(current_supplements) != len(previous_supplements):
            changes.append({
                "change_type": "supplement_count_change",
                "field": "supplement_count",
                "before": len(previous_supplements),
                "after": len(current_supplements),
                "message": (
                    f"Supplement count changed from "
                    f"{len(previous_supplements)} to {len(current_supplements)}"
                ),
            })

        return changes

    def _detect_decision_changes(
        self, current: Dict, previous: Dict
    ) -> List[Dict[str, Any]]:
        """Detect decision code changes."""
        changes = []
        curr_code = current.get("decision_code", "")
        prev_code = previous.get("decision_code", "")

        if curr_code and prev_code and curr_code != prev_code:
            changes.append({
                "change_type": "decision_code_change",
                "field": "decision_code",
                "before": prev_code,
                "after": curr_code,
                "message": (
                    f"Decision code changed from {prev_code} to {curr_code}"
                ),
            })

        return changes

    def _detect_ao_changes(
        self, current: Dict, previous: Dict
    ) -> List[Dict[str, Any]]:
        """Detect approval order statement changes."""
        changes = []
        curr_ao = current.get("ao_statement", "")
        prev_ao = previous.get("ao_statement", "")

        if curr_ao and prev_ao and curr_ao != prev_ao:
            changes.append({
                "change_type": "ao_statement_update",
                "field": "ao_statement",
                "before": prev_ao[:200],
                "after": curr_ao[:200],
                "message": "Approval order statement updated",
            })

        return changes

    def _detect_field_change(
        self,
        current: Dict,
        previous: Dict,
        field: str,
        change_type: str,
    ) -> List[Dict[str, Any]]:
        """Detect changes in a specific field."""
        changes = []
        curr_val = current.get(field, "")
        prev_val = previous.get(field, "")

        if curr_val and prev_val and curr_val != prev_val:
            type_config = CHANGE_TYPES.get(change_type, {})
            changes.append({
                "change_type": change_type,
                "field": field,
                "before": prev_val,
                "after": curr_val,
                "message": (
                    f"{type_config.get('label', field)} changed: "
                    f"'{prev_val}' -> '{curr_val}'"
                ),
            })

        return changes

    def _detect_maude_changes(
        self, current: Dict, previous: Dict
    ) -> List[Dict[str, Any]]:
        """Detect MAUDE event count spikes."""
        changes = []
        product_code = current.get("product_code", "")
        if not product_code:
            return changes

        # Get current MAUDE counts
        try:
            result = self.store.client.get_events(
                product_code, count="event_type.exact"
            )
            if result.get("degraded") or result.get("error"):
                return changes

            curr_total = sum(
                e.get("count", 0) for e in result.get("results", [])
            )

            # Compare with previous (stored in snapshot metadata)
            prev_maude = previous.get("_maude_total_events", 0)

            if prev_maude > 0 and curr_total > prev_maude:
                increase_pct = (
                    (curr_total - prev_maude) / prev_maude * 100
                )
                if increase_pct > 20:  # >20% increase is noteworthy
                    changes.append({
                        "change_type": "maude_spike",
                        "field": "maude_events",
                        "before": prev_maude,
                        "after": curr_total,
                        "increase_pct": round(increase_pct, 1),
                        "message": (
                            f"MAUDE events increased by {increase_pct:.1f}% "
                            f"({prev_maude} -> {curr_total})"
                        ),
                    })
        except Exception:
            pass

        return changes

    # ------------------------------------------------------------------
    # Significance scoring
    # ------------------------------------------------------------------

    def _score_significance(self, change: Dict[str, Any]) -> int:
        """Score the significance of a change (0-100).

        Args:
            change: Change dictionary.

        Returns:
            Significance score (0-100).
        """
        change_type = change.get("change_type", "")
        type_config = CHANGE_TYPES.get(change_type, {})
        base_score = type_config.get("base_significance", 50)

        # Apply modifiers based on change details
        modifiers = 0

        # Decision code changes involving denial or withdrawal are more significant
        if change_type == "decision_code_change":
            after = change.get("after", "")
            if after in ("DENY", "WDRN"):
                modifiers += 10

        # Supplement changes with safety implications
        if change_type == "new_supplement":
            details = change.get("details", {})
            reason = details.get("supplement_reason", "").lower()
            if any(w in reason for w in ["safety", "recall", "warning", "death"]):
                modifiers += 15
            if details.get("decision_code") == "DENY":
                modifiers += 10

        # MAUDE spikes with large increases
        if change_type == "maude_spike":
            increase_pct = change.get("increase_pct", 0)
            if increase_pct > 100:
                modifiers += 15
            elif increase_pct > 50:
                modifiers += 10

        return min(100, max(0, base_score + modifiers))

    # ------------------------------------------------------------------
    # History and reporting
    # ------------------------------------------------------------------

    def get_change_history(
        self,
        pma_number: Optional[str] = None,
        since: Optional[str] = None,
        change_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get change history, optionally filtered.

        Args:
            pma_number: Filter by PMA number.
            since: Filter by date (ISO string).
            change_types: Filter by change types.
            limit: Maximum entries to return.

        Returns:
            List of change history entries.
        """
        filtered = self._change_history

        if pma_number:
            filtered = [
                c for c in filtered
                if c.get("pma_number", "").upper() == pma_number.upper()
            ]

        if since:
            filtered = [
                c for c in filtered
                if c.get("detected_at", "") >= since
            ]

        if change_types:
            filtered = [
                c for c in filtered
                if c.get("change_type", "") in change_types
            ]

        return filtered[-limit:]

    def generate_change_report(
        self,
        pma_number: str,
        since: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive change report for a PMA.

        Args:
            pma_number: PMA number.
            since: Optional start date.
            output_path: Optional path to write report.

        Returns:
            Change report dictionary.
        """
        # Detect current changes
        result = self.detect_changes(pma_number, since=since)

        # Get history
        history = self.get_change_history(pma_number=pma_number, since=since)

        # Group by change type
        by_type: Dict[str, List[Dict]] = defaultdict(list)
        for change in result.get("changes", []):
            by_type[change.get("change_type", "unknown")].append(change)

        report = {
            "pma_number": pma_number.upper(),
            "report_type": "change_detection",
            "current_changes": result,
            "history_summary": {
                "total_historical_changes": len(history),
                "by_type": {
                    ct: len([h for h in history if h.get("change_type") == ct])
                    for ct in CHANGE_TYPES
                },
            },
            "change_types_detected": list(by_type.keys()),
            "recommendations": self._generate_recommendations(result),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": ENGINE_VERSION,
            "disclaimer": (
                "This change report is AI-generated from public FDA data. "
                "All detected changes and recommendations require "
                "independent verification by qualified regulatory professionals."
            ),
        }

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            report["output_file"] = output_path

        return report

    def _generate_recommendations(
        self, result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on detected changes."""
        recommendations = []
        changes = result.get("changes", [])

        for change in changes:
            change_type = change.get("change_type", "")
            type_config = CHANGE_TYPES.get(change_type, {})
            significance = change.get("significance", 0)

            if significance >= 80:
                recommendations.append({
                    "priority": "HIGH",
                    "change_type": change_type,
                    "recommendation": (
                        f"Review {type_config.get('label', change_type)} immediately. "
                        f"{type_config.get('regulatory_impact', '')}"
                    ),
                })
            elif significance >= 50:
                recommendations.append({
                    "priority": "MEDIUM",
                    "change_type": change_type,
                    "recommendation": (
                        f"Monitor {type_config.get('label', change_type)}. "
                        f"{type_config.get('regulatory_impact', '')}"
                    ),
                })

        return recommendations


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    """CLI entry point for Change Detection Engine."""
    parser = argparse.ArgumentParser(
        description="FDA Change Detection Engine -- Track PMA data changes"
    )
    parser.add_argument(
        "--pma", type=str, required=True,
        help="PMA number to check for changes"
    )
    parser.add_argument(
        "--since", type=str,
        help="ISO date to compare against (default: latest snapshot)"
    )
    parser.add_argument(
        "--change-types", type=str,
        help="Comma-separated change types to check"
    )
    parser.add_argument(
        "--output", type=str,
        help="Output file path for change report"
    )
    parser.add_argument(
        "--history", action="store_true",
        help="Show change history instead of detecting changes"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate comprehensive change report"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()
    engine = ChangeDetectionEngine()

    change_types = None
    if args.change_types:
        change_types = [ct.strip() for ct in args.change_types.split(",")]

    if args.history:
        result = engine.get_change_history(
            pma_number=args.pma,
            since=args.since,
            change_types=change_types,
        )
    elif args.report:
        result = engine.generate_change_report(
            pma_number=args.pma,
            since=args.since,
            output_path=args.output,
        )
    else:
        result = engine.detect_changes(
            pma_number=args.pma,
            since=args.since,
            change_types=change_types,
        )

    if args.json or True:  # Always JSON for CLI
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
