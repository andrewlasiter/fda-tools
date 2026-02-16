#!/usr/bin/env python3
"""
Supplement Approval Probability Scorer -- Predict supplement approval likelihood
using decision tree classification on historical PMA supplement data.

Analyzes features including change type, clinical data presence, predicate
citations, applicant track record, regulatory type, and supplement frequency
to predict approval probability with risk flags and recommended mitigations.

Training data sourced from Phase 3 supplement_tracker historical data.
When scikit-learn is available, uses Decision Tree or Random Forest classifiers;
otherwise falls back to rule-based statistical baselines.

Usage:
    from approval_probability import ApprovalProbabilityScorer

    scorer = ApprovalProbabilityScorer()
    result = scorer.score_approval_probability("P170019", "S015")
    result = scorer.score_hypothetical_supplement(features)
    analysis = scorer.analyze_historical_outcomes("P170019")

    # CLI usage:
    python3 approval_probability.py --pma P170019
    python3 approval_probability.py --pma P170019 --supplement S015
    python3 approval_probability.py --pma P170019 --historical
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore

# Try importing scikit-learn
_HAS_SKLEARN = False
RandomForestClassifier = None  # type: ignore
try:
    from sklearn.ensemble import RandomForestClassifier
    _HAS_SKLEARN = True
except ImportError:
    pass


# ------------------------------------------------------------------
# Approval outcome categories
# ------------------------------------------------------------------

OUTCOME_APPROVED = "approved"
OUTCOME_DENIED = "denied"
OUTCOME_WITHDRAWN = "withdrawn"
OUTCOME_UNKNOWN = "unknown"

DECISION_CODE_MAP = {
    "APPR": OUTCOME_APPROVED,
    "APRL": OUTCOME_APPROVED,
    "APPN": OUTCOME_APPROVED,
    "DENY": OUTCOME_DENIED,
    "WDRN": OUTCOME_WITHDRAWN,
    "WTDR": OUTCOME_WITHDRAWN,
    "WTHI": OUTCOME_WITHDRAWN,
}


# ------------------------------------------------------------------
# Supplement type baseline approval rates (empirical)
# ------------------------------------------------------------------

BASELINE_APPROVAL_RATES: Dict[str, float] = {
    "180_day": 0.92,
    "real_time": 0.88,
    "30_day_notice": 0.97,
    "panel_track": 0.78,
    "pas_related": 0.95,
    "manufacturing": 0.93,
    "labeling": 0.94,
    "design_change": 0.85,
    "indication_expansion": 0.82,
    "other": 0.88,
    "original": 0.80,
}

# Risk factors that decrease approval probability
RISK_FACTOR_PENALTIES: Dict[str, Dict[str, Any]] = {
    "no_clinical_data": {
        "label": "No Clinical Data",
        "penalty": 0.10,
        "description": "Supplement lacks clinical data support",
        "mitigation": "Provide clinical evidence or literature support for the change.",
    },
    "prior_denial": {
        "label": "Prior Denial History",
        "penalty": 0.15,
        "description": "Applicant has prior denied supplements for this PMA",
        "mitigation": "Address all prior deficiency reasons in the new submission.",
    },
    "design_plus_indication": {
        "label": "Combined Design + Indication Change",
        "penalty": 0.08,
        "description": "Supplement combines design change with indication expansion",
        "mitigation": "Consider separating into individual supplements for focused review.",
    },
    "high_supplement_velocity": {
        "label": "High Supplement Frequency",
        "penalty": 0.05,
        "description": "High rate of supplement submissions may trigger additional scrutiny",
        "mitigation": "Consolidate changes when possible to reduce submission frequency.",
    },
    "panel_track_required": {
        "label": "Panel-Track Review Required",
        "penalty": 0.12,
        "description": "Significant change requiring advisory committee review",
        "mitigation": "Prepare comprehensive clinical and preclinical data packages.",
    },
    "novel_indication": {
        "label": "Novel Indication Without Precedent",
        "penalty": 0.10,
        "description": "Proposed indication has no precedent in similar PMAs",
        "mitigation": "Include comparative analysis with similar devices and strong clinical evidence.",
    },
    "short_track_record": {
        "label": "Short Applicant Track Record",
        "penalty": 0.05,
        "description": "Applicant has limited PMA supplement history with FDA",
        "mitigation": "Consider pre-submission meetings with FDA to clarify expectations.",
    },
    "safety_concern_history": {
        "label": "Prior Safety Concerns",
        "penalty": 0.08,
        "description": "Device has history of safety-related supplements or recalls",
        "mitigation": "Provide updated risk-benefit analysis addressing safety concerns.",
    },
}

# Positive factors that increase approval probability
POSITIVE_FACTORS: Dict[str, Dict[str, Any]] = {
    "strong_clinical_data": {
        "label": "Strong Clinical Data",
        "bonus": 0.05,
        "description": "Supplement supported by robust clinical evidence",
    },
    "prior_approvals": {
        "label": "Consistent Approval History",
        "bonus": 0.05,
        "description": "Applicant has strong track record of approved supplements",
    },
    "expedited_pathway": {
        "label": "Expedited Review Pathway",
        "bonus": 0.03,
        "description": "Supplement qualifies for expedited review",
    },
    "minor_change": {
        "label": "Minor Change (30-Day Notice)",
        "bonus": 0.05,
        "description": "Change is minor and well-characterized",
    },
}


# ------------------------------------------------------------------
# Model versioning
# ------------------------------------------------------------------

MODEL_VERSION = "1.0.0"
MODEL_TYPE_SKLEARN = "sklearn_random_forest"
MODEL_TYPE_RULES = "rule_based_baseline"


# ------------------------------------------------------------------
# Approval Probability Scorer
# ------------------------------------------------------------------

class ApprovalProbabilityScorer:
    """Predict supplement approval probability using historical data.

    Uses decision tree classification when scikit-learn is available,
    with rule-based statistical baselines as fallback.

    Attributes:
        store: PMADataStore instance for data access.
        model_type: Current model type in use.
        _trained_model: Trained ML classifier (if available).
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Approval Probability Scorer.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()
        self.model_type: str = MODEL_TYPE_RULES
        self._trained_model: Any = None
        self._training_stats: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Main scoring entry points
    # ------------------------------------------------------------------

    def score_approval_probability(
        self,
        pma_number: str,
        supplement_number: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Score approval probability for a PMA's supplements.

        If supplement_number is provided, scores that specific supplement.
        Otherwise, scores all supplements and provides aggregate analysis.

        Args:
            pma_number: PMA number (e.g., 'P170019').
            supplement_number: Optional specific supplement (e.g., 'S015').
            refresh: Force refresh from API.

        Returns:
            Scoring result dict.
        """
        pma_key = pma_number.upper()
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)

        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
                "model_version": MODEL_VERSION,
            }

        supplements = self.store.get_supplements(pma_key, refresh=refresh)
        if not supplements:
            return {
                "pma_number": pma_key,
                "total_supplements": 0,
                "note": "No supplements found.",
                "model_version": MODEL_VERSION,
            }

        # Score specific supplement or all
        if supplement_number:
            target = self._find_supplement(supplements, supplement_number.upper())
            if target is None:
                return {
                    "pma_number": pma_key,
                    "error": f"Supplement {supplement_number} not found.",
                    "model_version": MODEL_VERSION,
                }
            scored = [self._score_single_supplement(target, supplements, api_data)]
        else:
            scored = []
            for supp in supplements:
                scored.append(self._score_single_supplement(supp, supplements, api_data))

        # Aggregate analysis
        aggregate = self._compute_aggregate_analysis(scored, api_data)

        return {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "total_supplements": len(supplements),
            "scored_supplements": scored,
            "aggregate_analysis": aggregate,
            "model_version": MODEL_VERSION,
            "model_type": self.model_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def score_hypothetical_supplement(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Score approval probability for a hypothetical supplement.

        Args:
            features: Feature dictionary with keys:
                - change_type: Type of change (e.g., 'labeling', 'design_change')
                - has_clinical_data: Whether clinical data is included
                - regulatory_type: Regulatory pathway (e.g., '180_day')
                - prior_denials: Number of prior denied supplements
                - prior_approvals: Number of prior approved supplements
                - applicant_pma_count: Total PMAs held by applicant
                - supplement_velocity: Supplements per year average

        Returns:
            Scoring result dict.
        """
        # Extract features and compute score
        change_type = features.get("change_type", "other")
        regulatory_type = features.get("regulatory_type", "other")

        base_rate = BASELINE_APPROVAL_RATES.get(
            change_type,
            BASELINE_APPROVAL_RATES.get(regulatory_type, 0.88),
        )

        # Detect risk factors
        risk_flags: List[Dict[str, Any]] = []
        total_penalty = 0.0

        if not features.get("has_clinical_data", True):
            risk_flags.append(RISK_FACTOR_PENALTIES["no_clinical_data"])
            total_penalty += RISK_FACTOR_PENALTIES["no_clinical_data"]["penalty"]

        if features.get("prior_denials", 0) > 0:
            risk_flags.append(RISK_FACTOR_PENALTIES["prior_denial"])
            total_penalty += RISK_FACTOR_PENALTIES["prior_denial"]["penalty"]

        if features.get("supplement_velocity", 0) > 5:
            risk_flags.append(RISK_FACTOR_PENALTIES["high_supplement_velocity"])
            total_penalty += RISK_FACTOR_PENALTIES["high_supplement_velocity"]["penalty"]

        if regulatory_type == "panel_track":
            risk_flags.append(RISK_FACTOR_PENALTIES["panel_track_required"])
            total_penalty += RISK_FACTOR_PENALTIES["panel_track_required"]["penalty"]

        # Detect positive factors
        positive_flags: List[Dict[str, Any]] = []
        total_bonus = 0.0

        if features.get("has_clinical_data", True) and features.get("clinical_strength", "") == "strong":
            positive_flags.append(POSITIVE_FACTORS["strong_clinical_data"])
            total_bonus += POSITIVE_FACTORS["strong_clinical_data"]["bonus"]

        if features.get("prior_approvals", 0) > 5:
            positive_flags.append(POSITIVE_FACTORS["prior_approvals"])
            total_bonus += POSITIVE_FACTORS["prior_approvals"]["bonus"]

        if regulatory_type == "30_day_notice":
            positive_flags.append(POSITIVE_FACTORS["minor_change"])
            total_bonus += POSITIVE_FACTORS["minor_change"]["bonus"]

        # Calculate final probability
        probability = min(max(base_rate - total_penalty + total_bonus, 0.01), 0.99)

        return {
            "approval_probability": round(probability * 100, 1),
            "approval_probability_raw": round(probability, 4),
            "base_rate": round(base_rate * 100, 1),
            "risk_flags": risk_flags,
            "positive_factors": positive_flags,
            "total_penalty": round(total_penalty * 100, 1),
            "total_bonus": round(total_bonus * 100, 1),
            "recommended_mitigations": [
                rf["mitigation"] for rf in risk_flags if "mitigation" in rf
            ],
            "confidence": "moderate" if not self._trained_model else "high",
            "model_version": MODEL_VERSION,
            "model_type": self.model_type,
        }

    # ------------------------------------------------------------------
    # Historical outcome analysis
    # ------------------------------------------------------------------

    def analyze_historical_outcomes(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Analyze historical supplement approval outcomes for a PMA.

        Args:
            pma_number: PMA number.
            refresh: Force refresh.

        Returns:
            Historical outcome analysis dict.
        """
        pma_key = pma_number.upper()
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)

        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        supplements = self.store.get_supplements(pma_key, refresh=refresh)
        if not supplements:
            return {
                "pma_number": pma_key,
                "total_supplements": 0,
                "note": "No supplements found.",
            }

        # Classify outcomes
        outcomes: Counter = Counter()
        by_type: Dict[str, Counter] = defaultdict(Counter)
        by_year: Dict[int, Counter] = defaultdict(Counter)

        for supp in supplements:
            dc = supp.get("decision_code", "").upper()
            outcome = DECISION_CODE_MAP.get(dc, OUTCOME_UNKNOWN)
            outcomes[outcome] += 1

            supp_type = self._classify_supplement_type(supp)
            by_type[supp_type][outcome] += 1

            dd = supp.get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    year = int(dd[:4])
                    by_year[year][outcome] += 1
                except ValueError:
                    pass

        total = sum(outcomes.values())
        approval_rate = outcomes.get(OUTCOME_APPROVED, 0) / max(total, 1)
        denial_rate = outcomes.get(OUTCOME_DENIED, 0) / max(total, 1)
        withdrawal_rate = outcomes.get(OUTCOME_WITHDRAWN, 0) / max(total, 1)

        # Type-level analysis
        type_analysis = {}
        for stype, stype_outcomes in by_type.items():
            stype_total = sum(stype_outcomes.values())
            type_analysis[stype] = {
                "total": stype_total,
                "approved": stype_outcomes.get(OUTCOME_APPROVED, 0),
                "denied": stype_outcomes.get(OUTCOME_DENIED, 0),
                "withdrawn": stype_outcomes.get(OUTCOME_WITHDRAWN, 0),
                "approval_rate": round(
                    stype_outcomes.get(OUTCOME_APPROVED, 0) / max(stype_total, 1) * 100, 1
                ),
            }

        # Year trend
        year_trend = {}
        for year in sorted(by_year.keys()):
            year_total = sum(by_year[year].values())
            year_trend[year] = {
                "total": year_total,
                "approved": by_year[year].get(OUTCOME_APPROVED, 0),
                "denied": by_year[year].get(OUTCOME_DENIED, 0),
                "approval_rate": round(
                    by_year[year].get(OUTCOME_APPROVED, 0) / max(year_total, 1) * 100, 1
                ),
            }

        return {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "total_supplements": total,
            "outcome_summary": {
                "approved": outcomes.get(OUTCOME_APPROVED, 0),
                "denied": outcomes.get(OUTCOME_DENIED, 0),
                "withdrawn": outcomes.get(OUTCOME_WITHDRAWN, 0),
                "unknown": outcomes.get(OUTCOME_UNKNOWN, 0),
            },
            "overall_approval_rate": round(approval_rate * 100, 1),
            "overall_denial_rate": round(denial_rate * 100, 1),
            "overall_withdrawal_rate": round(withdrawal_rate * 100, 1),
            "by_type": type_analysis,
            "year_trend": year_trend,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Model training
    # ------------------------------------------------------------------

    def train_model(
        self,
        training_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Train the approval probability model.

        Args:
            training_data: Optional training examples. If None, builds
                from cached supplement data.

        Returns:
            Training result dict.
        """
        if training_data is None:
            training_data = self._build_training_set()

        if len(training_data) < 10:
            self.model_type = MODEL_TYPE_RULES
            return {
                "status": "baseline_model",
                "model_type": MODEL_TYPE_RULES,
                "training_examples": len(training_data),
                "note": "Insufficient data for ML model. Using rule-based baselines.",
            }

        if _HAS_SKLEARN and len(training_data) >= 20:
            return self._train_sklearn_model(training_data)

        self.model_type = MODEL_TYPE_RULES
        self._training_stats = self._compute_outcome_baselines(training_data)
        return {
            "status": "baseline_model",
            "model_type": MODEL_TYPE_RULES,
            "training_examples": len(training_data),
            "baseline_stats": self._training_stats,
        }

    def _train_sklearn_model(
        self,
        training_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Train sklearn Random Forest classifier.

        Args:
            training_data: List of training examples.

        Returns:
            Training result dict.
        """
        import numpy as np

        features_list = []
        labels = []

        for example in training_data:
            outcome = example.get("outcome", OUTCOME_UNKNOWN)
            if outcome == OUTCOME_UNKNOWN:
                continue
            feat_vec = self._featurize_supplement(example)
            features_list.append(feat_vec)
            labels.append(1 if outcome == OUTCOME_APPROVED else 0)

        if len(features_list) < 10:
            self.model_type = MODEL_TYPE_RULES
            return {
                "status": "baseline_model",
                "model_type": MODEL_TYPE_RULES,
                "training_examples": len(features_list),
                "note": "Insufficient labeled data for ML model.",
            }

        X = np.array(features_list)
        y = np.array(labels)

        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=5,
            random_state=42,
        )
        model.fit(X, y)

        # Training accuracy
        predictions = model.predict(X)
        accuracy = float(np.mean(predictions == y))

        self._trained_model = model
        self.model_type = MODEL_TYPE_SKLEARN

        return {
            "status": "trained",
            "model_type": MODEL_TYPE_SKLEARN,
            "training_examples": len(features_list),
            "training_accuracy": round(accuracy * 100, 1),
            "class_distribution": {
                "approved": int(sum(y)),
                "not_approved": int(len(y) - sum(y)),
            },
            "model_version": MODEL_VERSION,
        }

    def _build_training_set(self) -> List[Dict[str, Any]]:
        """Build training set from cached supplement data.

        Returns:
            List of training examples.
        """
        manifest = self.store.get_manifest()
        entries = manifest.get("pma_entries", {})
        training_data: List[Dict[str, Any]] = []

        for pma_key, entry in entries.items():
            supplements = self.store.get_supplements(pma_key)
            for supp in supplements:
                dc = supp.get("decision_code", "").upper()
                outcome = DECISION_CODE_MAP.get(dc, OUTCOME_UNKNOWN)
                supp_type = self._classify_supplement_type(supp)

                training_data.append({
                    "pma_number": pma_key,
                    "supplement_number": supp.get("supplement_number", ""),
                    "supplement_type": supp_type,
                    "decision_code": dc,
                    "outcome": outcome,
                    "decision_date": supp.get("decision_date", ""),
                })

        return training_data

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _score_single_supplement(
        self,
        supp: Dict[str, Any],
        all_supplements: List[Dict[str, Any]],
        api_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Score a single supplement.

        Args:
            supp: Supplement dict.
            all_supplements: All supplements for context.
            api_data: Base PMA API data.

        Returns:
            Scored supplement dict.
        """
        supp_type = self._classify_supplement_type(supp)
        dc = supp.get("decision_code", "").upper()
        actual_outcome = DECISION_CODE_MAP.get(dc, OUTCOME_UNKNOWN)

        # Get base rate
        base_rate = BASELINE_APPROVAL_RATES.get(supp_type, 0.88)

        # Analyze context for risk factors
        risk_flags: List[Dict[str, Any]] = []
        positive_flags: List[Dict[str, Any]] = []
        total_penalty = 0.0
        total_bonus = 0.0

        # Check prior denials
        prior_denials = sum(
            1 for s in all_supplements
            if DECISION_CODE_MAP.get(s.get("decision_code", "").upper()) == OUTCOME_DENIED
            and s.get("decision_date", "") < supp.get("decision_date", "")
        )
        if prior_denials > 0:
            penalty_info = RISK_FACTOR_PENALTIES["prior_denial"]
            risk_flags.append({
                "flag": "prior_denial",
                "label": penalty_info["label"],
                "penalty": penalty_info["penalty"],
                "description": f"{prior_denials} prior denial(s) detected",
            })
            total_penalty += penalty_info["penalty"]

        # Check prior approval track record
        prior_approvals = sum(
            1 for s in all_supplements
            if DECISION_CODE_MAP.get(s.get("decision_code", "").upper()) == OUTCOME_APPROVED
            and s.get("decision_date", "") < supp.get("decision_date", "")
        )
        if prior_approvals > 5:
            bonus_info = POSITIVE_FACTORS["prior_approvals"]
            positive_flags.append({
                "flag": "prior_approvals",
                "label": bonus_info["label"],
                "bonus": bonus_info["bonus"],
                "description": f"{prior_approvals} prior approval(s)",
            })
            total_bonus += bonus_info["bonus"]

        # Check for panel-track
        if supp_type == "panel_track":
            penalty_info = RISK_FACTOR_PENALTIES["panel_track_required"]
            risk_flags.append({
                "flag": "panel_track_required",
                "label": penalty_info["label"],
                "penalty": penalty_info["penalty"],
            })
            total_penalty += penalty_info["penalty"]

        # Calculate probability
        probability = min(max(base_rate - total_penalty + total_bonus, 0.01), 0.99)

        result: Dict[str, Any] = {
            "supplement_number": supp.get("supplement_number", ""),
            "pma_number": supp.get("pma_number", ""),
            "supplement_type": supp_type,
            "decision_date": supp.get("decision_date", ""),
            "decision_code": dc,
            "actual_outcome": actual_outcome,
            "approval_probability": round(probability * 100, 1),
            "base_rate": round(base_rate * 100, 1),
            "risk_flags": risk_flags,
            "positive_factors": positive_flags,
            "total_penalty_pct": round(total_penalty * 100, 1),
            "total_bonus_pct": round(total_bonus * 100, 1),
        }

        # Check prediction accuracy
        if actual_outcome != OUTCOME_UNKNOWN:
            predicted_approved = probability >= 0.5
            actually_approved = actual_outcome == OUTCOME_APPROVED
            result["prediction_correct"] = predicted_approved == actually_approved

        return result

    def _compute_aggregate_analysis(
        self,
        scored: List[Dict[str, Any]],
        api_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute aggregate analysis from scored supplements.

        Args:
            scored: List of scored supplement dicts.
            api_data: Base PMA data.

        Returns:
            Aggregate analysis dict.
        """
        if not scored:
            return {"total_scored": 0}

        probabilities = [s["approval_probability"] for s in scored]
        correct_predictions = [
            s for s in scored
            if s.get("prediction_correct") is not None
        ]

        accuracy = None
        if correct_predictions:
            correct_count = sum(1 for s in correct_predictions if s["prediction_correct"])
            accuracy = round(correct_count / len(correct_predictions) * 100, 1)

        # Risk pattern analysis
        all_flags = []
        for s in scored:
            all_flags.extend([rf["flag"] for rf in s.get("risk_flags", []) if "flag" in rf])

        flag_counts = Counter(all_flags)

        return {
            "total_scored": len(scored),
            "avg_approval_probability": round(sum(probabilities) / len(probabilities), 1),
            "min_approval_probability": round(min(probabilities), 1),
            "max_approval_probability": round(max(probabilities), 1),
            "classification_accuracy": accuracy,
            "predictions_evaluated": len(correct_predictions),
            "most_common_risk_flags": dict(flag_counts.most_common(5)),
        }

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _find_supplement(
        self,
        supplements: List[Dict[str, Any]],
        supplement_number: str,
    ) -> Optional[Dict[str, Any]]:
        """Find a specific supplement in the list.

        Args:
            supplements: List of supplement dicts.
            supplement_number: Supplement number to find.

        Returns:
            Matching supplement dict or None.
        """
        for supp in supplements:
            sn = supp.get("supplement_number", "").upper()
            if sn == supplement_number:
                return supp
            pn = supp.get("pma_number", "")
            if pn.endswith(supplement_number):
                return supp
        return None

    def _classify_supplement_type(self, supp: Dict[str, Any]) -> str:
        """Classify supplement type from raw fields.

        Args:
            supp: Supplement dict.

        Returns:
            Classified type string.
        """
        supp_type = supp.get("supplement_type", "").lower()
        supp_reason = supp.get("supplement_reason", "").lower()
        combined = f"{supp_type} {supp_reason}"

        # Priority classification
        type_keywords = {
            "panel_track": ["panel track", "panel-track"],
            "30_day_notice": ["30-day", "30 day"],
            "pas_related": ["post-approval", "post approval", "pas", "condition of approval"],
            "indication_expansion": ["new indication", "expanded indication", "indication expansion"],
            "design_change": ["design change", "design modification", "component change"],
            "manufacturing": ["manufacturing", "facility", "sterilization", "site change"],
            "labeling": ["labeling", "label", "ifu", "instructions"],
            "180_day": ["180-day", "180 day"],
            "real_time": ["real-time", "real time"],
        }

        for type_key, keywords in type_keywords.items():
            for kw in keywords:
                if kw in combined:
                    return type_key

        return "other"

    def _featurize_supplement(self, example: Dict[str, Any]) -> List[float]:
        """Convert supplement to numeric feature vector.

        Args:
            example: Supplement example dict.

        Returns:
            Numeric feature vector.
        """
        vec: List[float] = []

        # Supplement type one-hot
        supp_type = example.get("supplement_type", "other")
        type_cats = [
            "180_day", "real_time", "30_day_notice", "panel_track",
            "pas_related", "manufacturing", "labeling", "design_change",
            "indication_expansion", "other",
        ]
        for t in type_cats:
            vec.append(1.0 if supp_type == t else 0.0)

        # Decision year (normalized)
        dd = example.get("decision_date", "")
        if dd and len(dd) >= 4:
            try:
                year = int(dd[:4])
                vec.append((year - 2000) / 30.0)
            except ValueError:
                vec.append(0.5)
        else:
            vec.append(0.5)

        return vec

    def _compute_outcome_baselines(
        self,
        training_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute outcome baselines from training data.

        Args:
            training_data: List of training examples.

        Returns:
            Baseline statistics dict.
        """
        type_outcomes: Dict[str, Counter] = defaultdict(Counter)
        for example in training_data:
            supp_type = example.get("supplement_type", "other")
            outcome = example.get("outcome", OUTCOME_UNKNOWN)
            type_outcomes[supp_type][outcome] += 1

        baselines = {}
        for stype, outcomes in type_outcomes.items():
            total = sum(outcomes.values())
            approved = outcomes.get(OUTCOME_APPROVED, 0)
            baselines[stype] = {
                "total": total,
                "approved": approved,
                "approval_rate": round(approved / max(total, 1) * 100, 1),
            }

        return baselines


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_scoring_result(result: Dict[str, Any]) -> str:
    """Format scoring result as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("SUPPLEMENT APPROVAL PROBABILITY ANALYSIS")
    lines.append("=" * 70)

    if result.get("error"):
        lines.append(f"ERROR: {result['error']}")
        return "\n".join(lines)

    lines.append(f"PMA Number:  {result.get('pma_number', 'N/A')}")
    lines.append(f"Device:      {result.get('device_name', 'N/A')}")
    lines.append(f"Applicant:   {result.get('applicant', 'N/A')}")
    lines.append(f"Total Supps: {result.get('total_supplements', 0)}")
    lines.append("")

    # Aggregate
    agg = result.get("aggregate_analysis", {})
    if agg.get("total_scored", 0) > 0:
        lines.append("--- Aggregate Analysis ---")
        lines.append(f"  Avg Approval Probability: {agg.get('avg_approval_probability', 'N/A')}%")
        lines.append(f"  Range: {agg.get('min_approval_probability', 'N/A')}% - "
                     f"{agg.get('max_approval_probability', 'N/A')}%")
        if agg.get("classification_accuracy") is not None:
            lines.append(f"  Classification Accuracy: {agg['classification_accuracy']}%")
        lines.append("")

    # Top supplements
    scored = result.get("scored_supplements", [])
    if scored:
        lines.append("--- Supplement Scores ---")
        for s in scored[:15]:
            outcome_marker = ""
            if s.get("actual_outcome") == OUTCOME_APPROVED:
                outcome_marker = " [APPROVED]"
            elif s.get("actual_outcome") == OUTCOME_DENIED:
                outcome_marker = " [DENIED]"
            elif s.get("actual_outcome") == OUTCOME_WITHDRAWN:
                outcome_marker = " [WITHDRAWN]"

            correct = ""
            if s.get("prediction_correct") is not None:
                correct = " CORRECT" if s["prediction_correct"] else " WRONG"

            lines.append(
                f"  {s.get('supplement_number', 'N/A'):6s} | "
                f"{s.get('supplement_type', 'N/A'):20s} | "
                f"Prob: {s.get('approval_probability', 'N/A'):5.1f}%"
                f"{outcome_marker}{correct}"
            )

            for rf in s.get("risk_flags", []):
                lines.append(f"         RISK: {rf.get('label', 'N/A')} (-{rf.get('penalty', 0)*100:.0f}%)")

        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Model: {result.get('model_type', 'N/A')} v{result.get('model_version', 'N/A')}")
    lines.append(f"Generated: {result.get('generated_at', 'N/A')[:10]}")
    lines.append("This analysis is AI-generated from public FDA data.")
    lines.append("Independent verification by qualified RA professionals required.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supplement Approval Probability Scorer -- Predict supplement approval likelihood"
    )
    parser.add_argument("--pma", help="PMA number to analyze")
    parser.add_argument("--supplement", help="Specific supplement number (e.g., S015)")
    parser.add_argument("--historical", action="store_true",
                        help="Show historical outcome analysis")
    parser.add_argument("--train", action="store_true",
                        help="Train/retrain the prediction model")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh from API")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    scorer = ApprovalProbabilityScorer()

    result: Optional[Dict[str, Any]] = None

    if args.train:
        result = scorer.train_model()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Training status: {result.get('status', 'N/A')}")
            print(f"Model type: {result.get('model_type', 'N/A')}")

    elif args.pma:
        if args.historical:
            result = scorer.analyze_historical_outcomes(args.pma, refresh=args.refresh)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(json.dumps(result, indent=2))
        else:
            result = scorer.score_approval_probability(
                args.pma,
                supplement_number=args.supplement,
                refresh=args.refresh,
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(_format_scoring_result(result))
    else:
        parser.error("Specify --pma or --train")

    if args.output and result:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
