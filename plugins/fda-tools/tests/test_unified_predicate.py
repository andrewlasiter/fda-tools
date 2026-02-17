"""
Tests for scripts/unified_predicate.py

Validates unified predicate analyzer for cross-pathway (510k/PMA) device
comparison, suitability assessment, and data normalization.

Test coverage:
- Device type detection (K/P/DEN/N numbers)
- Unified data retrieval and normalization
- Cross-pathway device comparison
- Suitability scoring and assessment
- Batch operations
- Text similarity utilities
- PMA SE table data extraction
- Error handling for invalid device numbers

Per FDA guidance on predicate selection, validates tools used for
substantial equivalence analysis.
"""

import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

import pytest

# Import the script module
# Package imports configured in conftest.py and pytest.ini

from scripts.unified_predicate import (
    UnifiedPredicateAnalyzer,
    _tokenize,
    _word_overlap,
    _cosine_similarity,
    DEVICE_PATTERNS,
    SUITABILITY_WEIGHTS,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def mock_510k_data():
    """Sample 510(k) data from FDA API."""
    return {
        "k_number": "K241335",
        "device_name": "Test Catheter Device",
        "applicant": "Test Medical Inc",
        "product_code": "DQY",
        "decision_date": "20240615",
        "clearance_type": "Traditional",
        "review_panel": "CV",
        "regulation_number": "870.1210",
        "statement_or_summary": "Indicated for temporary vascular access in patients requiring hemodynamic monitoring",
    }


@pytest.fixture
def mock_pma_data():
    """Sample PMA data from FDA API."""
    return {
        "pma_number": "P170019",
        "device_name": "Test PMA Cardiac Device",
        "trade_name": "CardioTech Pro",
        "applicant": "Advanced Medical Corp",
        "product_code": "NMH",
        "decision_date": "20170501",
        "advisory_committee": "CV",
        "advisory_committee_description": "Cardiovascular",
        "regulation_number": "870.3610",
        "expedited_review_flag": "N",
    }


@pytest.fixture
def mock_pma_sections():
    """Sample PMA SSED extracted sections."""
    return {
        "sections": {
            "indications_for_use": {
                "content": "Indicated for treatment of advanced heart failure in patients with reduced ejection fraction",
                "word_count": 150,
            },
            "device_description": {
                "content": "A fully implantable cardiac assist device consisting of titanium pump and control module",
                "word_count": 200,
            },
            "clinical_studies": {
                "content": "Multi-center randomized clinical trial with 300 patients enrolled across 25 sites",
                "word_count": 500,
            },
        },
        "metadata": {"quality_score": 85},
    }


@pytest.fixture
def mock_fda_client():
    """Mock FDAClient with controlled responses."""
    client = Mock()
    client.get_510k = Mock()
    client.get_pma = Mock()
    client.validate_device = Mock()
    return client


@pytest.fixture
def mock_pma_store():
    """Mock PMADataStore with controlled responses."""
    store = Mock()
    store.get_pma_data = Mock()
    store.get_extracted_sections = Mock()
    store.get_supplements = Mock()
    return store


# ============================================================================
# Device Type Detection Tests
# ============================================================================


class TestDeviceTypeDetection:
    """Test suite for device number type detection."""

    def test_detect_510k_number(self):
        """Test 510(k) K-number detection."""
        assert UnifiedPredicateAnalyzer.detect_device_type("K241335") == "510k"
        assert UnifiedPredicateAnalyzer.detect_device_type("k241335") == "510k"
        assert UnifiedPredicateAnalyzer.detect_device_type("K123456") == "510k"

    def test_detect_pma_number(self):
        """Test PMA P-number detection."""
        assert UnifiedPredicateAnalyzer.detect_device_type("P170019") == "pma"
        assert UnifiedPredicateAnalyzer.detect_device_type("p170019") == "pma"
        assert UnifiedPredicateAnalyzer.detect_device_type("P170019S001") == "pma"

    def test_detect_de_novo_number(self):
        """Test De Novo DEN-number detection."""
        # DEN numbers are 7 digits, but pattern in unified_predicate only checks for 6+
        assert UnifiedPredicateAnalyzer.detect_device_type("DEN1700577") == "de_novo"
        assert UnifiedPredicateAnalyzer.detect_device_type("den1700577") == "de_novo"

    def test_detect_pre_amendment_number(self):
        """Test Pre-Amendment N-number detection."""
        assert UnifiedPredicateAnalyzer.detect_device_type("N12345") == "pre_amendment"
        assert UnifiedPredicateAnalyzer.detect_device_type("n87654") == "pre_amendment"

    def test_detect_unknown_format(self):
        """Test unknown format returns 'unknown'."""
        assert UnifiedPredicateAnalyzer.detect_device_type("INVALID123") == "unknown"
        assert UnifiedPredicateAnalyzer.detect_device_type("123456") == "unknown"
        assert UnifiedPredicateAnalyzer.detect_device_type("") == "unknown"

    def test_is_pma_number_validation(self):
        """Test PMA number validation helper."""
        assert UnifiedPredicateAnalyzer.is_pma_number("P170019") is True
        assert UnifiedPredicateAnalyzer.is_pma_number("K241335") is False
        assert UnifiedPredicateAnalyzer.is_pma_number("DEN170057") is False

    def test_is_510k_number_validation(self):
        """Test 510(k) number validation helper."""
        assert UnifiedPredicateAnalyzer.is_510k_number("K241335") is True
        assert UnifiedPredicateAnalyzer.is_510k_number("P170019") is False
        assert UnifiedPredicateAnalyzer.is_510k_number("DEN170057") is False

    def test_classify_device_list(self):
        """Test batch device classification."""
        devices = ["K241335", "P170019", "DEN1700577", "K241336", "INVALID"]

        classified = UnifiedPredicateAnalyzer.classify_device_list(devices)

        assert "K241335" in classified["510k"]
        assert "K241336" in classified["510k"]
        assert "P170019" in classified["pma"]
        assert "DEN1700577" in classified.get("de_novo", [])
        assert "INVALID" in classified["unknown"]


# ============================================================================
# 510(k) Analysis Tests
# ============================================================================


class TestAnalyze510k:
    """Test suite for 510(k) device analysis."""

    def test_analyze_510k_success(self, mock_fda_client, mock_510k_data):
        """Test successful 510(k) analysis."""
        mock_fda_client.get_510k.return_value = {
            "results": [mock_510k_data],
            "meta": {"results": {"total": 1}},
        }

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        result = analyzer.analyze_predicate("K241335")

        assert result["valid"] is True
        assert result["device_type"] == "510k"
        assert result["device_number"] == "K241335"
        assert result["device_name"] == "Test Catheter Device"
        assert result["applicant"] == "Test Medical Inc"
        assert result["product_code"] == "DQY"
        assert result["regulatory_status"] == "cleared"

    def test_analyze_510k_not_found(self, mock_fda_client):
        """Test 510(k) analysis for non-existent device."""
        mock_fda_client.get_510k.return_value = {
            "results": [],
            "meta": {"results": {"total": 0}},
        }

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        result = analyzer.analyze_predicate("K999999")

        assert result["valid"] is False
        assert result["device_type"] == "510k"
        assert "error" in result

    def test_analyze_510k_degraded_mode(self, mock_fda_client):
        """Test 510(k) analysis handles API degradation."""
        mock_fda_client.get_510k.return_value = {
            "degraded": True,
            "error": "API unavailable",
        }

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        result = analyzer.analyze_predicate("K241335")

        assert result["valid"] is False
        assert "error" in result


# ============================================================================
# PMA Analysis Tests
# ============================================================================


class TestAnalyzePMA:
    """Test suite for PMA device analysis."""

    def test_analyze_pma_success(self, mock_fda_client, mock_pma_store, mock_pma_data, mock_pma_sections):
        """Test successful PMA analysis with SSED sections."""
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = mock_pma_sections
        mock_pma_store.get_supplements.return_value = [
            {"supplement_number": "S001", "supplement_type": "Manufacturing"},
            {"supplement_number": "S002", "supplement_type": "Labeling"},
        ]

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        result = analyzer.analyze_predicate("P170019")

        assert result["valid"] is True
        assert result["device_type"] == "pma"
        assert result["device_number"] == "P170019"
        assert result["device_name"] == "Test PMA Cardiac Device"
        assert result["regulatory_status"] == "approved"
        assert result["supplement_count"] == 2
        assert result["has_clinical_data"] is True
        assert result["has_ssed_sections"] is True

    def test_analyze_pma_without_sections(self, mock_fda_client, mock_pma_store, mock_pma_data):
        """Test PMA analysis without extracted SSED sections."""
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = None
        mock_pma_store.get_supplements.return_value = []

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        result = analyzer.analyze_predicate("P170019")

        assert result["valid"] is True
        assert result["has_ssed_sections"] is False
        assert result["has_clinical_data"] is False
        assert result["supplement_count"] == 0
        assert result["clinical_data_source"] == "api_metadata"

    def test_analyze_pma_error(self, mock_fda_client, mock_pma_store):
        """Test PMA analysis handles errors."""
        mock_pma_store.get_pma_data.return_value = {
            "error": "PMA not found",
        }

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        result = analyzer.analyze_predicate("P999999")

        assert result["valid"] is False
        assert "error" in result


# ============================================================================
# Cross-Pathway Comparison Tests
# ============================================================================


class TestCrossPathwayComparison:
    """Test suite for device comparison across pathways."""

    def test_compare_510k_to_510k(self, mock_fda_client, mock_510k_data):
        """Test comparing two 510(k) devices."""
        mock_fda_client.get_510k.side_effect = [
            {"results": [mock_510k_data], "meta": {}},
            {
                "results": [{
                    **mock_510k_data,
                    "k_number": "K241336",
                    "device_name": "Similar Catheter",
                }],
                "meta": {},
            },
        ]

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        result = analyzer.compare_devices("K241335", "K241336")

        assert "error" not in result
        assert result["comparison_type"] == "510k_vs_510k"
        assert result["device1"]["number"] == "K241335"
        assert result["device2"]["number"] == "K241336"
        assert "overall_similarity" in result
        assert "dimensions" in result

    def test_compare_510k_to_pma(self, mock_fda_client, mock_pma_store, mock_510k_data, mock_pma_data):
        """Test cross-pathway comparison (510k vs PMA)."""
        mock_fda_client.get_510k.return_value = {
            "results": [mock_510k_data],
            "meta": {},
        }
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = None
        mock_pma_store.get_supplements.return_value = []

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        result = analyzer.compare_devices("K241335", "P170019")

        assert result["comparison_type"] == "510k_vs_pma"
        assert result["data_quality"]["cross_pathway"] is True
        assert result["device1"]["type"] == "510k"
        assert result["device2"]["type"] == "pma"

    def test_compare_same_product_code_high_similarity(self, mock_fda_client, mock_510k_data):
        """Test devices with same product code have high similarity."""
        mock_fda_client.get_510k.side_effect = [
            {"results": [mock_510k_data], "meta": {}},
            {
                "results": [{
                    **mock_510k_data,
                    "k_number": "K241336",
                }],
                "meta": {},
            },
        ]

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        result = analyzer.compare_devices("K241335", "K241336")

        # Same product code should boost device_specs similarity
        assert result["dimensions"]["device_specs"]["score"] >= 40

    def test_comparison_key_differences_identified(self, mock_fda_client, mock_510k_data):
        """Test key differences identified in comparison."""
        mock_fda_client.get_510k.side_effect = [
            {"results": [mock_510k_data], "meta": {}},
            {
                "results": [{
                    **mock_510k_data,
                    "k_number": "K241336",
                    "product_code": "MAX",  # Different product code
                }],
                "meta": {},
            },
        ]

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        result = analyzer.compare_devices("K241335", "K241336")

        # Should identify product code difference
        if result["key_differences"]:
            assert any(
                "device_specs" in diff["dimension"]
                for diff in result["key_differences"]
            )


# ============================================================================
# Suitability Assessment Tests
# ============================================================================


class TestSuitabilityAssessment:
    """Test suite for predicate suitability assessment."""

    def test_assess_suitability_high_score(self, mock_fda_client, mock_510k_data):
        """Test suitability assessment with high similarity."""
        mock_fda_client.get_510k.return_value = {
            "results": [mock_510k_data],
            "meta": {},
        }

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        subject = {
            "product_code": "DQY",  # Same as candidate
            "intended_use": "Indicated for temporary vascular access in patients",  # Similar text
            "device_description": "Test Catheter Device for vascular access",  # Similar
        }

        result = analyzer.assess_suitability("K241335", subject)

        assert result["suitable"] is True
        assert result["score"] >= 50  # Should score well due to matching product code
        assert result["recommendation"]
        assert len(result["factors"]) > 0

    def test_assess_suitability_product_code_mismatch(self, mock_fda_client, mock_510k_data):
        """Test suitability with different product codes."""
        mock_fda_client.get_510k.return_value = {
            "results": [mock_510k_data],
            "meta": {},
        }

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        subject = {
            "product_code": "MAX",  # Different from DQY
            "intended_use": "Different indication",
            "device_description": "Different device",
        }

        result = analyzer.assess_suitability("K241335", subject)

        # Should have lower score due to product code mismatch
        assert result["score"] < SUITABILITY_WEIGHTS["product_code_match"]

    def test_assess_suitability_pma_predicate(self, mock_fda_client, mock_pma_store, mock_pma_data):
        """Test suitability assessment with PMA as predicate."""
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = None
        mock_pma_store.get_supplements.return_value = []

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        subject = {
            "product_code": "NMH",
            "intended_use": "Treatment of heart failure",
            "device_description": "Cardiac assist device",
        }

        result = analyzer.assess_suitability("P170019", subject)

        assert result["candidate_type"] == "pma"
        assert len(result["pathway_notes"]) > 0
        # Should have note about PMA predicate considerations
        assert any("PMA" in note for note in result["pathway_notes"])

    def test_assess_suitability_invalid_candidate(self, mock_fda_client):
        """Test suitability assessment with invalid device number."""
        mock_fda_client.get_510k.return_value = {
            "results": [],
            "meta": {},
        }

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        subject = {"product_code": "DQY", "intended_use": "Test"}

        result = analyzer.assess_suitability("K999999", subject)

        assert result["suitable"] is False
        assert result["score"] == 0
        assert "error" in result


# ============================================================================
# Text Similarity Tests
# ============================================================================


class TestTextSimilarity:
    """Test suite for text similarity utilities."""

    def test_tokenize_basic_text(self):
        """Test basic text tokenization."""
        text = "This is a test device for vascular access"

        tokens = _tokenize(text)

        assert "this" in tokens
        assert "test" in tokens
        assert "device" in tokens
        assert "vascular" in tokens
        # Short words (< 3 chars) filtered out
        assert "is" not in tokens

    def test_tokenize_removes_punctuation(self):
        """Test tokenization removes punctuation."""
        text = "Test device, with punctuation! And symbols?"

        tokens = _tokenize(text)

        assert "test" in tokens
        assert "device" in tokens
        assert "punctuation" in tokens
        assert "symbols" in tokens

    def test_word_overlap_identical_text(self):
        """Test word overlap for identical texts."""
        text1 = "This is a test device"
        text2 = "This is a test device"

        overlap = _word_overlap(text1, text2)

        assert overlap == 1.0  # 100% overlap

    def test_word_overlap_no_overlap(self):
        """Test word overlap for completely different texts."""
        text1 = "cardiac stent device"
        text2 = "orthopedic bone screw"

        overlap = _word_overlap(text1, text2)

        assert overlap == 0.0  # No overlap

    def test_word_overlap_partial(self):
        """Test word overlap for partially similar texts."""
        text1 = "catheter device for vascular access"
        text2 = "catheter for temporary access"

        overlap = _word_overlap(text1, text2)

        assert 0 < overlap < 1.0  # Partial overlap

    def test_cosine_similarity_identical(self):
        """Test cosine similarity for identical texts."""
        text1 = "Test device for vascular access"
        text2 = "Test device for vascular access"

        similarity = _cosine_similarity(text1, text2)

        assert similarity == pytest.approx(1.0, abs=0.001)  # Allow for floating point precision

    def test_cosine_similarity_different(self):
        """Test cosine similarity for different texts."""
        text1 = "cardiac stent implant"
        text2 = "orthopedic bone screw"

        similarity = _cosine_similarity(text1, text2)

        assert similarity < 0.3  # Low similarity

    def test_cosine_similarity_term_frequency(self):
        """Test cosine similarity considers term frequency."""
        text1 = "device device device test"  # 'device' repeated
        text2 = "device test test test"  # 'test' repeated

        similarity = _cosine_similarity(text1, text2)

        assert 0 < similarity < 1.0  # Different TF distributions


# ============================================================================
# Batch Operations Tests
# ============================================================================


class TestBatchOperations:
    """Test suite for batch analysis operations."""

    def test_analyze_batch(self, mock_fda_client, mock_pma_store, mock_510k_data, mock_pma_data):
        """Test batch analysis of multiple devices."""
        mock_fda_client.get_510k.return_value = {
            "results": [mock_510k_data],
            "meta": {},
        }
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = None
        mock_pma_store.get_supplements.return_value = []

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        results = analyzer.analyze_batch(["K241335", "P170019"])

        assert len(results) == 2
        assert "K241335" in results
        assert "P170019" in results
        assert results["K241335"]["device_type"] == "510k"
        assert results["P170019"]["device_type"] == "pma"

    def test_compare_all_pairs(self, mock_fda_client, mock_510k_data):
        """Test pairwise comparison of device list."""
        mock_fda_client.get_510k.side_effect = [
            {"results": [mock_510k_data], "meta": {}},
            {"results": [{**mock_510k_data, "k_number": "K241336"}], "meta": {}},
            {"results": [{**mock_510k_data, "k_number": "K241337"}], "meta": {}},
        ] * 3  # Multiple calls for comparisons

        analyzer = UnifiedPredicateAnalyzer(client=mock_fda_client)
        comparisons = analyzer.compare_all_pairs(["K241335", "K241336", "K241337"])

        # 3 devices = 3 comparisons (1-2, 1-3, 2-3)
        assert len(comparisons) == 3


# ============================================================================
# PMA SE Table Integration Tests
# ============================================================================


class TestPMASETableIntegration:
    """Test suite for PMA-to-SE table data extraction."""

    def test_get_pma_se_table_data(self, mock_fda_client, mock_pma_store, mock_pma_data, mock_pma_sections):
        """Test extracting PMA data in SE table format."""
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = mock_pma_sections
        mock_pma_store.get_supplements.return_value = []

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        result = analyzer.get_pma_se_table_data("P170019")

        assert result["device_type"] == "pma"
        assert result["device_number"] == "P170019"
        assert result["device_name"] == "Test PMA Cardiac Device"
        assert result["regulatory_status"] == "PMA Approved"
        assert result["data_source"] == "ssed"
        assert result["intended_use"]  # Should have IFU content from sections

    def test_get_pma_intelligence_summary(self, mock_fda_client, mock_pma_store, mock_pma_data):
        """Test PMA intelligence summary generation."""
        mock_pma_store.get_pma_data.return_value = mock_pma_data
        mock_pma_store.get_extracted_sections.return_value = None
        mock_pma_store.get_supplements.return_value = [
            {"supplement_number": "S001", "supplement_type": "Manufacturing"},
            {"supplement_number": "S002", "supplement_type": "Labeling"},
            {"supplement_number": "S003", "supplement_type": "Labeling"},
        ]

        analyzer = UnifiedPredicateAnalyzer(
            client=mock_fda_client, pma_store=mock_pma_store
        )
        result = analyzer.get_pma_intelligence_summary("P170019")

        assert result["pma_number"] == "P170019"
        assert result["supplement_count"] == 3
        assert result["supplement_types"]["Labeling"] == 2
        assert result["supplement_types"]["Manufacturing"] == 1


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.scripts,
]
