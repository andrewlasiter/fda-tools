"""
Tests for lib/predicate_diversity.py (FDA-29: No Tests for lib/ Modules).

Validates the 5-dimension predicate diversity scoring system that
detects "echo chamber" risk in 510(k) predicate selections.

Scoring dimensions:
1. Manufacturer diversity (0-30 pts)
2. Technology diversity (0-30 pts)
3. Age diversity (0-25 pts)
4. Regulatory pathway diversity (0-10 pts)
5. Geographic diversity (0-10 pts)
"""

import os
import sys

import pytest

# Ensure lib directory is importable
LIB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "lib"
)
sys.path.insert(0, LIB_DIR)

from predicate_diversity import PredicateDiversityAnalyzer


# ============================================================================
# Test Data
# ============================================================================


def _make_predicate(
    k_number="K241335",
    manufacturer="Acme Medical",
    device_name="Test Device",
    clearance_date="2024-06-15",
    product_code="DQY",
    decision_description="A medical device",
    review_panel="CV",
    contact_country="US",
):
    return {
        "k_number": k_number,
        "manufacturer": manufacturer,
        "device_name": device_name,
        "clearance_date": clearance_date,
        "product_code": product_code,
        "decision_description": decision_description,
        "review_panel": review_panel,
        "contact_country": contact_country,
    }


@pytest.fixture
def diverse_predicates():
    """Predicates from multiple manufacturers, years, and countries."""
    return [
        _make_predicate("K241335", "Acme Medical", "CardioStent A",
                        "2024-06-15", "DQY", "Drug-coated stent", "CV", "US"),
        _make_predicate("K221001", "BioTech Corp", "FlowCath B",
                        "2022-03-10", "DQY", "Polymer catheter", "CV", "DE"),
        _make_predicate("K190500", "MedDevice Inc", "VascuLine C",
                        "2019-11-20", "DQY", "Metallic stent", "CV", "JP"),
        _make_predicate("K150200", "CardioSystems", "HeartFlow D",
                        "2015-05-01", "DQY", "Silicone catheter", "CV", "US"),
    ]


@pytest.fixture
def homogeneous_predicates():
    """All predicates from same manufacturer, same year, same country."""
    return [
        _make_predicate("K241001", "Acme Medical", "Device A",
                        "2024-01-15", "DQY", "Polymer catheter A", "CV", "US"),
        _make_predicate("K241002", "Acme Medical", "Device B",
                        "2024-03-10", "DQY", "Polymer catheter B", "CV", "US"),
        _make_predicate("K241003", "Acme Medical", "Device C",
                        "2024-06-20", "DQY", "Polymer catheter C", "CV", "US"),
    ]


@pytest.fixture
def single_predicate():
    """Only one predicate device."""
    return [
        _make_predicate("K241335", "Acme Medical", "Solo Device",
                        "2024-06-15", "DQY", "A catheter", "CV", "US"),
    ]


# ============================================================================
# Score Range Tests
# ============================================================================


class TestScoreRanges:
    """Test that scores fall within valid ranges."""

    def test_diverse_predicates_score_high(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        assert 0 <= result["total_score"] <= 100
        # Diverse set should score at least FAIR (40+)
        assert result["total_score"] >= 40

    def test_homogeneous_predicates_score_low(self, homogeneous_predicates):
        analyzer = PredicateDiversityAnalyzer(homogeneous_predicates)
        result = analyzer.analyze()
        assert 0 <= result["total_score"] <= 100
        # Homogeneous set should score below GOOD (60)
        assert result["total_score"] < 60

    def test_single_predicate_score(self, single_predicate):
        analyzer = PredicateDiversityAnalyzer(single_predicate)
        result = analyzer.analyze()
        assert 0 <= result["total_score"] <= 100

    def test_empty_predicates(self):
        analyzer = PredicateDiversityAnalyzer([])
        result = analyzer.analyze()
        assert result["total_score"] == 0


# ============================================================================
# Dimension Score Tests
# ============================================================================


class TestDimensionScores:
    """Test individual dimension scoring."""

    def test_manufacturer_score_range(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        assert 0 <= result["manufacturer_score"] <= 30

    def test_technology_score_range(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        assert 0 <= result["technology_score"] <= 30

    def test_age_score_range(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        assert 0 <= result["age_score"] <= 25

    def test_manufacturer_diversity_detected(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        # 4 different manufacturers should score well
        assert result["manufacturer_score"] >= 15

    def test_single_manufacturer_low_score(self, homogeneous_predicates):
        analyzer = PredicateDiversityAnalyzer(homogeneous_predicates)
        result = analyzer.analyze()
        # All same manufacturer should score very low
        assert result["manufacturer_score"] <= 10


# ============================================================================
# Grading Tests
# ============================================================================


class TestGrading:
    """Test grade assignment based on total score."""

    def test_grade_is_assigned(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        assert "grade" in result
        assert result["grade"] in ("EXCELLENT", "GOOD", "FAIR", "POOR")

    def test_result_has_required_keys(self, diverse_predicates):
        analyzer = PredicateDiversityAnalyzer(diverse_predicates)
        result = analyzer.analyze()
        required_keys = [
            "total_score",
            "manufacturer_score",
            "technology_score",
            "age_score",
            "grade",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_missing_manufacturer_field(self):
        predicates = [
            {"k_number": "K241001", "clearance_date": "2024-01-15"},
            {"k_number": "K221001", "clearance_date": "2022-03-10"},
        ]
        analyzer = PredicateDiversityAnalyzer(predicates)
        result = analyzer.analyze()
        # Should not crash, should return valid result
        assert isinstance(result["total_score"], (int, float))

    def test_missing_dates(self):
        predicates = [
            _make_predicate("K241001", clearance_date=""),
            _make_predicate("K221001", clearance_date="invalid-date"),
        ]
        analyzer = PredicateDiversityAnalyzer(predicates)
        result = analyzer.analyze()
        assert isinstance(result["total_score"], (int, float))

    def test_many_predicates(self):
        """10+ predicates should still work correctly."""
        predicates = [
            _make_predicate(
                f"K24{i:04d}",
                f"Manufacturer_{i % 5}",
                clearance_date=f"20{20 + i % 5}-06-15",
            )
            for i in range(15)
        ]
        analyzer = PredicateDiversityAnalyzer(predicates)
        result = analyzer.analyze()
        assert 0 <= result["total_score"] <= 100
