#!/usr/bin/env python3
"""
Unified Predicate Analyzer -- Abstract interface for 510(k) and PMA predicates.

Provides a single entry point for analyzing predicate/reference devices regardless
of whether they are 510(k) clearances (K-numbers) or PMA approvals (P-numbers).
This module bridges the existing 510(k) pipeline with the PMA Intelligence
infrastructure from Phase 0/1.

Key features:
    - Auto-detect device number type (K/P/DEN)
    - Unified data retrieval and normalization
    - Cross-pathway comparison (510(k) vs PMA, PMA vs PMA, mixed)
    - Suitability scoring with pathway-appropriate criteria
    - Caching through existing data stores

Usage:
    from unified_predicate import UnifiedPredicateAnalyzer

    analyzer = UnifiedPredicateAnalyzer()

    # Analyze any device number
    result = analyzer.analyze_predicate("P170019")
    result = analyzer.analyze_predicate("K241335")

    # Compare devices across pathways
    comparison = analyzer.compare_devices("K241335", "P170019")

    # Assess suitability as predicate
    suitability = analyzer.assess_suitability(
        candidate="P170019",
        subject_device={"product_code": "NMH", "intended_use": "..."}
    )

    # CLI usage:
    python3 unified_predicate.py --device P170019
    python3 unified_predicate.py --compare K241335 P170019
    python3 unified_predicate.py --assess P170019 --product-code NMH
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_api_client import FDAClient
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

# Device number format patterns
DEVICE_PATTERNS = {
    "510k": re.compile(r"^K\d{6}$", re.IGNORECASE),
    "pma": re.compile(r"^P\d{6}(?:S\d+)?$", re.IGNORECASE),
    "de_novo": re.compile(r"^DEN\d{7}$", re.IGNORECASE),
    "pre_amendment": re.compile(r"^N\d+$", re.IGNORECASE),
}

# Unified suitability scoring weights
SUITABILITY_WEIGHTS = {
    "product_code_match": 25,
    "indication_overlap": 30,
    "device_similarity": 20,
    "recency": 10,
    "clinical_evidence": 10,
    "regulatory_standing": 5,
}

# Cross-pathway comparison dimension mapping
# Maps SE table dimensions to PMA SSED section keys
SSED_TO_SE_MAPPING = {
    "indications_for_use": "intended_use",
    "device_description": "device_description",
    "clinical_studies": "clinical_data",
    "nonclinical_testing": "performance_testing",
    "manufacturing": "sterilization",
    "potential_risks": "safety_profile",
    "biocompatibility": "biocompatibility",
}

# Normalized field names for cross-pathway data
NORMALIZED_FIELDS = [
    "device_number",
    "device_type",       # "510k", "pma", "de_novo"
    "device_name",
    "applicant",
    "product_code",
    "decision_date",
    "intended_use",
    "device_description",
    "materials",
    "sterilization",
    "clinical_data_summary",
    "regulatory_status",
    "supplement_count",
    "recall_history",
]


# ------------------------------------------------------------------
# Unified Predicate Analyzer
# ------------------------------------------------------------------

class UnifiedPredicateAnalyzer:
    """Unified interface for analyzing 510(k) and PMA predicates.

    Abstracts the differences between K-numbers and P-numbers, providing
    a consistent API for predicate analysis, comparison, and suitability
    assessment across regulatory pathways.
    """

    def __init__(
        self,
        client: Optional[FDAClient] = None,
        pma_store: Optional[PMADataStore] = None,
    ):
        """Initialize the unified predicate analyzer.

        Args:
            client: Optional pre-configured FDAClient instance.
            pma_store: Optional pre-configured PMADataStore instance.
        """
        self.client = client or FDAClient()
        self.pma_store = pma_store or PMADataStore(client=self.client)

    # ------------------------------------------------------------------
    # Device type detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_device_type(device_number: str) -> str:
        """Detect the regulatory pathway type from a device number.

        Args:
            device_number: FDA device number (K, P, DEN, or N prefix).

        Returns:
            Device type string: "510k", "pma", "de_novo", "pre_amendment",
            or "unknown".
        """
        num = device_number.strip().upper()
        for dtype, pattern in DEVICE_PATTERNS.items():
            if pattern.match(num):
                return dtype
        return "unknown"

    @staticmethod
    def is_pma_number(device_number: str) -> bool:
        """Check if a device number is a PMA P-number.

        Args:
            device_number: Device number to check.

        Returns:
            True if PMA number format.
        """
        return DEVICE_PATTERNS["pma"].match(device_number.strip().upper()) is not None

    @staticmethod
    def is_510k_number(device_number: str) -> bool:
        """Check if a device number is a 510(k) K-number.

        Args:
            device_number: Device number to check.

        Returns:
            True if 510(k) number format.
        """
        return DEVICE_PATTERNS["510k"].match(device_number.strip().upper()) is not None

    @staticmethod
    def classify_device_list(device_numbers: List[str]) -> Dict[str, List[str]]:
        """Classify a list of device numbers by type.

        Args:
            device_numbers: List of device numbers.

        Returns:
            Dictionary mapping device type to list of numbers.
            Example: {"510k": ["K241335"], "pma": ["P170019"]}
        """
        classified = {"510k": [], "pma": [], "de_novo": [], "unknown": []}
        for num in device_numbers:
            dtype = UnifiedPredicateAnalyzer.detect_device_type(num)
            if dtype in classified:
                classified[dtype].append(num.upper())
            else:
                classified["unknown"].append(num.upper())
        return {k: v for k, v in classified.items() if v}

    # ------------------------------------------------------------------
    # Unified data retrieval
    # ------------------------------------------------------------------

    def analyze_predicate(self, device_number: str, refresh: bool = False) -> Dict:
        """Analyze a predicate device regardless of type.

        Retrieves data from the appropriate source (510(k) or PMA) and
        normalizes it into a unified format.

        Args:
            device_number: K-number, P-number, or DEN-number.
            refresh: Force refresh from API.

        Returns:
            Normalized predicate analysis dict with unified fields.
        """
        num = device_number.strip().upper()
        dtype = self.detect_device_type(num)

        if dtype == "510k":
            return self._analyze_510k(num)
        elif dtype == "pma":
            return self._analyze_pma(num, refresh=refresh)
        elif dtype == "de_novo":
            return self._analyze_de_novo(num)
        else:
            return {
                "device_number": num,
                "device_type": "unknown",
                "error": f"Unrecognized device number format: {num}",
                "valid": False,
            }

    def _analyze_510k(self, k_number: str) -> Dict:
        """Analyze a 510(k) clearance.

        Args:
            k_number: 510(k) K-number.

        Returns:
            Normalized predicate data.
        """
        result = self.client.get_510k(k_number)

        if result.get("degraded") or not result.get("results"):
            return {
                "device_number": k_number,
                "device_type": "510k",
                "valid": False,
                "error": result.get("error", f"K-number {k_number} not found in FDA database"),
            }

        data = result["results"][0]

        return {
            "device_number": k_number,
            "device_type": "510k",
            "valid": True,
            "device_name": data.get("device_name", ""),
            "applicant": data.get("applicant", ""),
            "product_code": data.get("product_code", ""),
            "decision_date": data.get("decision_date", ""),
            "intended_use": data.get("statement_or_summary", ""),
            "device_description": data.get("device_name", ""),
            "regulatory_status": "cleared",
            "clearance_type": data.get("clearance_type", ""),
            "review_panel": data.get("review_panel", ""),
            "regulation_number": data.get("regulation_number", ""),
            "supplement_count": 0,
            "has_clinical_data": False,
            "clinical_data_source": "510k_summary_pdf",
            "raw_data": data,
        }

    def _analyze_pma(self, pma_number: str, refresh: bool = False) -> Dict:
        """Analyze a PMA approval using PMA Intelligence infrastructure.

        Args:
            pma_number: PMA P-number.
            refresh: Force refresh.

        Returns:
            Normalized predicate data with PMA intelligence fields.
        """
        # Use PMADataStore for cached data
        api_data = self.pma_store.get_pma_data(pma_number, refresh=refresh)

        if api_data.get("error"):
            return {
                "device_number": pma_number,
                "device_type": "pma",
                "valid": False,
                "error": api_data.get("error", f"PMA {pma_number} not found"),
            }

        # Get extracted SSED sections if available
        sections = self.pma_store.get_extracted_sections(pma_number)
        has_sections = sections is not None and bool(sections.get("sections", sections))

        # Extract intended use from SSED indications section
        intended_use = ""
        device_desc = ""
        if has_sections:
            section_dict = sections.get("sections", sections)
            ind = section_dict.get("indications_for_use", {})
            if isinstance(ind, dict):
                intended_use = ind.get("content", "")
            desc = section_dict.get("device_description", {})
            if isinstance(desc, dict):
                device_desc = desc.get("content", "")

        # Get supplement count
        supplements = self.pma_store.get_supplements(pma_number)
        supplement_count = len(supplements) if supplements else 0

        # Check for clinical data availability
        has_clinical = False
        if has_sections:
            section_dict = sections.get("sections", sections)
            clinical = section_dict.get("clinical_studies", {})
            if isinstance(clinical, dict) and clinical.get("word_count", 0) > 100:
                has_clinical = True

        return {
            "device_number": pma_number,
            "device_type": "pma",
            "valid": True,
            "device_name": api_data.get("device_name", "") or api_data.get("trade_name", ""),
            "applicant": api_data.get("applicant", ""),
            "product_code": api_data.get("product_code", ""),
            "decision_date": api_data.get("decision_date", ""),
            "intended_use": intended_use,
            "device_description": device_desc or api_data.get("device_name", ""),
            "regulatory_status": "approved",
            "advisory_committee": api_data.get("advisory_committee", ""),
            "advisory_committee_description": api_data.get("advisory_committee_description", ""),
            "review_panel": api_data.get("advisory_committee", ""),
            "regulation_number": api_data.get("regulation_number", ""),
            "supplement_count": supplement_count,
            "has_clinical_data": has_clinical,
            "has_ssed_sections": has_sections,
            "clinical_data_source": "ssed_extraction" if has_sections else "api_metadata",
            "expedited_review": api_data.get("expedited_review_flag", "N"),
            "raw_data": api_data,
        }

    def _analyze_de_novo(self, den_number: str) -> Dict:
        """Analyze a De Novo classification.

        Args:
            den_number: De Novo DEN-number.

        Returns:
            Normalized predicate data.
        """
        result = self.client.validate_device(den_number)

        if result.get("degraded") or not result.get("results"):
            return {
                "device_number": den_number,
                "device_type": "de_novo",
                "valid": False,
                "error": result.get("note", f"DEN-number {den_number} not found"),
            }

        data = result["results"][0]

        return {
            "device_number": den_number,
            "device_type": "de_novo",
            "valid": True,
            "device_name": data.get("device_name", ""),
            "applicant": data.get("applicant", ""),
            "product_code": data.get("product_code", ""),
            "decision_date": data.get("decision_date", ""),
            "intended_use": data.get("statement_or_summary", ""),
            "device_description": data.get("device_name", ""),
            "regulatory_status": "granted",
            "supplement_count": 0,
            "has_clinical_data": False,
            "raw_data": data,
        }

    # ------------------------------------------------------------------
    # Cross-pathway comparison
    # ------------------------------------------------------------------

    def compare_devices(
        self,
        device1: str,
        device2: str,
        focus_areas: Optional[List[str]] = None,
        refresh: bool = False,
    ) -> Dict:
        """Compare two devices across pathways.

        Works for any combination: K vs K, P vs P, K vs P, etc.

        Args:
            device1: First device number.
            device2: Second device number.
            focus_areas: Optional list of comparison dimensions.
            refresh: Force refresh of data.

        Returns:
            Comparison result dict with similarity scores.
        """
        # Analyze both devices
        d1 = self.analyze_predicate(device1, refresh=refresh)
        d2 = self.analyze_predicate(device2, refresh=refresh)

        if not d1.get("valid"):
            return {
                "error": f"Could not retrieve data for {device1}: {d1.get('error', 'unknown')}",
                "device1": device1,
                "device2": device2,
            }
        if not d2.get("valid"):
            return {
                "error": f"Could not retrieve data for {device2}: {d2.get('error', 'unknown')}",
                "device1": device1,
                "device2": device2,
            }

        # Determine comparison type
        comparison_type = f"{d1['device_type']}_vs_{d2['device_type']}"

        # Run comparisons across dimensions
        dimensions = {}
        all_areas = focus_areas or [
            "indications", "device_specs", "clinical_data",
            "safety_profile", "regulatory_history",
        ]

        for area in all_areas:
            dimensions[area] = self._compare_dimension(area, d1, d2)

        # Calculate overall similarity
        total_weight = 0.0
        weighted_score = 0.0
        dimension_weights = {
            "indications": 0.30,
            "device_specs": 0.20,
            "clinical_data": 0.25,
            "safety_profile": 0.15,
            "regulatory_history": 0.10,
        }
        for area, result in dimensions.items():
            weight = dimension_weights.get(area, 0.10)
            score = result.get("score", 0.0)
            total_weight += weight
            weighted_score += weight * score

        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # Determine similarity level
        if overall_score >= 75:
            similarity_level = "HIGH"
        elif overall_score >= 50:
            similarity_level = "MODERATE"
        elif overall_score >= 25:
            similarity_level = "LOW"
        else:
            similarity_level = "MINIMAL"

        # Identify key differences
        key_differences = []
        for area, result in dimensions.items():
            if result.get("score", 0) < 50:
                key_differences.append({
                    "dimension": area,
                    "score": result.get("score", 0),
                    "detail": result.get("detail", ""),
                    "severity": "NOTABLE" if result.get("score", 0) >= 25 else "CRITICAL",
                })

        return {
            "device1": {
                "number": d1["device_number"],
                "type": d1["device_type"],
                "name": d1.get("device_name", ""),
                "applicant": d1.get("applicant", ""),
                "product_code": d1.get("product_code", ""),
                "decision_date": d1.get("decision_date", ""),
            },
            "device2": {
                "number": d2["device_number"],
                "type": d2["device_type"],
                "name": d2.get("device_name", ""),
                "applicant": d2.get("applicant", ""),
                "product_code": d2.get("product_code", ""),
                "decision_date": d2.get("decision_date", ""),
            },
            "comparison_type": comparison_type,
            "overall_similarity": round(overall_score, 1),
            "similarity_level": similarity_level,
            "dimensions": dimensions,
            "key_differences": key_differences,
            "data_quality": {
                "device1_source": d1.get("clinical_data_source", "api"),
                "device2_source": d2.get("clinical_data_source", "api"),
                "cross_pathway": d1["device_type"] != d2["device_type"],
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _compare_dimension(self, dimension: str, d1: Dict, d2: Dict) -> Dict:
        """Compare two devices on a single dimension.

        Args:
            dimension: Comparison dimension name.
            d1: Normalized data for device 1.
            d2: Normalized data for device 2.

        Returns:
            Dimension comparison result with score and detail.
        """
        if dimension == "indications":
            return self._compare_indications(d1, d2)
        elif dimension == "device_specs":
            return self._compare_device_specs(d1, d2)
        elif dimension == "clinical_data":
            return self._compare_clinical_data(d1, d2)
        elif dimension == "safety_profile":
            return self._compare_safety(d1, d2)
        elif dimension == "regulatory_history":
            return self._compare_regulatory(d1, d2)
        else:
            return {"score": 0.0, "detail": f"Unknown dimension: {dimension}"}

    def _compare_indications(self, d1: Dict, d2: Dict) -> Dict:
        """Compare indications/intended use between two devices.

        Args:
            d1: Device 1 normalized data.
            d2: Device 2 normalized data.

        Returns:
            Indication comparison result.
        """
        text1 = d1.get("intended_use", "")
        text2 = d2.get("intended_use", "")

        if not text1 and not text2:
            return {
                "score": 50.0,
                "detail": "No indication text available for either device",
                "data_quality": "none",
            }

        if not text1 or not text2:
            # Fall back to device name comparison
            name1 = d1.get("device_name", "")
            name2 = d2.get("device_name", "")
            score = _word_overlap(name1, name2) * 100
            return {
                "score": round(score, 1),
                "detail": "Limited to device name comparison (indication text unavailable)",
                "data_quality": "partial",
            }

        # Full text comparison using cosine similarity
        cosine = _cosine_similarity(text1, text2)
        jaccard = _word_overlap(text1, text2)

        # Blend cosine and jaccard (cosine emphasizes important terms)
        score = (cosine * 0.6 + jaccard * 0.4) * 100

        return {
            "score": round(score, 1),
            "cosine_similarity": round(cosine, 3),
            "jaccard_similarity": round(jaccard, 3),
            "detail": f"Indication text similarity: cosine={cosine:.2f}, jaccard={jaccard:.2f}",
            "data_quality": "full",
        }

    def _compare_device_specs(self, d1: Dict, d2: Dict) -> Dict:
        """Compare device specifications.

        Args:
            d1: Device 1 normalized data.
            d2: Device 2 normalized data.

        Returns:
            Device specification comparison result.
        """
        score = 0.0
        factors = []

        # Product code match (major factor)
        pc1 = d1.get("product_code", "")
        pc2 = d2.get("product_code", "")
        if pc1 and pc2:
            if pc1 == pc2:
                score += 40
                factors.append(f"Same product code ({pc1})")
            else:
                factors.append(f"Different product codes ({pc1} vs {pc2})")

        # Device description similarity
        desc1 = d1.get("device_description", "")
        desc2 = d2.get("device_description", "")
        if desc1 and desc2:
            desc_sim = _cosine_similarity(desc1, desc2)
            desc_score = desc_sim * 40
            score += desc_score
            factors.append(f"Description similarity: {desc_sim:.2f}")

        # Same review panel bonus
        rp1 = d1.get("review_panel", "")
        rp2 = d2.get("review_panel", "")
        if rp1 and rp2 and rp1 == rp2:
            score += 10
            factors.append(f"Same review panel ({rp1})")

        # Same regulation number bonus
        reg1 = d1.get("regulation_number", "")
        reg2 = d2.get("regulation_number", "")
        if reg1 and reg2 and reg1 == reg2:
            score += 10
            factors.append(f"Same regulation ({reg1})")

        return {
            "score": round(min(score, 100.0), 1),
            "factors": factors,
            "detail": "; ".join(factors),
        }

    def _compare_clinical_data(self, d1: Dict, d2: Dict) -> Dict:
        """Compare clinical data availability and type.

        Args:
            d1: Device 1 normalized data.
            d2: Device 2 normalized data.

        Returns:
            Clinical data comparison result.
        """
        has1 = d1.get("has_clinical_data", False)
        has2 = d2.get("has_clinical_data", False)

        if has1 and has2:
            # Both have clinical data -- good comparability
            return {
                "score": 70.0,
                "detail": "Both devices have clinical data available",
                "data_quality": "full",
            }
        elif has1 or has2:
            # One has clinical data, one does not
            source1 = d1.get("clinical_data_source", "none")
            source2 = d2.get("clinical_data_source", "none")
            return {
                "score": 40.0,
                "detail": f"Asymmetric clinical evidence ({source1} vs {source2})",
                "data_quality": "partial",
            }
        else:
            # Neither has clinical data
            return {
                "score": 50.0,
                "detail": "No clinical data available for either device",
                "data_quality": "none",
            }

    def _compare_safety(self, d1: Dict, d2: Dict) -> Dict:
        """Compare safety profiles.

        Args:
            d1: Device 1 normalized data.
            d2: Device 2 normalized data.

        Returns:
            Safety comparison result.
        """
        score = 50.0
        factors = []

        # Same product code implies similar risk profile
        pc1 = d1.get("product_code", "")
        pc2 = d2.get("product_code", "")
        if pc1 and pc2 and pc1 == pc2:
            score += 25
            factors.append("Same product code implies similar risk classification")

        # Supplement count comparison (for PMAs, many supplements may indicate issues)
        supp1 = d1.get("supplement_count", 0)
        supp2 = d2.get("supplement_count", 0)
        if supp1 > 0 or supp2 > 0:
            # Large differences in supplement count may indicate different safety profiles
            max_supp = max(supp1, supp2)
            min_supp = min(supp1, supp2)
            if max_supp > 0:
                ratio = min_supp / max_supp
                supp_score = ratio * 15
                score += supp_score
                factors.append(f"Supplement ratio: {min_supp}/{max_supp}")

        return {
            "score": round(min(score, 100.0), 1),
            "factors": factors,
            "detail": "; ".join(factors) if factors else "Baseline safety comparison",
        }

    def _compare_regulatory(self, d1: Dict, d2: Dict) -> Dict:
        """Compare regulatory history and pathway.

        Args:
            d1: Device 1 normalized data.
            d2: Device 2 normalized data.

        Returns:
            Regulatory comparison result.
        """
        score = 0.0
        factors = []

        # Same pathway type
        type1 = d1.get("device_type", "")
        type2 = d2.get("device_type", "")
        if type1 == type2:
            score += 30
            factors.append(f"Same pathway ({type1})")
        else:
            score += 10
            factors.append(f"Cross-pathway comparison ({type1} vs {type2})")

        # Product code match
        pc1 = d1.get("product_code", "")
        pc2 = d2.get("product_code", "")
        if pc1 and pc2 and pc1 == pc2:
            score += 30
            factors.append(f"Same product code ({pc1})")

        # Decision date proximity (closer dates = more relevant)
        dd1 = d1.get("decision_date", "")
        dd2 = d2.get("decision_date", "")
        if dd1 and dd2 and len(dd1) >= 4 and len(dd2) >= 4:
            try:
                year1 = int(dd1[:4])
                year2 = int(dd2[:4])
                diff = abs(year1 - year2)
                if diff <= 2:
                    score += 20
                    factors.append(f"Approved within {diff} years of each other")
                elif diff <= 5:
                    score += 10
                    factors.append(f"Approved {diff} years apart")
                else:
                    score += 5
                    factors.append(f"Approved {diff} years apart (significant gap)")
            except ValueError as e:
                print(f"Warning: Could not parse decision_date years for regulatory comparison: {e}", file=sys.stderr)

        # Regulatory status match
        status1 = d1.get("regulatory_status", "")
        status2 = d2.get("regulatory_status", "")
        if status1 and status2 and status1 == status2:
            score += 20
            factors.append(f"Same regulatory status ({status1})")

        return {
            "score": round(min(score, 100.0), 1),
            "factors": factors,
            "detail": "; ".join(factors) if factors else "Regulatory comparison",
        }

    # ------------------------------------------------------------------
    # Suitability assessment
    # ------------------------------------------------------------------

    def assess_suitability(
        self,
        candidate: str,
        subject_device: Dict,
        refresh: bool = False,
    ) -> Dict:
        """Assess a device's suitability as a predicate for a subject device.

        Works for both K-numbers and P-numbers as candidates.

        Args:
            candidate: Device number of the predicate candidate.
            subject_device: Dict with subject device info:
                - product_code: Target product code
                - intended_use: Subject device intended use
                - device_description: Subject device description
            refresh: Force data refresh.

        Returns:
            Suitability assessment dict with score, factors, and recommendation.
        """
        candidate_data = self.analyze_predicate(candidate, refresh=refresh)

        if not candidate_data.get("valid"):
            return {
                "candidate": candidate,
                "suitable": False,
                "score": 0,
                "max_score": 100,
                "error": candidate_data.get("error", "Could not retrieve device data"),
            }

        score = 0.0
        factors = []

        # Product code match (25 points)
        cand_pc = candidate_data.get("product_code", "")
        subj_pc = subject_device.get("product_code", "")
        if cand_pc and subj_pc:
            if cand_pc == subj_pc:
                score += SUITABILITY_WEIGHTS["product_code_match"]
                factors.append(f"Same product code ({cand_pc}) (+{SUITABILITY_WEIGHTS['product_code_match']})")
            else:
                factors.append(f"Different product code ({cand_pc} vs {subj_pc}) (+0)")

        # Indication overlap (30 points)
        cand_use = candidate_data.get("intended_use", "")
        subj_use = subject_device.get("intended_use", "")
        if cand_use and subj_use:
            ind_sim = _cosine_similarity(cand_use, subj_use)
            ind_score = ind_sim * SUITABILITY_WEIGHTS["indication_overlap"]
            score += ind_score
            factors.append(f"Indication similarity: {ind_score:.0f}/{SUITABILITY_WEIGHTS['indication_overlap']}")
        elif not cand_use:
            factors.append("No indication text available for candidate")

        # Device description similarity (20 points)
        cand_desc = candidate_data.get("device_description", "")
        subj_desc = subject_device.get("device_description", "")
        if cand_desc and subj_desc:
            desc_sim = _cosine_similarity(cand_desc, subj_desc)
            desc_score = desc_sim * SUITABILITY_WEIGHTS["device_similarity"]
            score += desc_score
            factors.append(f"Device similarity: {desc_score:.0f}/{SUITABILITY_WEIGHTS['device_similarity']}")

        # Recency (10 points)
        dd = candidate_data.get("decision_date", "")
        if dd and len(dd) >= 4:
            try:
                year = int(dd[:4])
                current_year = datetime.now().year
                age = current_year - year
                if age <= 5:
                    rec_score = SUITABILITY_WEIGHTS["recency"]
                    score += rec_score
                    factors.append(f"Recent ({age} years old) (+{rec_score})")
                elif age <= 10:
                    rec_score = SUITABILITY_WEIGHTS["recency"] // 2
                    score += rec_score
                    factors.append(f"Moderate age ({age} years) (+{rec_score})")
                else:
                    factors.append(f"Older device ({age} years) (+0)")
            except ValueError as e:
                print(f"Warning: Could not parse decision_date year for suitability assessment: {e}", file=sys.stderr)

        # Clinical evidence availability (10 points)
        if candidate_data.get("has_clinical_data"):
            ce_score = SUITABILITY_WEIGHTS["clinical_evidence"]
            score += ce_score
            factors.append(f"Clinical data available (+{ce_score})")
        elif candidate_data.get("has_ssed_sections"):
            ce_score = SUITABILITY_WEIGHTS["clinical_evidence"] // 2
            score += ce_score
            factors.append(f"SSED sections available (+{ce_score})")
        else:
            factors.append("No clinical data available (+0)")

        # Regulatory standing (5 points)
        status = candidate_data.get("regulatory_status", "")
        if status in ("cleared", "approved", "granted"):
            rs_score = SUITABILITY_WEIGHTS["regulatory_standing"]
            score += rs_score
            factors.append(f"Active regulatory status ({status}) (+{rs_score})")

        # Determine recommendation
        if score >= 70:
            suitable = True
            recommendation = "STRONG reference. High similarity across multiple dimensions."
        elif score >= 50:
            suitable = True
            recommendation = "MODERATE reference. Some similarity, review specific differences."
        elif score >= 30:
            suitable = False
            recommendation = "WEAK reference. Significant differences may require justification."
        else:
            suitable = False
            recommendation = "NOT recommended as reference. Low similarity across dimensions."

        # Add pathway-specific notes
        pathway_notes = []
        cand_type = candidate_data.get("device_type", "")
        if cand_type == "pma":
            pathway_notes.append(
                "PMA predicate: Clinical evidence from SSED may support SE argument. "
                "Consider whether PMA-level evidence strengthens or overcomplicates the submission."
            )
            if candidate_data.get("supplement_count", 0) > 10:
                pathway_notes.append(
                    f"Active PMA with {candidate_data['supplement_count']} supplements -- "
                    "indicates ongoing product evolution. Verify current labeling."
                )
        elif cand_type == "510k":
            pathway_notes.append(
                "510(k) predicate: Standard substantial equivalence comparison applies."
            )

        return {
            "candidate": candidate,
            "candidate_type": cand_type,
            "suitable": suitable,
            "score": round(score, 1),
            "max_score": 100,
            "recommendation": recommendation,
            "factors": factors,
            "pathway_notes": pathway_notes,
            "candidate_summary": {
                "device_name": candidate_data.get("device_name", ""),
                "applicant": candidate_data.get("applicant", ""),
                "product_code": candidate_data.get("product_code", ""),
                "decision_date": candidate_data.get("decision_date", ""),
                "device_type": cand_type,
                "supplement_count": candidate_data.get("supplement_count", 0),
                "has_clinical_data": candidate_data.get("has_clinical_data", False),
            },
        }

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def analyze_batch(
        self,
        device_numbers: List[str],
        refresh: bool = False,
    ) -> Dict[str, Dict]:
        """Analyze multiple devices in batch.

        Args:
            device_numbers: List of device numbers (mixed K/P/DEN).
            refresh: Force refresh.

        Returns:
            Dict mapping device number to analysis result.
        """
        results = {}
        for num in device_numbers:
            results[num.upper()] = self.analyze_predicate(num, refresh=refresh)
        return results

    def compare_all_pairs(
        self,
        device_numbers: List[str],
        refresh: bool = False,
    ) -> List[Dict]:
        """Compare all pairs of devices.

        Args:
            device_numbers: List of device numbers.
            refresh: Force refresh.

        Returns:
            List of pairwise comparison results.
        """
        comparisons = []
        for i in range(len(device_numbers)):
            for j in range(i + 1, len(device_numbers)):
                comparison = self.compare_devices(
                    device_numbers[i],
                    device_numbers[j],
                    refresh=refresh,
                )
                comparisons.append(comparison)
        return comparisons

    # ------------------------------------------------------------------
    # PMA-specific utilities for SE table integration
    # ------------------------------------------------------------------

    def get_pma_se_table_data(self, pma_number: str) -> Dict:
        """Extract PMA data formatted for SE comparison table rows.

        Maps SSED sections to SE table dimensions so PMA devices can
        participate in 510(k) SE comparison tables.

        Args:
            pma_number: PMA P-number.

        Returns:
            Dict with SE table-compatible fields.
        """
        data = self.analyze_predicate(pma_number)
        if not data.get("valid"):
            return {"error": data.get("error", "Could not retrieve PMA data")}

        # Get SSED sections for richer data
        sections = self.pma_store.get_extracted_sections(pma_number)
        section_content = {}
        if sections:
            section_dict = sections.get("sections", sections)
            for ssed_key, se_key in SSED_TO_SE_MAPPING.items():
                sec = section_dict.get(ssed_key, {})
                if isinstance(sec, dict):
                    section_content[se_key] = sec.get("content", "")
                elif isinstance(sec, str):
                    section_content[se_key] = sec

        return {
            "device_number": pma_number,
            "device_type": "pma",
            "device_name": data.get("device_name", ""),
            "applicant": data.get("applicant", ""),
            "product_code": data.get("product_code", ""),
            "decision_date": data.get("decision_date", ""),
            "intended_use": data.get("intended_use", "") or section_content.get("intended_use", ""),
            "device_description": section_content.get("device_description", "") or data.get("device_description", ""),
            "clinical_data": section_content.get("clinical_data", ""),
            "performance_testing": section_content.get("performance_testing", ""),
            "sterilization": section_content.get("sterilization", ""),
            "biocompatibility": section_content.get("biocompatibility", ""),
            "safety_profile": section_content.get("safety_profile", ""),
            "regulatory_status": "PMA Approved",
            "data_source": "ssed" if section_content else "api_metadata",
            "section_quality": sections.get("metadata", {}).get("quality_score", 0) if sections else 0,
        }

    def get_pma_intelligence_summary(self, pma_number: str) -> Dict:
        """Get a brief intelligence summary for a PMA device.

        Useful for integration into research reports and presub packages
        without running the full intelligence engine.

        Args:
            pma_number: PMA P-number.

        Returns:
            Brief intelligence summary dict.
        """
        data = self.analyze_predicate(pma_number)
        if not data.get("valid"):
            return {"error": data.get("error")}

        # Get supplement info
        supplements = self.pma_store.get_supplements(pma_number)
        supp_count = len(supplements) if supplements else 0

        # Categorize supplements
        supp_types = {}
        if supplements:
            for s in supplements:
                stype = s.get("supplement_type", "Unknown")
                supp_types[stype] = supp_types.get(stype, 0) + 1

        return {
            "pma_number": pma_number,
            "device_name": data.get("device_name", ""),
            "applicant": data.get("applicant", ""),
            "product_code": data.get("product_code", ""),
            "decision_date": data.get("decision_date", ""),
            "supplement_count": supp_count,
            "supplement_types": supp_types,
            "has_clinical_data": data.get("has_clinical_data", False),
            "has_ssed_sections": data.get("has_ssed_sections", False),
            "clinical_data_source": data.get("clinical_data_source", "none"),
        }


# ------------------------------------------------------------------
# Text similarity utilities (lightweight, no dependency on pma_comparison)
# ------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words.

    Args:
        text: Raw text string.

    Returns:
        List of lowercase word tokens (length > 2).
    """
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in cleaned.split() if len(w) > 2]


def _word_overlap(text1: str, text2: str) -> float:
    """Calculate Jaccard word overlap between two texts.

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


def _cosine_similarity(text1: str, text2: str) -> float:
    """Calculate cosine similarity between two texts using TF vectors.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Cosine similarity (0.0 to 1.0).
    """
    import math
    from collections import Counter

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
# CLI interface
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Unified Predicate Analyzer -- Analyze 510(k) and PMA devices"
    )
    parser.add_argument("--device", help="Analyze a device number (K/P/DEN)")
    parser.add_argument("--compare", nargs=2, metavar=("DEV1", "DEV2"),
                        help="Compare two device numbers")
    parser.add_argument("--assess", help="Assess device as predicate candidate")
    parser.add_argument("--product-code", help="Subject device product code (for --assess)")
    parser.add_argument("--intended-use", help="Subject device intended use (for --assess)")
    parser.add_argument("--batch", help="Analyze multiple devices (comma-separated)")
    parser.add_argument("--refresh", action="store_true", help="Force API refresh")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    analyzer = UnifiedPredicateAnalyzer()

    if args.device:
        result = analyzer.analyze_predicate(args.device, refresh=args.refresh)
        if args.json:
            # Remove raw_data for cleaner JSON output
            result.pop("raw_data", None)
            print(json.dumps(result, indent=2))
        else:
            _print_analysis(result)

    elif args.compare:
        result = analyzer.compare_devices(
            args.compare[0], args.compare[1], refresh=args.refresh
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            _print_comparison(result)

    elif args.assess:
        subject = {
            "product_code": args.product_code or "",
            "intended_use": args.intended_use or "",
        }
        result = analyzer.assess_suitability(
            args.assess, subject, refresh=args.refresh
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            _print_suitability(result)

    elif args.batch:
        numbers = [n.strip() for n in args.batch.split(",") if n.strip()]
        results = analyzer.analyze_batch(numbers, refresh=args.refresh)
        if args.json:
            # Remove raw_data from each
            for _k, v in results.items():
                v.pop("raw_data", None)
            print(json.dumps(results, indent=2))
        else:
            for _num, result in results.items():
                _print_analysis(result)
                print()

    else:
        parser.print_help()


def _print_analysis(result: Dict) -> None:
    """Print device analysis in readable format."""
    if not result.get("valid"):
        print(f"ERROR: {result.get('error', 'Unknown error')}")
        return

    print(f"{'=' * 60}")
    print(f"Device: {result['device_number']} ({result['device_type'].upper()})")
    print(f"{'=' * 60}")
    print(f"  Name:         {result.get('device_name', 'N/A')}")
    print(f"  Applicant:    {result.get('applicant', 'N/A')}")
    print(f"  Product Code: {result.get('product_code', 'N/A')}")
    print(f"  Decision:     {result.get('decision_date', 'N/A')}")
    print(f"  Status:       {result.get('regulatory_status', 'N/A')}")
    print(f"  Supplements:  {result.get('supplement_count', 0)}")
    print(f"  Clinical:     {'Yes' if result.get('has_clinical_data') else 'No'}")
    print(f"  Data Source:  {result.get('clinical_data_source', 'N/A')}")


def _print_comparison(result: Dict) -> None:
    """Print comparison result in readable format."""
    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return

    d1 = result["device1"]
    d2 = result["device2"]
    print(f"{'=' * 60}")
    print(f"Comparison: {d1['number']} ({d1['type']}) vs {d2['number']} ({d2['type']})")
    print(f"{'=' * 60}")
    print(f"  Overall Similarity: {result['overall_similarity']}/100 ({result['similarity_level']})")
    print()
    print(f"  Dimensions:")
    for dim, data in result.get("dimensions", {}).items():
        print(f"    {dim:25s} {data.get('score', 0):5.1f}/100  {data.get('detail', '')[:50]}")
    print()
    if result.get("key_differences"):
        print(f"  Key Differences:")
        for diff in result["key_differences"]:
            print(f"    [{diff['severity']}] {diff['dimension']}: {diff.get('detail', '')[:60]}")


def _print_suitability(result: Dict) -> None:
    """Print suitability assessment in readable format."""
    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return

    print(f"{'=' * 60}")
    print(f"Predicate Suitability: {result['candidate']} ({result.get('candidate_type', 'N/A').upper()})")
    print(f"{'=' * 60}")
    print(f"  Score: {result['score']}/{result['max_score']}")
    print(f"  Suitable: {'YES' if result['suitable'] else 'NO'}")
    print(f"  {result['recommendation']}")
    print()
    print(f"  Factors:")
    for f in result.get("factors", []):
        print(f"    - {f}")
    if result.get("pathway_notes"):
        print()
        print(f"  Pathway Notes:")
        for note in result["pathway_notes"]:
            print(f"    * {note}")


if __name__ == "__main__":
    main()
