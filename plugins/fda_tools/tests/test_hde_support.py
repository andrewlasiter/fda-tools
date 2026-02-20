"""
Tests for FDA-44: Humanitarian Device Exemption (HDE) Support
=============================================================

Comprehensive test suite covering:
- HDE submission outline generator
- Rare disease prevalence validator (<8,000 patients/year)
- Probable benefit analysis template
- IRB approval tracker
- Annual distribution reports

Test count: 40+ tests across 6 test classes
"""

import os
import sys
from datetime import datetime, timezone, timedelta

import pytest

# Add lib to path

from hde_support import (  # type: ignore
    HDESubmissionOutline,
    PrevalenceValidator,
    ProbableBenefitAnalyzer,
    IRBApprovalTracker,
    AnnualDistributionReport,
    generate_hde_outline,
    validate_hde_prevalence,
    generate_probable_benefit_template,
    HDE_PREVALENCE_THRESHOLD,
    HDE_SUBMISSION_SECTIONS,
    IRB_STATUS_VALUES,
    PROBABLE_BENEFIT_CATEGORIES,
    ANNUAL_REPORT_FIELDS,
)


# ========================================================================
# FIXTURES
# ========================================================================

@pytest.fixture
def sample_device_info():
    return {
        "device_name": "OrphanStent Vascular Graft",
        "trade_name": "OrphanStent VG-100",
        "manufacturer": "RareMed Devices Inc.",
        "hud_designation_number": "HUD-2025-0042",
        "disease_condition": "Takayasu Arteritis with aortic aneurysm",
        "intended_use": "Treatment of aortic aneurysms in patients with Takayasu Arteritis",
        "device_class": "III",
        "product_code": "DRC",
        "has_software": False,
        "has_biocompat_concern": True,
    }


@pytest.fixture
def sample_evidence_items():
    return [
        {
            "category": "bench_testing",
            "description": "Burst pressure testing per ISO 7198",
            "published": False,
            "quantitative": True,
        },
        {
            "category": "bench_testing",
            "description": "Fatigue testing 400M cycles",
            "published": False,
            "quantitative": True,
        },
        {
            "category": "animal_studies",
            "description": "12-month porcine implant study (n=20)",
            "published": True,
            "quantitative": True,
        },
        {
            "category": "clinical_experience",
            "description": "Compassionate use in 5 patients",
            "published": False,
            "quantitative": False,
        },
        {
            "category": "literature",
            "description": "Systematic review of Takayasu surgical outcomes",
            "published": True,
            "quantitative": True,
        },
    ]


# ========================================================================
# TEST CLASS: HDE SUBMISSION OUTLINE
# ========================================================================

class TestHDESubmissionOutline:
    """Tests for HDE submission outline generator."""

    def test_generate_returns_dict(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        assert isinstance(result, dict)

    def test_generate_has_required_keys(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        required_keys = [
            "title", "generated_at", "regulatory_basis", "device_info",
            "sections", "gaps", "warnings", "hde_specific_requirements", "disclaimer",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_regulatory_basis_correct(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "814 Subpart H" in result["regulatory_basis"]["regulation"]
        assert "520(m)" in result["regulatory_basis"]["statute"]

    def test_device_info_populated(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        assert result["device_info"]["device_name"] == "OrphanStent Vascular Graft"
        assert result["device_info"]["hud_designation_number"] == "HUD-2025-0042"

    def test_sections_include_required(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        required_titles = [
            "Administrative Information",
            "Humanitarian Use Designation (HUD) Request",
            "Prevalence Documentation",
            "Probable Benefit",
            "IRB Information",
        ]
        section_titles = [s["title"] for s in result["sections"]]
        for title in required_titles:
            assert title in section_titles, f"Missing required section: {title}"

    def test_optional_software_section_excluded(self, sample_device_info):
        """Software section should be excluded when has_software=False."""
        sample_device_info["has_software"] = False
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        titles = [s["title"] for s in result["sections"]]
        assert "Software Documentation" not in titles

    def test_optional_software_section_included(self, sample_device_info):
        """Software section should be included when has_software=True."""
        sample_device_info["has_software"] = True
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        titles = [s["title"] for s in result["sections"]]
        assert "Software Documentation" in titles

    def test_gaps_identified_for_empty_device(self):
        outline = HDESubmissionOutline({})
        result = outline.generate()
        assert len(result["gaps"]) > 0
        gap_fields = [g["field"] for g in result["gaps"]]
        assert "device_name" in gap_fields

    def test_hde_requirements_include_profit_restriction(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "profit" in result["hde_specific_requirements"]["profit_restriction"].lower()

    def test_hde_requirements_include_irb_supervision(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "IRB" in result["hde_specific_requirements"]["irb_supervision"]

    def test_to_markdown_produces_string(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        md = outline.to_markdown()
        assert isinstance(md, str)
        assert "Humanitarian Device Exemption" in md

    def test_to_markdown_contains_sections(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        md = outline.to_markdown()
        assert "## Submission Sections" in md
        assert "### Section 1:" in md

    def test_disclaimer_present(self, sample_device_info):
        outline = HDESubmissionOutline(sample_device_info)
        result = outline.generate()
        assert "RESEARCH USE ONLY" in result["disclaimer"]


# ========================================================================
# TEST CLASS: PREVALENCE VALIDATOR
# ========================================================================

class TestPrevalenceValidator:
    """Tests for rare disease prevalence validator."""

    def test_eligible_below_threshold(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Takayasu Arteritis", 3000)
        assert result["eligible"] is True

    def test_ineligible_above_threshold(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Common Condition", 10000)
        assert result["eligible"] is False

    def test_threshold_is_8000(self):
        assert HDE_PREVALENCE_THRESHOLD == 8000

    def test_exactly_at_threshold_ineligible(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Borderline Condition", 8000)
        assert result["eligible"] is False

    def test_margin_calculation(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Rare Disease", 5000)
        assert result["margin"] == 3000
        assert result["margin_percentage"] == 37.5

    def test_warning_for_close_to_threshold(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Near Threshold Disease", 7500)
        warnings = [w for w in result["warnings"] if "close to threshold" in w.lower()]
        assert len(warnings) > 0

    def test_warning_for_no_sources(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Disease X", 2000)
        assert any("No data sources" in w for w in result["warnings"])

    def test_quality_score_with_good_data(self):
        validator = PrevalenceValidator()
        sources = [
            {"name": "NIH GARD Database", "url": "https://rarediseases.info.nih.gov", "date": "2025"},
            {"name": "CDC WONDER", "url": "https://wonder.cdc.gov", "date": "2025"},
            {"name": "Orphanet Registry", "url": "https://orphanet.org", "date": "2024"},
        ]
        result = validator.validate_prevalence(
            "Well-documented Rare Disease", 2000, sources, 2025
        )
        assert result["data_quality_score"] >= 50

    def test_quality_score_with_no_data(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Unknown Disease", 2000)
        assert result["data_quality_score"] < 30

    def test_old_data_warning(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Old Data Disease", 2000, [], 2010)
        assert any("years old" in w.lower() for w in result["warnings"])

    def test_source_recommendations(self):
        validator = PrevalenceValidator()
        recs = validator.get_source_recommendations("Takayasu Arteritis")
        assert len(recs) > 0
        assert any("NIH" in r["source"] for r in recs)

    def test_ineligible_recommends_alternative(self):
        validator = PrevalenceValidator()
        result = validator.validate_prevalence("Common Disease", 50000)
        assert any("alternative pathway" in r.lower() for r in result["recommendations"])


# ========================================================================
# TEST CLASS: PROBABLE BENEFIT ANALYZER
# ========================================================================

class TestProbableBenefitAnalyzer:
    """Tests for probable benefit analysis template generator."""

    def test_generate_template_returns_dict(self):
        analyzer = ProbableBenefitAnalyzer()
        result = analyzer.generate_template("TestDevice", "TestCondition")
        assert isinstance(result, dict)

    def test_template_has_required_keys(self):
        analyzer = ProbableBenefitAnalyzer()
        result = analyzer.generate_template("TestDevice", "TestCondition")
        assert "evidence_categories" in result
        assert "risk_benefit_determination" in result
        assert "overall_score" in result

    def test_evidence_categories_complete(self):
        analyzer = ProbableBenefitAnalyzer()
        result = analyzer.generate_template("TestDevice", "TestCondition")
        cat_ids = [c["id"] for c in result["evidence_categories"]]
        for expected in ["bench_testing", "animal_studies", "clinical_experience", "literature", "alternative_analysis"]:
            assert expected in cat_ids

    def test_no_evidence_produces_zero_score(self):
        analyzer = ProbableBenefitAnalyzer()
        result = analyzer.generate_template("TestDevice", "TestCondition")
        assert result["overall_score"] == 0

    def test_with_evidence_produces_nonzero_score(self, sample_evidence_items):
        analyzer = ProbableBenefitAnalyzer()
        result = analyzer.generate_template("TestDevice", "TestCondition", sample_evidence_items)
        assert result["overall_score"] > 0

    def test_gaps_identified_for_missing_categories(self):
        analyzer = ProbableBenefitAnalyzer()
        evidence = [{"category": "bench_testing", "description": "Test data"}]
        result = analyzer.generate_template("TestDevice", "TestCondition", evidence)
        gap_categories = [g["category"] for g in result["gaps"]]
        assert "Animal Studies" in gap_categories

    def test_risk_benefit_template_structure(self):
        analyzer = ProbableBenefitAnalyzer()
        result = analyzer.generate_template("TestDevice", "TestCondition")
        rb = result["risk_benefit_determination"]
        assert "probable_benefits" in rb
        assert "known_risks" in rb
        assert "alternative_treatments" in rb
        assert "determination" in rb

    def test_to_markdown_produces_string(self, sample_evidence_items):
        analyzer = ProbableBenefitAnalyzer()
        template = analyzer.generate_template("TestDevice", "TestCondition", sample_evidence_items)
        md = analyzer.to_markdown(template)
        assert isinstance(md, str)
        assert "Probable Benefit Analysis" in md

    def test_evidence_strength_none(self):
        analyzer = ProbableBenefitAnalyzer()
        assert analyzer._assess_evidence_strength([]) == "none"

    def test_evidence_strength_strong(self):
        analyzer = ProbableBenefitAnalyzer()
        items = [
            {"published": True, "quantitative": True},
            {"published": False, "quantitative": True},
            {"published": True, "quantitative": False},
        ]
        assert analyzer._assess_evidence_strength(items) == "strong"


# ========================================================================
# TEST CLASS: IRB APPROVAL TRACKER
# ========================================================================

class TestIRBApprovalTracker:
    """Tests for IRB approval tracking."""

    def test_add_facility(self):
        tracker = IRBApprovalTracker()
        result = tracker.add_facility("Johns Hopkins Hospital", status="approved")
        assert result["facility_name"] == "Johns Hopkins Hospital"
        assert result["status"] == "approved"
        assert result["is_active"] is True

    def test_invalid_status_raises_error(self):
        tracker = IRBApprovalTracker()
        with pytest.raises(ValueError, match="Invalid status"):
            tracker.add_facility("Test Hospital", status="invalid_status")

    def test_all_valid_statuses_accepted(self):
        tracker = IRBApprovalTracker()
        for status in IRB_STATUS_VALUES:
            result = tracker.add_facility(f"Hospital-{status}", status=status)
            assert result["status"] == status

    def test_expired_detection(self):
        tracker = IRBApprovalTracker()
        past_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        result = tracker.add_facility(
            "Expired Hospital",
            status="approved",
            expiration_date=past_date,
        )
        assert result["status"] == "expired"
        assert result["is_active"] is False
        assert result["needs_renewal"] is True

    def test_renewal_warning(self):
        tracker = IRBApprovalTracker()
        near_date = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        result = tracker.add_facility(
            "Expiring Hospital",
            status="approved",
            expiration_date=near_date,
        )
        assert result["needs_renewal"] is True

    def test_summary_counts(self):
        tracker = IRBApprovalTracker()
        tracker.add_facility("Hospital A", status="approved")
        tracker.add_facility("Hospital B", status="pending_submission")
        tracker.add_facility("Hospital C", status="denied")
        summary = tracker.get_summary()
        assert summary["total_facilities"] == 3
        assert summary["active_approvals"] == 1
        assert summary["pending_review"] == 1

    def test_compliance_rate(self):
        tracker = IRBApprovalTracker()
        tracker.add_facility("Hospital A", status="approved")
        tracker.add_facility("Hospital B", status="approved")
        tracker.add_facility("Hospital C", status="pending_submission")
        summary = tracker.get_summary()
        assert summary["compliance_rate"] == pytest.approx(66.7, abs=0.1)

    def test_alerts_for_expired(self):
        tracker = IRBApprovalTracker()
        past_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        tracker.add_facility("Expired Hospital", status="approved", expiration_date=past_date)
        summary = tracker.get_summary()
        assert len(summary["alerts"]) > 0
        assert summary["alerts"][0]["level"] == "CRITICAL"

    def test_duplicate_facility_update(self):
        tracker = IRBApprovalTracker()
        tracker.add_facility("Hospital A", status="pending_submission")
        tracker.add_facility("Hospital A", status="approved")
        assert len(tracker.facilities) == 1
        assert tracker.facilities[0]["status"] == "approved"

    def test_to_markdown(self):
        tracker = IRBApprovalTracker()
        tracker.add_facility("Hospital A", status="approved")
        md = tracker.to_markdown()
        assert isinstance(md, str)
        assert "IRB Approval Tracker" in md
        assert "Hospital A" in md


# ========================================================================
# TEST CLASS: ANNUAL DISTRIBUTION REPORT
# ========================================================================

class TestAnnualDistributionReport:
    """Tests for annual distribution report generation."""

    def test_basic_report_generation(self):
        report = AnnualDistributionReport("H250001", "OrphanStent VG-100", "RareMed Inc.")
        result = report.generate_report("2025-01-01", "2025-12-31")
        assert result["hde_number"] == "H250001"
        assert result["device_name"] == "OrphanStent VG-100"

    def test_report_has_distribution_summary(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        facilities = [
            {"name": "Johns Hopkins", "location": "Baltimore, MD"},
            {"name": "Mayo Clinic", "location": "Rochester, MN"},
        ]
        result = report.generate_report("2025-01-01", "2025-12-31", devices_distributed=15, facilities=facilities)
        assert result["distribution_summary"]["total_devices_distributed"] == 15
        assert result["distribution_summary"]["total_facilities"] == 2

    def test_safety_summary(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        events = [
            {"description": "Minor infection", "mdr_filed": True},
            {"description": "Device migration", "mdr_filed": False},
        ]
        result = report.generate_report("2025-01-01", "2025-12-31", adverse_events=events)
        assert result["safety_summary"]["total_adverse_events"] == 2
        assert result["safety_summary"]["mdr_reports_filed"] == 1

    def test_nonprofit_declaration(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        result = report.generate_report("2025-01-01", "2025-12-31", is_nonprofit=True)
        assert result["profit_status"]["is_nonprofit"] is True
        assert "cost-recovery" in result["profit_status"]["declaration"]

    def test_profit_declaration_pediatric(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        result = report.generate_report("2025-01-01", "2025-12-31", is_nonprofit=False)
        assert result["profit_status"]["is_nonprofit"] is False
        assert "pediatric" in result["profit_status"]["declaration"].lower()

    def test_prevalence_update_eligible(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        result = report.generate_report("2025-01-01", "2025-12-31", updated_prevalence=3000)
        assert result["prevalence_update"]["still_eligible"] is True

    def test_prevalence_update_ineligible(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        result = report.generate_report("2025-01-01", "2025-12-31", updated_prevalence=9000)
        assert result["prevalence_update"]["still_eligible"] is False

    def test_completeness_scoring(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        tracker = IRBApprovalTracker()
        tracker.add_facility("Hospital A", status="approved")
        result = report.generate_report(
            "2025-01-01", "2025-12-31",
            devices_distributed=10,
            facilities=[{"name": "Hospital A", "location": "City"}],
            updated_prevalence=3000,
            irb_tracker=tracker,
        )
        assert result["completeness_score"] == 100.0

    def test_missing_sections_identified(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        result = report.generate_report("2025-01-01", "2025-12-31")
        assert len(result["missing_sections"]) > 0

    def test_to_markdown(self):
        report = AnnualDistributionReport("H250001", "Device", "Company")
        report.generate_report("2025-01-01", "2025-12-31", devices_distributed=5)
        md = report.to_markdown()
        assert isinstance(md, str)
        assert "Annual Distribution Report" in md
        assert "H250001" in md


# ========================================================================
# TEST CLASS: CONVENIENCE FUNCTIONS
# ========================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_hde_outline(self):
        result = generate_hde_outline({"device_name": "TestDevice"})
        assert isinstance(result, dict)
        assert "sections" in result

    def test_validate_hde_prevalence(self):
        result = validate_hde_prevalence("Rare Disease", 3000)
        assert result["eligible"] is True

    def test_generate_probable_benefit_template(self):
        result = generate_probable_benefit_template("TestDevice", "TestCondition")
        assert isinstance(result, dict)
        assert "evidence_categories" in result

    def test_generate_hde_outline_no_args(self):
        result = generate_hde_outline()
        assert isinstance(result, dict)
        assert len(result["gaps"]) > 0


# ========================================================================
# TEST CLASS: CONSTANTS AND CONFIGURATION
# ========================================================================

class TestConstants:
    """Tests for module constants and configuration."""

    def test_prevalence_threshold_value(self):
        assert HDE_PREVALENCE_THRESHOLD == 8000

    def test_submission_sections_count(self):
        assert len(HDE_SUBMISSION_SECTIONS) >= 13

    def test_all_sections_have_required_fields(self):
        for section in HDE_SUBMISSION_SECTIONS:
            assert "number" in section
            assert "title" in section
            assert "description" in section
            assert "required" in section
            assert "cfr_reference" in section

    def test_irb_status_values_complete(self):
        expected = ["approved", "pending_submission", "denied", "expired", "suspended"]
        for status in expected:
            assert status in IRB_STATUS_VALUES

    def test_probable_benefit_categories_count(self):
        assert len(PROBABLE_BENEFIT_CATEGORIES) == 5

    def test_probable_benefit_weights_sum_to_one(self):
        total = sum(c["weight"] for c in PROBABLE_BENEFIT_CATEGORIES)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_annual_report_fields_present(self):
        assert "number_devices_distributed" in ANNUAL_REPORT_FIELDS
        assert "profit_status" in ANNUAL_REPORT_FIELDS
