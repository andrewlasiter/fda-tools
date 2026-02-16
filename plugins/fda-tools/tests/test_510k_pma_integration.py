"""
Integration test suite for 510(k)-PMA unified predicate interface.

Tests cover TICKET-003 Phase 1.5 integration:
    1. TestDeviceTypeDetection -- device number format detection
    2. TestUnifiedAnalysis -- analyze_predicate() for K/P/DEN numbers
    3. TestCrossPathwayComparison -- compare_devices() across pathways
    4. TestSuitabilityAssessment -- assess_suitability() scoring
    5. TestBatchOperations -- batch analysis and pairwise comparison
    6. TestSETableIntegration -- PMA data formatted for SE tables
    7. TestPMAIntelligenceSummary -- lightweight PMA intelligence
    8. TestTextSimilarity -- text comparison utilities
    9. TestPresub510kPMA -- presub planning with PMA predicates
   10. TestResearchPMA -- research command PMA integration

Target: 25+ tests, all offline using mocks.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ============================================================
# Shared test fixtures and mock data
# ============================================================

SAMPLE_510K_RESULT = {
    "results": [
        {
            "k_number": "K241335",
            "device_name": "Coronary Stent System",
            "applicant": "CardioTech Inc.",
            "product_code": "NIQ",
            "decision_date": "20240315",
            "clearance_type": "Traditional",
            "review_panel": "CV",
            "regulation_number": "870.3460",
            "statement_or_summary": "The device is intended for improving coronary luminal diameter in patients with ischemic heart disease.",
        }
    ],
    "meta": {"results": {"total": 1}},
}

SAMPLE_PMA_RESULT = {
    "pma_number": "P170019",
    "device_name": "FoundationOne CDx",
    "trade_name": "FoundationOne CDx",
    "applicant": "Foundation Medicine, Inc.",
    "product_code": "NMH",
    "decision_date": "20171130",
    "advisory_committee": "CH",
    "advisory_committee_description": "Clinical Chemistry",
    "regulation_number": "862.3360",
    "expedited_review_flag": "N",
    "supplement_count": 29,
}

SAMPLE_PMA_API_RESPONSE = {
    "results": [SAMPLE_PMA_RESULT],
    "meta": {"results": {"total": 1}},
}

SAMPLE_SSED_SECTIONS = {
    "metadata": {
        "total_sections_found": 10,
        "total_possible_sections": 15,
        "quality_score": 72,
    },
    "sections": {
        "indications_for_use": {
            "content": "The device is indicated as a companion diagnostic to identify patients with solid tumors who may benefit from targeted therapy based on genomic profiling.",
            "word_count": 25,
        },
        "device_description": {
            "content": "FoundationOne CDx is an FDA-approved next-generation sequencing (NGS) based in vitro diagnostic device that detects substitutions, insertion/deletions, and copy number alterations in 324 genes and select gene rearrangements.",
            "word_count": 35,
        },
        "clinical_studies": {
            "content": "A pivotal single-arm study enrolled 3,162 patients across 12 clinical sites. The primary endpoint was positive percent agreement for individual variant detection.",
            "word_count": 250,
        },
        "nonclinical_testing": {
            "content": "Analytical validation studies demonstrated high sensitivity and specificity for variant detection across all sample types.",
            "word_count": 50,
        },
        "potential_risks": {
            "content": "The primary risks associated with the device include false positive and false negative results that could lead to inappropriate treatment decisions.",
            "word_count": 30,
        },
        "biocompatibility": {
            "content": "Not applicable -- in vitro diagnostic device.",
            "word_count": 6,
        },
    },
}

SAMPLE_PMA_SUPPLEMENTS = [
    {"pma_number": "P170019S001", "supplement_type": "Labeling", "decision_date": "20180315"},
    {"pma_number": "P170019S002", "supplement_type": "New Indication", "decision_date": "20180710"},
    {"pma_number": "P170019S003", "supplement_type": "Design Change", "decision_date": "20190122"},
]


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_client():
    """Create a mocked FDAClient."""
    client = MagicMock()
    client.enabled = True

    # Default 510(k) response
    client.get_510k.return_value = SAMPLE_510K_RESULT

    # Default PMA response
    client.get_pma.return_value = SAMPLE_PMA_API_RESPONSE

    # Default validate_device routing
    def validate_side_effect(num):
        num = num.upper()
        if num.startswith("K"):
            return client.get_510k(num)
        elif num.startswith("P"):
            return client.get_pma(num)
        elif num.startswith("DEN"):
            return {"results": [], "meta": {"results": {"total": 0}},
                    "note": "DEN number not found"}
        return {"error": f"Unsupported format: {num}", "degraded": True}

    client.validate_device.side_effect = validate_side_effect
    return client


@pytest.fixture
def mock_pma_store(mock_client):
    """Create a mocked PMADataStore."""
    store = MagicMock()
    store.client = mock_client

    store.get_pma_data.return_value = SAMPLE_PMA_RESULT
    store.get_extracted_sections.return_value = SAMPLE_SSED_SECTIONS
    store.get_supplements.return_value = SAMPLE_PMA_SUPPLEMENTS

    return store


@pytest.fixture
def analyzer(mock_client, mock_pma_store):
    """Create a UnifiedPredicateAnalyzer with mocked dependencies."""
    from unified_predicate import UnifiedPredicateAnalyzer
    return UnifiedPredicateAnalyzer(client=mock_client, pma_store=mock_pma_store)


# ============================================================
# Test Classes
# ============================================================

class TestDeviceTypeDetection:
    """Test device number format detection."""

    def test_detect_510k_number(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("K241335") == "510k"

    def test_detect_510k_lowercase(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("k241335") == "510k"

    def test_detect_pma_number(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("P170019") == "pma"

    def test_detect_pma_supplement(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("P170019S001") == "pma"

    def test_detect_de_novo(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("DEN1234567") == "de_novo"

    def test_detect_pre_amendment(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("N123456") == "pre_amendment"

    def test_detect_unknown(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.detect_device_type("X123456") == "unknown"

    def test_is_pma_number(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.is_pma_number("P170019") is True
        assert UnifiedPredicateAnalyzer.is_pma_number("K241335") is False

    def test_is_510k_number(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        assert UnifiedPredicateAnalyzer.is_510k_number("K241335") is True
        assert UnifiedPredicateAnalyzer.is_510k_number("P170019") is False

    def test_classify_mixed_list(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        result = UnifiedPredicateAnalyzer.classify_device_list(
            ["K241335", "P170019", "K232050", "P200024", "DEN1234567"]
        )
        assert len(result.get("510k", [])) == 2
        assert len(result.get("pma", [])) == 2
        assert len(result.get("de_novo", [])) == 1


class TestUnifiedAnalysis:
    """Test analyze_predicate() for different device types."""

    def test_analyze_510k(self, analyzer, mock_client):
        result = analyzer.analyze_predicate("K241335")
        assert result["valid"] is True
        assert result["device_type"] == "510k"
        assert result["device_number"] == "K241335"
        assert result["device_name"] == "Coronary Stent System"
        assert result["product_code"] == "NIQ"
        assert result["regulatory_status"] == "cleared"

    def test_analyze_pma(self, analyzer, mock_pma_store):
        result = analyzer.analyze_predicate("P170019")
        assert result["valid"] is True
        assert result["device_type"] == "pma"
        assert result["device_number"] == "P170019"
        assert result["device_name"] == "FoundationOne CDx"
        assert result["product_code"] == "NMH"
        assert result["regulatory_status"] == "approved"
        assert result["supplement_count"] == 3
        assert result["has_clinical_data"] is True

    def test_analyze_pma_intended_use_from_ssed(self, analyzer, mock_pma_store):
        result = analyzer.analyze_predicate("P170019")
        assert "companion diagnostic" in result.get("intended_use", "")

    def test_analyze_pma_without_sections(self, analyzer, mock_pma_store):
        mock_pma_store.get_extracted_sections.return_value = None
        result = analyzer.analyze_predicate("P170019")
        assert result["valid"] is True
        assert result["has_ssed_sections"] is False
        assert result["clinical_data_source"] == "api_metadata"

    def test_analyze_unknown_format(self, analyzer):
        result = analyzer.analyze_predicate("X123456")
        assert result["valid"] is False
        assert "Unrecognized" in result.get("error", "")

    def test_analyze_510k_not_found(self, analyzer, mock_client):
        mock_client.get_510k.return_value = {
            "results": [],
            "meta": {"results": {"total": 0}},
        }
        result = analyzer.analyze_predicate("K999999")
        assert result["valid"] is False
        assert "not found" in result.get("error", "").lower()

    def test_analyze_pma_api_error(self, analyzer, mock_pma_store):
        mock_pma_store.get_pma_data.return_value = {"error": "API timeout"}
        result = analyzer.analyze_predicate("P999999")
        assert result["valid"] is False
        assert "API timeout" in result.get("error", "")


class TestCrossPathwayComparison:
    """Test compare_devices() across 510(k) and PMA pathways."""

    def test_compare_510k_vs_pma(self, analyzer):
        result = analyzer.compare_devices("K241335", "P170019")
        assert "error" not in result
        assert result["comparison_type"] == "510k_vs_pma"
        assert result["data_quality"]["cross_pathway"] is True
        assert 0 <= result["overall_similarity"] <= 100

    def test_compare_same_type_510k(self, analyzer, mock_client):
        # Second 510(k) with different data
        second_510k = {
            "results": [{
                "k_number": "K232050",
                "device_name": "Coronary Balloon Catheter",
                "applicant": "CardioTech Inc.",
                "product_code": "NIQ",
                "decision_date": "20230901",
                "clearance_type": "Traditional",
                "review_panel": "CV",
                "regulation_number": "870.3460",
                "statement_or_summary": "The device is intended for dilatation of coronary artery stenosis.",
            }],
            "meta": {"results": {"total": 1}},
        }

        def get_510k_side_effect(num):
            if num == "K232050":
                return second_510k
            return SAMPLE_510K_RESULT

        mock_client.get_510k.side_effect = get_510k_side_effect

        result = analyzer.compare_devices("K241335", "K232050")
        assert result["comparison_type"] == "510k_vs_510k"
        assert result["data_quality"]["cross_pathway"] is False

    def test_compare_dimensions_present(self, analyzer):
        result = analyzer.compare_devices("K241335", "P170019")
        dims = result.get("dimensions", {})
        assert "indications" in dims
        assert "device_specs" in dims
        assert "clinical_data" in dims
        assert "safety_profile" in dims
        assert "regulatory_history" in dims

    def test_compare_dimension_scores(self, analyzer):
        result = analyzer.compare_devices("K241335", "P170019")
        for dim_name, dim_data in result.get("dimensions", {}).items():
            assert "score" in dim_data
            assert 0 <= dim_data["score"] <= 100

    def test_compare_similarity_level(self, analyzer):
        result = analyzer.compare_devices("K241335", "P170019")
        assert result["similarity_level"] in ("HIGH", "MODERATE", "LOW", "MINIMAL")

    def test_compare_key_differences(self, analyzer):
        result = analyzer.compare_devices("K241335", "P170019")
        for diff in result.get("key_differences", []):
            assert "dimension" in diff
            assert "score" in diff
            assert "severity" in diff
            assert diff["severity"] in ("NOTABLE", "CRITICAL")

    def test_compare_device1_not_found(self, analyzer, mock_client):
        mock_client.get_510k.return_value = {"results": [], "meta": {"results": {"total": 0}}}
        result = analyzer.compare_devices("K999999", "P170019")
        assert "error" in result

    def test_compare_device2_not_found(self, analyzer, mock_pma_store):
        mock_pma_store.get_pma_data.return_value = {"error": "Not found"}
        result = analyzer.compare_devices("K241335", "P999999")
        assert "error" in result


class TestSuitabilityAssessment:
    """Test assess_suitability() scoring."""

    def test_assess_pma_as_predicate(self, analyzer):
        subject = {
            "product_code": "NMH",
            "intended_use": "A companion diagnostic test for identifying patients with solid tumors who may benefit from targeted therapy.",
            "device_description": "An NGS-based in vitro diagnostic device for genomic profiling.",
        }
        result = analyzer.assess_suitability("P170019", subject)
        assert result["candidate"] == "P170019"
        assert result["candidate_type"] == "pma"
        assert 0 <= result["score"] <= 100
        assert result["max_score"] == 100
        assert isinstance(result["suitable"], bool)
        assert len(result["factors"]) > 0

    def test_assess_510k_as_predicate(self, analyzer):
        subject = {
            "product_code": "NIQ",
            "intended_use": "The device is intended for improving coronary luminal diameter.",
        }
        result = analyzer.assess_suitability("K241335", subject)
        assert result["candidate_type"] == "510k"
        assert 0 <= result["score"] <= 100

    def test_assess_product_code_match_scoring(self, analyzer):
        # Same product code
        subject_match = {"product_code": "NMH", "intended_use": "Test"}
        result_match = analyzer.assess_suitability("P170019", subject_match)

        # Different product code
        subject_diff = {"product_code": "XXX", "intended_use": "Test"}
        result_diff = analyzer.assess_suitability("P170019", subject_diff)

        # Same product code should score higher
        assert result_match["score"] > result_diff["score"]

    def test_assess_indication_similarity_scoring(self, analyzer):
        # High similarity intended use
        subject_similar = {
            "product_code": "NMH",
            "intended_use": "A companion diagnostic to identify patients with solid tumors who may benefit from genomic profiling based targeted therapy.",
        }
        result_similar = analyzer.assess_suitability("P170019", subject_similar)

        # Low similarity intended use
        subject_different = {
            "product_code": "NMH",
            "intended_use": "A blood pressure monitoring device for home use.",
        }
        result_different = analyzer.assess_suitability("P170019", subject_different)

        # Similar intended use should score higher
        assert result_similar["score"] > result_different["score"]

    def test_assess_pathway_notes_for_pma(self, analyzer):
        subject = {"product_code": "NMH"}
        result = analyzer.assess_suitability("P170019", subject)
        assert len(result.get("pathway_notes", [])) > 0
        assert any("PMA" in note for note in result["pathway_notes"])

    def test_assess_candidate_not_found(self, analyzer, mock_pma_store):
        mock_pma_store.get_pma_data.return_value = {"error": "Not found"}
        result = analyzer.assess_suitability("P999999", {"product_code": "NMH"})
        assert result["suitable"] is False
        assert result["score"] == 0

    def test_assess_suitability_thresholds(self, analyzer):
        """Verify suitability thresholds: >=70 STRONG, >=50 MODERATE, >=30 WEAK, <30 NOT."""
        subject = {"product_code": "NMH", "intended_use": "Companion diagnostic for genomic profiling of solid tumors."}
        result = analyzer.assess_suitability("P170019", subject)

        if result["score"] >= 70:
            assert result["suitable"] is True
            assert "STRONG" in result["recommendation"]
        elif result["score"] >= 50:
            assert result["suitable"] is True
            assert "MODERATE" in result["recommendation"]
        elif result["score"] >= 30:
            assert result["suitable"] is False
            assert "WEAK" in result["recommendation"]
        else:
            assert result["suitable"] is False
            assert "NOT recommended" in result["recommendation"]


class TestBatchOperations:
    """Test batch analysis and pairwise comparison."""

    def test_analyze_batch_mixed(self, analyzer):
        results = analyzer.analyze_batch(["K241335", "P170019"])
        assert "K241335" in results
        assert "P170019" in results
        assert results["K241335"]["device_type"] == "510k"
        assert results["P170019"]["device_type"] == "pma"

    def test_compare_all_pairs(self, analyzer, mock_client):
        # Set up second 510(k)
        second_510k = {
            "results": [{
                "k_number": "K232050",
                "device_name": "NGS Panel",
                "applicant": "GenomeTech",
                "product_code": "NMH",
                "decision_date": "20230601",
                "clearance_type": "Traditional",
                "review_panel": "CH",
                "regulation_number": "862.3360",
                "statement_or_summary": "NGS-based diagnostic panel.",
            }],
            "meta": {"results": {"total": 1}},
        }

        original_get_510k = mock_client.get_510k
        def get_510k_side_effect(num):
            if num == "K232050":
                return second_510k
            return SAMPLE_510K_RESULT

        mock_client.get_510k.side_effect = get_510k_side_effect

        comparisons = analyzer.compare_all_pairs(["K241335", "P170019", "K232050"])
        # 3 devices => 3 pairs: (K241335,P170019), (K241335,K232050), (P170019,K232050)
        assert len(comparisons) == 3


class TestSETableIntegration:
    """Test PMA data formatted for SE comparison tables."""

    def test_get_pma_se_table_data(self, analyzer):
        result = analyzer.get_pma_se_table_data("P170019")
        assert "error" not in result
        assert result["device_type"] == "pma"
        assert result["device_number"] == "P170019"
        assert result["intended_use"] != ""
        assert result["device_description"] != ""
        assert result["regulatory_status"] == "PMA Approved"

    def test_se_table_data_has_clinical_fields(self, analyzer):
        result = analyzer.get_pma_se_table_data("P170019")
        assert "clinical_data" in result
        assert "performance_testing" in result
        assert "biocompatibility" in result
        assert "safety_profile" in result

    def test_se_table_data_quality_score(self, analyzer):
        result = analyzer.get_pma_se_table_data("P170019")
        assert result.get("section_quality", 0) > 0

    def test_se_table_data_without_sections(self, analyzer, mock_pma_store):
        mock_pma_store.get_extracted_sections.return_value = None
        result = analyzer.get_pma_se_table_data("P170019")
        assert result["data_source"] == "api_metadata"


class TestPMAIntelligenceSummary:
    """Test lightweight PMA intelligence summary."""

    def test_intelligence_summary(self, analyzer):
        result = analyzer.get_pma_intelligence_summary("P170019")
        assert "error" not in result
        assert result["pma_number"] == "P170019"
        assert result["device_name"] == "FoundationOne CDx"
        assert result["supplement_count"] == 3
        assert isinstance(result["supplement_types"], dict)

    def test_intelligence_summary_supplement_categorization(self, analyzer):
        result = analyzer.get_pma_intelligence_summary("P170019")
        supp_types = result.get("supplement_types", {})
        assert supp_types.get("Labeling", 0) >= 1
        assert supp_types.get("New Indication", 0) >= 1


class TestTextSimilarity:
    """Test text similarity utility functions."""

    def test_cosine_identical(self):
        from unified_predicate import _cosine_similarity
        text = "The device is intended for coronary artery stenting."
        score = _cosine_similarity(text, text)
        assert abs(score - 1.0) < 0.01

    def test_cosine_different(self):
        from unified_predicate import _cosine_similarity
        text1 = "The device is intended for coronary artery stenting."
        text2 = "A software application for analyzing brain MRI scans."
        score = _cosine_similarity(text1, text2)
        assert score < 0.3

    def test_cosine_empty(self):
        from unified_predicate import _cosine_similarity
        assert _cosine_similarity("", "test") == 0.0
        assert _cosine_similarity("test", "") == 0.0

    def test_word_overlap_identical(self):
        from unified_predicate import _word_overlap
        text = "coronary artery stent device"
        score = _word_overlap(text, text)
        assert abs(score - 1.0) < 0.01

    def test_word_overlap_partial(self):
        from unified_predicate import _word_overlap
        text1 = "coronary artery stent device for patients"
        text2 = "coronary artery catheter device for intervention"
        score = _word_overlap(text1, text2)
        assert 0.2 < score < 0.8

    def test_tokenize(self):
        from unified_predicate import _tokenize
        tokens = _tokenize("The device is FDA-approved!")
        assert "the" in tokens
        assert "device" in tokens
        assert "fda" in tokens
        # Short words (<=2 chars) should be excluded
        assert "is" not in tokens


class TestPresub510kPMA:
    """Test pre-submission planning with PMA predicates.

    Verifies that the unified predicate interface works correctly
    in presub context -- analyzing PMA devices for Pre-Sub packages.
    """

    def test_pma_predicate_for_presub(self, analyzer):
        """A PMA predicate should provide rich data for Pre-Sub planning."""
        result = analyzer.analyze_predicate("P170019")
        assert result["valid"] is True
        assert result["device_type"] == "pma"
        # Must have enough data for presub template population
        assert result.get("product_code", "") != ""
        assert result.get("decision_date", "") != ""

    def test_mixed_predicates_for_presub(self, analyzer):
        """Pre-Sub with both 510(k) and PMA predicates should work."""
        batch = analyzer.analyze_batch(["K241335", "P170019"])
        assert len(batch) == 2
        # Both should be valid
        for num, data in batch.items():
            assert data["valid"] is True
        # Types should differ
        types = {data["device_type"] for data in batch.values()}
        assert "510k" in types
        assert "pma" in types


class TestResearchPMA:
    """Test research command PMA integration.

    Verifies that PMA intelligence can be integrated into research reports.
    """

    def test_pma_intelligence_for_research(self, analyzer):
        """PMA intelligence summary should provide research-ready data."""
        summary = analyzer.get_pma_intelligence_summary("P170019")
        # Must have fields needed for research report PMA section
        assert "pma_number" in summary
        assert "device_name" in summary
        assert "applicant" in summary
        assert "supplement_count" in summary
        assert "supplement_types" in summary

    def test_pma_se_data_for_research(self, analyzer):
        """SE table data should be usable in research competitive analysis."""
        se_data = analyzer.get_pma_se_table_data("P170019")
        assert "intended_use" in se_data
        assert "device_description" in se_data
        assert "clinical_data" in se_data


# ============================================================
# Additional edge case tests
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_whitespace_in_device_number(self, analyzer):
        result = analyzer.analyze_predicate("  P170019  ")
        assert result["valid"] is True
        assert result["device_number"] == "P170019"

    def test_lowercase_device_number(self, analyzer):
        result = analyzer.analyze_predicate("p170019")
        assert result["valid"] is True
        assert result["device_number"] == "P170019"

    def test_pma_with_no_supplements(self, analyzer, mock_pma_store):
        mock_pma_store.get_supplements.return_value = []
        result = analyzer.analyze_predicate("P170019")
        assert result["supplement_count"] == 0

    def test_pma_with_none_supplements(self, analyzer, mock_pma_store):
        mock_pma_store.get_supplements.return_value = None
        result = analyzer.analyze_predicate("P170019")
        assert result["supplement_count"] == 0

    def test_compare_same_device(self, analyzer):
        """Comparing a device with itself should yield high similarity."""
        result = analyzer.compare_devices("P170019", "P170019")
        assert result["overall_similarity"] >= 75

    def test_suitability_empty_subject(self, analyzer):
        """Assessment with empty subject device should still work."""
        result = analyzer.assess_suitability("P170019", {})
        assert 0 <= result["score"] <= 100
        # Without any subject info, score should be low
        # (only regulatory standing and possibly recency/clinical points)

    def test_classify_empty_list(self):
        from unified_predicate import UnifiedPredicateAnalyzer
        result = UnifiedPredicateAnalyzer.classify_device_list([])
        assert result == {}
