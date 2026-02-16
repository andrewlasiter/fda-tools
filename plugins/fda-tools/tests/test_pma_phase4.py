"""
Comprehensive test suite for PMA Advanced Analytics & Machine Learning -- Phase 4 (TICKET-003).

Tests cover all Phase 4 modules:
    1. TestReviewTimePredictor -- review_time_predictor.py ML prediction engine
    2. TestApprovalProbability -- approval_probability.py decision tree classifier
    3. TestMAUDEComparison -- maude_comparison.py peer comparison engine
    4. TestCompetitiveDashboard -- competitive_dashboard.py market intelligence
    5. TestPhase4Integration -- Cross-module integration and Phase 0-3 compatibility

Target: 60+ tests covering all Phase 4 acceptance criteria.
All tests run offline (no network access) using mocks.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ============================================================
# Shared test fixtures and sample data
# ============================================================

SAMPLE_PMA_DATA = {
    "pma_number": "P170019",
    "applicant": "FOUNDATION MEDICINE, INC.",
    "device_name": "FoundationOne CDx",
    "generic_name": "Next Generation Sequencing System",
    "product_code": "NMH",
    "decision_date": "20171130",
    "decision_code": "APPR",
    "advisory_committee": "CH",
    "advisory_committee_description": "Clinical Chemistry",
    "ao_statement": "Condition of approval: post-approval study required.",
    "supplement_count": 10,
    "expedited_review_flag": "N",
}

SAMPLE_PMA_DATA_EXPEDITED = {
    **SAMPLE_PMA_DATA,
    "pma_number": "P200050",
    "expedited_review_flag": "Y",
    "advisory_committee": "CV",
}

SAMPLE_SUPPLEMENTS = [
    {
        "pma_number": "P170019S001",
        "supplement_number": "S001",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "New indication for BRCA1/2 companion diagnostic labeling",
        "decision_date": "20180615",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S002",
        "supplement_number": "S002",
        "supplement_type": "30-Day Notice",
        "supplement_reason": "Minor labeling editorial change",
        "decision_date": "20180901",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S003",
        "supplement_number": "S003",
        "supplement_type": "Real-Time Supplement",
        "supplement_reason": "Design change to include new biomarker panel with clinical data",
        "decision_date": "20190301",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S004",
        "supplement_number": "S004",
        "supplement_type": "PMA Supplement",
        "supplement_reason": "Post-approval study interim report",
        "decision_date": "20190715",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S005",
        "supplement_number": "S005",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "Expanded indication for ALK fusion detection",
        "decision_date": "20200115",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S006",
        "supplement_number": "S006",
        "supplement_type": "Manufacturing Change",
        "supplement_reason": "Manufacturing facility site change",
        "decision_date": "20200601",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S007",
        "supplement_number": "S007",
        "supplement_type": "Panel-Track Supplement",
        "supplement_reason": "Significant modification requiring advisory committee panel review",
        "decision_date": "20210715",
        "decision_code": "DENY",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S008",
        "supplement_number": "S008",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "New indication expansion for ROS1 fusion detection",
        "decision_date": "20220301",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S009",
        "supplement_number": "S009",
        "supplement_type": "PMA Supplement",
        "supplement_reason": "Labeling update for new warnings",
        "decision_date": "20230101",
        "decision_code": "WDRN",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S010",
        "supplement_number": "S010",
        "supplement_type": "Real-Time Supplement",
        "supplement_reason": "Design change for new algorithm with clinical data",
        "decision_date": "20230615",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
]

SAMPLE_CLINICAL_SECTIONS = {
    "sections": {
        "clinical_studies": {
            "content": (
                "A pivotal randomized controlled trial was conducted with "
                "enrollment of 1,200 patients across 15 clinical sites. "
                "The study used a non-inferiority design. "
                "The primary endpoint was device success rate at 12 months. "
                "Follow-up of 24 months was completed."
            ),
            "word_count": 500,
        },
        "device_description": {
            "content": "An in vitro diagnostic next generation sequencing system.",
            "word_count": 9,
        },
    },
}

SAMPLE_MAUDE_COUNT_RESULT = {
    "results": [
        {"term": "Malfunction", "count": 150},
        {"term": "Injury", "count": 80},
        {"term": "Death", "count": 5},
        {"term": "No answer provided", "count": 30},
        {"term": "Other", "count": 15},
    ],
}

SAMPLE_MAUDE_EVENTS = {
    "results": [
        {"event_type": "Malfunction", "date_received": "20230101", "date_of_event": "20221215"},
        {"event_type": "Injury", "date_received": "20230215", "date_of_event": "20230201"},
        {"event_type": "Death", "date_received": "20220601", "date_of_event": "20220515"},
        {"event_type": "Malfunction", "date_received": "20220315", "date_of_event": "20220301"},
        {"event_type": "Injury", "date_received": "20210901", "date_of_event": "20210815"},
        {"event_type": "Malfunction", "date_received": "20210601", "date_of_event": "20210515"},
        {"event_type": "Malfunction", "date_received": "20200301", "date_of_event": "20200215"},
        {"event_type": "Injury", "date_received": "20200115", "date_of_event": "20200101"},
        {"event_type": "Malfunction", "date_received": "20190601", "date_of_event": "20190515"},
        {"event_type": "Malfunction", "date_received": "20180901", "date_of_event": "20180815"},
    ],
}

SAMPLE_PMA_SEARCH_RESULT = {
    "meta": {"results": {"total": 5}},
    "results": [
        {
            "pma_number": "P170019", "product_code": "NMH",
            "decision_date": "20171130", "trade_name": "Device A",
            "applicant": "Company A", "decision_code": "APPR",
            "advisory_committee": "CH",
        },
        {
            "pma_number": "P160035", "product_code": "NMH",
            "decision_date": "20160801", "trade_name": "Device B",
            "applicant": "Company B", "decision_code": "APPR",
            "advisory_committee": "CH",
        },
        {
            "pma_number": "P150009", "product_code": "NMH",
            "decision_date": "20150301", "trade_name": "Device C",
            "applicant": "Company A", "decision_code": "APPR",
            "advisory_committee": "CH",
        },
        {
            "pma_number": "P140020", "product_code": "NMH",
            "decision_date": "20140601", "trade_name": "Device D",
            "applicant": "Company C", "decision_code": "APPR",
            "advisory_committee": "CH",
        },
        {
            "pma_number": "P130015", "product_code": "NMH",
            "decision_date": "20130901", "trade_name": "Device E",
            "applicant": "Company A", "decision_code": "DENY",
            "advisory_committee": "CH",
        },
    ],
}


def _create_mock_store():
    """Create a mock PMADataStore with consistent test data."""
    store = MagicMock()
    store.get_pma_data.return_value = SAMPLE_PMA_DATA
    store.get_supplements.return_value = SAMPLE_SUPPLEMENTS
    store.get_extracted_sections.return_value = SAMPLE_CLINICAL_SECTIONS
    store.get_pma_dir.return_value = Path("/tmp/test_pma_cache/P170019")
    store.cache_dir = Path("/tmp/test_pma_cache")

    # Set up client mock
    store.client = MagicMock()
    store.client.search_pma.return_value = SAMPLE_PMA_SEARCH_RESULT
    store.client.get_pma.return_value = {"results": [SAMPLE_PMA_DATA]}
    store.client.get_pma_supplements.return_value = {"results": SAMPLE_SUPPLEMENTS}
    store.client.get_events.return_value = SAMPLE_MAUDE_COUNT_RESULT
    store.client.get_classification.return_value = {
        "results": [{"product_code": "NMH", "device_class": "3"}],
    }
    store.client.get_pma_by_product_code.return_value = SAMPLE_PMA_SEARCH_RESULT

    # Manifest mock
    store.get_manifest.return_value = {
        "pma_entries": {
            "P170019": {
                "pma_number": "P170019",
                "product_code": "NMH",
                "advisory_committee": "CH",
                "decision_date": "20171130",
                "applicant": "FOUNDATION MEDICINE, INC.",
                "supplement_count": 10,
            },
        },
        "search_cache": {},
    }

    return store


# ============================================================
# 1. TestReviewTimePredictor
# ============================================================

class TestReviewTimePredictor:
    """Test suite for review_time_predictor.py."""

    def setup_method(self):
        from review_time_predictor import ReviewTimePredictionEngine
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)

    def test_predict_review_time_basic(self):
        """Test basic review time prediction for a PMA."""
        result = self.engine.predict_review_time("P170019")
        assert result["pma_number"] == "P170019"
        assert "prediction" in result
        pred = result["prediction"]
        assert "expected_days" in pred
        assert "confidence_interval" in pred
        assert pred["expected_days"] > 0

    def test_predict_returns_expected_months(self):
        """Test that prediction includes expected months."""
        result = self.engine.predict_review_time("P170019")
        pred = result["prediction"]
        assert "expected_months" in pred
        assert pred["expected_months"] > 0
        assert abs(pred["expected_months"] - pred["expected_days"] / 30.44) < 0.2

    def test_confidence_interval_bounds(self):
        """Test that confidence interval has proper bounds."""
        result = self.engine.predict_review_time("P170019")
        ci = result["prediction"]["confidence_interval"]
        assert ci["lower_days"] > 0
        assert ci["upper_days"] > ci["lower_days"]
        assert ci["confidence_level"] == 0.80

    def test_predict_api_error(self):
        """Test prediction with API error."""
        self.store.get_pma_data.return_value = {"error": "API unavailable"}
        result = self.engine.predict_review_time("P170019")
        assert "error" in result

    def test_features_extraction(self):
        """Test feature extraction from PMA data."""
        result = self.engine.predict_review_time("P170019")
        features = result["features"]
        assert features["product_code"] == "NMH"
        assert features["advisory_committee"] == "CH"
        assert isinstance(features["has_clinical_data"], bool)
        assert isinstance(features["risk_factors_detected"], list)

    def test_clinical_data_detection(self):
        """Test clinical data presence detection from sections."""
        result = self.engine.predict_review_time("P170019")
        features = result["features"]
        assert features["has_clinical_data"] is True

    def test_clinical_data_absent(self):
        """Test when no clinical sections are available."""
        self.store.get_extracted_sections.return_value = None
        result = self.engine.predict_review_time("P170019")
        features = result["features"]
        assert features["has_clinical_data"] is False

    def test_expedited_review_detection(self):
        """Test expedited review flag detection."""
        self.store.get_pma_data.return_value = SAMPLE_PMA_DATA_EXPEDITED
        result = self.engine.predict_review_time("P200050")
        features = result["features"]
        assert features["is_expedited"] is True
        assert "expedited_review" in features["risk_factors_detected"]

    def test_panel_baseline_applied(self):
        """Test that panel-specific baseline is used."""
        result = self.engine.predict_review_time("P170019")
        pred = result["prediction"]
        # CH panel baseline is 320 days
        assert pred.get("baseline_days", 0) == 320

    def test_predict_for_new_submission(self):
        """Test prediction for hypothetical new submission."""
        result = self.engine.predict_for_new_submission({
            "product_code": "NMH",
            "advisory_committee": "CV",
            "has_clinical_data": True,
            "clinical_complexity": "complex",
        })
        assert "prediction" in result
        pred = result["prediction"]
        assert pred["expected_days"] > 0

    def test_analyze_historical_review_times(self):
        """Test historical review time analysis."""
        result = self.engine.analyze_historical_review_times("NMH")
        assert result["product_code"] == "NMH"
        assert result["total_pmas"] >= 1
        assert "statistics" in result or "error" in result

    def test_analyze_historical_no_data(self):
        """Test historical analysis with no data."""
        self.store.client.search_pma.return_value = {"degraded": True}
        result = self.engine.analyze_historical_review_times("ZZZ")
        assert result["total_pmas"] == 0

    def test_train_model_no_data(self):
        """Test model training with no data."""
        self.store.get_manifest.return_value = {"pma_entries": {}, "search_cache": {}}
        result = self.engine.train_model()
        assert result["status"] == "no_training_data"
        assert result["model_type"] == "statistical_baseline"

    def test_train_model_few_examples(self):
        """Test model training with few examples."""
        training_data = [
            {"advisory_committee": "CH", "review_days": 300},
            {"advisory_committee": "CV", "review_days": 400},
        ]
        result = self.engine.train_model(training_data=training_data)
        assert result["model_type"] == "statistical_baseline"
        assert result["training_examples"] == 2

    def test_model_save_load(self):
        """Test model save and load."""
        from review_time_predictor import ReviewTimePredictionEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "model.json")
            saved_path = self.engine.save_model(filepath=filepath)
            assert os.path.exists(saved_path)

            new_engine = ReviewTimePredictionEngine.__new__(
                ReviewTimePredictionEngine
            )
            new_engine.store = self.store
            new_engine.model_type = "statistical_baseline"
            new_engine._trained_model = None
            new_engine._label_encoders = {}
            new_engine._training_data = None
            new_engine._training_stats = {}
            loaded = new_engine.load_model(filepath=filepath)
            assert loaded is True

    def test_model_version_present(self):
        """Test that model version is included in results."""
        result = self.engine.predict_review_time("P170019")
        assert "model_version" in result
        assert result["model_version"] == "1.0.0"

    def test_risk_factor_impact(self):
        """Test that risk factors affect prediction."""
        # Baseline prediction
        baseline = self.engine.predict_for_new_submission({
            "product_code": "NMH",
            "advisory_committee": "CH",
            "clinical_complexity": "simple",
        })
        # Complex prediction
        complex_pred = self.engine.predict_for_new_submission({
            "product_code": "NMH",
            "advisory_committee": "CH",
            "clinical_complexity": "complex",
        })
        # Complex should predict longer
        assert (complex_pred["prediction"]["expected_days"]
                >= baseline["prediction"]["expected_days"])


# ============================================================
# 2. TestApprovalProbability
# ============================================================

class TestApprovalProbability:
    """Test suite for approval_probability.py."""

    def setup_method(self):
        from approval_probability import ApprovalProbabilityScorer
        self.store = _create_mock_store()
        self.scorer = ApprovalProbabilityScorer(store=self.store)

    def test_score_all_supplements_basic(self):
        """Test scoring all supplements for a PMA."""
        result = self.scorer.score_approval_probability("P170019")
        assert result["pma_number"] == "P170019"
        assert result["total_supplements"] == 10
        assert "scored_supplements" in result
        assert len(result["scored_supplements"]) == 10

    def test_score_single_supplement(self):
        """Test scoring a specific supplement."""
        result = self.scorer.score_approval_probability("P170019", supplement_number="S001")
        assert len(result["scored_supplements"]) == 1
        assert result["scored_supplements"][0]["supplement_number"] == "S001"

    def test_score_missing_supplement(self):
        """Test scoring a non-existent supplement."""
        result = self.scorer.score_approval_probability("P170019", supplement_number="S999")
        assert "error" in result

    def test_probability_range(self):
        """Test that probabilities are in valid range."""
        result = self.scorer.score_approval_probability("P170019")
        for s in result["scored_supplements"]:
            assert 0 < s["approval_probability"] <= 100

    def test_approved_supplements_high_probability(self):
        """Test that approved supplements generally get high probability."""
        result = self.scorer.score_approval_probability("P170019")
        approved_probs = [
            s["approval_probability"]
            for s in result["scored_supplements"]
            if s["actual_outcome"] == "approved"
        ]
        avg_approved = sum(approved_probs) / max(len(approved_probs), 1)
        assert avg_approved > 60  # Should be generally above 60%

    def test_denied_supplement_lower_probability(self):
        """Test that denied supplement gets risk flag penalty."""
        result = self.scorer.score_approval_probability("P170019", supplement_number="S007")
        s = result["scored_supplements"][0]
        # Panel-track supplement should have penalty
        assert s["approval_probability"] < 90

    def test_prediction_accuracy_tracking(self):
        """Test that prediction accuracy is tracked."""
        result = self.scorer.score_approval_probability("P170019")
        agg = result["aggregate_analysis"]
        assert "classification_accuracy" in agg
        assert "predictions_evaluated" in agg

    def test_risk_flags_present(self):
        """Test that risk flags are detected."""
        result = self.scorer.score_approval_probability("P170019")
        # At least some supplements should have risk flags
        all_flags = []
        for s in result["scored_supplements"]:
            all_flags.extend(s.get("risk_flags", []))
        # The denied supplement should cause prior_denial risk flag for later supplements
        assert len(all_flags) >= 1

    def test_aggregate_analysis(self):
        """Test aggregate analysis computation."""
        result = self.scorer.score_approval_probability("P170019")
        agg = result["aggregate_analysis"]
        assert agg["total_scored"] == 10
        assert "avg_approval_probability" in agg
        assert "min_approval_probability" in agg
        assert "max_approval_probability" in agg

    def test_api_error_handling(self):
        """Test scoring with API error."""
        self.store.get_pma_data.return_value = {"error": "Not found"}
        result = self.scorer.score_approval_probability("P999999")
        assert "error" in result

    def test_no_supplements(self):
        """Test scoring with no supplements."""
        self.store.get_supplements.return_value = []
        result = self.scorer.score_approval_probability("P170019")
        assert result["total_supplements"] == 0

    def test_historical_outcomes(self):
        """Test historical outcome analysis."""
        result = self.scorer.analyze_historical_outcomes("P170019")
        assert result["total_supplements"] == 10
        assert "outcome_summary" in result
        assert result["outcome_summary"]["approved"] >= 7
        assert result["outcome_summary"]["denied"] == 1
        assert result["outcome_summary"]["withdrawn"] == 1

    def test_historical_by_type(self):
        """Test historical analysis by supplement type."""
        result = self.scorer.analyze_historical_outcomes("P170019")
        by_type = result["by_type"]
        assert len(by_type) >= 2

    def test_hypothetical_supplement_scoring(self):
        """Test scoring a hypothetical supplement."""
        result = self.scorer.score_hypothetical_supplement({
            "change_type": "labeling",
            "regulatory_type": "180_day",
            "has_clinical_data": True,
            "prior_denials": 0,
            "prior_approvals": 8,
        })
        assert "approval_probability" in result
        assert result["approval_probability"] > 80

    def test_hypothetical_high_risk(self):
        """Test hypothetical supplement with high risk factors."""
        result = self.scorer.score_hypothetical_supplement({
            "change_type": "panel_track",
            "regulatory_type": "panel_track",
            "has_clinical_data": False,
            "prior_denials": 2,
        })
        # Should have lower probability
        assert result["approval_probability"] < 75
        assert len(result["risk_flags"]) >= 2

    def test_model_version_present(self):
        """Test model version in results."""
        result = self.scorer.score_approval_probability("P170019")
        assert result["model_version"] == "1.0.0"

    def test_train_model_no_data(self):
        """Test training with no data."""
        self.store.get_manifest.return_value = {"pma_entries": {}, "search_cache": {}}
        result = self.scorer.train_model()
        assert result["model_type"] == "rule_based_baseline"


# ============================================================
# 3. TestMAUDEComparison
# ============================================================

class TestMAUDEComparison:
    """Test suite for maude_comparison.py."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    def test_build_profile_basic(self):
        """Test building basic adverse event profile."""
        profile = self.engine.build_adverse_event_profile("P170019")
        assert profile["pma_number"] == "P170019"
        assert profile["total_events"] > 0
        assert "event_type_distribution" in profile
        assert "severity_distribution" in profile

    def test_profile_event_counts(self):
        """Test event counts in profile."""
        profile = self.engine.build_adverse_event_profile("P170019")
        assert profile["malfunction_count"] == 150
        assert profile["injury_count"] == 80
        assert profile["death_count"] == 5

    def test_profile_death_flag(self):
        """Test death report detection flag."""
        profile = self.engine.build_adverse_event_profile("P170019")
        assert profile["has_death_reports"] is True

    def test_profile_no_product_code(self):
        """Test profile with missing product code."""
        self.store.get_pma_data.return_value = {
            **SAMPLE_PMA_DATA,
            "product_code": "",
        }
        profile = self.engine.build_adverse_event_profile("P170019")
        assert profile["total_events"] == 0

    def test_compare_adverse_events_basic(self):
        """Test basic adverse event comparison."""
        result = self.engine.compare_adverse_events("P170019")
        assert result["pma_number"] == "P170019"
        assert "primary_profile" in result
        assert "peer_benchmarks" in result
        assert "outliers" in result
        assert "safety_signals" in result

    def test_compare_with_explicit_comparators(self):
        """Test comparison with explicitly listed comparators."""
        result = self.engine.compare_adverse_events(
            "P170019", comparators=["P160035", "P150009"]
        )
        assert result["total_devices_compared"] >= 2

    def test_peer_benchmarks_computed(self):
        """Test peer benchmark computation."""
        result = self.engine.compare_adverse_events("P170019")
        benchmarks = result["peer_benchmarks"]
        assert "total_devices" in benchmarks
        assert "devices_with_events" in benchmarks

    def test_detect_safety_signals_basic(self):
        """Test safety signal detection for a product code."""
        result = self.engine.detect_safety_signals("NMH")
        assert result["product_code"] == "NMH"
        assert result["total_events"] > 0
        assert "signals" in result
        assert isinstance(result["signals"], list)

    def test_death_signal_detected(self):
        """Test that death reports trigger a safety signal."""
        result = self.engine.detect_safety_signals("NMH")
        death_signals = [
            s for s in result["signals"]
            if s["signal_type"] == "death_reports"
        ]
        assert len(death_signals) >= 1
        assert death_signals[0]["severity"] == "CRITICAL"

    def test_no_events(self):
        """Test signal detection with no events."""
        self.store.client.get_events.return_value = {"degraded": True}
        result = self.engine.detect_safety_signals("ZZZ")
        assert result["total_events"] == 0
        assert len(result["signals"]) == 0

    def test_generate_heatmap_basic(self):
        """Test event heatmap generation."""
        # Set up events mock to return detailed events (heatmap calls _query_event_details)
        self.store.client.get_events.return_value = SAMPLE_MAUDE_EVENTS
        result = self.engine.generate_event_heatmap("NMH")
        assert result["product_code"] == "NMH"
        assert result["has_data"] is True
        assert "years" in result
        assert "event_types" in result
        assert "matrix" in result

    def test_heatmap_no_data(self):
        """Test heatmap with no data."""
        self.store.client.get_events.return_value = {"degraded": True}
        result = self.engine.generate_event_heatmap("ZZZ")
        assert result["has_data"] is False

    def test_heatmap_matrix_dimensions(self):
        """Test heatmap matrix dimensions match labels."""
        self.store.client.get_events.return_value = SAMPLE_MAUDE_EVENTS
        result = self.engine.generate_event_heatmap("NMH")
        if result["has_data"]:
            assert len(result["matrix"]) == len(result["years"])
            for row in result["matrix"]:
                assert len(row) == len(result["event_types"])

    def test_outlier_detection(self):
        """Test outlier detection in comparison."""
        result = self.engine.compare_adverse_events("P170019")
        outliers = result["outliers"]
        # Outliers should be a list of dicts with z_score
        for o in outliers:
            assert "z_score" in o
            assert "event_type" in o

    def test_severity_distribution(self):
        """Test severity distribution mapping."""
        profile = self.engine.build_adverse_event_profile("P170019")
        sev_dist = profile["severity_distribution"]
        assert "critical" in sev_dist or "high" in sev_dist or "medium" in sev_dist

    def test_api_error_handling(self):
        """Test comparison with API error."""
        self.store.get_pma_data.return_value = {"error": "Not found"}
        result = self.engine.compare_adverse_events("P999999")
        assert "error" in result


# ============================================================
# 4. TestCompetitiveDashboard
# ============================================================

class TestCompetitiveDashboard:
    """Test suite for competitive_dashboard.py."""

    def setup_method(self):
        from competitive_dashboard import CompetitiveDashboardGenerator
        self.store = _create_mock_store()
        self.generator = CompetitiveDashboardGenerator(store=self.store)

    def test_generate_dashboard_basic(self):
        """Test basic dashboard generation."""
        dashboard = self.generator.generate_dashboard("NMH")
        assert dashboard["product_code"] == "NMH"
        assert "key_metrics" in dashboard
        assert "market_share" in dashboard
        assert "approval_trends" in dashboard
        assert "recent_approvals" in dashboard

    def test_key_metrics(self):
        """Test key metrics computation."""
        dashboard = self.generator.generate_dashboard("NMH")
        metrics = dashboard["key_metrics"]
        assert metrics["total_pmas"] >= 1
        assert metrics["total_applicants"] >= 1
        assert 0 <= metrics["approval_rate"] <= 100

    def test_market_share_by_applicant(self):
        """Test market share analysis."""
        dashboard = self.generator.generate_dashboard("NMH")
        share = dashboard["market_share"]
        by_applicant = share["by_applicant"]
        assert len(by_applicant) >= 1
        # Check first entry (market leader)
        leader = by_applicant[0]
        assert "applicant" in leader
        assert "count" in leader
        assert "share_pct" in leader
        assert leader["share_pct"] > 0

    def test_hhi_concentration(self):
        """Test HHI market concentration calculation."""
        dashboard = self.generator.generate_dashboard("NMH")
        concentration = dashboard["market_share"]["concentration"]
        assert "hhi" in concentration
        assert concentration["hhi"] >= 0
        assert concentration["concentration"] in (
            "competitive", "moderately_concentrated", "highly_concentrated"
        )

    def test_approval_trends(self):
        """Test approval trend analysis."""
        dashboard = self.generator.generate_dashboard("NMH")
        trends = dashboard["approval_trends"]
        assert "year_distribution" in trends
        assert "peak_year" in trends

    def test_recent_approvals(self):
        """Test recent approvals list."""
        dashboard = self.generator.generate_dashboard("NMH")
        recent = dashboard["recent_approvals"]
        assert len(recent) >= 1
        # Check structure
        r = recent[0]
        assert "pma_number" in r
        assert "device_name" in r
        assert "applicant" in r
        assert "decision_date" in r

    def test_safety_summary(self):
        """Test safety summary from MAUDE data."""
        dashboard = self.generator.generate_dashboard("NMH")
        safety = dashboard["safety_summary"]
        assert "total_events" in safety
        assert "death_count" in safety
        assert "injury_count" in safety

    def test_supplement_summary(self):
        """Test supplement activity summary."""
        dashboard = self.generator.generate_dashboard("NMH")
        supps = dashboard["supplement_activity"]
        assert "total_supplements" in supps
        assert "avg_per_pma" in supps

    def test_no_data(self):
        """Test dashboard with no PMA data."""
        self.store.client.search_pma.return_value = {"degraded": True}
        dashboard = self.generator.generate_dashboard("ZZZ")
        assert "error" in dashboard

    def test_export_html(self):
        """Test HTML export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "test_dashboard.html")
            result_path = self.generator.export_html("NMH", output_path=html_path)
            assert os.path.exists(result_path)
            with open(result_path) as f:
                content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "NMH" in content
            assert "DISCLAIMER" in content

    def test_export_csv(self):
        """Test CSV export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test_data.csv")
            result_path = self.generator.export_csv("NMH", output_path=csv_path)
            assert os.path.exists(result_path)
            with open(result_path) as f:
                content = f.read()
            assert "pma_number" in content

    def test_export_json(self):
        """Test JSON export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test_data.json")
            result_path = self.generator.export_json("NMH", output_path=json_path)
            assert os.path.exists(result_path)
            with open(result_path) as f:
                data = json.load(f)
            assert data["product_code"] == "NMH"

    def test_market_summary(self):
        """Test concise market summary."""
        summary = self.generator.generate_market_summary("NMH")
        assert summary["product_code"] == "NMH"
        assert "market_leader" in summary
        assert "market_trend" in summary

    def test_html_escaping(self):
        """Test HTML special character escaping."""
        from competitive_dashboard import CompetitiveDashboardGenerator
        assert CompetitiveDashboardGenerator._escape("<script>") == "&lt;script&gt;"
        assert CompetitiveDashboardGenerator._escape('"test"') == "&quot;test&quot;"
        assert CompetitiveDashboardGenerator._escape("a&b") == "a&amp;b"

    def test_clinical_endpoints(self):
        """Test clinical endpoint aggregation."""
        dashboard = self.generator.generate_dashboard("NMH")
        endpoints = dashboard["clinical_endpoints"]
        assert "pmas_with_clinical_data" in endpoints
        assert "clinical_data_coverage" in endpoints


# ============================================================
# 5. TestPhase4Integration
# ============================================================

class TestPhase4Integration:
    """Test cross-module integration and Phase 0-3 compatibility."""

    def setup_method(self):
        self.store = _create_mock_store()

    def test_review_predictor_uses_data_store(self):
        """Test that review predictor properly uses PMADataStore."""
        from review_time_predictor import ReviewTimePredictionEngine
        engine = ReviewTimePredictionEngine(store=self.store)
        result = engine.predict_review_time("P170019")
        self.store.get_pma_data.assert_called()
        assert result["pma_number"] == "P170019"

    def test_approval_scorer_uses_data_store(self):
        """Test that approval scorer properly uses PMADataStore."""
        from approval_probability import ApprovalProbabilityScorer
        scorer = ApprovalProbabilityScorer(store=self.store)
        result = scorer.score_approval_probability("P170019")
        self.store.get_supplements.assert_called()
        assert result["total_supplements"] == 10

    def test_maude_engine_uses_data_store(self):
        """Test that MAUDE engine properly uses PMADataStore."""
        from maude_comparison import MAUDEComparisonEngine
        engine = MAUDEComparisonEngine(store=self.store)
        profile = engine.build_adverse_event_profile("P170019")
        self.store.get_pma_data.assert_called()
        assert profile["product_code"] == "NMH"

    def test_dashboard_uses_data_store(self):
        """Test that dashboard generator properly uses PMADataStore."""
        from competitive_dashboard import CompetitiveDashboardGenerator
        generator = CompetitiveDashboardGenerator(store=self.store)
        dashboard = generator.generate_dashboard("NMH")
        self.store.client.search_pma.assert_called()
        assert dashboard["product_code"] == "NMH"

    def test_all_modules_share_store(self):
        """Test all Phase 4 modules can share the same data store."""
        from review_time_predictor import ReviewTimePredictionEngine
        from approval_probability import ApprovalProbabilityScorer
        from maude_comparison import MAUDEComparisonEngine
        from competitive_dashboard import CompetitiveDashboardGenerator

        store = self.store
        rtp = ReviewTimePredictionEngine(store=store)
        aps = ApprovalProbabilityScorer(store=store)
        mce = MAUDEComparisonEngine(store=store)
        cdg = CompetitiveDashboardGenerator(store=store)

        r1 = rtp.predict_review_time("P170019")
        r2 = aps.score_approval_probability("P170019")
        r3 = mce.build_adverse_event_profile("P170019")
        r4 = cdg.generate_dashboard("NMH")

        assert r1["pma_number"] == "P170019"
        assert r2["pma_number"] == "P170019"
        assert r3["pma_number"] == "P170019"
        assert r4["product_code"] == "NMH"

    def test_phase3_compatibility_supplement_tracker(self):
        """Test Phase 4 works alongside Phase 3 supplement_tracker."""
        from supplement_tracker import SupplementTracker
        from approval_probability import ApprovalProbabilityScorer

        tracker = SupplementTracker(store=self.store)
        scorer = ApprovalProbabilityScorer(store=self.store)

        p3_report = tracker.generate_supplement_report("P170019")
        p4_result = scorer.score_approval_probability("P170019")

        # Both should process the same supplements
        assert p3_report["total_supplements"] == p4_result["total_supplements"]

    def test_phase1_compatibility_intelligence(self):
        """Test Phase 4 works alongside Phase 1 intelligence module."""
        from pma_intelligence import PMAIntelligenceEngine
        from review_time_predictor import ReviewTimePredictionEngine

        intel = PMAIntelligenceEngine(store=self.store)
        predictor = ReviewTimePredictionEngine(store=self.store)

        # Both should operate on same PMA data
        intel_report = intel.generate_intelligence("P170019", focus="clinical")
        prediction = predictor.predict_review_time("P170019")

        assert intel_report["pma_number"] == prediction["pma_number"]

    def test_cross_module_pma_data_consistency(self):
        """Test that all modules get consistent PMA data."""
        from review_time_predictor import ReviewTimePredictionEngine
        from approval_probability import ApprovalProbabilityScorer
        from maude_comparison import MAUDEComparisonEngine

        rtp = ReviewTimePredictionEngine(store=self.store)
        aps = ApprovalProbabilityScorer(store=self.store)
        mce = MAUDEComparisonEngine(store=self.store)

        r1 = rtp.predict_review_time("P170019")
        r2 = aps.score_approval_probability("P170019")
        r3 = mce.build_adverse_event_profile("P170019")

        # All should reference same device
        assert r1.get("device_name") == r2.get("device_name")
        assert r1.get("product_code") == r3.get("product_code")

    def test_generated_at_timestamps(self):
        """Test that all modules include generated_at timestamps."""
        from review_time_predictor import ReviewTimePredictionEngine
        from approval_probability import ApprovalProbabilityScorer
        from competitive_dashboard import CompetitiveDashboardGenerator

        rtp = ReviewTimePredictionEngine(store=self.store)
        aps = ApprovalProbabilityScorer(store=self.store)
        cdg = CompetitiveDashboardGenerator(store=self.store)

        r1 = rtp.predict_review_time("P170019")
        r2 = aps.score_approval_probability("P170019")
        r3 = cdg.generate_dashboard("NMH")

        assert "generated_at" in r1
        assert "generated_at" in r2
        assert "generated_at" in r3


# ============================================================
# 6. TestEdgeCases
# ============================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions across Phase 4 modules."""

    def setup_method(self):
        self.store = _create_mock_store()

    def test_empty_product_code_maude(self):
        """Test MAUDE comparison with empty product code."""
        from maude_comparison import MAUDEComparisonEngine
        self.store.get_pma_data.return_value = {
            **SAMPLE_PMA_DATA,
            "product_code": "",
        }
        engine = MAUDEComparisonEngine(store=self.store)
        profile = engine.build_adverse_event_profile("P170019")
        assert profile["total_events"] == 0

    def test_single_pma_dashboard(self):
        """Test dashboard with only one PMA."""
        from competitive_dashboard import CompetitiveDashboardGenerator
        self.store.client.search_pma.return_value = {
            "results": [SAMPLE_PMA_SEARCH_RESULT["results"][0]],
        }
        generator = CompetitiveDashboardGenerator(store=self.store)
        dashboard = generator.generate_dashboard("NMH")
        assert dashboard["key_metrics"]["total_pmas"] == 1

    def test_all_denied_supplements(self):
        """Test approval probability with all denied supplements."""
        from approval_probability import ApprovalProbabilityScorer
        denied_supps = [
            {**s, "decision_code": "DENY"}
            for s in SAMPLE_SUPPLEMENTS
        ]
        self.store.get_supplements.return_value = denied_supps
        scorer = ApprovalProbabilityScorer(store=self.store)
        result = scorer.score_approval_probability("P170019")
        agg = result["aggregate_analysis"]
        # Average probability should be lower
        assert agg["avg_approval_probability"] < 90

    def test_prediction_minimum_days(self):
        """Test that prediction never goes below minimum."""
        from review_time_predictor import ReviewTimePredictionEngine
        engine = ReviewTimePredictionEngine(store=self.store)
        result = engine.predict_for_new_submission({
            "product_code": "NMH",
            "advisory_committee": "CH",
            "supplement_type": "30_day_notice",  # Short review type
            "is_expedited": True,
        })
        pred = result["prediction"]
        assert pred["expected_days"] >= 30

    def test_maude_empty_events(self):
        """Test MAUDE with empty event results."""
        from maude_comparison import MAUDEComparisonEngine
        self.store.client.get_events.return_value = {"results": []}
        engine = MAUDEComparisonEngine(store=self.store)
        result = engine.detect_safety_signals("NMH")
        assert result["total_events"] == 0
        assert len(result["signals"]) == 0

    def test_dashboard_html_with_special_chars(self):
        """Test HTML dashboard handles special characters."""
        from competitive_dashboard import CompetitiveDashboardGenerator
        special_pma = {
            **SAMPLE_PMA_SEARCH_RESULT["results"][0],
            "applicant": "Test & <Company> \"Inc.\"",
        }
        self.store.client.search_pma.return_value = {
            "results": [special_pma],
        }
        generator = CompetitiveDashboardGenerator(store=self.store)
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = os.path.join(tmpdir, "test.html")
            generator.export_html("NMH", output_path=html_path)
            with open(html_path) as f:
                content = f.read()
            # Special characters should be escaped
            assert "&lt;" in content or "Test &amp;" in content

    def test_std_dev_single_value(self):
        """Test standard deviation with single value."""
        from maude_comparison import MAUDEComparisonEngine
        engine = MAUDEComparisonEngine(store=self.store)
        assert engine._std_dev([5.0]) == 0.0

    def test_std_dev_empty(self):
        """Test standard deviation with empty list."""
        from maude_comparison import MAUDEComparisonEngine
        engine = MAUDEComparisonEngine(store=self.store)
        assert engine._std_dev([]) == 0.0
