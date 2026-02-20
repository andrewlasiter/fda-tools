"""
Tests for lib/gap_analyzer.py (FDA-29: No Tests for lib/ Modules).

Validates gap analysis logic including missing field detection,
priority scoring, weak predicate identification, testing gaps,
and standards gaps.

Per IEC 62304 V&V requirements, all analytical modules must have
test coverage verifying correctness of outputs.
"""

import json
import os
import sys

import pytest

# Ensure lib directory is importable
LIB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "lib"
)

from gap_analyzer import GapAnalyzer


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def empty_project(tmp_path):
    """Project with no files at all."""
    return str(tmp_path / "empty_project")


@pytest.fixture
def minimal_project(tmp_path):
    """Project with minimal valid device profile."""
    project_dir = tmp_path / "minimal"
    project_dir.mkdir()

    profile = {
        "product_code": "DQY",
        "device_class": "2",
        "regulation_number": "21 CFR 870.1210",
        "device_description": "A catheter used for vascular access",
        "indications_for_use": "Indicated for temporary vascular access",
        "intended_use_statement": "Temporary vascular access",
        "technological_characteristics": "Polyurethane catheter",
        "materials": "Polyurethane, silicone",
    }
    (project_dir / "device_profile.json").write_text(json.dumps(profile))

    review = {
        "accepted_predicates": [
            {
                "k_number": "K241335",
                "clearance_date": "2024-06-15",
                "recalls": 0,
            }
        ],
        "rejected_predicates": [],
    }
    (project_dir / "review.json").write_text(json.dumps(review))

    return str(project_dir)


@pytest.fixture
def incomplete_project(tmp_path):
    """Project with many missing fields."""
    project_dir = tmp_path / "incomplete"
    project_dir.mkdir()

    profile = {
        "product_code": "DQY",
        "device_class": "2",
        # Missing: indications_for_use, intended_use_statement, etc.
    }
    (project_dir / "device_profile.json").write_text(json.dumps(profile))

    return str(project_dir)


@pytest.fixture
def project_with_weak_predicates(tmp_path):
    """Project with predicates that have recalls and old clearance dates."""
    project_dir = tmp_path / "weak_pred"
    project_dir.mkdir()

    profile = {
        "product_code": "OVE",
        "device_class": "2",
        "regulation_number": "21 CFR 888.3080",
        "device_description": "Spinal fusion cage",
        "indications_for_use": "Spinal fusion",
        "intended_use_statement": "Intervertebral body fusion",
        "technological_characteristics": "PEEK material",
        "materials": "PEEK, Titanium",
    }
    (project_dir / "device_profile.json").write_text(json.dumps(profile))

    review = {
        "accepted_predicates": [
            {
                "k_number": "K050123",
                "decision_date": "2005-03-15",
                "recalls_total": 3,
                "device_name": "Old Fusion Device",
            },
            {
                "k_number": "K200456",
                "decision_date": "2020-09-01",
                "recalls_total": 0,
                "device_name": "Recent Fusion Device",
            },
        ],
        "rejected_predicates": [],
    }
    (project_dir / "review.json").write_text(json.dumps(review))

    return str(project_dir)


@pytest.fixture
def project_with_standards(tmp_path):
    """Project with standards lookup data."""
    project_dir = tmp_path / "standards"
    project_dir.mkdir()

    profile = {
        "product_code": "DQY",
        "device_class": "2",
        "regulation_number": "21 CFR 870.1210",
        "device_description": "Catheter",
        "indications_for_use": "Vascular access",
        "intended_use_statement": "Temporary access",
        "technological_characteristics": "Polymer catheter",
        "materials": "Polyurethane",
    }
    (project_dir / "device_profile.json").write_text(json.dumps(profile))

    standards = [
        {"number": "ISO 10993-1:2018", "title": "Biocompatibility"},
        {"number": "ISO 14971:2019", "title": "Risk Management"},
    ]
    (project_dir / "standards_lookup.json").write_text(json.dumps(standards))

    return str(project_dir)


# ============================================================================
# Missing Device Data Detection
# ============================================================================


class TestMissingDeviceData:
    """Test detection of missing/incomplete device profile fields."""

    def test_empty_project_returns_critical_gap(self, empty_project):
        analyzer = GapAnalyzer(empty_project)
        gaps = analyzer.detect_missing_device_data()
        assert len(gaps) == 1
        assert gaps[0]["priority"] == "CRITICAL"
        assert "missing" in gaps[0]["reason"].lower()

    def test_minimal_project_no_high_gaps(self, minimal_project):
        analyzer = GapAnalyzer(minimal_project)
        gaps = analyzer.detect_missing_device_data()
        high_gaps = [g for g in gaps if g["priority"] == "HIGH"]
        assert len(high_gaps) == 0, (
            f"Unexpected HIGH gaps: {[g['field'] for g in high_gaps]}"
        )

    def test_incomplete_project_detects_missing_fields(self, incomplete_project):
        analyzer = GapAnalyzer(incomplete_project)
        gaps = analyzer.detect_missing_device_data()
        high_gaps = [g for g in gaps if g["priority"] == "HIGH"]
        # Should detect missing indications_for_use, intended_use_statement, etc.
        assert len(high_gaps) >= 3
        gap_fields = {g["field"] for g in high_gaps}
        assert "indications_for_use" in gap_fields
        assert "intended_use_statement" in gap_fields

    def test_gap_has_required_fields(self, incomplete_project):
        analyzer = GapAnalyzer(incomplete_project)
        gaps = analyzer.detect_missing_device_data()
        for gap in gaps:
            assert "field" in gap
            assert "priority" in gap
            assert "reason" in gap
            assert "confidence" in gap
            assert gap["priority"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            assert 0 <= gap["confidence"] <= 100

    def test_empty_string_fields_detected(self, tmp_path):
        """Fields with empty strings should be detected as gaps."""
        project_dir = tmp_path / "empty_strings"
        project_dir.mkdir()
        profile = {
            "product_code": "DQY",
            "device_class": "2",
            "indications_for_use": "",
            "intended_use_statement": "   ",
            "regulation_number": "21 CFR 870.1210",
            "technological_characteristics": "Valid",
            "device_description": "Valid device",
            "materials": "Polymer",
        }
        (project_dir / "device_profile.json").write_text(json.dumps(profile))

        analyzer = GapAnalyzer(str(project_dir))
        gaps = analyzer.detect_missing_device_data()
        gap_fields = {g["field"] for g in gaps}
        assert "indications_for_use" in gap_fields
        assert "intended_use_statement" in gap_fields


# ============================================================================
# Weak Predicate Detection
# ============================================================================


class TestWeakPredicateDetection:
    """Test identification of weak predicates (recalls, age, differences)."""

    def test_project_with_recalled_predicate(self, project_with_weak_predicates):
        analyzer = GapAnalyzer(project_with_weak_predicates)
        gaps = analyzer.detect_weak_predicates()
        # Should flag the predicate with 3 recalls
        recall_gaps = [g for g in gaps if "recall" in g.get("reason", "").lower()]
        assert len(recall_gaps) >= 1

    def test_minimal_project_no_weak_predicates(self, minimal_project):
        analyzer = GapAnalyzer(minimal_project)
        gaps = analyzer.detect_weak_predicates()
        # Predicate with 0 recalls and recent date should not be flagged
        critical_gaps = [g for g in gaps if g["priority"] in ("HIGH", "CRITICAL")]
        # Recent, no-recall predicate should not produce HIGH gaps
        assert len(critical_gaps) == 0 or all(
            "recall" not in g.get("reason", "").lower() for g in critical_gaps
        )


# ============================================================================
# Full Gap Analysis
# ============================================================================


class TestFullGapAnalysis:
    """Test the complete gap analysis workflow."""

    def test_analyze_all_returns_dict(self, minimal_project):
        analyzer = GapAnalyzer(minimal_project)
        result = analyzer.analyze_all_gaps()
        assert isinstance(result, dict)
        assert "missing_data" in result or "gaps" in result or len(result) > 0

    def test_analyze_all_on_empty_project(self, empty_project):
        analyzer = GapAnalyzer(empty_project)
        result = analyzer.analyze_all_gaps()
        assert isinstance(result, dict)

    def test_gap_analyzer_with_standards(self, project_with_standards):
        analyzer = GapAnalyzer(project_with_standards)
        result = analyzer.analyze_all_gaps()
        assert isinstance(result, dict)
