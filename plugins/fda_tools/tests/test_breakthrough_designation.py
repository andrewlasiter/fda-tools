"""
Comprehensive test suite for Breakthrough Device Designation Support -- FDA-43.

Tests cover all deliverables:
    1. Breakthrough designation request template generation
    2. Life-threatening condition justification templates
    3. Unmet medical need analysis templates
    4. Sprint review process tracker
    5. Interactive review documentation
    6. Milestone status updates
    7. Template persistence
    8. CLI formatting

Target: 30+ tests covering all FDA-43 acceptance criteria.
All tests run offline (no network access).
"""

import os
import sys
import tempfile
from datetime import datetime

import pytest

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)

from breakthrough_designation import (  # type: ignore
    BREAKTHROUGH_CRITERIA,
    CONDITION_CATEGORIES,
    SPRINT_REVIEW_MILESTONES,
    INTERACTIVE_REVIEW_SECTIONS,
    REGULATORY_DISCLAIMER,
    BreakthroughDesignation,
)


# ============================================================
# Test fixtures
# ============================================================

@pytest.fixture
def bt():
    """Create BreakthroughDesignation instance with temp output dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield BreakthroughDesignation(output_dir=tmpdir)


@pytest.fixture
def sample_request(bt):
    """Generate a sample request template."""
    return bt.generate_request_template(
        device_name="CardioAssist Pro",
        specialty="cardiology",
        intended_use="Treatment of severe heart failure",
    )


@pytest.fixture
def sample_tracker(bt):
    """Generate a sample sprint tracker."""
    return bt.create_sprint_review_tracker(
        device_name="CardioAssist Pro",
        start_date="2026-01-15",
    )


# ============================================================
# Test: Constants and definitions
# ============================================================

class TestConstants:
    """Test module-level constants and definitions."""

    def test_breakthrough_criteria_defined(self):
        """All four statutory criteria should be defined."""
        assert len(BREAKTHROUGH_CRITERIA) == 4
        expected_keys = {
            "breakthrough_technology",
            "no_alternatives",
            "significant_advantages",
            "best_interest",
        }
        assert set(BREAKTHROUGH_CRITERIA.keys()) == expected_keys

    def test_breakthrough_criteria_have_required_fields(self):
        """Each criterion should have label, cfr_ref, description, evidence_needed."""
        for key, criterion in BREAKTHROUGH_CRITERIA.items():
            assert "label" in criterion, f"Missing label for {key}"
            assert "cfr_ref" in criterion, f"Missing cfr_ref for {key}"
            assert "description" in criterion, f"Missing description for {key}"
            assert "evidence_needed" in criterion, f"Missing evidence_needed for {key}"
            assert len(criterion["evidence_needed"]) >= 3, f"Too few evidence items for {key}"

    def test_condition_categories_defined(self):
        """At least 5 condition categories should be defined."""
        assert len(CONDITION_CATEGORIES) >= 5
        assert "cardiovascular" in CONDITION_CATEGORIES
        assert "oncology" in CONDITION_CATEGORIES
        assert "neurological" in CONDITION_CATEGORIES

    def test_condition_categories_have_required_fields(self):
        """Each category should have label, conditions, mortality_data."""
        for key, category in CONDITION_CATEGORIES.items():
            assert "label" in category, f"Missing label for {key}"
            assert "conditions" in category, f"Missing conditions for {key}"
            assert len(category["conditions"]) >= 3, f"Too few conditions for {key}"
            assert "mortality_data" in category, f"Missing mortality_data for {key}"

    def test_sprint_review_milestones_defined(self):
        """At least 8 sprint review milestones should be defined."""
        assert len(SPRINT_REVIEW_MILESTONES) >= 8

    def test_sprint_milestones_have_required_fields(self):
        """Each milestone should have id, label, description, deliverables."""
        for milestone in SPRINT_REVIEW_MILESTONES:
            assert "id" in milestone
            assert "label" in milestone
            assert "description" in milestone
            assert "deliverables" in milestone
            assert len(milestone["deliverables"]) >= 2
            assert "typical_week" in milestone

    def test_interactive_review_sections_defined(self):
        """Interactive review sections should be defined."""
        assert len(INTERACTIVE_REVIEW_SECTIONS) >= 3
        assert "meeting_summary" in INTERACTIVE_REVIEW_SECTIONS
        assert "action_item_tracker" in INTERACTIVE_REVIEW_SECTIONS


# ============================================================
# Test: Request template generation
# ============================================================

class TestRequestTemplate:
    """Test Breakthrough designation request template generation."""

    def test_generate_request_template_basic(self, bt):
        """Basic request template should have all required sections."""
        template = bt.generate_request_template("TestDevice")
        assert template["document_type"] == "Breakthrough Device Designation Request"
        assert template["regulatory_reference"] == "Section 515B of the FD&C Act (21 U.S.C. 360e-3)"
        assert template["fda_form"] == "FDA Form 3913"

    def test_request_template_device_info(self, sample_request):
        """Device information should be populated."""
        device_info = sample_request["device_information"]
        assert device_info["device_name"] == "CardioAssist Pro"
        assert device_info["specialty"] == "cardiology"
        assert device_info["intended_use"] == "Treatment of severe heart failure"

    def test_request_template_all_criteria_included(self, sample_request):
        """All 4 criteria should be included by default."""
        criteria = sample_request["designation_criteria"]
        assert len(criteria) == 4
        criteria_types = {c["criterion"] for c in criteria}
        assert "breakthrough_technology" in criteria_types
        assert "significant_advantages" in criteria_types

    def test_request_template_selective_criteria(self, bt):
        """Should support selecting specific criteria."""
        template = bt.generate_request_template(
            "TestDevice",
            criteria=["breakthrough_technology", "no_alternatives"],
        )
        criteria = template["designation_criteria"]
        assert len(criteria) == 2

    def test_request_template_criteria_status_not_started(self, sample_request):
        """All criteria should start with NOT_STARTED status."""
        for criterion in sample_request["designation_criteria"]:
            assert criterion["status"] == "NOT_STARTED"
            assert criterion["evidence_provided"] == []

    def test_request_template_has_checklist(self, sample_request):
        """Request should include a submission checklist."""
        checklist = sample_request["submission_checklist"]
        assert isinstance(checklist, dict)
        assert len(checklist) >= 5
        # All items should be unchecked initially
        for _item, done in checklist.items():
            assert done is False

    def test_request_template_has_applicant_section(self, sample_request):
        """Request should include applicant information section."""
        applicant = sample_request["applicant_information"]
        assert "company_name" in applicant
        assert "contact_name" in applicant

    def test_request_template_has_generated_at(self, sample_request):
        """Template should have a generated_at timestamp."""
        assert "generated_at" in sample_request
        # Should be a valid ISO format
        datetime.fromisoformat(sample_request["generated_at"].replace("Z", "+00:00"))

    def test_request_template_has_unmet_need_section(self, sample_request):
        """Request should include unmet medical need section."""
        unmet = sample_request["unmet_medical_need"]
        assert "current_treatment_landscape" in unmet
        assert "device_advantages" in unmet

    def test_request_template_has_preliminary_evidence(self, sample_request):
        """Request should include preliminary evidence section."""
        evidence = sample_request["preliminary_evidence"]
        assert "bench_testing" in evidence
        assert "clinical_data" in evidence


# ============================================================
# Test: Condition justification templates
# ============================================================

class TestConditionJustification:
    """Test life-threatening condition justification templates."""

    def test_generate_cardiovascular_justification(self, bt):
        """Should generate cardiovascular condition justification."""
        just = bt.generate_condition_justification("cardiovascular")
        assert just["document_type"] == "Life-Threatening Condition Justification"
        assert just["condition_category"]["category"] == "cardiovascular"
        assert len(just["condition_category"]["conditions_in_scope"]) >= 5

    def test_generate_oncology_justification(self, bt):
        """Should generate oncology condition justification."""
        just = bt.generate_condition_justification("oncology")
        assert just["condition_category"]["label"] == "Oncology Conditions"
        assert len(just["condition_category"]["conditions_in_scope"]) >= 4

    def test_justification_with_specific_condition(self, bt):
        """Should accept a specific condition within the category."""
        just = bt.generate_condition_justification(
            "cardiovascular",
            specific_condition="Heart failure (HFrEF)",
        )
        assert just["condition_category"]["specific_condition"] == "Heart failure (HFrEF)"

    def test_justification_with_custom_conditions(self, bt):
        """Should accept custom conditions not in predefined list."""
        custom = ["Rare cardiac myopathy", "Novel arrhythmia syndrome"]
        just = bt.generate_condition_justification(
            "cardiovascular",
            custom_conditions=custom,
        )
        conditions = just["condition_category"]["conditions_in_scope"]
        assert "Rare cardiac myopathy" in conditions
        assert "Novel arrhythmia syndrome" in conditions

    def test_justification_has_criteria_sections(self, bt):
        """Should include life-threatening and irreversibly debilitating criteria."""
        just = bt.generate_condition_justification("neurological")
        elements = just["justification_elements"]
        assert "life_threatening_criteria" in elements
        assert "irreversibly_debilitating_criteria" in elements
        assert elements["life_threatening_criteria"]["applies"] is None  # To be filled

    def test_justification_has_epidemiological_data(self, bt):
        """Should include epidemiological data section."""
        just = bt.generate_condition_justification("oncology")
        epi = just["epidemiological_data"]
        assert "prevalence" in epi
        assert "mortality_data" in epi
        assert len(epi["mortality_data"]) > 0  # Pre-populated from constants

    def test_justification_unknown_category(self, bt):
        """Should handle unknown category gracefully."""
        just = bt.generate_condition_justification("unknown_category")
        assert just["condition_category"]["category"] == "unknown_category"
        assert just["condition_category"]["label"] == "unknown_category"


# ============================================================
# Test: Unmet medical need analysis
# ============================================================

class TestUnmetNeedAnalysis:
    """Test unmet medical need analysis templates."""

    def test_generate_unmet_need_basic(self, bt):
        """Should generate unmet need analysis template."""
        analysis = bt.generate_unmet_need_analysis("TestDevice")
        assert analysis["document_type"] == "Unmet Medical Need Analysis"
        assert analysis["device_name"] == "TestDevice"

    def test_unmet_need_with_comparison(self, bt):
        """Should accept comparison device."""
        analysis = bt.generate_unmet_need_analysis(
            "NewDevice",
            comparison_device="ExistingDevice",
            condition="Heart failure",
        )
        assert analysis["comparison_device"] == "ExistingDevice"
        assert analysis["target_condition"] == "Heart failure"

    def test_unmet_need_has_analysis_sections(self, bt):
        """Should include all required analysis sections."""
        analysis = bt.generate_unmet_need_analysis("TestDevice")
        sections = analysis["analysis_sections"]
        assert "current_treatment_landscape" in sections
        assert "limitations_of_current_options" in sections
        assert "proposed_device_advantages" in sections
        assert "comparison_matrix" in sections
        assert "patient_population_impact" in sections
        assert "evidence_summary" in sections

    def test_unmet_need_comparison_dimensions(self, bt):
        """Comparison matrix should have standard dimensions."""
        analysis = bt.generate_unmet_need_analysis("TestDevice")
        dimensions = analysis["analysis_sections"]["comparison_matrix"]["comparison_dimensions"]
        assert len(dimensions) >= 5
        assert "Efficacy / Performance" in dimensions
        assert "Safety Profile" in dimensions


# ============================================================
# Test: Sprint review tracker
# ============================================================

class TestSprintReviewTracker:
    """Test sprint review process tracker."""

    def test_create_tracker_basic(self, bt):
        """Should create a basic sprint review tracker."""
        tracker = bt.create_sprint_review_tracker("TestDevice")
        assert tracker["document_type"] == "Breakthrough Device Sprint Review Tracker"
        assert tracker["device_name"] == "TestDevice"
        assert tracker["overall_progress_pct"] == 0.0

    def test_tracker_milestones_populated(self, sample_tracker):
        """Tracker should have all milestones populated."""
        milestones = sample_tracker["milestones"]
        assert len(milestones) == len(SPRINT_REVIEW_MILESTONES)

    def test_tracker_milestones_have_dates(self, sample_tracker):
        """All milestones should have target dates."""
        for milestone in sample_tracker["milestones"]:
            assert milestone["target_date"] is not None
            # Should be a valid date
            datetime.strptime(milestone["target_date"], "%Y-%m-%d")

    def test_tracker_milestone_dates_progressive(self, sample_tracker):
        """Milestone target dates should be in chronological order."""
        dates = [m["target_date"] for m in sample_tracker["milestones"]]
        for i in range(1, len(dates)):
            assert dates[i] >= dates[i - 1], f"Milestone {i} date not progressive"

    def test_tracker_all_milestones_not_started(self, sample_tracker):
        """All milestones should start as NOT_STARTED."""
        for milestone in sample_tracker["milestones"]:
            assert milestone["status"] == "NOT_STARTED"

    def test_tracker_milestones_have_deliverables(self, sample_tracker):
        """Each milestone should have deliverables."""
        for milestone in sample_tracker["milestones"]:
            assert len(milestone["deliverables"]) >= 1
            for d in milestone["deliverables"]:
                assert d["status"] == "NOT_STARTED"

    def test_tracker_with_custom_start_date(self, bt):
        """Should accept custom start date."""
        tracker = bt.create_sprint_review_tracker("TestDevice", start_date="2026-03-01")
        assert tracker["start_date"] == "2026-03-01"

    def test_tracker_estimated_completion(self, sample_tracker):
        """Should calculate estimated completion date (72 weeks from start)."""
        start = datetime.strptime(sample_tracker["start_date"], "%Y-%m-%d")
        completion = datetime.strptime(sample_tracker["estimated_completion"], "%Y-%m-%d")
        weeks_diff = (completion - start).days / 7
        assert 70 <= weeks_diff <= 74  # Approximately 72 weeks

    def test_tracker_has_status_history(self, sample_tracker):
        """Should have initial status history entry."""
        history = sample_tracker["status_history"]
        assert len(history) == 1
        assert history[0]["status"] == "INITIATED"


# ============================================================
# Test: Milestone updates
# ============================================================

class TestMilestoneUpdates:
    """Test milestone status update functionality."""

    def test_update_milestone_status(self, bt, sample_tracker):
        """Should update milestone status."""
        updated = bt.update_milestone_status(
            sample_tracker,
            "pre_submission",
            "COMPLETED",
            actual_date="2026-01-20",
            notes="Pre-submission sent to FDA",
        )
        milestone = updated["milestones"][0]
        assert milestone["status"] == "COMPLETED"
        assert milestone["actual_date"] == "2026-01-20"
        assert milestone["notes"] == "Pre-submission sent to FDA"

    def test_update_milestone_progress_calculation(self, bt, sample_tracker):
        """Progress should update when milestones complete."""
        total = len(sample_tracker["milestones"])
        updated = bt.update_milestone_status(sample_tracker, "pre_submission", "COMPLETED")
        expected_pct = round(1 / total * 100, 1)
        assert updated["overall_progress_pct"] == expected_pct

    def test_update_milestone_current_phase(self, bt, sample_tracker):
        """Current phase should advance past completed milestones."""
        updated = bt.update_milestone_status(sample_tracker, "pre_submission", "COMPLETED")
        assert updated["current_phase"] == "designation_request"

    def test_update_milestone_invalid_status(self, bt, sample_tracker):
        """Should reject invalid status values."""
        with pytest.raises(ValueError):
            bt.update_milestone_status(sample_tracker, "pre_submission", "INVALID")

    def test_update_milestone_adds_history(self, bt, sample_tracker):
        """Should add entry to status history."""
        initial_history_len = len(sample_tracker["status_history"])
        updated = bt.update_milestone_status(sample_tracker, "pre_submission", "IN_PROGRESS")
        assert len(updated["status_history"]) == initial_history_len + 1


# ============================================================
# Test: Interactive review records
# ============================================================

class TestInteractiveReview:
    """Test interactive review documentation."""

    def test_create_review_record(self, bt):
        """Should create an interactive review record template."""
        record = bt.create_interactive_review_record(
            "TestDevice",
            meeting_type="sprint_review",
            meeting_date="2026-03-15",
        )
        assert record["document_type"] == "Interactive Review Record"
        assert record["device_name"] == "TestDevice"
        assert record["meeting_information"]["meeting_date"] == "2026-03-15"
        assert record["meeting_information"]["meeting_type"] == "sprint_review"

    def test_review_record_has_attendees_section(self, bt):
        """Record should have attendee sections."""
        record = bt.create_interactive_review_record("TestDevice")
        assert "fda_attendees" in record["attendees"]
        assert "sponsor_attendees" in record["attendees"]

    def test_review_record_has_feedback_section(self, bt):
        """Record should have FDA feedback section."""
        record = bt.create_interactive_review_record("TestDevice")
        feedback = record["fda_feedback"]
        assert "positive_feedback" in feedback
        assert "concerns_raised" in feedback
        assert "recommendations" in feedback
        assert "required_actions" in feedback


# ============================================================
# Test: Report generation
# ============================================================

class TestReportGeneration:
    """Test report summary generation."""

    def test_designation_summary(self, bt, sample_request):
        """Should generate readable designation summary."""
        summary = bt.generate_designation_summary(sample_request)
        assert "BREAKTHROUGH DEVICE DESIGNATION REQUEST SUMMARY" in summary
        assert "CardioAssist Pro" in summary
        assert "cardiology" in summary

    def test_tracker_summary(self, bt, sample_tracker):
        """Should generate readable tracker summary."""
        summary = bt.generate_tracker_summary(sample_tracker)
        assert "BREAKTHROUGH DEVICE SPRINT REVIEW TRACKER" in summary
        assert "CardioAssist Pro" in summary
        assert "0.0%" in summary  # Initial progress


# ============================================================
# Test: Template persistence
# ============================================================

class TestPersistence:
    """Test template save/load functionality."""

    def test_save_and_load_template(self, bt, sample_request):
        """Should save and load template successfully."""
        filepath = bt.save_template(sample_request, "test_request")
        assert os.path.exists(filepath)

        loaded = bt.load_template("test_request")
        assert loaded is not None
        assert loaded["device_information"]["device_name"] == "CardioAssist Pro"

    def test_load_nonexistent_template(self, bt):
        """Should return None for nonexistent template."""
        result = bt.load_template("nonexistent_file")
        assert result is None

    def test_save_tracker(self, bt, sample_tracker):
        """Should save tracker successfully."""
        filepath = bt.save_template(sample_tracker, "test_tracker")
        assert os.path.exists(filepath)
        assert filepath.endswith(".json")

        loaded = bt.load_template("test_tracker")
        assert loaded is not None
        assert loaded["device_name"] == "CardioAssist Pro"


# ============================================================
# Test: Regulatory Disclaimers (FDA-87)
# ============================================================

class TestRegulatoryDisclaimers:
    """Test FDA-87: Regulatory disclaimers on Breakthrough designation outputs."""

    def test_regulatory_disclaimer_constant_exists(self):
        """REGULATORY_DISCLAIMER constant should be defined."""
        assert REGULATORY_DISCLAIMER is not None
        assert len(REGULATORY_DISCLAIMER.strip()) > 100
        assert "PLANNING AND RESEARCH" in REGULATORY_DISCLAIMER
        assert "regulatory affairs professionals" in REGULATORY_DISCLAIMER.lower()

    def test_designation_summary_includes_disclaimer(self, bt, sample_request):
        """Designation summary should include regulatory disclaimer."""
        summary = bt.generate_designation_summary(sample_request)
        assert "REGULATORY DISCLAIMER" in summary
        assert "PLANNING AND RESEARCH" in summary

    def test_tracker_summary_includes_disclaimer(self, bt, sample_tracker):
        """Tracker summary should include regulatory disclaimer."""
        summary = bt.generate_tracker_summary(sample_tracker)
        assert "REGULATORY DISCLAIMER" in summary
        assert "PLANNING AND RESEARCH" in summary

    def test_disclaimer_warns_against_sole_reliance(self):
        """Disclaimer should warn against using as sole basis for decisions."""
        assert "NOT" in REGULATORY_DISCLAIMER
        assert "sole basis" in REGULATORY_DISCLAIMER.lower() or \
               "without independent review" in REGULATORY_DISCLAIMER.lower()
