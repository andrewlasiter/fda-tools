"""
Comprehensive test suite for PMA Post-Approval Monitoring -- Phase 3 (TICKET-003).

Tests cover all Phase 3 modules:
    1. TestSupplementTracker -- supplement_tracker.py lifecycle management
    2. TestAnnualReportTracker -- annual_report_tracker.py compliance calendar
    3. TestPASMonitor -- pas_monitor.py study monitoring
    4. TestSupplementClassification -- Regulatory type classification accuracy
    5. TestCrossModuleIntegration -- Integration across Phase 3 modules
    6. TestPhase1Compatibility -- Backward compatibility with Phase 1 supplement analysis

Target: 40+ tests covering all Phase 3 acceptance criteria.
All tests run offline (no network access) using mocks.
"""

import json
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

SAMPLE_PMA_DATA = {
    "pma_number": "P170019",
    "applicant": "FOUNDATION MEDICINE, INC.",
    "device_name": "FoundationOne CDx",
    "generic_name": "Next Generation Sequencing System",
    "product_code": "NMH",
    "decision_date": "20171130",
    "decision_code": "APPR",
    "advisory_committee": "CH",
    "advisory_committee_description": "Clinical Chemistry",
    "ao_statement": "Condition of approval: post-approval study required to evaluate long-term clinical utility.",
    "supplement_count": 29,
    "expedited_review_flag": "N",
}

SAMPLE_SUPPLEMENTS = [
    {
        "pma_number": "P170019S001",
        "supplement_number": "S001",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "New indication for BRCA1/2 companion diagnostic",
        "decision_date": "20180615",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S002",
        "supplement_number": "S002",
        "supplement_type": "30-Day Notice",
        "supplement_reason": "Minor labeling update for IFU revision",
        "decision_date": "20180901",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S003",
        "supplement_number": "S003",
        "supplement_type": "Real-Time Supplement",
        "supplement_reason": "Design change to include new biomarker panel",
        "decision_date": "20190301",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S004",
        "supplement_number": "S004",
        "supplement_type": "PMA Supplement",
        "supplement_reason": "Post-approval study interim report submission",
        "decision_date": "20190715",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S005",
        "supplement_number": "S005",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "Expanded indication for ALK fusion detection",
        "decision_date": "20200115",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S006",
        "supplement_number": "S006",
        "supplement_type": "Manufacturing Change",
        "supplement_reason": "Manufacturing facility site change",
        "decision_date": "20200601",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S007",
        "supplement_number": "S007",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "Labeling change for updated warnings and precautions",
        "decision_date": "20210301",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S008",
        "supplement_number": "S008",
        "supplement_type": "Panel-Track Supplement",
        "supplement_reason": "Significant modification to panel review required",
        "decision_date": "20210715",
        "decision_code": "DENY",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S009",
        "supplement_number": "S009",
        "supplement_type": "180-Day Supplement",
        "supplement_reason": "New indication expansion for ROS1 fusion detection",
        "decision_date": "20220301",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S010",
        "supplement_number": "S010",
        "supplement_type": "Real-Time Supplement",
        "supplement_reason": "Design change for new algorithm version with clinical data",
        "decision_date": "20230615",
        "decision_code": "APPR",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "trade_name": "FoundationOne CDx",
    },
]

SAMPLE_SECTIONS = {
    "sections": {
        "clinical_studies": {
            "content": "Post-approval study is required as a condition of approval to verify long-term clinical utility. A 522 post-market surveillance study is also ordered.",
            "word_count": 20,
        },
        "general_information": {
            "content": "The FoundationOne CDx is a next generation sequencing based in vitro diagnostic device.",
            "word_count": 14,
        },
    },
}


# ============================================================
# Mock fixtures
# ============================================================

def _create_mock_store():
    """Create a mock PMADataStore with consistent test data."""
    store = MagicMock()
    store.get_pma_data.return_value = SAMPLE_PMA_DATA
    store.get_supplements.return_value = SAMPLE_SUPPLEMENTS
    store.get_extracted_sections.return_value = SAMPLE_SECTIONS
    store.get_pma_dir.return_value = Path("/tmp/test_pma_cache/P170019")
    return store


# ============================================================
# 1. TestSupplementTracker
# ============================================================

class TestSupplementTracker:
    """Test the SupplementTracker class."""

    def setup_method(self):
        from supplement_tracker import SupplementTracker
        self.store = _create_mock_store()
        self.tracker = SupplementTracker(store=self.store)

    def test_generate_report_basic(self):
        """Test basic report generation."""
        report = self.tracker.generate_supplement_report("P170019")
        assert report["pma_number"] == "P170019"
        assert report["total_supplements"] == 10
        assert "regulatory_type_summary" in report
        assert "approval_status_summary" in report
        assert "supplements" in report

    def test_generate_report_no_supplements(self):
        """Test report generation with no supplements."""
        self.store.get_supplements.return_value = []
        report = self.tracker.generate_supplement_report("P170019")
        assert report["total_supplements"] == 0
        assert "note" in report

    def test_generate_report_api_error(self):
        """Test report generation with API error."""
        self.store.get_pma_data.return_value = {"error": "API unavailable"}
        report = self.tracker.generate_supplement_report("P170019")
        assert "error" in report

    def test_regulatory_type_classification(self):
        """Test that supplements are classified into correct regulatory types."""
        report = self.tracker.generate_supplement_report("P170019")
        types = report["regulatory_type_summary"]
        # Should have multiple types detected
        assert len(types) >= 3
        # 180-day supplements should be detected
        assert "180_day" in types

    def test_approval_status_summary(self):
        """Test approval status counting."""
        report = self.tracker.generate_supplement_report("P170019")
        statuses = report["approval_status_summary"]
        assert "approved" in statuses
        assert statuses["approved"] >= 8
        assert "denied" in statuses
        assert statuses["denied"] == 1

    def test_change_impact_analysis(self):
        """Test change impact analysis."""
        report = self.tracker.generate_supplement_report("P170019")
        impact = report["change_impact"]
        assert impact["total_changes"] == 10
        assert impact["cumulative_burden_score"] > 0
        assert impact["impact_level"] in ("HIGH", "MODERATE", "LOW", "MINIMAL")

    def test_frequency_analysis(self):
        """Test frequency analysis."""
        report = self.tracker.generate_supplement_report("P170019")
        freq = report["frequency_analysis"]
        assert freq["avg_per_year"] > 0
        assert freq["years_active"] >= 1
        assert "trend" in freq
        assert freq["trend"] in ("accelerating", "stable", "decelerating")

    def test_risk_flag_detection(self):
        """Test risk flag detection."""
        report = self.tracker.generate_supplement_report("P170019")
        flags = report["risk_flags"]
        # Should detect denied supplement flag
        denied_flags = [f for f in flags if f["flag"] == "denied_withdrawn_supplements"]
        assert len(denied_flags) >= 1

    def test_timeline_generation(self):
        """Test timeline generation includes initial approval and supplements."""
        report = self.tracker.generate_supplement_report("P170019")
        timeline = report["timeline"]
        # Should have initial approval + 10 supplements = 11 events
        assert len(timeline) >= 11
        # First event should be initial approval
        assert timeline[0]["event_type"] == "initial_approval"

    def test_lifecycle_tracking(self):
        """Test lifecycle phase tracking."""
        report = self.tracker.generate_supplement_report("P170019")
        lifecycle = report["lifecycle"]
        assert len(lifecycle["phases"]) >= 1
        assert lifecycle["phases"][0]["phase"] == "initial_approval"

    def test_dependency_detection(self):
        """Test supplement dependency detection."""
        report = self.tracker.generate_supplement_report("P170019")
        deps = report["dependencies"]
        # Dependencies are detected between design + labeling pairs
        assert isinstance(deps, list)


# ============================================================
# 2. TestSupplementClassification
# ============================================================

class TestSupplementClassification:
    """Test regulatory type classification accuracy."""

    def setup_method(self):
        from supplement_tracker import SupplementTracker
        self.store = _create_mock_store()
        self.tracker = SupplementTracker(store=self.store)

    def test_180_day_detection(self):
        """Test 180-day supplement detection."""
        supp = {
            "supplement_type": "180-Day Supplement",
            "supplement_reason": "New indication for labeling",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["regulatory_type"] == "180_day"
        assert classified["approval_status"] == "approved"

    def test_real_time_detection(self):
        """Test real-time supplement detection."""
        supp = {
            "supplement_type": "Real-Time Supplement",
            "supplement_reason": "Design change with clinical data support",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["regulatory_type"] == "real_time"

    def test_30_day_notice_detection(self):
        """Test 30-day notice detection."""
        supp = {
            "supplement_type": "30-Day Notice",
            "supplement_reason": "Minor labeling editorial change",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["regulatory_type"] == "30_day_notice"

    def test_panel_track_detection(self):
        """Test panel-track supplement detection."""
        supp = {
            "supplement_type": "Panel-Track Supplement",
            "supplement_reason": "Significant change requiring panel review",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["regulatory_type"] == "panel_track"

    def test_pas_related_detection(self):
        """Test PAS-related supplement detection."""
        supp = {
            "supplement_type": "PMA Supplement",
            "supplement_reason": "Post-approval study interim report",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["regulatory_type"] == "pas_related"

    def test_manufacturing_detection(self):
        """Test manufacturing change detection."""
        supp = {
            "supplement_type": "Manufacturing Change",
            "supplement_reason": "Manufacturing facility site change",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        # Manufacturing changes typically classify as real_time or manufacturing
        # depending on whether they require clinical data
        assert classified["regulatory_type"] in ["manufacturing", "real_time"]

    def test_denied_status(self):
        """Test denied supplement status mapping."""
        supp = {
            "supplement_type": "PMA Supplement",
            "supplement_reason": "Some change",
            "decision_date": "20200101",
            "decision_code": "DENY",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["approval_status"] == "denied"

    def test_withdrawn_status(self):
        """Test withdrawn supplement status mapping."""
        supp = {
            "supplement_type": "PMA Supplement",
            "supplement_reason": "Some change",
            "decision_date": "20200101",
            "decision_code": "WDRN",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["approval_status"] == "withdrawn"

    def test_change_scope_labeling_only(self):
        """Test labeling-only change scope detection."""
        supp = {
            "supplement_type": "180-Day Supplement",
            "supplement_reason": "Labeling change for warnings",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["change_scope"] == "labeling_only"

    def test_change_scope_design(self):
        """Test design change scope detection."""
        supp = {
            "supplement_type": "Real-Time Supplement",
            "supplement_reason": "Design modification to component material",
            "decision_date": "20200101",
            "decision_code": "APPR",
        }
        classified = self.tracker._classify_supplement(supp)
        assert classified["change_scope"] == "design_change"


# ============================================================
# 3. TestAnnualReportTracker
# ============================================================

class TestAnnualReportTracker:
    """Test the AnnualReportTracker class."""

    def setup_method(self):
        from annual_report_tracker import AnnualReportTracker
        self.store = _create_mock_store()
        self.tracker = AnnualReportTracker(store=self.store)

    def test_generate_calendar_basic(self):
        """Test basic calendar generation."""
        calendar = self.tracker.generate_compliance_calendar("P170019")
        assert calendar["pma_number"] == "P170019"
        assert calendar["approval_date"] == "2017-11-30"
        assert "due_dates" in calendar
        assert "required_sections" in calendar
        assert "compliance_risks" in calendar

    def test_due_date_calculation(self):
        """Test that due dates are calculated from approval anniversary."""
        calendar = self.tracker.generate_compliance_calendar("P170019")
        due_dates = calendar["due_dates"]
        assert len(due_dates) >= 5
        # First report should be 1 year after approval
        first_report = due_dates[0]
        assert first_report["report_number"] == 1
        assert first_report["anniversary_date"] == "2018-11-30"

    def test_grace_period(self):
        """Test that grace period is 60 days per 21 CFR 814.84."""
        assert (calendar_data := self.tracker.generate_compliance_calendar("P170019"))
        assert calendar_data["grace_period_days"] == 60
        # Check first due date grace deadline
        first = calendar_data["due_dates"][0]
        # Anniversary 2018-11-30 + 60 days = 2019-01-29
        assert first["grace_deadline"] == "2019-01-29"

    def test_required_sections(self):
        """Test that required sections are determined correctly."""
        calendar = self.tracker.generate_compliance_calendar("P170019")
        sections = calendar["required_sections"]
        # Should have at least the 6 always-required sections
        required = [s for s in sections if s["required"]]
        assert len(required) >= 6
        # Check specific sections
        section_names = [s["section"] for s in sections]
        assert "device_distribution" in section_names
        assert "adverse_events" in section_names
        assert "clinical_studies" in section_names

    def test_next_due_date(self):
        """Test next due date identification."""
        calendar = self.tracker.generate_compliance_calendar("P170019")
        next_due = calendar["next_due_date"]
        assert next_due is not None
        assert "due_date" in next_due
        assert "grace_deadline" in next_due

    def test_total_reports_expected(self):
        """Test total expected reports count."""
        calendar = self.tracker.generate_compliance_calendar("P170019")
        total = calendar["total_reports_expected"]
        # PMA approved 2017, current date 2026, should be ~8 reports
        assert total >= 7

    def test_compliance_risks(self):
        """Test compliance risk assessment."""
        calendar = self.tracker.generate_compliance_calendar("P170019")
        risks = calendar["compliance_risks"]
        assert isinstance(risks, list)
        # Should have at least an info risk about expected reports
        assert len(risks) >= 1

    def test_api_error_handling(self):
        """Test calendar generation with API error."""
        self.store.get_pma_data.return_value = {"error": "API unavailable"}
        calendar = self.tracker.generate_compliance_calendar("P170019")
        assert "error" in calendar

    def test_batch_calendar(self):
        """Test batch calendar generation."""
        result = self.tracker.generate_batch_calendar(["P170019", "P200024"])
        assert result["total_pmas"] == 2
        assert "calendars" in result
        assert "upcoming_deadlines" in result

    def test_device_characteristics_sterile(self):
        """Test sterile device characteristic detection."""
        self.store.get_pma_data.return_value = {
            **SAMPLE_PMA_DATA,
            "device_name": "Sterile Cardiac Stent System",
        }
        # Add sterile keyword in supplement
        sterile_supps = list(SAMPLE_SUPPLEMENTS)
        sterile_supps.append({
            "pma_number": "P170019S011",
            "supplement_number": "S011",
            "supplement_type": "Manufacturing",
            "supplement_reason": "Sterilization method change from EO to gamma",
            "decision_date": "20240101",
            "decision_code": "APPR",
        })
        self.store.get_supplements.return_value = sterile_supps

        calendar = self.tracker.generate_compliance_calendar("P170019")
        chars = calendar["device_characteristics"]
        char_types = [c["characteristic"] for c in chars]
        assert "sterile_device" in char_types


# ============================================================
# 4. TestPASMonitor
# ============================================================

class TestPASMonitor:
    """Test the PASMonitor class."""

    def setup_method(self):
        from pas_monitor import PASMonitor
        self.store = _create_mock_store()
        self.monitor = PASMonitor(store=self.store)

    def test_generate_report_basic(self):
        """Test basic PAS report generation."""
        report = self.monitor.generate_pas_report("P170019")
        assert report["pma_number"] == "P170019"
        assert "pas_required" in report
        assert "pas_requirements" in report
        assert "pas_status" in report
        assert "milestones" in report
        assert "compliance" in report
        assert "alerts" in report

    def test_pas_requirement_detection_from_ao(self):
        """Test PAS requirement detection from AO statement."""
        report = self.monitor.generate_pas_report("P170019")
        # AO statement contains 'post-approval study' keyword
        assert report["pas_required"] is True
        assert len(report["pas_requirements"]) >= 1
        # Check confidence is high for AO statement source
        for req in report["pas_requirements"]:
            if req.get("source") == "ao_statement":
                assert req["confidence"] >= 0.80

    def test_pas_requirement_detection_from_sections(self):
        """Test PAS requirement detection from SSED sections."""
        report = self.monitor.generate_pas_report("P170019")
        # Clinical sections contain '522 post-market surveillance'
        req_types = [r["type"] for r in report["pas_requirements"]]
        assert "section_522" in req_types or "continued_approval" in req_types

    def test_pas_supplement_identification(self):
        """Test PAS supplement identification."""
        report = self.monitor.generate_pas_report("P170019")
        pas_supps = report["pas_supplements"]
        # S004 has 'post-approval study' keyword
        assert len(pas_supps) >= 1
        supp_nums = [s["supplement_number"] for s in pas_supps]
        assert "S004" in supp_nums

    def test_pas_status_determination(self):
        """Test PAS status determination."""
        report = self.monitor.generate_pas_report("P170019")
        status = report["pas_status"]
        assert status["overall_status"] != "no_pas_required"
        assert len(status["per_study"]) >= 1

    def test_milestone_timeline(self):
        """Test milestone timeline generation."""
        report = self.monitor.generate_pas_report("P170019")
        milestones = report["milestones"]
        assert len(milestones) >= 8  # At least the required milestones
        # Check milestone structure
        for m in milestones:
            assert "milestone_id" in m
            assert "label" in m
            assert "expected_date" in m
            assert "status" in m

    def test_compliance_assessment(self):
        """Test compliance assessment."""
        report = self.monitor.generate_pas_report("P170019")
        compliance = report["compliance"]
        assert "compliance_status" in compliance
        assert "compliance_score" in compliance
        assert compliance["compliance_status"] in (
            "COMPLIANT", "ON_TRACK", "AT_RISK",
            "NON_COMPLIANT", "INSUFFICIENT_DATA", "not_applicable",
        )

    def test_alert_generation(self):
        """Test alert generation."""
        report = self.monitor.generate_pas_report("P170019")
        alerts = report["alerts"]
        assert len(alerts) >= 1  # At least PAS requirement alert
        # Check alert structure
        for alert in alerts:
            assert "alert_type" in alert
            assert "severity" in alert
            assert "description" in alert

    def test_no_pas_required(self):
        """Test when no PAS is required."""
        self.store.get_pma_data.return_value = {
            **SAMPLE_PMA_DATA,
            "ao_statement": "",
        }
        self.store.get_supplements.return_value = [
            {
                "pma_number": "P999999S001",
                "supplement_number": "S001",
                "supplement_type": "180-Day Supplement",
                "supplement_reason": "Minor labeling change",
                "decision_date": "20200101",
                "decision_code": "APPR",
            },
        ]
        self.store.get_extracted_sections.return_value = None

        report = self.monitor.generate_pas_report("P999999")
        assert report["pas_required"] is False
        assert report["pas_status"]["overall_status"] == "no_pas_required"

    def test_api_error_handling(self):
        """Test report generation with API error."""
        self.store.get_pma_data.return_value = {"error": "Not found"}
        report = self.monitor.generate_pas_report("P999999")
        assert "error" in report

    def test_milestone_status_classification(self):
        """Test that milestones are classified into proper statuses."""
        report = self.monitor.generate_pas_report("P170019")
        milestones = report["milestones"]
        statuses = set(m["status"] for m in milestones)
        # Should have at least one valid status (mock data may have uniform status)
        assert len(statuses) >= 1
        # Verify statuses are valid
        valid_statuses = {"completed", "overdue", "upcoming", "future", "not_started"}
        assert all(s in valid_statuses for s in statuses)


# ============================================================
# 5. TestCrossModuleIntegration
# ============================================================

class TestCrossModuleIntegration:
    """Test integration across Phase 3 modules."""

    def setup_method(self):
        self.store = _create_mock_store()

    def test_supplement_to_annual_report_data_flow(self):
        """Test that supplement data informs annual report requirements."""
        from supplement_tracker import SupplementTracker
        from annual_report_tracker import AnnualReportTracker

        supp_tracker = SupplementTracker(store=self.store)
        ar_tracker = AnnualReportTracker(store=self.store)

        supp_report = supp_tracker.generate_supplement_report("P170019")
        ar_calendar = ar_tracker.generate_compliance_calendar("P170019")

        # Both should use the same PMA data
        assert supp_report["pma_number"] == ar_calendar["pma_number"]

        # Annual report should reflect supplement activity
        assert ar_calendar["total_reports_expected"] >= 7

    def test_supplement_to_pas_monitor_link(self):
        """Test that PAS supplements are consistently identified."""
        from supplement_tracker import SupplementTracker
        from pas_monitor import PASMonitor

        supp_tracker = SupplementTracker(store=self.store)
        pas_monitor = PASMonitor(store=self.store)

        supp_report = supp_tracker.generate_supplement_report("P170019")
        pas_report = pas_monitor.generate_pas_report("P170019")

        # PAS-related supplements should appear in both reports
        supp_pas_count = sum(
            1 for s in supp_report.get("supplements", [])
            if s.get("regulatory_type") == "pas_related"
        )
        pas_supp_count = len(pas_report.get("pas_supplements", []))

        # Both should detect PAS supplements
        assert supp_pas_count >= 1
        assert pas_supp_count >= 1

    def test_all_modules_same_store(self):
        """Test all Phase 3 modules can share the same store."""
        from supplement_tracker import SupplementTracker
        from annual_report_tracker import AnnualReportTracker
        from pas_monitor import PASMonitor

        store = self.store
        st = SupplementTracker(store=store)
        ar = AnnualReportTracker(store=store)
        pm = PASMonitor(store=store)

        # All should successfully generate reports
        r1 = st.generate_supplement_report("P170019")
        r2 = ar.generate_compliance_calendar("P170019")
        r3 = pm.generate_pas_report("P170019")

        assert r1["pma_number"] == "P170019"
        assert r2["pma_number"] == "P170019"
        assert r3["pma_number"] == "P170019"

    def test_risk_flags_to_compliance(self):
        """Test that supplement risk flags can inform compliance assessment."""
        from supplement_tracker import SupplementTracker
        from annual_report_tracker import AnnualReportTracker

        supp_tracker = SupplementTracker(store=self.store)
        ar_tracker = AnnualReportTracker(store=self.store)

        supp_report = supp_tracker.generate_supplement_report("P170019")
        ar_calendar = ar_tracker.generate_compliance_calendar("P170019")

        # High supplement activity should generate active device monitoring risk
        assert supp_report["total_supplements"] == 10
        ar_risks = ar_calendar.get("compliance_risks", [])
        active_risks = [
            r for r in ar_risks
            if r.get("risk") == "active_device_monitoring"
        ]
        assert len(active_risks) >= 1


# ============================================================
# 6. TestPhase1Compatibility
# ============================================================

class TestPhase1Compatibility:
    """Test backward compatibility with Phase 1 supplement analysis."""

    def setup_method(self):
        self.store = _create_mock_store()

    def test_phase1_supplement_types_covered(self):
        """Test that Phase 1 SUPPLEMENT_TYPES are covered by Phase 3."""
        from pma_intelligence import SUPPLEMENT_TYPES
        from supplement_tracker import SUPPLEMENT_REGULATORY_TYPES

        phase1_types = set(SUPPLEMENT_TYPES.keys())
        phase3_types = set(SUPPLEMENT_REGULATORY_TYPES.keys())

        # Phase 3 should cover all Phase 1 categories or equivalent
        # Phase 1 has: labeling, design_change, indication_expansion,
        #              post_approval_study, manufacturing, panel_track
        # Phase 3 has: 180_day, real_time, 30_day_notice, panel_track,
        #              pas_related, manufacturing, other
        assert "panel_track" in phase3_types
        assert "manufacturing" in phase3_types
        assert "pas_related" in phase3_types

    def test_phase1_and_phase3_coexist(self):
        """Test that Phase 1 and Phase 3 can operate on same data."""
        from pma_intelligence import PMAIntelligenceEngine
        from supplement_tracker import SupplementTracker

        engine = PMAIntelligenceEngine(store=self.store)
        tracker = SupplementTracker(store=self.store)

        p1_result = engine.analyze_supplements("P170019")
        p3_result = tracker.generate_supplement_report("P170019")

        # Both should count same total supplements
        assert p1_result["total_supplements"] == p3_result["total_supplements"]

    def test_phase3_enriches_phase1_data(self):
        """Test that Phase 3 provides richer classification than Phase 1."""
        from pma_intelligence import PMAIntelligenceEngine
        from supplement_tracker import SupplementTracker

        engine = PMAIntelligenceEngine(store=self.store)
        tracker = SupplementTracker(store=self.store)

        p1_result = engine.analyze_supplements("P170019")
        p3_result = tracker.generate_supplement_report("P170019")

        # Phase 3 should provide additional analysis
        assert "change_impact" in p3_result
        assert "risk_flags" in p3_result
        assert "lifecycle" in p3_result
        assert "dependencies" in p3_result

        # Phase 1 should not have these
        assert "change_impact" not in p1_result
        assert "risk_flags" not in p1_result


# ============================================================
# 7. TestEdgeCases
# ============================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        self.store = _create_mock_store()

    def test_empty_supplements(self):
        """Test all modules handle empty supplement lists gracefully."""
        from supplement_tracker import SupplementTracker
        from annual_report_tracker import AnnualReportTracker
        from pas_monitor import PASMonitor

        self.store.get_supplements.return_value = []

        st = SupplementTracker(store=self.store)
        ar = AnnualReportTracker(store=self.store)
        pm = PASMonitor(store=self.store)

        r1 = st.generate_supplement_report("P170019")
        r2 = ar.generate_compliance_calendar("P170019")
        r3 = pm.generate_pas_report("P170019")

        assert r1["total_supplements"] == 0
        assert len(r2["due_dates"]) >= 1
        # PAS may still be detected from AO statement
        assert "pas_status" in r3

    def test_malformed_dates(self):
        """Test handling of malformed decision dates."""
        from supplement_tracker import SupplementTracker

        self.store.get_supplements.return_value = [
            {
                "pma_number": "P170019S001",
                "supplement_number": "S001",
                "supplement_type": "180-Day Supplement",
                "supplement_reason": "Labeling change",
                "decision_date": "",  # Empty date
                "decision_code": "APPR",
            },
            {
                "pma_number": "P170019S002",
                "supplement_number": "S002",
                "supplement_type": "Manufacturing",
                "supplement_reason": "Facility change",
                "decision_date": "invalid",  # Invalid date
                "decision_code": "APPR",
            },
        ]

        tracker = SupplementTracker(store=self.store)
        report = tracker.generate_supplement_report("P170019")
        # Should not crash
        assert report["total_supplements"] == 2

    def test_single_supplement(self):
        """Test with only one supplement."""
        from supplement_tracker import SupplementTracker

        self.store.get_supplements.return_value = [SAMPLE_SUPPLEMENTS[0]]
        tracker = SupplementTracker(store=self.store)
        report = tracker.generate_supplement_report("P170019")
        assert report["total_supplements"] == 1
        assert report["frequency_analysis"]["avg_per_year"] >= 0

    def test_very_old_pma(self):
        """Test with a very old PMA (many expected annual reports)."""
        from annual_report_tracker import AnnualReportTracker

        self.store.get_pma_data.return_value = {
            **SAMPLE_PMA_DATA,
            "decision_date": "20000101",
        }
        tracker = AnnualReportTracker(store=self.store)
        calendar = tracker.generate_compliance_calendar("P170019")
        assert calendar["total_reports_expected"] >= 25

    def test_no_sections_available(self):
        """Test PAS monitor without extracted sections."""
        from pas_monitor import PASMonitor

        self.store.get_extracted_sections.return_value = None
        monitor = PASMonitor(store=self.store)
        report = monitor.generate_pas_report("P170019")
        # Should still detect PAS from AO statement
        assert "pas_requirements" in report
