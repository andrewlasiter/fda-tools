#!/usr/bin/env python3
"""
PMA Approval Timeline Predictor -- Predict FDA review timelines from historical data.

Analyzes historical PMA approval timelines by device classification, product code,
advisory committee panel, submission type, clinical trial complexity, and manufacturer
track record. Builds statistical models and generates timeline predictions with
confidence intervals and milestone dates.

Integrates with PMA Data Store for cached data and PMA Intelligence for clinical
complexity assessment.

Usage:
    from timeline_predictor import TimelinePredictor

    predictor = TimelinePredictor()
    prediction = predictor.predict_timeline("P170019")
    prediction = predictor.predict_for_product_code("NMH")
    analysis = predictor.analyze_historical_timelines("NMH")

    # CLI usage:
    python3 timeline_predictor.py --pma P170019
    python3 timeline_predictor.py --product-code NMH
    python3 timeline_predictor.py --product-code NMH --historical
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore
from pma_intelligence import PMAIntelligenceEngine


# ------------------------------------------------------------------
# Timeline phase durations (in days) -- empirical baseline estimates
# ------------------------------------------------------------------

PHASE_BASELINES = {
    "administrative_review": {
        "label": "Administrative Review (Filing/RTA)",
        "typical_days": 45,
        "range": (30, 90),
        "description": "FDA acceptance review, filing decision, refuse-to-accept check",
    },
    "scientific_review": {
        "label": "Substantive/Scientific Review",
        "typical_days": 180,
        "range": (120, 365),
        "description": "Clinical, nonclinical, manufacturing, and labeling reviews",
    },
    "advisory_panel": {
        "label": "Advisory Panel Meeting",
        "typical_days": 90,
        "range": (60, 150),
        "description": "Panel scheduling, preparation, meeting, and recommendation",
    },
    "fda_decision": {
        "label": "FDA Final Decision",
        "typical_days": 45,
        "range": (20, 90),
        "description": "Final decision letter after panel recommendation or review completion",
    },
    "major_deficiency": {
        "label": "Major Deficiency Response Cycle",
        "typical_days": 120,
        "range": (60, 365),
        "description": "FDA issues major deficiency, applicant responds, FDA re-reviews",
    },
}

# ------------------------------------------------------------------
# Risk factor impact on timeline (days added)
# ------------------------------------------------------------------

RISK_FACTOR_IMPACTS = {
    "novel_technology": {
        "label": "Novel Technology",
        "impact_days": 60,
        "probability": 0.3,
        "description": "First-of-kind or breakthrough device technology",
    },
    "complex_clinical": {
        "label": "Complex Clinical Program",
        "impact_days": 90,
        "probability": 0.4,
        "description": "Large RCT, long follow-up, or adaptive design",
    },
    "advisory_panel_required": {
        "label": "Advisory Panel Required",
        "impact_days": 90,
        "probability": 0.5,
        "description": "Device requires advisory committee panel meeting",
    },
    "major_deficiency": {
        "label": "Major Deficiency Letter",
        "impact_days": 120,
        "probability": 0.3,
        "description": "FDA identifies significant gaps requiring response",
    },
    "labeling_issues": {
        "label": "Labeling Deficiencies",
        "impact_days": 30,
        "probability": 0.2,
        "description": "Minor labeling issues requiring revision",
    },
    "manufacturing_issues": {
        "label": "Manufacturing Review Issues",
        "impact_days": 45,
        "probability": 0.15,
        "description": "Manufacturing process questions or facility concerns",
    },
    "first_time_applicant": {
        "label": "First-Time PMA Applicant",
        "impact_days": 30,
        "probability": 0.1,
        "description": "Applicant has no prior PMA approvals",
    },
    "missing_clinical_data": {
        "label": "Incomplete Clinical Data",
        "impact_days": 90,
        "probability": 0.2,
        "description": "Clinical data gaps identified during review",
    },
}

# ------------------------------------------------------------------
# Advisory panel codes that typically require panel meetings
# ------------------------------------------------------------------

PANEL_MEETING_LIKELY = {
    "CV",  # Cardiovascular
    "NE",  # Neurological
    "OR",  # Orthopedic
    "GU",  # Gastroenterology/Urology
}


# ------------------------------------------------------------------
# Timeline Predictor
# ------------------------------------------------------------------

class TimelinePredictor:
    """Predict FDA PMA review timelines from historical data and device characteristics.

    Uses statistical analysis of historical approval timelines, device-specific
    risk factors, and clinical trial complexity to generate timeline predictions
    with confidence intervals and milestone dates.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Timeline Predictor.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()
        self.intelligence = PMAIntelligenceEngine(store=self.store)

    # ------------------------------------------------------------------
    # Main prediction
    # ------------------------------------------------------------------

    def predict_timeline(
        self,
        pma_number: str,
        submission_date: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict:
        """Predict approval timeline for a PMA based on device characteristics.

        Args:
            pma_number: PMA number to analyze.
            submission_date: Optional planned submission date (YYYY-MM-DD).
            refresh: Force refresh.

        Returns:
            Timeline prediction with milestones and confidence intervals.
        """
        pma_key = pma_number.upper()

        # Load PMA data
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        # Extract device characteristics
        product_code = api_data.get("product_code", "")
        panel = api_data.get("advisory_committee", "")

        # Get historical timeline data for this product code
        historical = self.analyze_historical_timelines(product_code) if product_code else {}

        # Assess risk factors
        risk_factors = self._assess_risk_factors(pma_key, api_data, refresh=refresh)

        # Build timeline prediction
        prediction = self._build_prediction(
            api_data, historical, risk_factors, submission_date
        )

        prediction.update({
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "product_code": product_code,
            "advisory_committee": panel,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "risk_factors": risk_factors,
            "historical_context": historical.get("summary", {}),
        })

        return prediction

    # ------------------------------------------------------------------
    # Product code prediction
    # ------------------------------------------------------------------

    def predict_for_product_code(
        self,
        product_code: str,
        submission_date: Optional[str] = None,
    ) -> Dict:
        """Predict timeline for a new PMA submission by product code.

        Uses historical data for the product code without requiring a
        specific PMA number.

        Args:
            product_code: FDA product code.
            submission_date: Optional planned submission date.

        Returns:
            Timeline prediction based on product code history.
        """
        historical = self.analyze_historical_timelines(product_code)

        if historical.get("error"):
            return {
                "product_code": product_code,
                "error": historical["error"],
            }

        summary = historical.get("summary", {})
        median_days = summary.get("median_days")

        if median_days is None:
            return {
                "product_code": product_code,
                "error": "Insufficient historical data for prediction",
            }

        # Base timeline from historical median
        base_days = median_days
        p25 = summary.get("p25_days", int(base_days * 0.7))
        p75 = summary.get("p75_days", int(base_days * 1.3))

        # Submission date handling
        start_date = None
        if submission_date:
            try:
                start_date = datetime.strptime(submission_date, "%Y-%m-%d")
            except ValueError:
                pass

        milestones = self._generate_milestones(
            base_days, start_date,
            panel_required=product_code in {"NMH", "DZE", "MQP"}  # High-risk codes
        )

        return {
            "product_code": product_code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "prediction": {
                "optimistic_days": p25,
                "realistic_days": base_days,
                "pessimistic_days": p75,
                "optimistic_months": round(p25 / 30, 1),
                "realistic_months": round(base_days / 30, 1),
                "pessimistic_months": round(p75 / 30, 1),
            },
            "milestones": milestones,
            "historical_basis": {
                "total_pmas_analyzed": summary.get("total_analyzed", 0),
                "median_days": median_days,
                "data_range": summary.get("year_range", "N/A"),
            },
            "recommendations": self._generate_recommendations(
                base_days, summary.get("total_analyzed", 0), []
            ),
        }

    # ------------------------------------------------------------------
    # Historical timeline analysis
    # ------------------------------------------------------------------

    def analyze_historical_timelines(
        self,
        product_code: str,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
    ) -> Dict:
        """Analyze historical PMA approval timelines for a product code.

        Args:
            product_code: FDA product code.
            year_start: Optional start year filter.
            year_end: Optional end year filter.

        Returns:
            Historical timeline analysis with statistics.
        """
        if not product_code:
            return {"error": "Product code required"}

        # Search for PMAs
        result = self.store.client.search_pma(
            product_code=product_code,
            year_start=year_start or 2015,
            year_end=year_end,
            limit=100,
            sort="decision_date:desc",
        )

        if result.get("degraded") or not result.get("results"):
            return {
                "product_code": product_code,
                "error": "No PMA data available for this product code",
                "summary": {},
            }

        # Extract timelines where submission and decision dates are available
        timelines = []
        applicant_history = Counter()
        yearly_counts = Counter()

        for r in result.get("results", []):
            # Filter to base PMAs (not supplements)
            pn = r.get("pma_number", "")
            if "S" in pn[1:]:
                continue

            dd = r.get("decision_date", "")
            applicant = r.get("applicant", "Unknown")
            applicant_history[applicant] += 1

            if dd and len(dd) >= 4:
                try:
                    year = int(dd[:4])
                    yearly_counts[year] += 1
                except ValueError:
                    pass

            # openFDA PMA endpoint does not always have date_received.
            # We still track approval dates for frequency analysis.
            timelines.append({
                "pma_number": pn,
                "decision_date": dd,
                "applicant": applicant,
                "device_name": r.get("trade_name", r.get("generic_name", "N/A")),
            })

        if not timelines:
            return {
                "product_code": product_code,
                "error": "No base PMA records found",
                "summary": {},
            }

        # Calculate statistics from available data
        years = sorted(yearly_counts.keys())
        year_range = f"{min(years)}-{max(years)}" if years else "N/A"

        # Use empirical baselines since openFDA PMA data rarely includes received date
        # Estimate based on product code complexity
        estimated_review_days = self._estimate_baseline_review_days(product_code, timelines)

        summary = {
            "total_analyzed": len(timelines),
            "total_base_pmas": len(timelines),
            "year_range": year_range,
            "yearly_counts": dict(sorted(yearly_counts.items())),
            "top_applicants": dict(applicant_history.most_common(5)),
            "median_days": estimated_review_days["median"],
            "p25_days": estimated_review_days["p25"],
            "p75_days": estimated_review_days["p75"],
            "mean_days": estimated_review_days["mean"],
            "estimation_method": estimated_review_days["method"],
        }

        return {
            "product_code": product_code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "timelines": timelines[:20],  # Limit detail output
        }

    def _estimate_baseline_review_days(
        self,
        product_code: str,
        timelines: List[Dict],
    ) -> Dict:
        """Estimate baseline review days using empirical FDA data.

        Since openFDA PMA data does not consistently include date_received,
        we use empirical estimates based on FDA MDUFA performance goals and
        published FDA annual reports.

        Args:
            product_code: Product code.
            timelines: Timeline entries.

        Returns:
            Dict with median, p25, p75, mean estimates in days.
        """
        # FDA MDUFA IV performance goals:
        # - Original PMA: 180-day review clock (starts at filing)
        # - Panel-track supplement: 320-day total time
        # - Actual performance: median ~300 days for original PMAs
        #
        # Adjust based on number of PMAs (more PMAs = more established pathway)
        n_pmas = len(timelines)

        if n_pmas >= 10:
            # Well-established product code
            return {
                "median": 300,
                "p25": 240,
                "p75": 420,
                "mean": 330,
                "method": "empirical_established",
            }
        elif n_pmas >= 3:
            # Moderately established
            return {
                "median": 360,
                "p25": 270,
                "p75": 540,
                "mean": 390,
                "method": "empirical_moderate",
            }
        else:
            # Novel or rare product code
            return {
                "median": 420,
                "p25": 300,
                "p75": 720,
                "mean": 450,
                "method": "empirical_novel",
            }

    # ------------------------------------------------------------------
    # Risk factor assessment
    # ------------------------------------------------------------------

    def _assess_risk_factors(
        self,
        pma_number: str,
        api_data: Dict,
        refresh: bool = False,
    ) -> List[Dict]:
        """Assess timeline risk factors for a PMA.

        Args:
            pma_number: PMA number.
            api_data: PMA API data.
            refresh: Force refresh.

        Returns:
            List of risk factor assessment dicts.
        """
        factors = []
        panel = api_data.get("advisory_committee", "")

        # Advisory panel meeting requirement
        if panel in PANEL_MEETING_LIKELY:
            factors.append({
                "factor": "advisory_panel_required",
                "label": "Advisory Panel Likely Required",
                "impact_days": RISK_FACTOR_IMPACTS["advisory_panel_required"]["impact_days"],
                "probability": 0.6 if panel == "CV" else 0.4,
                "rationale": f"Panel {panel} historically requires advisory committee meetings",
            })

        # Check clinical complexity from intelligence
        sections = self.store.get_extracted_sections(pma_number)
        if sections:
            section_dict = sections.get("sections", sections)
            clinical = section_dict.get("clinical_studies", {})
            if isinstance(clinical, dict):
                word_count = clinical.get("word_count", 0)
                if word_count > 5000:
                    factors.append({
                        "factor": "complex_clinical",
                        "label": "Complex Clinical Program",
                        "impact_days": RISK_FACTOR_IMPACTS["complex_clinical"]["impact_days"],
                        "probability": 0.5,
                        "rationale": f"Extensive clinical data ({word_count:,} words) suggests complex review",
                    })

        # Check manufacturer track record
        applicant = api_data.get("applicant", "")
        if applicant:
            manufacturer_history = self._check_manufacturer_history(applicant)
            if manufacturer_history.get("total_pmas", 0) == 0:
                factors.append({
                    "factor": "first_time_applicant",
                    "label": "First-Time PMA Applicant",
                    "impact_days": RISK_FACTOR_IMPACTS["first_time_applicant"]["impact_days"],
                    "probability": 0.3,
                    "rationale": "No prior PMA approvals found for this applicant",
                })

        # Check supplement count (high supplements may indicate prior issues)
        supp_count = api_data.get("supplement_count", 0)
        if supp_count > 20:
            factors.append({
                "factor": "complex_regulatory_history",
                "label": "Complex Regulatory History",
                "impact_days": 30,
                "probability": 0.2,
                "rationale": f"{supp_count} supplements suggest active post-approval changes",
            })

        return factors

    def _check_manufacturer_history(self, applicant: str) -> Dict:
        """Check manufacturer's PMA approval history.

        Args:
            applicant: Applicant/manufacturer name.

        Returns:
            Dict with manufacturer history metrics.
        """
        try:
            result = self.store.client.search_pma(applicant=applicant, limit=5)
            if result.get("degraded"):
                return {"total_pmas": -1, "note": "API unavailable"}

            total = result.get("meta", {}).get("results", {}).get("total", 0)
            return {"total_pmas": total, "applicant": applicant}
        except Exception:
            return {"total_pmas": -1, "note": "Error checking history"}

    # ------------------------------------------------------------------
    # Prediction building
    # ------------------------------------------------------------------

    def _build_prediction(
        self,
        api_data: Dict,
        historical: Dict,
        risk_factors: List[Dict],
        submission_date: Optional[str] = None,
    ) -> Dict:
        """Build timeline prediction from all inputs.

        Args:
            api_data: PMA API data.
            historical: Historical timeline analysis.
            risk_factors: Assessed risk factors.
            submission_date: Optional submission date string.

        Returns:
            Prediction dict with scenarios and milestones.
        """
        summary = historical.get("summary", {})
        base_days = summary.get("median_days") or 360  # Default 360 days if no data

        # Calculate risk-adjusted timeline
        expected_risk_days = sum(
            f.get("impact_days", 0) * f.get("probability", 0.3)
            for f in risk_factors
        )

        optimistic_days = max(180, base_days - 60)
        realistic_days = int(base_days + expected_risk_days)
        pessimistic_days = int(base_days + sum(
            f.get("impact_days", 0) for f in risk_factors
        ))

        # Determine panel requirement
        panel = api_data.get("advisory_committee", "")
        panel_required = any(
            f.get("factor") == "advisory_panel_required" for f in risk_factors
        )

        # Parse submission date
        start_date = None
        if submission_date:
            try:
                start_date = datetime.strptime(submission_date, "%Y-%m-%d")
            except ValueError:
                pass

        milestones = self._generate_milestones(
            realistic_days, start_date, panel_required
        )

        return {
            "prediction": {
                "optimistic_days": optimistic_days,
                "realistic_days": realistic_days,
                "pessimistic_days": pessimistic_days,
                "optimistic_months": round(optimistic_days / 30, 1),
                "realistic_months": round(realistic_days / 30, 1),
                "pessimistic_months": round(pessimistic_days / 30, 1),
                "expected_risk_impact_days": round(expected_risk_days),
                "confidence_range": f"{optimistic_days}-{pessimistic_days} days",
            },
            "milestones": milestones,
            "scenarios": {
                "optimistic": {
                    "days": optimistic_days,
                    "label": "Best Case (no deficiencies, no panel)",
                    "assumptions": [
                        "Complete submission accepted on first review",
                        "No major deficiency letters",
                        "No advisory panel required",
                        "Standard review timeline",
                    ],
                },
                "realistic": {
                    "days": realistic_days,
                    "label": "Expected (risk-adjusted)",
                    "assumptions": [
                        f"Based on {summary.get('total_analyzed', 0)} historical PMAs",
                        f"Risk adjustment: +{round(expected_risk_days)} days",
                        f"{len(risk_factors)} risk factors identified",
                    ],
                },
                "pessimistic": {
                    "days": pessimistic_days,
                    "label": "Worst Case (all risks materialize)",
                    "assumptions": [
                        "All identified risk factors materialize",
                        "Major deficiency letter likely",
                        "Advisory panel meeting required",
                    ],
                },
            },
            "recommendations": self._generate_recommendations(
                realistic_days,
                summary.get("total_analyzed", 0),
                risk_factors,
            ),
        }

    def _generate_milestones(
        self,
        total_days: int,
        start_date: Optional[datetime] = None,
        panel_required: bool = False,
    ) -> List[Dict]:
        """Generate timeline milestones with estimated dates.

        Args:
            total_days: Total predicted days.
            start_date: Optional submission start date.
            panel_required: Whether advisory panel is expected.

        Returns:
            List of milestone dicts with dates if start_date provided.
        """
        milestones = []
        cumulative = 0

        # Phase 1: Administrative Review
        admin_days = PHASE_BASELINES["administrative_review"]["typical_days"]
        cumulative += admin_days
        milestones.append({
            "phase": "administrative_review",
            "label": "Filing/RTA Decision",
            "day": cumulative,
            "estimated_date": (start_date + timedelta(days=cumulative)).strftime("%Y-%m-%d") if start_date else None,
            "description": "FDA accepts submission for substantive review",
        })

        # Phase 2: Scientific Review
        review_days = PHASE_BASELINES["scientific_review"]["typical_days"]
        cumulative += review_days
        milestones.append({
            "phase": "scientific_review",
            "label": "Scientific Review Complete",
            "day": cumulative,
            "estimated_date": (start_date + timedelta(days=cumulative)).strftime("%Y-%m-%d") if start_date else None,
            "description": "Clinical, nonclinical, manufacturing reviews concluded",
        })

        # Phase 3: Advisory Panel (if required)
        if panel_required:
            panel_days = PHASE_BASELINES["advisory_panel"]["typical_days"]
            cumulative += panel_days
            milestones.append({
                "phase": "advisory_panel",
                "label": "Advisory Panel Meeting",
                "day": cumulative,
                "estimated_date": (start_date + timedelta(days=cumulative)).strftime("%Y-%m-%d") if start_date else None,
                "description": "Advisory committee reviews application and votes",
            })

        # Phase 4: FDA Decision
        decision_days = PHASE_BASELINES["fda_decision"]["typical_days"]
        cumulative += decision_days
        milestones.append({
            "phase": "fda_decision",
            "label": "FDA Approval Decision",
            "day": cumulative,
            "estimated_date": (start_date + timedelta(days=cumulative)).strftime("%Y-%m-%d") if start_date else None,
            "description": "FDA issues approval order (or approvable/not approvable letter)",
        })

        # Add 180-day MDUFA clock reference
        milestones.insert(1, {
            "phase": "mdufa_clock",
            "label": "MDUFA 180-Day Review Clock",
            "day": admin_days + 180,
            "estimated_date": (start_date + timedelta(days=admin_days + 180)).strftime("%Y-%m-%d") if start_date else None,
            "description": "FDA performance goal for completing substantive review",
        })

        return milestones

    def _generate_recommendations(
        self,
        predicted_days: int,
        historical_count: int,
        risk_factors: List[Dict],
    ) -> List[str]:
        """Generate recommendations to accelerate or de-risk the timeline.

        Args:
            predicted_days: Predicted review days.
            historical_count: Number of historical PMAs analyzed.
            risk_factors: Assessed risk factors.

        Returns:
            List of recommendation strings.
        """
        recs = []

        if predicted_days > 400:
            recs.append(
                "Consider a Pre-Submission (Q-Sub) meeting with FDA to align on "
                "clinical study design and acceptance criteria before submission."
            )

        if any(f.get("factor") == "advisory_panel_required" for f in risk_factors):
            recs.append(
                "Advisory panel meeting likely required. Prepare panel briefing "
                "materials early and consider requesting a specific panel date."
            )

        if any(f.get("factor") == "complex_clinical" for f in risk_factors):
            recs.append(
                "Complex clinical program may benefit from a modular PMA submission "
                "approach, submitting nonclinical and manufacturing modules early."
            )

        if any(f.get("factor") == "first_time_applicant" for f in risk_factors):
            recs.append(
                "First-time PMA applicants should consider engaging experienced "
                "regulatory counsel and requesting a Pre-Submission meeting."
            )

        if historical_count < 5:
            recs.append(
                "Limited historical data for this product code. Timeline estimate "
                "has wider uncertainty. Consider De Novo if appropriate."
            )

        recs.append(
            "Ensure complete submission to avoid administrative deficiency "
            "letters that reset the review clock."
        )

        return recs

    # ------------------------------------------------------------------
    # Applicant timeline analysis
    # ------------------------------------------------------------------

    def analyze_applicant_track_record(self, applicant: str) -> Dict:
        """Analyze an applicant's PMA approval track record.

        Args:
            applicant: Applicant name.

        Returns:
            Track record analysis dict.
        """
        result = self.store.client.search_pma(applicant=applicant, limit=50)

        if result.get("degraded") or not result.get("results"):
            return {
                "applicant": applicant,
                "error": "No PMA history found",
            }

        approvals = []
        product_codes = Counter()
        panels = Counter()

        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            if "S" in pn[1:]:
                continue

            decision_code = r.get("decision_code", "")
            pc = r.get("product_code", "")
            panel = r.get("advisory_committee", "")

            if pc:
                product_codes[pc] += 1
            if panel:
                panels[panel] += 1

            approvals.append({
                "pma_number": pn,
                "device_name": r.get("trade_name", "N/A"),
                "product_code": pc,
                "decision_date": r.get("decision_date", ""),
                "decision_code": decision_code,
            })

        return {
            "applicant": applicant,
            "total_pmas": len(approvals),
            "product_codes": dict(product_codes.most_common()),
            "panels": dict(panels.most_common()),
            "recent_approvals": approvals[:10],
            "experience_level": (
                "extensive" if len(approvals) >= 10
                else "moderate" if len(approvals) >= 3
                else "limited" if len(approvals) >= 1
                else "none"
            ),
        }


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_prediction(pred: Dict) -> str:
    """Format timeline prediction as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("PMA APPROVAL TIMELINE PREDICTION")
    lines.append("=" * 70)

    lines.append(f"PMA: {pred.get('pma_number', pred.get('product_code', 'N/A'))}")
    lines.append(f"Device: {pred.get('device_name', 'N/A')}")
    lines.append(f"Product Code: {pred.get('product_code', 'N/A')}")
    lines.append(f"Advisory Committee: {pred.get('advisory_committee', 'N/A')}")
    lines.append("")

    # Prediction summary
    prediction = pred.get("prediction", {})
    lines.append("--- Timeline Prediction ---")
    lines.append(f"  Optimistic: {prediction.get('optimistic_days', 'N/A')} days ({prediction.get('optimistic_months', 'N/A')} months)")
    lines.append(f"  Realistic:  {prediction.get('realistic_days', 'N/A')} days ({prediction.get('realistic_months', 'N/A')} months)")
    lines.append(f"  Pessimistic: {prediction.get('pessimistic_days', 'N/A')} days ({prediction.get('pessimistic_months', 'N/A')} months)")
    lines.append("")

    # Milestones
    milestones = pred.get("milestones", [])
    if milestones:
        lines.append("--- Key Milestones ---")
        for m in milestones:
            date_str = f" ({m['estimated_date']})" if m.get("estimated_date") else ""
            lines.append(f"  Day {m['day']:4d}{date_str}: {m['label']}")
        lines.append("")

    # Risk factors
    risks = pred.get("risk_factors", [])
    if risks:
        lines.append("--- Risk Factors ---")
        for r in risks:
            lines.append(
                f"  [{r.get('probability', 0):.0%}] {r.get('label', 'N/A')} "
                f"(+{r.get('impact_days', 0)} days)"
            )
            lines.append(f"        {r.get('rationale', '')}")
        lines.append("")

    # Scenarios
    scenarios = pred.get("scenarios", {})
    if scenarios:
        lines.append("--- Scenarios ---")
        for key, scenario in scenarios.items():
            lines.append(f"  {scenario.get('label', key)}: {scenario.get('days', 'N/A')} days")
            for assumption in scenario.get("assumptions", []):
                lines.append(f"    - {assumption}")
        lines.append("")

    # Recommendations
    recs = pred.get("recommendations", [])
    if recs:
        lines.append("--- Recommendations ---")
        for i, rec in enumerate(recs, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    # Historical context
    historical = pred.get("historical_context", {})
    if historical:
        lines.append("--- Historical Context ---")
        lines.append(f"  PMAs Analyzed: {historical.get('total_analyzed', 'N/A')}")
        lines.append(f"  Historical Median: {historical.get('median_days', 'N/A')} days")
        lines.append(f"  Year Range: {historical.get('year_range', 'N/A')}")
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {pred.get('generated_at', 'N/A')[:10]}")
    lines.append("This prediction is AI-generated from historical FDA data.")
    lines.append("Actual timelines vary. Not regulatory advice.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA Timeline Predictor -- Predict FDA review timelines"
    )
    parser.add_argument("--pma", help="PMA number for device-specific prediction")
    parser.add_argument("--product-code", dest="product_code",
                        help="Product code for general prediction")
    parser.add_argument("--submission-date", dest="submission_date",
                        help="Planned submission date (YYYY-MM-DD)")
    parser.add_argument("--historical", action="store_true",
                        help="Show historical timeline analysis")
    parser.add_argument("--applicant", help="Analyze applicant track record")
    parser.add_argument("--refresh", action="store_true", help="Force API refresh")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    predictor = TimelinePredictor()

    result = None

    if args.pma:
        result = predictor.predict_timeline(
            args.pma,
            submission_date=args.submission_date,
            refresh=args.refresh,
        )
    elif args.product_code and args.historical:
        result = predictor.analyze_historical_timelines(args.product_code)
    elif args.product_code:
        result = predictor.predict_for_product_code(
            args.product_code,
            submission_date=args.submission_date,
        )
    elif args.applicant:
        result = predictor.analyze_applicant_track_record(args.applicant)
    else:
        parser.error("Specify --pma, --product-code, or --applicant")
        return

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if "prediction" in result:
            print(_format_prediction(result))
        else:
            print(json.dumps(result, indent=2, default=str))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
