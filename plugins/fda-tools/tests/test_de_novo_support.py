"""
Tests for FDA-45: De Novo Classification Request Support
========================================================

Comprehensive test suite covering:
- De Novo submission outline generator
- Special controls proposal template
- Risk assessment framework
- Benefit-risk analysis tool
- De Novo vs 510(k) decision tree
- Predicate search documentation

Test count: 45+ tests across 7 test classes
"""

import os
import sys
from datetime import datetime

import pytest

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from de_novo_support import (  # type: ignore
    DeNovoSubmissionOutline,
    SpecialControlsProposal,
    DeNovoRiskAssessment,
    BenefitRiskAnalysis,
    PathwayDecisionTree,
    PredicateSearchDocumentation,
    generate_de_novo_outline,
    generate_special_controls,
    evaluate_pathway,
    perform_benefit_risk_analysis,
    DE_NOVO_SUBMISSION_SECTIONS,
    RISK_CATEGORIES,
    SPECIAL_CONTROLS_CATEGORIES,
    DECISION_FACTORS,
)


# ========================================================================
# FIXTURES
# ========================================================================

@pytest.fixture
def sample_device_info():
    return {
        "device_name": "SmartPulse AI Cardiac Monitor",
        "trade_name": "SmartPulse CM-200",
        "manufacturer": "NovelMed Technologies Inc.",
        "intended_use": "Continuous cardiac rhythm monitoring using AI-based analysis",
        "indications_for_use": "For use in adult patients for detection of cardiac arrhythmias",
        "technology_description": "Novel AI algorithm for real-time ECG interpretation",
        "proposed_class": "II",
        "proposed_product_code": "NEW",
        "proposed_regulation_number": "21 CFR 870.XXXX",
        "review_panel": "Cardiovascular",
        "has_software": True,
        "has_biocompat_concern": True,
        "is_electrical": True,
        "is_sterile": False,
    }


@pytest.fixture
def sample_risks():
    return [
        {"id": "R-001", "description": "False negative arrhythmia detection", "severity": "CRITICAL", "category": "clinical"},
        {"id": "R-002", "description": "False positive leading to unnecessary treatment", "severity": "MAJOR", "category": "indirect"},
        {"id": "R-003", "description": "Software malfunction during monitoring", "severity": "MAJOR", "category": "device_related"},
        {"id": "R-004", "description": "Skin irritation from electrode contact", "severity": "MINOR", "category": "device_related"},
        {"id": "R-005", "description": "User interpretation error of results", "severity": "MAJOR", "category": "use_related"},
    ]


@pytest.fixture
def sample_controls():
    return [
        {
            "id": "SC-001",
            "description": "Clinical validation study demonstrating sensitivity >= 95% for arrhythmia detection",
            "category": "premarket_testing",
            "linked_risks": ["R-001"],
        },
        {
            "id": "SC-002",
            "description": "Clinical validation study demonstrating specificity >= 90%",
            "category": "premarket_testing",
            "linked_risks": ["R-002"],
        },
        {
            "id": "SC-003",
            "description": "Software validation per IEC 62304 Level B",
            "category": "performance_standards",
            "linked_risks": ["R-003"],
        },
        {
            "id": "SC-004",
            "description": "Biocompatibility testing per ISO 10993-5 and ISO 10993-10",
            "category": "performance_standards",
            "linked_risks": ["R-004"],
        },
        {
            "id": "SC-005",
            "description": "Labeling must include interpretation guidance and training requirements",
            "category": "labeling_requirements",
            "linked_risks": ["R-005"],
        },
    ]


# ========================================================================
# TEST CLASS: DE NOVO SUBMISSION OUTLINE
# ========================================================================

class TestDeNovoSubmissionOutline:
    """Tests for De Novo submission outline generator."""

    def test_generate_returns_dict(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        assert isinstance(result, dict)

    def test_generate_has_required_keys(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        required_keys = [
            "title", "generated_at", "regulatory_basis", "device_info",
            "classification_recommendation", "sections", "gaps",
            "de_novo_specific_notes", "user_fee_info", "timeline_estimate",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_regulatory_basis_correct(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "860.260" in result["regulatory_basis"]["regulation"]
        assert "513(f)(2)" in result["regulatory_basis"]["statute"]

    def test_device_info_populated(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        assert result["device_info"]["device_name"] == "SmartPulse AI Cardiac Monitor"
        assert result["device_info"]["proposed_class"] == "II"

    def test_classification_recommendation_present(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        cr = result["classification_recommendation"]
        assert cr["proposed_class"] == "II"
        assert "Class I" in cr["class_i_considerations"]
        assert "Class II" in cr["class_ii_considerations"]

    def test_sections_include_required(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        required_titles = [
            "Administrative Information",
            "Device Description",
            "Intended Use / Indications for Use",
            "Classification Recommendation",
            "Predicate Search and Classification Assessment",
            "Risks and Mitigations",
            "Proposed Special Controls",
            "Benefit-Risk Assessment",
        ]
        section_titles = [s["title"] for s in result["sections"]]
        for title in required_titles:
            assert title in section_titles, f"Missing required section: {title}"

    def test_software_section_included_when_applicable(self, sample_device_info):
        sample_device_info["has_software"] = True
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        titles = [s["title"] for s in result["sections"]]
        assert "Software Documentation" in titles

    def test_software_section_excluded_when_not_applicable(self, sample_device_info):
        sample_device_info["has_software"] = False
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        titles = [s["title"] for s in result["sections"]]
        assert "Software Documentation" not in titles

    def test_electrical_section_included(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        titles = [s["title"] for s in result["sections"]]
        assert "Electrical Safety and EMC" in titles

    def test_gaps_identified_for_empty_device(self):
        outline = DeNovoSubmissionOutline({})
        result = outline.generate()
        assert len(result["gaps"]) > 0

    def test_user_fee_info_present(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        assert result["user_fee_info"]["de_novo_fee_fy2025"] == 130682

    def test_timeline_estimate_present(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "150 review days" in result["timeline_estimate"]["fda_review_goal"]

    def test_de_novo_notes_include_differences(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        notes = result["de_novo_specific_notes"]
        assert len(notes["key_differences_from_510k"]) > 0
        assert len(notes["common_de_novo_pitfalls"]) > 0
        assert len(notes["pre_submission_recommendations"]) > 0

    def test_to_markdown_produces_string(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        md = outline.to_markdown()
        assert isinstance(md, str)
        assert "De Novo Classification Request" in md

    def test_disclaimer_present(self, sample_device_info):
        outline = DeNovoSubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "RESEARCH USE ONLY" in result["disclaimer"]


# ========================================================================
# TEST CLASS: SPECIAL CONTROLS PROPOSAL
# ========================================================================

class TestSpecialControlsProposal:
    """Tests for special controls proposal template."""

    def test_generate_returns_dict(self, sample_risks, sample_controls):
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", sample_risks, sample_controls)
        assert isinstance(result, dict)

    def test_risk_control_matrix_populated(self, sample_risks, sample_controls):
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", sample_risks, sample_controls)
        assert len(result["risk_control_matrix"]) == 5

    def test_all_risks_addressed(self, sample_risks, sample_controls):
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", sample_risks, sample_controls)
        assert result["completeness_score"] == 100.0
        assert len(result["unmitigated_risks"]) == 0

    def test_unmitigated_risks_detected(self, sample_risks):
        partial_controls = [
            {"id": "SC-001", "description": "Control 1", "category": "premarket_testing", "linked_risks": ["R-001"]},
        ]
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", sample_risks, partial_controls)
        assert result["completeness_score"] < 100
        assert len(result["unmitigated_risks"]) > 0

    def test_controls_categories_present(self, sample_risks, sample_controls):
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", sample_risks, sample_controls)
        cat_ids = [c["id"] for c in result["controls_categories"]]
        assert "performance_standards" in cat_ids
        assert "labeling_requirements" in cat_ids

    def test_general_controls_reference(self, sample_risks, sample_controls):
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", sample_risks, sample_controls)
        gc = result["general_controls_reference"]
        assert len(gc) >= 8
        gc_controls = [g["control"] for g in gc]
        assert "Good Manufacturing Practices (QSR)" in gc_controls

    def test_empty_risks_and_controls(self):
        proposal = SpecialControlsProposal()
        result = proposal.generate("TestDevice", [], [])
        assert result["completeness_score"] == 0
        assert len(result["risk_control_matrix"]) == 0

    def test_to_markdown(self, sample_risks, sample_controls):
        proposal = SpecialControlsProposal()
        template = proposal.generate("TestDevice", sample_risks, sample_controls)
        md = proposal.to_markdown(template)
        assert isinstance(md, str)
        assert "Special Controls Proposal" in md
        assert "Risk-Control Traceability" in md


# ========================================================================
# TEST CLASS: RISK ASSESSMENT FRAMEWORK
# ========================================================================

class TestDeNovoRiskAssessment:
    """Tests for De Novo risk assessment framework."""

    def test_add_risk_returns_dict(self):
        assessment = DeNovoRiskAssessment()
        result = assessment.add_risk("R-001", "Test risk", "device_related")
        assert isinstance(result, dict)
        assert result["risk_id"] == "R-001"

    def test_rpn_calculation(self):
        assessment = DeNovoRiskAssessment()
        result = assessment.add_risk(
            "R-001", "Test risk", "device_related",
            severity=4, probability=3, detectability=2,
        )
        assert result["rpn"] == 24  # 4 * 3 * 2

    def test_risk_level_classification(self):
        assessment = DeNovoRiskAssessment()
        # LOW: RPN <= 10
        r1 = assessment.add_risk("R-001", "Low risk", "device_related", severity=1, probability=2, detectability=3)
        assert r1["risk_level"] == "LOW"
        # CRITICAL: RPN > 60
        r2 = assessment.add_risk("R-002", "Critical risk", "clinical", severity=5, probability=5, detectability=3)
        assert r2["risk_level"] == "CRITICAL"

    def test_severity_score_clamped(self):
        assessment = DeNovoRiskAssessment()
        result = assessment.add_risk("R-001", "Test", "device_related", severity=10)
        assert result["severity"]["score"] == 5

    def test_score_clamped_to_minimum(self):
        assessment = DeNovoRiskAssessment()
        result = assessment.add_risk("R-001", "Test", "device_related", severity=0, probability=-1)
        assert result["severity"]["score"] == 1
        assert result["probability"]["score"] == 1

    def test_residual_risk_calculation(self):
        assessment = DeNovoRiskAssessment()
        result = assessment.add_risk(
            "R-001", "Test", "device_related",
            severity=4, probability=4, detectability=2,
            residual_severity=2, residual_probability=2,
        )
        assert result["residual_risk"]["rpn"] == 8  # 2 * 2 * 2

    def test_acceptability_determination(self):
        assessment = DeNovoRiskAssessment()
        # Acceptable: effective RPN <= 30
        r1 = assessment.add_risk("R-001", "Low", "device_related", severity=2, probability=2, detectability=2)
        assert r1["acceptable"] is True
        # Unacceptable: RPN > 30
        r2 = assessment.add_risk("R-002", "High", "clinical", severity=5, probability=4, detectability=3)
        assert r2["acceptable"] is False

    def test_assessment_summary(self):
        assessment = DeNovoRiskAssessment()
        assessment.add_risk("R-001", "Low risk", "device_related", severity=2, probability=2, detectability=2)
        assessment.add_risk("R-002", "High risk", "clinical", severity=5, probability=4, detectability=3)
        summary = assessment.get_assessment_summary()
        assert summary["total_risks"] == 2
        assert summary["acceptable_risks"] == 1
        assert summary["unacceptable_risks"] == 1
        assert summary["acceptance_rate"] == 50.0

    def test_summary_by_category(self):
        assessment = DeNovoRiskAssessment()
        assessment.add_risk("R-001", "Risk A", "device_related", severity=3, probability=3, detectability=3)
        assessment.add_risk("R-002", "Risk B", "device_related", severity=4, probability=4, detectability=2)
        assessment.add_risk("R-003", "Risk C", "clinical", severity=2, probability=2, detectability=2)
        summary = assessment.get_assessment_summary()
        assert "device_related" in summary["by_category"]
        assert summary["by_category"]["device_related"]["count"] == 2

    def test_to_markdown(self):
        assessment = DeNovoRiskAssessment()
        assessment.add_risk("R-001", "Test risk", "device_related", severity=3, probability=3, detectability=3)
        md = assessment.to_markdown()
        assert isinstance(md, str)
        assert "Risk Matrix" in md
        assert "R-001" in md


# ========================================================================
# TEST CLASS: BENEFIT-RISK ANALYSIS
# ========================================================================

class TestBenefitRiskAnalysis:
    """Tests for benefit-risk analysis tool."""

    def test_add_benefit(self):
        bra = BenefitRiskAnalysis("Device", "Cardiac monitoring")
        result = bra.add_benefit("B-001", "Early arrhythmia detection", magnitude=4, probability=4)
        assert result["benefit_score"] == 16

    def test_add_risk(self):
        bra = BenefitRiskAnalysis("Device", "Cardiac monitoring")
        result = bra.add_risk("R-001", "False alarm", severity=2, probability=3)
        assert result["risk_score"] == 6

    def test_favorable_determination(self):
        bra = BenefitRiskAnalysis("Device", "Monitoring")
        bra.add_benefit("B-001", "Major benefit", magnitude=5, probability=5)
        bra.add_risk("R-001", "Minor risk", severity=2, probability=2)
        analysis = bra.analyze()
        assert analysis["summary"]["determination"] == "FAVORABLE"
        assert analysis["summary"]["benefit_risk_ratio"] > 1.0

    def test_unfavorable_determination(self):
        bra = BenefitRiskAnalysis("Device", "Monitoring")
        bra.add_benefit("B-001", "Small benefit", magnitude=1, probability=1)
        bra.add_risk("R-001", "Major risk", severity=5, probability=5)
        analysis = bra.analyze()
        assert analysis["summary"]["determination"] == "UNFAVORABLE"

    def test_residual_risk_used_when_available(self):
        bra = BenefitRiskAnalysis("Device", "Monitoring")
        bra.add_benefit("B-001", "Benefit", magnitude=4, probability=4)
        bra.add_risk("R-001", "Risk", severity=4, probability=4,
                      mitigation="Added safety check",
                      residual_severity=2, residual_probability=2)
        analysis = bra.analyze()
        assert analysis["summary"]["effective_risk_score"] == 4  # 2*2 residual
        assert analysis["summary"]["benefit_risk_ratio"] == 4.0  # 16/4

    def test_analysis_has_required_keys(self):
        bra = BenefitRiskAnalysis("Device", "Use")
        bra.add_benefit("B-001", "Benefit", magnitude=3, probability=3)
        bra.add_risk("R-001", "Risk", severity=2, probability=2)
        analysis = bra.analyze()
        assert "determination_statement" in analysis
        assert "summary" in analysis
        assert "disclaimer" in analysis

    def test_scores_clamped(self):
        bra = BenefitRiskAnalysis("Device", "Use")
        benefit = bra.add_benefit("B-001", "Test", magnitude=10, probability=-1)
        assert benefit["benefit_score"] == 5  # 5 * 1 (clamped)

    def test_confidence_levels(self):
        # HIGH confidence: ratio >= 2.0
        bra = BenefitRiskAnalysis("Device", "Use")
        bra.add_benefit("B-001", "Big benefit", magnitude=5, probability=5)
        bra.add_risk("R-001", "Small risk", severity=2, probability=1)
        analysis = bra.analyze()
        assert analysis["summary"]["confidence"] == "HIGH"


# ========================================================================
# TEST CLASS: PATHWAY DECISION TREE
# ========================================================================

class TestPathwayDecisionTree:
    """Tests for De Novo vs 510(k) decision tree."""

    def test_evaluate_returns_dict(self):
        tree = PathwayDecisionTree()
        result = tree.evaluate({"predicate_exists": True})
        assert isinstance(result, dict)

    def test_510k_recommended_with_predicate(self):
        tree = PathwayDecisionTree()
        answers = {
            "predicate_exists": True,
            "same_intended_use": True,
            "novel_technology": False,
            "different_questions_of_safety": False,
            "low_to_moderate_risk": True,
            "general_special_controls_sufficient": True,
        }
        result = tree.evaluate(answers)
        assert result["recommendation"] == "510(k)"
        assert result["scores"]["510k_score"] > result["scores"]["de_novo_score"]

    def test_de_novo_recommended_without_predicate(self):
        tree = PathwayDecisionTree()
        answers = {
            "predicate_exists": False,
            "same_intended_use": False,
            "novel_technology": True,
            "different_questions_of_safety": True,
            "low_to_moderate_risk": True,
            "general_special_controls_sufficient": True,
        }
        result = tree.evaluate(answers)
        assert result["recommendation"] == "De Novo"
        assert result["scores"]["de_novo_score"] > result["scores"]["510k_score"]

    def test_further_analysis_for_mixed(self):
        tree = PathwayDecisionTree()
        answers = {
            "predicate_exists": True,
            "same_intended_use": False,
            "novel_technology": True,
            "different_questions_of_safety": False,
            "low_to_moderate_risk": True,
            "general_special_controls_sufficient": True,
        }
        result = tree.evaluate(answers)
        # Mixed signals should not give high confidence
        assert result["confidence"] in ("LOW", "MODERATE")

    def test_missing_answers_handled(self):
        tree = PathwayDecisionTree()
        result = tree.evaluate({"predicate_exists": False})
        analysis = result["factor_analysis"]
        not_provided = [a for a in analysis if a.get("answer") == "NOT PROVIDED"]
        assert len(not_provided) > 0

    def test_next_steps_for_510k(self):
        tree = PathwayDecisionTree()
        answers = {"predicate_exists": True, "same_intended_use": True}
        result = tree.evaluate(answers)
        # Even with incomplete answers, next steps should be provided
        assert len(result["next_steps"]) > 0

    def test_next_steps_for_de_novo(self):
        tree = PathwayDecisionTree()
        answers = {
            "predicate_exists": False,
            "same_intended_use": False,
            "novel_technology": True,
            "different_questions_of_safety": True,
            "low_to_moderate_risk": True,
            "general_special_controls_sufficient": True,
        }
        result = tree.evaluate(answers)
        assert any("special controls" in s.lower() for s in result["next_steps"])

    def test_disclaimer_present(self):
        tree = PathwayDecisionTree()
        result = tree.evaluate({})
        assert "RESEARCH USE ONLY" in result["disclaimer"]


# ========================================================================
# TEST CLASS: PREDICATE SEARCH DOCUMENTATION
# ========================================================================

class TestPredicateSearchDocumentation:
    """Tests for predicate search documentation."""

    def test_add_search_strategy(self):
        doc = PredicateSearchDocumentation("TestDevice")
        result = doc.add_search_strategy(
            "FDA 510(k) Database",
            ["cardiac monitor", "ECG", "arrhythmia"],
            results_count=42,
        )
        assert result["database"] == "FDA 510(k) Database"
        assert result["results_count"] == 42

    def test_add_candidate_evaluation(self):
        doc = PredicateSearchDocumentation("TestDevice")
        result = doc.add_candidate_evaluation(
            "ExistingDevice A",
            k_number="K201234",
            product_code="DPS",
            se_possible=False,
            rejection_reason="Different technology (no AI component)",
        )
        assert result["se_possible"] is False
        assert "AI" in result["rejection_reason"]

    def test_supports_de_novo_when_no_predicates(self):
        doc = PredicateSearchDocumentation("TestDevice")
        doc.add_search_strategy("FDA 510(k) Database", ["test"], results_count=5)
        doc.add_candidate_evaluation("Device A", se_possible=False, rejection_reason="Different use")
        doc.add_candidate_evaluation("Device B", se_possible=False, rejection_reason="Different tech")
        result = doc.generate_documentation()
        assert result["supports_de_novo"] is True
        assert "No suitable predicate" in result["conclusion"]

    def test_does_not_support_de_novo_when_predicate_found(self):
        doc = PredicateSearchDocumentation("TestDevice")
        doc.add_candidate_evaluation("Device A", se_possible=True, rejection_reason="")
        result = doc.generate_documentation()
        assert result["supports_de_novo"] is False
        assert "510(k)" in result["conclusion"]

    def test_databases_tracked(self):
        doc = PredicateSearchDocumentation("TestDevice")
        doc.add_search_strategy("FDA 510(k) Database", ["test"])
        doc.add_search_strategy("FDA PMA Database", ["test"])
        doc.add_search_strategy("FDA De Novo Database", ["test"])
        result = doc.generate_documentation()
        assert len(result["databases_searched"]) == 3

    def test_recommended_databases_present(self):
        doc = PredicateSearchDocumentation("TestDevice")
        result = doc.generate_documentation()
        assert len(result["recommended_databases"]) >= 5

    def test_to_markdown(self):
        doc = PredicateSearchDocumentation("TestDevice")
        doc.add_search_strategy("FDA 510(k) Database", ["cardiac", "monitor"], results_count=10)
        doc.add_candidate_evaluation("Device A", k_number="K201234", se_possible=False, rejection_reason="Different tech")
        md = doc.to_markdown()
        assert isinstance(md, str)
        assert "Predicate Search Documentation" in md
        assert "K201234" in md


# ========================================================================
# TEST CLASS: CONVENIENCE FUNCTIONS AND CONSTANTS
# ========================================================================

class TestConvenienceFunctionsAndConstants:
    """Tests for convenience functions and module constants."""

    def test_generate_de_novo_outline(self):
        result = generate_de_novo_outline({"device_name": "TestDevice"})
        assert isinstance(result, dict)
        assert "sections" in result

    def test_generate_de_novo_outline_no_args(self):
        result = generate_de_novo_outline()
        assert isinstance(result, dict)
        assert len(result["gaps"]) > 0

    def test_generate_special_controls(self, sample_risks, sample_controls):
        result = generate_special_controls("TestDevice", sample_risks, sample_controls)
        assert isinstance(result, dict)
        assert result["completeness_score"] == 100.0

    def test_evaluate_pathway_function(self):
        result = evaluate_pathway({"predicate_exists": False, "novel_technology": True})
        assert isinstance(result, dict)
        assert "recommendation" in result

    def test_perform_benefit_risk_analysis(self):
        bra = perform_benefit_risk_analysis("Device", "Monitoring")
        assert isinstance(bra, BenefitRiskAnalysis)
        assert bra.device_name == "Device"

    def test_submission_sections_count(self):
        assert len(DE_NOVO_SUBMISSION_SECTIONS) >= 10

    def test_all_sections_have_required_fields(self):
        for section in DE_NOVO_SUBMISSION_SECTIONS:
            assert "number" in section
            assert "title" in section
            assert "description" in section
            assert "required" in section
            assert "cfr_reference" in section
            assert "acceptance_criteria" in section

    def test_risk_categories_count(self):
        assert len(RISK_CATEGORIES) >= 4

    def test_special_controls_categories_count(self):
        assert len(SPECIAL_CONTROLS_CATEGORIES) >= 6

    def test_decision_factors_weights_sum(self):
        total = sum(f["weight"] for f in DECISION_FACTORS.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_decision_factors_have_questions(self):
        for factor_id, factor in DECISION_FACTORS.items():
            assert "question" in factor
            assert "weight" in factor
            assert "510k_if" in factor
            assert "de_novo_if" in factor
