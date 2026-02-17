#!/usr/bin/env python3
"""
Clinical Requirements Mapper -- Identify clinical trial requirements from PMA precedent.

Analyzes PMA SSED clinical sections to extract trial design patterns, enrollment
targets, endpoints, follow-up durations, and data requirements. Maps device
characteristics to clinical trial requirements and generates requirement
comparison tables across comparable PMAs.

Integrates with PMA Intelligence (pma_intelligence.py) for clinical data
extraction and PMA Comparison (pma_comparison.py) for identifying comparable
devices.

Usage:
    from clinical_requirements_mapper import ClinicalRequirementsMapper

    mapper = ClinicalRequirementsMapper()
    reqs = mapper.map_requirements("P170019")
    comparison = mapper.compare_requirements("P170019", ["P160035", "P150009"])
    timeline = mapper.estimate_trial_timeline("P170019")

    # CLI usage:
    python3 clinical_requirements_mapper.py --pma P170019
    python3 clinical_requirements_mapper.py --pma P170019 --compare P160035,P150009
    python3 clinical_requirements_mapper.py --product-code NMH --all-requirements
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
# Study design classification hierarchy
# ------------------------------------------------------------------

STUDY_DESIGN_HIERARCHY = {
    "pivotal_rct": {
        "label": "Pivotal Randomized Controlled Trial",
        "tier": 1,
        "complexity": "high",
        "typical_cost_per_patient": 35000,
        "typical_enrollment_range": (200, 2000),
        "regulatory_weight": "gold_standard",
    },
    "pivotal_single_arm": {
        "label": "Pivotal Single-Arm Study",
        "tier": 2,
        "complexity": "moderate",
        "typical_cost_per_patient": 25000,
        "typical_enrollment_range": (100, 500),
        "regulatory_weight": "accepted_with_justification",
    },
    "rct": {
        "label": "Randomized Controlled Trial",
        "tier": 1,
        "complexity": "high",
        "typical_cost_per_patient": 30000,
        "typical_enrollment_range": (150, 1500),
        "regulatory_weight": "gold_standard",
    },
    "non_inferiority": {
        "label": "Non-Inferiority Trial",
        "tier": 1,
        "complexity": "high",
        "typical_cost_per_patient": 32000,
        "typical_enrollment_range": (200, 2000),
        "regulatory_weight": "gold_standard",
    },
    "sham_controlled": {
        "label": "Sham-Controlled Trial",
        "tier": 1,
        "complexity": "very_high",
        "typical_cost_per_patient": 40000,
        "typical_enrollment_range": (100, 500),
        "regulatory_weight": "gold_standard",
    },
    "bayesian": {
        "label": "Bayesian Adaptive Design",
        "tier": 2,
        "complexity": "high",
        "typical_cost_per_patient": 30000,
        "typical_enrollment_range": (100, 800),
        "regulatory_weight": "accepted_with_justification",
    },
    "single_arm": {
        "label": "Single-Arm Study",
        "tier": 3,
        "complexity": "moderate",
        "typical_cost_per_patient": 20000,
        "typical_enrollment_range": (50, 300),
        "regulatory_weight": "supplementary",
    },
    "registry": {
        "label": "Registry Study",
        "tier": 3,
        "complexity": "low",
        "typical_cost_per_patient": 8000,
        "typical_enrollment_range": (500, 10000),
        "regulatory_weight": "supplementary",
    },
    "prospective_cohort": {
        "label": "Prospective Cohort Study",
        "tier": 3,
        "complexity": "moderate",
        "typical_cost_per_patient": 15000,
        "typical_enrollment_range": (100, 1000),
        "regulatory_weight": "supplementary",
    },
    "retrospective": {
        "label": "Retrospective Study",
        "tier": 4,
        "complexity": "low",
        "typical_cost_per_patient": 5000,
        "typical_enrollment_range": (100, 5000),
        "regulatory_weight": "supporting_only",
    },
    "feasibility": {
        "label": "Feasibility/Pilot Study",
        "tier": 4,
        "complexity": "moderate",
        "typical_cost_per_patient": 30000,
        "typical_enrollment_range": (10, 50),
        "regulatory_weight": "supporting_only",
    },
}

# ------------------------------------------------------------------
# Blinding patterns
# ------------------------------------------------------------------

BLINDING_PATTERNS = {
    "double_blind": {
        "label": "Double-Blind",
        "patterns": [
            r"(?i)double[- ]?blind",
            r"(?i)double[- ]?masked",
        ],
    },
    "single_blind": {
        "label": "Single-Blind",
        "patterns": [
            r"(?i)single[- ]?blind",
            r"(?i)(?:patient|subject|investigator)[- ]?blind",
        ],
    },
    "open_label": {
        "label": "Open-Label",
        "patterns": [
            r"(?i)open[- ]?label",
            r"(?i)un[- ]?blinded",
            r"(?i)non[- ]?blinded",
        ],
    },
}

# Compiled blinding patterns
_COMPILED_BLINDING = {}
for key, info in BLINDING_PATTERNS.items():
    _COMPILED_BLINDING[key] = [re.compile(p) for p in info["patterns"]]

# ------------------------------------------------------------------
# Control arm patterns
# ------------------------------------------------------------------

CONTROL_ARM_PATTERNS = {
    "sham": {
        "label": "Sham Control",
        "patterns": [r"(?i)sham[- ]?control", r"(?i)sham\s+procedure"],
    },
    "standard_of_care": {
        "label": "Standard of Care",
        "patterns": [
            r"(?i)standard\s+of\s+care",
            r"(?i)standard\s+(?:medical\s+)?therapy",
            r"(?i)(?:current|best)\s+(?:available\s+)?(?:treatment|therapy)",
        ],
    },
    "active_comparator": {
        "label": "Active Comparator",
        "patterns": [
            r"(?i)active\s+(?:control|comparator)",
            r"(?i)(?:predicate|comparator)\s+device",
        ],
    },
    "historical": {
        "label": "Historical Control",
        "patterns": [
            r"(?i)historical\s+control",
            r"(?i)(?:literature|published)\s+(?:control|comparator|data)",
            r"(?i)objective\s+performance\s+criter(?:ion|ia)",
            r"(?i)\bOPC\b",
        ],
    },
    "no_control": {
        "label": "No Control (Single-Arm)",
        "patterns": [
            r"(?i)single[- ]?arm",
            r"(?i)(?:no|without)\s+control",
        ],
    },
}

_COMPILED_CONTROLS = {}
for key, info in CONTROL_ARM_PATTERNS.items():
    _COMPILED_CONTROLS[key] = [re.compile(p) for p in info["patterns"]]

# ------------------------------------------------------------------
# Follow-up duration standards by device category
# ------------------------------------------------------------------

FOLLOW_UP_STANDARDS = {
    "cardiovascular_implant": {"min_months": 12, "typical_months": 24, "max_months": 60},
    "orthopedic_implant": {"min_months": 24, "typical_months": 60, "max_months": 120},
    "neurological_implant": {"min_months": 12, "typical_months": 24, "max_months": 60},
    "ophthalmic": {"min_months": 6, "typical_months": 12, "max_months": 36},
    "general_surgical": {"min_months": 3, "typical_months": 12, "max_months": 24},
    "diagnostic": {"min_months": 0, "typical_months": 0, "max_months": 6},
    "default": {"min_months": 6, "typical_months": 12, "max_months": 36},
}

# Advisory committee to device category mapping
PANEL_TO_CATEGORY = {
    "CV": "cardiovascular_implant",
    "OR": "orthopedic_implant",
    "NE": "neurological_implant",
    "OP": "ophthalmic",
    "SU": "general_surgical",
    "RA": "diagnostic",
    "CH": "diagnostic",
    "HE": "diagnostic",
    "MI": "diagnostic",
    "IM": "diagnostic",
}

# ------------------------------------------------------------------
# Endpoint category patterns
# ------------------------------------------------------------------

ENDPOINT_CATEGORIES = {
    "survival": {
        "label": "Survival/Mortality",
        "patterns": [
            r"(?i)(?:overall|disease[- ]?free|event[- ]?free)\s+survival",
            r"(?i)mortality\s+(?:rate|at|through)",
            r"(?i)all[- ]?cause\s+(?:death|mortality)",
        ],
    },
    "device_success": {
        "label": "Device/Technical Success",
        "patterns": [
            r"(?i)(?:device|technical|procedural)\s+success",
            r"(?i)(?:primary|acute)\s+(?:device\s+)?success\s+rate",
        ],
    },
    "clinical_efficacy": {
        "label": "Clinical Efficacy Rate",
        "patterns": [
            r"(?i)(?:clinical\s+)?efficacy\s+rate",
            r"(?i)(?:clinical\s+)?response\s+rate",
            r"(?i)freedom\s+from\s+(?:target|device)",
        ],
    },
    "safety_composite": {
        "label": "Safety Composite / MACE",
        "patterns": [
            r"(?i)(?:major\s+)?adverse\s+(?:cardiac\s+)?events?",
            r"(?i)\bMACE\b",
            r"(?i)composite\s+(?:safety\s+)?(?:endpoint|end\s*point)",
        ],
    },
    "functional_outcome": {
        "label": "Functional Outcome",
        "patterns": [
            r"(?i)functional\s+(?:outcome|score|improvement|recovery)",
            r"(?i)quality\s+of\s+life|QoL|SF-?36|EQ-?5D",
            r"(?i)pain\s+(?:score|VAS|NRS|reduction|improvement)",
        ],
    },
    "performance_diagnostic": {
        "label": "Diagnostic Performance",
        "patterns": [
            r"(?i)sensitivity\s+(?:and|or)\s+specificity",
            r"(?i)(?:area\s+under\s+(?:the\s+)?curve|AUC|ROC)",
            r"(?i)(?:positive|negative)\s+(?:predictive\s+value|percent\s+agreement)",
        ],
    },
    "anatomical_outcome": {
        "label": "Anatomical/Imaging Outcome",
        "patterns": [
            r"(?i)(?:angiographic|radiographic|imaging)\s+(?:outcome|success|endpoint)",
            r"(?i)(?:lumen|vessel|target\s+lesion)\s+(?:loss|diameter|patency)",
        ],
    },
}

_COMPILED_ENDPOINTS = {}
for key, info in ENDPOINT_CATEGORIES.items():
    _COMPILED_ENDPOINTS[key] = [re.compile(p) for p in info["patterns"]]


# ------------------------------------------------------------------
# Clinical Requirements Mapper
# ------------------------------------------------------------------

class ClinicalRequirementsMapper:
    """Map clinical trial requirements from PMA precedent and FDA guidance.

    Analyzes SSED clinical sections from comparable PMAs to identify
    trial design patterns, enrollment targets, endpoint requirements,
    follow-up durations, and data requirements. Generates structured
    requirement matrices and cost/timeline estimates.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Clinical Requirements Mapper.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()
        self.intelligence = PMAIntelligenceEngine(store=self.store)

    # ------------------------------------------------------------------
    # Main requirement mapping
    # ------------------------------------------------------------------

    def map_requirements(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict:
        """Map clinical trial requirements from a PMA's SSED data.

        Extracts study design requirements, enrollment targets, endpoint
        requirements, follow-up durations, and data requirements from
        the clinical sections of the PMA's SSED.

        Args:
            pma_number: PMA number to analyze (e.g., 'P170019').
            refresh: Force refresh of underlying data.

        Returns:
            Clinical requirements dictionary with all requirement categories.
        """
        pma_key = pma_number.upper()

        # Get clinical intelligence from the PMA
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        sections = self.store.get_extracted_sections(pma_key)

        if api_data.get("error") and not sections:
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
                "requirements_available": False,
            }

        # Extract clinical intelligence
        clinical_intel = self.intelligence.extract_clinical_intelligence(
            pma_key, api_data, sections
        )

        # Get clinical text for detailed extraction
        clinical_text = self._get_combined_clinical_text(sections)

        # Build requirement map
        requirements = {
            "pma_number": pma_key,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "requirements_available": True,
            "device_summary": self._build_device_summary(api_data),
            "study_design_requirements": self._extract_study_design_requirements(
                clinical_intel, clinical_text
            ),
            "enrollment_requirements": self._extract_enrollment_requirements(
                clinical_intel, clinical_text, api_data
            ),
            "endpoint_requirements": self._extract_endpoint_requirements(
                clinical_intel, clinical_text
            ),
            "follow_up_requirements": self._extract_follow_up_requirements(
                clinical_intel, clinical_text, api_data
            ),
            "data_requirements": self._extract_data_requirements(
                clinical_intel, clinical_text
            ),
            "statistical_requirements": self._extract_statistical_requirements(
                clinical_text
            ),
        }

        # Generate cost and timeline estimates
        requirements["cost_estimate"] = self._estimate_trial_costs(requirements)
        requirements["timeline_estimate"] = self._estimate_trial_timeline(requirements)
        requirements["confidence"] = self._calculate_requirements_confidence(requirements)

        return requirements

    # ------------------------------------------------------------------
    # Multi-PMA comparison
    # ------------------------------------------------------------------

    def compare_requirements(
        self,
        primary_pma: str,
        comparator_pmas: List[str],
        refresh: bool = False,
    ) -> Dict:
        """Compare clinical requirements across multiple PMAs.

        Args:
            primary_pma: Primary PMA number.
            comparator_pmas: List of comparator PMA numbers.
            refresh: Force refresh.

        Returns:
            Requirements comparison matrix.
        """
        primary_key = primary_pma.upper()
        comp_keys = [c.upper() for c in comparator_pmas]

        # Map requirements for all PMAs
        all_requirements = {}
        all_requirements[primary_key] = self.map_requirements(primary_key, refresh=refresh)

        for comp in comp_keys:
            all_requirements[comp] = self.map_requirements(comp, refresh=refresh)

        # Build comparison matrix
        comparison = {
            "primary_pma": primary_key,
            "comparator_pmas": comp_keys,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "requirements": all_requirements,
            "comparison_matrix": self._build_comparison_matrix(all_requirements),
            "consensus_requirements": self._derive_consensus(all_requirements),
            "notable_differences": self._identify_differences(all_requirements),
        }

        return comparison

    # ------------------------------------------------------------------
    # Product code-level analysis
    # ------------------------------------------------------------------

    def analyze_product_code_requirements(
        self,
        product_code: str,
        limit: int = 10,
    ) -> Dict:
        """Analyze clinical requirements patterns for an entire product code.

        Args:
            product_code: FDA product code (e.g., 'NMH').
            limit: Maximum PMAs to analyze.

        Returns:
            Product code requirement analysis.
        """
        # Search for PMAs with this product code
        result = self.store.client.search_pma(
            product_code=product_code, limit=limit, sort="decision_date:desc"
        )

        if result.get("degraded") or not result.get("results"):
            return {
                "product_code": product_code,
                "error": "No PMAs found for this product code",
            }

        # Extract unique base PMAs
        pma_numbers = []
        seen = set()
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            base = re.sub(r"S\d+$", "", pn)
            if base and base not in seen:
                seen.add(base)
                pma_numbers.append(base)

        pma_numbers = pma_numbers[:limit]

        # Map requirements for each PMA
        all_reqs = {}
        for pma in pma_numbers:
            reqs = self.map_requirements(pma)
            if reqs.get("requirements_available"):
                all_reqs[pma] = reqs

        if not all_reqs:
            return {
                "product_code": product_code,
                "pma_count": len(pma_numbers),
                "error": "No clinical requirements data available for analyzed PMAs",
            }

        return {
            "product_code": product_code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pmas_analyzed": len(all_reqs),
            "pma_numbers": list(all_reqs.keys()),
            "consensus_requirements": self._derive_consensus(all_reqs),
            "design_patterns": self._summarize_design_patterns(all_reqs),
            "enrollment_statistics": self._summarize_enrollment(all_reqs),
            "endpoint_patterns": self._summarize_endpoints(all_reqs),
            "follow_up_patterns": self._summarize_follow_up(all_reqs),
            "cost_range": self._summarize_costs(all_reqs),
        }

    # ------------------------------------------------------------------
    # Study design requirement extraction
    # ------------------------------------------------------------------

    def _extract_study_design_requirements(
        self,
        clinical_intel: Dict,
        clinical_text: str,
    ) -> Dict:
        """Extract study design requirements from clinical intelligence.

        Args:
            clinical_intel: Clinical intelligence dict from PMAIntelligenceEngine.
            clinical_text: Combined clinical study text.

        Returns:
            Study design requirements dict.
        """
        designs = clinical_intel.get("study_designs", [])
        if not designs and not clinical_text:
            return {
                "trial_type": "unknown",
                "blinding": "unknown",
                "control_arm": "unknown",
                "randomization_required": None,
                "multicenter_required": None,
                "confidence": 0.0,
            }

        # Determine primary trial type
        primary_type = "unknown"
        primary_label = "Unknown"
        for d in designs:
            dtype = d.get("type", "")
            if dtype in STUDY_DESIGN_HIERARCHY:
                info = STUDY_DESIGN_HIERARCHY[dtype]
                if primary_type == "unknown" or info["tier"] < STUDY_DESIGN_HIERARCHY.get(
                    primary_type, {"tier": 99}
                ).get("tier", 99):
                    primary_type = dtype
                    primary_label = info["label"]

        # Detect blinding
        blinding = self._detect_blinding(clinical_text)

        # Detect control arm type
        control_arm = self._detect_control_arm(clinical_text)

        # Detect randomization
        randomization_required = any(
            d.get("type", "") in ("pivotal_rct", "rct", "non_inferiority", "sham_controlled")
            for d in designs
        )

        # Detect multicenter
        multicenter = bool(re.search(r"(?i)multi[- ]?(?:center|site)", clinical_text or ""))

        # Adaptive design
        adaptive = bool(re.search(
            r"(?i)(?:adaptive|bayesian)\s+(?:design|trial|analysis)", clinical_text or ""
        ))

        return {
            "trial_type": primary_type,
            "trial_type_label": primary_label,
            "all_designs_detected": [d.get("type") for d in designs],
            "blinding": blinding,
            "control_arm": control_arm,
            "randomization_required": randomization_required,
            "multicenter_required": multicenter,
            "adaptive_design": adaptive,
            "complexity": STUDY_DESIGN_HIERARCHY.get(
                primary_type, {}
            ).get("complexity", "unknown"),
            "regulatory_weight": STUDY_DESIGN_HIERARCHY.get(
                primary_type, {}
            ).get("regulatory_weight", "unknown"),
            "confidence": max((d.get("confidence", 0) for d in designs), default=0.0),
        }

    def _detect_blinding(self, text: str) -> str:
        """Detect blinding type from clinical text.

        Args:
            text: Clinical study text.

        Returns:
            Blinding type string.
        """
        if not text:
            return "unknown"

        for key, patterns in _COMPILED_BLINDING.items():
            for pattern in patterns:
                if pattern.search(text):
                    return key

        return "unknown"

    def _detect_control_arm(self, text: str) -> str:
        """Detect control arm type from clinical text.

        Args:
            text: Clinical study text.

        Returns:
            Control arm type string.
        """
        if not text:
            return "unknown"

        for key, patterns in _COMPILED_CONTROLS.items():
            for pattern in patterns:
                if pattern.search(text):
                    return key

        return "unknown"

    # ------------------------------------------------------------------
    # Enrollment requirement extraction
    # ------------------------------------------------------------------

    def _extract_enrollment_requirements(
        self,
        clinical_intel: Dict,
        clinical_text: str,
        api_data: Dict,
    ) -> Dict:
        """Extract enrollment requirements.

        Args:
            clinical_intel: Clinical intelligence dict.
            clinical_text: Combined clinical text.
            api_data: PMA API data.

        Returns:
            Enrollment requirements dict.
        """
        enrollment = clinical_intel.get("enrollment", {})
        total = enrollment.get("total_enrollment")
        sites = enrollment.get("number_of_sites")

        # Extract inclusion/exclusion criteria patterns
        inclusion_patterns = self._extract_criteria_patterns(clinical_text, "inclusion")
        exclusion_patterns = self._extract_criteria_patterns(clinical_text, "exclusion")

        # Determine geographic scope
        geographic = "unknown"
        if clinical_text:
            if re.search(r"(?i)(?:US[- ]?only|United\s+States\s+only)", clinical_text):
                geographic = "us_only"
            elif re.search(r"(?i)(?:multi[- ]?national|international|OUS|European|global)", clinical_text):
                geographic = "multinational"
            elif sites and sites > 1:
                geographic = "multicenter_us"

        # Stratification patterns
        stratification = []
        strat_patterns = [
            (r"(?i)stratif(?:ied|ication)\s+by\s+([^.;]{10,80})", "general"),
            (r"(?i)subgroup\s+analysis\s+(?:by|for)\s+([^.;]{10,80})", "subgroup"),
        ]
        for pattern, stype in strat_patterns:
            match = re.search(pattern, clinical_text or "")
            if match:
                stratification.append({
                    "type": stype,
                    "description": match.group(1).strip()[:80],
                })

        return {
            "minimum_sample_size": total,
            "recommended_sample_size": self._calculate_recommended_enrollment(total),
            "number_of_sites": sites,
            "geographic_scope": geographic,
            "inclusion_criteria_patterns": inclusion_patterns,
            "exclusion_criteria_patterns": exclusion_patterns,
            "stratification": stratification,
            "demographics_required": enrollment.get("demographics_mentioned", False),
            "confidence": enrollment.get("confidence", 0.0),
        }

    def _extract_criteria_patterns(self, text: str, criteria_type: str) -> List[str]:
        """Extract inclusion/exclusion criteria patterns from text.

        Args:
            text: Clinical study text.
            criteria_type: 'inclusion' or 'exclusion'.

        Returns:
            List of criteria pattern strings.
        """
        if not text:
            return []

        patterns = [
            rf"(?i){criteria_type}\s+criteria\s*:?\s*([^.]*(?:\.\s+[^.]*)*?)(?:\n\n|\Z)",
            rf"(?i)key\s+{criteria_type}\s+criteria\s*(?:included?|were?)?\s*:?\s*([^.]*)",
        ]

        criteria = []
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                text_block = match.group(1).strip()
                # Split on bullet points, semicolons, or numbered items
                items = re.split(r"[;\n]+|\d+\.", text_block)
                for item in items:
                    item = item.strip()
                    if len(item) > 10 and len(item) < 200:
                        criteria.append(item)

        return criteria[:10]  # Limit to 10

    def _calculate_recommended_enrollment(self, observed: Optional[int]) -> Optional[int]:
        """Calculate recommended enrollment based on observed plus margin.

        Args:
            observed: Observed enrollment from PMA.

        Returns:
            Recommended enrollment (20% above observed).
        """
        if observed is None:
            return None
        # Add 20% safety margin for dropouts and screen failures
        return int(observed * 1.2)

    # ------------------------------------------------------------------
    # Endpoint requirement extraction
    # ------------------------------------------------------------------

    def _extract_endpoint_requirements(
        self,
        clinical_intel: Dict,
        clinical_text: str,
    ) -> Dict:
        """Extract endpoint requirements.

        Args:
            clinical_intel: Clinical intelligence dict.
            clinical_text: Combined clinical text.

        Returns:
            Endpoint requirements dict.
        """
        endpoints = clinical_intel.get("endpoints", {})

        # Categorize extracted endpoints
        primary_categories = self._categorize_endpoints(
            endpoints.get("primary", []), clinical_text
        )
        secondary_categories = self._categorize_endpoints(
            endpoints.get("secondary", []), clinical_text
        )

        # Extract success criteria thresholds
        success_criteria = self._extract_success_criteria(clinical_text)

        # Determine if objective vs composite primary endpoint
        endpoint_type = "unknown"
        if primary_categories:
            if len(primary_categories) > 1:
                endpoint_type = "composite"
            elif primary_categories[0].get("category") in ("device_success", "clinical_efficacy"):
                endpoint_type = "objective"
            else:
                endpoint_type = "clinical"

        return {
            "primary_endpoints": endpoints.get("primary", []),
            "primary_endpoint_categories": primary_categories,
            "secondary_endpoints": endpoints.get("secondary", []),
            "secondary_endpoint_categories": secondary_categories,
            "safety_endpoints": endpoints.get("safety", []),
            "endpoint_type": endpoint_type,
            "success_criteria": success_criteria,
            "timepoints": self._extract_timepoints(clinical_text),
            "confidence": endpoints.get("confidence", 0.0),
        }

    def _categorize_endpoints(
        self,
        endpoints: List[Dict],
        clinical_text: str,
    ) -> List[Dict]:
        """Categorize extracted endpoints into standard categories.

        Args:
            endpoints: List of extracted endpoint dicts.
            clinical_text: Full clinical text for context.

        Returns:
            List of categorized endpoint dicts.
        """
        categorized = []
        for ep in endpoints:
            ep_text = ep.get("text", "")
            category = "other"
            category_label = "Other"

            for cat_key, cat_patterns in _COMPILED_ENDPOINTS.items():
                for pattern in cat_patterns:
                    if pattern.search(ep_text) or pattern.search(clinical_text or ""):
                        category = cat_key
                        category_label = ENDPOINT_CATEGORIES[cat_key]["label"]
                        break
                if category != "other":
                    break

            categorized.append({
                "text": ep_text,
                "category": category,
                "category_label": category_label,
                "confidence": ep.get("confidence", 0.5),
            })

        return categorized

    def _extract_success_criteria(self, text: str) -> List[Dict]:
        """Extract success/performance criteria from text.

        Args:
            text: Clinical study text.

        Returns:
            List of success criteria dicts.
        """
        if not text:
            return []

        criteria = []
        patterns = [
            (r"(?i)(?:success|performance)\s+(?:criterion|criteria|goal|target)\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%", "success_threshold"),
            (r"(?i)non[- ]?inferiority\s+margin\s*(?:of|was|:)?\s*(\d+\.?\d*)\s*%", "ni_margin"),
            (r"(?i)(?:powered|power)\s+(?:at|to\s+detect)\s*(\d+\.?\d*)\s*%", "statistical_power"),
            (r"(?i)alpha\s*(?:=|of|was)?\s*(0?\.\d+)", "alpha_level"),
        ]

        for pattern, crit_type in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    criteria.append({
                        "type": crit_type,
                        "value": value,
                        "matched_text": match.group().strip()[:100],
                    })
                except ValueError:
                    continue

        return criteria

    def _extract_timepoints(self, text: str) -> List[Dict]:
        """Extract assessment timepoints from clinical text.

        Args:
            text: Clinical study text.

        Returns:
            List of timepoint dicts.
        """
        if not text:
            return []

        timepoints = []
        patterns = [
            r"(?i)(?:at|through)\s+(\d+)\s*(day|week|month|year)s?(?:\s+(?:follow[- ]?up|assessment|visit))?",
            r"(?i)(\d+)[- ](day|week|month|year)\s+(?:follow[- ]?up|assessment|time\s*point|visit)",
        ]

        seen = set()
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                try:
                    value = int(match.group(1))
                    unit = match.group(2).lower().rstrip("s")
                    key = f"{value}_{unit}"
                    if key not in seen:
                        seen.add(key)
                        timepoints.append({
                            "value": value,
                            "unit": unit,
                            "months": self._to_months(value, unit),
                        })
                except (ValueError, IndexError):
                    continue

        timepoints.sort(key=lambda t: t.get("months", 0))
        return timepoints

    @staticmethod
    def _to_months(value: int, unit: str) -> float:
        """Convert a duration to months."""
        if unit == "day":
            return value / 30.0
        elif unit == "week":
            return value / 4.3
        elif unit == "month":
            return float(value)
        elif unit == "year":
            return value * 12.0
        return float(value)

    # ------------------------------------------------------------------
    # Follow-up requirement extraction
    # ------------------------------------------------------------------

    def _extract_follow_up_requirements(
        self,
        clinical_intel: Dict,
        clinical_text: str,
        api_data: Dict,
    ) -> Dict:
        """Extract follow-up duration requirements.

        Args:
            clinical_intel: Clinical intelligence dict.
            clinical_text: Combined clinical text.
            api_data: PMA API data.

        Returns:
            Follow-up requirements dict.
        """
        follow_up = clinical_intel.get("follow_up", {})

        # Get device category for standard follow-up
        panel = api_data.get("advisory_committee", "")
        category = PANEL_TO_CATEGORY.get(panel, "default")
        standards = FOLLOW_UP_STANDARDS.get(category, FOLLOW_UP_STANDARDS["default"])

        # Observed follow-up from clinical data
        observed_duration = follow_up.get("duration")
        observed_unit = follow_up.get("unit", "month")
        observed_months = None
        if observed_duration is not None:
            observed_months = self._to_months(int(observed_duration), observed_unit)

        # Post-approval study requirement detection
        post_approval = bool(
            re.search(
                r"(?i)(?:post[- ]?approval\s+study|condition\s+of\s+approval|PAS\b)",
                clinical_text or "",
            )
        )

        return {
            "observed_follow_up": {
                "duration": observed_duration,
                "unit": observed_unit,
                "months": observed_months,
            },
            "standard_follow_up": standards,
            "device_category": category,
            "post_approval_study_required": post_approval,
            "recommended_follow_up_months": max(
                observed_months or 0,
                standards["typical_months"],
            ),
            "confidence": follow_up.get("confidence", 0.0),
        }

    # ------------------------------------------------------------------
    # Data requirement extraction
    # ------------------------------------------------------------------

    def _extract_data_requirements(
        self,
        clinical_intel: Dict,
        clinical_text: str,
    ) -> Dict:
        """Extract data and monitoring requirements.

        Args:
            clinical_intel: Clinical intelligence dict.
            clinical_text: Combined clinical text.

        Returns:
            Data requirements dict.
        """
        requirements = {
            "interim_analysis": False,
            "independent_review": False,
            "dsmb_required": False,
            "core_lab": False,
            "cec_required": False,
            "adverse_event_standards": [],
            "device_tracking_required": False,
        }

        if not clinical_text:
            return requirements

        # Interim analysis
        if re.search(r"(?i)interim\s+analysis", clinical_text):
            requirements["interim_analysis"] = True

        # Independent review (CEC, DSMB, Core Lab)
        if re.search(r"(?i)(?:independent|central)\s+(?:review|adjudication|committee)", clinical_text):
            requirements["independent_review"] = True

        if re.search(r"(?i)(?:DSMB|data\s+(?:and\s+)?safety\s+monitoring\s+board)", clinical_text):
            requirements["dsmb_required"] = True

        if re.search(r"(?i)(?:core\s+lab|central\s+laboratory)", clinical_text):
            requirements["core_lab"] = True

        if re.search(r"(?i)(?:CEC|clinical\s+(?:events?\s+)?committee)", clinical_text):
            requirements["cec_required"] = True

        # AE reporting standards
        ae_standards = []
        if re.search(r"(?i)MedDRA", clinical_text):
            ae_standards.append("MedDRA coding")
        if re.search(r"(?i)CTCAE|common\s+terminology\s+criteria", clinical_text):
            ae_standards.append("CTCAE grading")
        if re.search(r"(?i)ISO\s+14155", clinical_text):
            ae_standards.append("ISO 14155 compliance")
        requirements["adverse_event_standards"] = ae_standards

        # Device tracking
        if re.search(r"(?i)(?:device\s+(?:tracking|traceability|accountability)|UDI)", clinical_text):
            requirements["device_tracking_required"] = True

        return requirements

    # ------------------------------------------------------------------
    # Statistical requirement extraction
    # ------------------------------------------------------------------

    def _extract_statistical_requirements(self, clinical_text: str) -> Dict:
        """Extract statistical analysis requirements.

        Args:
            clinical_text: Combined clinical text.

        Returns:
            Statistical requirements dict.
        """
        requirements: Dict = {
            "analysis_populations": [],
            "statistical_methods": [],
            "power_calculation": None,
            "alpha_level": None,
            "multiple_comparison_adjustment": False,
        }

        if not clinical_text:
            return requirements

        # Analysis populations
        population_patterns = [
            (r"(?i)intent[- ]?to[- ]?treat|ITT", "Intent-to-Treat (ITT)"),
            (r"(?i)per[- ]?protocol|PP", "Per-Protocol (PP)"),
            (r"(?i)(?:modified|m)ITT", "Modified Intent-to-Treat (mITT)"),
            (r"(?i)as[- ]?treated", "As-Treated"),
            (r"(?i)safety\s+(?:analysis\s+)?(?:population|set)", "Safety Population"),
        ]
        for pattern, label in population_patterns:
            if re.search(pattern, clinical_text):
                requirements["analysis_populations"].append(label)

        # Statistical methods
        method_patterns = [
            (r"(?i)Kaplan[- ]?Meier", "Kaplan-Meier survival analysis"),
            (r"(?i)Cox\s+(?:proportional\s+)?(?:hazard|regression)", "Cox proportional hazards"),
            (r"(?i)(?:Fisher|chi[- ]?square|chi[- ]?squared)", "Fisher/Chi-square test"),
            (r"(?i)(?:log[- ]?rank|Mantel[- ]?Haenszel)", "Log-rank test"),
            (r"(?i)mixed[- ]?(?:effects?\s+)?model", "Mixed-effects model"),
            (r"(?i)Bayesian\s+(?:analysis|framework|method)", "Bayesian analysis"),
        ]
        for pattern, label in method_patterns:
            if re.search(pattern, clinical_text):
                requirements["statistical_methods"].append(label)

        # Power calculation
        power_match = re.search(
            r"(?i)(?:powered|power)\s+(?:at|of|to)\s*(\d+)\s*%", clinical_text
        )
        if power_match:
            try:
                requirements["power_calculation"] = int(power_match.group(1))
            except ValueError as e:
                print(f"Warning: Failed to parse power calculation: {e}", file=sys.stderr)

        # Alpha level
        alpha_match = re.search(
            r"(?i)(?:alpha|significance\s+level)\s*(?:=|of|was)?\s*(0?\.\d+)", clinical_text
        )
        if alpha_match:
            try:
                requirements["alpha_level"] = float(alpha_match.group(1))
            except ValueError as e:
                print(f"Warning: Failed to parse alpha level: {e}", file=sys.stderr)

        # Multiple comparison adjustment
        if re.search(
            r"(?i)(?:Bonferroni|Hochberg|Holm|multiple\s+comparison|multiplicity\s+adjustment)",
            clinical_text,
        ):
            requirements["multiple_comparison_adjustment"] = True

        return requirements

    # ------------------------------------------------------------------
    # Cost and timeline estimation
    # ------------------------------------------------------------------

    def _estimate_trial_costs(self, requirements: Dict) -> Dict:
        """Estimate clinical trial costs based on extracted requirements.

        Args:
            requirements: Full requirements dict.

        Returns:
            Cost estimate dict with low/mid/high scenarios.
        """
        study_design = requirements.get("study_design_requirements", {})
        enrollment = requirements.get("enrollment_requirements", {})

        trial_type = study_design.get("trial_type", "unknown")
        design_info = STUDY_DESIGN_HIERARCHY.get(trial_type, {})

        n_patients = enrollment.get("minimum_sample_size") or design_info.get(
            "typical_enrollment_range", (100, 500)
        )[0]

        cost_per_patient = design_info.get("typical_cost_per_patient", 25000)

        # Base cost calculation
        base_cost = n_patients * cost_per_patient

        # Adjustments
        multiplier = 1.0
        if study_design.get("multicenter_required"):
            multiplier += 0.15  # Multi-site overhead
        if study_design.get("blinding") == "double_blind":
            multiplier += 0.10  # Blinding costs
        if requirements.get("data_requirements", {}).get("dsmb_required"):
            multiplier += 0.05
        if requirements.get("data_requirements", {}).get("core_lab"):
            multiplier += 0.10

        adjusted = base_cost * multiplier

        return {
            "estimated_per_patient_cost": cost_per_patient,
            "estimated_patients": n_patients,
            "low_estimate": int(adjusted * 0.7),
            "mid_estimate": int(adjusted),
            "high_estimate": int(adjusted * 1.5),
            "currency": "USD",
            "cost_drivers": self._identify_cost_drivers(requirements),
            "note": "Estimates based on historical PMA trial costs. Actual costs vary significantly.",
        }

    def _identify_cost_drivers(self, requirements: Dict) -> List[str]:
        """Identify key cost drivers from requirements.

        Args:
            requirements: Full requirements dict.

        Returns:
            List of cost driver descriptions.
        """
        drivers = []
        design = requirements.get("study_design_requirements", {})
        data_reqs = requirements.get("data_requirements", {})
        follow_up = requirements.get("follow_up_requirements", {})

        if design.get("complexity") == "very_high":
            drivers.append("Very high complexity trial design (sham-controlled)")
        elif design.get("complexity") == "high":
            drivers.append("High complexity trial design (RCT)")

        if design.get("multicenter_required"):
            drivers.append("Multicenter trial adds 15-20% overhead")

        if data_reqs.get("dsmb_required"):
            drivers.append("DSMB adds $200K-$500K")

        if data_reqs.get("core_lab"):
            drivers.append("Core laboratory adds $500K-$2M")

        recommended_months = follow_up.get("recommended_follow_up_months", 12)
        if recommended_months and recommended_months > 24:
            drivers.append(f"Extended follow-up ({recommended_months} months) increases per-patient costs")

        if follow_up.get("post_approval_study_required"):
            drivers.append("Post-approval study adds $2M-$10M+ to total program cost")

        return drivers

    def _estimate_trial_timeline(self, requirements: Dict) -> Dict:
        """Estimate clinical trial timeline from requirements.

        Args:
            requirements: Full requirements dict.

        Returns:
            Timeline estimate dict.
        """
        enrollment = requirements.get("enrollment_requirements", {})
        follow_up = requirements.get("follow_up_requirements", {})
        design = requirements.get("study_design_requirements", {})

        n_patients = enrollment.get("minimum_sample_size") or 200
        n_sites = enrollment.get("number_of_sites") or 10

        # Enrollment rate estimate (patients per site per month)
        enrollment_rate = 1.5 if design.get("complexity") in ("high", "very_high") else 2.5

        # Startup phase
        startup_months = 6 if design.get("multicenter_required") else 3

        # Enrollment duration
        enrollment_months = max(1, n_patients / (n_sites * enrollment_rate))

        # Follow-up duration
        follow_up_months = follow_up.get("recommended_follow_up_months", 12) or 12

        # Database lock and analysis
        analysis_months = 3

        total_months = startup_months + enrollment_months + follow_up_months + analysis_months

        return {
            "startup_months": round(startup_months, 1),
            "enrollment_months": round(enrollment_months, 1),
            "follow_up_months": round(follow_up_months, 1),
            "analysis_months": round(analysis_months, 1),
            "total_months": round(total_months, 1),
            "optimistic_months": round(total_months * 0.8, 1),
            "pessimistic_months": round(total_months * 1.5, 1),
            "note": "Excludes regulatory review time. Based on typical enrollment rates.",
        }

    # ------------------------------------------------------------------
    # Comparison helpers
    # ------------------------------------------------------------------

    def _build_comparison_matrix(self, all_requirements: Dict) -> Dict:
        """Build a requirement comparison matrix across PMAs.

        Args:
            all_requirements: Dict mapping PMA number to requirements.

        Returns:
            Comparison matrix dict.
        """
        matrix = {
            "study_design": {},
            "enrollment": {},
            "follow_up": {},
            "endpoints": {},
        }

        for pma, reqs in all_requirements.items():
            if not reqs.get("requirements_available"):
                continue

            design = reqs.get("study_design_requirements", {})
            enrollment = reqs.get("enrollment_requirements", {})
            follow_up = reqs.get("follow_up_requirements", {})
            endpoints = reqs.get("endpoint_requirements", {})

            matrix["study_design"][pma] = {
                "trial_type": design.get("trial_type_label", "Unknown"),
                "blinding": design.get("blinding", "unknown"),
                "control": design.get("control_arm", "unknown"),
                "complexity": design.get("complexity", "unknown"),
            }

            matrix["enrollment"][pma] = {
                "sample_size": enrollment.get("minimum_sample_size"),
                "sites": enrollment.get("number_of_sites"),
                "geographic": enrollment.get("geographic_scope", "unknown"),
            }

            matrix["follow_up"][pma] = {
                "duration_months": follow_up.get("observed_follow_up", {}).get("months"),
                "post_approval_study": follow_up.get("post_approval_study_required", False),
            }

            matrix["endpoints"][pma] = {
                "type": endpoints.get("endpoint_type", "unknown"),
                "primary_count": len(endpoints.get("primary_endpoints", [])),
                "secondary_count": len(endpoints.get("secondary_endpoints", [])),
            }

        return matrix

    def _derive_consensus(self, all_requirements: Dict) -> Dict:
        """Derive consensus requirements from multiple PMAs.

        Args:
            all_requirements: Dict mapping PMA number to requirements.

        Returns:
            Consensus requirements dict representing the most common patterns.
        """
        design_types = Counter()
        blindings = Counter()
        controls = Counter()
        enrollments = []
        follow_ups = []

        for pma, reqs in all_requirements.items():
            if not reqs.get("requirements_available"):
                continue

            design = reqs.get("study_design_requirements", {})
            enrollment = reqs.get("enrollment_requirements", {})
            follow_up = reqs.get("follow_up_requirements", {})

            dt = design.get("trial_type", "unknown")
            if dt != "unknown":
                design_types[dt] += 1

            bl = design.get("blinding", "unknown")
            if bl != "unknown":
                blindings[bl] += 1

            ctrl = design.get("control_arm", "unknown")
            if ctrl != "unknown":
                controls[ctrl] += 1

            n = enrollment.get("minimum_sample_size")
            if n is not None:
                enrollments.append(n)

            fu = follow_up.get("observed_follow_up", {}).get("months")
            if fu is not None:
                follow_ups.append(fu)

        return {
            "most_common_design": design_types.most_common(1)[0][0] if design_types else "unknown",
            "most_common_blinding": blindings.most_common(1)[0][0] if blindings else "unknown",
            "most_common_control": controls.most_common(1)[0][0] if controls else "unknown",
            "median_enrollment": int(sorted(enrollments)[len(enrollments) // 2]) if enrollments else None,
            "enrollment_range": (min(enrollments), max(enrollments)) if enrollments else None,
            "median_follow_up_months": round(sorted(follow_ups)[len(follow_ups) // 2], 1) if follow_ups else None,
            "pmas_analyzed": len([r for r in all_requirements.values() if r.get("requirements_available")]),
        }

    def _identify_differences(self, all_requirements: Dict) -> List[Dict]:
        """Identify notable differences across PMAs.

        Args:
            all_requirements: Dict mapping PMA number to requirements.

        Returns:
            List of difference dicts.
        """
        differences = []
        available = {
            k: v for k, v in all_requirements.items() if v.get("requirements_available")
        }

        if len(available) < 2:
            return differences

        # Compare study designs
        designs = set()
        for pma, reqs in available.items():
            dt = reqs.get("study_design_requirements", {}).get("trial_type", "unknown")
            designs.add(dt)
        if len(designs) > 1:
            differences.append({
                "dimension": "study_design",
                "description": f"Different study designs used: {', '.join(designs)}",
                "severity": "notable",
            })

        # Compare enrollment sizes
        enrollments = {}
        for pma, reqs in available.items():
            n = reqs.get("enrollment_requirements", {}).get("minimum_sample_size")
            if n is not None:
                enrollments[pma] = n
        if enrollments:
            values = list(enrollments.values())
            if max(values) > min(values) * 3:
                differences.append({
                    "dimension": "enrollment",
                    "description": (
                        f"Wide enrollment range: {min(values):,} to {max(values):,} patients"
                    ),
                    "severity": "critical",
                    "details": enrollments,
                })

        return differences

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def _summarize_design_patterns(self, all_reqs: Dict) -> Dict:
        """Summarize study design patterns across PMAs."""
        design_counts = Counter()
        for reqs in all_reqs.values():
            dt = reqs.get("study_design_requirements", {}).get("trial_type", "unknown")
            if dt != "unknown":
                design_counts[dt] += 1
        return dict(design_counts.most_common())

    def _summarize_enrollment(self, all_reqs: Dict) -> Dict:
        """Summarize enrollment statistics."""
        values = []
        for reqs in all_reqs.values():
            n = reqs.get("enrollment_requirements", {}).get("minimum_sample_size")
            if n is not None:
                values.append(n)

        if not values:
            return {"count": 0}

        values.sort()
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "median": values[len(values) // 2],
            "mean": int(sum(values) / len(values)),
        }

    def _summarize_endpoints(self, all_reqs: Dict) -> Dict:
        """Summarize endpoint patterns."""
        categories = Counter()
        for reqs in all_reqs.values():
            for cat in reqs.get("endpoint_requirements", {}).get("primary_endpoint_categories", []):
                categories[cat.get("category", "other")] += 1
        return dict(categories.most_common())

    def _summarize_follow_up(self, all_reqs: Dict) -> Dict:
        """Summarize follow-up patterns."""
        durations = []
        for reqs in all_reqs.values():
            fu = reqs.get("follow_up_requirements", {}).get("observed_follow_up", {}).get("months")
            if fu is not None:
                durations.append(fu)

        if not durations:
            return {"count": 0}

        durations.sort()
        return {
            "count": len(durations),
            "min_months": round(min(durations), 1),
            "max_months": round(max(durations), 1),
            "median_months": round(durations[len(durations) // 2], 1),
        }

    def _summarize_costs(self, all_reqs: Dict) -> Dict:
        """Summarize cost ranges."""
        costs = []
        for reqs in all_reqs.values():
            cost = reqs.get("cost_estimate", {}).get("mid_estimate")
            if cost:
                costs.append(cost)

        if not costs:
            return {"available": False}

        return {
            "available": True,
            "min_estimate": min(costs),
            "max_estimate": max(costs),
            "median_estimate": sorted(costs)[len(costs) // 2],
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _build_device_summary(self, api_data: Dict) -> Dict:
        """Build device summary from API data."""
        return {
            "pma_number": api_data.get("pma_number", ""),
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "product_code": api_data.get("product_code", ""),
            "advisory_committee": api_data.get("advisory_committee", ""),
            "decision_date": api_data.get("decision_date", ""),
        }

    def _get_combined_clinical_text(self, sections: Optional[Dict]) -> str:
        """Get combined clinical and statistical text from sections."""
        if not sections:
            return ""

        section_dict = sections.get("sections", sections)
        texts = []
        for key in ["clinical_studies", "statistical_analysis", "benefit_risk"]:
            sec = section_dict.get(key, {})
            if isinstance(sec, dict):
                content = sec.get("content", "")
                if content:
                    texts.append(content)
            elif isinstance(sec, str) and sec:
                texts.append(sec)

        return " ".join(texts)

    def _calculate_requirements_confidence(self, requirements: Dict) -> float:
        """Calculate overall confidence for extracted requirements."""
        scores = []

        design_conf = requirements.get("study_design_requirements", {}).get("confidence", 0)
        scores.append(design_conf)

        enrollment_conf = requirements.get("enrollment_requirements", {}).get("confidence", 0)
        scores.append(enrollment_conf)

        endpoint_conf = requirements.get("endpoint_requirements", {}).get("confidence", 0)
        scores.append(endpoint_conf)

        follow_up_conf = requirements.get("follow_up_requirements", {}).get("confidence", 0)
        scores.append(follow_up_conf)

        return round(sum(scores) / len(scores), 2) if scores else 0.0


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_requirements(reqs: Dict) -> str:
    """Format requirements as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("CLINICAL TRIAL REQUIREMENTS ANALYSIS")
    lines.append("=" * 70)

    device = reqs.get("device_summary", {})
    lines.append(f"PMA: {device.get('pma_number', 'N/A')}")
    lines.append(f"Device: {device.get('device_name', 'N/A')}")
    lines.append(f"Applicant: {device.get('applicant', 'N/A')}")
    lines.append(f"Overall Confidence: {reqs.get('confidence', 0):.0%}")
    lines.append("")

    # Study Design
    design = reqs.get("study_design_requirements", {})
    lines.append("--- Study Design Requirements ---")
    lines.append(f"  Trial Type: {design.get('trial_type_label', 'Unknown')}")
    lines.append(f"  Blinding: {design.get('blinding', 'unknown')}")
    lines.append(f"  Control Arm: {design.get('control_arm', 'unknown')}")
    lines.append(f"  Randomization: {'Yes' if design.get('randomization_required') else 'No'}")
    lines.append(f"  Multicenter: {'Yes' if design.get('multicenter_required') else 'No'}")
    lines.append(f"  Complexity: {design.get('complexity', 'unknown')}")
    lines.append("")

    # Enrollment
    enrollment = reqs.get("enrollment_requirements", {})
    lines.append("--- Enrollment Requirements ---")
    n = enrollment.get("minimum_sample_size")
    lines.append(f"  Observed Sample Size: {n:,}" if n else "  Observed Sample Size: N/A")
    rec = enrollment.get("recommended_sample_size")
    lines.append(f"  Recommended (with margin): {rec:,}" if rec else "  Recommended: N/A")
    lines.append(f"  Sites: {enrollment.get('number_of_sites', 'N/A')}")
    lines.append(f"  Geographic Scope: {enrollment.get('geographic_scope', 'unknown')}")
    lines.append("")

    # Endpoints
    endpoints = reqs.get("endpoint_requirements", {})
    lines.append("--- Endpoint Requirements ---")
    lines.append(f"  Type: {endpoints.get('endpoint_type', 'unknown')}")
    for ep in endpoints.get("primary_endpoints", [])[:3]:
        lines.append(f"  Primary: {ep.get('text', 'N/A')[:80]}")
    for ep in endpoints.get("secondary_endpoints", [])[:3]:
        lines.append(f"  Secondary: {ep.get('text', 'N/A')[:80]}")
    for ep in endpoints.get("safety_endpoints", [])[:2]:
        lines.append(f"  Safety: {ep.get('text', 'N/A')[:80]}")
    lines.append("")

    # Follow-up
    follow_up = reqs.get("follow_up_requirements", {})
    lines.append("--- Follow-up Requirements ---")
    obs = follow_up.get("observed_follow_up", {})
    if obs.get("duration"):
        lines.append(f"  Observed: {obs['duration']} {obs.get('unit', 'months')}")
    rec_fu = follow_up.get("recommended_follow_up_months")
    lines.append(f"  Recommended: {rec_fu} months" if rec_fu else "  Recommended: N/A")
    lines.append(f"  Post-Approval Study: {'Required' if follow_up.get('post_approval_study_required') else 'Not detected'}")
    lines.append("")

    # Cost Estimate
    cost = reqs.get("cost_estimate", {})
    lines.append("--- Cost Estimate ---")
    lines.append(f"  Per Patient: ${cost.get('estimated_per_patient_cost', 0):,}")
    lines.append(f"  Low: ${cost.get('low_estimate', 0):,}")
    lines.append(f"  Mid: ${cost.get('mid_estimate', 0):,}")
    lines.append(f"  High: ${cost.get('high_estimate', 0):,}")
    for driver in cost.get("cost_drivers", []):
        lines.append(f"  * {driver}")
    lines.append("")

    # Timeline
    timeline = reqs.get("timeline_estimate", {})
    lines.append("--- Timeline Estimate ---")
    lines.append(f"  Startup: {timeline.get('startup_months', 'N/A')} months")
    lines.append(f"  Enrollment: {timeline.get('enrollment_months', 'N/A')} months")
    lines.append(f"  Follow-up: {timeline.get('follow_up_months', 'N/A')} months")
    lines.append(f"  Analysis: {timeline.get('analysis_months', 'N/A')} months")
    lines.append(f"  TOTAL: {timeline.get('total_months', 'N/A')} months")
    lines.append(f"  Optimistic: {timeline.get('optimistic_months', 'N/A')} months")
    lines.append(f"  Pessimistic: {timeline.get('pessimistic_months', 'N/A')} months")
    lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {reqs.get('generated_at', 'N/A')[:10]}")
    lines.append("This analysis is AI-generated from PMA SSED data.")
    lines.append("Verify with qualified regulatory professionals.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Clinical Requirements Mapper -- Map trial requirements from PMA precedent"
    )
    parser.add_argument("--pma", help="PMA number to analyze")
    parser.add_argument("--compare", help="Comma-separated comparator PMA numbers")
    parser.add_argument("--product-code", dest="product_code",
                        help="Analyze all PMAs for a product code")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    mapper = ClinicalRequirementsMapper()

    if args.pma and args.compare:
        comparators = [c.strip().upper() for c in args.compare.split(",") if c.strip()]
        result = mapper.compare_requirements(
            args.pma, comparators, refresh=args.refresh
        )
    elif args.pma:
        result = mapper.map_requirements(args.pma, refresh=args.refresh)
    elif args.product_code:
        result = mapper.analyze_product_code_requirements(args.product_code)
    else:
        parser.error("Specify --pma or --product-code")
        return

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if "comparison_matrix" in result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(_format_requirements(result))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
