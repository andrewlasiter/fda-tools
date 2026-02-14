"""Tests for standards supersession detection and currency checking.

Validates the supersession database, date comparison logic, alert generation,
and the standards-tracking.md reference integrity.
"""

import os
import re
import pytest
from datetime import date, datetime


# Supersession database (mirrors the data in standards-tracking.md)
SUPERSESSIONS = {
    "ISO 10993-1:2018": {"new": "ISO 10993-1:2025", "transition": "2027-11-18"},
    "ISO 10993-1:2009": {"new": "ISO 10993-1:2025", "transition": "2027-11-18"},
    "ISO 11137-1:2006": {"new": "ISO 11137-1:2025", "transition": "2027-06-01"},
    "ISO 17665-1:2006": {"new": "ISO 17665:2024", "transition": "2026-12-01"},
}


@pytest.fixture
def standards_tracking_content():
    """Load the standards-tracking.md reference."""
    ref_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "skills",
        "fda-510k-knowledge",
        "references",
        "standards-tracking.md",
    )
    with open(ref_path) as f:
        return f.read()


class TestSupersessionDatabase:
    """Test the supersession database structure and accuracy."""

    def test_iso_10993_1_2018_superseded(self):
        info = SUPERSESSIONS["ISO 10993-1:2018"]
        assert info["new"] == "ISO 10993-1:2025"
        assert info["transition"] == "2027-11-18"

    def test_iso_10993_1_2009_superseded(self):
        info = SUPERSESSIONS["ISO 10993-1:2009"]
        assert info["new"] == "ISO 10993-1:2025"

    def test_iso_11137_superseded(self):
        info = SUPERSESSIONS["ISO 11137-1:2006"]
        assert info["new"] == "ISO 11137-1:2025"

    def test_iso_17665_superseded(self):
        info = SUPERSESSIONS["ISO 17665-1:2006"]
        assert info["new"] == "ISO 17665:2024"


class TestDateComparison:
    """Test transition deadline date comparison logic."""

    def test_transition_date_parsing(self):
        for info in SUPERSESSIONS.values():
            deadline = datetime.strptime(info["transition"], "%Y-%m-%d").date()
            assert isinstance(deadline, date)

    def test_days_remaining_calculation(self):
        today = date(2026, 2, 7)
        deadline = datetime.strptime("2027-11-18", "%Y-%m-%d").date()
        days = (deadline - today).days
        assert days > 0
        assert days == 649  # 2026-02-07 to 2027-11-18

    def test_expired_deadline_detection(self):
        today = date(2028, 1, 1)
        deadline = datetime.strptime("2027-11-18", "%Y-%m-%d").date()
        days = (deadline - today).days
        assert days < 0  # Past deadline

    def test_severity_assignment_critical(self):
        """Transition deadline < 3 months = critical."""
        days_remaining = 80
        severity = "critical" if days_remaining < 90 else "warning" if days_remaining < 180 else "info"
        assert severity == "critical"

    def test_severity_assignment_warning(self):
        """Transition deadline 3-6 months = warning."""
        days_remaining = 120
        severity = "critical" if days_remaining < 90 else "warning" if days_remaining < 180 else "info"
        assert severity == "warning"

    def test_severity_assignment_info(self):
        """Transition deadline > 6 months = info."""
        days_remaining = 365
        severity = "critical" if days_remaining < 90 else "warning" if days_remaining < 180 else "info"
        assert severity == "info"


class TestAlertGeneration:
    """Test alert structure generation from supersession data."""

    def test_alert_has_required_fields(self):
        alert = {
            "type": "standard_update",
            "standard": "ISO 10993-1",
            "old_version": "2018",
            "new_version": "2025",
            "transition_deadline": "2027-11-18",
            "days_remaining": 649,
            "severity": "info",
            "action_required": "Update biocompatibility testing plan",
        }
        assert alert["type"] == "standard_update"
        assert "standard" in alert
        assert "old_version" in alert
        assert "new_version" in alert
        assert "transition_deadline" in alert
        assert "severity" in alert
        assert "action_required" in alert

    def test_generate_alerts_from_cited_standards(self):
        cited = ["ISO 10993-1:2018", "ISO 14971:2019", "IEC 62304:2006"]
        alerts = []
        for std in cited:
            if std in SUPERSESSIONS:
                info = SUPERSESSIONS[std]
                alerts.append({
                    "type": "standard_update",
                    "standard": std.split(":")[0],
                    "old_version": std.split(":")[-1],
                    "new_version": info["new"].split(":")[-1],
                })
        assert len(alerts) == 1
        assert alerts[0]["standard"] == "ISO 10993-1"
        assert alerts[0]["old_version"] == "2018"
        assert alerts[0]["new_version"] == "2025"

    def test_no_alerts_for_current_standards(self):
        cited = ["ISO 14971:2019", "IEC 62304:2006", "ISO 13485:2016"]
        alerts = [std for std in cited if std in SUPERSESSIONS]
        assert len(alerts) == 0


class TestStandardsTrackingIntegrity:
    """Verify standards-tracking.md reference has supersession data."""

    def test_has_supersession_database_section(self, standards_tracking_content):
        assert "Supersession Database" in standards_tracking_content

    def test_has_last_verified_dates(self, standards_tracking_content):
        assert "Last Verified" in standards_tracking_content
        assert "2026-02-07" in standards_tracking_content

    def test_has_severity_levels(self, standards_tracking_content):
        assert "Severity Levels" in standards_tracking_content
        assert "critical" in standards_tracking_content.lower()
        assert "warning" in standards_tracking_content.lower()

    def test_supersession_entries_match_database(self, standards_tracking_content):
        # Verify the reference contains the key supersession entries
        assert "ISO 10993-1:2018" in standards_tracking_content
        assert "ISO 10993-1:2025" in standards_tracking_content
        assert "ISO 11137-1:2025" in standards_tracking_content
        assert "ISO 17665:2024" in standards_tracking_content


class TestStandardPatternExtraction:
    """Test extracting standard references from document text."""

    STD_PATTERN = re.compile(r"(ISO|IEC|ASTM|AAMI|UL)\s*[\d]+(?:-\d+)?(?::\d{4})?")

    def test_extract_iso_standard(self):
        text = "Testing per ISO 10993-1:2018 biocompatibility framework."
        matches = self.STD_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_extract_iec_standard(self):
        text = "Software lifecycle per IEC 62304:2006."
        matches = self.STD_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_extract_multiple_standards(self):
        text = "Per ISO 14971:2019 and IEC 60601-1:2005 and ISO 13485:2016."
        matches = self.STD_PATTERN.findall(text)
        assert len(matches) >= 3

    def test_full_standard_with_year_extraction(self):
        full_pattern = re.compile(r"((?:ISO|IEC|ASTM|AAMI|UL)\s*[\d]+(?:-\d+)?(?::\d{4})?)")
        text = "ISO 10993-1:2018 was superseded by ISO 10993-1:2025 in November."
        matches = full_pattern.findall(text)
        assert "ISO 10993-1:2018" in matches
        assert "ISO 10993-1:2025" in matches
