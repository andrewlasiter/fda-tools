#!/usr/bin/env python3
"""
Competitive Intelligence Dashboard Generator -- Market intelligence reports
for PMA device categories with interactive HTML dashboard output.

Generates comprehensive market intelligence dashboards covering:
    - Market share estimation from PMA approval counts by applicant
    - Approval trends over time (year distribution, decision codes)
    - Clinical endpoint analysis across comparable devices
    - Supplement activity and post-market device evolution
    - Safety profile comparisons (MAUDE event summaries)

Data sources: Phase 0-3 modules (PMA Data Store, Intelligence, Supplements,
Comparison, MAUDE events).

Usage:
    from competitive_dashboard import CompetitiveDashboardGenerator

    generator = CompetitiveDashboardGenerator()
    dashboard = generator.generate_dashboard("NMH")
    html = generator.export_html("NMH", output_path="dashboard.html")
    csv_data = generator.export_csv("NMH", output_path="data.csv")
    summary = generator.generate_market_summary("NMH")

    # CLI usage:
    python3 competitive_dashboard.py --product-code NMH
    python3 competitive_dashboard.py --product-code NMH --html dashboard.html
    python3 competitive_dashboard.py --product-code NMH --csv data.csv
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import sibling modules
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Dashboard configuration
# ------------------------------------------------------------------

DASHBOARD_VERSION = "1.0.0"

# Template file path (relative to scripts directory)
TEMPLATE_DIR = Path(__file__).parent.parent / "data" / "templates"
DASHBOARD_TEMPLATE_FILE = TEMPLATE_DIR / "competitive_dashboard.html"


def _load_html_template() -> str:
    """Load HTML template from file.

    Returns:
        HTML template string.

    Raises:
        FileNotFoundError: If template file is not found.
        IOError: If template file cannot be read.
    """
    if not DASHBOARD_TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            f"Dashboard template not found at {DASHBOARD_TEMPLATE_FILE}. "
            f"Please ensure the template file exists in data/templates/"
        )

    try:
        return DASHBOARD_TEMPLATE_FILE.read_text(encoding="utf-8")
    except IOError as e:
        raise IOError(
            f"Failed to read dashboard template from {DASHBOARD_TEMPLATE_FILE}: {e}"
        ) from e


# ------------------------------------------------------------------
# Competitive Dashboard Generator
# ------------------------------------------------------------------

class CompetitiveDashboardGenerator:
    """Generate competitive intelligence dashboards for PMA device categories.

    Aggregates data from PMA approvals, supplements, and MAUDE events
    to provide market intelligence reports.

    Attributes:
        store: PMADataStore instance for data access.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Competitive Dashboard Generator.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()

    # ------------------------------------------------------------------
    # Main dashboard generation
    # ------------------------------------------------------------------

    def generate_dashboard(
        self,
        product_code: str,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Generate comprehensive competitive intelligence dashboard data.

        Args:
            product_code: FDA product code to analyze.
            refresh: Force refresh from API.

        Returns:
            Dashboard data dict with market share, trends, and safety data.
        """
        pc = product_code.upper()

        # Fetch PMA approvals for product code
        pma_results = self._fetch_pma_approvals(pc)

        if not pma_results:
            return {
                "product_code": pc,
                "error": "No PMA approvals found for this product code.",
                "dashboard_version": DASHBOARD_VERSION,
            }

        # Build market share analysis
        market_share = self._compute_market_share(pma_results)

        # Build approval trends
        trends = self._compute_approval_trends(pma_results)

        # Build recent approvals table
        recent = self._build_recent_approvals(pma_results)

        # Fetch safety summary
        safety = self._build_safety_summary(pc)

        # Build supplement activity summary
        supplement_activity = self._build_supplement_summary(pma_results)

        # Clinical endpoint summary (from available SSED data)
        clinical_endpoints = self._aggregate_clinical_endpoints(pma_results)

        # Compute key metrics
        total_pmas = len(pma_results)
        total_applicants = len(set(r.get("applicant", "") for r in pma_results))
        approved_count = sum(
            1 for r in pma_results
            if r.get("decision_code", "").upper() in ("APPR", "APRL", "APPN")
        )
        approval_rate = round(approved_count / max(total_pmas, 1) * 100, 1)

        years = []
        for r in pma_results:
            dd = r.get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    years.append(int(dd[:4]))
                except ValueError as e:
                    print(f"Warning: Could not parse year from decision_date {dd!r}: {e}", file=sys.stderr)
        year_span = f"{min(years)}-{max(years)}" if years else "N/A"

        return {
            "product_code": pc,
            "dashboard_version": DASHBOARD_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "key_metrics": {
                "total_pmas": total_pmas,
                "total_applicants": total_applicants,
                "approval_rate": approval_rate,
                "year_span": year_span,
                "earliest_year": min(years) if years else None,
                "latest_year": max(years) if years else None,
            },
            "market_share": market_share,
            "approval_trends": trends,
            "recent_approvals": recent,
            "safety_summary": safety,
            "supplement_activity": supplement_activity,
            "clinical_endpoints": clinical_endpoints,
        }

    def generate_market_summary(
        self,
        product_code: str,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Generate a concise market summary for a product code.

        Args:
            product_code: FDA product code.
            refresh: Force refresh.

        Returns:
            Market summary dict.
        """
        dashboard = self.generate_dashboard(product_code, refresh=refresh)

        if dashboard.get("error"):
            return dashboard

        metrics = dashboard.get("key_metrics", {})
        share = dashboard.get("market_share", {})
        trends = dashboard.get("approval_trends", {})

        # Market leader
        leaders = share.get("by_applicant", [])
        leader = leaders[0] if leaders else {"applicant": "N/A", "share_pct": 0}

        # Trend direction
        year_dist = trends.get("year_distribution", {})
        sorted_years = sorted(year_dist.keys())
        if len(sorted_years) >= 4:
            recent = sum(year_dist[y] for y in sorted_years[-2:]) / 2
            older = sum(year_dist[y] for y in sorted_years[:2]) / 2
            trend_dir = "growing" if recent > older * 1.3 else (
                "declining" if older > recent * 1.3 else "stable"
            )
        else:
            trend_dir = "insufficient_data"

        return {
            "product_code": product_code.upper(),
            "total_pmas": metrics.get("total_pmas", 0),
            "total_applicants": metrics.get("total_applicants", 0),
            "approval_rate": metrics.get("approval_rate", 0),
            "market_leader": {
                "applicant": leader.get("applicant", "N/A"),
                "pma_count": leader.get("count", 0),
                "share_pct": leader.get("share_pct", 0),
            },
            "market_trend": trend_dir,
            "year_span": metrics.get("year_span", "N/A"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # HTML export
    # ------------------------------------------------------------------

    def export_html(
        self,
        product_code: str,
        output_path: Optional[str] = None,
        refresh: bool = False,
    ) -> str:
        """Export dashboard as HTML file.

        Args:
            product_code: FDA product code.
            output_path: Output file path. Default: competitive_dashboard_{pc}.html
            refresh: Force refresh.

        Returns:
            Path to generated HTML file.
        """
        dashboard = self.generate_dashboard(product_code, refresh=refresh)

        if dashboard.get("error"):
            html = f"<h1>Error</h1><p>{dashboard['error']}</p>"
        else:
            html = self._render_html(dashboard)

        if output_path is None:
            output_path = f"competitive_dashboard_{product_code.upper()}.html"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _render_html(self, dashboard: Dict[str, Any]) -> str:
        """Render dashboard data as HTML.

        Args:
            dashboard: Dashboard data dict.

        Returns:
            HTML string.

        Raises:
            FileNotFoundError: If template file is not found.
            IOError: If template file cannot be read.
        """
        metrics = dashboard.get("key_metrics", {})
        share = dashboard.get("market_share", {})
        trends = dashboard.get("approval_trends", {})
        recent = dashboard.get("recent_approvals", [])
        safety = dashboard.get("safety_summary", {})
        supplements = dashboard.get("supplement_activity", {})

        # Market share rows
        market_rows = ""
        max_count = 1
        by_applicant = share.get("by_applicant", [])
        if by_applicant:
            max_count = max(a.get("count", 1) for a in by_applicant)

        for entry in by_applicant[:15]:
            bar_width = round(entry.get("count", 0) / max(max_count, 1) * 200)
            market_rows += (
                f'<tr><td>{self._escape(entry.get("applicant", "N/A"))}</td>'
                f'<td>{entry.get("count", 0)}</td>'
                f'<td>{entry.get("share_pct", 0)}%</td>'
                f'<td><div class="bar-container">'
                f'<div class="bar" style="width:{bar_width}px"></div>'
                f'</div></td></tr>\n'
            )

        # Trend rows
        trend_rows = ""
        year_dist = trends.get("year_distribution", {})
        max_year_count = max(year_dist.values()) if year_dist else 1
        for year in sorted(year_dist.keys()):
            count = year_dist[year]
            bar_width = round(count / max(max_year_count, 1) * 200)
            trend_rows += (
                f'<tr><td>{year}</td><td>{count}</td>'
                f'<td><div class="bar-container">'
                f'<div class="bar" style="width:{bar_width}px"></div>'
                f'</div></td></tr>\n'
            )

        # Recent approval rows
        recent_rows = ""
        for r in recent[:20]:
            dc = r.get("decision_code", "").upper()
            badge_class = "badge-approved" if dc in ("APPR", "APRL") else "badge-denied"
            recent_rows += (
                f'<tr><td>{self._escape(r.get("pma_number", ""))}</td>'
                f'<td>{self._escape(r.get("device_name", "")[:40])}</td>'
                f'<td>{self._escape(r.get("applicant", "")[:30])}</td>'
                f'<td>{r.get("decision_date", "N/A")}</td>'
                f'<td><span class="badge {badge_class}">{dc}</span></td></tr>\n'
            )

        # Safety section
        safety_html = ""
        if safety.get("total_events", 0) > 0:
            safety_html = f"""
            <table>
              <tr><th>Metric</th><th>Value</th></tr>
              <tr><td>Total MAUDE Events</td><td>{safety.get('total_events', 0)}</td></tr>
              <tr><td>Death Reports</td><td>{safety.get('death_count', 0)}</td></tr>
              <tr><td>Injury Reports</td><td>{safety.get('injury_count', 0)}</td></tr>
              <tr><td>Malfunction Reports</td><td>{safety.get('malfunction_count', 0)}</td></tr>
            </table>"""
        else:
            safety_html = "<p>No MAUDE event data available for this product code.</p>"

        # Supplement section
        supp_html = ""
        if supplements.get("total_supplements", 0) > 0:
            supp_html = f"""
            <table>
              <tr><th>Metric</th><th>Value</th></tr>
              <tr><td>Total Supplements</td><td>{supplements.get('total_supplements', 0)}</td></tr>
              <tr><td>Avg per PMA</td><td>{supplements.get('avg_per_pma', 0)}</td></tr>
              <tr><td>Most Active PMA</td><td>{self._escape(supplements.get('most_active_pma', 'N/A'))}</td></tr>
            </table>"""
        else:
            supp_html = "<p>No supplement activity data available.</p>"

        # Load and render template
        html_template = _load_html_template()
        return html_template.format(
            product_code=self._escape(dashboard.get("product_code", "")),
            generated_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            version=DASHBOARD_VERSION,
            total_pmas=metrics.get("total_pmas", 0),
            total_applicants=metrics.get("total_applicants", 0),
            approval_rate=metrics.get("approval_rate", 0),
            year_span=metrics.get("year_span", "N/A"),
            market_share_rows=market_rows,
            trend_rows=trend_rows,
            recent_approval_rows=recent_rows,
            safety_section=safety_html,
            supplement_section=supp_html,
        )

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def export_csv(
        self,
        product_code: str,
        output_path: Optional[str] = None,
        refresh: bool = False,
    ) -> str:
        """Export dashboard data as CSV file.

        Args:
            product_code: FDA product code.
            output_path: Output file path. Default: competitive_data_{pc}.csv
            refresh: Force refresh.

        Returns:
            Path to generated CSV file.
        """
        dashboard = self.generate_dashboard(product_code, refresh=refresh)

        if output_path is None:
            output_path = f"competitive_data_{product_code.upper()}.csv"

        recent = dashboard.get("recent_approvals", [])

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "pma_number", "device_name", "applicant",
                "decision_date", "decision_code", "product_code",
            ])
            for r in recent:
                writer.writerow([
                    r.get("pma_number", ""),
                    r.get("device_name", ""),
                    r.get("applicant", ""),
                    r.get("decision_date", ""),
                    r.get("decision_code", ""),
                    product_code.upper(),
                ])

        return output_path

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def export_json(
        self,
        product_code: str,
        output_path: Optional[str] = None,
        refresh: bool = False,
    ) -> str:
        """Export dashboard data as JSON file.

        Args:
            product_code: FDA product code.
            output_path: Output file path.
            refresh: Force refresh.

        Returns:
            Path to generated JSON file.
        """
        dashboard = self.generate_dashboard(product_code, refresh=refresh)

        if output_path is None:
            output_path = f"competitive_data_{product_code.upper()}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dashboard, f, indent=2)

        return output_path

    # ------------------------------------------------------------------
    # Data aggregation helpers
    # ------------------------------------------------------------------

    def _fetch_pma_approvals(self, product_code: str) -> List[Dict[str, Any]]:
        """Fetch PMA approvals for a product code.

        Args:
            product_code: FDA product code.

        Returns:
            List of PMA result dicts.
        """
        result = self.store.client.search_pma(
            product_code=product_code, limit=100
        )

        if result.get("degraded") or not result.get("results"):
            return []

        # Filter to base PMAs (exclude supplements)
        base_pmas = []
        seen = set()
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            base_pma = re.sub(r"S\d+$", "", pn)

            if "S" in pn[1:]:
                continue
            if base_pma in seen:
                continue
            seen.add(base_pma)
            base_pmas.append(r)

        return base_pmas

    def _compute_market_share(
        self,
        pma_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute market share by applicant.

        Args:
            pma_results: List of PMA results.

        Returns:
            Market share analysis dict.
        """
        applicant_counts: Counter = Counter()
        for r in pma_results:
            applicant = r.get("applicant", "Unknown")
            applicant_counts[applicant] += 1

        total = len(pma_results)
        by_applicant = []
        for applicant, count in applicant_counts.most_common():
            by_applicant.append({
                "applicant": applicant,
                "count": count,
                "share_pct": round(count / max(total, 1) * 100, 1),
            })

        return {
            "total_pmas": total,
            "total_applicants": len(applicant_counts),
            "by_applicant": by_applicant,
            "concentration": self._compute_hhi(applicant_counts, total),
        }

    def _compute_hhi(
        self,
        counts: Counter,
        total: int,
    ) -> Dict[str, Any]:
        """Compute Herfindahl-Hirschman Index for market concentration.

        Args:
            counts: Applicant -> count counter.
            total: Total PMA count.

        Returns:
            HHI analysis dict.
        """
        if total == 0:
            return {"hhi": 0, "concentration": "none"}

        hhi = sum((count / total * 100) ** 2 for count in counts.values())

        if hhi >= 2500:
            concentration = "highly_concentrated"
        elif hhi >= 1500:
            concentration = "moderately_concentrated"
        else:
            concentration = "competitive"

        return {
            "hhi": round(hhi, 0),
            "concentration": concentration,
            "description": (
                f"HHI = {hhi:.0f}. "
                f"{'Highly concentrated' if hhi >= 2500 else 'Moderately concentrated' if hhi >= 1500 else 'Competitive'} market."
            ),
        }

    def _compute_approval_trends(
        self,
        pma_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute approval trends by year.

        Args:
            pma_results: List of PMA results.

        Returns:
            Trend analysis dict.
        """
        year_counts: Counter = Counter()
        year_decision: Dict[int, Counter] = defaultdict(Counter)

        for r in pma_results:
            dd = r.get("decision_date", "")
            dc = r.get("decision_code", "").upper()
            if dd and len(dd) >= 4:
                try:
                    year = int(dd[:4])
                    year_counts[year] += 1
                    year_decision[year][dc] += 1
                except ValueError:
                    continue

        # Compute moving average
        sorted_years = sorted(year_counts.keys())
        moving_avg: Dict[int, float] = {}
        for i, year in enumerate(sorted_years):
            window = [year_counts[sorted_years[j]]
                      for j in range(max(0, i - 1), min(len(sorted_years), i + 2))]
            moving_avg[year] = round(sum(window) / len(window), 1)

        return {
            "year_distribution": dict(sorted(year_counts.items())),
            "year_decision_codes": {
                year: dict(decisions) for year, decisions in sorted(year_decision.items())
            },
            "moving_average": moving_avg,
            "peak_year": max(year_counts, key=lambda y: year_counts[y]) if year_counts else None,
            "peak_count": max(year_counts.values()) if year_counts else 0,
        }

    def _build_recent_approvals(
        self,
        pma_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build recent approvals list.

        Args:
            pma_results: List of PMA results.

        Returns:
            Sorted list of recent approval dicts.
        """
        recent = []
        for r in pma_results:
            recent.append({
                "pma_number": r.get("pma_number", ""),
                "device_name": r.get("trade_name", r.get("generic_name", "N/A")),
                "applicant": r.get("applicant", "N/A"),
                "decision_date": r.get("decision_date", "N/A"),
                "decision_code": r.get("decision_code", "N/A"),
                "product_code": r.get("product_code", ""),
            })

        # Sort by date descending
        recent.sort(key=lambda x: x.get("decision_date", ""), reverse=True)
        return recent[:50]

    def _build_safety_summary(
        self,
        product_code: str,
    ) -> Dict[str, Any]:
        """Build MAUDE safety summary for product code.

        Args:
            product_code: FDA product code.

        Returns:
            Safety summary dict.
        """
        result = self.store.client.get_events(
            product_code, count="event_type.exact"
        )

        if result.get("degraded") or not result.get("results"):
            return {"total_events": 0, "note": "No MAUDE data available."}

        type_counts: Dict[str, int] = {}
        total = 0
        for item in result.get("results", []):
            if isinstance(item, dict):
                term = item.get("term", "Unknown")
                count = item.get("count", 0)
                type_counts[term] = count
                total += count

        return {
            "total_events": total,
            "event_types": type_counts,
            "death_count": type_counts.get("Death", 0),
            "injury_count": type_counts.get("Injury", 0),
            "malfunction_count": type_counts.get("Malfunction", 0),
            "death_rate": round(
                type_counts.get("Death", 0) / max(total, 1) * 100, 2
            ),
            "injury_rate": round(
                type_counts.get("Injury", 0) / max(total, 1) * 100, 2
            ),
        }

    def _build_supplement_summary(
        self,
        pma_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build supplement activity summary.

        Args:
            pma_results: List of PMA results.

        Returns:
            Supplement summary dict.
        """
        total_supplements = 0
        pma_supplement_counts: Dict[str, int] = {}

        for r in pma_results:
            pn = r.get("pma_number", "")
            # Try to get supplement count from cached data
            cached = self.store.get_manifest().get("pma_entries", {}).get(pn, {})
            supp_count = cached.get("supplement_count", 0)
            pma_supplement_counts[pn] = supp_count
            total_supplements += supp_count

        # Most active PMA
        most_active = max(
            pma_supplement_counts, key=lambda k: pma_supplement_counts[k]
        ) if pma_supplement_counts else "N/A"

        avg_per_pma = round(
            total_supplements / max(len(pma_results), 1), 1
        )

        return {
            "total_supplements": total_supplements,
            "avg_per_pma": avg_per_pma,
            "most_active_pma": most_active,
            "most_active_count": pma_supplement_counts.get(most_active, 0),
            "pma_supplement_counts": pma_supplement_counts,
        }

    def _aggregate_clinical_endpoints(
        self,
        pma_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregate clinical endpoint information across PMAs.

        Args:
            pma_results: List of PMA results.

        Returns:
            Clinical endpoint summary dict.
        """
        endpoints_found: List[str] = []
        pmas_with_clinical = 0

        for r in pma_results:
            pn = r.get("pma_number", "")
            sections = self.store.get_extracted_sections(pn)
            if sections:
                section_dict = sections.get("sections", sections)
                clinical = section_dict.get("clinical_studies", {})
                if isinstance(clinical, dict) and clinical.get("word_count", 0) > 100:
                    pmas_with_clinical += 1
                    content = clinical.get("content", "")
                    # Extract common endpoint keywords
                    for kw in ["survival", "success rate", "efficacy",
                               "safety endpoint", "primary endpoint",
                               "non-inferiority", "superiority"]:
                        if kw.lower() in content.lower():
                            endpoints_found.append(kw)

        endpoint_counts = Counter(endpoints_found)

        return {
            "pmas_with_clinical_data": pmas_with_clinical,
            "common_endpoints": dict(endpoint_counts.most_common(10)),
            "clinical_data_coverage": round(
                pmas_with_clinical / max(len(pma_results), 1) * 100, 1
            ),
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Input string.

        Returns:
            HTML-escaped string.
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_dashboard(dashboard: Dict[str, Any]) -> str:
    """Format dashboard data as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("PMA COMPETITIVE INTELLIGENCE DASHBOARD")
    lines.append("=" * 70)

    if dashboard.get("error"):
        lines.append(f"ERROR: {dashboard['error']}")
        return "\n".join(lines)

    metrics = dashboard.get("key_metrics", {})
    lines.append(f"Product Code: {dashboard.get('product_code', 'N/A')}")
    lines.append(f"Total PMAs:   {metrics.get('total_pmas', 0)}")
    lines.append(f"Applicants:   {metrics.get('total_applicants', 0)}")
    lines.append(f"Approval Rate: {metrics.get('approval_rate', 0)}%")
    lines.append(f"Year Range:   {metrics.get('year_span', 'N/A')}")
    lines.append("")

    # Market share
    share = dashboard.get("market_share", {})
    by_applicant = share.get("by_applicant", [])
    if by_applicant:
        lines.append("--- Market Share (by PMA Count) ---")
        for entry in by_applicant[:10]:
            lines.append(
                f"  {entry['applicant'][:35]:35s} | "
                f"{entry['count']:3d} PMAs | "
                f"{entry['share_pct']:5.1f}%"
            )
        conc = share.get("concentration", {})
        if conc:
            lines.append(f"  Market Concentration: {conc.get('concentration', 'N/A')} "
                         f"(HHI: {conc.get('hhi', 0):.0f})")
        lines.append("")

    # Trends
    trends = dashboard.get("approval_trends", {})
    year_dist = trends.get("year_distribution", {})
    if year_dist:
        lines.append("--- Approval Trends ---")
        for year in sorted(year_dist.keys())[-10:]:
            count = year_dist[year]
            bar = "#" * min(count, 40)
            lines.append(f"  {year}: {count:3d} {bar}")
        lines.append(f"  Peak Year: {trends.get('peak_year', 'N/A')} "
                     f"({trends.get('peak_count', 0)} approvals)")
        lines.append("")

    # Safety
    safety = dashboard.get("safety_summary", {})
    if safety.get("total_events", 0) > 0:
        lines.append("--- MAUDE Safety Summary ---")
        lines.append(f"  Total Events:   {safety['total_events']}")
        lines.append(f"  Deaths:         {safety.get('death_count', 0)} "
                     f"({safety.get('death_rate', 0)}%)")
        lines.append(f"  Injuries:       {safety.get('injury_count', 0)} "
                     f"({safety.get('injury_rate', 0)}%)")
        lines.append(f"  Malfunctions:   {safety.get('malfunction_count', 0)}")
        lines.append("")

    # Recent approvals
    recent = dashboard.get("recent_approvals", [])
    if recent:
        lines.append("--- Recent Approvals ---")
        for r in recent[:10]:
            lines.append(
                f"  {r.get('pma_number', 'N/A'):10s} | "
                f"{r.get('device_name', 'N/A')[:30]:30s} | "
                f"{r.get('applicant', 'N/A')[:20]:20s} | "
                f"{r.get('decision_date', 'N/A')}"
            )
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {dashboard.get('generated_at', 'N/A')[:10]}")
    lines.append(f"Dashboard v{dashboard.get('dashboard_version', 'N/A')}")
    lines.append("This dashboard is AI-generated from public FDA data.")
    lines.append("Independent verification by qualified RA professionals required.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Competitive Intelligence Dashboard -- Market intelligence for PMA device categories"
    )
    parser.add_argument("--product-code", dest="product_code",
                        help="FDA product code to analyze")
    parser.add_argument("--html", help="Export as HTML file")
    parser.add_argument("--csv", help="Export as CSV file")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--summary", action="store_true",
                        help="Show concise market summary")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh from API")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.product_code:
        parser.error("Specify --product-code")

    generator = CompetitiveDashboardGenerator()

    if args.html:
        path = generator.export_html(
            args.product_code, output_path=args.html, refresh=args.refresh
        )
        print(f"HTML dashboard saved to: {path}")

    elif args.csv:
        path = generator.export_csv(
            args.product_code, output_path=args.csv, refresh=args.refresh
        )
        print(f"CSV data saved to: {path}")

    elif args.summary:
        result = generator.generate_market_summary(
            args.product_code, refresh=args.refresh
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))

    else:
        dashboard = generator.generate_dashboard(
            args.product_code, refresh=args.refresh
        )
        if args.json:
            print(json.dumps(dashboard, indent=2))
        else:
            print(_format_dashboard(dashboard))

    if args.output:
        path = generator.export_json(
            args.product_code, output_path=args.output, refresh=args.refresh
        )
        print(f"JSON data saved to: {path}")


if __name__ == "__main__":
    main()
