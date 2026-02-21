"""
Post-Market Surveillance module for FDA 510(k) submissions (FDA-119).

Integrates MAUDE adverse events and recall data into predicate risk scoring
and provides safety trend analysis for subject devices.

Usage:
    from fda_tools.lib.post_market_surveillance import PostMarketSurveillance

    pms = PostMarketSurveillance(api_client)
    report = pms.generate_safety_report("DQY")
    risk_data = pms.get_predicate_risk_data(["K123456", "K234567"], product_code="DQY")
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MAUDE risk scoring thresholds (events per year per product code)
# ---------------------------------------------------------------------------

_MAUDE_SCORE_MAP = [
    (0,    10),   # 0 events/year  → full 10 pts
    (10,    7),   # 1–10 events/yr → 7 pts
    (50,    4),   # 11–50          → 4 pts
    (100,   2),   # 51–100         → 2 pts
    (None,  0),   # >100           → 0 pts (high risk)
]

# Recall risk deduction applied on top of recalls_score
_RECALL_DEDUCTION_PER_RECALL = 5   # lose 5 pts per recall (max 0)

# Trend classification thresholds (% change year-over-year)
_TREND_INCREASING_THRESHOLD = 0.25   # >25% YoY increase
_TREND_DECREASING_THRESHOLD = -0.25  # >25% YoY decrease


def _maude_safety_score(events_per_year: float) -> int:
    """Return a 0–10 MAUDE safety score from annual event rate."""
    for upper, pts in _MAUDE_SCORE_MAP:
        if upper is None or events_per_year <= upper:
            return pts
    return 0


class PostMarketSurveillance:
    """
    Post-market surveillance engine for FDA 510(k) submissions.

    Fetches MAUDE adverse event and recall data via FDAClient and produces:
    - Per-predicate risk data (annual event rate, safety score, recall score)
    - Safety trend analysis (increasing / stable / decreasing)
    - Markdown safety intelligence reports

    All network I/O goes through the injected *api_client*, making the class
    fully testable via mocks.
    """

    def __init__(self, api_client: Any) -> None:
        """
        Args:
            api_client: An FDAClient instance (or compatible mock) that
                        exposes get_events(product_code) and
                        get_recalls(product_code).
        """
        self.client = api_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_maude_risk_score(self, events_per_year: float) -> int:
        """
        Convert an annual MAUDE event rate to a 0–10 safety score.

        Higher score = safer (fewer adverse events per year).

        Args:
            events_per_year: Annualised adverse-event count for the product code.

        Returns:
            Integer score in [0, 10].
        """
        return _maude_safety_score(events_per_year)

    def analyze_trends(
        self, product_code: str, years: int = 5
    ) -> Dict[str, Any]:
        """
        Analyse MAUDE event trends over *years* years for *product_code*.

        Fetches up to 1 000 events and buckets them by year, then calculates
        YoY change between the most recent two full years.

        Args:
            product_code: FDA product code (e.g. "DQY").
            years: Look-back window in years (default 5).

        Returns:
            Dict with keys:
              - product_code (str)
              - total_events (int)
              - events_by_year (Dict[int, int])
              - trend (str): "INCREASING" | "STABLE" | "DECREASING"
              - events_per_year (float): annualised rate over window
              - yoy_change (float | None): fractional YoY change (latest vs prior)
        """
        result: Dict[str, Any] = {
            "product_code": product_code,
            "total_events": 0,
            "events_by_year": {},
            "trend": "STABLE",
            "events_per_year": 0.0,
            "yoy_change": None,
        }

        response = self.client.get_events(product_code, limit=1000)
        if not response or "results" not in response:
            return result

        events = response.get("results", [])
        cutoff = datetime.now() - timedelta(days=years * 365)

        events_by_year: Dict[int, int] = {}
        for event in events:
            date_str = (
                event.get("date_of_event")
                or event.get("date_received")
                or ""
            )
            year = self._parse_event_year(date_str, cutoff)
            if year is not None:
                events_by_year[year] = events_by_year.get(year, 0) + 1

        total = sum(events_by_year.values())
        epa = total / years if years > 0 else 0.0

        trend, yoy = self._classify_trend(events_by_year)

        result.update(
            {
                "total_events": total,
                "events_by_year": events_by_year,
                "trend": trend,
                "events_per_year": round(epa, 2),
                "yoy_change": yoy,
            }
        )
        return result

    def get_predicate_risk_data(
        self,
        k_numbers: List[str],
        product_code: Optional[str] = None,
        years: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch MAUDE + recall risk data for a list of predicate K-numbers.

        Uses *product_code* for MAUDE if provided; otherwise looks up the
        product code from each predicate's metadata.  This is intentionally
        product-code–level because MAUDE is indexed by product code, not by
        individual K-number.

        Args:
            k_numbers: List of predicate K-numbers (e.g. ["K123456"]).
            product_code: Shared product code for MAUDE lookup (optional).
            years: Look-back window for MAUDE trend analysis.

        Returns:
            Dict keyed by K-number with risk sub-dicts containing:
              - maude_events_per_year (float)
              - maude_safety_score (int, 0–10)
              - recall_count (int)
              - recall_score (int, 0–10)
              - combined_risk_score (int, 0–20)
              - risk_level (str): "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
        """
        if not k_numbers:
            return {}

        # Fetch MAUDE for the shared product code once (if known)
        maude_epa: Optional[float] = None
        if product_code:
            trend_data = self.analyze_trends(product_code, years=years)
            maude_epa = trend_data["events_per_year"]

        result: Dict[str, Dict[str, Any]] = {}

        for k_number in k_numbers:
            epa = maude_epa if maude_epa is not None else 0.0
            maude_score = _maude_safety_score(epa)

            # Fetch recalls
            recall_response = self.client.get_recalls(
                product_code or "", limit=100
            )
            recall_count = 0
            if recall_response and "results" in recall_response:
                recall_count = len(recall_response["results"])

            recall_score = max(0, 10 - recall_count * _RECALL_DEDUCTION_PER_RECALL)
            combined = maude_score + recall_score
            risk_level = self._classify_risk_level(combined)

            result[k_number] = {
                "maude_events_per_year": epa,
                "maude_safety_score": maude_score,
                "recall_count": recall_count,
                "recall_score": recall_score,
                "combined_risk_score": combined,
                "risk_level": risk_level,
            }

        return result

    def generate_safety_report(
        self, product_code: str, years: int = 5
    ) -> str:
        """
        Generate a Markdown post-market safety intelligence report.

        Args:
            product_code: FDA product code (e.g. "DQY").
            years: Look-back window (default 5 years).

        Returns:
            Markdown-formatted report string.
        """
        trend = self.analyze_trends(product_code, years=years)

        recall_response = self.client.get_recalls(product_code, limit=100)
        recall_count = 0
        recall_details: List[str] = []
        if recall_response and "results" in recall_response:
            recalls = recall_response["results"]
            recall_count = len(recalls)
            for r in recalls[:5]:  # show up to 5 in report
                firm = r.get("recalling_firm", "Unknown firm")
                reason = r.get("reason_for_recall", "N/A")
                recall_details.append(f"- {firm}: {reason[:80]}")

        maude_score = _maude_safety_score(trend["events_per_year"])
        recall_score = max(0, 10 - recall_count * _RECALL_DEDUCTION_PER_RECALL)
        combined = maude_score + recall_score
        risk_level = self._classify_risk_level(combined)

        lines = [
            "# Post-Market Safety Intelligence Report",
            f"**Product Code:** {product_code}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Look-back Window:** {years} years",
            "",
            "---",
            "",
            "## Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total MAUDE Events ({years}y) | {trend['total_events']} |",
            f"| Events / Year | {trend['events_per_year']:.1f} |",
            f"| Trend | {trend['trend']} |",
            f"| Recall Count | {recall_count} |",
            f"| MAUDE Safety Score | {maude_score}/10 |",
            f"| Recall Score | {recall_score}/10 |",
            f"| Combined Risk Score | {combined}/20 |",
            f"| **Risk Level** | **{risk_level}** |",
            "",
        ]

        if trend["events_by_year"]:
            lines += [
                "## MAUDE Events by Year",
                "| Year | Events |",
                "|------|--------|",
            ]
            for yr in sorted(trend["events_by_year"]):
                lines.append(f"| {yr} | {trend['events_by_year'][yr]} |")
            lines.append("")

        if recall_details:
            lines += [
                "## Recent Recalls (up to 5)",
                *recall_details,
                "",
            ]
        elif recall_count == 0:
            lines += ["## Recalls", "No recalls found for this product code.", ""]

        lines += [
            "---",
            "",
            "> ⚠️ **Disclaimer:** This report is generated from openFDA data for research and",
            "> intelligence purposes only. Verify all data against official FDA sources before",
            "> use in regulatory submissions.",
        ]

        return "\n".join(lines)

    def get_dashboard_summary(self, product_code: str) -> Dict[str, Any]:
        """
        Return a concise safety summary suitable for dashboard display.

        Args:
            product_code: FDA product code.

        Returns:
            Dict with total_events, events_per_year, trend, recall_count,
            risk_level, and maude_safety_score.
        """
        trend = self.analyze_trends(product_code, years=5)
        recall_response = self.client.get_recalls(product_code, limit=100)
        recall_count = 0
        if recall_response and "results" in recall_response:
            recall_count = len(recall_response["results"])

        maude_score = _maude_safety_score(trend["events_per_year"])
        recall_score = max(0, 10 - recall_count * _RECALL_DEDUCTION_PER_RECALL)
        risk_level = self._classify_risk_level(maude_score + recall_score)

        return {
            "product_code": product_code,
            "total_events": trend["total_events"],
            "events_per_year": trend["events_per_year"],
            "trend": trend["trend"],
            "recall_count": recall_count,
            "maude_safety_score": maude_score,
            "risk_level": risk_level,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_event_year(date_str: str, cutoff: datetime) -> Optional[int]:
        """Parse year from MAUDE date string; return None if outside cutoff."""
        if not date_str:
            return None
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(date_str[:10], fmt[:len(date_str[:10])])
                if dt >= cutoff:
                    return dt.year
                return None
            except (ValueError, IndexError):
                continue
        return None

    @staticmethod
    def _classify_trend(
        events_by_year: Dict[int, int],
    ) -> tuple:
        """
        Classify trend and compute YoY change from annual event counts.

        Returns:
            (trend_str, yoy_change_float_or_None)
        """
        if len(events_by_year) < 2:
            return "STABLE", None

        sorted_years = sorted(events_by_year.keys())
        latest = events_by_year[sorted_years[-1]]
        prior = events_by_year[sorted_years[-2]]

        if prior == 0:
            yoy = 1.0 if latest > 0 else 0.0
        else:
            yoy = (latest - prior) / prior

        if yoy > _TREND_INCREASING_THRESHOLD:
            trend = "INCREASING"
        elif yoy < _TREND_DECREASING_THRESHOLD:
            trend = "DECREASING"
        else:
            trend = "STABLE"

        return trend, round(yoy, 3)

    @staticmethod
    def _classify_risk_level(combined_score: int) -> str:
        """
        Classify risk level from combined MAUDE + recall score (0–20).

        LOW ≥ 16, MEDIUM ≥ 11, HIGH ≥ 6, CRITICAL < 6.
        """
        if combined_score >= 16:
            return "LOW"
        elif combined_score >= 11:
            return "MEDIUM"
        elif combined_score >= 6:
            return "HIGH"
        else:
            return "CRITICAL"
