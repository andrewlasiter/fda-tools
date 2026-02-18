#!/usr/bin/env python3
"""
Test suite for PMA Section Extractor error handling and quality indicators.

Tests:
    - Proper error logging instead of silent exceptions
    - Extraction quality indicators (completeness_score, failed_sections, warnings)
    - Graceful degradation when sections fail
    - PDF extraction error handling
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set up path for importing
import sys

scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from pma_section_extractor import PMAExtractor  # type: ignore


@pytest.fixture
def extractor():
    """Create a PMAExtractor instance without data store."""
    return PMAExtractor(store=None)


@pytest.fixture
def sample_ssed_text() -> str:
    """Sample SSED text with multiple sections."""
    return """
I. GENERAL INFORMATION

This is a PMA for a medical device. The device name is Test Device.
The manufacturer is Test Company Inc. located at 123 Test Street.
This section contains general information about the device and application.
Additional details about the regulatory pathway and submission type.
The device has been under development for several years.
Clinical data support the safety and effectiveness.

II. INDICATIONS FOR USE

The device is indicated for use in treating patients with specific conditions.
It should be used by qualified healthcare professionals in clinical settings.
Contraindications include patients with certain allergies or conditions.
The device provides therapeutic benefits for target patient population.

III. DEVICE DESCRIPTION

The device consists of multiple components including sensor and processor.
Materials used include biocompatible polymers and titanium alloys.
Dimensions are 10cm x 5cm x 2cm with total weight of 50 grams.
Power source is rechargeable lithium-ion battery rated at 3.7V.
The device includes software version 2.1.3 for control functions.

VII. SUMMARY OF CLINICAL STUDIES

A pivotal clinical trial was conducted with 250 patients across 10 sites.
Primary endpoint was achieved with statistical significance (p < 0.001).
Secondary endpoints also showed positive results in all categories.
Safety profile was acceptable with no serious adverse events.
Long-term follow-up data will be collected for 5 years post-approval.

XI. BENEFIT-RISK ANALYSIS

The benefits of the device outweigh the potential risks based on clinical data.
Patients gain significant therapeutic benefit with minimal side effects.
Risk mitigation strategies include training and proper patient selection.
Overall benefit-risk determination is favorable for approval.

XIII. OVERALL CONCLUSIONS

Based on comprehensive evaluation of preclinical and clinical data.
The device is safe and effective for its intended use.
Manufacturing quality systems are adequate and compliant with regulations.
Labeling provides sufficient information for safe and effective use.
Approval is recommended with standard post-market surveillance.
"""


@pytest.fixture
def malformed_ssed_text() -> str:
    """SSED text with problematic sections."""
    return """
I. GENERAL INFORMATION
Short.

II. INDICATIONS FOR USE

This section has moderate content describing the indications.
Multiple paragraphs with clinical details and usage instructions.
Patient population and contraindications are well described.

CORRUPTED SECTION MARKER ###

VII. SUMMARY OF CLINICAL STUDIES

Clinical trial data showing efficacy and safety results.
"""


class TestErrorHandling:
    """Test proper error handling and logging."""

    def test_no_silent_exceptions_in_pdf_extraction(self, extractor, tmp_path):
        """Test that PDF extraction failures are logged, not silently ignored."""
        # Create a non-existent PDF path
        fake_pdf = tmp_path / "nonexistent.pdf"

        with patch("logging.Logger.error") as mock_error, \
             patch("logging.Logger.warning") as mock_warning:

            result = extractor.extract_from_pdf(str(fake_pdf))

            # Should have logged errors or warnings
            assert mock_error.called or mock_warning.called
            assert not result["success"]
            assert "extraction_warnings" in result["metadata"]

    def test_pdf_extraction_logs_page_failures(self, extractor, tmp_path):
        """Test that individual page extraction failures are logged."""
        # Mock pdfplumber to simulate page extraction failure
        mock_page = Mock()
        mock_page.extract_text.side_effect = Exception("Page corrupted")

        mock_pdf_context = MagicMock()
        mock_pdf_context.__enter__.return_value.pages = [mock_page]

        with patch("pdfplumber.open", return_value=mock_pdf_context), \
             patch("logging.Logger.warning") as mock_warning:

            fake_pdf = tmp_path / "test.pdf"
            fake_pdf.write_bytes(b"%PDF-1.4\n")

            _ = extractor._extract_text_from_pdf(str(fake_pdf))

            # Should log the page failure
            assert mock_warning.called
            assert len(extractor.extraction_warnings) > 0
            assert any("Failed to extract page" in w for w in extractor.extraction_warnings)

    def test_section_extraction_continues_on_failure(self, extractor, sample_ssed_text):
        """Test that extraction continues when one section fails."""
        # Use the fixture correctly
        text = sample_ssed_text

        # Mock section extraction to fail for one section
        original_extract = extractor._extract_sections

        def mock_extract(text, boundaries):
            # Inject a boundary that will cause an issue
            modified_boundaries = list(boundaries)
            if len(modified_boundaries) > 1:
                # Corrupt one boundary to test error handling
                bad_boundary = (
                    len(text) + 1000,  # Invalid position
                    "corrupted_section",
                    "BAD HEADER",
                    0.5
                )
                modified_boundaries.insert(1, bad_boundary)

            return original_extract(text, modified_boundaries)

        with patch.object(extractor, "_extract_sections", side_effect=mock_extract):
            result = extractor.extract_from_text(text)

            # Should still succeed with some sections
            # (Original implementation may not have this boundary injection,
            # so we test the actual behavior)
            assert result["success"]

    def test_extraction_logs_short_sections(self, extractor, malformed_ssed_text):
        """Test that very short sections are logged as warnings."""
        with patch("logging.Logger.warning") as mock_warning:
            _ = extractor.extract_from_text(malformed_ssed_text)

            # Should warn about short section
            assert mock_warning.called
            assert len(extractor.extraction_warnings) > 0

    def test_text_too_short_error(self, extractor):
        """Test error handling for text that's too short."""
        short_text = "Too short"

        result = extractor.extract_from_text(short_text)

        assert not result["success"]
        assert "error" in result
        assert "extraction_warnings" in result["metadata"]
        assert len(result["metadata"]["extraction_warnings"]) > 0


class TestQualityIndicators:
    """Test extraction quality indicators."""

    def test_completeness_score_present(self, extractor, sample_ssed_text):
        """Test that completeness_score is included in results."""
        result = extractor.extract_from_text(sample_ssed_text)

        assert "completeness_score" in result["metadata"]
        score = result["metadata"]["completeness_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_failed_sections_tracking(self, extractor, malformed_ssed_text):
        """Test that failed sections are tracked."""
        result = extractor.extract_from_text(malformed_ssed_text)

        assert "failed_sections" in result["metadata"]
        assert isinstance(result["metadata"]["failed_sections"], list)

    def test_extraction_warnings_tracking(self, extractor, sample_ssed_text):
        """Test that extraction warnings are tracked."""
        result = extractor.extract_from_text(sample_ssed_text)

        assert "extraction_warnings" in result["metadata"]
        assert isinstance(result["metadata"]["extraction_warnings"], list)

    def test_completeness_score_calculation(self, extractor):
        """Test completeness score calculation logic."""
        # Test with no sections (but no failed sections either, so gets 0.1 bonus)
        extractor.failed_sections = []
        result_empty = {"sections": {}, "metadata": {}}
        score_empty = extractor._calculate_completeness_score(result_empty)
        assert score_empty == 0.1  # Gets the "no failures" bonus

        # Test with all key sections
        sections_all_key = {
            "general_information": {"word_count": 100},
            "indications_for_use": {"word_count": 100},
            "device_description": {"word_count": 100},
            "clinical_studies": {"word_count": 100},
            "overall_conclusions": {"word_count": 100},
            "benefit_risk": {"word_count": 100},
        }
        result_key = {"sections": sections_all_key, "metadata": {}}
        score_key = extractor._calculate_completeness_score(result_key)
        assert score_key > 0.5  # Should be relatively high

        # Test with failed sections
        extractor.failed_sections = ["section1", "section2"]
        result_failed = {"sections": sections_all_key, "metadata": {}}
        score_failed = extractor._calculate_completeness_score(result_failed)
        # Should not get full bonus for no failures
        assert score_failed < 1.0

    def test_completeness_score_increases_with_sections(self, extractor):
        """Test that completeness score increases as more sections are found."""
        # Few sections
        extractor.failed_sections = []
        result_few = {
            "sections": {
                "general_information": {"word_count": 100},
                "indications_for_use": {"word_count": 100},
            },
            "metadata": {},
        }
        score_few = extractor._calculate_completeness_score(result_few)

        # Many sections
        result_many = {
            "sections": {
                "general_information": {"word_count": 100},
                "indications_for_use": {"word_count": 100},
                "device_description": {"word_count": 100},
                "clinical_studies": {"word_count": 100},
                "overall_conclusions": {"word_count": 100},
                "benefit_risk": {"word_count": 100},
                "preclinical_studies": {"word_count": 100},
                "manufacturing": {"word_count": 100},
            },
            "metadata": {},
        }
        score_many = extractor._calculate_completeness_score(result_many)

        assert score_many > score_few


class TestPDFExtractionResilience:
    """Test PDF extraction error handling."""

    def test_no_pdf_library_handling(self, extractor, tmp_path):
        """Test handling when no PDF library is available."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("builtins.__import__", side_effect=ImportError("No module")):
            result = extractor._extract_text_from_pdf(str(fake_pdf))

            assert result is None
            assert len(extractor.extraction_warnings) > 0
            assert any("No PDF library" in w for w in extractor.extraction_warnings)

    def test_pdfplumber_fallback_to_pypdf2(self, extractor, tmp_path):
        """Test fallback from pdfplumber to PyPDF2."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")

        mock_pypdf_page = Mock()
        mock_pypdf_page.extract_text.return_value = "Test content from PyPDF2"
        mock_pypdf_reader = Mock()
        mock_pypdf_reader.pages = [mock_pypdf_page]

        with patch("pdfplumber.open", side_effect=ImportError("Not installed")), \
             patch("PyPDF2.PdfReader", return_value=mock_pypdf_reader):

            result = extractor._extract_text_from_pdf(str(fake_pdf))

            assert result is not None
            assert "PyPDF2" in result

    def test_page_count_fallback(self, extractor, tmp_path):
        """Test page count fallback mechanism."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")

        mock_pypdf_reader = Mock()
        mock_pypdf_reader.pages = [Mock(), Mock(), Mock()]

        with patch("pdfplumber.open", side_effect=ImportError("Not installed")), \
             patch("PyPDF2.PdfReader", return_value=mock_pypdf_reader):

            count = extractor._get_page_count(str(fake_pdf))

            assert count == 3

    def test_page_count_failure_handling(self, extractor, tmp_path):
        """Test page count failure returns 0 with warnings."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("pdfplumber.open", side_effect=Exception("Corrupt PDF")), \
             patch("PyPDF2.PdfReader", side_effect=Exception("Also corrupt")):

            count = extractor._get_page_count(str(fake_pdf))

            assert count == 0
            assert len(extractor.extraction_warnings) > 0


class TestExtractionMetadata:
    """Test metadata and quality reporting."""

    def test_metadata_includes_all_quality_fields(self, extractor, sample_ssed_text):
        """Test that metadata includes all required quality fields."""
        result = extractor.extract_from_text(sample_ssed_text)

        metadata = result["metadata"]
        required_fields = [
            "total_sections_found",
            "total_possible_sections",
            "total_word_count",
            "char_count",
            "extraction_quality",
            "quality_score",
            "average_confidence",
            "missing_sections",
            "section_order",
            "completeness_score",
            "failed_sections",
            "extraction_warnings",
        ]

        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"

    def test_extraction_warnings_reset_between_runs(self, extractor, sample_ssed_text):
        """Test that warnings are reset between extraction runs."""
        # First extraction
        _ = extractor.extract_from_text(sample_ssed_text)

        # Add some artificial warnings
        extractor.extraction_warnings.append("Test warning")

        # Second extraction should reset
        result2 = extractor.extract_from_text(sample_ssed_text)
        warnings2 = result2["metadata"]["extraction_warnings"]

        # Should not contain the artificial warning
        assert "Test warning" not in warnings2

    def test_failed_sections_reset_between_runs(self, extractor, sample_ssed_text):
        """Test that failed sections are reset between extraction runs."""
        # First extraction
        _ = extractor.extract_from_text(sample_ssed_text)

        # Add artificial failed section
        extractor.failed_sections.append("artificial_section")

        # Second extraction should reset
        result2 = extractor.extract_from_text(sample_ssed_text)
        failed2 = result2["metadata"]["failed_sections"]

        # Should not contain the artificial failed section
        assert "artificial_section" not in failed2


class TestLoggingConfiguration:
    """Test logging behavior."""

    def test_extraction_logs_info_on_success(self, extractor, sample_ssed_text, caplog):
        """Test that successful extraction logs info message."""
        with caplog.at_level(logging.INFO):
            result = extractor.extract_from_text(sample_ssed_text)

        assert result["success"]
        # Should have logged extraction completion
        assert any("Extraction complete" in record.message for record in caplog.records)

    def test_extraction_logs_errors(self, extractor, caplog):
        """Test that errors are logged at appropriate level."""
        with caplog.at_level(logging.WARNING):
            _ = extractor.extract_from_text("x")  # Too short

        # Should have warning about short text
        assert any("too short" in record.message.lower() for record in caplog.records)

    def test_section_extraction_logs_debug_info(self, extractor, sample_ssed_text, caplog):
        """Test that section extraction logs debug information."""
        with caplog.at_level(logging.DEBUG):
            _ = extractor.extract_from_text(sample_ssed_text)

        # Should have debug logs for individual sections
        debug_logs = [r for r in caplog.records if r.levelname == "DEBUG"]
        assert len(debug_logs) > 0


class TestIntegrationScenarios:
    """Test realistic extraction scenarios."""

    def test_complete_ssed_extraction(self, extractor, sample_ssed_text):
        """Test extraction of a complete SSED document."""
        result = extractor.extract_from_text(sample_ssed_text)

        assert result["success"]
        assert len(result["sections"]) >= 4  # We have at least 4 sections
        assert result["metadata"]["completeness_score"] > 0.0
        assert result["metadata"]["quality_score"] > 0

    def test_partial_ssed_extraction(self, extractor):
        """Test extraction when only some sections are present."""
        partial_text = """
        I. GENERAL INFORMATION

        This device is for testing purposes only.
        Contains minimal information for partial extraction test.
        Manufacturer details and other required information.
        """

        result = extractor.extract_from_text(partial_text)

        assert result["success"]
        assert len(result["sections"]) >= 1
        assert "general_information" in result["sections"]
        # Completeness should be low
        assert result["metadata"]["completeness_score"] < 0.5

    def test_extraction_with_warnings_still_succeeds(self, extractor, malformed_ssed_text):
        """Test that extraction with warnings can still succeed."""
        result = extractor.extract_from_text(malformed_ssed_text)

        assert result["success"]
        assert len(result["metadata"]["extraction_warnings"]) > 0
        # Should still extract some valid sections
        assert len(result["sections"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
