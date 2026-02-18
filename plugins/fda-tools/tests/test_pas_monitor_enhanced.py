"""
Comprehensive test suite for Post-Approval Study Monitoring Enhancement -- FDA-64.

Tests cover all enhanced deliverables:
    1. Enhanced post-approval study tracker
    2. Milestone monitoring dashboard
    3. Progress report generator
    4. Enrollment tracking
    5. Protocol deviation logger
    6. Study completion criteria validator
    7. Final report outline generator

Target: 40+ tests covering all FDA-64 acceptance criteria.
All tests run offline (no network access) using mocks.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

from pas_monitor import (  # type: ignore
    PAS_TYPES,
    PAS_STATUS,
    PAS_MILESTONES,
    PASMonitor,
)


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
    "ao_statement": "Condition of approval: post-approval study required.",
}

SAMPLE_SUPPLEMENTS = [
    {
        "pma_number": "P170019S001",
        "supplement_number": "S001",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "New indication for BRCA1/2 companion diagnostic labeling",
        "decision_date": "20180615",
        "decision_code": "APPR",
    },
    {
        "pma_number": "P170019S004",
        "supplement_number": "S004",
        "supplement_type": "PAS Update",
        "supplement_reason": "Post-approval study enrollment interim report",
        "decision_date": "20200301",
        "decision_code": "APPR",
    },
]

SAMPLE_SITES = [
    {
        "site_id": "SITE-001",
        "site_name": "Johns Hopkins Hospital",
        "pi": "Dr. Smith",
        "irb_date": "2023-01-15",
        "activation_date": "2023-03-01",
        "enrolled": 45,
        "screened": 60,
        "screen_failures": 15,
        "status": "ACTIVE",
    },
    {
        "site_id": "SITE-002",
        "site_name": "Mayo Clinic",
        "pi": "Dr. Jones",
        "irb_date": "2023-02-01",
        "activation_date": "2023-04-15",
        "enrolled": 30,
        "screened": 42,
        "screen_failures": 12,
        "status": "ACTIVE",
    },
    {
        "site_id": "SITE-003",
        "site_name": "Cleveland Clinic",
        "pi": "Dr. Lee",
        "irb_date": "2023-03-01",
        "activation_date": "",
        "enrolled": 0,
        "screened": 0,
        "screen_failures": 0,
        "status": "NOT_ACTIVATED",
    },
]


@pytest.fixture
def mock_store():
    """Create a mock PMADataStore."""
    store = MagicMock()
    store.get_pma_data.return_value = SAMPLE_PMA_DATA
    store.get_supplements.return_value = SAMPLE_SUPPLEMENTS
    store.get_extracted_sections.return_value = None
    store.get_pma_dir.return_value = MagicMock()
    return store


@pytest.fixture
def monitor(mock_store):
    """Create PASMonitor with mocked store."""
    return PASMonitor(store=mock_store)


# ============================================================
# Test: Enrollment tracking
# ============================================================

class TestEnrollmentTracker:
    """Test enrollment tracking functionality."""

    def test_generate_enrollment_tracker_basic(self, monitor):
        """Should generate basic enrollment tracker."""
        tracker = monitor.generate_enrollment_tracker("P170019")
        assert tracker["document_type"] == "PAS Enrollment Tracker"
        assert tracker["pma_number"] == "P170019"

    def test_enrollment_tracker_with_target(self, monitor):
        """Should accept enrollment target."""
        tracker = monitor.generate_enrollment_tracker(
            "P170019",
            study_name="Post-Approval Safety Study",
            target_enrollment=500,
        )
        assert tracker["enrollment_summary"]["target_enrollment"] == 500
        assert tracker["study_name"] == "Post-Approval Safety Study"

    def test_enrollment_tracker_with_sites(self, monitor):
        """Should pre-populate from site data."""
        tracker = monitor.generate_enrollment_tracker(
            "P170019",
            target_enrollment=200,
            sites=SAMPLE_SITES,
        )
        assert tracker["total_sites"] == 3
        assert tracker["active_sites"] == 2
        assert tracker["enrollment_summary"]["total_enrolled"] == 75  # 45 + 30
        assert tracker["enrollment_summary"]["enrollment_pct"] == 37.5  # 75/200

    def test_enrollment_tracker_milestones(self, monitor):
        """Should calculate enrollment milestones."""
        tracker = monitor.generate_enrollment_tracker(
            "P170019",
            target_enrollment=100,
            sites=SAMPLE_SITES,
        )
        milestones = tracker["enrollment_milestones"]
        assert len(milestones) == 4  # 25%, 50%, 75%, 100%
        # 75 enrolled out of 100 target
        assert milestones[0]["achieved"] is True   # 25% = 25 (achieved)
        assert milestones[1]["achieved"] is True   # 50% = 50 (achieved)
        assert milestones[2]["achieved"] is True   # 75% = 75 (achieved)
        assert milestones[3]["achieved"] is False  # 100% = 100 (not achieved)

    def test_enrollment_tracker_zero_target(self, monitor):
        """Should handle zero enrollment target gracefully."""
        tracker = monitor.generate_enrollment_tracker(
            "P170019", target_enrollment=0
        )
        assert tracker["enrollment_summary"]["enrollment_pct"] == 0.0

    def test_enrollment_tracker_site_details(self, monitor):
        """Should include detailed site information."""
        tracker = monitor.generate_enrollment_tracker(
            "P170019",
            target_enrollment=200,
            sites=SAMPLE_SITES,
        )
        sites = tracker["sites"]
        assert len(sites) == 3
        assert sites[0]["site_name"] == "Johns Hopkins Hospital"
        assert sites[0]["principal_investigator"] == "Dr. Smith"
        assert sites[0]["enrolled"] == 45

    def test_enrollment_tracker_screen_failure_tracking(self, monitor):
        """Should track screen failures."""
        tracker = monitor.generate_enrollment_tracker(
            "P170019",
            target_enrollment=200,
            sites=SAMPLE_SITES,
        )
        assert tracker["enrollment_summary"]["total_screened"] == 102  # 60+42+0
        assert tracker["enrollment_summary"]["total_screen_failures"] == 27  # 15+12+0


# ============================================================
# Test: Protocol deviation logger
# ============================================================

class TestProtocolDeviationLog:
    """Test protocol deviation logging functionality."""

    def test_create_deviation_log_basic(self, monitor):
        """Should create protocol deviation log template."""
        log = monitor.create_protocol_deviation_log(
            "P170019", study_name="Safety Study"
        )
        assert log["document_type"] == "Protocol Deviation Log"
        assert log["pma_number"] == "P170019"
        assert log["study_name"] == "Safety Study"

    def test_deviation_log_has_template(self, monitor):
        """Should include a deviation template for consistency."""
        log = monitor.create_protocol_deviation_log("P170019")
        template = log["deviation_template"]
        assert "deviation_id" in template
        assert "deviation_type" in template
        assert "category" in template
        assert "impact_on_subject_safety" in template
        assert "corrective_action" in template

    def test_log_protocol_deviation(self, monitor):
        """Should add a deviation to the log."""
        log = monitor.create_protocol_deviation_log("P170019")
        deviation = {
            "date_occurred": "2026-01-15",
            "site_id": "SITE-001",
            "subject_id": "SUBJ-042",
            "deviation_type": "Major",
            "category": "Consent",
            "description": "Informed consent obtained after procedure",
            "impact_on_subject_safety": "Minimal",
            "resolution_status": "Open",
        }
        updated = monitor.log_protocol_deviation(log, deviation)
        assert len(updated["deviations"]) == 1
        assert updated["deviations"][0]["deviation_id"] == "PD-0001"

    def test_log_multiple_deviations(self, monitor):
        """Should handle multiple deviations with auto-incrementing IDs."""
        log = monitor.create_protocol_deviation_log("P170019")
        for i in range(3):
            deviation = {
                "deviation_type": "Minor" if i < 2 else "Major",
                "category": "Data",
                "resolution_status": "Resolved" if i == 0 else "Open",
                "site_id": f"SITE-{i+1:03d}",
            }
            log = monitor.log_protocol_deviation(log, deviation)

        assert len(log["deviations"]) == 3
        assert log["deviations"][0]["deviation_id"] == "PD-0001"
        assert log["deviations"][2]["deviation_id"] == "PD-0003"

    def test_deviation_summary_statistics(self, monitor):
        """Should compute summary statistics after logging."""
        log = monitor.create_protocol_deviation_log("P170019")
        deviations = [
            {"deviation_type": "Major", "category": "Consent", "resolution_status": "Resolved", "site_id": "SITE-001"},
            {"deviation_type": "Minor", "category": "Data", "resolution_status": "Open", "site_id": "SITE-001"},
            {"deviation_type": "Major", "category": "Safety", "resolution_status": "Open", "site_id": "SITE-002"},
            {"deviation_type": "Important", "category": "Data", "resolution_status": "Resolved", "site_id": "SITE-002"},
        ]
        for d in deviations:
            log = monitor.log_protocol_deviation(log, d)

        stats = log["summary_statistics"]
        assert stats["total_deviations"] == 4
        assert stats["major_deviations"] == 2
        assert stats["minor_deviations"] == 1
        assert stats["important_deviations"] == 1
        assert stats["open_deviations"] == 2
        assert stats["resolved_deviations"] == 2
        assert stats["by_category"]["Data"] == 2
        assert stats["by_site"]["SITE-001"] == 2
        assert stats["by_site"]["SITE-002"] == 2


# ============================================================
# Test: Study completion criteria validator
# ============================================================

class TestStudyCompletionValidator:
    """Test study completion criteria validation."""

    def test_validate_complete_study(self, monitor):
        """Should pass all criteria for a complete study."""
        study_data = {
            "study_name": "Post-Approval Safety Study",
            "enrollment_target": 500,
            "enrolled": 520,
            "min_followup_months": 24,
            "followup_completed_months": 30,
            "followup_rate_pct": 92,
            "min_followup_rate_pct": 80,
            "primary_endpoints_analyzed": True,
            "safety_analysis_complete": True,
            "unresolved_major_deviations": 0,
        }
        result = monitor.validate_study_completion("P170019", study_data)
        assert result["all_criteria_met"] is True
        assert result["criteria_met"] == 6
        assert result["criteria_not_met"] == 0
        assert "Proceed with final report" in result["recommendation"]

    def test_validate_incomplete_study(self, monitor):
        """Should fail criteria for an incomplete study."""
        study_data = {
            "study_name": "Incomplete Study",
            "enrollment_target": 500,
            "enrolled": 300,
            "min_followup_months": 24,
            "followup_completed_months": 12,
            "followup_rate_pct": 75,
            "min_followup_rate_pct": 80,
            "primary_endpoints_analyzed": False,
            "safety_analysis_complete": False,
            "unresolved_major_deviations": 2,
        }
        result = monitor.validate_study_completion("P170019", study_data)
        assert result["all_criteria_met"] is False
        assert result["criteria_not_met"] > 0
        assert "does NOT meet" in result["recommendation"]

    def test_validate_enrollment_criterion(self, monitor):
        """Should correctly assess enrollment target criterion."""
        study_data = {
            "enrollment_target": 100,
            "enrolled": 99,
            "min_followup_months": 0,
            "followup_completed_months": 0,
            "followup_rate_pct": 100,
            "min_followup_rate_pct": 80,
            "primary_endpoints_analyzed": True,
            "safety_analysis_complete": True,
            "unresolved_major_deviations": 0,
        }
        result = monitor.validate_study_completion("P170019", study_data)
        enrollment_criterion = next(
            c for c in result["criteria"] if c["criterion"] == "enrollment_target"
        )
        assert enrollment_criterion["met"] is False
        assert "99/100" in enrollment_criterion["details"]

    def test_validate_followup_rate_criterion(self, monitor):
        """Should correctly assess follow-up rate criterion."""
        study_data = {
            "enrollment_target": 100,
            "enrolled": 100,
            "min_followup_months": 12,
            "followup_completed_months": 12,
            "followup_rate_pct": 79,
            "min_followup_rate_pct": 80,
            "primary_endpoints_analyzed": True,
            "safety_analysis_complete": True,
            "unresolved_major_deviations": 0,
        }
        result = monitor.validate_study_completion("P170019", study_data)
        followup_criterion = next(
            c for c in result["criteria"] if c["criterion"] == "followup_rate"
        )
        assert followup_criterion["met"] is False

    def test_validate_has_six_criteria(self, monitor):
        """Should have exactly 6 completion criteria."""
        study_data = {
            "enrollment_target": 100,
            "enrolled": 100,
            "min_followup_months": 12,
            "followup_completed_months": 12,
            "followup_rate_pct": 90,
            "min_followup_rate_pct": 80,
            "primary_endpoints_analyzed": True,
            "safety_analysis_complete": True,
            "unresolved_major_deviations": 0,
        }
        result = monitor.validate_study_completion("P170019", study_data)
        assert result["total_criteria"] == 6


# ============================================================
# Test: Progress report generator
# ============================================================

class TestProgressReport:
    """Test progress report generation."""

    def test_generate_progress_report_basic(self, monitor):
        """Should generate progress report template."""
        report = monitor.generate_progress_report("P170019")
        assert report["document_type"] == "PAS Progress Report"
        assert report["pma_number"] == "P170019"

    def test_progress_report_with_enrollment(self, monitor):
        """Should pre-populate from enrollment data."""
        enrollment = {
            "enrollment_summary": {
                "target_enrollment": 500,
                "total_enrolled": 250,
                "enrollment_pct": 50.0,
            },
            "active_sites": 12,
        }
        report = monitor.generate_progress_report(
            "P170019",
            enrollment_data=enrollment,
        )
        assert report["enrollment_status"]["target"] == 500
        assert report["enrollment_status"]["enrolled"] == 250
        assert report["enrollment_status"]["active_sites"] == 12

    def test_progress_report_with_deviations(self, monitor):
        """Should pre-populate from deviation log."""
        deviation_log = {
            "summary_statistics": {
                "total_deviations": 15,
                "major_deviations": 3,
                "open_deviations": 5,
            },
        }
        report = monitor.generate_progress_report(
            "P170019",
            deviation_log=deviation_log,
        )
        assert report["protocol_deviations"]["total"] == 15
        assert report["protocol_deviations"]["major"] == 3
        assert report["protocol_deviations"]["open"] == 5

    def test_progress_report_has_safety_section(self, monitor):
        """Should include safety summary section."""
        report = monitor.generate_progress_report("P170019")
        safety = report["safety_summary"]
        assert "total_adverse_events" in safety
        assert "serious_adverse_events" in safety
        assert "device_related_events" in safety
        assert "safety_signal_detected" in safety

    def test_progress_report_has_timeline_assessment(self, monitor):
        """Should include timeline assessment."""
        report = monitor.generate_progress_report("P170019")
        timeline = report["timeline_assessment"]
        assert "on_track" in timeline
        assert "enrollment_projection" in timeline
        assert "timeline_risks" in timeline

    def test_progress_report_has_data_quality(self, monitor):
        """Should include data quality metrics."""
        report = monitor.generate_progress_report("P170019")
        quality = report["data_quality"]
        assert "queries_generated" in quality
        assert "queries_resolved" in quality
        assert "missing_data_rate_pct" in quality


# ============================================================
# Test: Final report outline generator
# ============================================================

class TestFinalReportOutline:
    """Test final report outline generation."""

    def test_generate_final_report_basic(self, monitor):
        """Should generate final report outline."""
        outline = monitor.generate_final_report_outline("P170019")
        assert outline["document_type"] == "PAS Final Report Outline"
        assert outline["pma_number"] == "P170019"

    def test_final_report_has_10_sections(self, monitor):
        """Should have 10 standard report sections."""
        outline = monitor.generate_final_report_outline("P170019")
        assert len(outline["sections"]) == 10

    def test_final_report_section_numbering(self, monitor):
        """Sections should be numbered 1-10."""
        outline = monitor.generate_final_report_outline("P170019")
        for i, section in enumerate(outline["sections"], 1):
            assert section["section_number"] == str(i)

    def test_final_report_sections_not_started(self, monitor):
        """All sections should start as NOT_STARTED."""
        outline = monitor.generate_final_report_outline("P170019")
        for section in outline["sections"]:
            assert section["status"] == "NOT_STARTED"

    def test_final_report_has_sign_off(self, monitor):
        """Should include review sign-off section."""
        outline = monitor.generate_final_report_outline("P170019")
        sign_off = outline["review_sign_off"]
        assert "clinical_lead" in sign_off
        assert "biostatistician" in sign_off
        assert "regulatory_lead" in sign_off
        assert "quality_assurance" in sign_off

    def test_final_report_has_regulatory_requirements(self, monitor):
        """Should include regulatory requirements."""
        outline = monitor.generate_final_report_outline("P170019")
        reqs = outline["regulatory_requirements"]
        assert reqs["cfr_ref"] == "21 CFR 814.82"
        assert reqs["submission_type"] == "PAS Final Report"

    def test_final_report_completion_status(self, monitor):
        """Should track completion status."""
        outline = monitor.generate_final_report_outline("P170019")
        status = outline["completion_status"]
        assert status["sections_completed"] == 0
        assert status["sections_total"] == 10
        assert status["pct_complete"] == 0.0

    def test_final_report_key_sections_present(self, monitor):
        """Should include key report sections."""
        outline = monitor.generate_final_report_outline("P170019")
        section_titles = [s["title"] for s in outline["sections"]]
        assert "Executive Summary" in section_titles
        assert "Safety Results" in section_titles
        assert "Effectiveness Results" in section_titles
        assert "Protocol Deviations" in section_titles
        assert "Conclusions" in section_titles


# ============================================================
# Test: Milestone monitoring dashboard
# ============================================================

class TestMilestoneDashboard:
    """Test milestone monitoring dashboard."""

    def test_generate_dashboard_basic(self, monitor, _mock_store):
        """Should generate milestone dashboard."""
        dashboard = monitor.generate_milestone_dashboard("P170019")
        assert dashboard["document_type"] == "PAS Milestone Dashboard"
        assert dashboard["pma_number"] == "P170019"

    def test_dashboard_has_metrics(self, monitor):
        """Should include dashboard metrics."""
        dashboard = monitor.generate_milestone_dashboard("P170019")
        metrics = dashboard["metrics"]
        assert "total_milestones" in metrics
        assert "completed" in metrics
        assert "overdue" in metrics
        assert "upcoming" in metrics
        assert "completion_pct" in metrics

    def test_dashboard_has_critical_path_status(self, monitor):
        """Should include critical path status."""
        dashboard = monitor.generate_milestone_dashboard("P170019")
        assert "critical_path_status" in dashboard
        assert dashboard["critical_path_status"] in {
            "CRITICAL", "AT_RISK", "ATTENTION_NEEDED", "ON_TRACK"
        }

    def test_dashboard_has_next_milestone(self, monitor):
        """Should identify next milestone."""
        dashboard = monitor.generate_milestone_dashboard("P170019")
        assert "next_milestone" in dashboard

    def test_dashboard_includes_compliance(self, monitor):
        """Should include compliance assessment."""
        dashboard = monitor.generate_milestone_dashboard("P170019")
        assert "compliance" in dashboard

    def test_dashboard_includes_alerts(self, monitor):
        """Should include alerts."""
        dashboard = monitor.generate_milestone_dashboard("P170019")
        assert "alerts" in dashboard


# ============================================================
# Test: Backward compatibility
# ============================================================

class TestBackwardCompatibility:
    """Verify enhanced monitor doesn't break existing functionality."""

    def test_existing_generate_pas_report(self, monitor):
        """Existing generate_pas_report should still work."""
        report = monitor.generate_pas_report("P170019")
        assert report["pma_number"] == "P170019"
        assert "pas_requirements" in report
        assert "milestones" in report
        assert "compliance" in report
        assert "alerts" in report

    def test_existing_pas_types_intact(self):
        """PAS_TYPES should be intact."""
        assert len(PAS_TYPES) >= 4
        assert "continued_approval" in PAS_TYPES
        assert "section_522" in PAS_TYPES

    def test_existing_pas_milestones_intact(self):
        """PAS_MILESTONES should be intact."""
        assert len(PAS_MILESTONES) >= 8

    def test_existing_pas_status_definitions(self):
        """PAS_STATUS definitions should be intact."""
        assert len(PAS_STATUS) >= 8
        assert "enrolling" in PAS_STATUS
        assert "completed" in PAS_STATUS
