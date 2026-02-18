"""
Tests for FDA-41: Real World Evidence (RWE) Integration
=======================================================

Comprehensive test suite covering:
- RWE data source connector
- Real-world data quality assessor
- RWE submission template generator (510(k) and PMA)

Test count: 40+ tests across 5 test classes
"""

import os
import sys
from datetime import datetime

import pytest

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from rwe_integration import (  # type: ignore
    RWEDataSourceConnector,
    RWDQualityAssessor,
    RWESubmissionTemplate,
    create_rwe_connector,
    assess_rwd_quality,
    generate_rwe_template,
    RWD_SOURCE_TYPES,
    RWD_QUALITY_DIMENSIONS,
    RWE_ANALYTICAL_METHODS,
)


# ========================================================================
# FIXTURES
# ========================================================================

@pytest.fixture
def connector():
    return RWEDataSourceConnector()


@pytest.fixture
def assessor():
    return RWDQualityAssessor()


@pytest.fixture
def populated_connector():
    conn = RWEDataSourceConnector()
    conn.add_source(
        source_type="ehr",
        source_name="Epic EHR - Hospital System A",
        patient_count=50000,
        data_period_start="2020-01-01",
        data_period_end="2025-12-31",
        udi_available=True,
        device_identifiable=True,
        irb_approved=True,
        dua_executed=True,
    )
    conn.add_source(
        source_type="registry",
        source_name="National Joint Registry",
        patient_count=200000,
        data_period_start="2015-01-01",
        data_period_end="2025-12-31",
        udi_available=True,
        device_identifiable=True,
        irb_approved=True,
        dua_executed=True,
    )
    conn.add_source(
        source_type="claims",
        source_name="CMS Medicare Claims",
        patient_count=1000000,
        data_period_start="2018-01-01",
        data_period_end="2024-12-31",
        udi_available=False,
        device_identifiable=False,
        irb_approved=False,
        dua_executed=False,
    )
    return conn


@pytest.fixture
def good_quality_scores():
    return {
        "relevance": {
            "population_representativeness": 4,
            "exposure_capture": 5,
            "outcome_measurement": 4,
            "follow_up_duration": 4,
        },
        "reliability": {
            "data_accrual_consistency": 4,
            "verification_procedures": 4,
            "audit_trail": 3,
            "data_standards_compliance": 4,
        },
        "completeness": {
            "variable_completeness": 4,
            "patient_follow_up_completeness": 3,
            "outcome_ascertainment": 4,
            "missing_data_patterns": 3,
        },
        "transparency": {
            "data_provenance_documented": 5,
            "processing_steps_documented": 4,
            "limitations_acknowledged": 4,
            "analysis_plan_prespecified": 5,
        },
        "regulatory_alignment": {
            "study_design_appropriate": 4,
            "endpoint_fda_acceptable": 4,
            "bias_control_adequate": 3,
            "statistical_methods_robust": 4,
        },
    }


# ========================================================================
# TEST CLASS: RWE DATA SOURCE CONNECTOR
# ========================================================================

class TestRWEDataSourceConnector:
    """Tests for RWE data source connector."""

    def test_add_source_returns_record(self, connector):
        result = connector.add_source(
            source_type="ehr",
            source_name="Test EHR",
        )
        assert isinstance(result, dict)
        assert result["source_type"] == "ehr"
        assert result["source_name"] == "Test EHR"

    def test_add_source_generates_id(self, connector):
        result = connector.add_source(source_type="ehr", source_name="Test")
        assert result["source_id"].startswith("RWD-")

    def test_invalid_source_type_raises(self, connector):
        with pytest.raises(ValueError, match="Invalid source type"):
            connector.add_source(source_type="invalid_type", source_name="Test")

    def test_all_source_types_valid(self, connector):
        for source_type in RWD_SOURCE_TYPES:
            result = connector.add_source(
                source_type=source_type,
                source_name=f"Test-{source_type}",
            )
            assert result["source_type"] == source_type
            assert result["fda_recognized"] is True

    def test_compliance_tracking(self, connector):
        result = connector.add_source(
            source_type="ehr",
            source_name="Non-compliant Source",
            irb_approved=False,
            dua_executed=False,
            hipaa_compliant=False,
        )
        assert result["compliance"]["irb_approved"] is False
        assert result["compliance"]["dua_executed"] is False
        assert len(result["readiness_flags"]) >= 2
        assert len(result["warnings"]) >= 1

    def test_udi_tracking(self, connector):
        result = connector.add_source(
            source_type="registry",
            source_name="UDI Registry",
            udi_available=True,
            device_identifiable=True,
        )
        assert result["device_tracking"]["udi_available"] is True
        assert result["device_tracking"]["device_identifiable"] is True

    def test_no_udi_warning(self, connector):
        result = connector.add_source(
            source_type="claims",
            source_name="Claims DB",
            udi_available=False,
            device_identifiable=False,
        )
        assert any("UDI" in f for f in result["readiness_flags"])
        assert any("identifiable" in w.lower() for w in result["warnings"])

    def test_sources_summary(self, populated_connector):
        summary = populated_connector.get_sources_summary()
        assert summary["total_sources"] == 3
        assert "ehr" in summary["source_types"]
        assert "registry" in summary["source_types"]
        assert summary["total_patients"] == 1250000
        assert summary["fda_recognized_count"] == 3
        assert summary["compliant_count"] == 2

    def test_recommend_sources_510k(self, connector):
        recs = connector.recommend_sources(submission_type="510k")
        assert len(recs) > 0
        rec_types = [r["source_type"] for r in recs]
        assert "registry" in rec_types

    def test_recommend_sources_pma(self, connector):
        recs = connector.recommend_sources(submission_type="pma")
        assert len(recs) > 0
        rec_types = [r["source_type"] for r in recs]
        assert "registry" in rec_types
        assert "ehr" in rec_types

    def test_recommend_sources_rare_disease(self, connector):
        recs = connector.recommend_sources(submission_type="hde", is_rare_disease=True)
        rec_types = [r["source_type"] for r in recs]
        assert "natural_history" in rec_types

    def test_recommend_sources_implant(self, connector):
        recs = connector.recommend_sources(
            submission_type="pma", device_type="implant"
        )
        rec_types = [r["source_type"] for r in recs]
        assert "sentinel" in rec_types

    def test_metadata_stored(self, connector):
        result = connector.add_source(
            source_type="ehr",
            source_name="Test",
            metadata={"custom_field": "custom_value"},
        )
        assert result["metadata"]["custom_field"] == "custom_value"


# ========================================================================
# TEST CLASS: RWD QUALITY ASSESSOR
# ========================================================================

class TestRWDQualityAssessor:
    """Tests for Real-World Data quality assessment."""

    def test_assess_source_returns_dict(self, assessor):
        result = assessor.assess_source("Test Source", "ehr")
        assert isinstance(result, dict)

    def test_assessment_has_required_keys(self, assessor):
        result = assessor.assess_source("Test Source", "ehr")
        required_keys = [
            "source_name", "overall_score", "grade",
            "dimensions", "fit_for_purpose", "recommendations",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_all_dimensions_present(self, assessor):
        result = assessor.assess_source("Test Source", "ehr")
        for dim_id in RWD_QUALITY_DIMENSIONS:
            assert dim_id in result["dimensions"]

    def test_zero_scores_grade_f(self, assessor):
        result = assessor.assess_source("Bad Source", "ehr")
        assert result["grade"] == "F"
        assert result["overall_score"] == 0

    def test_good_scores_high_grade(self, assessor, good_quality_scores):
        result = assessor.assess_source("Good Source", "registry", good_quality_scores)
        assert result["grade"] in ("A", "B")
        assert result["overall_score"] > 60

    def test_scores_clamped_to_range(self, assessor):
        scores = {
            "relevance": {
                "population_representativeness": 10,  # Should be clamped to 5
                "exposure_capture": -1,  # Should be clamped to 0
                "outcome_measurement": 3,
                "follow_up_duration": 3,
            }
        }
        result = assessor.assess_source("Test", "ehr", scores)
        rel = result["dimensions"]["relevance"]
        sub_scores = {s["criterion"]: s["score"] for s in rel["sub_criteria"]}
        assert sub_scores["population_representativeness"] == 5
        assert sub_scores["exposure_capture"] == 0

    def test_fit_for_purpose_510k(self, assessor, good_quality_scores):
        result = assessor.assess_source("Good Source", "registry", good_quality_scores)
        assert result["fit_for_purpose"]["510k_supplementary"] is True
        assert result["fit_for_purpose"]["post_market_surveillance"] is True

    def test_recommendations_for_low_dimensions(self, assessor):
        scores = {
            "relevance": {
                "population_representativeness": 1,
                "exposure_capture": 1,
                "outcome_measurement": 1,
                "follow_up_duration": 1,
            }
        }
        result = assessor.assess_source("Weak Source", "claims", scores)
        assert len(result["recommendations"]) > 0
        assert result["recommendations"][0]["priority"] == "HIGH"

    def test_compare_sources(self, assessor, good_quality_scores):
        assessor.assess_source("Source A", "ehr", good_quality_scores)
        assessor.assess_source("Source B", "claims")
        comparison = assessor.compare_sources()
        assert comparison["sources_compared"] == 2
        assert comparison["rankings"][0]["source_name"] == "Source A"

    def test_to_markdown(self, assessor, good_quality_scores):
        result = assessor.assess_source("Test Source", "registry", good_quality_scores)
        md = assessor.to_markdown(result)
        assert isinstance(md, str)
        assert "RWD Quality Assessment" in md
        assert "Test Source" in md

    def test_disclaimer_present(self, assessor):
        result = assessor.assess_source("Test", "ehr")
        assert "RESEARCH USE ONLY" in result["disclaimer"]


# ========================================================================
# TEST CLASS: RWE SUBMISSION TEMPLATE
# ========================================================================

class TestRWESubmissionTemplate:
    """Tests for RWE submission template generator."""

    def test_510k_template_creation(self):
        template_gen = RWESubmissionTemplate("510k")
        assert template_gen.submission_type == "510k"

    def test_pma_template_creation(self):
        template_gen = RWESubmissionTemplate("pma")
        assert template_gen.submission_type == "pma"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid submission type"):
            RWESubmissionTemplate("invalid")

    def test_510k_generate_returns_dict(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate("TestDevice", "Is device safe and effective?")
        assert isinstance(result, dict)

    def test_510k_has_required_sections(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate("TestDevice", "Is device safe?")
        section_titles = [s["title"] for s in result["sections"]]
        required = ["Executive Summary", "Study Design and Protocol", "Results", "Conclusions"]
        for title in required:
            assert title in section_titles, f"Missing section: {title}"

    def test_pma_has_more_sections(self):
        gen_510k = RWESubmissionTemplate("510k")
        gen_pma = RWESubmissionTemplate("pma")
        result_510k = gen_510k.generate("Device", "Question")
        result_pma = gen_pma.generate("Device", "Question")
        assert len(result_pma["sections"]) > len(result_510k["sections"])

    def test_pma_has_integration_section(self):
        gen = RWESubmissionTemplate("pma")
        result = gen.generate("Device", "Question")
        titles = [s["title"] for s in result["sections"]]
        assert "Integration with Clinical Trial Data" in titles

    def test_quality_checklist_present(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate("Device", "Question")
        assert len(result["quality_checklist"]) > 0

    def test_recommended_methods_present(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate("Device", "Question")
        assert len(result["recommended_methods"]) > 0
        method_names = [m["method"] for m in result["recommended_methods"]]
        assert "Propensity Score Matching" in method_names

    def test_gaps_identified(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate("Device", "Question")
        assert len(result["gaps"]) > 0

    def test_study_overview_populated(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate(
            "TestDevice",
            "Is TestDevice equivalent to predicate?",
            study_design="Retrospective cohort",
            endpoints=["Primary: complication rate", "Secondary: revision rate"],
            population="Adult patients receiving hip replacement",
            comparator="Predicate device XYZ",
            analytical_method="Propensity Score Matching",
        )
        assert result["study_overview"]["design"] == "Retrospective cohort"
        assert result["study_overview"]["comparator"] == "Predicate device XYZ"
        assert len(result["study_overview"]["primary_endpoints"]) > 0

    def test_to_markdown_510k(self):
        gen = RWESubmissionTemplate("510k")
        template = gen.generate("TestDevice", "Safety question")
        md = gen.to_markdown(template)
        assert isinstance(md, str)
        assert "RWE Submission Package" in md
        assert "510K" in md.upper()

    def test_to_markdown_pma(self):
        gen = RWESubmissionTemplate("pma")
        template = gen.generate("TestDevice", "Effectiveness question")
        md = gen.to_markdown(template)
        assert isinstance(md, str)
        assert "PMA" in md.upper()

    def test_disclaimer_present(self):
        gen = RWESubmissionTemplate("510k")
        result = gen.generate("Device", "Question")
        assert "RESEARCH USE ONLY" in result["disclaimer"]


# ========================================================================
# TEST CLASS: CONVENIENCE FUNCTIONS AND CONSTANTS
# ========================================================================

class TestConvenienceFunctionsAndConstants:
    """Tests for convenience functions and module constants."""

    def test_create_rwe_connector(self):
        conn = create_rwe_connector()
        assert isinstance(conn, RWEDataSourceConnector)

    def test_assess_rwd_quality(self):
        result = assess_rwd_quality("Test Source", "ehr")
        assert isinstance(result, dict)
        assert "overall_score" in result

    def test_generate_rwe_template_510k(self):
        result = generate_rwe_template("510k", "Device", "Question")
        assert result["submission_type"] == "510k"

    def test_generate_rwe_template_pma(self):
        result = generate_rwe_template("pma", "Device", "Question")
        assert result["submission_type"] == "pma"

    def test_rwd_source_types_count(self):
        assert len(RWD_SOURCE_TYPES) >= 7

    def test_all_source_types_fda_recognized(self):
        for source_type, source_def in RWD_SOURCE_TYPES.items():
            assert source_def["fda_recognized"] is True

    def test_quality_dimensions_count(self):
        assert len(RWD_QUALITY_DIMENSIONS) == 5

    def test_quality_dimensions_max_scores_sum(self):
        total = sum(d["max_score"] for d in RWD_QUALITY_DIMENSIONS.values())
        assert total == 100

    def test_analytical_methods_all_fda_accepted(self):
        for method in RWE_ANALYTICAL_METHODS:
            assert method["fda_accepted"] is True

    def test_analytical_methods_count(self):
        assert len(RWE_ANALYTICAL_METHODS) >= 6
