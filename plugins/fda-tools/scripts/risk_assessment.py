#!/usr/bin/env python3
"""
PMA Risk Assessment Framework -- Systematic risk analysis for PMA devices.

Implements a structured risk categorization framework covering device-related,
clinical, regulatory, and manufacturing risks. Analyzes PMA SSED safety sections
for risk patterns, extracts risk mitigation strategies from approved PMAs,
and generates risk-benefit analysis reports with Risk Priority Numbers (RPN).

Integrates with PMA Intelligence for safety data extraction and PMA Comparison
for risk profile comparison across comparable devices.

Usage:
    from risk_assessment import RiskAssessmentEngine

    engine = RiskAssessmentEngine()
    assessment = engine.assess_risks("P170019")
    comparison = engine.compare_risk_profiles("P170019", ["P160035"])
    matrix = engine.generate_risk_matrix("P170019")

    # CLI usage:
    python3 risk_assessment.py --pma P170019
    python3 risk_assessment.py --pma P170019 --compare P160035,P150009
    python3 risk_assessment.py --product-code NMH --risk-landscape
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore
from pma_intelligence import PMAIntelligenceEngine


# ------------------------------------------------------------------
# Risk severity scale (1-5)
# ------------------------------------------------------------------

SEVERITY_SCALE = {
    1: {"label": "Minor", "description": "Temporary discomfort, no medical intervention needed"},
    2: {"label": "Moderate", "description": "Medical intervention required but non-serious"},
    3: {"label": "Serious", "description": "Serious injury, hospitalization, or significant disability"},
    4: {"label": "Critical", "description": "Life-threatening injury or permanent impairment"},
    5: {"label": "Catastrophic", "description": "Death or irreversible major disability"},
}

# ------------------------------------------------------------------
# Risk probability scale (1-5)
# ------------------------------------------------------------------

PROBABILITY_SCALE = {
    1: {"label": "Rare", "description": "< 0.01% occurrence rate", "max_rate": 0.01},
    2: {"label": "Unlikely", "description": "0.01-0.1% occurrence rate", "max_rate": 0.1},
    3: {"label": "Possible", "description": "0.1-1% occurrence rate", "max_rate": 1.0},
    4: {"label": "Likely", "description": "1-10% occurrence rate", "max_rate": 10.0},
    5: {"label": "Frequent", "description": "> 10% occurrence rate", "max_rate": 100.0},
}

# ------------------------------------------------------------------
# Risk detectability scale (1-5)
# ------------------------------------------------------------------

DETECTABILITY_SCALE = {
    1: {"label": "Always Detected", "description": "Risk detected before patient impact"},
    2: {"label": "High Detection", "description": "Risk detected in most cases during use"},
    3: {"label": "Moderate Detection", "description": "Risk may not be detected immediately"},
    4: {"label": "Low Detection", "description": "Risk difficult to detect before harm"},
    5: {"label": "Undetectable", "description": "Risk cannot be detected before patient impact"},
}

# ------------------------------------------------------------------
# Device risk factors with default severity and detectability
# ------------------------------------------------------------------

DEVICE_RISK_FACTORS = {
    "mechanical_failure": {
        "label": "Mechanical Failure / Fracture",
        "category": "device",
        "default_severity": 4,
        "default_detectability": 3,
        "patterns": [
            r"(?i)(?:device|mechanical)\s+failure",
            r"(?i)(?:fracture|breakage|fatigue)\s+(?:of|in)\s+(?:the\s+)?device",
            r"(?i)structural\s+(?:failure|integrity)",
        ],
    },
    "material_biocompat": {
        "label": "Material Biocompatibility",
        "category": "device",
        "default_severity": 3,
        "default_detectability": 3,
        "patterns": [
            r"(?i)biocompatibility",
            r"(?i)(?:material|tissue)\s+(?:reaction|response|compatibility)",
            r"(?i)(?:cytotoxicity|sensitization|irritation|genotoxicity)",
        ],
    },
    "electrical_safety": {
        "label": "Electrical Safety",
        "category": "device",
        "default_severity": 4,
        "default_detectability": 2,
        "patterns": [
            r"(?i)electrical\s+(?:safety|hazard|shock)",
            r"(?i)(?:leakage\s+current|electromagnetic|EMC|EMI)",
            r"(?i)(?:battery|power)\s+(?:failure|depletion)",
        ],
    },
    "software_malfunction": {
        "label": "Software Reliability / Cybersecurity",
        "category": "device",
        "default_severity": 3,
        "default_detectability": 4,
        "patterns": [
            r"(?i)software\s+(?:malfunction|error|failure|bug)",
            r"(?i)cyber\s*security",
            r"(?i)(?:algorithm|AI|machine\s+learning)\s+(?:error|failure|bias)",
        ],
    },
    "migration_displacement": {
        "label": "Device Migration / Displacement",
        "category": "device",
        "default_severity": 4,
        "default_detectability": 3,
        "patterns": [
            r"(?i)(?:device\s+)?migration",
            r"(?i)(?:displacement|dislodgment|embolization)",
        ],
    },
    "sterility_compromise": {
        "label": "Sterility / Contamination",
        "category": "device",
        "default_severity": 3,
        "default_detectability": 2,
        "patterns": [
            r"(?i)steril(?:ity|ization)\s+(?:failure|compromise|breach)",
            r"(?i)(?:contamination|pyrogen|endotoxin)",
        ],
    },
    "adverse_event_serious": {
        "label": "Serious Adverse Events",
        "category": "clinical",
        "default_severity": 4,
        "default_detectability": 2,
        "patterns": [
            r"(?i)serious\s+adverse\s+event",
            r"(?i)\bSAE\b",
            r"(?i)device[- ]?related\s+(?:serious\s+)?(?:adverse|complication)",
        ],
    },
    "death": {
        "label": "Death",
        "category": "clinical",
        "default_severity": 5,
        "default_detectability": 1,
        "patterns": [
            r"(?i)\bdeath\b",
            r"(?i)\bmortality\b",
            r"(?i)(?:fatal|lethal)\s+(?:outcome|event|complication)",
        ],
    },
    "infection": {
        "label": "Infection",
        "category": "clinical",
        "default_severity": 3,
        "default_detectability": 2,
        "patterns": [
            r"(?i)\binfection\b",
            r"(?i)\bsepsis\b",
            r"(?i)(?:wound|surgical\s+site)\s+infection",
        ],
    },
    "thrombosis_embolism": {
        "label": "Thrombosis / Embolism",
        "category": "clinical",
        "default_severity": 4,
        "default_detectability": 3,
        "patterns": [
            r"(?i)\bthrombosis\b",
            r"(?i)\bembolism\b",
            r"(?i)(?:blood\s+)?clot",
            r"(?i)thromboemboli",
        ],
    },
    "hemorrhage": {
        "label": "Hemorrhage / Bleeding",
        "category": "clinical",
        "default_severity": 4,
        "default_detectability": 2,
        "patterns": [
            r"(?i)\bhemorrhage\b",
            r"(?i)(?:major|significant)\s+bleeding",
        ],
    },
    "perforation": {
        "label": "Perforation",
        "category": "clinical",
        "default_severity": 4,
        "default_detectability": 3,
        "patterns": [
            r"(?i)\bperforation\b",
            r"(?i)(?:vessel|organ|tissue)\s+perforation",
        ],
    },
    "revision_explant": {
        "label": "Revision / Explant Required",
        "category": "clinical",
        "default_severity": 3,
        "default_detectability": 2,
        "patterns": [
            r"(?i)\bexplant\b",
            r"(?i)\brevision\b",
            r"(?i)(?:device\s+)?(?:removal|replacement|reintervention)",
        ],
    },
    "off_label_use": {
        "label": "Off-Label Use Potential",
        "category": "clinical",
        "default_severity": 3,
        "default_detectability": 4,
        "patterns": [
            r"(?i)off[- ]?label",
            r"(?i)(?:unapproved|unauthorized)\s+(?:use|indication)",
        ],
    },
    "predicate_acceptability": {
        "label": "Predicate/Reference Acceptability",
        "category": "regulatory",
        "default_severity": 2,
        "default_detectability": 2,
        "patterns": [
            r"(?i)(?:predicate|reference)\s+(?:device|PMA)",
            r"(?i)substantial\s+equivalence",
        ],
    },
    "clinical_evidence_gap": {
        "label": "Clinical Evidence Gap",
        "category": "regulatory",
        "default_severity": 3,
        "default_detectability": 2,
        "patterns": [
            r"(?i)(?:clinical|evidence)\s+(?:gap|deficiency|insufficien)",
            r"(?i)(?:additional|further)\s+(?:clinical\s+)?(?:data|evidence|study|studies)\s+(?:required|needed|recommended)",
        ],
    },
    "labeling_deficiency": {
        "label": "Labeling Deficiency",
        "category": "regulatory",
        "default_severity": 2,
        "default_detectability": 2,
        "patterns": [
            r"(?i)labeling\s+(?:deficiency|issue|concern)",
            r"(?i)(?:contraindication|warning|precaution)\s+(?:missing|inadequate)",
        ],
    },
    "post_approval_requirement": {
        "label": "Post-Approval Study Required",
        "category": "regulatory",
        "default_severity": 2,
        "default_detectability": 1,
        "patterns": [
            r"(?i)post[- ]?approval\s+(?:study|condition|requirement)",
            r"(?i)condition\s+of\s+approval",
            r"(?i)\bPAS\b",
        ],
    },
    "manufacturing_complexity": {
        "label": "Manufacturing Process Complexity",
        "category": "manufacturing",
        "default_severity": 2,
        "default_detectability": 2,
        "patterns": [
            r"(?i)(?:complex|novel)\s+(?:manufacturing|fabrication)\s+process",
            r"(?i)(?:process\s+)?validation\s+(?:challenge|concern)",
        ],
    },
    "sterilization_validation": {
        "label": "Sterilization Validation",
        "category": "manufacturing",
        "default_severity": 3,
        "default_detectability": 2,
        "patterns": [
            r"(?i)sterilization\s+validation",
            r"(?i)(?:EO|ethylene\s+oxide|gamma|e-beam)\s+(?:sterilization|validation)",
        ],
    },
    "shelf_life": {
        "label": "Shelf Life / Stability",
        "category": "manufacturing",
        "default_severity": 2,
        "default_detectability": 2,
        "patterns": [
            r"(?i)shelf\s+life",
            r"(?i)(?:stability|aging)\s+(?:test|study|validation)",
            r"(?i)(?:expiration|expiry)\s+dat(?:e|ing)",
        ],
    },
}

# Compiled patterns
_COMPILED_RISKS = {}
for key, info in DEVICE_RISK_FACTORS.items():
    _COMPILED_RISKS[key] = [re.compile(p) for p in info["patterns"]]

# ------------------------------------------------------------------
# RPN thresholds
# ------------------------------------------------------------------

RPN_HIGH = 100      # RPN >= 100: High priority
RPN_MEDIUM = 50     # RPN >= 50:  Medium priority
# RPN < 50: Low priority


# ------------------------------------------------------------------
# Risk Assessment Engine
# ------------------------------------------------------------------

class RiskAssessmentEngine:
    """Systematic risk analysis for PMA devices using FDA precedent.

    Implements FMEA-style risk categorization with device-related, clinical,
    regulatory, and manufacturing risk dimensions. Extracts risk patterns
    from SSED safety sections and generates risk matrices with RPN scoring.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Risk Assessment Engine.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()
        self.intelligence = PMAIntelligenceEngine(store=self.store)

    # ------------------------------------------------------------------
    # Main risk assessment
    # ------------------------------------------------------------------

    def assess_risks(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict:
        """Perform comprehensive risk assessment for a PMA device.

        Args:
            pma_number: PMA number to analyze.
            refresh: Force refresh of data.

        Returns:
            Risk assessment dict with categorized risks, RPN scores,
            risk matrix, and mitigation strategies.
        """
        pma_key = pma_number.upper()

        # Load data
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        sections = self.store.get_extracted_sections(pma_key)

        if api_data.get("error") and not sections:
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        # Get safety text
        safety_text = self._get_combined_safety_text(sections)
        clinical_text = self._get_clinical_text(sections)

        # Extract adverse event data
        ae_data = self.intelligence.extract_adverse_events(safety_text) if safety_text else {}

        # Identify risks
        identified_risks = self._identify_risks(
            safety_text, clinical_text, ae_data, api_data
        )

        # Score risks (severity, probability, detectability)
        scored_risks = self._score_risks(identified_risks, ae_data, safety_text)

        # Generate risk matrix
        risk_matrix = self._build_risk_matrix(scored_risks)

        # Extract mitigation strategies
        mitigations = self._extract_mitigations(safety_text, clinical_text)

        # Determine residual risk level
        residual_risk = self._assess_residual_risk(scored_risks, mitigations)

        # Build assessment
        assessment = {
            "pma_number": pma_key,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "device_summary": self._build_device_summary(api_data),
            "risk_summary": {
                "total_risks_identified": len(scored_risks),
                "high_priority": len([r for r in scored_risks if r.get("priority") == "HIGH"]),
                "medium_priority": len([r for r in scored_risks if r.get("priority") == "MEDIUM"]),
                "low_priority": len([r for r in scored_risks if r.get("priority") == "LOW"]),
                "categories": self._summarize_by_category(scored_risks),
                "residual_risk_level": residual_risk,
            },
            "identified_risks": scored_risks,
            "risk_matrix": risk_matrix,
            "mitigation_strategies": mitigations,
            "evidence_requirements": self._map_evidence_requirements(scored_risks),
            "adverse_event_data": ae_data,
            "confidence": self._calculate_confidence(safety_text, scored_risks),
        }

        return assessment

    # ------------------------------------------------------------------
    # Risk profile comparison
    # ------------------------------------------------------------------

    def compare_risk_profiles(
        self,
        primary_pma: str,
        comparator_pmas: List[str],
        refresh: bool = False,
    ) -> Dict:
        """Compare risk profiles across multiple PMAs.

        Args:
            primary_pma: Primary PMA number.
            comparator_pmas: List of comparator PMA numbers.
            refresh: Force refresh.

        Returns:
            Risk profile comparison dict.
        """
        all_assessments = {}
        all_assessments[primary_pma.upper()] = self.assess_risks(primary_pma, refresh=refresh)

        for comp in comparator_pmas:
            all_assessments[comp.upper()] = self.assess_risks(comp, refresh=refresh)

        # Compare risk inventories
        risk_overlap = self._calculate_risk_overlap(all_assessments)

        # Compare severity profiles
        severity_comparison = self._compare_severity_profiles(all_assessments)

        return {
            "primary_pma": primary_pma.upper(),
            "comparators": [c.upper() for c in comparator_pmas],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "assessments": all_assessments,
            "risk_overlap": risk_overlap,
            "severity_comparison": severity_comparison,
            "notable_differences": self._identify_risk_differences(all_assessments),
        }

    # ------------------------------------------------------------------
    # Product code risk landscape
    # ------------------------------------------------------------------

    def analyze_risk_landscape(
        self,
        product_code: str,
        limit: int = 10,
    ) -> Dict:
        """Analyze risk landscape for an entire product code.

        Args:
            product_code: FDA product code.
            limit: Maximum PMAs to analyze.

        Returns:
            Risk landscape analysis.
        """
        result = self.store.client.search_pma(
            product_code=product_code, limit=limit, sort="decision_date:desc"
        )

        if result.get("degraded") or not result.get("results"):
            return {
                "product_code": product_code,
                "error": "No PMAs found for this product code",
            }

        # Unique base PMAs
        pma_numbers = []
        seen = set()
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            base = re.sub(r"S\d+$", "", pn)
            if base and base not in seen:
                seen.add(base)
                pma_numbers.append(base)

        pma_numbers = pma_numbers[:limit]

        # Assess each PMA
        all_risks = Counter()
        all_severities = {}

        for pma in pma_numbers:
            assessment = self.assess_risks(pma)
            for risk in assessment.get("identified_risks", []):
                risk_key = risk.get("risk_id", "")
                all_risks[risk_key] += 1
                if risk_key not in all_severities:
                    all_severities[risk_key] = []
                all_severities[risk_key].append(risk.get("severity", 1))

        # Compute landscape summary
        landscape_risks = []
        for risk_key, count in all_risks.most_common():
            severities = all_severities.get(risk_key, [])
            risk_info = DEVICE_RISK_FACTORS.get(risk_key, {})
            landscape_risks.append({
                "risk_id": risk_key,
                "label": risk_info.get("label", risk_key),
                "category": risk_info.get("category", "unknown"),
                "frequency_across_pmas": count,
                "percentage_of_pmas": round(count / len(pma_numbers) * 100, 1),
                "avg_severity": round(sum(severities) / len(severities), 1) if severities else 0,
                "max_severity": max(severities) if severities else 0,
            })

        return {
            "product_code": product_code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pmas_analyzed": len(pma_numbers),
            "pma_numbers": pma_numbers,
            "common_risks": landscape_risks,
            "risk_categories": self._summarize_landscape_categories(landscape_risks),
        }

    # ------------------------------------------------------------------
    # Risk identification
    # ------------------------------------------------------------------

    def _identify_risks(
        self,
        safety_text: str,
        clinical_text: str,
        ae_data: Dict,
        api_data: Dict,
    ) -> List[Dict]:
        """Identify risks from safety text, clinical data, and API data.

        Args:
            safety_text: Combined safety text from SSED.
            clinical_text: Clinical study text.
            ae_data: Extracted adverse event data.
            api_data: PMA API data.

        Returns:
            List of identified risk dicts.
        """
        identified = []
        combined_text = f"{safety_text or ''} {clinical_text or ''}".strip()

        for risk_key, patterns in _COMPILED_RISKS.items():
            for pattern in patterns:
                match = pattern.search(combined_text)
                if match:
                    risk_info = DEVICE_RISK_FACTORS[risk_key]
                    identified.append({
                        "risk_id": risk_key,
                        "label": risk_info["label"],
                        "category": risk_info["category"],
                        "matched_text": match.group().strip()[:100],
                        "position": match.start(),
                        "source": "ssed_extraction",
                    })
                    break  # One match per risk is enough

        # Add inherent risks based on device characteristics
        panel = api_data.get("advisory_committee", "")
        if panel == "CV":
            self._add_if_missing(identified, "thrombosis_embolism")
            self._add_if_missing(identified, "hemorrhage")
        elif panel == "OR":
            self._add_if_missing(identified, "mechanical_failure")
        elif panel == "NE":
            self._add_if_missing(identified, "electrical_safety")

        return identified

    def _add_if_missing(self, risks: List[Dict], risk_id: str) -> None:
        """Add a risk if not already identified."""
        if not any(r.get("risk_id") == risk_id for r in risks):
            risk_info = DEVICE_RISK_FACTORS.get(risk_id, {})
            if risk_info:
                risks.append({
                    "risk_id": risk_id,
                    "label": risk_info.get("label", risk_id),
                    "category": risk_info.get("category", "unknown"),
                    "matched_text": "",
                    "source": "inherent_device_risk",
                })

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    def _score_risks(
        self,
        identified_risks: List[Dict],
        ae_data: Dict,
        safety_text: str,
    ) -> List[Dict]:
        """Score identified risks with severity, probability, detectability.

        Args:
            identified_risks: List of identified risks.
            ae_data: Adverse event data.
            safety_text: Safety text for context.

        Returns:
            List of scored risk dicts with RPN.
        """
        scored = []
        ae_events = ae_data.get("events", [])

        for risk in identified_risks:
            risk_id = risk.get("risk_id", "")
            risk_info = DEVICE_RISK_FACTORS.get(risk_id, {})

            # Determine severity
            severity = risk_info.get("default_severity", 3)

            # Adjust severity based on AE data
            for ae in ae_events:
                ae_type = ae.get("type", "")
                if ae_type == "specific_ae":
                    ae_name = ae.get("event", "").lower()
                    if ae_name in risk_id.lower() or risk_id.lower() in ae_name:
                        rate = ae.get("value", 0)
                        if rate > 5:
                            severity = min(severity + 1, 5)

            # Determine probability
            probability = self._estimate_probability(risk_id, ae_data, safety_text)

            # Determine detectability
            detectability = risk_info.get("default_detectability", 3)

            # Calculate RPN
            rpn = severity * probability * detectability

            # Determine priority
            if rpn >= RPN_HIGH:
                priority = "HIGH"
            elif rpn >= RPN_MEDIUM:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            scored.append({
                **risk,
                "severity": severity,
                "severity_label": SEVERITY_SCALE.get(severity, {}).get("label", "Unknown"),
                "probability": probability,
                "probability_label": PROBABILITY_SCALE.get(probability, {}).get("label", "Unknown"),
                "detectability": detectability,
                "detectability_label": DETECTABILITY_SCALE.get(detectability, {}).get("label", "Unknown"),
                "rpn": rpn,
                "priority": priority,
            })

        # Sort by RPN descending
        scored.sort(key=lambda r: r.get("rpn", 0), reverse=True)

        return scored

    def _estimate_probability(
        self,
        risk_id: str,
        ae_data: Dict,
        safety_text: str,
    ) -> int:
        """Estimate probability score from AE data and text.

        Args:
            risk_id: Risk identifier.
            ae_data: Adverse event data.
            safety_text: Safety text.

        Returns:
            Probability score (1-5).
        """
        # Check if AE data has specific rates
        for ae in ae_data.get("events", []):
            if ae.get("type") == "specific_ae":
                ae_name = ae.get("event", "").lower()
                if ae_name in risk_id.lower() or risk_id.lower() in ae_name:
                    rate = ae.get("value", 0)
                    if rate > 10:
                        return 5
                    elif rate > 1:
                        return 4
                    elif rate > 0.1:
                        return 3
                    elif rate > 0.01:
                        return 2
                    else:
                        return 1

            if ae.get("type") == "ae_rate":
                rate = ae.get("value", 0)
                if rate > 5:
                    return 4
                elif rate > 1:
                    return 3

        # Default estimation from safety text context
        if not safety_text:
            return 2  # Default: unlikely

        # Check for frequency language
        risk_info = DEVICE_RISK_FACTORS.get(risk_id, {})
        label = risk_info.get("label", "").lower()

        freq_patterns = [
            (r"(?i)(?:common|frequent|high\s+rate)\s+(?:of\s+)?" + re.escape(label[:10]), 4),
            (r"(?i)(?:uncommon|infrequent|low\s+rate)\s+(?:of\s+)?" + re.escape(label[:10]), 2),
            (r"(?i)(?:rare|very\s+rare)\s+(?:of\s+)?" + re.escape(label[:10]), 1),
        ]

        for pattern, prob in freq_patterns:
            try:
                if re.search(pattern, safety_text):
                    return prob
            except re.error:
                continue

        return 2  # Default

    # ------------------------------------------------------------------
    # Risk matrix
    # ------------------------------------------------------------------

    def _build_risk_matrix(self, scored_risks: List[Dict]) -> Dict:
        """Build a risk matrix (probability vs severity).

        Args:
            scored_risks: List of scored risk dicts.

        Returns:
            Risk matrix dict with cells populated by risk IDs.
        """
        matrix = {}
        for sev in range(1, 6):
            for prob in range(1, 6):
                matrix[f"S{sev}_P{prob}"] = []

        for risk in scored_risks:
            sev = risk.get("severity", 3)
            prob = risk.get("probability", 2)
            key = f"S{sev}_P{prob}"
            matrix[key].append(risk.get("risk_id", ""))

        # Determine matrix zone (green/yellow/red)
        zones = {}
        for sev in range(1, 6):
            for prob in range(1, 6):
                key = f"S{sev}_P{prob}"
                product = sev * prob
                if product >= 15:
                    zones[key] = "red"
                elif product >= 6:
                    zones[key] = "yellow"
                else:
                    zones[key] = "green"

        return {
            "cells": matrix,
            "zones": zones,
            "severity_labels": {str(k): v["label"] for k, v in SEVERITY_SCALE.items()},
            "probability_labels": {str(k): v["label"] for k, v in PROBABILITY_SCALE.items()},
        }

    # ------------------------------------------------------------------
    # Mitigation extraction
    # ------------------------------------------------------------------

    def _extract_mitigations(
        self,
        safety_text: str,
        clinical_text: str,
    ) -> List[Dict]:
        """Extract risk mitigation strategies from text.

        Args:
            safety_text: Safety text from SSED.
            clinical_text: Clinical study text.

        Returns:
            List of mitigation strategy dicts.
        """
        mitigations = []
        combined = f"{safety_text or ''} {clinical_text or ''}".strip()

        if not combined:
            return mitigations

        # Pattern-based mitigation extraction
        mit_patterns = [
            (r"(?i)(?:mitigat(?:ed|ion)|reduc(?:ed|tion|ing))\s+(?:by|through|via|with)\s+([^.]{15,150})", "risk_reduction"),
            (r"(?i)(?:contraindication|contraindicated)\s+(?:in|for)\s+([^.]{15,100})", "contraindication"),
            (r"(?i)(?:warning|precaution)\s*:?\s*([^.]{15,150})", "warning_precaution"),
            (r"(?i)(?:training|instruction)\s+(?:required|recommended|necessary)\s+([^.]{10,100})", "training"),
            (r"(?i)(?:biocompatibility|biocompat)\s+testing\s+(?:per|according\s+to)\s+(ISO\s+10993[^.]*)", "biocompat_testing"),
            (r"(?i)(?:design\s+(?:control|verification|validation))\s+([^.]{10,100})", "design_control"),
        ]

        for pattern, mit_type in mit_patterns:
            for match in re.finditer(pattern, combined):
                mitigations.append({
                    "type": mit_type,
                    "description": match.group(1).strip()[:150] if match.lastindex else match.group().strip()[:150],
                    "source": "ssed_extraction",
                })

        return mitigations[:20]  # Limit

    # ------------------------------------------------------------------
    # Evidence requirement mapping
    # ------------------------------------------------------------------

    def _map_evidence_requirements(self, scored_risks: List[Dict]) -> List[Dict]:
        """Map high-priority risks to required evidence/testing.

        Args:
            scored_risks: List of scored risks.

        Returns:
            List of evidence requirement dicts.
        """
        requirements = []

        for risk in scored_risks:
            if risk.get("priority") not in ("HIGH", "MEDIUM"):
                continue

            risk_id = risk.get("risk_id", "")
            category = risk.get("category", "")

            # Map risk to evidence type
            evidence = []
            if risk_id in ("mechanical_failure",):
                evidence = [
                    "Mechanical fatigue testing (10 million cycles minimum)",
                    "Finite element analysis (FEA)",
                    "Accelerated aging study",
                ]
            elif risk_id in ("material_biocompat",):
                evidence = [
                    "ISO 10993 biocompatibility testing suite",
                    "Cytotoxicity, sensitization, irritation, genotoxicity",
                    "Implantation study (if applicable)",
                ]
            elif risk_id in ("electrical_safety",):
                evidence = [
                    "IEC 60601-1 electrical safety testing",
                    "EMC testing per IEC 60601-1-2",
                    "Battery performance testing (if applicable)",
                ]
            elif risk_id in ("software_malfunction",):
                evidence = [
                    "IEC 62304 software lifecycle documentation",
                    "Software verification and validation report",
                    "Cybersecurity risk assessment",
                ]
            elif risk_id in ("adverse_event_serious", "death"):
                evidence = [
                    "Clinical trial safety data with sufficient follow-up",
                    "Independent Clinical Events Committee (CEC) adjudication",
                    "Post-approval surveillance plan",
                ]
            elif risk_id in ("sterility_compromise", "sterilization_validation"):
                evidence = [
                    "Sterilization validation per ISO 11135/11137",
                    "Sterile barrier system testing per ISO 11607",
                    "Bioburden testing",
                ]
            elif category == "regulatory":
                evidence = [
                    "Comprehensive regulatory strategy document",
                    "Pre-Submission meeting with FDA",
                    "Gap analysis against FDA guidance",
                ]
            else:
                evidence = [
                    "Risk mitigation testing appropriate for the risk type",
                    "Documentation in Design History File",
                ]

            if evidence:
                requirements.append({
                    "risk_id": risk_id,
                    "risk_label": risk.get("label", ""),
                    "priority": risk.get("priority", ""),
                    "rpn": risk.get("rpn", 0),
                    "evidence_required": evidence,
                })

        return requirements

    # ------------------------------------------------------------------
    # Residual risk assessment
    # ------------------------------------------------------------------

    def _assess_residual_risk(
        self,
        scored_risks: List[Dict],
        mitigations: List[Dict],
    ) -> str:
        """Assess overall residual risk level.

        Args:
            scored_risks: Scored risks.
            mitigations: Identified mitigations.

        Returns:
            Residual risk level string.
        """
        if not scored_risks:
            return "UNKNOWN"

        high_count = len([r for r in scored_risks if r.get("priority") == "HIGH"])
        medium_count = len([r for r in scored_risks if r.get("priority") == "MEDIUM"])
        mit_count = len(mitigations)

        # If many high risks and few mitigations, residual risk is high
        if high_count >= 3 and mit_count < high_count:
            return "HIGH"
        elif high_count >= 1 or medium_count >= 3:
            return "MODERATE"
        else:
            return "LOW"

    # ------------------------------------------------------------------
    # Comparison helpers
    # ------------------------------------------------------------------

    def _calculate_risk_overlap(self, all_assessments: Dict) -> Dict:
        """Calculate risk overlap between PMAs."""
        pma_risks = {}
        for pma, assessment in all_assessments.items():
            pma_risks[pma] = set(
                r.get("risk_id", "") for r in assessment.get("identified_risks", [])
            )

        pma_list = list(pma_risks.keys())
        if len(pma_list) < 2:
            return {"overlap": "insufficient_data"}

        # All risks across all PMAs
        all_risk_ids = set()
        for risks in pma_risks.values():
            all_risk_ids.update(risks)

        # Common risks (in all PMAs)
        common = all_risk_ids.copy()
        for risks in pma_risks.values():
            common &= risks

        return {
            "total_unique_risks": len(all_risk_ids),
            "common_risks": sorted(common),
            "common_count": len(common),
            "overlap_percentage": round(len(common) / len(all_risk_ids) * 100, 1) if all_risk_ids else 0,
        }

    def _compare_severity_profiles(self, all_assessments: Dict) -> Dict:
        """Compare severity profiles across PMAs."""
        profiles = {}
        for pma, assessment in all_assessments.items():
            sevs = Counter()
            for risk in assessment.get("identified_risks", []):
                sevs[risk.get("severity", 0)] += 1
            profiles[pma] = dict(sevs)
        return profiles

    def _identify_risk_differences(self, all_assessments: Dict) -> List[Dict]:
        """Identify risks present in one PMA but not others."""
        differences = []
        pma_risks = {}
        for pma, assessment in all_assessments.items():
            pma_risks[pma] = set(
                r.get("risk_id", "") for r in assessment.get("identified_risks", [])
            )

        pma_list = list(pma_risks.keys())
        for i, pma1 in enumerate(pma_list):
            for pma2 in pma_list[i + 1:]:
                unique_to_1 = pma_risks[pma1] - pma_risks[pma2]
                unique_to_2 = pma_risks[pma2] - pma_risks[pma1]

                if unique_to_1:
                    differences.append({
                        "pma": pma1,
                        "vs": pma2,
                        "unique_risks": sorted(unique_to_1),
                        "description": f"Risks in {pma1} not found in {pma2}",
                    })
                if unique_to_2:
                    differences.append({
                        "pma": pma2,
                        "vs": pma1,
                        "unique_risks": sorted(unique_to_2),
                        "description": f"Risks in {pma2} not found in {pma1}",
                    })

        return differences

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _build_device_summary(self, api_data: Dict) -> Dict:
        """Build device summary."""
        return {
            "pma_number": api_data.get("pma_number", ""),
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "product_code": api_data.get("product_code", ""),
            "advisory_committee": api_data.get("advisory_committee", ""),
            "decision_date": api_data.get("decision_date", ""),
        }

    def _get_combined_safety_text(self, sections: Optional[Dict]) -> str:
        """Get combined safety text from sections."""
        if not sections:
            return ""
        section_dict = sections.get("sections", sections)
        texts = []
        for key in ["potential_risks", "benefit_risk", "preclinical_studies"]:
            sec = section_dict.get(key, {})
            if isinstance(sec, dict):
                content = sec.get("content", "")
                if content:
                    texts.append(content)
            elif isinstance(sec, str) and sec:
                texts.append(sec)
        return " ".join(texts)

    def _get_clinical_text(self, sections: Optional[Dict]) -> str:
        """Get clinical text from sections."""
        if not sections:
            return ""
        section_dict = sections.get("sections", sections)
        sec = section_dict.get("clinical_studies", {})
        if isinstance(sec, dict):
            return sec.get("content", "")
        elif isinstance(sec, str):
            return sec
        return ""

    def _summarize_by_category(self, scored_risks: List[Dict]) -> Dict:
        """Summarize risks by category."""
        categories = Counter()
        for risk in scored_risks:
            categories[risk.get("category", "unknown")] += 1
        return dict(categories)

    def _summarize_landscape_categories(self, landscape_risks: List[Dict]) -> Dict:
        """Summarize risk landscape by category."""
        categories = Counter()
        for risk in landscape_risks:
            categories[risk.get("category", "unknown")] += risk.get("frequency_across_pmas", 1)
        return dict(categories.most_common())

    def _calculate_confidence(self, safety_text: str, scored_risks: List[Dict]) -> float:
        """Calculate assessment confidence."""
        if not safety_text:
            return 0.2
        word_count = len(safety_text.split())
        text_score = min(word_count / 2000, 1.0) * 0.5
        risk_score = min(len(scored_risks) / 10, 1.0) * 0.5
        return round(text_score + risk_score, 2)


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_assessment(assessment: Dict) -> str:
    """Format risk assessment as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("PMA RISK ASSESSMENT REPORT")
    lines.append("=" * 70)

    device = assessment.get("device_summary", {})
    lines.append(f"PMA: {device.get('pma_number', 'N/A')}")
    lines.append(f"Device: {device.get('device_name', 'N/A')}")
    lines.append(f"Panel: {device.get('advisory_committee', 'N/A')}")
    lines.append(f"Confidence: {assessment.get('confidence', 0):.0%}")
    lines.append("")

    # Summary
    summary = assessment.get("risk_summary", {})
    lines.append("--- Risk Summary ---")
    lines.append(f"  Total Risks: {summary.get('total_risks_identified', 0)}")
    lines.append(f"  HIGH: {summary.get('high_priority', 0)}  MEDIUM: {summary.get('medium_priority', 0)}  LOW: {summary.get('low_priority', 0)}")
    lines.append(f"  Residual Risk: {summary.get('residual_risk_level', 'N/A')}")
    cats = summary.get("categories", {})
    lines.append(f"  Categories: {', '.join(f'{k}={v}' for k, v in cats.items())}")
    lines.append("")

    # Top risks
    risks = assessment.get("identified_risks", [])
    if risks:
        lines.append("--- Top Risks (by RPN) ---")
        lines.append(f"  {'Risk':<30s} {'S':>3s} {'P':>3s} {'D':>3s} {'RPN':>5s} Priority")
        lines.append(f"  {'-'*30} {'---':>3s} {'---':>3s} {'---':>3s} {'-----':>5s} --------")
        for r in risks[:15]:
            lines.append(
                f"  {r.get('label', 'N/A'):<30s} "
                f"{r.get('severity', 0):3d} "
                f"{r.get('probability', 0):3d} "
                f"{r.get('detectability', 0):3d} "
                f"{r.get('rpn', 0):5d} "
                f"{r.get('priority', 'N/A')}"
            )
        lines.append("")

    # Mitigations
    mitigations = assessment.get("mitigation_strategies", [])
    if mitigations:
        lines.append("--- Mitigation Strategies ---")
        for m in mitigations[:10]:
            lines.append(f"  [{m.get('type', 'N/A')}] {m.get('description', 'N/A')[:80]}")
        lines.append("")

    # Evidence requirements
    evidence = assessment.get("evidence_requirements", [])
    if evidence:
        lines.append("--- Evidence Requirements (HIGH/MEDIUM priority) ---")
        for e in evidence[:10]:
            lines.append(f"  {e.get('risk_label', 'N/A')} [{e.get('priority', 'N/A')}]:")
            for req in e.get("evidence_required", []):
                lines.append(f"    - {req}")
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {assessment.get('generated_at', 'N/A')[:10]}")
    lines.append("This assessment is AI-generated from PMA SSED data.")
    lines.append("Independent risk analysis by qualified professionals is required.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA Risk Assessment -- Systematic risk analysis for PMA devices"
    )
    parser.add_argument("--pma", help="PMA number to assess")
    parser.add_argument("--compare", help="Comma-separated comparator PMAs")
    parser.add_argument("--product-code", dest="product_code",
                        help="Risk landscape for product code")
    parser.add_argument("--refresh", action="store_true", help="Force API refresh")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    engine = RiskAssessmentEngine()

    result = None

    if args.pma and args.compare:
        comparators = [c.strip().upper() for c in args.compare.split(",") if c.strip()]
        result = engine.compare_risk_profiles(args.pma, comparators, refresh=args.refresh)
    elif args.pma:
        result = engine.assess_risks(args.pma, refresh=args.refresh)
    elif args.product_code:
        result = engine.analyze_risk_landscape(args.product_code)
    else:
        parser.error("Specify --pma or --product-code")
        return

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    elif "identified_risks" in result:
        print(_format_assessment(result))
    else:
        print(json.dumps(result, indent=2, default=str))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
