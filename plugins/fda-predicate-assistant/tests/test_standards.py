"""Tests for standards database lookup and supersession detection.

Validates that the standards-tracking.md reference is well-structured
and that supersession detection logic works correctly.
"""

import os
import re
import pytest


@pytest.fixture
def standards_content():
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


@pytest.fixture
def standards_db_content():
    """Load the standards-database.md reference."""
    ref_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "skills",
        "fda-510k-knowledge",
        "references",
        "standards-database.md",
    )
    with open(ref_path) as f:
        return f.read()


class TestStandardsTrackingReference:
    """Verify the standards-tracking.md reference structure."""

    def test_has_quality_management_section(self, standards_content):
        assert "Quality Management" in standards_content

    def test_has_biocompatibility_section(self, standards_content):
        assert "Biocompatibility" in standards_content

    def test_has_sterilization_section(self, standards_content):
        assert "Sterilization" in standards_content

    def test_has_electrical_safety_section(self, standards_content):
        assert "Electrical Safety" in standards_content

    def test_has_software_section(self, standards_content):
        assert "Software" in standards_content

    def test_has_cybersecurity_section(self, standards_content):
        assert "Cybersecurity" in standards_content

    def test_iso_13485_present(self, standards_content):
        assert "ISO 13485" in standards_content

    def test_iso_14971_present(self, standards_content):
        assert "ISO 14971" in standards_content

    def test_iso_10993_1_present(self, standards_content):
        assert "ISO 10993-1" in standards_content

    def test_iec_60601_present(self, standards_content):
        assert "IEC 60601" in standards_content

    def test_iec_62304_present(self, standards_content):
        assert "IEC 62304" in standards_content


class TestSupersessionData:
    """Verify supersession tracking data is accurate."""

    def test_iso_10993_1_supersession(self, standards_content):
        # ISO 10993-1:2018 -> 2025
        assert "ISO 10993-1:2025" in standards_content
        assert "superseded" in standards_content.lower()

    def test_iso_11137_supersession(self, standards_content):
        # ISO 11137-1:2006 -> 2025
        assert "ISO 11137-1:2025" in standards_content

    def test_iso_17665_supersession(self, standards_content):
        # ISO 17665-1:2006 -> 2024
        assert "ISO 17665" in standards_content
        assert "2024" in standards_content


class TestStandardsDatabaseReference:
    """Verify the standards-database.md reference structure."""

    def test_has_overview(self, standards_db_content):
        assert "Overview" in standards_db_content or "RCSD" in standards_db_content

    def test_has_recognition_status_info(self, standards_db_content):
        assert "Recognized" in standards_db_content
        assert "Withdrawn" in standards_db_content

    def test_has_transition_period_info(self, standards_db_content):
        assert "transition" in standards_db_content.lower()

    def test_has_query_patterns(self, standards_db_content):
        assert "Query Patterns" in standards_db_content or "query" in standards_db_content.lower()

    def test_has_supersession_table(self, standards_db_content):
        assert "Supersession" in standards_db_content

    def test_has_integration_points(self, standards_db_content):
        assert "/fda:standards" in standards_db_content


class TestStandardNumberParsing:
    """Test standard number format recognition."""

    ISO_PATTERN = re.compile(r"ISO\s*\d+(?:-\d+)?(?::\d{4})?")
    IEC_PATTERN = re.compile(r"IEC\s*\d+(?:-\d+(?:-\d+)?)?(?::\d{4})?")
    ASTM_PATTERN = re.compile(r"ASTM\s*[A-Z]\d+")

    def test_iso_standard_format(self):
        assert self.ISO_PATTERN.match("ISO 10993-1:2025")
        assert self.ISO_PATTERN.match("ISO 13485:2016")
        assert self.ISO_PATTERN.match("ISO 14971")

    def test_iec_standard_format(self):
        assert self.IEC_PATTERN.match("IEC 60601-1:2005")
        assert self.IEC_PATTERN.match("IEC 62304")
        assert self.IEC_PATTERN.match("IEC 60601-1-2:2014")

    def test_astm_standard_format(self):
        assert self.ASTM_PATTERN.match("ASTM F1980")
        assert self.ASTM_PATTERN.match("ASTM F2077")

    def test_extract_standards_from_text(self):
        text = "Testing per ISO 10993-5:2009, IEC 60601-1:2005, and ASTM F1980."
        iso_matches = self.ISO_PATTERN.findall(text)
        iec_matches = self.IEC_PATTERN.findall(text)
        astm_matches = self.ASTM_PATTERN.findall(text)
        assert len(iso_matches) == 1
        assert len(iec_matches) == 1
        assert len(astm_matches) == 1
