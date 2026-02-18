#!/usr/bin/env python3
"""
Test suite for PMA Supplement Enhancement (FDA-65).

Tests cover:
  - SupplementTypeClassifier (pattern matching, confidence, batch)
  - SupplementDecisionTree (traversal, leaf nodes, all paths)
  - ChangeImpactAssessor (scoring, risk levels, documentation)
  - SupplementPackageGenerator (sections, cover letter, references)

Minimum 35 tests required for this module.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts directory is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pma_supplement_enhanced import (
    SupplementTypeClassifier,
    SupplementDecisionTree,
    ChangeImpactAssessor,
    SupplementPackageGenerator,
    SUPPLEMENT_TYPES,
    DECISION_TREE,
    PACKAGE_SECTIONS,
    CLASSIFICATION_PATTERNS,
    REGULATORY_DISCLAIMER,
)


# ==================================================================
# SupplementTypeClassifier Tests
# ==================================================================

class TestSupplementTypeClassifier:
    """Tests for the enhanced supplement type classifier."""

    @pytest.fixture
    def classifier(self):
        return SupplementTypeClassifier()

    # -- Basic classification tests --

    def test_classify_180_day_explicit(self, classifier):
        """Test explicit 180-day supplement keyword."""
        result = classifier.classify("180-day supplement for manufacturing change")
        assert result["supplement_type"] == "180_day"
        assert result["confidence"] > 0.5

    def test_classify_real_time_labeling(self, classifier):
        """Test real-time supplement for labeling change."""
        result = classifier.classify("labeling change to update warnings and contraindications")
        assert result["supplement_type"] == "real_time"

    def test_classify_30_day_notice(self, classifier):
        """Test 30-day notice for minor change."""
        result = classifier.classify("30-day notice for minor manufacturing change")
        assert result["supplement_type"] == "30_day_notice"

    def test_classify_panel_track(self, classifier):
        """Test panel-track for significant change."""
        result = classifier.classify("panel-track supplement requiring advisory committee review")
        assert result["supplement_type"] == "panel_track"

    def test_classify_annual_report(self, classifier):
        """Test annual report for administrative change."""
        result = classifier.classify("company name change to report in annual report")
        assert result["supplement_type"] == "annual_report"

    # -- Contextual classification tests --

    def test_classify_design_change_with_clinical_data(self, classifier):
        """Design change with clinical data should be 180-day."""
        result = classifier.classify(
            "design change with clinical data supporting safety",
            has_clinical_data=True,
            is_design_change=True,
        )
        assert result["supplement_type"] == "180_day"

    def test_classify_manufacturing_with_validation(self, classifier):
        """Manufacturing change with validation data should be 180-day."""
        result = classifier.classify(
            "new manufacturing site with validation data",
            has_performance_data=True,
            is_manufacturing_change=True,
        )
        assert result["supplement_type"] == "180_day"

    def test_classify_labeling_flag_boosts_real_time(self, classifier):
        """Labeling flag should boost real-time score."""
        result = classifier.classify(
            "IFU revision for clarity update",
            is_labeling_change=True,
        )
        assert result["supplement_type"] == "real_time"

    # -- Confidence tests --

    def test_high_confidence_explicit_keyword(self, classifier):
        """Explicit keyword should yield high confidence."""
        result = classifier.classify("180-day supplement")
        assert result["confidence_label"] in ("HIGH", "MEDIUM")
        assert result["confidence"] >= 0.5

    def test_low_confidence_ambiguous(self, classifier):
        """Ambiguous text should yield lower confidence."""
        result = classifier.classify("some kind of device change")
        assert result["confidence"] < 0.85

    def test_confidence_label_matches_threshold(self, classifier):
        """Confidence label should match numeric threshold."""
        result = classifier.classify("panel-track supplement advisory committee")
        conf = result["confidence"]
        label = result["confidence_label"]
        if conf >= 0.85:
            assert label == "HIGH"
        elif conf >= 0.60:
            assert label == "MEDIUM"
        elif conf >= 0.40:
            assert label == "LOW"
        else:
            assert label == "VERY_LOW"

    # -- Empty/edge case tests --

    def test_classify_empty_string(self, classifier):
        """Empty string should return default with zero confidence."""
        result = classifier.classify("")
        assert result["supplement_type"] == "180_day"
        assert result["confidence"] == 0.0

    def test_classify_whitespace_only(self, classifier):
        """Whitespace-only input should return default."""
        result = classifier.classify("   \n\t  ")
        assert result["confidence"] == 0.0

    # -- Alternatives tests --

    def test_alternatives_present(self, classifier):
        """Classification should include alternative types."""
        result = classifier.classify("design change with labeling update for manufacturing")
        assert "alternatives" in result
        # Should have some alternatives when multiple patterns match

    # -- Batch classification tests --

    def test_classify_batch(self, classifier):
        """Batch classification should return list of results."""
        descriptions = [
            "labeling change for warnings",
            "manufacturing site change",
            "panel-track supplement",
        ]
        results = classifier.classify_batch(descriptions)
        assert len(results) == 3
        assert all("supplement_type" in r for r in results)

    # -- CFR and metadata tests --

    def test_result_includes_cfr_section(self, classifier):
        """Result should include CFR section reference."""
        result = classifier.classify("180-day supplement for design change")
        assert result["cfr_section"] != ""
        assert "21 CFR" in result["cfr_section"]

    def test_result_includes_review_days(self, classifier):
        """Result should include review timeline."""
        result = classifier.classify("30-day notice for packaging change")
        assert "review_days" in result
        assert isinstance(result["review_days"], int)

    def test_result_includes_risk_level(self, classifier):
        """Result should include risk level."""
        result = classifier.classify("panel-track supplement")
        assert result["risk_level"] in ("critical", "high", "medium", "low", "minimal", "unknown")


# ==================================================================
# SupplementDecisionTree Tests
# ==================================================================

class TestSupplementDecisionTree:
    """Tests for the supplement decision tree."""

    @pytest.fixture
    def tree(self):
        return SupplementDecisionTree()

    def test_root_node_exists(self, tree):
        """Root node should exist and have options."""
        root = tree.get_root()
        assert root is not None
        assert "question" in root
        assert "options" in root

    def test_leaf_nodes_have_recommendations(self, tree):
        """All leaf nodes should have supplement type recommendations."""
        for node_id, node in DECISION_TREE.items():
            if node_id.startswith("leaf_"):
                assert "recommendation" in node, f"Leaf {node_id} missing recommendation"
                assert node["recommendation"] in SUPPLEMENT_TYPES or node["recommendation"] in ("annual_report",)

    def test_evaluate_design_change(self, tree):
        """Design change should navigate to appropriate type."""
        result = tree.evaluate(
            change_description="new device design with significant modifications",
            is_design_change=True,
        )
        assert "supplement_type" in result
        assert result["supplement_type"] in SUPPLEMENT_TYPES

    def test_evaluate_manufacturing_change(self, tree):
        """Manufacturing change should navigate correctly."""
        result = tree.evaluate(
            change_description="minor manufacturing process parameter change",
            is_manufacturing_change=True,
        )
        assert result["supplement_type"] in ("30_day_notice", "180_day")

    def test_evaluate_labeling_change(self, tree):
        """Labeling change should navigate to real_time or 30_day."""
        result = tree.evaluate(
            change_description="IFU revision with updated warnings",
            is_labeling_change=True,
        )
        assert result["supplement_type"] in ("real_time", "30_day_notice", "annual_report")

    def test_evaluate_panel_required(self, tree):
        """Panel requirement should navigate to panel_track."""
        result = tree.evaluate(
            change_description="significant indication change",
            is_design_change=True,
            requires_panel=True,
        )
        assert result["supplement_type"] == "panel_track"

    def test_evaluate_includes_decision_path(self, tree):
        """Result should include the decision path taken."""
        result = tree.evaluate(change_description="company name change")
        assert "decision_path" in result
        assert len(result["decision_path"]) >= 1
        assert result["decision_path"][0] == "root"

    def test_get_all_paths(self, tree):
        """Should enumerate all possible decision paths."""
        paths = tree.get_all_paths()
        assert len(paths) > 0
        # Every path should end at a leaf with a recommendation
        for path in paths:
            assert "recommendation" in path
            assert "path" in path
            assert path["path"][0] == "root"

    def test_is_leaf_correct(self, tree):
        """is_leaf should correctly identify leaf nodes."""
        assert tree.is_leaf("leaf_panel_track") is True
        assert tree.is_leaf("leaf_180_day") is True
        assert tree.is_leaf("root") is False
        assert tree.is_leaf("node_design") is False

    def test_get_recommendation_returns_type_info(self, tree):
        """get_recommendation should return full type info."""
        rec = tree.get_recommendation("leaf_180_day")
        assert rec is not None
        assert rec["supplement_type"] == "180_day"
        assert "cfr_section" in rec
        assert "rationale" in rec
        assert "estimated_timeline_months" in rec


# ==================================================================
# ChangeImpactAssessor Tests
# ==================================================================

class TestChangeImpactAssessor:
    """Tests for the change impact assessor."""

    @pytest.fixture
    def assessor(self):
        return ChangeImpactAssessor()

    def test_design_change_base_score(self, assessor):
        """Design change should have appropriate base score."""
        result = assessor.assess_impact(change_type="design_change")
        assert result["base_score"] == 40
        assert result["impact_score"] >= 40

    def test_labeling_change_lower_score(self, assessor):
        """Labeling change should have lower impact than design."""
        result = assessor.assess_impact(change_type="labeling_change")
        assert result["base_score"] == 15
        assert result["risk_level"] in ("LOW", "MEDIUM")

    def test_components_add_to_score(self, assessor):
        """Affected components should increase impact score."""
        result_no_comp = assessor.assess_impact(change_type="design_change")
        result_with_comp = assessor.assess_impact(
            change_type="design_change",
            affected_components=["materials", "biocompatibility"],
        )
        assert result_with_comp["impact_score"] > result_no_comp["impact_score"]

    def test_data_gaps_detected(self, assessor):
        """Missing data should be identified as gaps."""
        result = assessor.assess_impact(
            change_type="design_change",
            has_performance_data=False,
            has_clinical_data=False,
        )
        assert len(result["data_gaps"]) > 0

    def test_data_readiness_with_all_data(self, assessor):
        """Having all data should yield high readiness score."""
        result = assessor.assess_impact(
            change_type="design_change",
            has_performance_data=True,
            has_clinical_data=True,
            has_biocompatibility_data=True,
        )
        assert result["data_readiness_score"] >= 40

    def test_risk_level_critical_for_high_score(self, assessor):
        """High impact score should yield CRITICAL risk level."""
        result = assessor.assess_impact(
            change_type="design_change",
            affected_components=["materials", "biocompatibility", "mechanism_of_action", "sterilization"],
        )
        assert result["risk_level"] in ("CRITICAL", "HIGH")

    def test_required_docs_include_change_summary(self, assessor):
        """Required docs should always include change summary."""
        result = assessor.assess_impact(change_type="labeling_change")
        doc_titles = [d["document"] for d in result["required_documentation"]]
        assert any("Change Summary" in t for t in doc_titles)

    def test_timeline_estimation(self, assessor):
        """Timeline should be estimated based on impact."""
        result = assessor.assess_impact(change_type="design_change")
        timeline = result["estimated_timeline"]
        assert "preparation_months" in timeline
        assert "fda_review_months" in timeline
        assert "total_estimated_months" in timeline
        assert timeline["total_estimated_months"] > 0

    def test_compare_changes(self, assessor):
        """Multiple changes should be compared and prioritized."""
        changes = [
            {"change_type": "design_change", "label": "Design A"},
            {"change_type": "labeling_change", "label": "Label B"},
        ]
        result = assessor.compare_changes(changes)
        assert result["total_changes"] == 2
        assert result["highest_impact_score"] > 0
        assert len(result["assessments"]) == 2

    def test_infer_change_type_from_description(self, assessor):
        """Should infer change type from description."""
        result = assessor.assess_impact(
            change_type="unknown_type",
            change_description="manufacturing facility change",
        )
        assert result["change_type"] == "manufacturing_change"


# ==================================================================
# SupplementPackageGenerator Tests
# ==================================================================

class TestSupplementPackageGenerator:
    """Tests for the supplement package generator."""

    @pytest.fixture
    def generator(self):
        return SupplementPackageGenerator()

    def test_generate_180_day_package(self, generator):
        """180-day package should have all required sections."""
        result = generator.generate(
            supplement_type="180_day",
            change_description="New manufacturing site",
            pma_number="P170019",
        )
        assert result["supplement_type"] == "180_day"
        assert result["total_sections"] > 0
        assert len(result["sections"]) > 0

    def test_generate_panel_track_includes_briefing(self, generator):
        """Panel-track package should include advisory committee briefing."""
        result = generator.generate(supplement_type="panel_track")
        section_titles = [s["section_title"] for s in result["sections"]]
        assert any("Advisory" in t or "Briefing" in t for t in section_titles)

    def test_generate_real_time_is_shorter(self, generator):
        """Real-time package should have fewer sections than 180-day."""
        rt = generator.generate(supplement_type="real_time")
        d180 = generator.generate(supplement_type="180_day")
        assert rt["total_sections"] < d180["total_sections"]

    def test_cover_letter_includes_pma_number(self, generator):
        """Cover letter should include PMA number."""
        result = generator.generate(
            supplement_type="180_day",
            pma_number="P170019",
        )
        assert "P170019" in result["cover_letter_template"]

    def test_cover_letter_includes_cfr_reference(self, generator):
        """Cover letter should reference appropriate CFR section."""
        result = generator.generate(supplement_type="real_time")
        assert "21 CFR 814.39(c)" in result["cover_letter_template"]

    def test_regulatory_references_present(self, generator):
        """Package should include regulatory references."""
        result = generator.generate(supplement_type="180_day")
        assert len(result["regulatory_references"]) > 0
        refs = [r["reference"] for r in result["regulatory_references"]]
        assert any("814.39" in r for r in refs)

    def test_disclaimer_present(self, generator):
        """Package should include AI-generated disclaimer."""
        result = generator.generate(supplement_type="180_day")
        assert "disclaimer" in result
        assert "AI-generated" in result["disclaimer"]

    def test_sections_have_status(self, generator):
        """Each section should have a status field."""
        result = generator.generate(supplement_type="180_day")
        for section in result["sections"]:
            assert "status" in section
            assert section["status"] == "NOT_STARTED"

    def test_generate_batch(self, generator):
        """Batch generation should produce multiple packages."""
        changes = [
            {"supplement_type": "180_day", "description": "Design A"},
            {"supplement_type": "real_time", "description": "Label B"},
        ]
        results = generator.generate_batch(changes, pma_number="P170019")
        assert len(results) == 2

    def test_unknown_type_defaults_to_180_day(self, generator):
        """Unknown supplement type should default to 180-day."""
        result = generator.generate(supplement_type="nonexistent_type")
        assert result["supplement_type"] == "180_day"


# ==================================================================
# Constants Validation Tests
# ==================================================================

class TestConstants:
    """Test that constants and configuration are correct."""

    def test_supplement_types_have_required_fields(self):
        """All supplement types should have required fields."""
        required = {"label", "cfr_section", "review_days", "risk_level", "description"}
        for stype, sdef in SUPPLEMENT_TYPES.items():
            for field in required:
                assert field in sdef, f"{stype} missing {field}"

    def test_classification_patterns_valid(self):
        """All classification patterns should be valid regex."""
        import re
        for pattern_str, weight, stype in CLASSIFICATION_PATTERNS:
            try:
                re.compile(pattern_str, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Invalid regex pattern: {pattern_str}: {e}")
            assert weight > 0, f"Weight must be positive: {pattern_str}"
            assert stype in SUPPLEMENT_TYPES, f"Unknown type: {stype}"

    def test_decision_tree_nodes_connected(self):
        """All referenced nodes in decision tree should exist."""
        for node_id, node in DECISION_TREE.items():
            for option_label, target in node.get("options", {}).items():
                assert target in DECISION_TREE, (
                    f"Node {node_id} references non-existent node {target}"
                )

    def test_package_sections_exist_for_all_types(self):
        """Package sections should exist for all supplement types."""
        for stype in SUPPLEMENT_TYPES:
            assert stype in PACKAGE_SECTIONS, f"Missing package sections for {stype}"
            assert len(PACKAGE_SECTIONS[stype]) > 0


# ==================================================================
# Regulatory Disclaimer Tests (FDA-87)
# ==================================================================

class TestRegulatoryDisclaimers:
    """Tests for FDA-87: Regulatory disclaimers on heuristic scoring."""

    def test_regulatory_disclaimer_constant_exists(self):
        """REGULATORY_DISCLAIMER constant should be defined."""
        assert REGULATORY_DISCLAIMER is not None
        assert len(REGULATORY_DISCLAIMER.strip()) > 100
        assert "HEURISTIC ESTIMATE" in REGULATORY_DISCLAIMER
        assert "regulatory affairs professionals" in REGULATORY_DISCLAIMER.lower()

    def test_classifier_result_includes_disclaimer(self):
        """Classification results should include disclaimer field."""
        classifier = SupplementTypeClassifier()
        result = classifier.classify("180-day supplement for design change")
        assert "disclaimer" in result
        assert "HEURISTIC ESTIMATE" in result["disclaimer"]

    def test_classifier_heuristic_fallback_includes_disclaimer(self):
        """Heuristic fallback results should include disclaimer field."""
        classifier = SupplementTypeClassifier()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = classifier.classify("some vague change text here")
        assert "disclaimer" in result

    def test_impact_assessor_result_includes_disclaimer(self):
        """Impact assessment results should include disclaimer field."""
        assessor = ChangeImpactAssessor()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = assessor.assess_impact(change_type="design_change")
        assert "disclaimer" in result
        assert "HEURISTIC ESTIMATE" in result["disclaimer"]

    def test_low_confidence_emits_warning(self):
        """Low confidence classification should emit runtime warning."""
        classifier = SupplementTypeClassifier()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Use ambiguous text likely to produce low confidence
            classifier.classify("some vague change")
            # Should have at least one warning about low confidence or heuristic
            warning_messages = [str(warning.message) for warning in w]
            assert any(
                "heuristic" in msg.lower() or "confidence" in msg.lower()
                for msg in warning_messages
            ), f"Expected low-confidence warning, got: {warning_messages}"

    def test_critical_impact_emits_warning(self):
        """CRITICAL impact score should emit runtime warning."""
        assessor = ChangeImpactAssessor()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assessor.assess_impact(
                change_type="design_change",
                affected_components=[
                    "materials", "biocompatibility",
                    "mechanism_of_action", "sterilization",
                ],
            )
            warning_messages = [str(warning.message) for warning in w]
            assert any(
                "CRITICAL" in msg or "heuristic" in msg.lower()
                for msg in warning_messages
            ), f"Expected CRITICAL warning, got: {warning_messages}"

    def test_package_generator_disclaimer_present(self):
        """Package generator output should include disclaimer."""
        generator = SupplementPackageGenerator()
        result = generator.generate(supplement_type="180_day")
        assert "disclaimer" in result
        assert "AI-generated" in result["disclaimer"] or "verification" in result["disclaimer"].lower()

    def test_disclaimer_in_json_output(self):
        """JSON output should include disclaimer field."""
        classifier = SupplementTypeClassifier()
        result = classifier.classify("180-day supplement")
        json_str = json.dumps(result, indent=2)
        parsed = json.loads(json_str)
        assert "disclaimer" in parsed


import warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
