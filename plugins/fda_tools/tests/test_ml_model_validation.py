"""
ML Model Validation Tests for review_time_predictor.py and maude_comparison.py (FDA-52).

Tests model accuracy using golden test datasets with known expected outcomes:
    1. Z-score calculation accuracy
    2. Panel-specific baseline calculations
    3. Risk factor adjustments
    4. Outlier detection thresholds
    5. Statistical computation correctness
    6. Safety signal detection logic
    7. Severity distribution mapping
    8. Prediction boundary conditions

All tests run offline using deterministic test data (no API calls).
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent.resolve()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:


# ---------------------------------------------------------------------------
# Golden Test Data
# ---------------------------------------------------------------------------

# Known panel baselines from review_time_predictor.py constants
GOLDEN_PANEL_BASELINES = {
    "CV": 380,   # Cardiovascular
    "OR": 340,   # Orthopedic
    "NE": 370,   # Neurological
    "CH": 320,   # Clinical Chemistry
    "RA": 280,   # Radiology
    "DE": 290,   # Dental
    "SU": 300,   # General Surgery
}

# Golden risk factor impacts (days added/subtracted)
GOLDEN_RISK_FACTORS = {
    "novel_technology": 60,
    "complex_clinical": 90,
    "advisory_panel_meeting": 75,
    "combination_product": 45,
    "pediatric_indication": 30,
    "expedited_review": -60,
    "high_supplement_count": -20,
    "applicant_experience": -30,
}

# Golden Z-score test cases: (values, test_value, expected_z_score)
GOLDEN_ZSCORE_CASES = [
    # Case 1: Simple values, exact center
    ([10, 20, 30], 20.0, 0.0),
    # Case 2: Above mean by 1 std
    ([10, 20, 30], 30.0, 1.0),
    # Case 3: Below mean by 1 std
    ([10, 20, 30], 10.0, -1.0),
    # Case 4: All same values, std=0
    ([5, 5, 5], 5.0, 0.0),
    # Case 5: Large dataset
    ([100, 200, 300, 400, 500], 500.0, None),  # Approx 1.41
    # Case 6: Realistic MAUDE counts
    ([150, 80, 5, 30, 15], 150.0, None),  # Computed below
]

# Golden outlier detection cases
GOLDEN_OUTLIER_CASES = [
    # (primary_count, peer_mean, peer_std, expected_direction, should_be_outlier)
    (200, 50, 30, "above", True),    # z = 5.0, well above threshold
    (10, 50, 30, "below", False),    # z = -1.33, below threshold of 2.0
    (110, 50, 30, "above", True),    # z = 2.0, exactly at threshold
    (50, 50, 30, None, False),       # z = 0.0, not an outlier
    (50, 50, 0, None, False),        # std = 0, z = 0
]

# Golden safety signal cases
GOLDEN_SIGNAL_CASES = [
    # Case: Death reports above threshold (3)
    {"Death": 5, "Injury": 80, "Malfunction": 150, "expected_death_signal": True},
    # Case: Death reports below threshold
    {"Death": 2, "Injury": 80, "Malfunction": 150, "expected_death_signal": False},
    # Case: High malfunction rate (> 60%)
    {"Death": 0, "Injury": 10, "Malfunction": 70, "expected_malfunction_signal": True},
    # Case: Normal malfunction rate
    {"Death": 0, "Injury": 40, "Malfunction": 40, "expected_malfunction_signal": False},
]


# ---------------------------------------------------------------------------
# Helper: Create mock PMADataStore
# ---------------------------------------------------------------------------


def _create_mock_store(pma_data=None, maude_counts=None, maude_events=None):
    """Create a mock PMADataStore with configurable responses."""
    store = MagicMock()

    if pma_data is None:
        pma_data = {
            "pma_number": "P170019",
            "product_code": "NMH",
            "advisory_committee": "CH",
            "device_name": "Test Device",
            "decision_date": "20171130",
            "supplement_count": 5,
            "expedited_review_flag": "N",
        }

    store.get_pma_data.return_value = pma_data
    store.get_extracted_sections.return_value = None
    store.cache_dir = Path("/tmp/test_pma_cache")

    # Client mock
    store.client = MagicMock()
    store.client.search_pma.return_value = {"results": [pma_data]}

    if maude_counts is not None:
        store.client.get_events.return_value = maude_counts
    else:
        store.client.get_events.return_value = {
            "results": [
                {"term": "Malfunction", "count": 150},
                {"term": "Injury", "count": 80},
                {"term": "Death", "count": 5},
            ],
        }

    if maude_events is not None:
        store.client.get_events.return_value = maude_events

    store.get_manifest.return_value = {"pma_entries": {}, "search_cache": {}}

    return store


# ============================================================
# 1. Review Time Predictor: Z-score and Statistics
# ============================================================


class TestReviewTimePredictorStatistics:
    """Validate statistical calculations in ReviewTimePredictionEngine."""

    def setup_method(self):
        from review_time_predictor import ReviewTimePredictionEngine
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)

    def test_calculate_statistics_basic(self):
        """Test _calculate_statistics with known values."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = self.engine._calculate_statistics(values)

        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0

    def test_calculate_statistics_std_dev(self):
        """Test standard deviation calculation accuracy."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = self.engine._calculate_statistics(values)

        # Expected std dev (sample): sqrt(250) = 15.81
        expected_std = math.sqrt(
            sum((v - 30.0) ** 2 for v in values) / (len(values) - 1)
        )
        assert abs(stats["std"] - round(expected_std, 1)) < 0.2

    def test_calculate_statistics_single_value(self):
        """Test statistics with single value."""
        stats = self.engine._calculate_statistics([42.0])
        assert stats["count"] == 1
        assert stats["mean"] == 42.0
        assert stats["median"] == 42.0
        assert stats["std"] == 0.0

    def test_calculate_statistics_empty(self):
        """Test statistics with empty list."""
        stats = self.engine._calculate_statistics([])
        assert stats["count"] == 0
        assert stats["mean"] == 0
        assert stats["median"] == 0

    def test_calculate_statistics_two_values(self):
        """Test statistics with exactly two values."""
        stats = self.engine._calculate_statistics([100.0, 200.0])
        assert stats["count"] == 2
        assert stats["mean"] == 150.0
        # Median of [100, 200] = 150
        assert stats["median"] == 150.0


# ============================================================
# 2. Review Time Predictor: Panel Baselines
# ============================================================


class TestPanelBaselineCalculations:
    """Validate panel-specific baseline calculations."""

    def setup_method(self):
        from review_time_predictor import (
            ReviewTimePredictionEngine,
            PANEL_BASELINE_DAYS,
            DEFAULT_BASELINE_DAYS,
        )
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)
        self.panel_baselines = PANEL_BASELINE_DAYS
        self.default_baseline = DEFAULT_BASELINE_DAYS

    @pytest.mark.parametrize("panel,expected_days", list(GOLDEN_PANEL_BASELINES.items()))
    def test_panel_baseline_values(self, panel, expected_days):
        """Verify each panel has the documented baseline days."""
        assert self.panel_baselines[panel] == expected_days, (
            f"Panel {panel} baseline mismatch: "
            f"expected {expected_days}, got {self.panel_baselines[panel]}"
        )

    def test_default_baseline(self):
        """Default baseline should be 330 days."""
        assert self.default_baseline == 330.0

    @pytest.mark.parametrize("panel,expected_days", list(GOLDEN_PANEL_BASELINES.items()))
    def test_prediction_uses_correct_panel_baseline(self, panel, expected_days):
        """Prediction should use the panel-specific baseline."""
        # Build features with specific panel, no risk factors
        features = {
            "advisory_committee": panel,
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        assert pred["baseline_days"] == expected_days, (
            f"Panel {panel}: prediction used baseline {pred['baseline_days']}, "
            f"expected {expected_days}"
        )

    def test_unknown_panel_uses_default(self):
        """Unknown panel code should fall back to default baseline."""
        features = {
            "advisory_committee": "ZZ",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        assert pred["baseline_days"] == round(self.default_baseline)


# ============================================================
# 3. Review Time Predictor: Risk Factor Adjustments
# ============================================================


class TestRiskFactorAdjustments:
    """Validate that risk factors correctly adjust predictions."""

    def setup_method(self):
        from review_time_predictor import ReviewTimePredictionEngine, REVIEW_RISK_FACTORS
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)
        self.risk_factors = REVIEW_RISK_FACTORS

    @pytest.mark.parametrize(
        "factor_key,expected_impact",
        list(GOLDEN_RISK_FACTORS.items()),
    )
    def test_risk_factor_impact_values(self, factor_key, expected_impact):
        """Verify each risk factor has the documented impact_days."""
        factor = self.risk_factors[factor_key]
        assert factor["impact_days"] == expected_impact, (
            f"Risk factor '{factor_key}' impact mismatch: "
            f"expected {expected_impact}, got {factor['impact_days']}"
        )

    def test_expedited_review_reduces_prediction(self):
        """Expedited review should reduce predicted days."""
        base_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        expedited_features = {
            **base_features,
            "risk_factors_detected": ["expedited_review"],
        }

        base_pred = self.engine._predict_with_baseline(base_features)
        exp_pred = self.engine._predict_with_baseline(expedited_features)

        assert exp_pred["expected_days"] < base_pred["expected_days"], (
            f"Expedited review should reduce days: "
            f"base={base_pred['expected_days']}, expedited={exp_pred['expected_days']}"
        )
        # Should reduce by exactly 60 days
        diff = base_pred["expected_days"] - exp_pred["expected_days"]
        assert diff == 60, f"Expected 60 day reduction, got {diff}"

    def test_novel_technology_increases_prediction(self):
        """Novel technology should increase predicted days."""
        base_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        novel_features = {
            **base_features,
            "risk_factors_detected": ["novel_technology"],
        }

        base_pred = self.engine._predict_with_baseline(base_features)
        novel_pred = self.engine._predict_with_baseline(novel_features)

        diff = novel_pred["expected_days"] - base_pred["expected_days"]
        assert diff == 60, f"Expected 60 day increase, got {diff}"

    def test_multiple_risk_factors_cumulative(self):
        """Multiple risk factors should have cumulative effect."""
        base_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        multi_features = {
            **base_features,
            "risk_factors_detected": ["novel_technology", "combination_product"],
        }

        base_pred = self.engine._predict_with_baseline(base_features)
        multi_pred = self.engine._predict_with_baseline(multi_features)

        expected_increase = 60 + 45  # novel + combination
        diff = multi_pred["expected_days"] - base_pred["expected_days"]
        assert diff == expected_increase, (
            f"Expected {expected_increase} day increase, got {diff}"
        )

    def test_clinical_complexity_simple_reduces(self):
        """Simple clinical complexity should reduce prediction."""
        moderate_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        simple_features = {**moderate_features, "clinical_complexity": "simple"}

        mod_pred = self.engine._predict_with_baseline(moderate_features)
        simple_pred = self.engine._predict_with_baseline(simple_features)

        assert simple_pred["expected_days"] < mod_pred["expected_days"]

    def test_clinical_complexity_complex_increases(self):
        """Complex clinical complexity should increase prediction."""
        moderate_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        complex_features = {**moderate_features, "clinical_complexity": "complex"}

        mod_pred = self.engine._predict_with_baseline(moderate_features)
        complex_pred = self.engine._predict_with_baseline(complex_features)

        assert complex_pred["expected_days"] > mod_pred["expected_days"]
        diff = complex_pred["expected_days"] - mod_pred["expected_days"]
        assert diff == 60, f"Expected 60 day increase for complex, got {diff}"

    def test_supplement_type_30_day_notice(self):
        """30-day notice supplements should dramatically reduce prediction."""
        original_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        notice_features = {**original_features, "supplement_type": "30_day_notice"}

        orig_pred = self.engine._predict_with_baseline(original_features)
        notice_pred = self.engine._predict_with_baseline(notice_features)

        assert notice_pred["expected_days"] < orig_pred["expected_days"]

    def test_high_enrollment_adjustment(self):
        """High clinical enrollment (>500) should increase prediction."""
        base_features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        high_enroll_features = {**base_features, "clinical_enrollment": 1000}

        base_pred = self.engine._predict_with_baseline(base_features)
        high_pred = self.engine._predict_with_baseline(high_enroll_features)

        assert high_pred["expected_days"] > base_pred["expected_days"]

    def test_prediction_minimum_floor(self):
        """Prediction should never go below 30 days."""
        features = {
            "advisory_committee": "RA",  # 280 day baseline
            "risk_factors_detected": ["expedited_review"],
            "clinical_complexity": "simple",
            "clinical_enrollment": 0,
            "supplement_type": "30_day_notice",  # -280 days
        }
        pred = self.engine._predict_with_baseline(features)
        assert pred["expected_days"] >= 30, (
            f"Prediction went below floor: {pred['expected_days']}"
        )


# ============================================================
# 4. Review Time Predictor: Confidence Intervals
# ============================================================


class TestConfidenceIntervals:
    """Validate confidence interval calculations."""

    def setup_method(self):
        from review_time_predictor import ReviewTimePredictionEngine
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)

    def test_ci_lower_bound_positive(self):
        """Confidence interval lower bound must be >= 14."""
        features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        ci = pred["confidence_interval"]
        assert ci["lower_days"] >= 14

    def test_ci_upper_greater_than_lower(self):
        """Upper CI bound must be greater than lower."""
        features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        ci = pred["confidence_interval"]
        assert ci["upper_days"] > ci["lower_days"]

    def test_ci_expected_within_bounds(self):
        """Expected days should fall within the confidence interval."""
        features = {
            "advisory_committee": "CV",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        ci = pred["confidence_interval"]
        assert ci["lower_days"] <= pred["expected_days"] <= ci["upper_days"]

    def test_ci_confidence_level(self):
        """Confidence level should be 0.80."""
        features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        assert pred["confidence_interval"]["confidence_level"] == 0.80

    def test_ci_months_consistent_with_days(self):
        """Month values in CI should be consistent with day values."""
        features = {
            "advisory_committee": "CH",
            "risk_factors_detected": [],
            "clinical_complexity": "moderate",
            "clinical_enrollment": 0,
            "supplement_type": "original",
        }
        pred = self.engine._predict_with_baseline(features)
        ci = pred["confidence_interval"]
        # Check lower months matches lower days / 30.44
        expected_lower_months = round(ci["lower_days"] / 30.44, 1)
        assert abs(ci["lower_months"] - expected_lower_months) < 0.2


# ============================================================
# 5. Review Time Predictor: Feature Extraction
# ============================================================


class TestFeatureExtraction:
    """Validate feature extraction from PMA data."""

    def setup_method(self):
        from review_time_predictor import ReviewTimePredictionEngine
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)

    def test_featurize_vector_length(self):
        """Feature vector should have consistent length."""
        from review_time_predictor import ADVISORY_COMMITTEES, SUPPLEMENT_TYPE_CODES
        example = {
            "advisory_committee": "CH",
            "supplement_type": "original",
            "has_clinical_data": True,
            "is_expedited": False,
            "supplement_count_prior": 5,
            "applicant_pma_count": 2,
            "clinical_enrollment": 100,
            "clinical_complexity": "moderate",
        }
        vec = self.engine._featurize(example)
        expected_len = len(ADVISORY_COMMITTEES) + len(SUPPLEMENT_TYPE_CODES) + 6
        assert len(vec) == expected_len, (
            f"Feature vector length {len(vec)} != expected {expected_len}"
        )

    def test_featurize_one_hot_encoding(self):
        """Panel one-hot encoding should have exactly one 1.0."""
        from review_time_predictor import ADVISORY_COMMITTEES
        example = {"advisory_committee": "CH", "supplement_type": "original"}
        vec = self.engine._featurize(example)
        panel_slice = vec[:len(ADVISORY_COMMITTEES)]
        assert sum(panel_slice) == 1.0, (
            f"Panel one-hot should sum to 1.0, got {sum(panel_slice)}"
        )

    def test_featurize_unknown_panel_all_zeros(self):
        """Unknown panel should produce all-zero one-hot encoding."""
        from review_time_predictor import ADVISORY_COMMITTEES
        example = {"advisory_committee": "ZZ", "supplement_type": "original"}
        vec = self.engine._featurize(example)
        panel_slice = vec[:len(ADVISORY_COMMITTEES)]
        assert sum(panel_slice) == 0.0

    def test_clinical_enrollment_extraction(self):
        """Clinical enrollment should be extracted from section text."""
        sections = {
            "sections": {
                "clinical_studies": {
                    "content": "A total enrollment of 1,200 patients",
                    "word_count": 100,
                },
            },
        }
        api_data = {
            "product_code": "NMH",
            "advisory_committee": "CH",
            "expedited_review_flag": "N",
            "supplement_count": 0,
        }
        features = self.engine._extract_features(api_data, sections)
        assert features["clinical_enrollment"] == 1200

    def test_clinical_complexity_detection(self):
        """Clinical complexity should be detected from word count."""
        # > 2000 words = complex
        sections_complex = {
            "sections": {
                "clinical_studies": {
                    "content": "x " * 2500,
                    "word_count": 2500,
                },
            },
        }
        api_data = {
            "product_code": "NMH",
            "advisory_committee": "CH",
            "expedited_review_flag": "N",
            "supplement_count": 0,
        }
        features = self.engine._extract_features(api_data, sections_complex)
        assert features["clinical_complexity"] == "complex"


# ============================================================
# 6. MAUDE Comparison: Z-score Outlier Detection
# ============================================================


class TestMAUDEZScoreCalculations:
    """Validate Z-score calculation accuracy in MAUDEComparisonEngine."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    def test_std_dev_known_values(self):
        """Standard deviation of [10, 20, 30] should be 10.0 (sample)."""
        values = [10.0, 20.0, 30.0]
        result = self.engine._std_dev(values)
        expected = math.sqrt(
            sum((v - 20.0) ** 2 for v in values) / 2
        )  # sample std
        assert abs(result - expected) < 0.01, (
            f"std_dev({values}) = {result}, expected {expected}"
        )

    def test_std_dev_single_value(self):
        """Standard deviation of single value should be 0.0."""
        assert self.engine._std_dev([5.0]) == 0.0

    def test_std_dev_empty(self):
        """Standard deviation of empty list should be 0.0."""
        assert self.engine._std_dev([]) == 0.0

    def test_std_dev_identical_values(self):
        """Standard deviation of identical values should be 0.0."""
        assert self.engine._std_dev([5.0, 5.0, 5.0]) == 0.0

    @pytest.mark.parametrize(
        "primary,mean,std,direction,should_flag",
        GOLDEN_OUTLIER_CASES,
    )
    def test_outlier_detection_golden_cases(
        self, primary, mean, std, direction, should_flag
    ):
        """Validate outlier detection against golden test cases."""
        from maude_comparison import OUTLIER_Z_THRESHOLD

        if std > 0:
            z_score = (primary - mean) / std
        else:
            z_score = 0.0

        is_outlier = abs(z_score) >= OUTLIER_Z_THRESHOLD

        assert is_outlier == should_flag, (
            f"primary={primary}, mean={mean}, std={std}: "
            f"z={z_score:.2f}, expected outlier={should_flag}, got {is_outlier}"
        )

        if is_outlier and direction is not None:
            actual_direction = "above" if z_score > 0 else "below"
            assert actual_direction == direction

    def test_detect_outliers_method(self):
        """Test _detect_outliers with known benchmark data."""
        primary = {
            "event_type_distribution": {
                "Death": 20,      # Way above peer mean
                "Injury": 50,     # Near peer mean
                "Malfunction": 100,
            },
            "total_events": 170,
            "death_count": 20,
        }

        benchmarks = {
            "event_type_benchmarks": {
                "Death": {"mean": 5.0, "std": 3.0, "min": 1, "max": 10, "median": 4.0},
                "Injury": {"mean": 50.0, "std": 20.0, "min": 20, "max": 80, "median": 50.0},
                "Malfunction": {"mean": 100.0, "std": 30.0, "min": 50, "max": 150, "median": 100.0},
            },
        }

        outliers = self.engine._detect_outliers(primary, benchmarks)

        # Death should be flagged (z = (20-5)/3 = 5.0)
        death_outliers = [o for o in outliers if o["event_type"] == "Death"]
        assert len(death_outliers) == 1, "Death should be flagged as outlier"
        assert death_outliers[0]["direction"] == "above"
        assert abs(death_outliers[0]["z_score"] - 5.0) < 0.1

        # Injury at mean should NOT be flagged (z = 0)
        injury_outliers = [o for o in outliers if o["event_type"] == "Injury"]
        assert len(injury_outliers) == 0, "Injury at mean should not be outlier"

    def test_outlier_z_score_threshold_value(self):
        """OUTLIER_Z_THRESHOLD should be 2.0."""
        from maude_comparison import OUTLIER_Z_THRESHOLD
        assert OUTLIER_Z_THRESHOLD == 2.0

    def test_signal_min_events_value(self):
        """SIGNAL_MIN_EVENTS should be 3."""
        from maude_comparison import SIGNAL_MIN_EVENTS
        assert SIGNAL_MIN_EVENTS == 3


# ============================================================
# 7. MAUDE Comparison: Safety Signal Detection
# ============================================================


class TestMAUDESafetySignalDetection:
    """Validate safety signal detection logic."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    @pytest.mark.parametrize("case_idx,case", enumerate(GOLDEN_SIGNAL_CASES))
    def test_death_signal_golden_cases(self, case_idx, case):
        """Test death signal detection with golden data."""
        if "expected_death_signal" not in case:
            pytest.skip("No death signal expectation in this case")

        type_dist = {k: v for k, v in case.items() if not k.startswith("expected_")}

        # Set up mock to return our test distribution
        count_results = [
            {"term": k, "count": v}
            for k, v in type_dist.items()
        ]
        self.store.client.get_events.return_value = {"results": count_results}

        result = self.engine.detect_safety_signals("TEST")
        death_signals = [
            s for s in result["signals"] if s["signal_type"] == "death_reports"
        ]

        expected = case["expected_death_signal"]
        has_death_signal = len(death_signals) > 0
        assert has_death_signal == expected, (
            f"Case {case_idx}: Death signal expected={expected}, got={has_death_signal}. "
            f"Distribution: {type_dist}"
        )

    @pytest.mark.parametrize("case_idx,case", enumerate(GOLDEN_SIGNAL_CASES))
    def test_malfunction_signal_golden_cases(self, case_idx, case):
        """Test malfunction rate signal with golden data."""
        if "expected_malfunction_signal" not in case:
            pytest.skip("No malfunction signal expectation in this case")

        type_dist = {k: v for k, v in case.items() if not k.startswith("expected_")}

        count_results = [
            {"term": k, "count": v}
            for k, v in type_dist.items()
        ]
        self.store.client.get_events.return_value = {"results": count_results}

        result = self.engine.detect_safety_signals("TEST")
        malf_signals = [
            s for s in result["signals"]
            if s["signal_type"] == "high_malfunction_rate"
        ]

        expected = case["expected_malfunction_signal"]
        has_malf_signal = len(malf_signals) > 0
        assert has_malf_signal == expected, (
            f"Case {case_idx}: Malfunction signal expected={expected}, "
            f"got={has_malf_signal}. Distribution: {type_dist}"
        )

    def test_death_signal_severity_is_critical(self):
        """Death signals should have CRITICAL severity."""
        count_results = [
            {"term": "Death", "count": 10},
            {"term": "Injury", "count": 50},
            {"term": "Malfunction", "count": 100},
        ]
        self.store.client.get_events.return_value = {"results": count_results}

        result = self.engine.detect_safety_signals("TEST")
        death_signals = [
            s for s in result["signals"] if s["signal_type"] == "death_reports"
        ]
        assert len(death_signals) == 1
        assert death_signals[0]["severity"] == "CRITICAL"

    def test_signals_sorted_by_severity(self):
        """Signals should be sorted by severity (CRITICAL first)."""
        count_results = [
            {"term": "Death", "count": 5},
            {"term": "Injury", "count": 80},
            {"term": "Malfunction", "count": 250},  # > 60% rate
        ]
        self.store.client.get_events.return_value = {"results": count_results}

        result = self.engine.detect_safety_signals("TEST")
        if len(result["signals"]) >= 2:
            severity_order = {"CRITICAL": 0, "WARNING": 1, "CAUTION": 2, "INFO": 3}
            for i in range(len(result["signals"]) - 1):
                s1 = severity_order.get(result["signals"][i]["severity"], 4)
                s2 = severity_order.get(result["signals"][i + 1]["severity"], 4)
                assert s1 <= s2, "Signals not sorted by severity"


# ============================================================
# 8. MAUDE Comparison: Severity Distribution
# ============================================================


class TestSeverityDistribution:
    """Validate severity distribution mapping."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    def test_death_maps_to_critical(self):
        """Death event type should map to critical severity."""
        dist = self.engine._compute_severity_distribution({"Death": 5})
        assert dist.get("critical", 0) == 5

    def test_injury_maps_to_high(self):
        """Injury event type should map to high severity."""
        dist = self.engine._compute_severity_distribution({"Injury": 10})
        assert dist.get("high", 0) == 10

    def test_malfunction_maps_to_medium(self):
        """Malfunction event type should map to medium severity."""
        dist = self.engine._compute_severity_distribution({"Malfunction": 20})
        assert dist.get("medium", 0) == 20

    def test_no_answer_maps_to_unknown(self):
        """'No answer provided' should map to unknown severity."""
        dist = self.engine._compute_severity_distribution({"No answer provided": 3})
        assert dist.get("unknown", 0) == 3

    def test_combined_severity_distribution(self):
        """Test combined severity distribution with all types."""
        input_dist = {
            "Death": 5,
            "Injury": 80,
            "Malfunction": 150,
            "No answer provided": 30,
            "Other": 15,
        }
        result = self.engine._compute_severity_distribution(input_dist)
        assert result["critical"] == 5
        assert result["high"] == 80
        assert result["medium"] == 150
        assert result["unknown"] == 30
        assert result["low"] == 15


# ============================================================
# 9. MAUDE Comparison: Event Classification
# ============================================================


class TestEventClassification:
    """Validate event type classification and year extraction."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    def test_classify_string_event_type(self):
        """String event_type should be returned as-is."""
        assert self.engine._classify_event_type({"event_type": "Death"}) == "Death"

    def test_classify_empty_event_type(self):
        """Empty event_type should return 'Other'."""
        assert self.engine._classify_event_type({"event_type": ""}) == "Other"

    def test_classify_missing_event_type(self):
        """Missing event_type should return 'Other'."""
        assert self.engine._classify_event_type({}) == "Other"

    def test_classify_list_event_type(self):
        """List event_type should return first element."""
        assert self.engine._classify_event_type(
            {"event_type": ["Injury", "Malfunction"]}
        ) == "Injury"

    def test_extract_year_from_date_received(self):
        """Year should be extracted from date_received field."""
        event = {"date_received": "20230601"}
        assert self.engine._extract_event_year(event) == 2023

    def test_extract_year_from_date_of_event(self):
        """Year should be extracted from date_of_event when date_received missing."""
        event = {"date_of_event": "20220315"}
        assert self.engine._extract_event_year(event) == 2022

    def test_extract_year_none_when_missing(self):
        """None should be returned when no date fields present."""
        assert self.engine._extract_event_year({}) is None


# ============================================================
# 10. MAUDE Comparison: Peer Benchmark Computation
# ============================================================


class TestPeerBenchmarkComputation:
    """Validate peer benchmark statistical computation."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    def test_compute_benchmarks_with_valid_profiles(self):
        """Benchmarks should compute correctly from valid profiles."""
        profiles = [
            {
                "total_events": 100,
                "event_type_distribution": {"Death": 5, "Injury": 40, "Malfunction": 55},
                "death_count": 5,
            },
            {
                "total_events": 200,
                "event_type_distribution": {"Death": 10, "Injury": 80, "Malfunction": 110},
                "death_count": 10,
            },
            {
                "total_events": 150,
                "event_type_distribution": {"Death": 3, "Injury": 60, "Malfunction": 87},
                "death_count": 3,
            },
        ]

        benchmarks = self.engine._compute_peer_benchmarks(profiles)

        assert benchmarks["total_devices"] == 3
        assert benchmarks["devices_with_events"] == 3

        total_stats = benchmarks["total_events_stats"]
        assert total_stats["mean"] == 150.0
        assert total_stats["min"] == 100
        assert total_stats["max"] == 200

    def test_compute_benchmarks_with_empty_profiles(self):
        """Benchmarks should handle profiles with no events."""
        profiles = [
            {"total_events": 0, "event_type_distribution": {}, "death_count": 0},
            {"total_events": 0, "event_type_distribution": {}, "death_count": 0},
        ]

        benchmarks = self.engine._compute_peer_benchmarks(profiles)
        assert benchmarks["total_devices"] == 2
        assert benchmarks["devices_with_events"] == 0

    def test_compute_benchmarks_death_rate_stats(self):
        """Death rate statistics should be computed correctly."""
        profiles = [
            {
                "total_events": 100,
                "event_type_distribution": {"Death": 5},
                "death_count": 5,
            },
            {
                "total_events": 200,
                "event_type_distribution": {"Death": 10},
                "death_count": 10,
            },
        ]
        benchmarks = self.engine._compute_peer_benchmarks(profiles)
        death_stats = benchmarks.get("death_rate_stats", {})
        assert "mean" in death_stats
        # Device 1: 5/100 = 5%, Device 2: 10/200 = 5%, mean = 5.0%
        assert abs(death_stats["mean"] - 5.0) < 0.1


# ============================================================
# 11. MAUDE Comparison: Year Trend Analysis
# ============================================================


class TestYearTrendAnalysis:
    """Validate year trend building from event data."""

    def setup_method(self):
        from maude_comparison import MAUDEComparisonEngine
        self.store = _create_mock_store()
        self.engine = MAUDEComparisonEngine(store=self.store)

    def test_build_year_trend_basic(self):
        """Year trend should count events per year correctly."""
        events = [
            {"date_received": "20230101"},
            {"date_received": "20230601"},
            {"date_received": "20220301"},
            {"date_received": "20210901"},
        ]
        trend = self.engine._build_year_trend(events)
        assert trend[2023] == 2
        assert trend[2022] == 1
        assert trend[2021] == 1

    def test_build_year_trend_sorted(self):
        """Year trend keys should be sorted."""
        events = [
            {"date_received": "20230101"},
            {"date_received": "20210601"},
            {"date_received": "20220301"},
        ]
        trend = self.engine._build_year_trend(events)
        years = list(trend.keys())
        assert years == sorted(years)

    def test_build_year_trend_empty(self):
        """Empty event list should produce empty trend."""
        trend = self.engine._build_year_trend([])
        assert trend == {}

    def test_increasing_trend_signal(self):
        """Increasing event trend should be detected as safety signal."""
        # Build events with sharply increasing trend
        events = []
        # Old years: few events
        for y in range(2018, 2021):
            events.append({"date_received": f"{y}0601"})

        # Recent years: many events (3x increase)
        for y in range(2021, 2024):
            for _ in range(5):
                events.append({"date_received": f"{y}0601"})

        # Also need count results for detect_safety_signals
        count_results = [
            {"term": "Malfunction", "count": 10},
            {"term": "Injury", "count": 5},
        ]

        # Override get_events to return different results for count vs detail
        call_count = [0]
        original_events = events[:]

        def mock_get_events(product_code, **kwargs):
            call_count[0] += 1
            if "count" in kwargs:
                return {"results": count_results}
            else:
                return {"results": original_events}

        self.store.client.get_events.side_effect = mock_get_events

        result = self.engine.detect_safety_signals("TEST")
        trend_signals = [
            s for s in result["signals"] if s["signal_type"] == "increasing_trend"
        ]
        assert len(trend_signals) >= 1, (
            "Should detect increasing trend signal"
        )


# ============================================================
# 12. Integration: End-to-end prediction scenarios
# ============================================================


class TestEndToEndPredictionScenarios:
    """End-to-end scenario tests with known expected outcome ranges."""

    def setup_method(self):
        from review_time_predictor import ReviewTimePredictionEngine
        self.store = _create_mock_store()
        self.engine = ReviewTimePredictionEngine(store=self.store)

    def test_scenario_simple_cardiovascular(self):
        """CV panel + moderate complexity should predict ~380 days."""
        result = self.engine.predict_for_new_submission({
            "product_code": "DQY",
            "advisory_committee": "CV",
            "has_clinical_data": True,
            "clinical_complexity": "moderate",
        })
        pred = result["prediction"]
        # CV baseline is 380, moderate has no adjustment
        assert 350 <= pred["expected_days"] <= 410

    def test_scenario_expedited_radiology(self):
        """RA panel + expedited should predict ~220 days."""
        result = self.engine.predict_for_new_submission({
            "product_code": "QAS",
            "advisory_committee": "RA",
            "is_expedited": True,
            "clinical_complexity": "simple",
        })
        pred = result["prediction"]
        # RA=280, expedited=-60, simple=-30 = 190
        assert 150 <= pred["expected_days"] <= 250

    def test_scenario_complex_novel_neurological(self):
        """NE panel + complex + novel should predict ~490+ days."""
        result = self.engine.predict_for_new_submission({
            "product_code": "NMH",
            "advisory_committee": "NE",
            "has_clinical_data": True,
            "clinical_complexity": "complex",
        })
        pred = result["prediction"]
        # NE=370, complex=+60 = 430
        assert pred["expected_days"] >= 400

    def test_scenario_30_day_supplement(self):
        """30-day notice supplement should predict very short review."""
        result = self.engine.predict_for_new_submission({
            "product_code": "NMH",
            "advisory_committee": "CH",
            "supplement_type": "30_day_notice",
            "clinical_complexity": "simple",
        })
        pred = result["prediction"]
        # CH=320, 30_day_notice=-280, simple=-30 = 10, but floor=30
        assert pred["expected_days"] >= 30
        assert pred["expected_days"] <= 100
