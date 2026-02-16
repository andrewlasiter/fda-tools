#!/usr/bin/env python3
"""
PMA Comparison Engine -- Multi-PMA comparison with similarity scoring.

Compares PMAs across multiple dimensions: indications, clinical data,
device specifications, safety profiles, and regulatory history. Produces
structured comparison matrices with weighted similarity scores.

Leverages Phase 0 infrastructure (PMADataStore, PMAExtractor, FDAClient)
for data retrieval and section extraction.

Comparison dimensions and weights:
    - Indications for Use:  30%  (most critical for regulatory pathway)
    - Clinical Data:        25%  (study design, endpoints, enrollment)
    - Device Specifications: 20% (technology, materials, form factor)
    - Safety Profile:       15%  (adverse events, risks, contraindications)
    - Regulatory History:   10%  (supplements, panel, pathway)

Usage:
    from pma_comparison import PMAComparisonEngine

    engine = PMAComparisonEngine()
    result = engine.compare_pmas("P170019", ["P160035", "P150009"])
    result = engine.compare_pmas("P170019", ["P160035"], focus_areas=["clinical"])

    # CLI usage:
    python3 pma_comparison.py --primary P170019 --comparators P160035,P150009
    python3 pma_comparison.py --primary P170019 --comparators P160035 --focus clinical
    python3 pma_comparison.py --product-code NMH --competitive
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore
from pma_section_extractor import PMAExtractor


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

# Comparison dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS = {
    "indications": 0.30,
    "clinical_data": 0.25,
    "device_specs": 0.20,
    "safety_profile": 0.15,
    "regulatory_history": 0.10,
}

# Similarity thresholds
SIMILARITY_HIGH = 75       # >= 75: Highly similar
SIMILARITY_MODERATE = 50   # >= 50: Moderately similar
SIMILARITY_LOW = 25        # >= 25: Some overlap
# < 25: Minimal similarity

# Comparison cache TTL in seconds (7 days)
COMPARISON_CACHE_TTL = 7 * 24 * 60 * 60

# Section mappings: comparison dimension -> SSED section keys
DIMENSION_SECTIONS = {
    "indications": ["indications_for_use"],
    "clinical_data": ["clinical_studies", "statistical_analysis"],
    "device_specs": ["device_description", "manufacturing", "nonclinical_testing"],
    "safety_profile": ["potential_risks", "preclinical_studies", "benefit_risk"],
    "regulatory_history": ["general_information", "marketing_history", "panel_recommendation"],
}


# ------------------------------------------------------------------
# Text similarity utilities
# ------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, removing punctuation.

    Args:
        text: Raw text string.

    Returns:
        List of lowercase word tokens.
    """
    if not text:
        return []
    # Remove punctuation, lowercase, split on whitespace
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in cleaned.split() if len(w) > 2]


def _word_overlap_score(text1: str, text2: str) -> float:
    """Calculate word overlap (Jaccard similarity) between two texts.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Jaccard similarity coefficient (0.0 to 1.0).
    """
    tokens1 = set(_tokenize(text1))
    tokens2 = set(_tokenize(text2))

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union) if union else 0.0


def _key_term_overlap(text1: str, text2: str, key_terms: List[str]) -> float:
    """Calculate overlap of specific key terms between two texts.

    Gives higher weight to domain-specific terms.

    Args:
        text1: First text.
        text2: Second text.
        key_terms: List of key terms to check for.

    Returns:
        Fraction of key terms present in both texts (0.0 to 1.0).
    """
    if not key_terms:
        return 0.0

    t1_lower = text1.lower() if text1 else ""
    t2_lower = text2.lower() if text2 else ""

    both = 0
    either = 0
    for term in key_terms:
        term_lower = term.lower()
        in_t1 = term_lower in t1_lower
        in_t2 = term_lower in t2_lower
        if in_t1 or in_t2:
            either += 1
        if in_t1 and in_t2:
            both += 1

    return both / either if either > 0 else 0.0


def _cosine_similarity(text1: str, text2: str) -> float:
    """Calculate cosine similarity between two texts using TF vectors.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Cosine similarity (0.0 to 1.0).
    """
    tokens1 = _tokenize(text1)
    tokens2 = _tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0

    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)

    all_terms = set(tf1.keys()) | set(tf2.keys())

    dot_product = sum(tf1.get(t, 0) * tf2.get(t, 0) for t in all_terms)
    mag1 = math.sqrt(sum(v ** 2 for v in tf1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in tf2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


# ------------------------------------------------------------------
# Clinical data key terms
# ------------------------------------------------------------------

CLINICAL_KEY_TERMS = [
    "randomized", "controlled", "single-arm", "pivotal", "feasibility",
    "registry", "prospective", "retrospective", "multicenter",
    "double-blind", "sham-controlled", "non-inferiority", "superiority",
    "primary endpoint", "secondary endpoint", "safety endpoint",
    "adverse event", "serious adverse event", "device-related",
    "enrollment", "follow-up", "intent-to-treat", "per-protocol",
    "statistical significance", "p-value", "confidence interval",
    "survival", "mortality", "morbidity", "efficacy",
    "sensitivity", "specificity", "positive predictive value",
    "negative predictive value", "area under curve", "AUC",
    "Kaplan-Meier", "Cox regression", "hazard ratio",
]

DEVICE_KEY_TERMS = [
    "implantable", "external", "invasive", "non-invasive",
    "percutaneous", "transcatheter", "endovascular", "laparoscopic",
    "robotic", "wireless", "powered", "passive",
    "biodegradable", "bioabsorbable", "permanent",
    "titanium", "nitinol", "stainless steel", "polymer", "ceramic",
    "drug-eluting", "drug-coated", "antibacterial",
    "sterile", "single-use", "reusable", "reprocessed",
    "battery", "rechargeable", "MR conditional", "MR safe",
]

SAFETY_KEY_TERMS = [
    "adverse event", "serious adverse event", "death", "hospitalization",
    "device malfunction", "device failure", "explant", "revision",
    "infection", "thrombosis", "embolism", "hemorrhage", "perforation",
    "migration", "fracture", "corrosion", "wear",
    "biocompatibility", "cytotoxicity", "sensitization", "irritation",
    "genotoxicity", "carcinogenicity", "reproductive toxicity",
    "contraindication", "warning", "precaution",
    "post-approval study", "post-market surveillance",
]


# ------------------------------------------------------------------
# Comparison Engine
# ------------------------------------------------------------------

class PMAComparisonEngine:
    """Multi-PMA comparison engine with similarity scoring.

    Compares PMAs across indications, clinical data, device specifications,
    safety profiles, and regulatory history. Produces structured comparison
    matrices with weighted overall similarity scores.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize PMA comparison engine.

        Args:
            store: Optional PMADataStore instance for data retrieval.
        """
        self.store = store or PMADataStore()
        self.extractor = PMAExtractor(store=self.store)

    # ------------------------------------------------------------------
    # Main comparison entry point
    # ------------------------------------------------------------------

    def compare_pmas(
        self,
        primary: str,
        comparators: List[str],
        focus_areas: Optional[List[str]] = None,
        refresh: bool = False,
    ) -> Dict:
        """Compare a primary PMA against one or more comparators.

        Args:
            primary: Primary PMA number (e.g., 'P170019').
            comparators: List of comparator PMA numbers.
            focus_areas: Optional list of focus areas to compare.
                Valid values: 'indications', 'clinical_data', 'device_specs',
                'safety_profile', 'regulatory_history', 'all'.
                If None or ['all'], all dimensions are compared.
            refresh: Force refresh of underlying PMA data.

        Returns:
            Comparison result dictionary with comparison matrix,
            similarity scores, key differences, and regulatory implications.
        """
        primary_key = primary.upper()
        comp_keys = [c.upper() for c in comparators]

        # Resolve focus areas
        if focus_areas is None or "all" in focus_areas:
            active_dimensions = list(DIMENSION_WEIGHTS.keys())
        else:
            active_dimensions = [
                f for f in focus_areas if f in DIMENSION_WEIGHTS
            ]
            if not active_dimensions:
                active_dimensions = list(DIMENSION_WEIGHTS.keys())

        # Check comparison cache
        cache_result = self._check_comparison_cache(
            primary_key, comp_keys, active_dimensions
        )
        if cache_result and not refresh:
            return cache_result

        # Load data for all PMAs
        primary_data = self._load_pma_data(primary_key, refresh)
        comparator_data = {}
        for ck in comp_keys:
            comparator_data[ck] = self._load_pma_data(ck, refresh)

        # Run comparisons for each dimension
        comparison_matrix = {}
        pairwise_scores = {}

        for comp_pma in comp_keys:
            pair_key = f"{primary_key}_vs_{comp_pma}"
            pair_comparisons = {}

            for dimension in active_dimensions:
                dim_result = self._compare_dimension(
                    dimension,
                    primary_data,
                    comparator_data[comp_pma],
                )
                pair_comparisons[dimension] = dim_result

            # Calculate pairwise similarity score
            overall_score = self._calculate_overall_score(
                pair_comparisons, active_dimensions
            )
            pairwise_scores[comp_pma] = overall_score
            comparison_matrix[pair_key] = pair_comparisons

        # Identify key differences across all comparisons
        key_differences = self._identify_key_differences(
            comparison_matrix, primary_key, comp_keys
        )

        # Determine regulatory implications
        regulatory_implications = self._assess_regulatory_implications(
            comparison_matrix, pairwise_scores, primary_data, comparator_data
        )

        # Build result
        comparison_id = f"{primary_key}_vs_{'_'.join(comp_keys)}"
        result = {
            "comparison_id": comparison_id,
            "primary_pma": primary_key,
            "comparator_pmas": comp_keys,
            "comparison_date": datetime.now(timezone.utc).isoformat(),
            "focus_areas": active_dimensions,
            "comparison_matrix": comparison_matrix,
            "pairwise_scores": pairwise_scores,
            "overall_similarity": (
                sum(pairwise_scores.values()) / len(pairwise_scores)
                if pairwise_scores
                else 0.0
            ),
            "similarity_level": self._score_to_level(
                sum(pairwise_scores.values()) / len(pairwise_scores)
                if pairwise_scores
                else 0.0
            ),
            "key_differences": key_differences,
            "regulatory_implications": regulatory_implications,
            "primary_data_summary": self._summarize_pma(primary_data),
            "comparator_summaries": {
                ck: self._summarize_pma(comparator_data[ck])
                for ck in comp_keys
            },
        }

        # Cache the result
        self._save_comparison_cache(result)

        return result

    # ------------------------------------------------------------------
    # Dimension comparison functions
    # ------------------------------------------------------------------

    def _compare_dimension(
        self,
        dimension: str,
        pma1_data: Dict,
        pma2_data: Dict,
    ) -> Dict:
        """Compare two PMAs on a specific dimension.

        Args:
            dimension: Comparison dimension name.
            pma1_data: Primary PMA data (api_data + sections).
            pma2_data: Comparator PMA data.

        Returns:
            Dimension comparison result with score and details.
        """
        dispatch = {
            "indications": self._compare_indications,
            "clinical_data": self._compare_clinical_data,
            "device_specs": self._compare_device_specs,
            "safety_profile": self._compare_safety_profiles,
            "regulatory_history": self._compare_regulatory_history,
        }

        compare_fn = dispatch.get(dimension)
        if compare_fn is None:
            return {"score": 0.0, "error": f"Unknown dimension: {dimension}"}

        return compare_fn(pma1_data, pma2_data)

    def _compare_indications(self, pma1: Dict, pma2: Dict) -> Dict:
        """Compare indications for use between two PMAs.

        Args:
            pma1: Primary PMA data dict.
            pma2: Comparator PMA data dict.

        Returns:
            Comparison result with score and indication details.
        """
        text1 = self._get_section_text(pma1, "indications_for_use")
        text2 = self._get_section_text(pma2, "indications_for_use")

        if not text1 and not text2:
            return {
                "score": 0.0,
                "data_quality": "no_data",
                "details": "No indication text available for either PMA.",
            }

        if not text1 or not text2:
            # Try device name / generic name as fallback
            name1 = pma1.get("api_data", {}).get("generic_name", "")
            name2 = pma2.get("api_data", {}).get("generic_name", "")
            fallback_score = _word_overlap_score(
                name1 or text1 or "", name2 or text2 or ""
            )
            return {
                "score": round(fallback_score * 100, 1),
                "data_quality": "partial",
                "details": "One PMA missing indication text. Score based on device names.",
                "pma1_has_data": bool(text1),
                "pma2_has_data": bool(text2),
            }

        # Multi-method similarity
        jaccard = _word_overlap_score(text1, text2)
        cosine = _cosine_similarity(text1, text2)
        key_term = _key_term_overlap(text1, text2, CLINICAL_KEY_TERMS[:15])

        # Weighted combination: cosine most reliable for longer texts
        score = (cosine * 0.50 + jaccard * 0.30 + key_term * 0.20) * 100

        # Extract specific indication details
        details = {
            "pma1_indication_length": len(text1.split()),
            "pma2_indication_length": len(text2.split()),
            "word_overlap": round(jaccard, 3),
            "cosine_similarity": round(cosine, 3),
            "key_term_overlap": round(key_term, 3),
        }

        return {
            "score": round(min(score, 100), 1),
            "data_quality": "full",
            "details": details,
        }

    def _compare_clinical_data(self, pma1: Dict, pma2: Dict) -> Dict:
        """Compare clinical study data between two PMAs.

        Examines study design, enrollment, endpoints, and results.

        Args:
            pma1: Primary PMA data.
            pma2: Comparator PMA data.

        Returns:
            Clinical comparison result with sub-scores.
        """
        text1 = self._get_section_text(pma1, "clinical_studies")
        text2 = self._get_section_text(pma2, "clinical_studies")

        stat_text1 = self._get_section_text(pma1, "statistical_analysis")
        stat_text2 = self._get_section_text(pma2, "statistical_analysis")

        # Combine clinical + statistical sections
        combined1 = f"{text1 or ''} {stat_text1 or ''}".strip()
        combined2 = f"{text2 or ''} {stat_text2 or ''}".strip()

        if not combined1 and not combined2:
            return {
                "score": 0.0,
                "data_quality": "no_data",
                "details": "No clinical data available for either PMA.",
            }

        if not combined1 or not combined2:
            return {
                "score": 0.0,
                "data_quality": "partial",
                "details": "Clinical data available for only one PMA.",
                "pma1_has_data": bool(combined1),
                "pma2_has_data": bool(combined2),
            }

        # Sub-dimension comparisons
        study_design_score = self._compare_study_designs(combined1, combined2)
        endpoint_score = self._compare_endpoints(combined1, combined2)
        enrollment_score = self._compare_enrollment(combined1, combined2)
        overall_text_score = _cosine_similarity(combined1, combined2)

        # Weighted sub-score
        score = (
            study_design_score * 0.30
            + endpoint_score * 0.30
            + enrollment_score * 0.15
            + overall_text_score * 0.25
        ) * 100

        return {
            "score": round(min(score, 100), 1),
            "data_quality": "full",
            "details": {
                "study_design_similarity": round(study_design_score, 3),
                "endpoint_similarity": round(endpoint_score, 3),
                "enrollment_similarity": round(enrollment_score, 3),
                "text_similarity": round(overall_text_score, 3),
                "pma1_word_count": len(combined1.split()),
                "pma2_word_count": len(combined2.split()),
            },
        }

    def _compare_device_specs(self, pma1: Dict, pma2: Dict) -> Dict:
        """Compare device descriptions and specifications.

        Args:
            pma1: Primary PMA data.
            pma2: Comparator PMA data.

        Returns:
            Device specification comparison result.
        """
        desc1 = self._get_section_text(pma1, "device_description")
        desc2 = self._get_section_text(pma2, "device_description")

        mfg1 = self._get_section_text(pma1, "manufacturing")
        mfg2 = self._get_section_text(pma2, "manufacturing")

        combined1 = f"{desc1 or ''} {mfg1 or ''}".strip()
        combined2 = f"{desc2 or ''} {mfg2 or ''}".strip()

        if not combined1 and not combined2:
            # Fall back to product code comparison
            pc1 = pma1.get("api_data", {}).get("product_code", "")
            pc2 = pma2.get("api_data", {}).get("product_code", "")
            if pc1 and pc2 and pc1 == pc2:
                return {
                    "score": 50.0,
                    "data_quality": "metadata_only",
                    "details": f"Same product code ({pc1}), but no device description available.",
                }
            return {
                "score": 0.0,
                "data_quality": "no_data",
                "details": "No device specification data available.",
            }

        if not combined1 or not combined2:
            return {
                "score": 0.0,
                "data_quality": "partial",
                "details": "Device description available for only one PMA.",
            }

        # Text similarity
        cosine = _cosine_similarity(combined1, combined2)
        device_terms = _key_term_overlap(combined1, combined2, DEVICE_KEY_TERMS)
        jaccard = _word_overlap_score(combined1, combined2)

        # Product code bonus: same product code implies same general device type
        pc1 = pma1.get("api_data", {}).get("product_code", "")
        pc2 = pma2.get("api_data", {}).get("product_code", "")
        product_code_bonus = 0.10 if (pc1 and pc2 and pc1 == pc2) else 0.0

        score = (
            cosine * 0.40
            + device_terms * 0.30
            + jaccard * 0.20
            + product_code_bonus
        ) * 100

        return {
            "score": round(min(score, 100), 1),
            "data_quality": "full",
            "details": {
                "cosine_similarity": round(cosine, 3),
                "device_term_overlap": round(device_terms, 3),
                "word_overlap": round(jaccard, 3),
                "same_product_code": pc1 == pc2 if (pc1 and pc2) else None,
                "pma1_word_count": len(combined1.split()),
                "pma2_word_count": len(combined2.split()),
            },
        }

    def _compare_safety_profiles(self, pma1: Dict, pma2: Dict) -> Dict:
        """Compare safety profiles and adverse event data.

        Args:
            pma1: Primary PMA data.
            pma2: Comparator PMA data.

        Returns:
            Safety profile comparison result.
        """
        risk1 = self._get_section_text(pma1, "potential_risks")
        risk2 = self._get_section_text(pma2, "potential_risks")

        br1 = self._get_section_text(pma1, "benefit_risk")
        br2 = self._get_section_text(pma2, "benefit_risk")

        combined1 = f"{risk1 or ''} {br1 or ''}".strip()
        combined2 = f"{risk2 or ''} {br2 or ''}".strip()

        if not combined1 and not combined2:
            return {
                "score": 0.0,
                "data_quality": "no_data",
                "details": "No safety data available for either PMA.",
            }

        if not combined1 or not combined2:
            return {
                "score": 0.0,
                "data_quality": "partial",
                "details": "Safety data available for only one PMA.",
            }

        cosine = _cosine_similarity(combined1, combined2)
        safety_terms = _key_term_overlap(combined1, combined2, SAFETY_KEY_TERMS)
        jaccard = _word_overlap_score(combined1, combined2)

        score = (cosine * 0.40 + safety_terms * 0.35 + jaccard * 0.25) * 100

        return {
            "score": round(min(score, 100), 1),
            "data_quality": "full",
            "details": {
                "cosine_similarity": round(cosine, 3),
                "safety_term_overlap": round(safety_terms, 3),
                "word_overlap": round(jaccard, 3),
            },
        }

    def _compare_regulatory_history(self, pma1: Dict, pma2: Dict) -> Dict:
        """Compare regulatory history and pathway characteristics.

        Args:
            pma1: Primary PMA data.
            pma2: Comparator PMA data.

        Returns:
            Regulatory history comparison result.
        """
        api1 = pma1.get("api_data", {})
        api2 = pma2.get("api_data", {})

        score = 0.0
        details = {}

        # Product code match (30% of this dimension)
        pc1 = api1.get("product_code", "")
        pc2 = api2.get("product_code", "")
        if pc1 and pc2:
            pc_match = 1.0 if pc1 == pc2 else 0.0
            score += pc_match * 30
            details["same_product_code"] = pc1 == pc2

        # Advisory committee match (25% of this dimension)
        ac1 = api1.get("advisory_committee", "")
        ac2 = api2.get("advisory_committee", "")
        if ac1 and ac2:
            ac_match = 1.0 if ac1 == ac2 else 0.0
            score += ac_match * 25
            details["same_advisory_committee"] = ac1 == ac2

        # Applicant match (15% of this dimension)
        app1 = api1.get("applicant", "")
        app2 = api2.get("applicant", "")
        if app1 and app2:
            app_match = 1.0 if app1.lower() == app2.lower() else 0.0
            score += app_match * 15
            details["same_applicant"] = app1.lower() == app2.lower()

        # Supplement count similarity (15% of this dimension)
        sc1 = api1.get("supplement_count", 0) or pma1.get("supplement_count", 0)
        sc2 = api2.get("supplement_count", 0) or pma2.get("supplement_count", 0)
        if sc1 > 0 or sc2 > 0:
            max_sc = max(sc1, sc2)
            min_sc = min(sc1, sc2)
            sc_ratio = min_sc / max_sc if max_sc > 0 else 0.0
            score += sc_ratio * 15
            details["supplement_similarity"] = round(sc_ratio, 3)
            details["pma1_supplements"] = sc1
            details["pma2_supplements"] = sc2

        # Decision date proximity (15% of this dimension)
        dd1 = api1.get("decision_date", "")
        dd2 = api2.get("decision_date", "")
        if dd1 and dd2 and len(dd1) == 8 and len(dd2) == 8:
            try:
                y1 = int(dd1[:4])
                y2 = int(dd2[:4])
                year_diff = abs(y1 - y2)
                # Full credit if within 3 years, linear decay to 10 years
                if year_diff <= 3:
                    date_score = 1.0
                elif year_diff >= 10:
                    date_score = 0.0
                else:
                    date_score = 1.0 - (year_diff - 3) / 7.0
                score += date_score * 15
                details["year_difference"] = year_diff
                details["date_proximity"] = round(date_score, 3)
            except (ValueError, TypeError):
                pass

        return {
            "score": round(min(score, 100), 1),
            "data_quality": "full" if (pc1 and pc2) else "partial",
            "details": details,
        }

    # ------------------------------------------------------------------
    # Sub-comparison helpers
    # ------------------------------------------------------------------

    def _compare_study_designs(self, text1: str, text2: str) -> float:
        """Compare clinical study design types between two texts.

        Args:
            text1: Clinical text from PMA 1.
            text2: Clinical text from PMA 2.

        Returns:
            Similarity score (0.0 to 1.0).
        """
        design_patterns = {
            "rct": r"(?i)randomized\s+controlled|RCT",
            "single_arm": r"(?i)single[- ]arm",
            "registry": r"(?i)registry\s+(?:study|data)",
            "prospective": r"(?i)prospective",
            "retrospective": r"(?i)retrospective",
            "multicenter": r"(?i)multi[- ]?center|multi[- ]?site",
            "pivotal": r"(?i)pivotal",
            "feasibility": r"(?i)feasibility|pilot\s+study",
            "sham_controlled": r"(?i)sham[- ]controlled",
            "non_inferiority": r"(?i)non[- ]?inferiority",
            "superiority": r"(?i)superiority",
            "double_blind": r"(?i)double[- ]?blind",
            "crossover": r"(?i)cross[- ]?over",
            "bayesian": r"(?i)bayesian",
        }

        designs1 = set()
        designs2 = set()

        for key, pattern in design_patterns.items():
            if re.search(pattern, text1):
                designs1.add(key)
            if re.search(pattern, text2):
                designs2.add(key)

        if not designs1 and not designs2:
            return 0.5  # Unknown designs -- neutral

        if not designs1 or not designs2:
            return 0.25  # One has designs, the other does not

        intersection = designs1 & designs2
        union = designs1 | designs2

        return len(intersection) / len(union) if union else 0.0

    def _compare_endpoints(self, text1: str, text2: str) -> float:
        """Compare clinical endpoints between two texts.

        Args:
            text1: Clinical text from PMA 1.
            text2: Clinical text from PMA 2.

        Returns:
            Similarity score (0.0 to 1.0).
        """
        endpoint_patterns = {
            "survival": r"(?i)survival|mortality|death\s+rate",
            "efficacy_rate": r"(?i)success\s+rate|efficacy\s+rate|response\s+rate",
            "adverse_event": r"(?i)adverse\s+event\s+rate|complication\s+rate",
            "device_success": r"(?i)device\s+success|technical\s+success",
            "sensitivity": r"(?i)sensitivity|PPA|positive\s+percent\s+agreement",
            "specificity": r"(?i)specificity|NPA|negative\s+percent\s+agreement",
            "AUC": r"(?i)area\s+under\s+(?:the\s+)?(?:curve|ROC)|AUC",
            "quality_of_life": r"(?i)quality\s+of\s+life|QoL|SF-?36|EQ-?5D",
            "pain_score": r"(?i)pain\s+(?:score|VAS|NRS)",
            "functional_outcome": r"(?i)functional\s+(?:outcome|score|capacity)",
            "hemodynamic": r"(?i)hemodynamic|pressure\s+gradient|EOA",
            "composite": r"(?i)composite\s+(?:endpoint|end\s*point|outcome)",
        }

        eps1 = set()
        eps2 = set()

        for key, pattern in endpoint_patterns.items():
            if re.search(pattern, text1):
                eps1.add(key)
            if re.search(pattern, text2):
                eps2.add(key)

        if not eps1 and not eps2:
            return 0.5  # Unknown endpoints

        if not eps1 or not eps2:
            return 0.25

        intersection = eps1 & eps2
        union = eps1 | eps2

        return len(intersection) / len(union) if union else 0.0

    def _compare_enrollment(self, text1: str, text2: str) -> float:
        """Compare enrollment sizes between two clinical studies.

        Args:
            text1: Clinical text from PMA 1.
            text2: Clinical text from PMA 2.

        Returns:
            Similarity score (0.0 to 1.0).
        """
        def extract_enrollment(text: str) -> Optional[int]:
            patterns = [
                r"(?i)(?:enrolled|enrollment\s+(?:of|was)?)\s*[=:]?\s*(\d[\d,]*)",
                r"(?i)(?:N\s*=\s*|n\s*=\s*)(\d[\d,]*)",
                r"(?i)(\d[\d,]*)\s+(?:patients?|subjects?)\s+(?:were\s+)?enrolled",
                r"(?i)(?:sample\s+size\s+(?:of|was)?)\s*[=:]?\s*(\d[\d,]*)",
                r"(?i)(\d[\d,]*)\s+(?:patients?|subjects?)\s+(?:completed|in\s+the\s+study)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        return int(match.group(1).replace(",", ""))
                    except ValueError:
                        continue
            return None

        n1 = extract_enrollment(text1)
        n2 = extract_enrollment(text2)

        if n1 is None and n2 is None:
            return 0.5  # Unknown enrollment

        if n1 is None or n2 is None:
            return 0.25

        # Log-ratio similarity (handles orders of magnitude difference)
        if n1 == 0 or n2 == 0:
            return 0.0

        log_ratio = abs(math.log10(n1) - math.log10(n2))

        if log_ratio < 0.1:
            return 1.0  # Nearly same size
        elif log_ratio < 0.3:
            return 0.8  # Similar
        elif log_ratio < 0.5:
            return 0.6  # Moderate difference
        elif log_ratio < 1.0:
            return 0.3  # Large difference
        else:
            return 0.1  # Very different scale

    # ------------------------------------------------------------------
    # Score calculation and level mapping
    # ------------------------------------------------------------------

    def _calculate_overall_score(
        self,
        pair_comparisons: Dict,
        active_dimensions: List[str],
    ) -> float:
        """Calculate weighted overall similarity score.

        Args:
            pair_comparisons: Dimension comparison results for a pair.
            active_dimensions: List of dimensions being compared.

        Returns:
            Overall similarity score (0-100).
        """
        total_weight = sum(
            DIMENSION_WEIGHTS.get(d, 0) for d in active_dimensions
        )

        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for dimension in active_dimensions:
            weight = DIMENSION_WEIGHTS.get(dimension, 0)
            dim_result = pair_comparisons.get(dimension, {})
            dim_score = dim_result.get("score", 0.0)
            weighted_sum += weight * dim_score

        # Normalize by total weight (handles partial focus areas)
        return round(weighted_sum / total_weight, 1)

    @staticmethod
    def _score_to_level(score: float) -> str:
        """Map similarity score to descriptive level.

        Args:
            score: Similarity score (0-100).

        Returns:
            Similarity level string.
        """
        if score >= SIMILARITY_HIGH:
            return "HIGH"
        elif score >= SIMILARITY_MODERATE:
            return "MODERATE"
        elif score >= SIMILARITY_LOW:
            return "LOW"
        else:
            return "MINIMAL"

    # ------------------------------------------------------------------
    # Key differences and regulatory implications
    # ------------------------------------------------------------------

    def _identify_key_differences(
        self,
        comparison_matrix: Dict,
        primary: str,
        comparators: List[str],
    ) -> List[Dict]:
        """Identify the most significant differences across comparisons.

        Args:
            comparison_matrix: Full comparison matrix.
            primary: Primary PMA number.
            comparators: List of comparator PMA numbers.

        Returns:
            List of key difference dicts, sorted by significance.
        """
        differences = []

        for comp_pma in comparators:
            pair_key = f"{primary}_vs_{comp_pma}"
            pair_data = comparison_matrix.get(pair_key, {})

            for dimension, dim_result in pair_data.items():
                score = dim_result.get("score", 0.0)

                # Flag dimensions with low similarity as key differences
                if score < SIMILARITY_MODERATE:
                    severity = "CRITICAL" if score < SIMILARITY_LOW else "NOTABLE"
                    differences.append({
                        "pair": pair_key,
                        "comparator": comp_pma,
                        "dimension": dimension,
                        "score": score,
                        "severity": severity,
                        "data_quality": dim_result.get("data_quality", "unknown"),
                        "details": dim_result.get("details", ""),
                    })

        # Sort by score ascending (worst differences first)
        differences.sort(key=lambda d: d["score"])

        return differences

    def _assess_regulatory_implications(
        self,
        comparison_matrix: Dict,
        pairwise_scores: Dict,
        primary_data: Dict,
        comparator_data: Dict,
    ) -> List[Dict]:
        """Assess regulatory implications of comparison results.

        Args:
            comparison_matrix: Full comparison matrix.
            pairwise_scores: Pairwise similarity scores.
            primary_data: Primary PMA data.
            comparator_data: Dict of comparator PMA data.

        Returns:
            List of regulatory implication dicts.
        """
        implications = []

        # Check if any comparator is highly similar (potential predicate)
        for comp_pma, score in pairwise_scores.items():
            if score >= SIMILARITY_HIGH:
                implications.append({
                    "type": "strong_comparator",
                    "pma": comp_pma,
                    "score": score,
                    "implication": (
                        f"{comp_pma} shows high similarity ({score:.1f}/100). "
                        f"This PMA may serve as a strong reference for clinical "
                        f"and regulatory strategy."
                    ),
                })

        # Check for divergent indications
        primary_key = primary_data.get("api_data", {}).get("pma_number", "")
        for comp_pma in comparator_data:
            pair_key = f"{primary_key}_vs_{comp_pma}"
            pair = comparison_matrix.get(pair_key, {})
            ind_score = pair.get("indications", {}).get("score", 0.0)

            if ind_score < SIMILARITY_LOW:
                implications.append({
                    "type": "divergent_indications",
                    "pma": comp_pma,
                    "score": ind_score,
                    "implication": (
                        f"Indications for use differ significantly from {comp_pma} "
                        f"(score: {ind_score:.1f}/100). Direct comparison may not be "
                        f"appropriate for regulatory strategy."
                    ),
                })

        # Check for clinical data gaps
        for comp_pma in comparator_data:
            pair_key = f"{primary_key}_vs_{comp_pma}"
            pair = comparison_matrix.get(pair_key, {})
            clinical = pair.get("clinical_data", {})

            if clinical.get("data_quality") in ("no_data", "partial"):
                implications.append({
                    "type": "clinical_data_gap",
                    "pma": comp_pma,
                    "implication": (
                        f"Clinical data comparison with {comp_pma} is incomplete. "
                        f"SSED section extraction may need to be run or expanded."
                    ),
                })

        # Check same product code
        primary_pc = primary_data.get("api_data", {}).get("product_code", "")
        for comp_pma, comp_data in comparator_data.items():
            comp_pc = comp_data.get("api_data", {}).get("product_code", "")
            if primary_pc and comp_pc and primary_pc != comp_pc:
                implications.append({
                    "type": "different_product_code",
                    "pma": comp_pma,
                    "implication": (
                        f"Different product codes: {primary_pc} vs {comp_pc} ({comp_pma}). "
                        f"Cross-product-code comparison may indicate different "
                        f"device categories."
                    ),
                })

        return implications

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------

    def _load_pma_data(self, pma_number: str, refresh: bool = False) -> Dict:
        """Load comprehensive PMA data (API + extracted sections).

        Args:
            pma_number: PMA number.
            refresh: Force refresh from API.

        Returns:
            Dict with 'api_data', 'sections', 'supplements'.
        """
        # Load API data
        api_data = self.store.get_pma_data(pma_number, refresh=refresh)

        # Load extracted sections
        sections = self.store.get_extracted_sections(pma_number)

        # Load supplements
        supplements = self.store.get_supplements(pma_number, refresh=refresh)

        return {
            "api_data": api_data,
            "sections": sections,
            "supplements": supplements,
            "supplement_count": len(supplements) if supplements else 0,
        }

    def _get_section_text(self, pma_data: Dict, section_key: str) -> Optional[str]:
        """Extract section text from loaded PMA data.

        Args:
            pma_data: Loaded PMA data dict.
            section_key: Section key (e.g., 'indications_for_use').

        Returns:
            Section content text, or None if not available.
        """
        sections = pma_data.get("sections")
        if not sections:
            return None

        # Check in 'sections' sub-dict (extraction result structure)
        section_dict = sections.get("sections", sections)
        section = section_dict.get(section_key)

        if section is None:
            return None

        if isinstance(section, dict):
            return section.get("content", "")
        elif isinstance(section, str):
            return section

        return None

    def _summarize_pma(self, pma_data: Dict) -> Dict:
        """Create a summary of PMA data for inclusion in comparison output.

        Args:
            pma_data: Loaded PMA data.

        Returns:
            Summary dict with key fields.
        """
        api = pma_data.get("api_data", {})
        sections = pma_data.get("sections")

        section_count = 0
        total_words = 0
        if sections:
            section_dict = sections.get("sections", sections)
            # Count sections that have content
            for v in section_dict.values():
                if isinstance(v, dict) and v.get("content"):
                    section_count += 1
                    total_words += v.get("word_count", 0)

        return {
            "pma_number": api.get("pma_number", ""),
            "device_name": api.get("device_name", ""),
            "applicant": api.get("applicant", ""),
            "product_code": api.get("product_code", ""),
            "decision_date": api.get("decision_date", ""),
            "advisory_committee": api.get("advisory_committee", ""),
            "supplement_count": pma_data.get("supplement_count", 0),
            "sections_available": section_count,
            "total_words": total_words,
        }

    # ------------------------------------------------------------------
    # Comparison caching
    # ------------------------------------------------------------------

    def _get_comparison_cache_path(self, comparison_id: str) -> Path:
        """Get file path for comparison cache.

        Args:
            comparison_id: Comparison identifier string.

        Returns:
            Path to cache file.
        """
        cache_dir = self.store.cache_dir / "_comparisons"
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Sanitize comparison_id for filesystem
        safe_id = re.sub(r"[^\w_]", "_", comparison_id)
        return cache_dir / f"{safe_id}.json"

    def _check_comparison_cache(
        self,
        primary: str,
        comparators: List[str],
        dimensions: List[str],
    ) -> Optional[Dict]:
        """Check for a cached comparison result.

        Args:
            primary: Primary PMA number.
            comparators: Comparator PMA numbers.
            dimensions: Active comparison dimensions.

        Returns:
            Cached comparison result, or None if not found/expired.
        """
        comparison_id = f"{primary}_vs_{'_'.join(sorted(comparators))}"
        cache_path = self._get_comparison_cache_path(comparison_id)

        if not cache_path.exists():
            return None

        try:
            import time
            with open(cache_path) as f:
                cached = json.load(f)

            # Check TTL
            cached_at = cached.get("_cached_at", 0)
            if isinstance(cached_at, str):
                dt = datetime.fromisoformat(cached_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
            else:
                elapsed = __import__("time").time() - cached_at

            if elapsed > COMPARISON_CACHE_TTL:
                cache_path.unlink(missing_ok=True)
                return None

            # Check that cached result covers the requested dimensions
            cached_dims = set(cached.get("focus_areas", []))
            if not set(dimensions).issubset(cached_dims):
                return None

            cached["_cache_status"] = "cached"
            return cached

        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def _save_comparison_cache(self, result: Dict) -> None:
        """Save comparison result to cache.

        Args:
            result: Comparison result dict.
        """
        comparison_id = result.get("comparison_id", "unknown")
        cache_path = self._get_comparison_cache_path(comparison_id)

        cache_data = dict(result)
        cache_data["_cached_at"] = datetime.now(timezone.utc).isoformat()

        try:
            tmp_path = cache_path.with_suffix(".json.tmp")
            with open(tmp_path, "w") as f:
                json.dump(cache_data, f, indent=2)
            tmp_path.replace(cache_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Competitive analysis
    # ------------------------------------------------------------------

    def competitive_analysis(
        self,
        product_code: str,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        limit: int = 20,
    ) -> Dict:
        """Generate a competitive analysis for all PMAs in a product code.

        Compares all PMAs pairwise and identifies clusters, leaders,
        and competitive landscape.

        Args:
            product_code: FDA product code.
            year_start: Optional start year filter.
            year_end: Optional end year filter.
            limit: Maximum PMAs to include.

        Returns:
            Competitive analysis result with pairwise matrix and clusters.
        """
        # Search for PMAs
        search_result = self.store.client.search_pma(
            product_code=product_code,
            year_start=year_start,
            year_end=year_end,
            limit=limit,
            sort="decision_date:desc",
        )

        if search_result.get("degraded"):
            return {
                "error": search_result.get("error", "API unavailable"),
                "product_code": product_code,
            }

        results = search_result.get("results", [])
        if not results:
            return {
                "error": f"No PMAs found for product code {product_code}",
                "product_code": product_code,
            }

        # Extract unique base PMA numbers (exclude supplements)
        pma_numbers = []
        seen = set()
        for r in results:
            pn = r.get("pma_number", "")
            # Extract base PMA (remove supplement suffix)
            base_pma = re.sub(r"S\d+$", "", pn)
            if base_pma and base_pma not in seen:
                seen.add(base_pma)
                pma_numbers.append(base_pma)

        if len(pma_numbers) < 2:
            return {
                "error": "Need at least 2 PMAs for competitive analysis.",
                "product_code": product_code,
                "pma_count": len(pma_numbers),
            }

        # Limit to manageable size
        pma_numbers = pma_numbers[:limit]

        # Load data for all PMAs
        all_data = {}
        for pn in pma_numbers:
            all_data[pn] = self._load_pma_data(pn)

        # Pairwise comparison matrix (use regulatory_history only for efficiency)
        pairwise_matrix = {}
        for i, pma1 in enumerate(pma_numbers):
            for j, pma2 in enumerate(pma_numbers):
                if i >= j:
                    continue  # Skip self-comparisons and duplicates

                pair_key = f"{pma1}_vs_{pma2}"
                score_sum = 0.0
                count = 0

                for dimension in ["indications", "device_specs", "regulatory_history"]:
                    dim_result = self._compare_dimension(
                        dimension, all_data[pma1], all_data[pma2]
                    )
                    score_sum += dim_result.get("score", 0.0)
                    count += 1

                avg_score = score_sum / count if count > 0 else 0.0
                pairwise_matrix[pair_key] = round(avg_score, 1)

        # Identify most similar pairs
        sorted_pairs = sorted(
            pairwise_matrix.items(), key=lambda x: x[1], reverse=True
        )

        # Applicant distribution
        applicants = Counter()
        for pn, data in all_data.items():
            app = data.get("api_data", {}).get("applicant", "Unknown")
            applicants[app] += 1

        # Timeline analysis
        approval_years = []
        for pn, data in all_data.items():
            dd = data.get("api_data", {}).get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    approval_years.append(int(dd[:4]))
                except ValueError:
                    pass

        return {
            "product_code": product_code,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "total_pmas": len(pma_numbers),
            "pma_numbers": pma_numbers,
            "pairwise_matrix": pairwise_matrix,
            "most_similar_pairs": sorted_pairs[:5],
            "least_similar_pairs": sorted_pairs[-5:] if len(sorted_pairs) > 5 else [],
            "applicant_distribution": dict(applicants.most_common()),
            "approval_year_range": (
                f"{min(approval_years)}-{max(approval_years)}"
                if approval_years else "N/A"
            ),
            "pma_summaries": {
                pn: self._summarize_pma(all_data[pn])
                for pn in pma_numbers
            },
        }


# ------------------------------------------------------------------
# CLI interface
# ------------------------------------------------------------------

def _format_comparison_output(result: Dict) -> str:
    """Format comparison result as readable text output.

    Args:
        result: Comparison result dictionary.

    Returns:
        Formatted string output.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("PMA COMPARISON REPORT")
    lines.append("=" * 70)
    lines.append(f"Primary PMA:    {result.get('primary_pma', 'N/A')}")
    lines.append(f"Comparators:    {', '.join(result.get('comparator_pmas', []))}")
    lines.append(f"Date:           {result.get('comparison_date', 'N/A')[:10]}")
    lines.append(f"Focus Areas:    {', '.join(result.get('focus_areas', []))}")
    lines.append("")

    # Overall score
    overall = result.get("overall_similarity", 0.0)
    level = result.get("similarity_level", "N/A")
    lines.append(f"Overall Similarity: {overall:.1f}/100 ({level})")
    lines.append("")

    # Pairwise scores
    lines.append("--- Pairwise Scores ---")
    for comp, score in result.get("pairwise_scores", {}).items():
        level = PMAComparisonEngine._score_to_level(score)
        bar = "#" * int(score / 5)
        lines.append(f"  vs {comp}: {score:5.1f}/100 [{bar:<20s}] {level}")
    lines.append("")

    # Dimension breakdown
    lines.append("--- Dimension Breakdown ---")
    for pair_key, dims in result.get("comparison_matrix", {}).items():
        lines.append(f"\n  {pair_key}:")
        for dim, dim_result in dims.items():
            score = dim_result.get("score", 0.0)
            quality = dim_result.get("data_quality", "unknown")
            lines.append(f"    {dim:25s} {score:5.1f}/100  (data: {quality})")
    lines.append("")

    # Key differences
    diffs = result.get("key_differences", [])
    if diffs:
        lines.append("--- Key Differences ---")
        for d in diffs[:10]:
            lines.append(
                f"  [{d['severity']}] {d['dimension']} vs {d['comparator']}: "
                f"{d['score']:.1f}/100"
            )
        lines.append("")

    # Regulatory implications
    implications = result.get("regulatory_implications", [])
    if implications:
        lines.append("--- Regulatory Implications ---")
        for imp in implications:
            lines.append(f"  [{imp['type']}] {imp['implication']}")
        lines.append("")

    # PMA summaries
    lines.append("--- PMA Summaries ---")
    primary_summary = result.get("primary_data_summary", {})
    lines.append(f"  PRIMARY: {primary_summary.get('pma_number', 'N/A')}")
    lines.append(f"    Device: {primary_summary.get('device_name', 'N/A')}")
    lines.append(f"    Applicant: {primary_summary.get('applicant', 'N/A')}")
    lines.append(f"    Product Code: {primary_summary.get('product_code', 'N/A')}")
    lines.append(f"    Sections Available: {primary_summary.get('sections_available', 0)}")

    for comp_pma, summary in result.get("comparator_summaries", {}).items():
        lines.append(f"  COMPARATOR: {summary.get('pma_number', 'N/A')}")
        lines.append(f"    Device: {summary.get('device_name', 'N/A')}")
        lines.append(f"    Applicant: {summary.get('applicant', 'N/A')}")
        lines.append(f"    Product Code: {summary.get('product_code', 'N/A')}")
        lines.append(f"    Sections Available: {summary.get('sections_available', 0)}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="PMA Comparison Engine -- Multi-PMA comparison with similarity scoring"
    )
    parser.add_argument("--primary", help="Primary PMA number")
    parser.add_argument("--comparators", help="Comma-separated comparator PMA numbers")
    parser.add_argument(
        "--focus",
        help="Focus areas (comma-separated): indications,clinical_data,device_specs,safety_profile,regulatory_history,all",
    )
    parser.add_argument("--product-code", dest="product_code",
                        help="Run competitive analysis for a product code")
    parser.add_argument("--year", type=int, help="Filter year for competitive analysis")
    parser.add_argument("--competitive", action="store_true",
                        help="Run competitive analysis mode")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    engine = PMAComparisonEngine()

    if args.competitive and args.product_code:
        result = engine.competitive_analysis(
            product_code=args.product_code,
            year_start=args.year,
            year_end=args.year,
        )
        if args.json or args.output:
            output = json.dumps(result, indent=2)
        else:
            output = json.dumps(result, indent=2)  # Competitive always JSON
        print(output)

    elif args.primary and args.comparators:
        comparators = [c.strip().upper() for c in args.comparators.split(",") if c.strip()]
        focus_areas = None
        if args.focus:
            focus_areas = [f.strip() for f in args.focus.split(",") if f.strip()]

        result = engine.compare_pmas(
            primary=args.primary,
            comparators=comparators,
            focus_areas=focus_areas,
            refresh=args.refresh,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_format_comparison_output(result))

    else:
        parser.error("Specify --primary + --comparators, or --product-code + --competitive")

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
