#!/usr/bin/env python3
"""
PMA Supplement Support Enhancement (FDA-65) -- Advanced supplement type
classification, decision tree, change impact assessment, and package generation
per 21 CFR 814.39.

REGULATORY DISCLAIMER:
All scores, classifications, and recommendations produced by this module are
HEURISTIC ESTIMATES based on historical patterns and keyword analysis. They
should NOT be used as the sole basis for regulatory decisions. Actual FDA
supplement type determination depends on device-specific characteristics,
current FDA policy, and detailed risk assessment by qualified personnel.
ALWAYS consult with qualified regulatory affairs professionals and consider
submitting a Pre-Submission (Q-Submission) to FDA for official guidance.

Extends supplement_tracker.py with:
  1. Enhanced supplement type classifier (>=95% accuracy target)
  2. Supplement decision tree (which type for which change)
  3. Change impact assessment tool (regulatory burden scoring)
  4. Supplement package generator (template-based output)

Supplement Types per 21 CFR 814.39:
  (d) 180-Day Supplement -- Manufacturing/design changes with clinical data
  (c) Real-Time Supplement -- Labeling changes, minor design changes
  (e) 30-Day Notice -- Minor manufacturing changes, editorial labeling
  (f) Panel-Track Supplement (Special PMA) -- Significant changes, panel review

Usage:
    from pma_supplement_enhanced import (
        SupplementTypeClassifier,
        SupplementDecisionTree,
        ChangeImpactAssessor,
        SupplementPackageGenerator,
    )

    # Classify a change description
    classifier = SupplementTypeClassifier()
    result = classifier.classify("New manufacturing site for sterilization")

    # Walk the decision tree
    tree = SupplementDecisionTree()
    recommendation = tree.evaluate(change_description="labeling update",
                                   has_clinical_data=False,
                                   is_design_change=False)

    # Assess change impact
    assessor = ChangeImpactAssessor()
    impact = assessor.assess_impact(change_type="manufacturing_site",
                                    affected_components=["sterilization"],
                                    has_performance_data=True)

    # Generate supplement package outline
    generator = SupplementPackageGenerator()
    package = generator.generate(supplement_type="180_day",
                                 change_description="New sterilization site",
                                 pma_number="P170019")

    # CLI usage:
    python3 pma_supplement_enhanced.py classify "labeling change for new indication"
    python3 pma_supplement_enhanced.py decide --change "new mfg site" --clinical-data
    python3 pma_supplement_enhanced.py impact --type manufacturing_site
    python3 pma_supplement_enhanced.py package --type 180_day --pma P170019
"""

import argparse
import json
import re
import sys
import warnings
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------------
# REGULATORY DISCLAIMER
# ------------------------------------------------------------------

REGULATORY_DISCLAIMER = """
REGULATORY DISCLAIMER:
This score is a HEURISTIC ESTIMATE based on historical patterns and should
NOT be used as the sole basis for regulatory decisions. Actual FDA
classification may differ based on:
- Specific device characteristics not captured in this model
- Current FDA policy and precedent
- Detailed risk assessment by qualified personnel

ALWAYS consult with qualified regulatory affairs professionals and consider
submitting a Pre-Submission (Q-Submission) to FDA for official guidance.
"""


# ------------------------------------------------------------------
# Supplement Type Definitions per 21 CFR 814.39
# ------------------------------------------------------------------

SUPPLEMENT_TYPES = OrderedDict([
    ("panel_track", {
        "label": "Panel-Track Supplement",
        "cfr_section": "21 CFR 814.39(f)",
        "short_name": "Panel-Track",
        "review_days": 365,
        "risk_level": "critical",
        "description": (
            "Significant changes in design, indication, or patient population "
            "that require advisory committee (panel) review."
        ),
        "examples": [
            "New clinical indication requiring panel review",
            "Significant modification to device design with new risk profile",
            "Expansion to pediatric population",
            "Change in implant material class",
        ],
    }),
    ("180_day", {
        "label": "180-Day Supplement",
        "cfr_section": "21 CFR 814.39(d)",
        "short_name": "180-Day",
        "review_days": 180,
        "risk_level": "high",
        "description": (
            "Manufacturing or design changes that could affect safety or "
            "effectiveness, supported by new clinical or nonclinical data."
        ),
        "examples": [
            "New manufacturing process with performance data",
            "Design change with new bench testing",
            "Manufacturing site change with validation data",
            "Sterilization method change with validation",
            "New indication with clinical data",
            "Change in materials requiring biocompatibility",
        ],
    }),
    ("real_time", {
        "label": "Real-Time Supplement",
        "cfr_section": "21 CFR 814.39(c)",
        "short_name": "Real-Time",
        "review_days": 90,
        "risk_level": "medium",
        "description": (
            "Labeling changes and minor design changes not affecting "
            "safety or effectiveness. Marketing can begin at submission."
        ),
        "examples": [
            "Labeling change for updated warnings",
            "IFU revision for clarity",
            "Contraindication addition",
            "Precaution update based on post-market data",
            "Minor design enhancement with existing data",
        ],
    }),
    ("30_day_notice", {
        "label": "30-Day Notice",
        "cfr_section": "21 CFR 814.39(e)",
        "short_name": "30-Day",
        "review_days": 30,
        "risk_level": "low",
        "description": (
            "Minor manufacturing changes with no performance impact. "
            "Marketing may begin 30 days after FDA acknowledgment."
        ),
        "examples": [
            "Editorial labeling corrections",
            "Manufacturing process parameter adjustment within spec",
            "Minor packaging change",
            "Supplier change for non-critical component",
            "Cosmetic device modifications",
        ],
    }),
    ("annual_report", {
        "label": "Annual Report (PMA Annual Report)",
        "cfr_section": "21 CFR 814.84",
        "short_name": "Annual",
        "review_days": 0,
        "risk_level": "minimal",
        "description": (
            "Changes reportable in the PMA annual report rather than "
            "requiring a separate supplement. Typically minor editorial "
            "or administrative changes."
        ),
        "examples": [
            "Company name change",
            "Administrative contact update",
            "Minor typographical correction",
            "Reformatting without content change",
        ],
    }),
])


# ------------------------------------------------------------------
# Keyword Pattern Library for Classification
# ------------------------------------------------------------------

# Each entry: (pattern, weight, supplement_type)
# Higher weight = stronger signal. Patterns checked in priority order.
CLASSIFICATION_PATTERNS: List[Tuple[str, float, str]] = [
    # Panel-Track (strongest signals first)
    (r"panel[\s-]?track", 10.0, "panel_track"),
    (r"advisory\s+committee", 9.0, "panel_track"),
    (r"significant\s+(?:change|modification)\s+(?:to|in)\s+(?:design|indication)", 8.0, "panel_track"),
    (r"(?:new|novel)\s+(?:clinical\s+)?indication.*panel", 8.0, "panel_track"),
    (r"expansion\s+to\s+pediatric", 7.5, "panel_track"),
    (r"(?:new|different)\s+implant\s+material\s+class", 7.0, "panel_track"),

    # 180-Day Supplement
    (r"180[\s-]?day", 10.0, "180_day"),
    (r"(?:new|change\w*)\s+manufactur\w+\s+(?:site|facility|process).*(?:valid|data|test)", 7.0, "180_day"),
    (r"design\s+change.*(?:clinical|bench|test|data|valid)", 7.0, "180_day"),
    (r"sterilization\s+(?:method|process)\s+change.*valid", 7.0, "180_day"),
    (r"(?:new|additional)\s+indication.*(?:clinical|data)", 7.0, "180_day"),
    (r"material\s+change.*biocompat", 6.5, "180_day"),
    (r"(?:performance|safety)\s+data.*(?:manufactur|design)", 6.0, "180_day"),
    (r"(?:manufactur|design)\s+change.*(?:affect|impact)\s+(?:safety|performance)", 6.0, "180_day"),
    (r"new\s+(?:manufactur|production)\s+(?:site|facility)", 5.5, "180_day"),
    (r"(?:change|modify)\s+(?:in|to)\s+(?:component|material)\s+(?:with|including)\s+(?:data|test)", 5.5, "180_day"),

    # Real-Time Supplement
    (r"real[\s-]?time\s+supplement", 10.0, "real_time"),
    (r"labeling\s+(?:change|update|revision).*(?:warning|contraindication|precaution)", 7.0, "real_time"),
    (r"(?:new|updated|revised)\s+(?:warning|contraindication|precaution)", 6.5, "real_time"),
    (r"(?:ifu|instructions?\s+for\s+use)\s+(?:revision|update|change)", 6.0, "real_time"),
    (r"labeling\s+(?:change|update|revision)", 5.5, "real_time"),
    (r"(?:minor|small)\s+design\s+(?:change|enhancement|modification)", 5.0, "real_time"),
    (r"label\s+(?:revision|update)", 5.0, "real_time"),

    # 30-Day Notice
    (r"30[\s-]?day\s+notice", 10.0, "30_day_notice"),
    (r"(?:minor|editorial)\s+(?:labeling|label)\s+(?:change|correction|update)", 7.0, "30_day_notice"),
    (r"(?:minor|non[\s-]?critical)\s+manufactur\w+\s+change", 6.5, "30_day_notice"),
    (r"packaging\s+(?:change|update)", 5.5, "30_day_notice"),
    (r"(?:supplier|vendor)\s+change.*(?:non[\s-]?critical|minor)", 5.5, "30_day_notice"),
    (r"(?:cosmetic|aesthetic)\s+(?:change|modification)", 5.0, "30_day_notice"),
    (r"process\s+parameter\s+(?:adjustment|change).*within\s+spec", 5.0, "30_day_notice"),

    # Annual Report
    (r"annual\s+report", 10.0, "annual_report"),
    (r"company\s+name\s+change", 7.0, "annual_report"),
    (r"(?:administrative|contact)\s+(?:change|update)", 6.0, "annual_report"),
    (r"(?:typographical|typo)\s+correction", 6.0, "annual_report"),
    (r"reformat(?:ting)?\s+(?:without|no)\s+content\s+change", 5.5, "annual_report"),
]

# Compiled patterns for efficiency
_COMPILED_PATTERNS = [
    (re.compile(pat, re.IGNORECASE), weight, stype)
    for pat, weight, stype in CLASSIFICATION_PATTERNS
]


# ------------------------------------------------------------------
# Decision Tree Nodes
# ------------------------------------------------------------------

DECISION_TREE = {
    "root": {
        "question": "What type of change are you making to the PMA device?",
        "options": {
            "design_change": "node_design",
            "manufacturing_change": "node_manufacturing",
            "labeling_change": "node_labeling",
            "indication_change": "node_indication",
            "administrative_change": "node_admin",
        },
    },
    "node_design": {
        "question": "Does the design change affect safety or effectiveness?",
        "options": {
            "yes_significant": "node_design_significant",
            "yes_minor": "node_design_minor",
            "no": "leaf_30_day_or_annual",
        },
    },
    "node_design_significant": {
        "question": "Does the change require advisory committee review?",
        "options": {
            "yes": "leaf_panel_track",
            "no": "leaf_180_day",
        },
    },
    "node_design_minor": {
        "question": "Is the change supported by existing data (no new testing needed)?",
        "options": {
            "yes": "leaf_real_time",
            "no": "leaf_180_day",
        },
    },
    "node_manufacturing": {
        "question": "Does the manufacturing change affect device performance?",
        "options": {
            "yes_with_data": "leaf_180_day",
            "yes_without_data": "leaf_180_day_needs_data",
            "no_minor": "leaf_30_day",
            "no_within_spec": "leaf_30_day",
        },
    },
    "node_labeling": {
        "question": "What type of labeling change?",
        "options": {
            "new_indication": "node_indication",
            "safety_update": "leaf_real_time",
            "ifu_revision": "leaf_real_time",
            "editorial_correction": "leaf_30_day",
            "formatting_only": "leaf_annual_report",
        },
    },
    "node_indication": {
        "question": "Is the indication change significant (new patient population, new anatomy)?",
        "options": {
            "yes_requires_panel": "leaf_panel_track",
            "yes_with_clinical_data": "leaf_180_day",
            "minor_clarification": "leaf_real_time",
        },
    },
    "node_admin": {
        "question": "What type of administrative change?",
        "options": {
            "company_name": "leaf_annual_report",
            "contact_info": "leaf_annual_report",
            "address_change": "leaf_annual_report",
        },
    },
    # Leaf nodes (supplement type recommendations)
    "leaf_panel_track": {
        "recommendation": "panel_track",
        "rationale": "Significant change requiring advisory committee panel review per 21 CFR 814.39(f).",
        "estimated_timeline_months": 12,
    },
    "leaf_180_day": {
        "recommendation": "180_day",
        "rationale": "Change affecting safety/effectiveness with supporting data per 21 CFR 814.39(d).",
        "estimated_timeline_months": 6,
    },
    "leaf_180_day_needs_data": {
        "recommendation": "180_day",
        "rationale": "Change affecting performance requires 180-Day supplement. Gather validation data first.",
        "estimated_timeline_months": 9,
        "warning": "Supporting data (bench, clinical, or manufacturing validation) must be included.",
    },
    "leaf_real_time": {
        "recommendation": "real_time",
        "rationale": "Labeling or minor change not affecting safety/effectiveness per 21 CFR 814.39(c).",
        "estimated_timeline_months": 3,
    },
    "leaf_30_day": {
        "recommendation": "30_day_notice",
        "rationale": "Minor manufacturing change with no performance impact per 21 CFR 814.39(e).",
        "estimated_timeline_months": 1,
    },
    "leaf_30_day_or_annual": {
        "recommendation": "30_day_notice",
        "rationale": "Non-impactful change. Consider if reportable in Annual Report or requires 30-Day Notice.",
        "estimated_timeline_months": 1,
    },
    "leaf_annual_report": {
        "recommendation": "annual_report",
        "rationale": "Administrative change reportable in PMA Annual Report per 21 CFR 814.84.",
        "estimated_timeline_months": 0,
    },
}


# ------------------------------------------------------------------
# Change Impact Scoring
# ------------------------------------------------------------------

IMPACT_CATEGORIES = {
    "design_change": {
        "base_score": 40,
        "subcategories": {
            "materials": 15,
            "dimensions": 10,
            "mechanism_of_action": 20,
            "software": 12,
            "biocompatibility": 18,
            "sterilization": 15,
        },
    },
    "manufacturing_change": {
        "base_score": 25,
        "subcategories": {
            "site_change": 15,
            "process_change": 12,
            "supplier_change": 10,
            "equipment_change": 8,
            "sterilization_method": 18,
            "packaging": 5,
        },
    },
    "labeling_change": {
        "base_score": 15,
        "subcategories": {
            "new_indication": 25,
            "contraindication": 12,
            "warning": 10,
            "ifu_revision": 8,
            "editorial": 2,
        },
    },
    "indication_change": {
        "base_score": 35,
        "subcategories": {
            "new_patient_population": 25,
            "new_anatomical_site": 20,
            "expanded_claim": 15,
            "restricted_claim": 10,
        },
    },
}


# ------------------------------------------------------------------
# Package Templates
# ------------------------------------------------------------------

PACKAGE_SECTIONS = {
    "panel_track": [
        "Cover Letter with 21 CFR 814.39(f) reference",
        "Table of Contents",
        "Device Description (updated)",
        "Summary of Changes from Approved PMA",
        "Significant Change Justification",
        "Updated Risk Analysis (ISO 14971)",
        "Nonclinical Testing (bench, biocompatibility, sterilization)",
        "Clinical Data (pivotal study results or literature review)",
        "Updated Labeling (proposed)",
        "Manufacturing Information (if changed)",
        "Advisory Committee Briefing Document",
        "Environmental Assessment or Claim of Categorical Exclusion",
        "Financial Certification/Disclosure (Form FDA 3454/3455)",
        "Truthful and Accurate Statement (Form FDA 3514)",
    ],
    "180_day": [
        "Cover Letter with 21 CFR 814.39(d) reference",
        "Table of Contents",
        "Summary of Changes from Approved PMA",
        "Updated Device Description",
        "Comparison Table: Approved vs. Modified Device",
        "Updated Risk Analysis (ISO 14971)",
        "Nonclinical Testing Data (bench, biocompatibility if applicable)",
        "Clinical Data (if applicable)",
        "Manufacturing Validation Data (if manufacturing change)",
        "Sterilization Validation (if sterilization change)",
        "Updated Labeling (proposed)",
        "Shelf Life Data (if applicable)",
        "Environmental Assessment or Claim of Categorical Exclusion",
        "Truthful and Accurate Statement (Form FDA 3514)",
    ],
    "real_time": [
        "Cover Letter with 21 CFR 814.39(c) reference",
        "Table of Contents",
        "Summary of Changes from Approved PMA",
        "Rationale for Supplement Type (Real-Time justification)",
        "Updated Labeling (proposed, redline comparison)",
        "Risk Analysis Update (if applicable)",
        "Supporting Data (post-market data, literature, if applicable)",
        "Truthful and Accurate Statement (Form FDA 3514)",
    ],
    "30_day_notice": [
        "Cover Letter with 21 CFR 814.39(e) reference",
        "Summary of Changes from Approved PMA",
        "Rationale: Change Does Not Affect Performance",
        "Supporting Data (validation summary, if applicable)",
        "Updated Labeling (if labeling change)",
        "Truthful and Accurate Statement (Form FDA 3514)",
    ],
    "annual_report": [
        "Annual Report Cover Page (21 CFR 814.84)",
        "Summary of Changes During Reporting Period",
        "Updated Device Description (if changed)",
        "Manufacturing Changes (within approved specs)",
        "Complaint Summary and Trend Analysis",
        "MDR Summary",
        "Distribution Data",
        "Updated Bibliography (if applicable)",
    ],
}


# ==================================================================
# Supplement Type Classifier
# ==================================================================

class SupplementTypeClassifier:
    """Enhanced supplement type classifier using weighted keyword matching
    and contextual analysis for >=95% accuracy target.

    Classifies change descriptions into supplement types per 21 CFR 814.39.
    Uses a multi-signal scoring approach:
      1. Regex pattern matching with priority weights
      2. Contextual modifiers (clinical data presence, risk signals)
      3. Confidence scoring with thresholds

    REGULATORY DISCLAIMER:
    Classification results are HEURISTIC ESTIMATES based on keyword pattern
    matching against historical data. They should NOT be used as the sole
    basis for regulatory decisions. Actual FDA supplement type determination
    depends on device-specific characteristics, current FDA policy, and
    professional risk assessment. Always consult qualified RA professionals.
    """

    CONFIDENCE_HIGH = 0.85
    CONFIDENCE_MEDIUM = 0.60
    CONFIDENCE_LOW = 0.40

    # Threshold below which a runtime warning is emitted
    LOW_CONFIDENCE_WARNING_THRESHOLD = 0.50

    def __init__(self):
        """Initialize classifier with compiled patterns."""
        self._patterns = _COMPILED_PATTERNS

    def classify(
        self,
        change_description: str,
        has_clinical_data: bool = False,
        has_performance_data: bool = False,
        is_design_change: bool = False,
        is_manufacturing_change: bool = False,
        is_labeling_change: bool = False,
    ) -> Dict[str, Any]:
        """Classify a change description into a supplement type.

        REGULATORY DISCLAIMER: This classification is a heuristic estimate.
        It should NOT be used as the sole basis for regulatory decisions.
        Always consult qualified regulatory affairs professionals.

        Args:
            change_description: Free-text description of the PMA change.
            has_clinical_data: Whether clinical data supports the change.
            has_performance_data: Whether performance/bench data exists.
            is_design_change: Explicit flag for design changes.
            is_manufacturing_change: Explicit flag for manufacturing changes.
            is_labeling_change: Explicit flag for labeling changes.

        Returns:
            Classification result with type, confidence, rationale,
            alternative types considered, and regulatory disclaimer.
        """
        if not change_description or not change_description.strip():
            return {
                "supplement_type": "180_day",
                "confidence": 0.0,
                "confidence_label": "UNKNOWN",
                "rationale": "No change description provided. Defaulting to 180-Day (safest).",
                "cfr_section": "21 CFR 814.39(d)",
                "alternatives": [],
            }

        text = change_description.strip().lower()

        # Phase 1: Pattern matching scores
        scores: Dict[str, float] = {}
        matched_patterns: Dict[str, List[str]] = {}
        for compiled_re, weight, stype in self._patterns:
            if compiled_re.search(text):
                scores[stype] = scores.get(stype, 0.0) + weight
                matched_patterns.setdefault(stype, []).append(compiled_re.pattern)

        # Phase 2: Contextual modifiers
        if has_clinical_data:
            scores["180_day"] = scores.get("180_day", 0.0) + 3.0
            scores["panel_track"] = scores.get("panel_track", 0.0) + 2.0
        if has_performance_data:
            scores["180_day"] = scores.get("180_day", 0.0) + 2.0
        if is_design_change:
            scores["180_day"] = scores.get("180_day", 0.0) + 2.5
            scores["panel_track"] = scores.get("panel_track", 0.0) + 1.0
        if is_manufacturing_change:
            scores["180_day"] = scores.get("180_day", 0.0) + 1.5
            scores["30_day_notice"] = scores.get("30_day_notice", 0.0) + 1.0
        if is_labeling_change:
            scores["real_time"] = scores.get("real_time", 0.0) + 2.0
            scores["30_day_notice"] = scores.get("30_day_notice", 0.0) + 1.0

        # Phase 3: Determine winner
        if not scores:
            # No patterns matched -- use heuristics
            return self._heuristic_classify(text, has_clinical_data)

        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_type, best_score = sorted_types[0]

        # Calculate confidence
        total_score = sum(s for _, s in sorted_types)
        confidence = best_score / total_score if total_score > 0 else 0.0

        # Determine confidence label
        if confidence >= self.CONFIDENCE_HIGH:
            confidence_label = "HIGH"
        elif confidence >= self.CONFIDENCE_MEDIUM:
            confidence_label = "MEDIUM"
        elif confidence >= self.CONFIDENCE_LOW:
            confidence_label = "LOW"
        else:
            confidence_label = "VERY_LOW"

        # Build alternatives
        alternatives = []
        for alt_type, alt_score in sorted_types[1:3]:
            alt_conf = alt_score / total_score if total_score > 0 else 0.0
            type_def = SUPPLEMENT_TYPES.get(alt_type, {})  # type: ignore
            alternatives.append({
                "supplement_type": alt_type,
                "label": type_def.get("label", alt_type),
                "confidence": round(alt_conf, 3),
                "score": round(alt_score, 1),
            })

        type_def = SUPPLEMENT_TYPES.get(best_type, {})  # type: ignore

        # Emit runtime warning for low-confidence classifications
        if confidence < self.LOW_CONFIDENCE_WARNING_THRESHOLD:
            warnings.warn(
                f"Low confidence ({confidence:.1%}) for PMA supplement classification "
                f"as '{type_def.get('label', best_type)}'. "
                f"This heuristic estimate should be verified by a qualified "
                f"regulatory affairs professional before any regulatory action.",
                stacklevel=2,
            )

        return {
            "supplement_type": best_type,
            "label": type_def.get("label", best_type),
            "cfr_section": type_def.get("cfr_section", ""),
            "review_days": type_def.get("review_days", 180),
            "risk_level": type_def.get("risk_level", "unknown"),
            "confidence": round(confidence, 3),
            "confidence_label": confidence_label,
            "score": round(best_score, 1),
            "rationale": self._build_rationale(best_type, matched_patterns.get(best_type, [])),
            "alternatives": alternatives,
            "matched_patterns": len(matched_patterns.get(best_type, [])),
            "disclaimer": REGULATORY_DISCLAIMER.strip(),
        }

    def _heuristic_classify(self, text: str, has_clinical: bool) -> Dict:
        """Fallback heuristic classification when no patterns match.

        REGULATORY DISCLAIMER: This is a low-confidence heuristic fallback.
        Results should be verified by qualified regulatory professionals.
        """
        # Simple keyword presence check
        if any(kw in text for kw in ("label", "ifu", "instructions")):
            stype = "real_time"
        elif any(kw in text for kw in ("manufactur", "facility", "supplier")):
            stype = "30_day_notice" if not has_clinical else "180_day"
        elif any(kw in text for kw in ("design", "material", "component")):
            stype = "180_day"
        elif any(kw in text for kw in ("indication", "claim", "population")):
            stype = "180_day"
        else:
            stype = "180_day"  # Conservative default

        type_def = SUPPLEMENT_TYPES.get(stype, {})

        # Always warn for heuristic fallback -- these are inherently low-confidence
        warnings.warn(
            f"Heuristic fallback classification to '{type_def.get('label', stype)}' "
            f"(confidence: 35%). No strong regulatory patterns matched. "
            f"Consult a qualified regulatory affairs professional.",
            stacklevel=3,
        )

        return {
            "supplement_type": stype,
            "label": type_def.get("label", stype),
            "cfr_section": type_def.get("cfr_section", ""),
            "review_days": type_def.get("review_days", 180),
            "risk_level": type_def.get("risk_level", "unknown"),
            "confidence": 0.35,
            "confidence_label": "LOW",
            "score": 0.0,
            "rationale": (
                "Heuristic classification based on keyword analysis. "
                "Consider consulting RA professional."
            ),
            "alternatives": [],
            "matched_patterns": 0,
            "disclaimer": REGULATORY_DISCLAIMER.strip(),
        }

    def _build_rationale(self, stype: str, patterns: List[str]) -> str:
        """Build human-readable rationale for classification."""
        type_def = SUPPLEMENT_TYPES.get(stype, {})  # type: ignore
        label = type_def.get("label", stype)
        cfr = type_def.get("cfr_section", "21 CFR 814.39")
        n_patterns = len(patterns)
        return (
            f"Classified as {label} per {cfr}. "
            f"Matched {n_patterns} regulatory pattern(s). "
            f"{type_def.get('description', '')}"
        )

    def classify_batch(
        self,
        descriptions: List[str],
        **kwargs,
    ) -> List[Dict]:
        """Classify multiple change descriptions.

        Args:
            descriptions: List of change description strings.
            **kwargs: Additional flags passed to classify().

        Returns:
            List of classification results.
        """
        return [self.classify(desc, **kwargs) for desc in descriptions]


# ==================================================================
# Supplement Decision Tree
# ==================================================================

class SupplementDecisionTree:
    """Interactive decision tree for determining the appropriate PMA
    supplement type based on structured questions.

    Implements the FDA's decision logic per 21 CFR 814.39 and associated
    guidance documents.
    """

    def __init__(self):
        """Initialize with the standard decision tree."""
        self._tree = DECISION_TREE

    def get_root(self) -> Dict:
        """Get the root node of the decision tree."""
        return self._tree["root"]

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a specific node by ID.

        Args:
            node_id: Node identifier.

        Returns:
            Node dict or None if not found.
        """
        return self._tree.get(node_id)

    def is_leaf(self, node_id: str) -> bool:
        """Check if a node is a leaf (recommendation) node."""
        node = self._tree.get(node_id, {})
        return "recommendation" in node

    def get_recommendation(self, node_id: str) -> Optional[Dict]:
        """Get the recommendation from a leaf node.

        Args:
            node_id: Leaf node identifier.

        Returns:
            Recommendation dict with supplement type and rationale.
        """
        node = self._tree.get(node_id)
        if not node or "recommendation" not in node:
            return None

        stype = node["recommendation"]
        type_def = SUPPLEMENT_TYPES.get(stype, {})

        return {
            "supplement_type": stype,
            "label": type_def.get("label", stype),
            "cfr_section": type_def.get("cfr_section", ""),
            "review_days": type_def.get("review_days", 180),
            "rationale": node.get("rationale", ""),
            "warning": node.get("warning"),
            "estimated_timeline_months": node.get("estimated_timeline_months", 6),
        }

    def evaluate(
        self,
        change_description: str = "",
        change_category: str = "",
        has_clinical_data: bool = False,
        is_design_change: bool = False,
        is_manufacturing_change: bool = False,
        is_labeling_change: bool = False,
        affects_safety: bool = False,
        requires_panel: bool = False,
    ) -> Dict:
        """Automatically traverse the decision tree based on inputs.

        Args:
            change_description: Free-text description.
            change_category: Pre-classified category.
            has_clinical_data: Clinical data available.
            is_design_change: Is a design change.
            is_manufacturing_change: Is a manufacturing change.
            is_labeling_change: Is a labeling change.
            affects_safety: Change affects safety/effectiveness.
            requires_panel: Change requires advisory committee review.

        Returns:
            Decision result with supplement type, rationale, and path taken.
        """
        path = ["root"]
        text = change_description.lower() if change_description else ""

        # Determine change category from flags or text
        if not change_category:
            if is_design_change or any(kw in text for kw in ("design", "material", "component")):
                change_category = "design_change"
            elif is_manufacturing_change or any(kw in text for kw in ("manufactur", "facility", "site", "supplier")):
                change_category = "manufacturing_change"
            elif is_labeling_change or any(kw in text for kw in ("label", "ifu", "instruction", "warning")):
                change_category = "labeling_change"
            elif any(kw in text for kw in ("indication", "claim", "population", "expand")):
                change_category = "indication_change"
            elif any(kw in text for kw in ("company", "contact", "address", "name change")):
                change_category = "administrative_change"
            else:
                change_category = "design_change"  # Conservative default

        # Walk the tree
        current = "root"
        visited = set()
        max_depth = 10

        for _ in range(max_depth):
            if current in visited:
                break
            visited.add(current)
            node = self._tree.get(current)
            if not node:
                break

            # Check if leaf
            if "recommendation" in node:
                rec = self.get_recommendation(current)
                if rec:
                    rec["decision_path"] = path
                    rec["change_category"] = change_category
                return rec  # type: ignore

            # Navigate based on options
            options = node.get("options", {})
            next_node = self._select_option(
                current, options, change_category,
                has_clinical_data, affects_safety, requires_panel, text
            )

            if next_node:
                path.append(next_node)
                current = next_node
            else:
                break

        # Fallback if tree walk failed
        return {
            "supplement_type": "180_day",
            "label": "180-Day Supplement",
            "cfr_section": "21 CFR 814.39(d)",
            "review_days": 180,
            "rationale": "Unable to determine exact type. Defaulting to 180-Day (conservative).",
            "estimated_timeline_months": 6,
            "decision_path": path,
            "change_category": change_category,
        }

    def _select_option(
        self,
        current: str,
        options: Dict[str, str],
        category: str,
        has_clinical: bool,
        affects_safety: bool,
        requires_panel: bool,
        text: str,
    ) -> Optional[str]:
        """Select the appropriate option at a decision node."""

        if current == "root":
            return options.get(category, options.get("design_change"))

        if current == "node_design":
            if affects_safety or requires_panel:
                return options.get("yes_significant")
            elif any(kw in text for kw in ("minor", "small", "cosmetic")):
                return options.get("yes_minor")
            elif has_clinical:
                return options.get("yes_significant")
            else:
                return options.get("yes_minor")

        if current == "node_design_significant":
            if requires_panel:
                return options.get("yes")
            return options.get("no")

        if current == "node_design_minor":
            if has_clinical or any(kw in text for kw in ("existing data", "no new test")):
                return options.get("yes")
            return options.get("no")

        if current == "node_manufacturing":
            if affects_safety and has_clinical:
                return options.get("yes_with_data")
            elif affects_safety:
                return options.get("yes_without_data")
            elif any(kw in text for kw in ("minor", "within spec")):
                return options.get("no_within_spec")
            return options.get("no_minor")

        if current == "node_labeling":
            if any(kw in text for kw in ("indication", "claim")):
                return options.get("new_indication")
            elif any(kw in text for kw in ("warning", "contraindication", "precaution", "safety")):
                return options.get("safety_update")
            elif any(kw in text for kw in ("ifu", "instructions")):
                return options.get("ifu_revision")
            elif any(kw in text for kw in ("editorial", "typo", "correction")):
                return options.get("editorial_correction")
            elif any(kw in text for kw in ("format", "layout")):
                return options.get("formatting_only")
            return options.get("safety_update")

        if current == "node_indication":
            if requires_panel:
                return options.get("yes_requires_panel")
            elif has_clinical:
                return options.get("yes_with_clinical_data")
            return options.get("minor_clarification")

        if current == "node_admin":
            if "name" in text:
                return options.get("company_name")
            elif "contact" in text:
                return options.get("contact_info")
            return options.get("address_change")

        # Default: return first option
        if options:
            return next(iter(options.values()))
        return None

    def get_all_paths(self) -> List[Dict]:
        """Get all possible decision paths through the tree.

        Returns:
            List of path dicts, each with nodes visited and leaf recommendation.
        """
        paths = []
        self._walk_paths("root", [], paths)
        return paths

    def _walk_paths(self, node_id: str, current_path: List[str], all_paths: List[Dict]):
        """Recursively walk all paths."""
        node = self._tree.get(node_id)
        if not node:
            return

        current_path = current_path + [node_id]

        if "recommendation" in node:
            all_paths.append({
                "path": current_path,
                "recommendation": node["recommendation"],
                "rationale": node.get("rationale", ""),
            })
            return

        for _option_label, next_node in node.get("options", {}).items():
            self._walk_paths(next_node, current_path, all_paths)


# ==================================================================
# Change Impact Assessor
# ==================================================================

class ChangeImpactAssessor:
    """Assess the regulatory impact of proposed PMA changes.

    Provides quantitative impact scoring to help determine:
    - Regulatory burden (testing, documentation, review time)
    - Risk level of the change
    - Required data packages
    - Estimated timeline and cost impact

    REGULATORY DISCLAIMER:
    Impact scores and risk levels are HEURISTIC ESTIMATES derived from
    weighted scoring models. They do NOT replace professional regulatory
    assessment. Actual regulatory burden depends on device-specific factors,
    current FDA guidance, and reviewer discretion. Always consult qualified
    regulatory affairs professionals before making regulatory decisions.
    """

    def __init__(self):
        """Initialize with impact category definitions."""
        self._categories = IMPACT_CATEGORIES

    def assess_impact(
        self,
        change_type: str,
        affected_components: Optional[List[str]] = None,
        has_performance_data: bool = False,
        has_clinical_data: bool = False,
        has_biocompatibility_data: bool = False,
        change_description: str = "",
    ) -> Dict:
        """Assess the regulatory impact of a proposed change.

        REGULATORY DISCLAIMER: Impact scores are heuristic estimates.
        They should NOT be used as the sole basis for regulatory decisions.
        Always consult qualified regulatory affairs professionals.

        Args:
            change_type: Primary change category (design_change, manufacturing_change,
                        labeling_change, indication_change).
            affected_components: List of affected subcategories.
            has_performance_data: Whether bench/performance data exists.
            has_clinical_data: Whether clinical data exists.
            has_biocompatibility_data: Whether biocompatibility data exists.
            change_description: Free-text description for additional analysis.

        Returns:
            Impact assessment with scores, risk level, required data,
            estimated timeline, and regulatory disclaimer.
        """
        if change_type not in self._categories:
            change_type = self._infer_change_type(change_description)

        category = self._categories.get(change_type, self._categories["design_change"])
        base_score = category["base_score"]

        # Calculate component scores
        component_score = 0
        matched_components = []
        if affected_components:
            for comp in affected_components:
                comp_key = comp.lower().replace(" ", "_").replace("-", "_")
                score = category.get("subcategories", {}).get(comp_key, 5)
                component_score += score
                matched_components.append({"component": comp, "score": score})

        total_score = base_score + component_score

        # Data availability modifiers
        data_readiness_score = 0
        data_gaps = []
        if has_performance_data:
            data_readiness_score += 20
        else:
            data_gaps.append("Performance/bench testing data")
        if has_clinical_data:
            data_readiness_score += 25
        else:
            if total_score >= 40:
                data_gaps.append("Clinical data (may be required for this impact level)")
        if has_biocompatibility_data:
            data_readiness_score += 15
        else:
            if any(kw in change_description.lower() for kw in
                   ("material", "biocompat", "implant", "tissue contact")):
                data_gaps.append("Biocompatibility data (material change detected)")

        # Determine overall risk level
        if total_score >= 60:
            risk_level = "CRITICAL"
            supplement_type = "panel_track"
        elif total_score >= 40:
            risk_level = "HIGH"
            supplement_type = "180_day"
        elif total_score >= 20:
            risk_level = "MEDIUM"
            supplement_type = "real_time"
        else:
            risk_level = "LOW"
            supplement_type = "30_day_notice"

        # Required documentation
        required_docs = self._determine_required_docs(
            change_type, total_score, affected_components or []
        )

        # Timeline estimation
        timeline = self._estimate_timeline(total_score, data_readiness_score)

        type_def = SUPPLEMENT_TYPES.get(supplement_type, {})

        # Emit runtime warning for high-impact (CRITICAL) scores
        if risk_level == "CRITICAL":
            warnings.warn(
                f"CRITICAL impact score ({total_score}) for change type "
                f"'{change_type}'. This heuristic assessment suggests a "
                f"Panel-Track Supplement may be required. Consult qualified "
                f"regulatory affairs professionals for definitive determination.",
                stacklevel=2,
            )

        return {
            "change_type": change_type,
            "impact_score": total_score,
            "base_score": base_score,
            "component_score": component_score,
            "matched_components": matched_components,
            "data_readiness_score": data_readiness_score,
            "data_gaps": data_gaps,
            "risk_level": risk_level,
            "recommended_supplement_type": supplement_type,
            "recommended_supplement_label": type_def.get("label", supplement_type),
            "cfr_section": type_def.get("cfr_section", ""),
            "required_documentation": required_docs,
            "estimated_timeline": timeline,
            "assessment_date": datetime.now(timezone.utc).isoformat(),
            "disclaimer": REGULATORY_DISCLAIMER.strip(),
        }

    def _infer_change_type(self, description: str) -> str:
        """Infer change type from description text."""
        text = description.lower()
        if any(kw in text for kw in ("design", "material", "component", "dimension")):
            return "design_change"
        if any(kw in text for kw in ("manufactur", "facility", "supplier", "site")):
            return "manufacturing_change"
        if any(kw in text for kw in ("label", "ifu", "warning", "instruction")):
            return "labeling_change"
        if any(kw in text for kw in ("indication", "claim", "population")):
            return "indication_change"
        return "design_change"

    def _determine_required_docs(
        self,
        _change_type: str,
        score: int,
        components: List[str],
    ) -> List[Dict]:
        """Determine required documentation based on impact analysis."""
        docs = []

        # Always required
        docs.append({
            "document": "Change Summary",
            "priority": "REQUIRED",
            "description": "Detailed description of change and rationale",
        })
        docs.append({
            "document": "Risk Analysis Update (ISO 14971)",
            "priority": "REQUIRED",
            "description": "Updated risk analysis addressing the proposed change",
        })

        # Score-based requirements
        if score >= 20:
            docs.append({
                "document": "Comparison Table (Approved vs. Modified)",
                "priority": "REQUIRED",
                "description": "Side-by-side comparison of current and proposed specifications",
            })

        if score >= 30:
            docs.append({
                "document": "Bench Testing Report",
                "priority": "REQUIRED",
                "description": "Performance testing data for the modified device",
            })

        if score >= 40:
            docs.append({
                "document": "Clinical Evidence",
                "priority": "RECOMMENDED",
                "description": "Clinical data or literature review supporting change safety",
            })

        # Component-specific requirements
        comp_lower = [c.lower() for c in components]
        if any("biocompat" in c or "material" in c for c in comp_lower):
            docs.append({
                "document": "Biocompatibility Assessment (ISO 10993)",
                "priority": "REQUIRED",
                "description": "Biocompatibility evaluation for material changes",
            })
        if any("steriliz" in c for c in comp_lower):
            docs.append({
                "document": "Sterilization Validation (ISO 11135/11137)",
                "priority": "REQUIRED",
                "description": "Sterilization validation data for process/method changes",
            })
        if any("software" in c for c in comp_lower):
            docs.append({
                "document": "Software Validation Report (IEC 62304)",
                "priority": "REQUIRED",
                "description": "Software verification and validation for software changes",
            })

        return docs

    def _estimate_timeline(self, impact_score: int, data_score: int) -> Dict:
        """Estimate timeline based on impact and data readiness."""
        # Base preparation time (months)
        if impact_score >= 60:
            prep_months = 6
            review_months = 12
        elif impact_score >= 40:
            prep_months = 4
            review_months = 6
        elif impact_score >= 20:
            prep_months = 2
            review_months = 3
        else:
            prep_months = 1
            review_months = 1

        # Data gap penalty
        if data_score < 20:
            prep_months += 3
        elif data_score < 40:
            prep_months += 1

        total_months = prep_months + review_months

        return {
            "preparation_months": prep_months,
            "fda_review_months": review_months,
            "total_estimated_months": total_months,
            "data_readiness_factor": "READY" if data_score >= 40 else "NEEDS_DATA",
        }

    def compare_changes(
        self,
        changes: List[Dict],
    ) -> Dict:
        """Compare multiple proposed changes and prioritize.

        Args:
            changes: List of change dicts, each with change_type,
                    affected_components, and optional flags.

        Returns:
            Comparison report with individual assessments and summary.
        """
        assessments = []
        for change in changes:
            assessment = self.assess_impact(
                change_type=change.get("change_type", "design_change"),
                affected_components=change.get("affected_components"),
                has_performance_data=change.get("has_performance_data", False),
                has_clinical_data=change.get("has_clinical_data", False),
                change_description=change.get("description", ""),
            )
            assessment["change_label"] = change.get("label", change.get("description", ""))
            assessments.append(assessment)

        # Sort by impact score descending
        assessments.sort(key=lambda a: a["impact_score"], reverse=True)

        # Overall recommendation
        max_score = max(a["impact_score"] for a in assessments) if assessments else 0
        if max_score >= 60:
            overall = "PANEL_TRACK_REQUIRED"
        elif max_score >= 40:
            overall = "180_DAY_SUPPLEMENT"
        elif max_score >= 20:
            overall = "REAL_TIME_SUPPLEMENT"
        else:
            overall = "30_DAY_NOTICE_OR_ANNUAL"

        # Can changes be bundled?
        types_needed = set(a["recommended_supplement_type"] for a in assessments)
        bundling = (
            "All changes can be bundled into a single supplement."
            if len(types_needed) == 1
            else f"Changes require {len(types_needed)} different supplement types. Consider bundling strategy."
        )

        return {
            "total_changes": len(assessments),
            "assessments": assessments,
            "highest_impact_score": max_score,
            "overall_recommendation": overall,
            "supplement_types_needed": sorted(types_needed),
            "bundling_recommendation": bundling,
        }


# ==================================================================
# Supplement Package Generator
# ==================================================================

class SupplementPackageGenerator:
    """Generate supplement package outlines with required sections,
    templates, and checklists per 21 CFR 814.39.
    """

    def __init__(self):
        """Initialize with package section templates."""
        self._sections = PACKAGE_SECTIONS

    def generate(
        self,
        supplement_type: str,
        change_description: str = "",
        pma_number: str = "",
        applicant: str = "",
        device_name: str = "",
    ) -> Dict:
        """Generate a supplement package outline.

        Args:
            supplement_type: Type of supplement (180_day, real_time, etc.)
            change_description: Description of the change.
            pma_number: PMA number being supplemented.
            applicant: Applicant name.
            device_name: Device name.

        Returns:
            Package outline with sections, checklist, and cover letter template.
        """
        if supplement_type not in SUPPLEMENT_TYPES:
            supplement_type = "180_day"

        type_def = SUPPLEMENT_TYPES[supplement_type]
        sections = self._sections.get(supplement_type, self._sections["180_day"])

        # Build section checklist
        checklist = []
        for i, section in enumerate(sections, 1):
            checklist.append({
                "section_number": i,
                "section_title": section,
                "status": "NOT_STARTED",
                "required": True,
                "notes": "",
            })

        # Generate cover letter template
        cover_letter = self._generate_cover_letter(
            supplement_type, type_def, pma_number, applicant,
            device_name, change_description
        )

        # Generate regulatory references
        reg_refs = self._get_regulatory_references(supplement_type)

        return {
            "supplement_type": supplement_type,
            "supplement_label": type_def["label"],
            "cfr_section": type_def["cfr_section"],
            "review_days": type_def["review_days"],
            "pma_number": pma_number,
            "device_name": device_name,
            "applicant": applicant,
            "change_description": change_description,
            "total_sections": len(checklist),
            "sections": checklist,
            "cover_letter_template": cover_letter,
            "regulatory_references": reg_refs,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "This package outline is AI-generated guidance. "
                "Independent verification by qualified regulatory professionals "
                "is required before FDA submission."
            ),
        }

    def _generate_cover_letter(
        self,
        _supplement_type: str,
        type_def: Dict,
        pma_number: str,
        applicant: str,
        device_name: str,
        change_description: str,
    ) -> str:
        """Generate a cover letter template."""
        today = datetime.now().strftime("%B %d, %Y")
        cfr = type_def.get("cfr_section", "21 CFR 814.39")
        label = type_def.get("label", "PMA Supplement")

        return f"""[TEMPLATE - CUSTOMIZE BEFORE USE]

{today}

Food and Drug Administration
Center for Devices and Radiological Health
Document Mail Center - WO66-G609
10903 New Hampshire Avenue
Silver Spring, MD 20993-0002

RE: {label}
    PMA Number: {pma_number or '[PMA NUMBER]'}
    Device Name: {device_name or '[DEVICE NAME]'}
    Applicant: {applicant or '[APPLICANT NAME]'}

Dear Sir or Madam:

{applicant or '[APPLICANT NAME]'} hereby submits this {label} to the
above-referenced PMA in accordance with {cfr}.

Summary of Change:
{change_description or '[DESCRIBE THE PROPOSED CHANGE IN DETAIL]'}

This supplement contains the following:
[LIST ENCLOSED SECTIONS]

We certify that the information contained in this supplement is true,
accurate, and complete, to the best of our knowledge. We understand
that any misstatement of a material fact may subject us to criminal
prosecution.

Sincerely,

_____________________________
[NAME]
[TITLE]
[COMPANY]

Enclosures: [NUMBER] sections as described in Table of Contents

[END TEMPLATE]"""

    def _get_regulatory_references(self, supplement_type: str) -> List[Dict]:
        """Get relevant regulatory references for the supplement type."""
        common_refs = [
            {
                "reference": "21 CFR 814.39",
                "title": "PMA Supplements",
                "relevance": "Primary regulation for PMA supplement requirements",
            },
            {
                "reference": "21 CFR 814.37",
                "title": "PMA Amendment",
                "relevance": "Requirements for PMA amendments during review",
            },
        ]

        type_refs = {
            "panel_track": [
                {
                    "reference": "21 CFR 814.39(f)",
                    "title": "Panel-Track Supplement",
                    "relevance": "Supplement requiring advisory committee review",
                },
                {
                    "reference": "FDA Guidance: PMA Supplements",
                    "title": "Guidance for PMA Supplement Types",
                    "relevance": "Detailed guidance on Panel-Track requirements",
                },
            ],
            "180_day": [
                {
                    "reference": "21 CFR 814.39(d)",
                    "title": "180-Day Supplement",
                    "relevance": "Changes requiring 180-day review period",
                },
            ],
            "real_time": [
                {
                    "reference": "21 CFR 814.39(c)",
                    "title": "Real-Time Supplement",
                    "relevance": "Marketing permitted upon submission",
                },
            ],
            "30_day_notice": [
                {
                    "reference": "21 CFR 814.39(e)",
                    "title": "30-Day Notice",
                    "relevance": "Minor changes, marketing after 30-day acknowledgment",
                },
            ],
            "annual_report": [
                {
                    "reference": "21 CFR 814.84",
                    "title": "PMA Annual Reports",
                    "relevance": "Requirements for PMA annual reporting",
                },
            ],
        }

        return common_refs + type_refs.get(supplement_type, [])

    def generate_batch(
        self,
        changes: List[Dict],
        pma_number: str = "",
    ) -> List[Dict]:
        """Generate package outlines for multiple changes.

        Args:
            changes: List of change dicts with supplement_type and description.
            pma_number: PMA number.

        Returns:
            List of package outlines.
        """
        packages = []
        for change in changes:
            pkg = self.generate(
                supplement_type=change.get("supplement_type", "180_day"),
                change_description=change.get("description", ""),
                pma_number=pma_number,
            )
            packages.append(pkg)
        return packages


# ==================================================================
# CLI Entry Point
# ==================================================================

def _format_classification(result: Dict) -> str:
    """Format classification result as text."""
    lines = [
        "=" * 60,
        "PMA SUPPLEMENT TYPE CLASSIFICATION",
        "=" * 60,
        f"Type:       {result.get('label', 'Unknown')}",
        f"CFR:        {result.get('cfr_section', '')}",
        f"Confidence: {result.get('confidence_label', '')} ({result.get('confidence', 0):.1%})",
        f"Risk Level: {result.get('risk_level', 'unknown')}",
        f"Review:     {result.get('review_days', 'N/A')} days",
        "",
        f"Rationale:  {result.get('rationale', '')}",
    ]

    alts = result.get("alternatives", [])
    if alts:
        lines.append("")
        lines.append("Alternative Types Considered:")
        for alt in alts:
            lines.append(f"  - {alt['label']} (confidence: {alt['confidence']:.1%})")

    lines.extend(["", "-" * 60])
    lines.append(REGULATORY_DISCLAIMER.strip())
    lines.extend(["=" * 60])
    return "\n".join(lines)


def _format_impact(result: Dict) -> str:
    """Format impact assessment as text."""
    lines = [
        "=" * 60,
        "CHANGE IMPACT ASSESSMENT",
        "=" * 60,
        f"Change Type:      {result.get('change_type', 'unknown')}",
        f"Impact Score:     {result.get('impact_score', 0)}/100",
        f"Risk Level:       {result.get('risk_level', 'unknown')}",
        f"Recommended Type: {result.get('recommended_supplement_label', 'unknown')}",
        f"CFR:              {result.get('cfr_section', '')}",
        "",
    ]

    timeline = result.get("estimated_timeline", {})
    if timeline:
        lines.append(f"Estimated Timeline:")
        lines.append(f"  Preparation:  {timeline.get('preparation_months', 0)} months")
        lines.append(f"  FDA Review:   {timeline.get('fda_review_months', 0)} months")
        lines.append(f"  Total:        {timeline.get('total_estimated_months', 0)} months")

    gaps = result.get("data_gaps", [])
    if gaps:
        lines.append("")
        lines.append("Data Gaps:")
        for gap in gaps:
            lines.append(f"  - {gap}")

    docs = result.get("required_documentation", [])
    if docs:
        lines.append("")
        lines.append("Required Documentation:")
        for doc in docs:
            lines.append(f"  [{doc['priority']}] {doc['document']}")

    lines.extend(["", "-" * 60])
    lines.append(REGULATORY_DISCLAIMER.strip())
    lines.extend(["=" * 60])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="PMA Supplement Enhancement Tools (FDA-65)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # classify command
    classify_p = subparsers.add_parser("classify", help="Classify change into supplement type")
    classify_p.add_argument("description", help="Change description text")
    classify_p.add_argument("--clinical-data", action="store_true")
    classify_p.add_argument("--performance-data", action="store_true")
    classify_p.add_argument("--json", action="store_true")

    # decide command
    decide_p = subparsers.add_parser("decide", help="Walk supplement decision tree")
    decide_p.add_argument("--change", required=True, help="Change description")
    decide_p.add_argument("--design", action="store_true")
    decide_p.add_argument("--manufacturing", action="store_true")
    decide_p.add_argument("--labeling", action="store_true")
    decide_p.add_argument("--clinical-data", action="store_true")
    decide_p.add_argument("--affects-safety", action="store_true")
    decide_p.add_argument("--requires-panel", action="store_true")
    decide_p.add_argument("--json", action="store_true")

    # impact command
    impact_p = subparsers.add_parser("impact", help="Assess change impact")
    impact_p.add_argument("--type", required=True, help="Change type")
    impact_p.add_argument("--components", nargs="*", help="Affected components")
    impact_p.add_argument("--description", default="", help="Change description")
    impact_p.add_argument("--json", action="store_true")

    # package command
    package_p = subparsers.add_parser("package", help="Generate supplement package")
    package_p.add_argument("--type", required=True, help="Supplement type")
    package_p.add_argument("--pma", default="", help="PMA number")
    package_p.add_argument("--description", default="", help="Change description")
    package_p.add_argument("--json", action="store_true")

    args = parser.parse_args()

    # Print disclaimer to stderr for all scoring commands
    if args.command in ("classify", "decide", "impact"):
        print(REGULATORY_DISCLAIMER, file=sys.stderr)

    if args.command == "classify":
        classifier = SupplementTypeClassifier()
        result = classifier.classify(
            args.description,
            has_clinical_data=args.clinical_data,
            has_performance_data=args.performance_data,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_format_classification(result))

    elif args.command == "decide":
        tree = SupplementDecisionTree()
        result = tree.evaluate(
            change_description=args.change,
            is_design_change=args.design,
            is_manufacturing_change=args.manufacturing,
            is_labeling_change=args.labeling,
            has_clinical_data=args.clinical_data,
            affects_safety=args.affects_safety,
            requires_panel=args.requires_panel,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Recommendation: {result.get('label', 'Unknown')}")
            print(f"CFR: {result.get('cfr_section', '')}")
            print(f"Rationale: {result.get('rationale', '')}")
            print(f"Timeline: ~{result.get('estimated_timeline_months', 'N/A')} months")
            path = result.get("decision_path", [])
            if path:
                print(f"Decision path: {' -> '.join(path)}")

    elif args.command == "impact":
        assessor = ChangeImpactAssessor()
        result = assessor.assess_impact(
            change_type=args.type,
            affected_components=args.components,
            change_description=args.description,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_format_impact(result))

    elif args.command == "package":
        generator = SupplementPackageGenerator()
        result = generator.generate(
            supplement_type=args.type,
            change_description=args.description,
            pma_number=args.pma,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Package: {result['supplement_label']}")
            print(f"Sections: {result['total_sections']}")
            for s in result["sections"]:
                print(f"  {s['section_number']}. {s['section_title']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
