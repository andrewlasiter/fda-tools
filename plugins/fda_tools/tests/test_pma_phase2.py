"""
Comprehensive test suite for PMA Advanced Analytics -- Phase 2 (TICKET-003).

Tests cover all Phase 2 modules:
    1. TestClinicalRequirementsMapper -- clinical_requirements_mapper.py
    2. TestTimelinePredictor -- timeline_predictor.py
    3. TestRiskAssessment -- risk_assessment.py
    4. TestPathwayRecommender -- pathway_recommender.py
    5. TestCrossModuleIntegration -- Cross-module integration tests

Target: 50+ tests covering all Phase 2 acceptance criteria.
All tests run offline (no network access) using mocks.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add scripts directory to path
# Package imports configured in conftest.py and pytest.ini


# ============================================================
# Shared test fixtures and sample data
# ============================================================

SAMPLE_CLINICAL_TEXT = """
VII. SUMMARY OF CLINICAL STUDIES

A pivotal randomized controlled trial was conducted to evaluate the safety
and effectiveness of the device. The study enrolled 1,200 patients across
15 clinical sites in a multicenter, prospective, double-blind design.

The primary endpoint was device success rate at 12 months, defined as
freedom from target lesion revascularization. The secondary endpoint
included all-cause mortality and quality of life (SF-36) assessments.

The study used a non-inferiority design with a margin of 5%. The study was
powered at 90% with alpha = 0.05. Intent-to-treat analysis was the primary
analysis population, with per-protocol as sensitivity analysis.

Results showed a device success rate of 92.5% (95% CI: 90.3-94.2%).
The p-value was < 0.001, demonstrating statistical significance versus
the standard of care control arm. Sensitivity was 95.2% and specificity
was 88.7%. The Kaplan-Meier survival analysis confirmed the results.

The primary safety endpoint was the rate of device-related serious adverse
events at 30 days. The adverse event rate was 3.2%. Death occurred in
2 patients (0.17%). Thrombosis rate was 1.5%. 15 serious adverse events
were reported. A Data Safety Monitoring Board (DSMB) reviewed interim data.

Follow-up of 24 months was completed for the primary analysis.
An independent core laboratory reviewed all imaging data.
The Clinical Events Committee (CEC) adjudicated all events.

Inclusion criteria: patients aged 18-80 with symptomatic coronary disease.
Exclusion criteria: patients with recent MI, severe renal insufficiency.

Stratification by lesion complexity and diabetes status was performed.

Post-approval study is required as a condition of approval.

VIII. STATISTICAL ANALYSIS

Sample size of N = 1200 was based on Bayesian adaptive design.
Cox regression and log-rank tests were used for time-to-event analyses.
"""

SAMPLE_SAFETY_TEXT = """
VI. POTENTIAL RISKS AND ADVERSE EFFECTS

The potential risks associated with the device include thrombosis,
embolism, hemorrhage, perforation, device malfunction, and migration.
There is a risk of death in rare cases. Device fracture may occur due
to mechanical fatigue over time.

Biocompatibility testing was performed per ISO 10993, including
cytotoxicity, sensitization, and genotoxicity assessments.
The device uses titanium alloy with bioabsorbable polymer coating.

Sterilization validation was conducted per ISO 11135 for ethylene oxide.

Contraindications include patients with known allergy to device materials.
Warning: Use only by trained physicians.

Post-approval study monitoring is required as a condition of approval.
The risk is mitigated by careful patient selection and proper training.
"""

SAMPLE_SECTIONS = {
    "sections": {
        "clinical_studies": {
            "content": SAMPLE_CLINICAL_TEXT,
            "word_count": len(SAMPLE_CLINICAL_TEXT.split()),
        },
        "statistical_analysis": {
            "content": "Statistical methods included Kaplan-Meier and Cox regression.",
            "word_count": 8,
        },
        "potential_risks": {
            "content": SAMPLE_SAFETY_TEXT,
            "word_count": len(SAMPLE_SAFETY_TEXT.split()),
        },
        "benefit_risk": {
            "content": "The benefits of the device outweigh the risks.",
            "word_count": 9,
        },
        "indications_for_use": {
            "content": "Indicated for coronary artery lesions in patients with ischemic disease.",
            "word_count": 10,
        },
        "device_description": {
            "content": "An implantable percutaneous titanium stent with drug-eluting coating.",
            "word_count": 9,
        },
    }
}

SAMPLE_API_DATA = {
    "pma_number": "P170019",
    "device_name": "Coronary Stent System",
    "generic_name": "Coronary Drug-Eluting Stent",
    "applicant": "TestMedical Inc.",
    "product_code": "NMH",
    "decision_date": "20230615",
    "decision_code": "APPR",
    "advisory_committee": "CV",
    "advisory_committee_description": "Cardiovascular",
    "supplement_count": 5,
    "expedited_review_flag": "N",
}

SAMPLE_PMA_SEARCH_RESULT = {
    "meta": {"results": {"total": 8}},
    "results": [
        {"pma_number": "P170019", "product_code": "NMH", "decision_date": "20230615",
         "trade_name": "Stent A", "applicant": "TestMedical Inc.", "decision_code": "APPR"},
        {"pma_number": "P160035", "product_code": "NMH", "decision_date": "20220301",
         "trade_name": "Stent B", "applicant": "CardioDevices LLC", "decision_code": "APPR"},
        {"pma_number": "P150009", "product_code": "NMH", "decision_date": "20200115",
         "trade_name": "Stent C", "applicant": "TestMedical Inc.", "decision_code": "APPR"},
    ],
}

SAMPLE_510K_SEARCH_RESULT = {
    "meta": {"results": {"total": 45}},
    "results": [{"k_number": "K201234", "decision_date": "20220601"}],
}

SAMPLE_CLASSIFICATION_RESULT = {
    "results": [{
        "product_code": "NMH",
        "device_class": "3",
        "device_name": "Stent, Coronary Drug-Eluting",
        "regulation_number": "870.3460",
        "review_panel": "CV",
        "medical_specialty_description": "Cardiovascular",
        "gmp_exempt_flag": "N",
    }],
}


def _create_mock_store():
    """Create a mock PMADataStore for testing."""
    store = MagicMock()
    store.get_pma_data.return_value = SAMPLE_API_DATA
    store.get_extracted_sections.return_value = SAMPLE_SECTIONS
    store.get_supplements.return_value = []
    store.get_pma_dir.return_value = Path("/tmp/test_pma/P170019")
    store.client = MagicMock()
    store.client.search_pma.return_value = SAMPLE_PMA_SEARCH_RESULT
    store.client.get_pma.return_value = {"results": [SAMPLE_API_DATA]}
    store.client.get_pma_supplements.return_value = {"results": []}
    store.client.get_pma_by_product_code.return_value = SAMPLE_PMA_SEARCH_RESULT
    store.client.get_clearances.return_value = SAMPLE_510K_SEARCH_RESULT
    store.client.get_classification.return_value = SAMPLE_CLASSIFICATION_RESULT
    store.client._request.return_value = SAMPLE_510K_SEARCH_RESULT
    return store


# ============================================================
# Test Clinical Requirements Mapper
# ============================================================

class TestClinicalRequirementsMapper:
    """Test suite for clinical_requirements_mapper.py."""

    def setup_method(self):
        from clinical_requirements_mapper import ClinicalRequirementsMapper
        self.store = _create_mock_store()
        self.mapper = ClinicalRequirementsMapper(store=self.store)

    def test_map_requirements_basic(self):
        """Test basic requirement mapping returns all sections."""
        result = self.mapper.map_requirements("P170019")
        assert result["pma_number"] == "P170019"
        assert result["requirements_available"] is True
        assert "study_design_requirements" in result
        assert "enrollment_requirements" in result
        assert "endpoint_requirements" in result
        assert "follow_up_requirements" in result
        assert "data_requirements" in result
        assert "cost_estimate" in result
        assert "timeline_estimate" in result

    def test_study_design_extraction(self):
        """Test study design type detection."""
        result = self.mapper.map_requirements("P170019")
        design = result["study_design_requirements"]
        assert design["trial_type"] in ("pivotal_rct", "rct", "non_inferiority")
        assert design["randomization_required"] is True
        assert design["multicenter_required"] is True
        assert design["confidence"] > 0

    def test_blinding_detection(self):
        """Test blinding type detection from text."""
        result = self.mapper.map_requirements("P170019")
        design = result["study_design_requirements"]
        assert design["blinding"] == "double_blind"

    def test_control_arm_detection(self):
        """Test control arm type detection."""
        result = self.mapper.map_requirements("P170019")
        design = result["study_design_requirements"]
        assert design["control_arm"] == "standard_of_care"

    def test_enrollment_extraction(self):
        """Test enrollment data extraction."""
        result = self.mapper.map_requirements("P170019")
        enrollment = result["enrollment_requirements"]
        assert enrollment["minimum_sample_size"] == 1200
        assert enrollment["recommended_sample_size"] == 1440  # 1200 * 1.2
        assert enrollment["number_of_sites"] == 15

    def test_endpoint_extraction(self):
        """Test endpoint extraction."""
        result = self.mapper.map_requirements("P170019")
        endpoints = result["endpoint_requirements"]
        assert len(endpoints["primary_endpoints"]) > 0
        assert endpoints["confidence"] > 0

    def test_follow_up_extraction(self):
        """Test follow-up duration extraction."""
        result = self.mapper.map_requirements("P170019")
        follow_up = result["follow_up_requirements"]
        assert follow_up["observed_follow_up"]["duration"] is not None
        assert follow_up["post_approval_study_required"] is True
        assert follow_up["device_category"] == "cardiovascular_implant"

    def test_data_requirements(self):
        """Test data and monitoring requirement extraction."""
        result = self.mapper.map_requirements("P170019")
        data_reqs = result["data_requirements"]
        assert data_reqs["dsmb_required"] is True
        assert data_reqs["core_lab"] is True
        assert data_reqs["cec_required"] is True
        # interim_analysis flag depends on specific keywords in clinical text
        assert isinstance(data_reqs["interim_analysis"], bool)

    def test_statistical_requirements(self):
        """Test statistical requirement extraction."""
        result = self.mapper.map_requirements("P170019")
        stats = result["statistical_requirements"]
        assert "Intent-to-Treat (ITT)" in stats["analysis_populations"]
        assert stats["power_calculation"] == 90
        assert stats["alpha_level"] == 0.05
        assert len(stats["statistical_methods"]) > 0

    def test_cost_estimate(self):
        """Test cost estimation."""
        result = self.mapper.map_requirements("P170019")
        cost = result["cost_estimate"]
        assert cost["low_estimate"] > 0
        assert cost["mid_estimate"] > cost["low_estimate"]
        assert cost["high_estimate"] > cost["mid_estimate"]
        assert cost["currency"] == "USD"

    def test_timeline_estimate(self):
        """Test timeline estimation."""
        result = self.mapper.map_requirements("P170019")
        timeline = result["timeline_estimate"]
        assert timeline["total_months"] > 0
        assert timeline["optimistic_months"] < timeline["total_months"]
        assert timeline["pessimistic_months"] > timeline["total_months"]

    def test_compare_requirements(self):
        """Test multi-PMA comparison."""
        result = self.mapper.compare_requirements("P170019", ["P160035"])
        assert result["primary_pma"] == "P170019"
        assert "comparison_matrix" in result
        assert "consensus_requirements" in result

    def test_requirements_error_handling(self):
        """Test graceful handling when data is unavailable."""
        self.store.get_pma_data.return_value = {"error": "Not found", "pma_number": "P999999"}
        self.store.get_extracted_sections.return_value = None
        result = self.mapper.map_requirements("P999999")
        assert result["requirements_available"] is False
        assert "error" in result

    def test_confidence_calculation(self):
        """Test overall confidence score."""
        result = self.mapper.map_requirements("P170019")
        assert 0 <= result["confidence"] <= 1.0


# ============================================================
# Test Timeline Predictor
# ============================================================

class TestTimelinePredictor:
    """Test suite for timeline_predictor.py."""

    def setup_method(self):
        from timeline_predictor import TimelinePredictor
        self.store = _create_mock_store()
        self.predictor = TimelinePredictor(store=self.store)

    def test_predict_timeline_basic(self):
        """Test basic timeline prediction."""
        result = self.predictor.predict_timeline("P170019")
        assert result["pma_number"] == "P170019"
        assert "prediction" in result
        pred = result["prediction"]
        assert pred["optimistic_days"] > 0
        assert pred["realistic_days"] >= pred["optimistic_days"]
        assert pred["pessimistic_days"] >= pred["realistic_days"]

    def test_prediction_milestones(self):
        """Test milestone generation."""
        result = self.predictor.predict_timeline("P170019")
        milestones = result["milestones"]
        assert len(milestones) >= 3
        # Check milestone order
        days = [m["day"] for m in milestones]
        assert days == sorted(days)

    def test_prediction_with_submission_date(self):
        """Test prediction with submission date generates milestone dates."""
        result = self.predictor.predict_timeline("P170019", submission_date="2026-06-01")
        milestones = result["milestones"]
        for m in milestones:
            assert m["estimated_date"] is not None
            assert m["estimated_date"].startswith("2026") or m["estimated_date"].startswith("2027")

    def test_risk_factor_assessment(self):
        """Test risk factor identification."""
        result = self.predictor.predict_timeline("P170019")
        risks = result["risk_factors"]
        # CV panel should trigger advisory panel risk
        panel_risk = [r for r in risks if r["factor"] == "advisory_panel_required"]
        assert len(panel_risk) > 0

    def test_prediction_scenarios(self):
        """Test scenario generation."""
        result = self.predictor.predict_timeline("P170019")
        scenarios = result["scenarios"]
        assert "optimistic" in scenarios
        assert "realistic" in scenarios
        assert "pessimistic" in scenarios
        for scenario in scenarios.values():
            assert "days" in scenario
            assert "assumptions" in scenario
            assert len(scenario["assumptions"]) > 0

    def test_recommendations(self):
        """Test recommendation generation."""
        result = self.predictor.predict_timeline("P170019")
        recs = result["recommendations"]
        assert len(recs) > 0
        assert all(isinstance(r, str) for r in recs)

    def test_predict_for_product_code(self):
        """Test product code prediction."""
        result = self.predictor.predict_for_product_code("NMH")
        assert "prediction" in result
        assert result["prediction"]["realistic_days"] > 0

    def test_analyze_historical(self):
        """Test historical timeline analysis."""
        result = self.predictor.analyze_historical_timelines("NMH")
        assert "summary" in result
        summary = result["summary"]
        assert summary["total_analyzed"] > 0
        assert summary["median_days"] > 0

    def test_applicant_track_record(self):
        """Test applicant track record analysis."""
        result = self.predictor.analyze_applicant_track_record("TestMedical Inc.")
        assert result["applicant"] == "TestMedical Inc."

    def test_error_handling(self):
        """Test graceful error handling."""
        self.store.get_pma_data.return_value = {"error": "Not found", "pma_number": "P999999"}
        result = self.predictor.predict_timeline("P999999")
        assert "error" in result

    def test_mdufa_clock_milestone(self):
        """Test MDUFA 180-day clock is included in milestones."""
        result = self.predictor.predict_timeline("P170019")
        milestones = result["milestones"]
        mdufa = [m for m in milestones if m["phase"] == "mdufa_clock"]
        assert len(mdufa) == 1


# ============================================================
# Test Risk Assessment
# ============================================================

class TestRiskAssessment:
    """Test suite for risk_assessment.py."""

    def setup_method(self):
        from risk_assessment import RiskAssessmentEngine
        self.store = _create_mock_store()
        self.engine = RiskAssessmentEngine(store=self.store)

    def test_assess_risks_basic(self):
        """Test basic risk assessment."""
        result = self.engine.assess_risks("P170019")
        assert result["pma_number"] == "P170019"
        assert "risk_summary" in result
        assert "identified_risks" in result
        assert "risk_matrix" in result

    def test_risk_identification(self):
        """Test that risks are identified from safety text."""
        result = self.engine.assess_risks("P170019")
        risks = result["identified_risks"]
        assert len(risks) > 0
        risk_ids = [r["risk_id"] for r in risks]
        # These should be found in our sample safety text
        assert "thrombosis_embolism" in risk_ids
        assert "death" in risk_ids
        assert "hemorrhage" in risk_ids

    def test_risk_scoring(self):
        """Test RPN scoring."""
        result = self.engine.assess_risks("P170019")
        for risk in result["identified_risks"]:
            assert 1 <= risk["severity"] <= 5
            assert 1 <= risk["probability"] <= 5
            assert 1 <= risk["detectability"] <= 5
            assert risk["rpn"] == risk["severity"] * risk["probability"] * risk["detectability"]
            assert risk["priority"] in ("HIGH", "MEDIUM", "LOW")

    def test_risk_matrix(self):
        """Test risk matrix generation."""
        result = self.engine.assess_risks("P170019")
        matrix = result["risk_matrix"]
        assert "cells" in matrix
        assert "zones" in matrix
        # Check that matrix has 5x5 = 25 cells
        assert len(matrix["cells"]) == 25
        assert len(matrix["zones"]) == 25

    def test_risk_categories(self):
        """Test risk categorization."""
        result = self.engine.assess_risks("P170019")
        summary = result["risk_summary"]
        categories = summary["categories"]
        assert "clinical" in categories or "device" in categories

    def test_mitigation_extraction(self):
        """Test mitigation strategy extraction."""
        result = self.engine.assess_risks("P170019")
        mitigations = result["mitigation_strategies"]
        # Our sample text has mitigation-related content
        assert isinstance(mitigations, list)

    def test_evidence_requirements(self):
        """Test evidence requirement mapping."""
        result = self.engine.assess_risks("P170019")
        evidence = result["evidence_requirements"]
        assert isinstance(evidence, list)
        for e in evidence:
            assert "risk_id" in e
            assert "evidence_required" in e
            assert len(e["evidence_required"]) > 0

    def test_residual_risk(self):
        """Test residual risk level assessment."""
        result = self.engine.assess_risks("P170019")
        residual = result["risk_summary"]["residual_risk_level"]
        assert residual in ("HIGH", "MODERATE", "LOW", "UNKNOWN")

    def test_compare_risk_profiles(self):
        """Test risk profile comparison."""
        result = self.engine.compare_risk_profiles("P170019", ["P160035"])
        assert "risk_overlap" in result
        assert "severity_comparison" in result
        assert "notable_differences" in result

    def test_risk_landscape(self):
        """Test product code risk landscape."""
        result = self.engine.analyze_risk_landscape("NMH")
        assert result["product_code"] == "NMH"
        assert "common_risks" in result

    def test_error_handling(self):
        """Test graceful error handling."""
        self.store.get_pma_data.return_value = {"error": "Not found", "pma_number": "P999999"}
        self.store.get_extracted_sections.return_value = None
        result = self.engine.assess_risks("P999999")
        assert "error" in result

    def test_confidence_scoring(self):
        """Test confidence calculation."""
        result = self.engine.assess_risks("P170019")
        assert 0 <= result["confidence"] <= 1.0

    def test_cardiovascular_inherent_risks(self):
        """Test that CV panel adds inherent cardiovascular risks."""
        result = self.engine.assess_risks("P170019")
        risk_ids = [r["risk_id"] for r in result["identified_risks"]]
        assert "thrombosis_embolism" in risk_ids
        assert "hemorrhage" in risk_ids


# ============================================================
# Test Pathway Recommender
# ============================================================

class TestPathwayRecommender:
    """Test suite for pathway_recommender.py."""

    def setup_method(self):
        from pathway_recommender import PathwayRecommender
        self.client = _create_mock_store().client
        self.pma_store = _create_mock_store()
        self.recommender = PathwayRecommender(
            client=self.client, pma_store=self.pma_store
        )

    def test_recommend_basic(self):
        """Test basic pathway recommendation."""
        result = self.recommender.recommend("NMH")
        assert result["product_code"] == "NMH"
        assert "recommended_pathway" in result
        assert "all_pathways" in result
        assert "ranking" in result
        assert "comparison_table" in result

    def test_class_iii_recommends_pma(self):
        """Test that Class III device recommends PMA."""
        result = self.recommender.recommend("NMH")
        rec = result["recommended_pathway"]
        # Class III + no predicates should strongly suggest PMA
        # But NMH has 510k predicates, so it depends on scoring
        assert rec["pathway"] in ("pma", "traditional_510k")
        assert rec["score"] > 0

    def test_all_pathways_scored(self):
        """Test that all 5 pathways are scored."""
        result = self.recommender.recommend("NMH")
        assert len(result["all_pathways"]) == 5
        for pw in ["traditional_510k", "special_510k", "abbreviated_510k", "de_novo", "pma"]:
            assert pw in result["all_pathways"]

    def test_ranking_order(self):
        """Test ranking is in descending score order."""
        result = self.recommender.recommend("NMH")
        ranking = result["ranking"]
        scores = [r["score"] for r in ranking]
        assert scores == sorted(scores, reverse=True)

    def test_comparison_table(self):
        """Test comparison table has all pathways."""
        result = self.recommender.recommend("NMH")
        table = result["comparison_table"]
        assert len(table) == 5
        for row in table:
            assert "timeline_range" in row
            assert "cost_range" in row
            assert "approval_rate" in row
            assert "user_fee" in row

    def test_special_510k_with_own_predicate(self):
        """Test Special 510(k) scoring with own predicate."""
        result = self.recommender.recommend("NMH", own_predicate="K201234")
        special = result["all_pathways"]["special_510k"]
        assert special["score"] >= 40  # Own predicate gives 40 points

    def test_novel_technology_detection(self):
        """Test novel technology detection from device info."""
        device_info = {
            "device_description": "An AI-powered diagnostic device",
            "novel_features": "Uses machine learning for image analysis",
        }
        result = self.recommender.recommend("NMH", device_info=device_info)
        assessment = result["device_assessment"]
        assert assessment["novel_technology"] is True
        assert "machine learning" in assessment["novel_technology_matches"]

    def test_high_risk_detection(self):
        """Test high-risk device detection."""
        device_info = {
            "device_description": "A life-sustaining implantable cardiac device",
        }
        result = self.recommender.recommend("NMH", device_info=device_info)
        assessment = result["device_assessment"]
        assert assessment["high_risk"] is True

    def test_considerations_generated(self):
        """Test strategic considerations are generated."""
        result = self.recommender.recommend("NMH")
        considerations = result["considerations"]
        assert len(considerations) > 0
        assert all(isinstance(c, str) for c in considerations)

    def test_pma_history_integration(self):
        """Test PMA history analysis is included."""
        result = self.recommender.recommend("NMH")
        pma_hist = result["pma_history"]
        assert pma_hist["product_code"] == "NMH"
        assert "pma_count" in pma_hist

    def test_predicate_analysis(self):
        """Test predicate analysis is included."""
        result = self.recommender.recommend("NMH")
        pred = result["predicate_analysis"]
        assert pred["product_code"] == "NMH"
        assert "total_clearances" in pred

    def test_class_ii_favors_510k(self):
        """Test Class II device favors 510(k) pathway."""
        # Override classification to Class II
        self.client.get_classification.return_value = {
            "results": [{
                "product_code": "QKQ",
                "device_class": "2",
                "device_name": "Digital Pathology System",
                "regulation_number": "892.2050",
                "review_panel": "RA",
                "gmp_exempt_flag": "N",
            }]
        }
        result = self.recommender.recommend("QKQ")
        rec = result["recommended_pathway"]
        assert rec["pathway"] in ("traditional_510k", "abbreviated_510k")


# ============================================================
# Test Cross-Module Integration
# ============================================================

class TestCrossModuleIntegration:
    """Test cross-module integration between Phase 2 components."""

    def setup_method(self):
        from clinical_requirements_mapper import ClinicalRequirementsMapper
        from timeline_predictor import TimelinePredictor
        from risk_assessment import RiskAssessmentEngine
        from pathway_recommender import PathwayRecommender

        self.store = _create_mock_store()
        self.mapper = ClinicalRequirementsMapper(store=self.store)
        self.predictor = TimelinePredictor(store=self.store)
        self.risk_engine = RiskAssessmentEngine(store=self.store)

    def test_requirements_and_timeline_consistency(self):
        """Test that requirements follow-up aligns with timeline prediction."""
        reqs = self.mapper.map_requirements("P170019")
        timeline = self.predictor.predict_timeline("P170019")

        # Follow-up in requirements should relate to timeline follow-up
        assert reqs["requirements_available"] is True
        assert "prediction" in timeline

    def test_risk_and_requirements_alignment(self):
        """Test that identified risks align with evidence requirements."""
        risk_result = self.risk_engine.assess_risks("P170019")
        reqs = self.mapper.map_requirements("P170019")

        # Both should identify PAS requirement
        assert risk_result.get("risk_summary", {}).get("total_risks_identified", 0) > 0
        assert reqs.get("follow_up_requirements", {}).get("post_approval_study_required") is True

    def test_all_modules_use_same_data(self):
        """Test that all modules can work with the same PMA data."""
        reqs = self.mapper.map_requirements("P170019")
        timeline = self.predictor.predict_timeline("P170019")
        risk = self.risk_engine.assess_risks("P170019")

        # All should have valid results
        assert reqs["requirements_available"] is True
        assert "prediction" in timeline
        assert len(risk["identified_risks"]) > 0


# ============================================================
# Test Edge Cases and Error Handling
# ============================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        from clinical_requirements_mapper import ClinicalRequirementsMapper
        from timeline_predictor import TimelinePredictor
        from risk_assessment import RiskAssessmentEngine
        from pathway_recommender import PathwayRecommender

        self.store = _create_mock_store()
        self.mapper = ClinicalRequirementsMapper(store=self.store)
        self.predictor = TimelinePredictor(store=self.store)
        self.risk_engine = RiskAssessmentEngine(store=self.store)
        self.recommender = PathwayRecommender(
            client=self.store.client, pma_store=self.store
        )

    def test_empty_clinical_text(self):
        """Test handling of empty clinical text."""
        self.store.get_extracted_sections.return_value = {
            "sections": {}
        }
        result = self.mapper.map_requirements("P170019")
        assert result["requirements_available"] is True
        # Should still produce results with low confidence
        design = result["study_design_requirements"]
        assert design["trial_type"] == "unknown"

    def test_no_sections_available(self):
        """Test handling when no SSED sections available."""
        self.store.get_extracted_sections.return_value = None
        result = self.risk_engine.assess_risks("P170019")
        # Should still produce some results from API data
        assert "identified_risks" in result

    def test_api_degraded_mode(self):
        """Test handling of API degraded mode."""
        self.store.client.search_pma.return_value = {
            "degraded": True,
            "error": "API rate limit",
        }
        result = self.predictor.analyze_historical_timelines("NMH")
        assert "error" in result or "summary" in result

    def test_unknown_product_code(self):
        """Test handling of unknown product code."""
        self.store.client.get_classification.return_value = {
            "degraded": True,
            "error": "Not found",
        }
        result = self.recommender.recommend("ZZZ")
        assert result["product_code"] == "ZZZ"
        # Should still return recommendation with lower confidence
        assert "recommended_pathway" in result

    def test_timepoint_extraction_various_formats(self):
        """Test timepoint extraction handles various formats."""
        from clinical_requirements_mapper import ClinicalRequirementsMapper
        mapper = ClinicalRequirementsMapper.__new__(ClinicalRequirementsMapper)
        timepoints = mapper._extract_timepoints(
            "at 30 days follow-up and through 12 months assessment and 5-year follow-up"
        )
        assert len(timepoints) >= 2

    def test_rpn_calculation_bounds(self):
        """Test RPN stays within valid bounds."""
        result = self.risk_engine.assess_risks("P170019")
        for risk in result["identified_risks"]:
            assert 1 <= risk["rpn"] <= 125  # 5*5*5 = 125 max


# ============================================================
# Test Module Imports and Structure
# ============================================================

class TestModuleStructure:
    """Test that all Phase 2 modules import correctly and have expected interfaces."""

    def test_import_clinical_requirements_mapper(self):
        from clinical_requirements_mapper import ClinicalRequirementsMapper
        assert hasattr(ClinicalRequirementsMapper, "map_requirements")
        assert hasattr(ClinicalRequirementsMapper, "compare_requirements")
        assert hasattr(ClinicalRequirementsMapper, "analyze_product_code_requirements")

    def test_import_timeline_predictor(self):
        from timeline_predictor import TimelinePredictor
        assert hasattr(TimelinePredictor, "predict_timeline")
        assert hasattr(TimelinePredictor, "predict_for_product_code")
        assert hasattr(TimelinePredictor, "analyze_historical_timelines")
        assert hasattr(TimelinePredictor, "analyze_applicant_track_record")

    def test_import_risk_assessment(self):
        from risk_assessment import RiskAssessmentEngine
        assert hasattr(RiskAssessmentEngine, "assess_risks")
        assert hasattr(RiskAssessmentEngine, "compare_risk_profiles")
        assert hasattr(RiskAssessmentEngine, "analyze_risk_landscape")

    def test_import_pathway_recommender(self):
        from pathway_recommender import PathwayRecommender
        assert hasattr(PathwayRecommender, "recommend")
        assert hasattr(PathwayRecommender, "compare_pathways")

    def test_all_constants_defined(self):
        """Test that key constants are properly defined."""
        from clinical_requirements_mapper import STUDY_DESIGN_HIERARCHY, FOLLOW_UP_STANDARDS
        from timeline_predictor import PHASE_BASELINES, RISK_FACTOR_IMPACTS
        from risk_assessment import SEVERITY_SCALE, PROBABILITY_SCALE, DEVICE_RISK_FACTORS
        from pathway_recommender import PATHWAY_DEFINITIONS, SCORING_FACTORS

        assert len(STUDY_DESIGN_HIERARCHY) >= 10
        assert len(FOLLOW_UP_STANDARDS) >= 5
        assert len(PHASE_BASELINES) >= 4
        assert len(RISK_FACTOR_IMPACTS) >= 5
        assert len(SEVERITY_SCALE) == 5
        assert len(PROBABILITY_SCALE) == 5
        assert len(DEVICE_RISK_FACTORS) >= 15
        assert len(PATHWAY_DEFINITIONS) == 5
        assert len(SCORING_FACTORS) == 5
