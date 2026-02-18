"""
Comprehensive test suite for PMA Annual Report Generator Enhancement -- FDA-66.

Tests cover all enhanced deliverables:
    1. Enhanced annual report outline (21 CFR 814.84 compliant)
    2. Distribution data template
    3. Adverse event summary generator
    4. Device modification tracking
    5. Bibliography updates
    6. Post-approval study status tracker
    7. Manufacturing changes documentation
    8. Labeling changes tracker

Target: 35+ tests covering all FDA-66 acceptance criteria.
All tests run offline (no network access) using mocks.
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

from annual_report_tracker import (  # type: ignore
    ANNUAL_REPORT_SECTIONS,
    ANNUAL_REPORT_GRACE_PERIOD_DAYS,
    AnnualReportTracker,
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
        "pma_number": "P170019S002",
        "supplement_number": "S002",
        "supplement_type": "30-Day Notice",
        "supplement_reason": "Minor labeling editorial change",
        "decision_date": "20180901",
        "decision_code": "APPR",
    },
    {
        "pma_number": "P170019S003",
        "supplement_number": "S003",
        "supplement_type": "Real-Time Supplement",
        "supplement_reason": "Design change with clinical data for safety improvement",
        "decision_date": "20190301",
        "decision_code": "APPR",
    },
]


@pytest.fixture
def mock_store():
    """Create a mock PMADataStore."""
    store = MagicMock()
    store.get_pma_data.return_value = SAMPLE_PMA_DATA
    store.get_supplements.return_value = SAMPLE_SUPPLEMENTS
    store.get_pma_dir.return_value = MagicMock()
    return store


@pytest.fixture
def tracker(mock_store):
    """Create AnnualReportTracker with mocked store."""
    return AnnualReportTracker(store=mock_store)


# ============================================================
# Test: Distribution data template
# ============================================================

class TestDistributionTemplate:
    """Test distribution data template generation."""

    def test_generate_distribution_template_basic(self, tracker):
        """Should generate distribution data template."""
        template = tracker.generate_distribution_template("P170019")
        assert template["section"] == "device_distribution"
        assert template["cfr_ref"] == "21 CFR 814.84(b)(1)"
        assert template["pma_number"] == "P170019"

    def test_distribution_template_has_fields(self, tracker):
        """Should include all required distribution data fields."""
        template = tracker.generate_distribution_template("P170019")
        dist = template["distribution_data"]
        assert "total_devices_distributed" in dist
        assert "domestic_distribution" in dist
        assert "international_distribution" in dist
        assert "devices_returned" in dist
        assert "devices_replaced" in dist
        assert "failure_complaints_received" in dist

    def test_distribution_template_reporting_period(self, tracker):
        """Should include reporting period."""
        template = tracker.generate_distribution_template(
            "P170019", "2025-11-30", "2026-11-30"
        )
        assert template["reporting_period"]["start"] == "2025-11-30"
        assert template["reporting_period"]["end"] == "2026-11-30"

    def test_distribution_template_pma_number_uppercased(self, tracker):
        """PMA number should be uppercased."""
        template = tracker.generate_distribution_template("p170019")
        assert template["pma_number"] == "P170019"


# ============================================================
# Test: Adverse event summary generator
# ============================================================

class TestAdverseEventSummary:
    """Test adverse event summary generation."""

    def test_generate_ae_summary_basic(self, tracker):
        """Should generate adverse event summary template."""
        summary = tracker.generate_adverse_event_summary("P170019")
        assert summary["section"] == "adverse_events"
        assert summary["cfr_ref"] == "21 CFR 814.84(b)(4)"

    def test_ae_summary_has_required_fields(self, tracker):
        """Should include required AE fields."""
        summary = tracker.generate_adverse_event_summary("P170019")
        s = summary["summary"]
        assert "total_mdr_reports" in s
        assert "deaths" in s
        assert "serious_injuries" in s
        assert "malfunctions" in s

    def test_ae_summary_with_maude_data(self, tracker):
        """Should pre-populate from MAUDE data when provided."""
        maude_data = [
            {"event_type": "Malfunction", "description": "Test1"},
            {"event_type": "Injury", "description": "Test2"},
            {"event_type": "Malfunction", "description": "Test3"},
        ]
        summary = tracker.generate_adverse_event_summary(
            "P170019", maude_data=maude_data
        )
        assert summary["summary"]["total_mdr_reports"] == 3
        breakdown = summary["summary"]["event_type_breakdown"]
        assert len(breakdown) == 2
        # Malfunctions should be first (sorted by count descending)
        assert breakdown[0]["event_type"] == "Malfunction"
        assert breakdown[0]["count"] == 2

    def test_ae_summary_without_maude_data(self, tracker):
        """Without MAUDE data, totals should be zero."""
        summary = tracker.generate_adverse_event_summary("P170019")
        assert summary["summary"]["total_mdr_reports"] == 0
        assert summary["summary"]["event_type_breakdown"] == []

    def test_ae_summary_has_trending_analysis(self, tracker):
        """Should include trending analysis section."""
        summary = tracker.generate_adverse_event_summary("P170019")
        trending = summary["trending_analysis"]
        assert "comparison_to_prior_period" in trending
        assert "new_signal_detected" in trending

    def test_ae_summary_has_maude_cross_reference(self, tracker):
        """Should include MAUDE cross-reference section."""
        summary = tracker.generate_adverse_event_summary("P170019")
        maude_ref = summary["maude_cross_reference"]
        assert "maude_search_performed" in maude_ref
        assert "maude_report_numbers" in maude_ref


# ============================================================
# Test: Device modification tracking
# ============================================================

class TestModificationTracker:
    """Test device modification tracking."""

    def test_generate_modification_tracker_basic(self, tracker):
        """Should generate modification tracker template."""
        mods = tracker.generate_modification_tracker("P170019")
        assert mods["section"] == "device_modifications"
        assert mods["cfr_ref"] == "21 CFR 814.84(b)(2)"

    def test_modification_tracker_with_supplements(self, tracker):
        """Should pre-populate from supplement data."""
        mods = tracker.generate_modification_tracker(
            "P170019", supplements=SAMPLE_SUPPLEMENTS
        )
        assert len(mods["supplement_changes"]) >= 1

    def test_modification_tracker_period_filtering(self, tracker):
        """Should filter supplements by reporting period."""
        mods = tracker.generate_modification_tracker(
            "P170019",
            supplements=SAMPLE_SUPPLEMENTS,
            reporting_period_start="2018-01-01",
            reporting_period_end="2018-12-31",
        )
        # Should include S001 (20180615) and S002 (20180901) but not S003 (20190301)
        for change in mods["supplement_changes"]:
            assert change["decision_date"] >= "20180101"
            assert change["decision_date"] <= "20181231"

    def test_modification_tracker_has_change_categories(self, tracker):
        """Should include labeling, design, and software change categories."""
        mods = tracker.generate_modification_tracker("P170019")
        assert "labeling_changes" in mods
        assert "design_changes" in mods
        assert "software_changes" in mods
        assert "thirty_day_notices" in mods


# ============================================================
# Test: Bibliography updates
# ============================================================

class TestBibliography:
    """Test bibliography update template."""

    def test_generate_bibliography_basic(self, tracker):
        """Should generate bibliography template."""
        bib = tracker.generate_bibliography_template("P170019")
        assert bib["section"] == "bibliography"
        assert bib["pma_number"] == "P170019"

    def test_bibliography_has_required_fields(self, tracker):
        """Should include all bibliography fields."""
        bib = tracker.generate_bibliography_template("P170019")
        assert "new_publications" in bib
        assert "conference_presentations" in bib
        assert "regulatory_guidances" in bib
        assert "standards_updates" in bib
        assert "total_new_references" in bib


# ============================================================
# Test: Post-approval study status
# ============================================================

class TestPASStatus:
    """Test post-approval study status template."""

    def test_generate_pas_status_basic(self, tracker):
        """Should generate PAS status template."""
        pas = tracker.generate_pas_status_template("P170019")
        assert pas["section"] == "clinical_studies"
        assert pas["cfr_ref"] == "21 CFR 814.84(b)(5)"

    def test_pas_status_has_study_template(self, tracker):
        """Should include a study template for consistency."""
        pas = tracker.generate_pas_status_template("P170019")
        template = pas["study_template"]
        assert "study_name" in template
        assert "enrollment_target" in template
        assert "study_status" in template
        assert "next_milestone" in template

    def test_pas_status_has_reporting_period(self, tracker):
        """Should include reporting period."""
        pas = tracker.generate_pas_status_template(
            "P170019", "2025-01-01", "2025-12-31"
        )
        assert pas["reporting_period"]["start"] == "2025-01-01"
        assert pas["reporting_period"]["end"] == "2025-12-31"


# ============================================================
# Test: Manufacturing changes
# ============================================================

class TestManufacturingChanges:
    """Test manufacturing changes documentation."""

    def test_generate_manufacturing_basic(self, tracker):
        """Should generate manufacturing changes template."""
        mfg = tracker.generate_manufacturing_changes_template("P170019")
        assert mfg["section"] == "manufacturing_changes"
        assert mfg["cfr_ref"] == "21 CFR 814.84(b)(6)"

    def test_manufacturing_has_change_categories(self, tracker):
        """Should include all manufacturing change categories."""
        mfg = tracker.generate_manufacturing_changes_template("P170019")
        assert "process_changes" in mfg
        assert "facility_changes" in mfg
        assert "supplier_changes" in mfg
        assert "equipment_changes" in mfg
        assert "sterilization_changes" in mfg
        assert "quality_system_changes" in mfg

    def test_manufacturing_has_supplement_tracking(self, tracker):
        """Should track which changes required supplements."""
        mfg = tracker.generate_manufacturing_changes_template("P170019")
        assert "changes_requiring_supplement" in mfg
        assert "changes_not_requiring_supplement" in mfg


# ============================================================
# Test: Labeling changes
# ============================================================

class TestLabelingChanges:
    """Test labeling changes tracker."""

    def test_generate_labeling_basic(self, tracker):
        """Should generate labeling changes template."""
        lab = tracker.generate_labeling_changes_template("P170019")
        assert lab["section"] == "labeling_changes"

    def test_labeling_has_change_categories(self, tracker):
        """Should include all labeling change categories."""
        lab = tracker.generate_labeling_changes_template("P170019")
        assert "ifu_changes" in lab
        assert "labeling_text_changes" in lab
        assert "indication_changes" in lab
        assert "warning_changes" in lab
        assert "contraindication_changes" in lab

    def test_labeling_has_submission_tracking(self, tracker):
        """Should track submission types for labeling changes."""
        lab = tracker.generate_labeling_changes_template("P170019")
        assert "changes_submitted_as_supplement" in lab
        assert "changes_submitted_as_30_day_notice" in lab
        assert "changes_not_requiring_submission" in lab


# ============================================================
# Test: Complete annual report outline
# ============================================================

class TestAnnualReportOutline:
    """Test complete annual report outline generation."""

    def test_generate_outline_basic(self, tracker, _mock_store):
        """Should generate complete annual report outline."""
        outline = tracker.generate_annual_report_outline("P170019")
        assert outline["document_type"] == "PMA Annual Report"
        assert outline["cfr_ref"] == "21 CFR 814.84"
        assert outline["pma_number"] == "P170019"

    def test_outline_has_all_sections(self, tracker):
        """Outline should include all 7 required sections."""
        outline = tracker.generate_annual_report_outline("P170019")
        sections = outline.get("sections", {})
        assert "distribution" in sections
        assert "modifications" in sections
        assert "adverse_events" in sections
        assert "pas_status" in sections
        assert "manufacturing" in sections
        assert "labeling" in sections
        assert "bibliography" in sections

    def test_outline_has_device_info(self, tracker):
        """Outline should include device information."""
        outline = tracker.generate_annual_report_outline("P170019")
        assert outline["device_name"] == "FoundationOne CDx"
        assert outline["applicant"] == "FOUNDATION MEDICINE, INC."

    def test_outline_has_reporting_period(self, tracker):
        """Outline should calculate reporting period from approval date."""
        outline = tracker.generate_annual_report_outline("P170019")
        period = outline["reporting_period"]
        assert "start" in period
        assert "end" in period
        assert period["start"] < period["end"]

    def test_outline_has_submission_deadline(self, tracker):
        """Outline should include submission deadline (60 days grace)."""
        outline = tracker.generate_annual_report_outline("P170019")
        assert "submission_deadline" in outline
        # Deadline should be parseable
        datetime.strptime(outline["submission_deadline"], "%Y-%m-%d")

    def test_outline_has_completion_status(self, tracker):
        """Outline should track completion status."""
        outline = tracker.generate_annual_report_outline("P170019")
        status = outline["completion_status"]
        assert status["sections_completed"] == 0  # Initial
        assert status["sections_total"] == 7
        assert status["pct_complete"] == 0.0

    def test_outline_has_disclaimer(self, tracker):
        """Outline should include regulatory disclaimer."""
        outline = tracker.generate_annual_report_outline("P170019")
        assert "disclaimer" in outline
        assert "21 CFR 814.84" in outline["disclaimer"]

    def test_outline_error_on_missing_approval_date(self, tracker, mock_store):
        """Should return error when approval date is missing."""
        mock_store.get_pma_data.return_value = {
            "pma_number": "P999999",
            "device_name": "Test",
        }
        outline = tracker.generate_annual_report_outline("P999999")
        assert "error" in outline

    def test_outline_error_on_api_error(self, tracker, mock_store):
        """Should return error when API returns error."""
        mock_store.get_pma_data.return_value = {"error": "Not found"}
        outline = tracker.generate_annual_report_outline("PXXXXXX")
        assert "error" in outline

    def test_outline_sections_have_cfr_refs(self, tracker):
        """Each section in the outline should have a CFR reference."""
        outline = tracker.generate_annual_report_outline("P170019")
        for name, section in outline.get("sections", {}).items():
            assert "cfr_ref" in section, f"Section '{name}' missing cfr_ref"


# ============================================================
# Test: Backward compatibility
# ============================================================

class TestBackwardCompatibility:
    """Verify enhanced tracker doesn't break existing functionality."""

    def test_existing_generate_compliance_calendar(self, tracker):
        """Existing generate_compliance_calendar should still work."""
        calendar = tracker.generate_compliance_calendar("P170019")
        assert calendar["pma_number"] == "P170019"
        assert "due_dates" in calendar
        assert "required_sections" in calendar

    def test_existing_batch_calendar(self, tracker, mock_store):
        """Existing generate_batch_calendar should still work."""
        result = tracker.generate_batch_calendar(["P170019"])
        assert result["total_pmas"] == 1
        assert "P170019" in result["calendars"]

    def test_existing_section_definitions(self):
        """Existing ANNUAL_REPORT_SECTIONS should be intact."""
        assert len(ANNUAL_REPORT_SECTIONS) >= 8
        assert "device_distribution" in ANNUAL_REPORT_SECTIONS
        assert "adverse_events" in ANNUAL_REPORT_SECTIONS

    def test_grace_period_unchanged(self):
        """Grace period should remain 60 days."""
        assert ANNUAL_REPORT_GRACE_PERIOD_DAYS == 60
