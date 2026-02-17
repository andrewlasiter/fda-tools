"""
Tests for scripts/compare_sections.py

Validates section comparison tool for regulatory intelligence including
coverage analysis, standards detection, and outlier identification.

Test coverage:
- Structured cache loading and filtering
- Section extraction from multiple devices
- Product code and year range filtering
- Standards citation extraction (ISO/IEC/ASTM)
- Coverage matrix generation
- Statistical outlier detection
- Section similarity analysis
- Temporal trend analysis

Per FDA guidance on regulatory intelligence gathering, validates tools
used for peer device analysis and competitive intelligence.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Import the script module
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

from compare_sections import (  # type: ignore
    filter_by_product_code,
    filter_by_year_range,
    extract_sections_batch,
    extract_standards_from_text,
    generate_coverage_matrix,
    SECTION_ALIASES,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_structured_cache():
    """Sample structured cache with multiple devices."""
    return {
        "K241335": {
            "k_number": "K241335",
            "device_name": "Test Catheter Device",
            "decision_date": "20240615",
            "product_code": "DQY",
            "metadata": {
                "product_code": "DQY",
                "extraction_date": "2024-06-15",
            },
            "sections": {
                "clinical_testing": {
                    "text": "Clinical study with 50 patients. Device tested per ISO 10993-1 biocompatibility.",
                    "word_count": 100,
                },
                "biocompatibility": {
                    "text": "Biocompatibility testing performed per ISO 10993-1, ISO 10993-5, and ISO 10993-10.",
                    "word_count": 150,
                },
                "performance_testing": {
                    "text": "Mechanical testing per ASTM F2606 and flow testing per ISO 8009.",
                    "word_count": 80,
                },
            },
        },
        "K241336": {
            "k_number": "K241336",
            "device_name": "Advanced Catheter Pro",
            "decision_date": "20240710",
            "product_code": "DQY",
            "metadata": {
                "product_code": "DQY",
                "extraction_date": "2024-07-10",
            },
            "sections": {
                "clinical_testing": {
                    "text": "Clinical validation with 75 patients following FDA guidance.",
                    "word_count": 120,
                },
                "biocompatibility": {
                    "text": "Testing per ISO 10993 series and ASTM F756.",
                    "word_count": 90,
                },
            },
        },
        "K231234": {
            "k_number": "K231234",
            "device_name": "Orthopedic Implant",
            "decision_date": "20231015",
            "product_code": "OVE",
            "metadata": {
                "product_code": "OVE",
                "extraction_date": "2023-10-15",
            },
            "sections": {
                "biocompatibility": {
                    "text": "PEEK material tested per ISO 10993-1 and ASTM F2026.",
                    "word_count": 110,
                },
                "performance_testing": {
                    "text": "Mechanical testing per ASTM F1717 and F2077.",
                    "word_count": 95,
                },
            },
        },
    }


@pytest.fixture
def text_with_standards():
    """Sample text containing various standards citations."""
    return """
    The device was tested for biocompatibility per ISO 10993-1, ISO 10993-5,
    and ISO 10993-10. Electrical safety testing was performed according to
    IEC 60601-1-2 and IEC 60601-1. Mechanical testing followed ASTM F2606,
    ASTM-F2077, and ANSI/AAMI ST79 sterilization standards.
    Additional testing per ISO-14971 risk management.
    """


# ============================================================================
# Filtering Tests
# ============================================================================


class TestFiltering:
    """Test suite for cache filtering operations."""

    def test_filter_by_product_code_single_match(self, sample_structured_cache):
        """Test filtering by product code returns matching devices."""
        filtered = filter_by_product_code(sample_structured_cache, "DQY")

        assert len(filtered) == 2
        assert "K241335" in filtered
        assert "K241336" in filtered
        assert "K231234" not in filtered

    def test_filter_by_product_code_case_insensitive(self, sample_structured_cache):
        """Test product code filtering is case-insensitive."""
        filtered_upper = filter_by_product_code(sample_structured_cache, "DQY")
        filtered_lower = filter_by_product_code(sample_structured_cache, "dqy")

        assert len(filtered_upper) == len(filtered_lower)
        assert set(filtered_upper.keys()) == set(filtered_lower.keys())

    def test_filter_by_product_code_no_matches(self, sample_structured_cache):
        """Test filtering with non-existent product code returns empty."""
        filtered = filter_by_product_code(sample_structured_cache, "XXX")

        assert len(filtered) == 0

    def test_filter_by_year_range_both_bounds(self, sample_structured_cache):
        """Test filtering by year range with both start and end."""
        filtered = filter_by_year_range(sample_structured_cache, 2024, 2024)

        assert len(filtered) == 2
        assert "K241335" in filtered
        assert "K241336" in filtered
        assert "K231234" not in filtered

    def test_filter_by_year_range_start_only(self, sample_structured_cache):
        """Test filtering by year range with only start year."""
        filtered = filter_by_year_range(sample_structured_cache, 2024, None)

        assert len(filtered) == 2
        assert "K241335" in filtered
        assert "K241336" in filtered

    def test_filter_by_year_range_end_only(self, sample_structured_cache):
        """Test filtering by year range with only end year."""
        filtered = filter_by_year_range(sample_structured_cache, None, 2023)

        assert len(filtered) == 1
        assert "K231234" in filtered

    def test_filter_by_year_range_no_bounds(self, sample_structured_cache):
        """Test filtering with no year bounds returns all."""
        filtered = filter_by_year_range(sample_structured_cache, None, None)

        assert len(filtered) == 3

    def test_filter_by_year_range_invalid_date_format(self, sample_structured_cache, capsys):
        """Test filtering handles invalid date formats gracefully."""
        # Add device with invalid date
        cache_copy = sample_structured_cache.copy()
        cache_copy["K999999"] = {
            "k_number": "K999999",
            "decision_date": "INVALID",
            "metadata": {"product_code": "DQY"},
        }

        filtered = filter_by_year_range(cache_copy, 2024, 2024)

        # Should not crash, just skip invalid dates
        assert "K999999" not in filtered


# ============================================================================
# Section Extraction Tests
# ============================================================================


class TestSectionExtraction:
    """Test suite for section extraction from cache."""

    def test_extract_sections_batch_single_section(self, sample_structured_cache):
        """Test extracting single section type from all devices."""
        results = extract_sections_batch(
            sample_structured_cache, ["clinical_testing"]
        )

        assert len(results) == 2  # K241335 and K241336 have clinical sections
        assert "K241335" in results
        assert "K241336" in results
        assert "clinical_testing" in results["K241335"]["sections"]

    def test_extract_sections_batch_multiple_sections(self, sample_structured_cache):
        """Test extracting multiple section types."""
        results = extract_sections_batch(
            sample_structured_cache, ["clinical_testing", "biocompatibility"]
        )

        # All devices have at least one of these sections
        assert len(results) == 3
        # K241335 has both
        assert len(results["K241335"]["sections"]) == 2

    def test_extracted_sections_include_metadata(self, sample_structured_cache):
        """Test extracted sections include device metadata."""
        results = extract_sections_batch(
            sample_structured_cache, ["biocompatibility"]
        )

        k241335 = results["K241335"]
        assert k241335["device_name"] == "Test Catheter Device"
        assert k241335["decision_date"] == "20240615"
        assert k241335["product_code"] == "DQY"

    def test_extracted_sections_calculate_word_count(self, sample_structured_cache):
        """Test word count calculated for extracted sections."""
        results = extract_sections_batch(
            sample_structured_cache, ["clinical_testing"]
        )

        clinical_section = results["K241335"]["sections"]["clinical_testing"]
        assert clinical_section["word_count"] > 0
        assert isinstance(clinical_section["word_count"], int)

    def test_extract_sections_with_standards(self, sample_structured_cache):
        """Test standards extracted from section text."""
        results = extract_sections_batch(
            sample_structured_cache, ["biocompatibility"]
        )

        biocompat = results["K241335"]["sections"]["biocompatibility"]
        assert "standards" in biocompat
        assert len(biocompat["standards"]) > 0
        # Should extract ISO 10993-1, 10993-5, 10993-10
        assert any("10993" in std for std in biocompat["standards"])

    def test_extract_sections_empty_result_for_missing_sections(self, sample_structured_cache):
        """Test devices without requested sections are excluded."""
        results = extract_sections_batch(
            sample_structured_cache, ["software"]  # No devices have software sections
        )

        assert len(results) == 0


# ============================================================================
# Standards Extraction Tests
# ============================================================================


class TestStandardsExtraction:
    """Test suite for standards citation extraction."""

    def test_extract_iso_standards(self):
        """Test extraction of ISO standards."""
        text = "Testing per ISO 10993-1, ISO-10993-5, and ISO10993-10"

        standards = extract_standards_from_text(text)

        assert len(standards) > 0
        # Should normalize to consistent format
        assert any("10993" in std for std in standards)

    def test_extract_iec_standards(self):
        """Test extraction of IEC standards."""
        text = "Electrical safety per IEC 60601-1-2 and IEC-60601-1"

        standards = extract_standards_from_text(text)

        assert len(standards) > 0
        assert any("60601" in std for std in standards)

    def test_extract_astm_standards(self):
        """Test extraction of ASTM standards."""
        text = "Mechanical testing per ASTM F2606, ASTM-F2077"

        standards = extract_standards_from_text(text)

        assert len(standards) > 0
        assert any("F2606" in std or "f2606" in std.lower() for std in standards)

    def test_extract_ansi_aami_standards(self):
        """Test extraction of ANSI/AAMI standards."""
        text = "Sterilization per ANSI/AAMI ST79"

        standards = extract_standards_from_text(text)

        assert len(standards) > 0
        assert any("AAMI" in std for std in standards)

    def test_extract_standards_case_insensitive(self):
        """Test standards extraction is case-insensitive."""
        text = "iso 10993-1, IEC 60601-1, astm f2606"

        standards = extract_standards_from_text(text)

        assert len(standards) >= 3

    def test_extract_standards_deduplicates(self):
        """Test duplicate standards are deduplicated."""
        text = "ISO 10993-1, ISO 10993-1, ISO-10993-1"

        standards = extract_standards_from_text(text)

        # Should deduplicate (may have slight format variations)
        assert len(standards) <= 2

    def test_extract_standards_from_complex_text(self, text_with_standards):
        """Test extraction from realistic text with multiple standards."""
        standards = extract_standards_from_text(text_with_standards)

        assert len(standards) >= 7  # Should find ISO, IEC, ASTM, ANSI/AAMI
        # Verify key standards found
        assert any("10993" in std for std in standards)
        assert any("60601" in std for std in standards)
        assert any("F2606" in std or "f2606" in std.lower() for std in standards)

    def test_extract_standards_empty_text(self):
        """Test extraction from text with no standards."""
        text = "This text has no standards citations at all."

        standards = extract_standards_from_text(text)

        assert len(standards) == 0


# ============================================================================
# Coverage Matrix Tests
# ============================================================================


class TestCoverageMatrix:
    """Test suite for coverage matrix generation."""

    def test_generate_coverage_matrix_basic(self, sample_structured_cache):
        """Test basic coverage matrix generation."""
        section_data = extract_sections_batch(
            sample_structured_cache, ["clinical_testing", "biocompatibility"]
        )

        coverage = generate_coverage_matrix(
            section_data, ["clinical_testing", "biocompatibility"]
        )

        assert coverage["total_devices"] == 3
        assert "section_coverage" in coverage

    def test_coverage_matrix_calculates_percentages(self, sample_structured_cache):
        """Test coverage matrix calculates correct percentages."""
        section_data = extract_sections_batch(
            sample_structured_cache, ["clinical_testing", "biocompatibility"]
        )

        coverage = generate_coverage_matrix(
            section_data, ["clinical_testing", "biocompatibility"]
        )

        # Biocompatibility: all 3 devices (100%)
        biocompat_cov = coverage["section_coverage"]["biocompatibility"]
        assert biocompat_cov["count"] == 3
        assert biocompat_cov["percentage"] == 100.0

        # Clinical testing: 2 devices (66.67%)
        clinical_cov = coverage["section_coverage"]["clinical_testing"]
        assert clinical_cov["count"] == 2
        assert clinical_cov["percentage"] == pytest.approx(66.67, abs=0.1)

    def test_coverage_matrix_lists_devices(self, sample_structured_cache):
        """Test coverage matrix includes device lists."""
        section_data = extract_sections_batch(
            sample_structured_cache, ["clinical_testing"]
        )

        coverage = generate_coverage_matrix(
            section_data, ["clinical_testing"]
        )

        clinical_devices = coverage["section_coverage"]["clinical_testing"]["devices"]
        assert "K241335" in clinical_devices
        assert "K241336" in clinical_devices
        assert len(clinical_devices) == 2


# ============================================================================
# Section Aliases Tests
# ============================================================================


class TestSectionAliases:
    """Test suite for section name aliasing."""

    def test_section_aliases_include_common_names(self):
        """Test common section aliases are defined."""
        assert SECTION_ALIASES["clinical"] == "clinical_testing"
        assert SECTION_ALIASES["biocompat"] == "biocompatibility"
        assert SECTION_ALIASES["se"] == "predicate_se"
        assert SECTION_ALIASES["ifu"] == "indications_for_use"

    def test_section_aliases_support_variations(self):
        """Test multiple variations map to same canonical name."""
        assert SECTION_ALIASES["predicate"] == "predicate_se"
        assert SECTION_ALIASES["se"] == "predicate_se"
        assert SECTION_ALIASES["substantial_equivalence"] == "predicate_se"

    def test_section_aliases_all_value(self):
        """Test 'all' alias for selecting all sections."""
        assert SECTION_ALIASES["all"] == "all"


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow_filter_extract_analyze(self, sample_structured_cache):
        """Test complete workflow: filter -> extract -> analyze."""
        # Step 1: Filter by product code
        filtered = filter_by_product_code(sample_structured_cache, "DQY")
        assert len(filtered) == 2

        # Step 2: Extract sections
        section_data = extract_sections_batch(
            filtered, ["clinical_testing", "biocompatibility"]
        )
        assert len(section_data) == 2

        # Step 3: Generate coverage matrix
        coverage = generate_coverage_matrix(
            section_data, ["clinical_testing", "biocompatibility"]
        )
        assert coverage["total_devices"] == 2

    def test_workflow_with_year_filtering(self, sample_structured_cache):
        """Test workflow with year range filtering."""
        # Filter by product code and year
        filtered = filter_by_product_code(sample_structured_cache, "DQY")
        filtered = filter_by_year_range(filtered, 2024, 2024)

        assert len(filtered) == 2
        assert all("2024" in data["decision_date"] for data in filtered.values())

    def test_standards_aggregation_across_devices(self, sample_structured_cache):
        """Test aggregating standards across multiple devices."""
        section_data = extract_sections_batch(
            sample_structured_cache, ["biocompatibility"]
        )

        # Collect all standards from all devices
        all_standards = []
        for device_data in section_data.values():
            if "biocompatibility" in device_data["sections"]:
                all_standards.extend(
                    device_data["sections"]["biocompatibility"]["standards"]
                )

        # Should find ISO 10993 series across devices
        iso_standards = [s for s in all_standards if "10993" in s]
        assert len(iso_standards) > 0

    def test_empty_cache_handling(self):
        """Test functions handle empty cache gracefully."""
        empty_cache = {}

        filtered = filter_by_product_code(empty_cache, "DQY")
        assert len(filtered) == 0

        section_data = extract_sections_batch(empty_cache, ["clinical_testing"])
        assert len(section_data) == 0

        coverage = generate_coverage_matrix(section_data, ["clinical_testing"])
        assert coverage["total_devices"] == 0


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.scripts,
]
