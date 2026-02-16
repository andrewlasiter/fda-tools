#!/usr/bin/env python3
"""
Regulatory Pathway Recommender -- Decision tree algorithm for optimal FDA pathway.

Implements a decision tree algorithm to recommend the optimal regulatory pathway
(510(k) Traditional/Special/Abbreviated, PMA, or De Novo) based on device
characteristics, intended use, technological characteristics, and PMA precedent.

Provides confidence-scored recommendations with cost, timeline, and clinical
evidence requirement comparisons across all pathways.

Integrates with PMA Data Store for PMA history analysis and FDAClient for
classification data.

Usage:
    from pathway_recommender import PathwayRecommender

    recommender = PathwayRecommender()
    recommendation = recommender.recommend("NMH", device_info={...})
    comparison = recommender.compare_pathways("NMH")

    # CLI usage:
    python3 pathway_recommender.py --product-code NMH
    python3 pathway_recommender.py --product-code NMH --device-description "..."
    python3 pathway_recommender.py --product-code NMH --novel-features "..."
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_api_client import FDAClient
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Pathway definitions with baseline characteristics
# ------------------------------------------------------------------

PATHWAY_DEFINITIONS = {
    "traditional_510k": {
        "label": "Traditional 510(k)",
        "description": "Standard substantial equivalence comparison to a legally marketed predicate device",
        "typical_timeline_months": (3, 12),
        "typical_cost": (20000, 200000),
        "clinical_data": "Often not required (bench testing may suffice)",
        "approval_rate": 85,
        "user_fee_2025": 22604,
        "requires_clinical": False,
    },
    "special_510k": {
        "label": "Special 510(k)",
        "description": "Streamlined review for modifications to your own cleared device",
        "typical_timeline_months": (2, 6),
        "typical_cost": (15000, 100000),
        "clinical_data": "Rarely required (design control documentation)",
        "approval_rate": 90,
        "user_fee_2025": 22604,
        "requires_clinical": False,
    },
    "abbreviated_510k": {
        "label": "Abbreviated 510(k)",
        "description": "Reliance on FDA guidance documents and recognized consensus standards",
        "typical_timeline_months": (3, 9),
        "typical_cost": (20000, 150000),
        "clinical_data": "Not typically required",
        "approval_rate": 85,
        "user_fee_2025": 22604,
        "requires_clinical": False,
    },
    "de_novo": {
        "label": "De Novo Classification",
        "description": "Novel device classification for low-to-moderate risk devices without predicates",
        "typical_timeline_months": (9, 18),
        "typical_cost": (100000, 500000),
        "clinical_data": "May be required depending on risk",
        "approval_rate": 60,
        "user_fee_2025": 130682,
        "requires_clinical": "maybe",
    },
    "pma": {
        "label": "Premarket Approval (PMA)",
        "description": "Full premarket review for Class III devices requiring clinical evidence of safety and effectiveness",
        "typical_timeline_months": (12, 36),
        "typical_cost": (500000, 5000000),
        "clinical_data": "Required (clinical trial data)",
        "approval_rate": 50,
        "user_fee_2025": 441968,
        "requires_clinical": True,
    },
}

# ------------------------------------------------------------------
# Decision factors and weights
# ------------------------------------------------------------------

# Maximum score per pathway = 100 points

SCORING_FACTORS = {
    "traditional_510k": {
        "predicate_availability": {"max_points": 30, "description": "Same product code predicates exist"},
        "recent_predicates": {"max_points": 20, "description": "3+ clearances in last 5 years"},
        "no_novel_technology": {"max_points": 20, "description": "No novel technological features"},
        "device_class_ii": {"max_points": 15, "description": "Device is Class II"},
        "guidance_exists": {"max_points": 15, "description": "FDA guidance found"},
    },
    "special_510k": {
        "own_prior_clearance": {"max_points": 40, "description": "Modifying own cleared device"},
        "modification_type": {"max_points": 30, "description": "Device modification context"},
        "design_controls": {"max_points": 20, "description": "Design controls documented"},
        "no_ifu_change": {"max_points": 10, "description": "Intended use unchanged"},
    },
    "abbreviated_510k": {
        "strong_guidance": {"max_points": 40, "description": "Device-specific guidance exists"},
        "consensus_standards": {"max_points": 30, "description": "Recognized standards cover testing"},
        "standard_comparison": {"max_points": 20, "description": "Straightforward predicate comparison"},
        "no_clinical_data": {"max_points": 10, "description": "Clinical data not required"},
    },
    "de_novo": {
        "no_predicates": {"max_points": 40, "description": "No/very few predicates available"},
        "novel_device": {"max_points": 30, "description": "Novel technological features"},
        "low_moderate_risk": {"max_points": 20, "description": "Low-to-moderate risk profile"},
        "de_novo_precedent": {"max_points": 10, "description": "Existing De Novo classification available"},
    },
    "pma": {
        "class_iii": {"max_points": 40, "description": "Device is Class III"},
        "high_risk": {"max_points": 30, "description": "Life-sustaining/life-supporting"},
        "clinical_required": {"max_points": 20, "description": "Clinical trial data needed"},
        "no_predicates": {"max_points": 10, "description": "No suitable 510(k) predicates"},
    },
}

# ------------------------------------------------------------------
# Novel technology indicators
# ------------------------------------------------------------------

NOVEL_TECHNOLOGY_KEYWORDS = [
    "artificial intelligence", "machine learning", "deep learning",
    "nanotechnology", "nanoparticle", "gene therapy", "gene editing",
    "CRISPR", "3D printing", "additive manufacturing",
    "blockchain", "digital therapeutic", "augmented reality",
    "virtual reality", "robotics", "autonomous", "adaptive algorithm",
    "personalized", "patient-specific", "point-of-care manufacturing",
    "bioprinting", "organoid", "tissue engineering",
    "wireless", "Bluetooth", "IoT", "cloud-connected",
]

# ------------------------------------------------------------------
# High risk device indicators
# ------------------------------------------------------------------

HIGH_RISK_KEYWORDS = [
    "life-sustaining", "life-supporting", "implantable",
    "implanted", "permanent implant", "critical care",
    "cardiac", "vascular", "neurological stimulation",
    "drug delivery", "combination product",
]


# ------------------------------------------------------------------
# Pathway Recommender
# ------------------------------------------------------------------

class PathwayRecommender:
    """Decision tree algorithm to recommend optimal FDA regulatory pathway.

    Analyzes device characteristics, predicate availability, classification
    data, PMA history, and novel technology indicators to score each
    regulatory pathway and recommend the optimal submission strategy.
    """

    def __init__(
        self,
        client: Optional[FDAClient] = None,
        pma_store: Optional[PMADataStore] = None,
    ):
        """Initialize Pathway Recommender.

        Args:
            client: Optional FDAClient instance.
            pma_store: Optional PMADataStore instance.
        """
        self.client = client or FDAClient()
        self.pma_store = pma_store or PMADataStore(client=self.client)

    # ------------------------------------------------------------------
    # Main recommendation
    # ------------------------------------------------------------------

    def recommend(
        self,
        product_code: str,
        device_info: Optional[Dict] = None,
        own_predicate: Optional[str] = None,
    ) -> Dict:
        """Recommend optimal regulatory pathway for a device.

        Args:
            product_code: FDA product code.
            device_info: Optional device information dict:
                - device_description: Text description of the device
                - intended_use: Intended use statement
                - novel_features: Novel technology description
                - modification: True if modifying existing device
            own_predicate: K-number of own prior cleared device (for Special 510(k)).

        Returns:
            Pathway recommendation dict with scores, rationale, and comparison.
        """
        device_info = device_info or {}

        # Step 1: Gather classification data
        classification = self._get_classification_data(product_code)

        # Step 2: Check predicate availability
        predicate_analysis = self._analyze_predicates(product_code)

        # Step 3: Check PMA history
        pma_history = self._analyze_pma_history(product_code)

        # Step 4: Assess device characteristics
        device_assessment = self._assess_device_characteristics(
            classification, device_info, predicate_analysis, pma_history
        )

        # Step 5: Score each pathway
        pathway_scores = self._score_all_pathways(
            classification, predicate_analysis, pma_history,
            device_assessment, device_info, own_predicate,
        )

        # Step 6: Rank and recommend
        ranked = sorted(
            pathway_scores.items(),
            key=lambda x: x[1]["total_score"],
            reverse=True,
        )

        recommended_pathway = ranked[0][0]
        recommended_score = ranked[0][1]["total_score"]

        # Step 7: Generate comparison table
        comparison = self._build_comparison_table(pathway_scores)

        # Step 8: Generate strategic considerations
        considerations = self._generate_considerations(
            recommended_pathway, classification, predicate_analysis,
            pma_history, device_assessment,
        )

        return {
            "product_code": product_code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "classification": classification,
            "recommended_pathway": {
                "pathway": recommended_pathway,
                "label": PATHWAY_DEFINITIONS[recommended_pathway]["label"],
                "score": recommended_score,
                "confidence": self._score_to_confidence(recommended_score),
                "rationale": pathway_scores[recommended_pathway]["rationale"],
            },
            "all_pathways": {
                pw: {
                    "label": PATHWAY_DEFINITIONS[pw]["label"],
                    "score": data["total_score"],
                    "breakdown": data["breakdown"],
                    "rationale": data["rationale"],
                }
                for pw, data in ranked
            },
            "ranking": [
                {
                    "rank": i + 1,
                    "pathway": pw,
                    "label": PATHWAY_DEFINITIONS[pw]["label"],
                    "score": data["total_score"],
                }
                for i, (pw, data) in enumerate(ranked)
            ],
            "comparison_table": comparison,
            "considerations": considerations,
            "predicate_analysis": predicate_analysis,
            "pma_history": pma_history,
            "device_assessment": device_assessment,
        }

    # ------------------------------------------------------------------
    # Pathway comparison
    # ------------------------------------------------------------------

    def compare_pathways(self, product_code: str) -> Dict:
        """Compare all pathways for a product code without specific device info.

        Args:
            product_code: FDA product code.

        Returns:
            Pathway comparison dict.
        """
        return self.recommend(product_code)

    # ------------------------------------------------------------------
    # Classification data
    # ------------------------------------------------------------------

    def _get_classification_data(self, product_code: str) -> Dict:
        """Get device classification data from openFDA.

        Args:
            product_code: Product code.

        Returns:
            Classification data dict.
        """
        result = self.client.get_classification(product_code)

        if result.get("degraded") or not result.get("results"):
            return {
                "product_code": product_code,
                "device_class": "unknown",
                "error": "Classification data unavailable",
            }

        data = result["results"][0]
        return {
            "product_code": product_code,
            "device_class": data.get("device_class", "unknown"),
            "device_name": data.get("device_name", "N/A"),
            "regulation_number": data.get("regulation_number", ""),
            "review_panel": data.get("review_panel", ""),
            "medical_specialty": data.get("medical_specialty_description", ""),
            "gmp_exempt": data.get("gmp_exempt_flag", "N") == "Y",
        }

    # ------------------------------------------------------------------
    # Predicate analysis
    # ------------------------------------------------------------------

    def _analyze_predicates(self, product_code: str) -> Dict:
        """Analyze predicate availability for a product code.

        Args:
            product_code: Product code.

        Returns:
            Predicate analysis dict.
        """
        # Get total clearances
        result = self.client.get_clearances(product_code, limit=1)
        total_clearances = result.get("meta", {}).get("results", {}).get("total", 0)

        # Get recent clearances (last 5 years)
        recent_result = self.client.search_pma(
            product_code=product_code, year_start=2021, limit=1
        )
        # For 510k, use separate search
        recent_510k = 0
        try:
            recent_search = self.client._request(
                "510k",
                {
                    "search": f'product_code:"{product_code}"+AND+decision_date:[20210101+TO+29991231]',
                    "limit": "1",
                },
            )
            recent_510k = recent_search.get("meta", {}).get("results", {}).get("total", 0)
        except Exception:
            pass

        return {
            "product_code": product_code,
            "total_clearances": total_clearances,
            "recent_clearances_5yr": recent_510k,
            "predicate_available": total_clearances > 0,
            "strong_predicate_base": total_clearances >= 10,
            "recent_activity": recent_510k >= 3,
        }

    # ------------------------------------------------------------------
    # PMA history analysis
    # ------------------------------------------------------------------

    def _analyze_pma_history(self, product_code: str) -> Dict:
        """Analyze PMA approval history for a product code.

        Args:
            product_code: Product code.

        Returns:
            PMA history analysis dict.
        """
        result = self.client.get_pma_by_product_code(product_code, limit=5)

        if result.get("degraded") or not result.get("results"):
            total = 0
            recent = None
        else:
            # Count base PMAs only
            total = 0
            recent = None
            for r in result.get("results", []):
                pn = r.get("pma_number", "")
                if "S" not in pn[1:]:
                    total += 1
                    if recent is None:
                        recent = {
                            "pma_number": pn,
                            "device_name": r.get("trade_name", "N/A"),
                            "decision_date": r.get("decision_date", ""),
                        }

        return {
            "product_code": product_code,
            "pma_count": total,
            "has_pma_history": total > 0,
            "most_recent_pma": recent,
            "established_pma_pathway": total >= 3,
        }

    # ------------------------------------------------------------------
    # Device characteristic assessment
    # ------------------------------------------------------------------

    def _assess_device_characteristics(
        self,
        classification: Dict,
        device_info: Dict,
        predicate_analysis: Dict,
        pma_history: Dict,
    ) -> Dict:
        """Assess device characteristics for pathway scoring.

        Args:
            classification: Classification data.
            device_info: User-provided device info.
            predicate_analysis: Predicate analysis results.
            pma_history: PMA history analysis.

        Returns:
            Device assessment dict.
        """
        device_class = classification.get("device_class", "unknown")
        description = device_info.get("device_description", "")
        novel_features = device_info.get("novel_features", "")
        combined_text = f"{description} {novel_features}".lower()

        # Novel technology detection
        novel_tech = False
        novel_matches = []
        for keyword in NOVEL_TECHNOLOGY_KEYWORDS:
            if keyword.lower() in combined_text:
                novel_tech = True
                novel_matches.append(keyword)

        # High risk detection
        high_risk = device_class == "3"
        high_risk_matches = []
        for keyword in HIGH_RISK_KEYWORDS:
            if keyword.lower() in combined_text:
                high_risk = True
                high_risk_matches.append(keyword)

        # Determine if clinical data likely needed
        clinical_likely = high_risk or device_class == "3" or (
            novel_tech and not predicate_analysis.get("strong_predicate_base")
        )

        return {
            "device_class": device_class,
            "is_class_iii": device_class == "3",
            "is_class_ii": device_class == "2",
            "is_class_i": device_class == "1",
            "novel_technology": novel_tech,
            "novel_technology_matches": novel_matches,
            "high_risk": high_risk,
            "high_risk_matches": high_risk_matches,
            "clinical_data_likely": clinical_likely,
            "has_predicates": predicate_analysis.get("predicate_available", False),
            "has_pma_precedent": pma_history.get("has_pma_history", False),
        }

    # ------------------------------------------------------------------
    # Pathway scoring
    # ------------------------------------------------------------------

    def _score_all_pathways(
        self,
        classification: Dict,
        predicate_analysis: Dict,
        pma_history: Dict,
        device_assessment: Dict,
        device_info: Dict,
        own_predicate: Optional[str] = None,
    ) -> Dict:
        """Score all pathways based on available evidence.

        Args:
            classification: Classification data.
            predicate_analysis: Predicate analysis.
            pma_history: PMA history.
            device_assessment: Device assessment.
            device_info: User device info.
            own_predicate: Own prior clearance K-number.

        Returns:
            Dict of pathway scores.
        """
        scores = {}

        scores["traditional_510k"] = self._score_traditional_510k(
            classification, predicate_analysis, device_assessment
        )
        scores["special_510k"] = self._score_special_510k(
            classification, device_assessment, device_info, own_predicate
        )
        scores["abbreviated_510k"] = self._score_abbreviated_510k(
            classification, predicate_analysis, device_assessment
        )
        scores["de_novo"] = self._score_de_novo(
            classification, predicate_analysis, device_assessment, pma_history
        )
        scores["pma"] = self._score_pma(
            classification, predicate_analysis, device_assessment, pma_history
        )

        return scores

    def _score_traditional_510k(
        self,
        classification: Dict,
        predicate_analysis: Dict,
        device_assessment: Dict,
    ) -> Dict:
        """Score Traditional 510(k) pathway."""
        breakdown = {}
        rationale = []
        total = 0

        # Predicate availability (30 pts)
        if predicate_analysis.get("predicate_available"):
            pts = 30
            breakdown["predicate_availability"] = pts
            rationale.append(f"Predicates available ({predicate_analysis.get('total_clearances', 0)} clearances)")
        else:
            pts = 0
            breakdown["predicate_availability"] = pts
            rationale.append("No predicates available (-30)")
        total += pts

        # Recent predicates (20 pts)
        if predicate_analysis.get("recent_activity"):
            pts = 20
            breakdown["recent_predicates"] = pts
            rationale.append("Active recent clearance activity")
        elif predicate_analysis.get("predicate_available"):
            pts = 10
            breakdown["recent_predicates"] = pts
            rationale.append("Predicates exist but limited recent activity")
        else:
            pts = 0
            breakdown["recent_predicates"] = pts
        total += pts

        # No novel technology (20 pts)
        if not device_assessment.get("novel_technology"):
            pts = 20
            breakdown["no_novel_technology"] = pts
            rationale.append("No novel technology detected")
        else:
            pts = 0
            breakdown["no_novel_technology"] = pts
            rationale.append("Novel technology reduces 510(k) suitability")
        total += pts

        # Device class (15 pts)
        if device_assessment.get("is_class_ii"):
            pts = 15
            breakdown["device_class_ii"] = pts
            rationale.append("Class II device (standard for 510(k))")
        elif device_assessment.get("is_class_i"):
            pts = 10
            breakdown["device_class_ii"] = pts
            rationale.append("Class I device (may not need 510(k))")
        else:
            pts = 0
            breakdown["device_class_ii"] = pts
            rationale.append("Class III device typically requires PMA")
        total += pts

        # Guidance exists (15 pts)
        reg_num = classification.get("regulation_number", "")
        if reg_num:
            pts = 15
            breakdown["guidance_exists"] = pts
            rationale.append(f"Regulation {reg_num} provides framework")
        else:
            pts = 5
            breakdown["guidance_exists"] = pts
        total += pts

        return {"total_score": total, "breakdown": breakdown, "rationale": rationale}

    def _score_special_510k(
        self,
        classification: Dict,
        device_assessment: Dict,
        device_info: Dict,
        own_predicate: Optional[str] = None,
    ) -> Dict:
        """Score Special 510(k) pathway."""
        breakdown = {}
        rationale = []
        total = 0

        # Own prior clearance (40 pts)
        if own_predicate:
            pts = 40
            breakdown["own_prior_clearance"] = pts
            rationale.append(f"Modifying own cleared device ({own_predicate})")
        else:
            pts = 0
            breakdown["own_prior_clearance"] = pts
            rationale.append("No own prior clearance provided")
        total += pts

        # Modification type (30 pts)
        is_modification = device_info.get("modification", False)
        if is_modification or own_predicate:
            pts = 30
            breakdown["modification_type"] = pts
            rationale.append("Device modification identified")
        else:
            pts = 0
            breakdown["modification_type"] = pts
        total += pts

        # Design controls (20 pts)
        if device_assessment.get("is_class_ii"):
            pts = 20
            breakdown["design_controls"] = pts
            rationale.append("Class II requires design controls (supports Special 510(k))")
        else:
            pts = 10
            breakdown["design_controls"] = pts
        total += pts

        # No IFU change (10 pts)
        ifu_change = device_info.get("ifu_change", False)
        if not ifu_change:
            pts = 10
            breakdown["no_ifu_change"] = pts
            rationale.append("No indication for use change")
        else:
            pts = 0
            breakdown["no_ifu_change"] = pts
            rationale.append("IFU change limits Special 510(k) eligibility")
        total += pts

        return {"total_score": total, "breakdown": breakdown, "rationale": rationale}

    def _score_abbreviated_510k(
        self,
        classification: Dict,
        predicate_analysis: Dict,
        device_assessment: Dict,
    ) -> Dict:
        """Score Abbreviated 510(k) pathway."""
        breakdown = {}
        rationale = []
        total = 0

        # Strong guidance (40 pts)
        reg_num = classification.get("regulation_number", "")
        if reg_num:
            pts = 30  # Partial credit for having regulation number
            breakdown["strong_guidance"] = pts
            rationale.append(f"Regulation {reg_num} provides regulatory framework")
        else:
            pts = 0
            breakdown["strong_guidance"] = pts
        total += pts

        # Consensus standards (30 pts)
        # Approximate based on device class and predicate base
        if predicate_analysis.get("strong_predicate_base"):
            pts = 25
            breakdown["consensus_standards"] = pts
            rationale.append("Established product code likely has recognized standards")
        elif predicate_analysis.get("predicate_available"):
            pts = 15
            breakdown["consensus_standards"] = pts
            rationale.append("Some standards likely available")
        else:
            pts = 0
            breakdown["consensus_standards"] = pts
        total += pts

        # Standard comparison (20 pts)
        if predicate_analysis.get("predicate_available") and not device_assessment.get("novel_technology"):
            pts = 20
            breakdown["standard_comparison"] = pts
            rationale.append("Straightforward predicate comparison possible")
        else:
            pts = 5
            breakdown["standard_comparison"] = pts
        total += pts

        # No clinical data (10 pts)
        if not device_assessment.get("clinical_data_likely"):
            pts = 10
            breakdown["no_clinical_data"] = pts
            rationale.append("Clinical data not expected to be required")
        else:
            pts = 0
            breakdown["no_clinical_data"] = pts
        total += pts

        return {"total_score": total, "breakdown": breakdown, "rationale": rationale}

    def _score_de_novo(
        self,
        classification: Dict,
        predicate_analysis: Dict,
        device_assessment: Dict,
        pma_history: Dict,
    ) -> Dict:
        """Score De Novo pathway."""
        breakdown = {}
        rationale = []
        total = 0

        # No predicates (40 pts)
        clearances = predicate_analysis.get("total_clearances", 0)
        if clearances == 0:
            pts = 40
            breakdown["no_predicates"] = pts
            rationale.append("No predicate devices found (strong De Novo indicator)")
        elif clearances <= 3:
            pts = 25
            breakdown["no_predicates"] = pts
            rationale.append("Very few predicates (De Novo may be appropriate)")
        else:
            pts = 0
            breakdown["no_predicates"] = pts
            rationale.append("Sufficient predicates exist for 510(k)")
        total += pts

        # Novel device (30 pts)
        if device_assessment.get("novel_technology"):
            pts = 30
            breakdown["novel_device"] = pts
            matches = device_assessment.get("novel_technology_matches", [])
            rationale.append(f"Novel technology detected: {', '.join(matches[:3])}")
        else:
            pts = 0
            breakdown["novel_device"] = pts
        total += pts

        # Low-moderate risk (20 pts)
        if device_assessment.get("is_class_i") or device_assessment.get("is_class_ii"):
            pts = 20
            breakdown["low_moderate_risk"] = pts
            rationale.append("Low-to-moderate risk profile suitable for De Novo")
        elif not device_assessment.get("high_risk"):
            pts = 10
            breakdown["low_moderate_risk"] = pts
            rationale.append("Risk profile may be suitable for De Novo")
        else:
            pts = 0
            breakdown["low_moderate_risk"] = pts
            rationale.append("High-risk profile less suitable for De Novo")
        total += pts

        # PMA history penalty
        if pma_history.get("has_pma_history"):
            total = max(0, total - 10)
            rationale.append("PMA history for product code reduces De Novo likelihood (-10)")

        # De Novo precedent (10 pts)
        breakdown["de_novo_precedent"] = 0  # Would need De Novo database search
        total += 0

        return {"total_score": total, "breakdown": breakdown, "rationale": rationale}

    def _score_pma(
        self,
        classification: Dict,
        predicate_analysis: Dict,
        device_assessment: Dict,
        pma_history: Dict,
    ) -> Dict:
        """Score PMA pathway."""
        breakdown = {}
        rationale = []
        total = 0

        # Class III (40 pts)
        if device_assessment.get("is_class_iii"):
            pts = 40
            breakdown["class_iii"] = pts
            rationale.append("Class III device (PMA is primary pathway)")
        else:
            pts = 0
            breakdown["class_iii"] = pts
            if device_assessment.get("is_class_ii"):
                rationale.append("Class II device does not typically require PMA")
        total += pts

        # High risk (30 pts)
        if device_assessment.get("high_risk"):
            pts = 30
            breakdown["high_risk"] = pts
            matches = device_assessment.get("high_risk_matches", [])
            rationale.append(f"High-risk characteristics: {', '.join(matches[:3])}")
        else:
            pts = 0
            breakdown["high_risk"] = pts
        total += pts

        # Clinical required (20 pts)
        if device_assessment.get("clinical_data_likely"):
            pts = 20
            breakdown["clinical_required"] = pts
            rationale.append("Clinical trial data expected to be required")
        else:
            pts = 0
            breakdown["clinical_required"] = pts
        total += pts

        # No predicates (10 pts)
        if not predicate_analysis.get("predicate_available"):
            pts = 10
            breakdown["no_predicates"] = pts
            rationale.append("No 510(k) predicates available")
        else:
            pts = 0
            breakdown["no_predicates"] = pts
        total += pts

        # PMA history bonus
        if pma_history.get("has_pma_history"):
            total += 15
            rationale.append(f"Established PMA pathway ({pma_history.get('pma_count', 0)} prior PMAs) (+15)")

        return {"total_score": min(total, 100), "breakdown": breakdown, "rationale": rationale}

    # ------------------------------------------------------------------
    # Comparison table
    # ------------------------------------------------------------------

    def _build_comparison_table(self, pathway_scores: Dict) -> List[Dict]:
        """Build pathway comparison table.

        Args:
            pathway_scores: Dict of pathway scores.

        Returns:
            List of comparison rows.
        """
        rows = []
        ranked = sorted(
            pathway_scores.items(),
            key=lambda x: x[1]["total_score"],
            reverse=True,
        )

        for rank, (pw, data) in enumerate(ranked, 1):
            definition = PATHWAY_DEFINITIONS[pw]
            timeline = definition["typical_timeline_months"]
            cost = definition["typical_cost"]

            rows.append({
                "rank": rank,
                "pathway": pw,
                "label": definition["label"],
                "score": data["total_score"],
                "confidence": self._score_to_confidence(data["total_score"]),
                "timeline_range": f"{timeline[0]}-{timeline[1]} months",
                "cost_range": f"${cost[0]:,}-${cost[1]:,}",
                "clinical_data": definition["clinical_data"],
                "approval_rate": f"{definition['approval_rate']}%",
                "user_fee": f"${definition['user_fee_2025']:,}",
            })

        return rows

    # ------------------------------------------------------------------
    # Strategic considerations
    # ------------------------------------------------------------------

    def _generate_considerations(
        self,
        recommended: str,
        classification: Dict,
        predicate_analysis: Dict,
        pma_history: Dict,
        device_assessment: Dict,
    ) -> List[str]:
        """Generate strategic considerations for the recommendation.

        Args:
            recommended: Recommended pathway.
            classification: Classification data.
            predicate_analysis: Predicate analysis.
            pma_history: PMA history.
            device_assessment: Device assessment.

        Returns:
            List of consideration strings.
        """
        considerations = []

        if recommended in ("traditional_510k", "special_510k", "abbreviated_510k"):
            if device_assessment.get("novel_technology"):
                considerations.append(
                    "Novel technology detected. FDA may question substantial equivalence. "
                    "Consider Pre-Submission meeting to confirm pathway appropriateness."
                )
            if not predicate_analysis.get("recent_activity"):
                considerations.append(
                    "Limited recent clearance activity for this product code. "
                    "Verify predicates are still legally marketed."
                )

        if recommended == "de_novo":
            considerations.append(
                "De Novo requires demonstrating the device is low-to-moderate risk. "
                "Prepare robust risk analysis and special controls proposal."
            )
            if pma_history.get("has_pma_history"):
                considerations.append(
                    "PMA history exists for this product code. FDA may question "
                    "De Novo classification if comparable devices required PMA."
                )

        if recommended == "pma":
            considerations.append(
                "PMA requires clinical trial evidence. Begin clinical study planning "
                "early. Consider Pre-Submission meeting for protocol agreement."
            )
            if pma_history.get("has_pma_history"):
                most_recent = pma_history.get("most_recent_pma", {})
                if most_recent:
                    considerations.append(
                        f"Reference PMA: {most_recent.get('pma_number', 'N/A')} "
                        f"({most_recent.get('device_name', 'N/A')}). "
                        "Review this PMA's SSED for clinical study design precedent."
                    )

        if device_assessment.get("is_class_iii") and recommended != "pma":
            considerations.append(
                "WARNING: Device is Class III. Verify that selected pathway is "
                "appropriate. Class III typically requires PMA unless reclassified."
            )

        considerations.append(
            "Confirm pathway selection with FDA through a Pre-Submission (Q-Sub) meeting "
            "before investing in submission preparation."
        )

        return considerations

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_confidence(score: int) -> str:
        """Map score to confidence level.

        Args:
            score: Pathway score (0-100).

        Returns:
            Confidence level string.
        """
        if score >= 80:
            return "HIGH"
        elif score >= 60:
            return "MODERATE"
        elif score >= 40:
            return "LOW"
        else:
            return "UNLIKELY"


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_recommendation(rec: Dict) -> str:
    """Format recommendation as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("FDA REGULATORY PATHWAY RECOMMENDATION")
    lines.append("=" * 70)

    cls = rec.get("classification", {})
    lines.append(f"Product Code: {cls.get('product_code', 'N/A')}")
    lines.append(f"Device: {cls.get('device_name', 'N/A')}")
    lines.append(f"Class: {cls.get('device_class', 'N/A')}")
    lines.append(f"Regulation: 21 CFR {cls.get('regulation_number', 'N/A')}")
    lines.append("")

    # Recommended pathway
    recommended = rec.get("recommended_pathway", {})
    lines.append("--- RECOMMENDED PATHWAY ---")
    lines.append(f"  {recommended.get('label', 'N/A')} -- Score: {recommended.get('score', 0)}/100 ({recommended.get('confidence', 'N/A')})")
    lines.append("")
    lines.append("  Rationale:")
    for r in recommended.get("rationale", []):
        lines.append(f"    - {r}")
    lines.append("")

    # Ranking table
    lines.append("--- ALL PATHWAYS RANKED ---")
    lines.append(f"  {'#':>2s} {'Pathway':<25s} {'Score':>6s} {'Timeline':<18s} {'Cost':<22s} {'Clinical':>10s}")
    lines.append(f"  {'-'*2} {'-'*25} {'-'*6} {'-'*18} {'-'*22} {'-'*10}")
    for row in rec.get("comparison_table", []):
        lines.append(
            f"  {row['rank']:2d} {row['label']:<25s} "
            f"{row['score']:5d}  {row['timeline_range']:<18s} "
            f"{row['cost_range']:<22s} {row['approval_rate']:>10s}"
        )
    lines.append("")

    # Considerations
    considerations = rec.get("considerations", [])
    if considerations:
        lines.append("--- STRATEGIC CONSIDERATIONS ---")
        for i, c in enumerate(considerations, 1):
            lines.append(f"  {i}. {c}")
        lines.append("")

    # PMA context
    pma_history = rec.get("pma_history", {})
    if pma_history.get("has_pma_history"):
        lines.append("--- PMA PATHWAY CONTEXT ---")
        lines.append(f"  PMA History: {pma_history.get('pma_count', 0)} PMAs for this product code")
        recent = pma_history.get("most_recent_pma", {})
        if recent:
            lines.append(f"  Most Recent: {recent.get('pma_number', 'N/A')} ({recent.get('device_name', 'N/A')})")
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {rec.get('generated_at', 'N/A')[:10]}")
    lines.append("This recommendation is AI-generated. Verify with FDA and qualified RA professionals.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Regulatory Pathway Recommender -- Optimal FDA pathway selection"
    )
    parser.add_argument("--product-code", dest="product_code",
                        help="FDA product code", required=True)
    parser.add_argument("--device-description", dest="device_description",
                        help="Device description text")
    parser.add_argument("--novel-features", dest="novel_features",
                        help="Novel technology features")
    parser.add_argument("--intended-use", dest="intended_use",
                        help="Intended use statement")
    parser.add_argument("--own-predicate", dest="own_predicate",
                        help="Own prior clearance K-number (for Special 510(k))")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    device_info = {}
    if args.device_description:
        device_info["device_description"] = args.device_description
    if args.novel_features:
        device_info["novel_features"] = args.novel_features
    if args.intended_use:
        device_info["intended_use"] = args.intended_use

    recommender = PathwayRecommender()
    result = recommender.recommend(
        args.product_code,
        device_info=device_info if device_info else None,
        own_predicate=args.own_predicate,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(_format_recommendation(result))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
