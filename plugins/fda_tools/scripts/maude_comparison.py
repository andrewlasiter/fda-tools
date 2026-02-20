#!/usr/bin/env python3
"""
MAUDE Peer Comparison Engine -- Comparative adverse event analysis across
similar PMA devices using openFDA MAUDE data.

Analyzes adverse event profiles for PMA devices by product code, comparing
event type frequency, severity distribution, reporting trends, and detecting
statistical outliers and safety signals.

Integrates with Phase 0 PMA Data Store for cached data and FDAClient for
MAUDE adverse event queries.

Usage:
    from maude_comparison import MAUDEComparisonEngine

    engine = MAUDEComparisonEngine()
    comparison = engine.compare_adverse_events("P170019", ["P160035", "P150009"])
    profile = engine.build_adverse_event_profile("P170019")
    signals = engine.detect_safety_signals("NMH")
    heatmap = engine.generate_event_heatmap("NMH")

    # CLI usage:
    python3 maude_comparison.py --pma P170019
    python3 maude_comparison.py --pma P170019 --compare P160035,P150009
    python3 maude_comparison.py --product-code NMH --signals
    python3 maude_comparison.py --product-code NMH --heatmap
"""

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Import sibling modules
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# MAUDE event type taxonomy
# ------------------------------------------------------------------

EVENT_TYPE_CATEGORIES = {
    "death": {
        "label": "Death",
        "severity": "critical",
        "severity_score": 5,
        "keywords": ["death", "died", "fatal", "mortality"],
    },
    "serious_injury": {
        "label": "Serious Injury",
        "severity": "high",
        "severity_score": 4,
        "keywords": [
            "serious injury", "hospitalization", "life-threatening",
            "permanent impairment", "disability",
        ],
    },
    "malfunction": {
        "label": "Device Malfunction",
        "severity": "medium",
        "severity_score": 3,
        "keywords": [
            "malfunction", "failure", "defect", "broken",
            "degradation", "fracture",
        ],
    },
    "injury": {
        "label": "Injury (Non-Serious)",
        "severity": "low",
        "severity_score": 2,
        "keywords": [
            "injury", "adverse event", "complication",
            "reaction", "irritation",
        ],
    },
    "no_answer_provided": {
        "label": "No Answer Provided",
        "severity": "unknown",
        "severity_score": 1,
        "keywords": ["no answer provided", "unknown"],
    },
    "other": {
        "label": "Other",
        "severity": "low",
        "severity_score": 1,
        "keywords": [],
    },
}

# Severity ordering for visualization
SEVERITY_ORDER = ["critical", "high", "medium", "low", "unknown"]

# Known event types from MAUDE
MAUDE_EVENT_TYPES = [
    "Death", "Injury", "Malfunction",
    "No answer provided", "Other",
]


# ------------------------------------------------------------------
# Statistical thresholds
# ------------------------------------------------------------------

OUTLIER_Z_THRESHOLD = 2.0  # Standard deviations for outlier detection
SIGNAL_MIN_EVENTS = 3      # Minimum events to flag a safety signal
TREND_WINDOW_YEARS = 3     # Years to analyze for trending


# ------------------------------------------------------------------
# MAUDE Comparison Engine
# ------------------------------------------------------------------

class MAUDEComparisonEngine:
    """Comparative adverse event analysis across PMA devices.

    Queries MAUDE adverse event data via openFDA, builds event profiles
    per device, and compares across peer devices in the same product code
    or across specified PMA numbers.

    Attributes:
        store: PMADataStore instance for data access.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize MAUDE Comparison Engine.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()

    # ------------------------------------------------------------------
    # Main comparison entry points
    # ------------------------------------------------------------------

    def compare_adverse_events(
        self,
        pma_number: str,
        comparators: Optional[List[str]] = None,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Compare adverse event profiles across PMAs.

        Args:
            pma_number: Primary PMA number.
            comparators: Optional list of comparator PMA numbers.
            refresh: Force refresh from API.

        Returns:
            Comparison result dict with per-device profiles, peer benchmarks,
            and outlier detection.
        """
        pma_key = pma_number.upper()
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)

        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        product_code = api_data.get("product_code", "")

        # Build primary device profile
        primary_profile = self.build_adverse_event_profile(pma_key, refresh=refresh)

        # Build comparator profiles
        comparator_profiles: List[Dict[str, Any]] = []
        if comparators:
            for comp in comparators:
                comp_profile = self.build_adverse_event_profile(
                    comp.upper(), refresh=refresh
                )
                comparator_profiles.append(comp_profile)
        elif product_code:
            # Auto-discover peers from same product code
            peers = self._discover_peer_pmas(pma_key, product_code)
            for peer_pma in peers[:5]:  # Limit to 5 peers
                comp_profile = self.build_adverse_event_profile(
                    peer_pma, refresh=refresh
                )
                comparator_profiles.append(comp_profile)

        # Compute peer benchmarks
        all_profiles = [primary_profile] + comparator_profiles
        benchmarks = self._compute_peer_benchmarks(all_profiles)

        # Detect outliers
        outliers = self._detect_outliers(primary_profile, benchmarks)

        # Detect safety signals
        signals = self._detect_signals_from_profile(primary_profile, benchmarks)

        return {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "product_code": product_code,
            "primary_profile": primary_profile,
            "comparator_profiles": comparator_profiles,
            "peer_benchmarks": benchmarks,
            "outliers": outliers,
            "safety_signals": signals,
            "total_devices_compared": len(all_profiles),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def build_adverse_event_profile(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Build a comprehensive adverse event profile for a PMA device.

        Args:
            pma_number: PMA number.
            refresh: Force refresh.

        Returns:
            Adverse event profile dict.
        """
        pma_key = pma_number.upper()
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)

        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
                "total_events": 0,
            }

        product_code = api_data.get("product_code", "")
        if not product_code:
            return {
                "pma_number": pma_key,
                "total_events": 0,
                "note": "No product code available for MAUDE query.",
            }

        # Query MAUDE events
        event_counts = self._query_event_counts(product_code)
        event_details = self._query_event_details(product_code)

        # Build event type distribution
        type_distribution = self._build_type_distribution(event_counts)

        # Build year trend
        year_trend = self._build_year_trend(event_details)

        # Severity distribution
        severity_dist = self._compute_severity_distribution(type_distribution)

        # Reporting rate
        total_events = sum(type_distribution.values())

        return {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "product_code": product_code,
            "total_events": total_events,
            "event_type_distribution": type_distribution,
            "severity_distribution": severity_dist,
            "year_trend": year_trend,
            "top_event_types": dict(
                Counter(type_distribution).most_common(10)
            ),
            "has_death_reports": type_distribution.get("Death", 0) > 0,
            "death_count": type_distribution.get("Death", 0),
            "injury_count": type_distribution.get("Injury", 0),
            "malfunction_count": type_distribution.get("Malfunction", 0),
        }

    # ------------------------------------------------------------------
    # Safety signal detection
    # ------------------------------------------------------------------

    def detect_safety_signals(
        self,
        product_code: str,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Detect safety signals for a product code from MAUDE data.

        Analyzes event frequency patterns, disproportionality, and
        trending to identify potential safety signals.

        Args:
            product_code: FDA product code.
            refresh: Force refresh.

        Returns:
            Safety signal analysis dict.
        """
        pc = product_code.upper()

        event_counts = self._query_event_counts(pc)
        event_details = self._query_event_details(pc)

        type_dist = self._build_type_distribution(event_counts)
        year_trend = self._build_year_trend(event_details)
        total_events = sum(type_dist.values())

        signals: List[Dict[str, Any]] = []

        # Signal 1: Death reports
        death_count = type_dist.get("Death", 0)
        if death_count >= SIGNAL_MIN_EVENTS:
            signals.append({
                "signal_type": "death_reports",
                "severity": "CRITICAL",
                "event_count": death_count,
                "description": (
                    f"{death_count} death report(s) found in MAUDE for product code {pc}."
                ),
                "recommendation": (
                    "Review death reports for device-relatedness assessment. "
                    "Consult MAUDE reports for detailed event narratives."
                ),
            })

        # Signal 2: High malfunction rate
        malfunction_count = type_dist.get("Malfunction", 0)
        if total_events > 0 and malfunction_count / total_events > 0.6:
            signals.append({
                "signal_type": "high_malfunction_rate",
                "severity": "WARNING",
                "event_count": malfunction_count,
                "rate": round(malfunction_count / total_events * 100, 1),
                "description": (
                    f"Malfunction rate is {malfunction_count / total_events:.0%} "
                    f"({malfunction_count}/{total_events} events). "
                    f"This is above the typical 50% threshold."
                ),
                "recommendation": (
                    "Investigate malfunction root causes. Consider design or "
                    "manufacturing improvements."
                ),
            })

        # Signal 3: Increasing trend
        if year_trend:
            sorted_years = sorted(year_trend.keys())
            if len(sorted_years) >= 3:
                recent_years = sorted_years[-TREND_WINDOW_YEARS:]
                older_years = sorted_years[:-TREND_WINDOW_YEARS]

                recent_avg = sum(year_trend[y] for y in recent_years) / len(recent_years)
                older_avg = sum(year_trend[y] for y in older_years) / max(len(older_years), 1)

                if older_avg > 0 and recent_avg > older_avg * 1.5:
                    signals.append({
                        "signal_type": "increasing_trend",
                        "severity": "WARNING",
                        "recent_avg": round(recent_avg, 1),
                        "older_avg": round(older_avg, 1),
                        "increase_factor": round(recent_avg / older_avg, 2),
                        "description": (
                            f"Adverse event reporting is increasing. "
                            f"Recent average: {recent_avg:.0f}/year vs "
                            f"historical: {older_avg:.0f}/year "
                            f"({recent_avg / older_avg:.1f}x increase)."
                        ),
                        "recommendation": (
                            "Monitor for continued increases. Determine if this reflects "
                            "increased device usage or emerging safety concerns."
                        ),
                    })

        # Signal 4: Disproportionate injury rate
        injury_count = type_dist.get("Injury", 0)
        if total_events > 10 and injury_count / total_events > 0.4:
            signals.append({
                "signal_type": "high_injury_rate",
                "severity": "CAUTION",
                "event_count": injury_count,
                "rate": round(injury_count / total_events * 100, 1),
                "description": (
                    f"Injury rate is {injury_count / total_events:.0%} of total events."
                ),
                "recommendation": (
                    "Review injury narratives for patterns and severity."
                ),
            })

        # Sort by severity
        severity_order = {"CRITICAL": 0, "WARNING": 1, "CAUTION": 2, "INFO": 3}
        signals.sort(key=lambda s: severity_order.get(s["severity"], 4))

        return {
            "product_code": pc,
            "total_events": total_events,
            "event_type_distribution": type_dist,
            "year_trend": year_trend,
            "signals": signals,
            "signal_count": len(signals),
            "highest_severity": signals[0]["severity"] if signals else "NONE",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Event heatmap generation
    # ------------------------------------------------------------------

    def generate_event_heatmap(
        self,
        product_code: str,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Generate event frequency heatmap data for a product code.

        Creates a year x event_type matrix for visualization.

        Args:
            product_code: FDA product code.
            refresh: Force refresh.

        Returns:
            Heatmap data dict with matrix, labels, and totals.
        """
        pc = product_code.upper()

        event_details = self._query_event_details(pc)
        year_trend = self._build_year_trend(event_details)

        # Build year x type matrix
        year_type_matrix: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for event in event_details:
            year = self._extract_event_year(event)
            event_type = self._classify_event_type(event)
            if year is not None:
                year_type_matrix[year][event_type] += 1

        # Build matrix data
        if not year_type_matrix:
            return {
                "product_code": pc,
                "has_data": False,
                "note": "No MAUDE event data available.",
            }

        sorted_years = sorted(year_type_matrix.keys())
        event_types = sorted(set(
            et for year_data in year_type_matrix.values()
            for et in year_data.keys()
        ))

        # Build matrix
        matrix: List[List[int]] = []
        for year in sorted_years:
            row = [year_type_matrix[year].get(et, 0) for et in event_types]
            matrix.append(row)

        # Row and column totals
        row_totals = [sum(row) for row in matrix]
        col_totals = [
            sum(matrix[i][j] for i in range(len(matrix)))
            for j in range(len(event_types))
        ]

        # Normalized matrix (percentage per year)
        normalized: List[List[float]] = []
        for i, row in enumerate(matrix):
            total = max(row_totals[i], 1)
            normalized.append([round(v / total * 100, 1) for v in row])

        return {
            "product_code": pc,
            "has_data": True,
            "years": sorted_years,
            "event_types": event_types,
            "matrix": matrix,
            "normalized_matrix": normalized,
            "row_totals": row_totals,
            "col_totals": col_totals,
            "grand_total": sum(row_totals),
            "peak_year": sorted_years[row_totals.index(max(row_totals))] if row_totals else None,
            "peak_event_type": event_types[col_totals.index(max(col_totals))] if col_totals else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Peer comparison helpers
    # ------------------------------------------------------------------

    def _discover_peer_pmas(
        self,
        pma_number: str,
        product_code: str,
    ) -> List[str]:
        """Discover peer PMAs from same product code.

        Args:
            pma_number: Primary PMA to exclude.
            product_code: Product code to search.

        Returns:
            List of peer PMA numbers.
        """
        import re

        result = self.store.client.search_pma(product_code=product_code, limit=20)

        if result.get("degraded") or not result.get("results"):
            return []

        peers = []
        seen = set()
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            base_pma = re.sub(r"S\d+$", "", pn)
            if base_pma == pma_number or base_pma in seen:
                continue
            if "S" in pn[1:]:
                continue
            seen.add(base_pma)
            peers.append(base_pma)

        return peers

    def _compute_peer_benchmarks(
        self,
        profiles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute peer group benchmark statistics.

        Args:
            profiles: List of adverse event profiles.

        Returns:
            Benchmark statistics dict.
        """
        valid_profiles = [p for p in profiles if p.get("total_events", 0) > 0]

        if not valid_profiles:
            return {
                "total_devices": len(profiles),
                "devices_with_events": 0,
                "note": "No devices with MAUDE events found.",
            }

        # Total events distribution
        total_events_list = [p["total_events"] for p in valid_profiles]

        # Event type benchmarks
        type_counts: Dict[str, List[int]] = defaultdict(list)
        for p in valid_profiles:
            dist = p.get("event_type_distribution", {})
            for event_type in MAUDE_EVENT_TYPES:
                type_counts[event_type].append(dist.get(event_type, 0))

        type_benchmarks = {}
        for event_type, counts in type_counts.items():
            if counts:
                type_benchmarks[event_type] = {
                    "mean": round(sum(counts) / len(counts), 1),
                    "median": round(sorted(counts)[len(counts) // 2], 1),
                    "min": min(counts),
                    "max": max(counts),
                    "std": round(self._std_dev(counts), 1),
                }

        # Death rate benchmark
        death_rates: List[float] = []
        for p in valid_profiles:
            total = p.get("total_events", 0)
            deaths = p.get("death_count", 0)
            if total > 0:
                death_rates.append(deaths / total * 100)

        return {
            "total_devices": len(profiles),
            "devices_with_events": len(valid_profiles),
            "total_events_stats": {
                "mean": round(sum(total_events_list) / len(total_events_list), 1),
                "median": round(sorted(total_events_list)[len(total_events_list) // 2], 1),
                "min": min(total_events_list),
                "max": max(total_events_list),
            },
            "event_type_benchmarks": type_benchmarks,
            "death_rate_stats": {
                "mean": round(sum(death_rates) / max(len(death_rates), 1), 2),
                "max": round(max(death_rates), 2) if death_rates else 0,
            } if death_rates else {},
        }

    def _detect_outliers(
        self,
        primary: Dict[str, Any],
        benchmarks: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect outlier metrics in primary profile vs benchmarks.

        Args:
            primary: Primary device profile.
            benchmarks: Peer benchmark statistics.

        Returns:
            List of outlier detection dicts.
        """
        outliers: List[Dict[str, Any]] = []

        type_benchmarks = benchmarks.get("event_type_benchmarks", {})
        primary_dist = primary.get("event_type_distribution", {})

        for event_type, bench in type_benchmarks.items():
            primary_count = primary_dist.get(event_type, 0)
            mean = bench.get("mean", 0)
            std = bench.get("std", 0)

            if std > 0:
                z_score = (primary_count - mean) / std
            else:
                z_score = 0.0

            if abs(z_score) >= OUTLIER_Z_THRESHOLD:
                direction = "above" if z_score > 0 else "below"
                outliers.append({
                    "event_type": event_type,
                    "primary_count": primary_count,
                    "peer_mean": mean,
                    "peer_std": std,
                    "z_score": round(z_score, 2),
                    "direction": direction,
                    "severity": "HIGH" if event_type in ("Death", "Injury") else "MEDIUM",
                    "description": (
                        f"{event_type} count ({primary_count}) is "
                        f"{abs(z_score):.1f} standard deviations {direction} "
                        f"the peer mean ({mean:.0f})."
                    ),
                })

        # Sort by absolute z-score descending
        outliers.sort(key=lambda o: abs(o["z_score"]), reverse=True)
        return outliers

    def _detect_signals_from_profile(
        self,
        primary: Dict[str, Any],
        benchmarks: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect safety signals from profile vs benchmarks.

        Args:
            primary: Primary device profile.
            benchmarks: Peer benchmark statistics.

        Returns:
            List of safety signal dicts.
        """
        signals: List[Dict[str, Any]] = []

        primary_total = primary.get("total_events", 0)
        bench_total_stats = benchmarks.get("total_events_stats", {})
        bench_mean = bench_total_stats.get("mean", 0)

        # Signal: Total events significantly above peer mean
        if bench_mean > 0 and primary_total > bench_mean * 2:
            signals.append({
                "signal_type": "high_event_volume",
                "severity": "WARNING",
                "primary_count": primary_total,
                "peer_mean": bench_mean,
                "ratio": round(primary_total / bench_mean, 2),
                "description": (
                    f"Total events ({primary_total}) are {primary_total / bench_mean:.1f}x "
                    f"the peer mean ({bench_mean:.0f})."
                ),
            })

        # Signal: Death rate above peer benchmark
        primary_deaths = primary.get("death_count", 0)
        death_stats = benchmarks.get("death_rate_stats", {})
        bench_death_mean = death_stats.get("mean", 0)
        if primary_total > 0 and primary_deaths > 0:
            primary_death_rate = primary_deaths / primary_total * 100
            if bench_death_mean > 0 and primary_death_rate > bench_death_mean * 2:
                signals.append({
                    "signal_type": "elevated_death_rate",
                    "severity": "CRITICAL",
                    "primary_rate": round(primary_death_rate, 2),
                    "peer_mean_rate": round(bench_death_mean, 2),
                    "description": (
                        f"Death rate ({primary_death_rate:.1f}%) is above "
                        f"peer mean ({bench_death_mean:.1f}%)."
                    ),
                })

        return signals

    # ------------------------------------------------------------------
    # MAUDE data query helpers
    # ------------------------------------------------------------------

    def _query_event_counts(self, product_code: str) -> Dict[str, Any]:
        """Query MAUDE event type counts for a product code.

        Args:
            product_code: FDA product code.

        Returns:
            Event count results from API.
        """
        result = self.store.client.get_events(
            product_code, count="event_type.exact"
        )

        if result.get("degraded"):
            return {}

        return result

    def _query_event_details(self, product_code: str) -> List[Dict[str, Any]]:
        """Query MAUDE event details for a product code.

        Args:
            product_code: FDA product code.

        Returns:
            List of event detail dicts.
        """
        result = self.store.client.get_events(product_code, limit=100)

        if result.get("degraded") or not result.get("results"):
            return []

        return result.get("results", [])

    def _build_type_distribution(
        self,
        event_counts: Dict[str, Any],
    ) -> Dict[str, int]:
        """Build event type distribution from count query results.

        Args:
            event_counts: Raw count query results.

        Returns:
            Dict of event_type -> count.
        """
        distribution: Dict[str, int] = {}

        results = event_counts.get("results", [])
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    term = item.get("term", "Unknown")
                    count = item.get("count", 0)
                    distribution[term] = count

        return distribution

    def _build_year_trend(
        self,
        events: List[Dict[str, Any]],
    ) -> Dict[int, int]:
        """Build year trend from event details.

        Args:
            events: List of event detail dicts.

        Returns:
            Dict of year -> event count.
        """
        year_counts: Counter = Counter()
        for event in events:
            year = self._extract_event_year(event)
            if year is not None:
                year_counts[year] += 1

        return dict(sorted(year_counts.items()))

    def _extract_event_year(self, event: Dict[str, Any]) -> Optional[int]:
        """Extract year from a MAUDE event record.

        Args:
            event: Event detail dict.

        Returns:
            Year as int, or None.
        """
        for date_field in ["date_received", "date_of_event", "date_report"]:
            date_str = event.get(date_field, "")
            if date_str and len(date_str) >= 4:
                try:
                    return int(date_str[:4])
                except ValueError:
                    continue
        return None

    def _classify_event_type(self, event: Dict[str, Any]) -> str:
        """Classify a MAUDE event by type.

        Args:
            event: Event detail dict.

        Returns:
            Event type string.
        """
        event_type = event.get("event_type", "")
        if isinstance(event_type, str):
            return event_type if event_type else "Other"
        if isinstance(event_type, list) and event_type:
            return event_type[0]
        return "Other"

    def _compute_severity_distribution(
        self,
        type_distribution: Dict[str, int],
    ) -> Dict[str, int]:
        """Map event types to severity categories.

        Args:
            type_distribution: Event type -> count dict.

        Returns:
            Severity category -> count dict.
        """
        severity_counts: Dict[str, int] = defaultdict(int)

        type_severity_map = {
            "Death": "critical",
            "Injury": "high",
            "Malfunction": "medium",
            "No answer provided": "unknown",
            "Other": "low",
        }

        for event_type, count in type_distribution.items():
            severity = type_severity_map.get(event_type, "low")
            severity_counts[severity] += count

        return dict(severity_counts)

    # ------------------------------------------------------------------
    # Statistical helpers
    # ------------------------------------------------------------------

    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation.

        Args:
            values: List of numeric values.

        Returns:
            Standard deviation.
        """
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_comparison(result: Dict[str, Any]) -> str:
    """Format comparison result as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("MAUDE PEER COMPARISON ANALYSIS")
    lines.append("=" * 70)

    if result.get("error"):
        lines.append(f"ERROR: {result['error']}")
        return "\n".join(lines)

    lines.append(f"PMA Number:   {result.get('pma_number', 'N/A')}")
    lines.append(f"Device:       {result.get('device_name', 'N/A')}")
    lines.append(f"Product Code: {result.get('product_code', 'N/A')}")
    lines.append(f"Devices Compared: {result.get('total_devices_compared', 0)}")
    lines.append("")

    # Primary profile
    primary = result.get("primary_profile", {})
    if primary.get("total_events", 0) > 0:
        lines.append("--- Primary Device Events ---")
        lines.append(f"  Total Events: {primary['total_events']}")
        lines.append(f"  Deaths:       {primary.get('death_count', 0)}")
        lines.append(f"  Injuries:     {primary.get('injury_count', 0)}")
        lines.append(f"  Malfunctions: {primary.get('malfunction_count', 0)}")
        lines.append("")

    # Peer benchmarks
    benchmarks = result.get("peer_benchmarks", {})
    total_stats = benchmarks.get("total_events_stats", {})
    if total_stats:
        lines.append("--- Peer Benchmarks ---")
        lines.append(f"  Mean Total Events: {total_stats.get('mean', 'N/A')}")
        lines.append(f"  Range: {total_stats.get('min', 'N/A')} - {total_stats.get('max', 'N/A')}")
        lines.append("")

    # Outliers
    outliers = result.get("outliers", [])
    if outliers:
        lines.append("--- Outlier Detection ---")
        for o in outliers:
            lines.append(
                f"  [{o.get('severity', 'N/A')}] {o.get('event_type', 'N/A')}: "
                f"{o.get('description', 'N/A')}"
            )
        lines.append("")

    # Safety signals
    signals = result.get("safety_signals", [])
    if signals:
        lines.append("--- Safety Signals ---")
        for s in signals:
            lines.append(
                f"  [{s.get('severity', 'N/A')}] {s.get('signal_type', 'N/A')}: "
                f"{s.get('description', 'N/A')}"
            )
        lines.append("")

    # Comparator summary
    comps = result.get("comparator_profiles", [])
    if comps:
        lines.append("--- Comparator Devices ---")
        for c in comps:
            lines.append(
                f"  {c.get('pma_number', 'N/A')}: "
                f"{c.get('device_name', 'N/A')[:35]} | "
                f"Events: {c.get('total_events', 0)}"
            )
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {result.get('generated_at', 'N/A')[:10]}")
    lines.append("This analysis is AI-generated from public MAUDE data.")
    lines.append("Independent verification by qualified RA professionals required.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MAUDE Peer Comparison Engine -- Compare adverse event profiles across PMAs"
    )
    parser.add_argument("--pma", help="Primary PMA number")
    parser.add_argument("--compare", help="Comma-separated comparator PMA numbers")
    parser.add_argument("--product-code", dest="product_code",
                        help="Analyze product code safety signals")
    parser.add_argument("--signals", action="store_true",
                        help="Detect safety signals")
    parser.add_argument("--heatmap", action="store_true",
                        help="Generate event heatmap data")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh from API")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    engine = MAUDEComparisonEngine()

    result: Optional[Dict[str, Any]] = None

    if args.product_code:
        if args.signals:
            result = engine.detect_safety_signals(args.product_code, refresh=args.refresh)
        elif args.heatmap:
            result = engine.generate_event_heatmap(args.product_code, refresh=args.refresh)
        else:
            result = engine.detect_safety_signals(args.product_code, refresh=args.refresh)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))

    elif args.pma:
        comparators = args.compare.split(",") if args.compare else None
        result = engine.compare_adverse_events(
            args.pma, comparators=comparators, refresh=args.refresh
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_format_comparison(result))
    else:
        parser.error("Specify --pma or --product-code")

    if args.output and result:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
