#!/usr/bin/env python3
"""
PMA Intelligence Module -- Clinical data analysis, supplement tracking,
and predicate intelligence for PMA devices.

Provides automated extraction and analysis of:
    - Clinical trial data (study design, endpoints, enrollment, results)
    - Supplement history (categorization, labeling changes, post-approval studies)
    - Predicate intelligence (citing 510(k)s, comparable PMAs, suitability)
    - Confidence scoring for all extracted data

Builds on Phase 0 infrastructure (PMADataStore, PMAExtractor, FDAClient)
and works alongside pma_comparison.py for comparative analysis.

Usage:
    from pma_intelligence import PMAIntelligenceEngine

    engine = PMAIntelligenceEngine()
    report = engine.generate_intelligence("P170019")
    clinical = engine.extract_clinical_intelligence("P170019")
    supplements = engine.analyze_supplements("P170019")

    # CLI usage:
    python3 pma_intelligence.py --pma P170019
    python3 pma_intelligence.py --pma P170019 --focus clinical
    python3 pma_intelligence.py --pma P170019 --focus supplements
    python3 pma_intelligence.py --pma P170019 --find-citing-510ks
"""

import argparse
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Import sibling modules
from pma_data_store import PMADataStore
from pma_section_extractor import PMAExtractor

# Import helpers for safe optional imports (FDA-17 / GAP-015)
lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
from import_helpers import  # type: ignore safe_import

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Clinical study design patterns
# ------------------------------------------------------------------

STUDY_DESIGN_PATTERNS = {
    "pivotal_rct": {
        "label": "Pivotal Randomized Controlled Trial",
        "patterns": [
            r"(?i)pivotal\s+randomized\s+controlled",
            r"(?i)pivotal\s+RCT",
            r"(?i)randomized\s+controlled\s+(?:trial|study).*pivotal",
        ],
    },
    "pivotal_single_arm": {
        "label": "Pivotal Single-Arm Study",
        "patterns": [
            r"(?i)pivotal\s+single[- ]arm",
            r"(?i)single[- ]arm\s+pivotal",
        ],
    },
    "rct": {
        "label": "Randomized Controlled Trial",
        "patterns": [
            r"(?i)randomized\s+controlled\s+(?:trial|study)",
            r"(?i)\bRCT\b",
        ],
    },
    "single_arm": {
        "label": "Single-Arm Study",
        "patterns": [
            r"(?i)single[- ]arm\s+(?:study|trial|design)",
            r"(?i)non[- ]?randomized.*single[- ]arm",
        ],
    },
    "registry": {
        "label": "Registry Study",
        "patterns": [
            r"(?i)registry\s+(?:study|data|analysis|based)",
            r"(?i)(?:patient|device)\s+registry",
        ],
    },
    "prospective_cohort": {
        "label": "Prospective Cohort Study",
        "patterns": [
            r"(?i)prospective\s+cohort",
            r"(?i)prospective\s+(?:observational|non[- ]?randomized)",
        ],
    },
    "retrospective": {
        "label": "Retrospective Study",
        "patterns": [
            r"(?i)retrospective\s+(?:study|analysis|review|cohort)",
        ],
    },
    "feasibility": {
        "label": "Feasibility/Pilot Study",
        "patterns": [
            r"(?i)feasibility\s+(?:study|trial|investigation)",
            r"(?i)pilot\s+(?:study|trial)",
            r"(?i)first[- ]?in[- ]?(?:human|man)\s+(?:study|trial)",
        ],
    },
    "post_approval": {
        "label": "Post-Approval Study",
        "patterns": [
            r"(?i)post[- ]?approval\s+(?:study|data|surveillance)",
            r"(?i)post[- ]?market\s+(?:study|surveillance)",
            r"(?i)PAS\b",
        ],
    },
    "meta_analysis": {
        "label": "Meta-Analysis/Systematic Review",
        "patterns": [
            r"(?i)meta[- ]?analysis",
            r"(?i)systematic\s+review",
        ],
    },
    "bayesian": {
        "label": "Bayesian Adaptive Design",
        "patterns": [
            r"(?i)bayesian\s+(?:adaptive|design|analysis)",
            r"(?i)adaptive\s+(?:bayesian|design)",
        ],
    },
    "non_inferiority": {
        "label": "Non-Inferiority Trial",
        "patterns": [
            r"(?i)non[- ]?inferiority\s+(?:trial|study|design|margin)",
        ],
    },
    "sham_controlled": {
        "label": "Sham-Controlled Trial",
        "patterns": [
            r"(?i)sham[- ]?controlled",
        ],
    },
    "double_blind": {
        "label": "Double-Blind Trial",
        "patterns": [
            r"(?i)double[- ]?blind",
        ],
    },
}

# Compiled patterns for efficiency
_COMPILED_DESIGNS = {}
for key, design in STUDY_DESIGN_PATTERNS.items():
    _COMPILED_DESIGNS[key] = [re.compile(p) for p in design["patterns"]]


# ------------------------------------------------------------------
# Supplement type classification
# ------------------------------------------------------------------

SUPPLEMENT_TYPES = {
    "labeling": {
        "label": "Labeling Change",
        "keywords": [
            "labeling", "label", "instructions for use", "IFU",
            "warnings", "precautions", "contraindications",
        ],
    },
    "design_change": {
        "label": "Design Change",
        "keywords": [
            "design change", "modification", "model", "configuration",
            "material change", "component", "manufacturing change",
        ],
    },
    "indication_expansion": {
        "label": "New Indication / Indication Expansion",
        "keywords": [
            "new indication", "additional indication", "expanded indication",
            "new use", "extended indication", "new patient population",
        ],
    },
    "post_approval_study": {
        "label": "Post-Approval Study",
        "keywords": [
            "post-approval study", "PAS", "condition of approval",
            "post-market", "surveillance", "annual report",
        ],
    },
    "manufacturing": {
        "label": "Manufacturing Change",
        "keywords": [
            "manufacturing", "facility", "process change", "sterilization",
            "supplier", "site change",
        ],
    },
    "panel_track": {
        "label": "Panel-Track Supplement",
        "keywords": [
            "panel track", "significant change",
        ],
    },
}


# ------------------------------------------------------------------
# PMA Intelligence Engine
# ------------------------------------------------------------------

class PMAIntelligenceEngine:
    """Automated intelligence extraction and analysis for PMA devices.

    Extracts clinical trial data, tracks supplement history, and provides
    predicate intelligence with confidence scoring.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize PMA Intelligence Engine.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()
        self.extractor = PMAExtractor(store=self.store)

    # ------------------------------------------------------------------
    # Main intelligence entry point
    # ------------------------------------------------------------------

    def generate_intelligence(
        self,
        pma_number: str,
        focus: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict:
        """Generate a comprehensive intelligence report for a PMA.

        Args:
            pma_number: PMA number (e.g., 'P170019').
            focus: Optional focus area ('clinical', 'supplements', 'predicates', 'all').
            refresh: Force refresh of underlying data.

        Returns:
            Intelligence report dictionary.
        """
        pma_key = pma_number.upper()

        # Load base data
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        sections = self.store.get_extracted_sections(pma_key)

        if api_data.get("error") and not sections:
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
                "intelligence_version": "2.0.0",
            }

        report = {
            "pma_number": pma_key,
            "intelligence_version": "2.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "device_summary": self._build_device_summary(api_data),
        }

        # Clinical intelligence
        if focus in (None, "all", "clinical"):
            report["clinical_intelligence"] = self.extract_clinical_intelligence(
                pma_key, api_data, sections
            )

        # Supplement intelligence
        if focus in (None, "all", "supplements"):
            report["supplement_intelligence"] = self.analyze_supplements(
                pma_key, refresh=refresh
            )

        # Predicate intelligence
        if focus in (None, "all", "predicates"):
            report["predicate_intelligence"] = self.analyze_predicate_relationships(
                pma_key, api_data
            )

        # Post-approval monitoring (Phase 3 integration)
        if focus in (None, "all", "supplements"):
            report["post_approval_monitoring"] = self.get_post_approval_summary(
                pma_key, api_data, refresh=refresh
            )

        # Generate executive summary
        report["executive_summary"] = self._generate_executive_summary(report)

        # Save intelligence report to cache
        self._save_intelligence_report(pma_key, report)

        return report

    # ------------------------------------------------------------------
    # Clinical Intelligence
    # ------------------------------------------------------------------

    def extract_clinical_intelligence(
        self,
        pma_number: str,
        api_data: Optional[Dict] = None,
        sections: Optional[Dict] = None,
    ) -> Dict:
        """Extract clinical trial intelligence from SSED sections.

        Args:
            pma_number: PMA number.
            api_data: Pre-loaded API data (or will be loaded).
            sections: Pre-loaded extracted sections (or will be loaded).

        Returns:
            Clinical intelligence dictionary.
        """
        pma_key = pma_number.upper()

        if api_data is None:
            api_data = self.store.get_pma_data(pma_key)
        if sections is None:
            sections = self.store.get_extracted_sections(pma_key)

        # Get clinical text
        clinical_text = self._get_section_content(sections, "clinical_studies")
        stat_text = self._get_section_content(sections, "statistical_analysis")
        combined_text = f"{clinical_text or ''} {stat_text or ''}".strip()

        if not combined_text:
            return {
                "has_clinical_data": False,
                "data_source": "none",
                "confidence": 0.0,
                "note": "No clinical study sections found in extracted SSED data.",
            }

        # Extract each clinical dimension
        study_designs = self.detect_study_designs(combined_text)
        enrollment = self.extract_enrollment_data(combined_text)
        endpoints = self.extract_endpoints(combined_text)
        efficacy = self.extract_efficacy_results(combined_text)
        safety_data = self.extract_adverse_events(
            self._get_section_content(sections, "potential_risks") or combined_text
        )
        follow_up = self._extract_follow_up(combined_text)

        # Calculate confidence
        confidence = self._calculate_clinical_confidence(
            study_designs, enrollment, endpoints, efficacy, safety_data
        )

        return {
            "has_clinical_data": True,
            "data_source": "ssed_extraction",
            "confidence": round(confidence, 2),
            "study_designs": study_designs,
            "enrollment": enrollment,
            "endpoints": endpoints,
            "efficacy_results": efficacy,
            "adverse_events": safety_data,
            "follow_up": follow_up,
            "clinical_text_word_count": len(combined_text.split()),
        }

    def detect_study_designs(self, text: str) -> List[Dict]:
        """Identify study design types from clinical text.

        Args:
            text: Clinical study text.

        Returns:
            List of detected study design dicts with label and confidence.
        """
        if not text:
            return []

        detected = []
        for key, patterns in _COMPILED_DESIGNS.items():
            best_match = None
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    best_match = match
                    break

            if best_match:
                design_def = STUDY_DESIGN_PATTERNS[key]
                detected.append({
                    "type": key,
                    "label": design_def["label"],
                    "matched_text": best_match.group().strip(),
                    "position": best_match.start(),
                    "confidence": 0.90 if key.startswith("pivotal") else 0.80,
                })

        # Sort by position (order of appearance in text)
        detected.sort(key=lambda d: d["position"])

        return detected

    def extract_enrollment_data(self, text: str) -> Dict:
        """Extract sample size and enrollment information.

        Args:
            text: Clinical text.

        Returns:
            Enrollment data dict.
        """
        if not text:
            return {"total_enrollment": None, "confidence": 0.0}

        result: Dict[str, Any] = {
            "total_enrollment": None,
            "enrollment_details": [],
            "demographics_mentioned": False,
            "sites_mentioned": False,
            "confidence": 0.0,
        }

        # Enrollment patterns (ordered by specificity)
        enrollment_patterns = [
            (r"(?i)(?:total\s+)?(?:enrolled|enrollment)\s*(?:of|was|:)?\s*(\d[\d,]*)\s*(?:patients?|subjects?|participants?)", 0.95),
            (r"(?i)(\d[\d,]*)\s*(?:patients?|subjects?|participants?)\s+(?:were\s+)?enrolled", 0.90),
            (r"(?i)N\s*=\s*(\d[\d,]*)", 0.80),
            (r"(?i)sample\s+size\s*(?:of|was|:)?\s*(\d[\d,]*)", 0.85),
            (r"(?i)(?:study|trial)\s+(?:included|comprised|enrolled)\s*(\d[\d,]*)", 0.85),
            (r"(?i)(\d[\d,]*)\s+(?:patients?|subjects?)\s+(?:completed|in\s+the\s+(?:study|trial))", 0.75),
        ]

        best_enrollment = None
        best_confidence = 0.0

        for pattern, conf in enrollment_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    n = int(match.group(1).replace(",", ""))
                    if n >= 10:  # Filter out single-digit numbers (likely not enrollment)
                        result["enrollment_details"].append({
                            "value": n,
                            "matched_text": match.group().strip()[:100],
                            "confidence": conf,
                        })
                        if conf > best_confidence or (
                            conf == best_confidence
                            and (best_enrollment is None or n > best_enrollment)
                        ):
                            best_enrollment = n
                            best_confidence = conf
                except ValueError:
                    continue

        result["total_enrollment"] = best_enrollment
        result["confidence"] = best_confidence

        # Check for demographics
        demo_patterns = [
            r"(?i)(?:mean|median)\s+age",
            r"(?i)(?:male|female)\s+(?:patients?|subjects?)",
            r"(?i)gender\s+distribution",
            r"(?i)demographic",
            r"(?i)(?:\d+\.?\d*)\s*%\s*(?:male|female|women|men)",
        ]
        result["demographics_mentioned"] = any(
            re.search(p, text) for p in demo_patterns
        )

        # Check for multi-site
        site_patterns = [
            r"(?i)(\d+)\s+(?:clinical\s+)?sites?",
            r"(?i)multi[- ]?(?:center|site)",
            r"(?i)(\d+)\s+investigat(?:ional|ing)\s+sites?",
        ]
        for p in site_patterns:
            match = re.search(p, text)
            if match:
                result["sites_mentioned"] = True
                try:
                    result["number_of_sites"] = int(match.group(1))
                except (IndexError, ValueError) as e:
                    logger.warning("Could not parse number of sites: %s", e)
                break

        return result

    def extract_endpoints(self, text: str) -> Dict:
        """Extract primary, secondary, and safety endpoints.

        Args:
            text: Clinical text.

        Returns:
            Endpoints dict with primary, secondary, and safety lists.
        """
        if not text:
            return {"primary": [], "secondary": [], "safety": [], "confidence": 0.0}

        result: Dict[str, Any] = {
            "primary": [],
            "secondary": [],
            "safety": [],
            "confidence": 0.0,
        }

        # Primary endpoint patterns
        primary_patterns = [
            r"(?i)primary\s+(?:end\s*point|outcome|efficacy\s+end\s*point)\s*(?:was|is|:)\s*([^.;]{10,150})",
            r"(?i)(?:the\s+)?primary\s+(?:end\s*point|outcome)\s+(?:of|for)\s+(?:the\s+)?(?:study|trial)\s*(?:was|is|:)\s*([^.;]{10,150})",
        ]
        for pattern in primary_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                endpoint_text = match.group(1).strip()
                if endpoint_text and endpoint_text not in [e["text"] for e in result["primary"]]:
                    result["primary"].append({
                        "text": endpoint_text,
                        "confidence": 0.85,
                    })

        # Secondary endpoint patterns
        secondary_patterns = [
            r"(?i)secondary\s+(?:end\s*point|outcome)s?\s*(?:included?|were?|is|:)\s*([^.;]{10,200})",
            r"(?i)(?:key\s+)?secondary\s+(?:end\s*point|outcome)s?\s*(?:was|is|:)\s*([^.;]{10,150})",
        ]
        for pattern in secondary_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                endpoint_text = match.group(1).strip()
                if endpoint_text and endpoint_text not in [e["text"] for e in result["secondary"]]:
                    result["secondary"].append({
                        "text": endpoint_text,
                        "confidence": 0.80,
                    })

        # Safety endpoint patterns
        safety_patterns = [
            r"(?i)(?:primary\s+)?safety\s+(?:end\s*point|outcome)s?\s*(?:included?|were?|was|is|:)\s*([^.;]{10,200})",
            r"(?i)(?:device[- ]?related\s+)?(?:serious\s+)?adverse\s+events?\s+(?:rate|incidence|at)\s*([^.;]{5,100})",
        ]
        for pattern in safety_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                endpoint_text = match.group(1).strip()
                if endpoint_text and endpoint_text not in [e["text"] for e in result["safety"]]:
                    result["safety"].append({
                        "text": endpoint_text,
                        "confidence": 0.80,
                    })

        # Overall confidence based on extraction quality
        total_found = len(result["primary"]) + len(result["secondary"]) + len(result["safety"])
        if total_found >= 3:
            result["confidence"] = 0.85
        elif total_found >= 1:
            result["confidence"] = 0.65
        else:
            result["confidence"] = 0.20

        return result

    def extract_efficacy_results(self, text: str) -> Dict:
        """Extract efficacy outcome data from clinical text.

        Args:
            text: Clinical text.

        Returns:
            Efficacy results dict.
        """
        if not text:
            return {"results": [], "confidence": 0.0}

        results: List[Dict] = []

        # Success/efficacy rate patterns
        rate_patterns = [
            (r"(?i)(?:success|efficacy|response)\s+rate\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%", "success_rate"),
            (r"(?i)(?:primary\s+)?(?:end\s*point|outcome)\s+(?:was\s+)?(?:met|achieved)\s+(?:in|by)\s*(\d+\.?\d*)\s*%", "endpoint_met_rate"),
            (r"(?i)(?:overall\s+)?survival\s+(?:rate\s+)?(?:of|was|:)?\s*(\d+\.?\d*)\s*%", "survival_rate"),
        ]

        for pattern, result_type in rate_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    value = float(match.group(1))
                    results.append({
                        "type": result_type,
                        "value": value,
                        "unit": "%",
                        "matched_text": match.group().strip()[:120],
                        "confidence": 0.85,
                    })
                except ValueError:
                    continue

        # P-value patterns
        p_patterns = [
            r"(?i)p\s*[<=<]\s*(0?\.\d+)",
            r"(?i)p\s*-?\s*value\s*(?:of|was|=|:)?\s*(0?\.\d+)",
        ]
        for pattern in p_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    value = float(match.group(1))
                    if 0 < value <= 1:
                        results.append({
                            "type": "p_value",
                            "value": value,
                            "significant": value < 0.05,
                            "matched_text": match.group().strip()[:80],
                            "confidence": 0.90,
                        })
                except ValueError:
                    continue

        # Confidence interval patterns
        ci_patterns = [
            r"(?i)(?:95%?\s+)?(?:CI|confidence\s+interval)\s*[:\(]?\s*(\d+\.?\d*)\s*[,\-to]+\s*(\d+\.?\d*)",
        ]
        for pattern in ci_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    lower = float(match.group(1))
                    upper = float(match.group(2))
                    results.append({
                        "type": "confidence_interval",
                        "lower": lower,
                        "upper": upper,
                        "matched_text": match.group().strip()[:100],
                        "confidence": 0.85,
                    })
                except ValueError:
                    continue

        # Sensitivity / Specificity
        ss_patterns = [
            (r"(?i)sensitivity\s*(?:\([^)]+\))?\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%?", "sensitivity"),
            (r"(?i)specificity\s*(?:\([^)]+\))?\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%?", "specificity"),
            (r"(?i)(?:positive\s+percent\s+agreement|PPA)\s*(?:\([^)]+\))?\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%?", "PPA"),
            (r"(?i)(?:negative\s+percent\s+agreement|NPA)\s*(?:\([^)]+\))?\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%?", "NPA"),
        ]
        for pattern, metric_type in ss_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    results.append({
                        "type": metric_type,
                        "value": value,
                        "unit": "%",
                        "matched_text": match.group().strip()[:100],
                        "confidence": 0.85,
                    })
                except ValueError as e:
                    logger.warning("Could not parse efficacy metric value: %s", e)

        return {
            "results": results,
            "total_metrics_extracted": len(results),
            "confidence": 0.80 if results else 0.0,
        }

    def extract_adverse_events(self, text: str) -> Dict:
        """Extract adverse event information from safety text.

        Args:
            text: Safety/adverse event text.

        Returns:
            Adverse event data dict.
        """
        if not text:
            return {"events": [], "confidence": 0.0}

        events: List[Dict] = []

        # AE rate patterns
        ae_patterns = [
            r"(?i)(?:device[- ]?related\s+)?(?:serious\s+)?adverse\s+event\s+rate\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%",
            r"(?i)(\d+\.?\d*)\s*%\s+(?:experienced?\s+)?(?:device[- ]?related\s+)?(?:serious\s+)?adverse\s+events?",
            r"(?i)(?:SAE|SADE)\s+rate\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%",
        ]
        for pattern in ae_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    value = float(match.group(1))
                    events.append({
                        "type": "ae_rate",
                        "value": value,
                        "unit": "%",
                        "matched_text": match.group().strip()[:120],
                        "confidence": 0.80,
                    })
                except ValueError:
                    continue

        # Specific adverse event types
        ae_types = [
            "death", "stroke", "myocardial infarction", "infection",
            "thrombosis", "hemorrhage", "perforation", "migration",
            "device malfunction", "explant", "revision",
            "reintervention", "amputation", "embolism",
        ]

        for ae_type in ae_types:
            pattern = rf"(?i)({ae_type})\s*[:\(]?\s*(\d+\.?\d*)\s*%"
            match = re.search(pattern, text)
            if match:
                try:
                    events.append({
                        "type": "specific_ae",
                        "event": ae_type,
                        "value": float(match.group(2)),
                        "unit": "%",
                        "matched_text": match.group().strip()[:80],
                        "confidence": 0.75,
                    })
                except ValueError as e:
                    logger.warning("Could not parse adverse event value: %s", e)

        # Total AE count
        count_pattern = r"(?i)(\d+)\s+(?:serious\s+)?adverse\s+events?\s+(?:were\s+)?(?:reported|observed|recorded)"
        count_match = re.search(count_pattern, text)
        total_aes = None
        if count_match:
            try:
                total_aes = int(count_match.group(1))
            except ValueError as e:
                logger.warning("Could not parse total adverse event count: %s", e)

        return {
            "events": events,
            "total_ae_count": total_aes,
            "total_metrics_extracted": len(events),
            "confidence": 0.75 if events else 0.0,
        }

    def _extract_follow_up(self, text: str) -> Dict:
        """Extract follow-up duration from clinical text.

        Args:
            text: Clinical text.

        Returns:
            Follow-up data dict.
        """
        if not text:
            return {"duration": None, "confidence": 0.0}

        patterns = [
            (r"(?i)(?:follow[- ]?up|FU)\s+(?:of|period|duration)?\s*(?:was\s+)?(\d+)\s*(years?|months?|weeks?|days?)", 0.90),
            (r"(?i)(\d+)[- ](?:year|month|week|day)\s+follow[- ]?up", 0.90),
            (r"(?i)followed\s+(?:for|up\s+to)\s+(\d+)\s*(years?|months?|weeks?|days?)", 0.85),
            (r"(?i)(?:minimum|median|mean)\s+follow[- ]?up\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*(years?|months?|weeks?|days?)", 0.85),
        ]

        best_match = None
        best_confidence = 0.0

        for pattern, conf in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    duration = float(match.group(1))
                    unit = match.group(2).lower().rstrip("s")
                    if conf > best_confidence:
                        best_match = {
                            "duration": duration,
                            "unit": unit,
                            "matched_text": match.group().strip()[:80],
                        }
                        best_confidence = conf
                except (ValueError, IndexError):
                    continue

        if best_match:
            return {
                "duration": best_match["duration"],
                "unit": best_match["unit"],
                "matched_text": best_match["matched_text"],
                "confidence": best_confidence,
            }

        return {"duration": None, "confidence": 0.0}

    def _calculate_clinical_confidence(
        self,
        study_designs: List[Dict],
        enrollment: Dict,
        endpoints: Dict,
        efficacy: Dict,
        safety: Dict,
    ) -> float:
        """Calculate overall confidence for clinical intelligence extraction.

        Args:
            study_designs: Detected study designs.
            enrollment: Enrollment data.
            endpoints: Endpoint data.
            efficacy: Efficacy results.
            safety: Safety data.

        Returns:
            Overall confidence score (0.0 to 1.0).
        """
        scores = []

        # Study design confidence
        if study_designs:
            scores.append(max(d.get("confidence", 0) for d in study_designs))
        else:
            scores.append(0.0)

        # Enrollment confidence
        scores.append(enrollment.get("confidence", 0.0))

        # Endpoint confidence
        scores.append(endpoints.get("confidence", 0.0))

        # Efficacy confidence
        scores.append(efficacy.get("confidence", 0.0))

        # Safety confidence
        scores.append(safety.get("confidence", 0.0))

        # Average of all sub-confidences
        return sum(scores) / len(scores) if scores else 0.0

    # ------------------------------------------------------------------
    # Supplement Intelligence
    # ------------------------------------------------------------------

    def analyze_supplements(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict:
        """Analyze all supplements for a PMA.

        Args:
            pma_number: PMA number.
            refresh: Force refresh from API.

        Returns:
            Supplement analysis dict.
        """
        pma_key = pma_number.upper()
        supplements = self.store.get_supplements(pma_key, refresh=refresh)

        if not supplements:
            return {
                "total_supplements": 0,
                "supplement_types": {},
                "timeline": [],
                "note": "No supplements found or data unavailable.",
            }

        # Categorize supplements
        categorized = self._categorize_supplements(supplements)

        # Track labeling changes
        labeling_changes = self._track_labeling_changes(supplements)

        # Identify post-approval studies
        pas_supplements = self._identify_post_approval_studies(supplements)

        # Build timeline
        timeline = self._build_supplement_timeline(supplements)

        # Supplement frequency analysis
        frequency = self._analyze_supplement_frequency(supplements)

        return {
            "total_supplements": len(supplements),
            "supplement_types": categorized,
            "labeling_changes": labeling_changes,
            "post_approval_studies": pas_supplements,
            "timeline": timeline,
            "frequency_analysis": frequency,
            "most_recent_supplement": supplements[0] if supplements else None,
        }

    def _categorize_supplements(self, supplements: List[Dict]) -> Dict:
        """Categorize supplements by type based on reason/type fields.

        Args:
            supplements: List of supplement dicts from API.

        Returns:
            Dict of category -> count and examples.
        """
        categories: Dict[str, Any] = {}

        for supp in supplements:
            supp_type = supp.get("supplement_type", "").lower()
            supp_reason = supp.get("supplement_reason", "").lower()
            combined = f"{supp_type} {supp_reason}"

            # Match to category
            matched_category = "other"
            for cat_key, cat_def in SUPPLEMENT_TYPES.items():
                for keyword in cat_def["keywords"]:
                    if keyword.lower() in combined:
                        matched_category = cat_key
                        break
                if matched_category != "other":
                    break

            if matched_category not in categories:
                categories[matched_category] = {
                    "label": SUPPLEMENT_TYPES.get(matched_category, {}).get("label", "Other"),
                    "count": 0,
                    "examples": [],
                }

            categories[matched_category]["count"] += 1
            if len(categories[matched_category]["examples"]) < 3:
                categories[matched_category]["examples"].append({
                    "pma_number": supp.get("pma_number", ""),
                    "supplement_number": supp.get("supplement_number", ""),
                    "decision_date": supp.get("decision_date", ""),
                    "reason": supp.get("supplement_reason", ""),
                })

        return categories

    def _track_labeling_changes(self, supplements: List[Dict]) -> List[Dict]:
        """Identify labeling-related supplements.

        Args:
            supplements: List of supplement dicts.

        Returns:
            List of labeling change dicts.
        """
        labeling_keywords = [
            "labeling", "label", "instructions", "IFU", "warnings",
            "precautions", "contraindication", "indication",
        ]

        changes = []
        for supp in supplements:
            combined = f"{supp.get('supplement_type', '')} {supp.get('supplement_reason', '')}".lower()
            if any(kw in combined for kw in labeling_keywords):
                changes.append({
                    "pma_number": supp.get("pma_number", ""),
                    "supplement_number": supp.get("supplement_number", ""),
                    "decision_date": supp.get("decision_date", ""),
                    "type": supp.get("supplement_type", ""),
                    "reason": supp.get("supplement_reason", ""),
                })

        return changes

    def _identify_post_approval_studies(self, supplements: List[Dict]) -> List[Dict]:
        """Find post-approval study supplements.

        Args:
            supplements: List of supplement dicts.

        Returns:
            List of PAS supplement dicts.
        """
        pas_keywords = [
            "post-approval", "post approval", "PAS", "condition of approval",
            "post-market", "surveillance", "annual report",
        ]

        pas_supplements = []
        for supp in supplements:
            combined = f"{supp.get('supplement_type', '')} {supp.get('supplement_reason', '')}".lower()
            if any(kw.lower() in combined for kw in pas_keywords):
                pas_supplements.append({
                    "pma_number": supp.get("pma_number", ""),
                    "supplement_number": supp.get("supplement_number", ""),
                    "decision_date": supp.get("decision_date", ""),
                    "type": supp.get("supplement_type", ""),
                    "reason": supp.get("supplement_reason", ""),
                })

        return pas_supplements

    def _build_supplement_timeline(self, supplements: List[Dict]) -> List[Dict]:
        """Build chronological supplement timeline.

        Args:
            supplements: List of supplement dicts.

        Returns:
            Sorted timeline of supplements.
        """
        timeline = []
        for supp in supplements:
            dd = supp.get("decision_date", "")
            timeline.append({
                "date": dd,
                "pma_number": supp.get("pma_number", ""),
                "supplement_number": supp.get("supplement_number", ""),
                "type": supp.get("supplement_type", ""),
                "reason": supp.get("supplement_reason", ""),
                "decision_code": supp.get("decision_code", ""),
            })

        # Sort by date ascending
        timeline.sort(key=lambda x: x.get("date", ""))
        return timeline

    def _analyze_supplement_frequency(self, supplements: List[Dict]) -> Dict:
        """Analyze supplement frequency patterns.

        Args:
            supplements: List of supplement dicts.

        Returns:
            Frequency analysis dict.
        """
        if not supplements:
            return {"avg_per_year": 0, "years_active": 0}

        dates = []
        for supp in supplements:
            dd = supp.get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    dates.append(int(dd[:4]))
                except ValueError:
                    continue

        if not dates:
            return {"avg_per_year": 0, "years_active": 0}

        min_year = min(dates)
        max_year = max(dates)
        years_active = max(max_year - min_year, 1)

        year_counts = Counter(dates)

        return {
            "first_supplement_year": min_year,
            "latest_supplement_year": max_year,
            "years_active": years_active,
            "avg_per_year": round(len(supplements) / years_active, 1),
            "max_in_single_year": max(year_counts.values()) if year_counts else 0,
            "year_distribution": dict(sorted(year_counts.items())),
        }

    # ------------------------------------------------------------------
    # Predicate Intelligence
    # ------------------------------------------------------------------

    def analyze_predicate_relationships(
        self,
        pma_number: str,
        api_data: Optional[Dict] = None,
    ) -> Dict:
        """Analyze predicate relationships for a PMA.

        Finds citing 510(k)s and comparable PMAs.

        Args:
            pma_number: PMA number.
            api_data: Pre-loaded API data (or will be loaded).

        Returns:
            Predicate relationship analysis dict.
        """
        pma_key = pma_number.upper()

        if api_data is None:
            api_data = self.store.get_pma_data(pma_key)

        if api_data is None:
            api_data = {}

        product_code = api_data.get("product_code", "")
        advisory_committee = api_data.get("advisory_committee", "")

        # Find comparable PMAs (same product code)
        comparable_pmas = self._find_comparable_pmas(
            pma_key, product_code, advisory_committee
        )

        # Find citing 510(k)s (same product code, may reference this PMA)
        citing_510ks = self._find_citing_510ks(pma_key, product_code)

        return {
            "comparable_pmas": comparable_pmas,
            "citing_510ks": citing_510ks,
            "product_code": product_code,
            "advisory_committee": advisory_committee,
        }

    def _find_comparable_pmas(
        self,
        pma_number: str,
        product_code: str,
        _advisory_committee: str,
    ) -> List[Dict]:
        """Find PMAs comparable to the given PMA.

        Args:
            pma_number: Primary PMA number.
            product_code: Product code to search.
            _advisory_committee: Advisory committee code (reserved for future use).

        Returns:
            List of comparable PMA summaries.
        """
        if not product_code:
            return []

        # Search by product code
        result = self.store.client.search_pma(
            product_code=product_code, limit=50
        )

        if result.get("degraded") or not result.get("results"):
            return []

        comparable = []
        seen = set()
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            # Extract base PMA
            base_pma = re.sub(r"S\d+$", "", pn)

            # Skip self and supplements, and duplicates
            if base_pma == pma_number or base_pma in seen:
                continue
            if "S" in pn[1:]:
                continue

            seen.add(base_pma)
            comparable.append({
                "pma_number": base_pma,
                "device_name": r.get("trade_name", r.get("generic_name", "N/A")),
                "applicant": r.get("applicant", "N/A"),
                "decision_date": r.get("decision_date", "N/A"),
                "product_code": r.get("product_code", product_code),
            })

        # Sort by decision date descending
        comparable.sort(
            key=lambda x: x.get("decision_date", ""), reverse=True
        )

        return comparable[:20]  # Limit to 20

    def _find_citing_510ks(
        self,
        pma_number: str,
        product_code: str,
    ) -> List[Dict]:
        """Find 510(k)s that may cite this PMA as a predicate.

        Since openFDA does not directly link 510(k) predicates to PMAs,
        we search for 510(k)s with the same product code that were
        cleared after the PMA was approved.

        Args:
            pma_number: PMA number.
            product_code: Product code.

        Returns:
            List of potentially citing 510(k) dicts.
        """
        if not product_code:
            return []

        # Search for 510(k)s with same product code
        result = self.store.client.get_clearances(product_code, limit=25)

        if result.get("degraded") or not result.get("results"):
            return []

        citing = []
        for r in result.get("results", []):
            citing.append({
                "k_number": r.get("k_number", "N/A"),
                "device_name": r.get("device_name", "N/A"),
                "applicant": r.get("applicant", "N/A"),
                "decision_date": r.get("decision_date", "N/A"),
                "clearance_type": r.get("clearance_type", "N/A"),
                "note": (
                    f"Same product code ({product_code}). "
                    f"May use {pma_number} or related PMA as reference."
                ),
            })

        return citing[:15]  # Limit to 15

    def assess_predicate_suitability(
        self,
        pma_number: str,
        subject_device: Dict,
    ) -> Dict:
        """Assess whether a PMA is suitable as a predicate/reference for a device.

        Args:
            pma_number: PMA number to assess as predicate.
            subject_device: Dict describing the subject device with fields:
                - product_code: Product code
                - intended_use: Intended use text
                - device_description: Device description text

        Returns:
            Suitability assessment dict.
        """
        pma_key = pma_number.upper()
        pma_data = self.store.get_pma_data(pma_key)
        sections = self.store.get_extracted_sections(pma_key)

        if pma_data.get("error"):
            return {
                "pma_number": pma_key,
                "suitable": False,
                "score": 0,
                "reason": f"Could not retrieve PMA data: {pma_data.get('error')}",
            }

        score = 0.0
        factors = []

        # Product code match (30 points)
        pma_pc = pma_data.get("product_code", "")
        subject_pc = subject_device.get("product_code", "")
        if pma_pc and subject_pc:
            if pma_pc == subject_pc:
                score += 30
                factors.append("Same product code (+30)")
            else:
                factors.append("Different product code (+0)")

        # Indication overlap (30 points)
        pma_indication = ""
        if sections:
            section_dict = sections.get("sections", sections)
            ind = section_dict.get("indications_for_use", {})
            if isinstance(ind, dict):
                pma_indication = ind.get("content", "")

        subject_use = subject_device.get("intended_use", "")
        if pma_indication and subject_use:
            from pma_comparison import _cosine_similarity
            ind_score = _cosine_similarity(pma_indication, subject_use) * 30
            score += ind_score
            factors.append(f"Indication similarity: {ind_score:.0f}/30")

        # Device description overlap (20 points)
        pma_desc = ""
        if sections:
            section_dict = sections.get("sections", sections)
            desc = section_dict.get("device_description", {})
            if isinstance(desc, dict):
                pma_desc = desc.get("content", "")

        subject_desc = subject_device.get("device_description", "")
        if pma_desc and subject_desc:
            from pma_comparison import _cosine_similarity
            desc_score = _cosine_similarity(pma_desc, subject_desc) * 20
            score += desc_score
            factors.append(f"Device description similarity: {desc_score:.0f}/20")

        # Recency bonus (10 points)
        dd = pma_data.get("decision_date", "")
        if dd and len(dd) >= 4:
            try:
                pma_year = int(dd[:4])
                current_year = datetime.now().year
                age = current_year - pma_year
                if age <= 5:
                    score += 10
                    factors.append(f"Recent approval ({age} years) (+10)")
                elif age <= 10:
                    score += 5
                    factors.append(f"Moderate age ({age} years) (+5)")
                else:
                    factors.append(f"Older approval ({age} years) (+0)")
            except ValueError as e:
                logger.warning("Could not parse decision_date year for suitability scoring: %s", e)

        # Clinical data availability (10 points)
        if sections:
            section_dict = sections.get("sections", sections)
            if "clinical_studies" in section_dict:
                clinical = section_dict["clinical_studies"]
                if isinstance(clinical, dict) and clinical.get("word_count", 0) > 200:
                    score += 10
                    factors.append("Clinical data available (+10)")
                else:
                    score += 5
                    factors.append("Limited clinical data (+5)")
            else:
                factors.append("No clinical data sections (+0)")

        # Determine suitability
        if score >= 70:
            suitable = True
            recommendation = "STRONG reference. High similarity across multiple dimensions."
        elif score >= 50:
            suitable = True
            recommendation = "MODERATE reference. Some similarity but review specific differences."
        elif score >= 30:
            suitable = False
            recommendation = "WEAK reference. Significant differences may require justification."
        else:
            suitable = False
            recommendation = "NOT recommended as reference. Low similarity across dimensions."

        return {
            "pma_number": pma_key,
            "suitable": suitable,
            "score": round(score, 1),
            "max_score": 100,
            "recommendation": recommendation,
            "factors": factors,
            "pma_summary": {
                "device_name": pma_data.get("device_name", ""),
                "applicant": pma_data.get("applicant", ""),
                "product_code": pma_data.get("product_code", ""),
                "decision_date": pma_data.get("decision_date", ""),
            },
        }

    # ------------------------------------------------------------------
    # Phase 3 Integration: Post-Approval Monitoring
    # ------------------------------------------------------------------

    def get_post_approval_summary(
        self,
        pma_number: str,
        api_data: Optional[Dict] = None,
        refresh: bool = False,
    ) -> Dict:
        """Generate post-approval monitoring summary using Phase 3 modules.

        Integrates data from supplement_tracker, annual_report_tracker,
        and pas_monitor to provide a unified post-approval view.

        Args:
            pma_number: PMA number.
            api_data: Pre-loaded API data (or will be loaded).
            refresh: Force refresh from API.

        Returns:
            Post-approval monitoring summary dict.
        """
        pma_key = pma_number.upper()

        if api_data is None:
            api_data = self.store.get_pma_data(pma_key, refresh=refresh)

        summary: Dict[str, Any] = {
            "has_post_approval_data": False,
            "supplement_lifecycle": None,
            "annual_report_compliance": None,
            "pas_monitoring": None,
        }

        # Try supplement lifecycle analysis
        result = safe_import('supplement_tracker', 'SupplementTracker', log_level=logging.DEBUG)
        if result.success:
            try:
                tracker = result.module(store=self.store)
                supp_report = tracker.generate_supplement_report(pma_key, refresh=refresh)

                if supp_report and not supp_report.get("error"):
                    summary["has_post_approval_data"] = True
                    summary["supplement_lifecycle"] = {
                        "total_supplements": supp_report.get("total_supplements", 0),
                        "regulatory_type_distribution": supp_report.get("regulatory_type_distribution", {}),
                        "change_impact": supp_report.get("change_impact", {}),
                        "risk_flags": supp_report.get("risk_flags", []),
                        "frequency": supp_report.get("frequency_analysis", {}),
                    }
            except Exception as e:
                logger.error(f"Error running supplement tracker: {e}", exc_info=True)
                summary["supplement_lifecycle"] = {
                    "note": f"Supplement tracker error: {type(e).__name__}"
                }
        else:
            summary["supplement_lifecycle"] = {
                "note": "Supplement tracker module not available."
            }

        # Try annual report compliance
        result = safe_import('annual_report_tracker', 'AnnualReportTracker', log_level=logging.DEBUG)
        if result.success:
            try:
                ar_tracker = result.module(store=self.store)
                ar_report = ar_tracker.generate_compliance_calendar(pma_key, refresh=refresh)

                if ar_report and not ar_report.get("error"):
                    summary["has_post_approval_data"] = True
                    summary["annual_report_compliance"] = {
                        "next_due_date": ar_report.get("next_due_date", {}),
                        "total_expected_reports": ar_report.get("total_expected_reports", 0),
                        "compliance_risks": ar_report.get("compliance_risks", []),
                    }
            except Exception as e:
                logger.error(f"Error running annual report tracker: {e}", exc_info=True)
                summary["annual_report_compliance"] = {
                    "note": f"Annual report tracker error: {type(e).__name__}"
                }
        else:
            summary["annual_report_compliance"] = {
                "note": "Annual report tracker module not available."
            }

        # Try PAS monitoring
        result = safe_import('pas_monitor', 'PASMonitor', log_level=logging.DEBUG)
        if result.success:
            try:
                monitor = result.module(store=self.store)
                pas_report = monitor.generate_pas_report(pma_key, refresh=refresh)

                if pas_report and not pas_report.get("error"):
                    summary["has_post_approval_data"] = True
                    summary["pas_monitoring"] = {
                        "pas_required": pas_report.get("pas_required", False),
                        "pas_requirements": pas_report.get("pas_requirements", []),
                        "pas_status": pas_report.get("pas_status", {}),
                        "compliance": pas_report.get("compliance", {}),
                        "alerts": pas_report.get("alerts", []),
                    }
            except Exception as e:
                logger.error(f"Error running PAS monitor: {e}", exc_info=True)
                summary["pas_monitoring"] = {
                    "note": f"PAS monitor error: {type(e).__name__}"
                }
        else:
            summary["pas_monitoring"] = {
                "note": "PAS monitor module not available."
            }

        return summary

    # ------------------------------------------------------------------
    # Phase 4 Integration: Advanced Analytics & ML
    # ------------------------------------------------------------------

    def get_advanced_analytics_summary(
        self,
        pma_number: str,
        api_data: Optional[Dict] = None,
        refresh: bool = False,
    ) -> Dict:
        """Generate advanced analytics summary using Phase 4 modules.

        Integrates review time prediction, approval probability scoring,
        MAUDE peer comparison, and competitive intelligence.

        Args:
            pma_number: PMA number.
            api_data: Pre-loaded API data (or will be loaded).
            refresh: Force refresh from API.

        Returns:
            Advanced analytics summary dict.
        """
        pma_key = pma_number.upper()

        if api_data is None:
            api_data = self.store.get_pma_data(pma_key, refresh=refresh)

        summary: Dict[str, Any] = {
            "has_analytics_data": False,
            "review_time_prediction": None,
            "approval_probability": None,
            "maude_comparison": None,
        }

        # Try review time prediction
        result = safe_import('review_time_predictor', 'ReviewTimePredictionEngine', log_level=logging.DEBUG)
        if result.success:
            try:
                predictor = result.module(store=self.store)
                prediction = predictor.predict_review_time(pma_key, refresh=refresh)

                if prediction and not prediction.get("error"):
                    summary["has_analytics_data"] = True
                    pred = prediction.get("prediction", {})
                    summary["review_time_prediction"] = {
                        "expected_days": pred.get("expected_days"),
                        "expected_months": pred.get("expected_months"),
                        "model_confidence": pred.get("model_confidence"),
                        "risk_factor_count": len(pred.get("risk_factors", [])),
                    }
            except Exception as e:
                logger.error(f"Error running review time predictor: {e}", exc_info=True)
                summary["review_time_prediction"] = {
                    "note": f"Review time predictor error: {type(e).__name__}"
                }
        else:
            summary["review_time_prediction"] = {
                "note": "Review time predictor module not available."
            }

        # Try approval probability
        result = safe_import('approval_probability', 'ApprovalProbabilityScorer', log_level=logging.DEBUG)
        if result.success:
            try:
                scorer = result.module(store=self.store)
                scores = scorer.score_approval_probability(pma_key, refresh=refresh)

                if scores and not scores.get("error"):
                    summary["has_analytics_data"] = True
                    agg = scores.get("aggregate_analysis", {})
                    summary["approval_probability"] = {
                        "avg_probability": agg.get("avg_approval_probability"),
                        "classification_accuracy": agg.get("classification_accuracy"),
                        "total_scored": agg.get("total_scored", 0),
                    }
            except Exception as e:
                logger.error(f"Error running approval probability scorer: {e}", exc_info=True)
                summary["approval_probability"] = {
                    "note": f"Approval probability scorer error: {type(e).__name__}"
                }
        else:
            summary["approval_probability"] = {
                "note": "Approval probability scorer module not available."
            }

        # Try MAUDE comparison
        result = safe_import('maude_comparison', 'MAUDEComparisonEngine', log_level=logging.DEBUG)
        if result.success:
            try:
                engine = result.module(store=self.store)
                profile = engine.build_adverse_event_profile(pma_key, refresh=refresh)

                if profile and profile.get("total_events", 0) > 0:
                    summary["has_analytics_data"] = True
                    summary["maude_comparison"] = {
                        "total_events": profile.get("total_events", 0),
                        "death_count": profile.get("death_count", 0),
                        "injury_count": profile.get("injury_count", 0),
                        "malfunction_count": profile.get("malfunction_count", 0),
                        "has_death_reports": profile.get("has_death_reports", False),
                    }
            except Exception as e:
                logger.error(f"Error running MAUDE comparison: {e}", exc_info=True)
                summary["maude_comparison"] = {
                    "note": f"MAUDE comparison error: {type(e).__name__}"
                }
        else:
            summary["maude_comparison"] = {
                "note": "MAUDE comparison engine not available."
            }

        return summary

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _build_device_summary(self, api_data: Dict) -> Dict:
        """Build device summary from API data.

        Args:
            api_data: PMA API data dict.

        Returns:
            Device summary dict.
        """
        return {
            "pma_number": api_data.get("pma_number", ""),
            "device_name": api_data.get("device_name", ""),
            "generic_name": api_data.get("generic_name", ""),
            "applicant": api_data.get("applicant", ""),
            "product_code": api_data.get("product_code", ""),
            "decision_date": api_data.get("decision_date", ""),
            "decision_code": api_data.get("decision_code", ""),
            "advisory_committee": api_data.get("advisory_committee", ""),
            "advisory_committee_description": api_data.get("advisory_committee_description", ""),
            "supplement_count": api_data.get("supplement_count", 0),
            "expedited_review": api_data.get("expedited_review_flag", "N"),
        }

    def _get_section_content(self, sections: Optional[Dict], key: str) -> Optional[str]:
        """Get text content from an extracted section.

        Args:
            sections: Extracted sections dict.
            key: Section key.

        Returns:
            Section content text or None.
        """
        if not sections:
            return None

        section_dict = sections.get("sections", sections)
        section = section_dict.get(key)

        if section is None:
            return None

        if isinstance(section, dict):
            return section.get("content", "")

        if isinstance(section, str):
            return section

        return None

    def _generate_executive_summary(self, report: Dict) -> Dict:
        """Generate executive summary from intelligence report.

        Args:
            report: Full intelligence report dict.

        Returns:
            Executive summary dict.
        """
        summary_points = []
        risk_level = "LOW"

        # Device info
        device = report.get("device_summary", {})
        summary_points.append(
            f"{device.get('device_name', 'Unknown')} by {device.get('applicant', 'Unknown')}, "
            f"approved {device.get('decision_date', 'N/A')}"
        )

        # Clinical intelligence highlights
        clinical = report.get("clinical_intelligence", {})
        if clinical.get("has_clinical_data"):
            designs = clinical.get("study_designs", [])
            if designs:
                design_labels = [d["label"] for d in designs[:3]]
                summary_points.append(f"Study designs: {', '.join(design_labels)}")

            enrollment = clinical.get("enrollment", {})
            if enrollment.get("total_enrollment"):
                summary_points.append(
                    f"Total enrollment: {enrollment['total_enrollment']:,} patients"
                )

            efficacy = clinical.get("efficacy_results", {})
            n_metrics = efficacy.get("total_metrics_extracted", 0)
            if n_metrics > 0:
                summary_points.append(f"{n_metrics} efficacy metrics extracted")
        else:
            summary_points.append("No clinical data extracted from SSED sections")
            risk_level = "MEDIUM"

        # Supplement highlights
        supplements = report.get("supplement_intelligence", {})
        total_supps = supplements.get("total_supplements", 0)
        if total_supps > 0:
            summary_points.append(f"{total_supps} supplements filed")
            labeling = supplements.get("labeling_changes", [])
            if labeling:
                summary_points.append(f"{len(labeling)} labeling changes identified")
            pas = supplements.get("post_approval_studies", [])
            if pas:
                summary_points.append(f"{len(pas)} post-approval study supplements")
                risk_level = max(risk_level, "MEDIUM")

        # Predicate intelligence highlights
        predicates = report.get("predicate_intelligence", {})
        comparable = predicates.get("comparable_pmas", [])
        if comparable:
            summary_points.append(f"{len(comparable)} comparable PMAs identified")
        citing = predicates.get("citing_510ks", [])
        if citing:
            summary_points.append(f"{len(citing)} related 510(k) clearances found")

        # Post-approval monitoring highlights
        post_approval = report.get("post_approval_monitoring", {})
        if post_approval.get("has_post_approval_data"):
            supp_lifecycle = post_approval.get("supplement_lifecycle", {})
            risk_flags = supp_lifecycle.get("risk_flags", [])
            if risk_flags:
                flag_count = len(risk_flags) if isinstance(risk_flags, list) else 0
                summary_points.append(f"{flag_count} supplement risk flag(s) detected")
                if flag_count >= 3:
                    risk_level = "HIGH"
                elif flag_count >= 1:
                    risk_level = max(risk_level, "MEDIUM")

            pas = post_approval.get("pas_monitoring", {})
            if pas and pas.get("pas_required"):
                pas_status = pas.get("pas_status", {})
                overall = pas_status.get("overall_status", "unknown")
                summary_points.append(f"Post-approval study: {overall}")

            ar = post_approval.get("annual_report_compliance", {})
            ar_risks = ar.get("compliance_risks", []) if ar else []
            if ar_risks:
                high_risks = [r for r in ar_risks if isinstance(r, dict) and r.get("severity") == "HIGH"]
                if high_risks:
                    summary_points.append(f"{len(high_risks)} high-severity annual report compliance risk(s)")
                    risk_level = "HIGH"

        # Overall confidence
        clinical_conf = clinical.get("confidence", 0.0) if clinical.get("has_clinical_data") else 0.0

        return {
            "key_findings": summary_points,
            "clinical_data_available": clinical.get("has_clinical_data", False),
            "clinical_confidence": round(clinical_conf, 2),
            "total_supplements": total_supps,
            "comparable_pmas_count": len(comparable),
            "risk_level": risk_level,
            "post_approval_monitoring_available": post_approval.get("has_post_approval_data", False),
        }

    def _save_intelligence_report(self, pma_number: str, report: Dict) -> None:
        """Save intelligence report to cache.

        Args:
            pma_number: PMA number.
            report: Intelligence report dict.
        """
        pma_dir = self.store.get_pma_dir(pma_number)
        report_path = pma_dir / "intelligence_report.json"
        tmp_path = report_path.with_suffix(".json.tmp")

        try:
            with open(tmp_path, "w") as f:
                json.dump(report, f, indent=2)
            tmp_path.replace(report_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)


# ------------------------------------------------------------------
# CLI interface
# ------------------------------------------------------------------

def _format_intelligence_report(report: Dict) -> str:
    """Format intelligence report as readable text.

    Args:
        report: Intelligence report dict.

    Returns:
        Formatted text output.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("PMA INTELLIGENCE REPORT")
    lines.append("=" * 70)

    # Device Summary
    device = report.get("device_summary", {})
    lines.append(f"PMA Number:  {device.get('pma_number', 'N/A')}")
    lines.append(f"Device:      {device.get('device_name', 'N/A')}")
    lines.append(f"Applicant:   {device.get('applicant', 'N/A')}")
    lines.append(f"Product Code: {device.get('product_code', 'N/A')}")
    lines.append(f"Approved:    {device.get('decision_date', 'N/A')}")
    lines.append(f"Committee:   {device.get('advisory_committee_description', 'N/A')}")
    lines.append("")

    # Executive Summary
    exec_summary = report.get("executive_summary", {})
    lines.append("--- Executive Summary ---")
    for point in exec_summary.get("key_findings", []):
        lines.append(f"  * {point}")
    lines.append(f"  Risk Level: {exec_summary.get('risk_level', 'N/A')}")
    lines.append(f"  Clinical Confidence: {exec_summary.get('clinical_confidence', 0):.0%}")
    lines.append("")

    # Clinical Intelligence
    clinical = report.get("clinical_intelligence", {})
    if clinical.get("has_clinical_data"):
        lines.append("--- Clinical Intelligence ---")
        lines.append(f"  Confidence: {clinical.get('confidence', 0):.0%}")
        lines.append(f"  Text analyzed: {clinical.get('clinical_text_word_count', 0)} words")

        designs = clinical.get("study_designs", [])
        if designs:
            lines.append("  Study Designs:")
            for d in designs:
                lines.append(f"    - {d['label']} (conf: {d['confidence']:.0%})")

        enrollment = clinical.get("enrollment", {})
        if enrollment.get("total_enrollment"):
            lines.append(f"  Enrollment: {enrollment['total_enrollment']:,} patients")
            if enrollment.get("number_of_sites"):
                lines.append(f"  Sites: {enrollment['number_of_sites']}")

        endpoints = clinical.get("endpoints", {})
        for ep_type in ["primary", "secondary", "safety"]:
            eps = endpoints.get(ep_type, [])
            if eps:
                lines.append(f"  {ep_type.title()} Endpoints:")
                for ep in eps[:3]:
                    lines.append(f"    - {ep['text'][:80]}")

        efficacy = clinical.get("efficacy_results", {})
        if efficacy.get("results"):
            lines.append("  Efficacy Results:")
            for r in efficacy["results"][:5]:
                if r["type"] == "p_value":
                    sig = "significant" if r.get("significant") else "not significant"
                    lines.append(f"    - p-value: {r['value']} ({sig})")
                else:
                    lines.append(f"    - {r['type']}: {r.get('value', 'N/A')}{r.get('unit', '')}")

        follow_up = clinical.get("follow_up", {})
        if follow_up.get("duration"):
            lines.append(f"  Follow-up: {follow_up['duration']} {follow_up.get('unit', '')}")

        lines.append("")

    # Supplement Intelligence
    supplements = report.get("supplement_intelligence", {})
    if supplements.get("total_supplements", 0) > 0:
        lines.append("--- Supplement Intelligence ---")
        lines.append(f"  Total Supplements: {supplements['total_supplements']}")

        categories = supplements.get("supplement_types", {})
        if categories:
            lines.append("  By Category:")
            for cat_key, cat_data in categories.items():
                lines.append(f"    - {cat_data.get('label', cat_key)}: {cat_data.get('count', 0)}")

        freq = supplements.get("frequency_analysis", {})
        if freq.get("avg_per_year"):
            lines.append(f"  Average/year: {freq['avg_per_year']}")
            lines.append(f"  Active years: {freq.get('first_supplement_year', 'N/A')}-{freq.get('latest_supplement_year', 'N/A')}")

        labeling = supplements.get("labeling_changes", [])
        if labeling:
            lines.append(f"  Labeling Changes: {len(labeling)}")
            for lc in labeling[:3]:
                lines.append(f"    - {lc.get('pma_number', 'N/A')} ({lc.get('decision_date', 'N/A')})")

        pas = supplements.get("post_approval_studies", [])
        if pas:
            lines.append(f"  Post-Approval Studies: {len(pas)}")

        lines.append("")

    # Predicate Intelligence
    predicates = report.get("predicate_intelligence", {})
    comparable = predicates.get("comparable_pmas", [])
    if comparable:
        lines.append("--- Comparable PMAs ---")
        for p in comparable[:10]:
            lines.append(
                f"  {p['pma_number']}: {p.get('device_name', 'N/A')[:40]} "
                f"({p.get('applicant', 'N/A')[:25]}) - {p.get('decision_date', 'N/A')}"
            )
        lines.append("")

    citing = predicates.get("citing_510ks", [])
    if citing:
        lines.append("--- Related 510(k) Clearances ---")
        for c in citing[:10]:
            lines.append(
                f"  {c['k_number']}: {c.get('device_name', 'N/A')[:40]} "
                f"({c.get('applicant', 'N/A')[:25]}) - {c.get('decision_date', 'N/A')}"
            )
        lines.append("")

    # Post-Approval Monitoring (Phase 3)
    post_approval = report.get("post_approval_monitoring", {})
    if post_approval.get("has_post_approval_data"):
        lines.append("--- Post-Approval Monitoring ---")

        # Supplement Lifecycle
        supp_lc = post_approval.get("supplement_lifecycle", {})
        if supp_lc and not supp_lc.get("note"):
            impact = supp_lc.get("change_impact", {})
            if impact:
                lines.append(f"  Impact Level: {impact.get('impact_level', 'N/A')}")
                lines.append(f"  Burden Score: {impact.get('cumulative_burden_score', 0)}")

            risk_flags = supp_lc.get("risk_flags", [])
            if risk_flags:
                lines.append(f"  Risk Flags ({len(risk_flags)}):")
                for flag in risk_flags[:5]:
                    if isinstance(flag, dict):
                        lines.append(f"    [{flag.get('severity', 'INFO')}] {flag.get('description', 'N/A')}")
                    else:
                        lines.append(f"    - {flag}")

        # Annual Report Compliance
        ar = post_approval.get("annual_report_compliance", {})
        if ar and not ar.get("note"):
            next_due = ar.get("next_due_date", {})
            if next_due:
                lines.append(f"  Next Annual Report: #{next_due.get('report_number', 'N/A')}")
                lines.append(f"    Due: {next_due.get('anniversary_date', 'N/A')}")
                lines.append(f"    Grace Deadline: {next_due.get('grace_deadline', 'N/A')}")
            ar_risks = ar.get("compliance_risks", [])
            if ar_risks:
                lines.append(f"  Compliance Risks: {len(ar_risks)}")

        # PAS Monitoring
        pas = post_approval.get("pas_monitoring", {})
        if pas and not pas.get("note"):
            lines.append(f"  PAS Required: {'YES' if pas.get('pas_required') else 'NO'}")
            if pas.get("pas_required"):
                pas_status = pas.get("pas_status", {})
                lines.append(f"  PAS Status: {pas_status.get('overall_status', 'unknown')}")
                compliance = pas.get("compliance", {})
                if compliance:
                    lines.append(f"  Compliance: {compliance.get('status', 'N/A')}")
                alerts = pas.get("alerts", [])
                if alerts:
                    lines.append(f"  Alerts ({len(alerts)}):")
                    for alert in alerts[:3]:
                        if isinstance(alert, dict):
                            lines.append(f"    [{alert.get('level', 'INFO')}] {alert.get('message', 'N/A')}")
                        else:
                            lines.append(f"    - {alert}")

        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {report.get('generated_at', 'N/A')[:10]}")
    lines.append(f"Intelligence Version: {report.get('intelligence_version', 'N/A')}")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="PMA Intelligence Module -- Clinical data analysis and supplement tracking"
    )
    parser.add_argument("--pma", help="PMA number to analyze")
    parser.add_argument(
        "--focus",
        choices=["clinical", "supplements", "predicates", "all"],
        default="all",
        help="Focus area for analysis",
    )
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--find-citing-510ks",
        action="store_true",
        dest="find_citing",
        help="Find 510(k)s that may cite this PMA",
    )
    parser.add_argument(
        "--assess-predicate",
        dest="assess_predicate",
        help="Assess PMA suitability for a subject device (provide product code)",
    )

    args = parser.parse_args()

    if not args.pma:
        parser.error("Specify --pma PMA_NUMBER")

    engine = PMAIntelligenceEngine()

    # Initialize output variables
    result: Optional[Dict] = None
    report: Optional[Dict] = None

    if args.find_citing:
        api_data = engine.store.get_pma_data(args.pma.upper())
        result = engine.analyze_predicate_relationships(args.pma, api_data)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            citing = result.get("citing_510ks", [])
            print(f"Related 510(k)s for {args.pma.upper()} ({result.get('product_code', 'N/A')}):")
            for c in citing:
                print(f"  {c['k_number']}: {c.get('device_name', 'N/A')[:50]} - {c.get('decision_date', 'N/A')}")

    elif args.assess_predicate:
        subject = {"product_code": args.assess_predicate}
        result = engine.assess_predicate_suitability(args.pma, subject)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Predicate Suitability: {args.pma.upper()}")
            print(f"  Score: {result['score']}/{result['max_score']}")
            print(f"  Suitable: {'YES' if result['suitable'] else 'NO'}")
            print(f"  {result['recommendation']}")
            for f in result.get("factors", []):
                print(f"    - {f}")

    else:
        report = engine.generate_intelligence(
            args.pma, focus=args.focus, refresh=args.refresh
        )

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(_format_intelligence_report(report))

    # Save to file if requested
    if args.output:
        if result is not None:
            output_data = result
        elif report is not None:
            output_data = report
        else:
            output_data = {}
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
