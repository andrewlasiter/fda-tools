"""
Comprehensive test suite for PMA Intelligence Module - Phase 1.

Tests cover all Phase 1 modules:
    1. TestPMAComparison -- pma_comparison.py comparison engine
    2. TestClinicalIntelligence -- pma_intelligence.py clinical extraction
    3. TestSupplementAnalysis -- pma_intelligence.py supplement tracking
    4. TestPredicateIntelligence -- pma_intelligence.py predicate analysis
    5. TestPMACompareCommand -- pma-compare.md interface
    6. TestPMAIntelligenceCommand -- pma-intelligence.md interface
    7. TestIntegration -- Cross-module integration

Target: 80+ tests, 90% code coverage.
All tests run offline (no network access) using mocks.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add scripts directory to path
# Package imports configured in conftest.py and pytest.ini


# ============================================================
# Shared test fixtures and data
# ============================================================

SAMPLE_SSED_CLINICAL_TEXT = """
VII. SUMMARY OF CLINICAL STUDIES

A pivotal randomized controlled trial was conducted to evaluate the safety
and effectiveness of the device. The study enrolled 1,200 patients across
15 clinical sites in a multicenter, prospective design.

The primary endpoint was device success rate at 12 months, defined as
freedom from target lesion revascularization. The secondary endpoint
included all-cause mortality and myocardial infarction rates.

Results showed a device success rate of 92.5% (95% CI: 90.3-94.2%).
The p-value was < 0.001, demonstrating statistical significance versus
the control arm. Sensitivity was 95.2% and specificity was 88.7%.
Positive percent agreement (PPA) was 93.1%.

The primary safety endpoint was the rate of device-related serious adverse
events at 30 days. The adverse event rate was 3.2%. There were 2 deaths
(0.17%) in the study population. 15 serious adverse events were reported.

Follow-up of 24 months was completed for the primary analysis.

VIII. STATISTICAL ANALYSIS

The sample size of N = 1200 was determined using a non-inferiority design
with a margin of 5%. The study was powered at 90% with alpha = 0.05.
Bayesian adaptive design was used for interim analyses.
"""

SAMPLE_SSED_DEVICE_TEXT = """
III. DEVICE DESCRIPTION

The device is an implantable percutaneous titanium stent with a
drug-eluting coating. It is designed for use in the coronary vasculature.
The device uses a balloon-expandable delivery system. The stent is
manufactured from stainless steel with a bioabsorbable polymer coating.

The device is sterile and single-use. It is available in multiple
dimensions including 2.5mm, 3.0mm, and 3.5mm diameters.
"""

SAMPLE_SSED_INDICATION_TEXT = """
II. INDICATIONS FOR USE

The device is indicated for improving coronary luminal diameter in
patients with symptomatic ischemic heart disease due to de novo native
coronary artery lesions (length <= 28 mm) with reference vessel
diameters of 2.5 mm to 3.5 mm.
"""

SAMPLE_SSED_SAFETY_TEXT = """
VI. POTENTIAL RISKS AND ADVERSE EFFECTS

The potential risks associated with the device include thrombosis,
embolism, hemorrhage, perforation, and device malfunction. There is
a risk of death in rare cases. Post-approval study monitoring is
required as a condition of approval.

Biocompatibility testing was performed per ISO 10993, including
cytotoxicity, sensitization, and genotoxicity assessments.
Contraindications include patients with known allergy to device materials.
"""

SAMPLE_SECTIONS = {
    "success": True,
    "sections": {
        "indications_for_use": {
            "display_name": "Indications for Use",
            "content": SAMPLE_SSED_INDICATION_TEXT,
            "word_count": len(SAMPLE_SSED_INDICATION_TEXT.split()),
            "confidence": 0.95,
        },
        "device_description": {
            "display_name": "Device Description",
            "content": SAMPLE_SSED_DEVICE_TEXT,
            "word_count": len(SAMPLE_SSED_DEVICE_TEXT.split()),
            "confidence": 0.90,
        },
        "clinical_studies": {
            "display_name": "Summary of Clinical Studies",
            "content": SAMPLE_SSED_CLINICAL_TEXT,
            "word_count": len(SAMPLE_SSED_CLINICAL_TEXT.split()),
            "confidence": 0.92,
        },
        "potential_risks": {
            "display_name": "Potential Risks and Adverse Effects",
            "content": SAMPLE_SSED_SAFETY_TEXT,
            "word_count": len(SAMPLE_SSED_SAFETY_TEXT.split()),
            "confidence": 0.88,
        },
        "general_information": {
            "display_name": "General Information",
            "content": "General information about the device application.",
            "word_count": 7,
            "confidence": 0.85,
        },
        "marketing_history": {
            "display_name": "Marketing History",
            "content": "The device has been marketed in the EU since 2015.",
            "word_count": 10,
            "confidence": 0.80,
        },
        "benefit_risk": {
            "display_name": "Benefit-Risk Analysis",
            "content": "The benefits outweigh the risks. Post-market surveillance required.",
            "word_count": 9,
            "confidence": 0.85,
        },
    },
    "metadata": {
        "total_sections_found": 7,
        "total_possible_sections": 15,
        "quality_score": 72,
    },
}

SAMPLE_API_DATA = {
    "pma_number": "P170019",
    "applicant": "Foundation Medicine",
    "device_name": "FoundationOne CDx",
    "generic_name": "IVD Panel",
    "product_code": "NMH",
    "decision_date": "20171130",
    "decision_code": "APPR",
    "advisory_committee": "CH",
    "advisory_committee_description": "Clinical Chemistry",
    "supplement_count": 29,
    "expedited_review_flag": "N",
}

SAMPLE_API_DATA_2 = {
    "pma_number": "P160035",
    "applicant": "Memorial Sloan Kettering",
    "device_name": "MSK-IMPACT",
    "generic_name": "IVD Panel",
    "product_code": "NMH",
    "decision_date": "20171115",
    "decision_code": "APPR",
    "advisory_committee": "CH",
    "advisory_committee_description": "Clinical Chemistry",
    "supplement_count": 12,
    "expedited_review_flag": "N",
}

SAMPLE_SUPPLEMENTS = [
    {
        "pma_number": "P170019S029",
        "supplement_number": "S029",
        "supplement_type": "labeling supplement",
        "supplement_reason": "New BRCA1/2 indication",
        "decision_date": "20210716",
        "decision_code": "APPR",
        "applicant": "Foundation Medicine",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S028",
        "supplement_number": "S028",
        "supplement_type": "labeling supplement",
        "supplement_reason": "Updated warnings and precautions",
        "decision_date": "20210521",
        "decision_code": "APPR",
        "applicant": "Foundation Medicine",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S020",
        "supplement_number": "S020",
        "supplement_type": "design change",
        "supplement_reason": "Manufacturing process modification",
        "decision_date": "20200315",
        "decision_code": "APPR",
        "applicant": "Foundation Medicine",
        "trade_name": "FoundationOne CDx",
    },
    {
        "pma_number": "P170019S005",
        "supplement_number": "S005",
        "supplement_type": "post-approval study",
        "supplement_reason": "PAS interim report",
        "decision_date": "20180901",
        "decision_code": "APPR",
        "applicant": "Foundation Medicine",
        "trade_name": "FoundationOne CDx",
    },
]


# ============================================================
# 1. TestPMAComparison -- pma_comparison.py
# ============================================================


class TestTextSimilarity:
    """Test text similarity utility functions."""

    def test_tokenize_basic(self):
        from pma_comparison import _tokenize
        tokens = _tokenize("Hello World test")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_tokenize_removes_short_words(self):
        from pma_comparison import _tokenize
        tokens = _tokenize("I am a test of the system")
        assert "test" in tokens
        assert "system" in tokens
        # Words <= 2 chars should be filtered
        assert "am" not in tokens
        assert "of" not in tokens

    def test_tokenize_empty(self):
        from pma_comparison import _tokenize
        assert _tokenize("") == []
        assert _tokenize(None) == []

    def test_word_overlap_identical(self):
        from pma_comparison import _word_overlap_score
        score = _word_overlap_score("test device clinical", "test device clinical")
        assert score == 1.0

    def test_word_overlap_no_overlap(self):
        from pma_comparison import _word_overlap_score
        score = _word_overlap_score("alpha beta gamma", "delta epsilon zeta")
        assert score == 0.0

    def test_word_overlap_partial(self):
        from pma_comparison import _word_overlap_score
        score = _word_overlap_score("test device clinical study",
                                     "test device safety analysis")
        assert 0.0 < score < 1.0

    def test_word_overlap_empty(self):
        from pma_comparison import _word_overlap_score
        assert _word_overlap_score("", "test") == 0.0
        assert _word_overlap_score("test", "") == 0.0

    def test_cosine_similarity_identical(self):
        from pma_comparison import _cosine_similarity
        text = "randomized controlled trial with clinical endpoints"
        score = _cosine_similarity(text, text)
        assert abs(score - 1.0) < 0.001

    def test_cosine_similarity_different(self):
        from pma_comparison import _cosine_similarity
        score = _cosine_similarity(
            "randomized controlled trial clinical",
            "manufacturing sterilization packaging"
        )
        assert score < 0.3

    def test_cosine_similarity_empty(self):
        from pma_comparison import _cosine_similarity
        assert _cosine_similarity("", "test") == 0.0

    def test_key_term_overlap(self):
        from pma_comparison import _key_term_overlap
        text1 = "This is a randomized controlled trial with primary endpoint survival"
        text2 = "This is a randomized study with primary endpoint efficacy"
        terms = ["randomized", "primary endpoint", "survival", "efficacy"]
        score = _key_term_overlap(text1, text2, terms)
        assert 0.0 < score < 1.0

    def test_key_term_overlap_no_terms(self):
        from pma_comparison import _key_term_overlap
        assert _key_term_overlap("test", "test", []) == 0.0


class TestPMAComparisonEngine:
    """Test PMA comparison engine core functionality."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_comparison import PMAComparisonEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAComparisonEngine(store=store)

    def test_compare_indications_full_data(self, engine):
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": SAMPLE_SECTIONS}
        pma2 = {"api_data": SAMPLE_API_DATA_2, "sections": SAMPLE_SECTIONS}
        result = engine._compare_indications(pma1, pma2)
        assert result["data_quality"] == "full"
        assert 0 <= result["score"] <= 100

    def test_compare_indications_no_data(self, engine):
        pma1 = {"api_data": {}, "sections": None}
        pma2 = {"api_data": {}, "sections": None}
        result = engine._compare_indications(pma1, pma2)
        assert result["data_quality"] == "no_data"
        assert result["score"] == 0.0

    def test_compare_indications_partial_data(self, engine):
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": SAMPLE_SECTIONS}
        pma2 = {"api_data": SAMPLE_API_DATA_2, "sections": None}
        result = engine._compare_indications(pma1, pma2)
        assert result["data_quality"] == "partial"

    def test_compare_clinical_data_full(self, engine):
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": SAMPLE_SECTIONS}
        pma2 = {"api_data": SAMPLE_API_DATA_2, "sections": SAMPLE_SECTIONS}
        result = engine._compare_clinical_data(pma1, pma2)
        assert result["data_quality"] == "full"
        assert 0 <= result["score"] <= 100
        assert "study_design_similarity" in result["details"]

    def test_compare_clinical_data_no_data(self, engine):
        pma1 = {"api_data": {}, "sections": None}
        pma2 = {"api_data": {}, "sections": None}
        result = engine._compare_clinical_data(pma1, pma2)
        assert result["data_quality"] == "no_data"

    def test_compare_device_specs_full(self, engine):
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": SAMPLE_SECTIONS}
        pma2 = {"api_data": SAMPLE_API_DATA_2, "sections": SAMPLE_SECTIONS}
        result = engine._compare_device_specs(pma1, pma2)
        assert result["data_quality"] == "full"
        assert 0 <= result["score"] <= 100

    def test_compare_device_specs_same_product_code_bonus(self, engine):
        pma1 = {"api_data": {"product_code": "NMH"}, "sections": SAMPLE_SECTIONS}
        pma2 = {"api_data": {"product_code": "NMH"}, "sections": SAMPLE_SECTIONS}
        result = engine._compare_device_specs(pma1, pma2)
        assert result["details"].get("same_product_code") is True

    def test_compare_device_specs_metadata_only(self, engine):
        pma1 = {"api_data": {"product_code": "NMH"}, "sections": None}
        pma2 = {"api_data": {"product_code": "NMH"}, "sections": None}
        result = engine._compare_device_specs(pma1, pma2)
        assert result["data_quality"] == "metadata_only"
        assert result["score"] == 50.0

    def test_compare_safety_profiles(self, engine):
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": SAMPLE_SECTIONS}
        pma2 = {"api_data": SAMPLE_API_DATA_2, "sections": SAMPLE_SECTIONS}
        result = engine._compare_safety_profiles(pma1, pma2)
        assert 0 <= result["score"] <= 100

    def test_compare_regulatory_history_same_pc(self, engine):
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": None, "supplement_count": 29}
        pma2 = {"api_data": SAMPLE_API_DATA_2, "sections": None, "supplement_count": 12}
        result = engine._compare_regulatory_history(pma1, pma2)
        assert result["details"]["same_product_code"] is True
        assert result["details"]["same_advisory_committee"] is True
        assert result["score"] > 50  # Same PC + same committee should be high

    def test_compare_regulatory_history_different_pc(self, engine):
        api_different_pc = dict(SAMPLE_API_DATA_2)
        api_different_pc["product_code"] = "XYZ"
        api_different_pc["advisory_committee"] = "OR"
        pma1 = {"api_data": SAMPLE_API_DATA, "sections": None, "supplement_count": 5}
        pma2 = {"api_data": api_different_pc, "sections": None, "supplement_count": 5}
        result = engine._compare_regulatory_history(pma1, pma2)
        assert result["details"]["same_product_code"] is False

    def test_score_to_level(self, engine):
        assert engine._score_to_level(80) == "HIGH"
        assert engine._score_to_level(60) == "MODERATE"
        assert engine._score_to_level(30) == "LOW"
        assert engine._score_to_level(10) == "MINIMAL"

    def test_calculate_overall_score(self, engine):
        pair_comparisons = {
            "indications": {"score": 80},
            "clinical_data": {"score": 70},
            "device_specs": {"score": 60},
            "safety_profile": {"score": 50},
            "regulatory_history": {"score": 90},
        }
        score = engine._calculate_overall_score(
            pair_comparisons,
            ["indications", "clinical_data", "device_specs", "safety_profile", "regulatory_history"],
        )
        # Should be weighted average
        expected = (80*0.30 + 70*0.25 + 60*0.20 + 50*0.15 + 90*0.10) / 1.0
        assert abs(score - expected) < 0.2

    def test_calculate_overall_score_partial_dimensions(self, engine):
        pair_comparisons = {
            "indications": {"score": 80},
            "clinical_data": {"score": 70},
        }
        score = engine._calculate_overall_score(
            pair_comparisons,
            ["indications", "clinical_data"],
        )
        # Only 2 dimensions, should normalize
        expected = (80*0.30 + 70*0.25) / (0.30 + 0.25)
        assert abs(score - expected) < 0.2

    def test_identify_key_differences(self, engine):
        matrix = {
            "P1_vs_P2": {
                "indications": {"score": 80},
                "clinical_data": {"score": 30},
                "device_specs": {"score": 20},
            }
        }
        diffs = engine._identify_key_differences(matrix, "P1", ["P2"])
        assert len(diffs) >= 1
        # Should be sorted by score ascending
        assert diffs[0]["score"] <= diffs[-1]["score"]

    def test_summarize_pma(self, engine):
        pma_data = {
            "api_data": SAMPLE_API_DATA,
            "sections": SAMPLE_SECTIONS,
            "supplement_count": 29,
        }
        summary = engine._summarize_pma(pma_data)
        assert summary["pma_number"] == "P170019"
        assert summary["device_name"] == "FoundationOne CDx"
        assert summary["sections_available"] > 0


class TestStudyDesignComparison:
    """Test study design comparison logic."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_comparison import PMAComparisonEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAComparisonEngine(store=store)

    def test_same_study_designs(self, engine):
        text1 = "A pivotal randomized controlled trial was conducted"
        text2 = "The pivotal randomized controlled trial enrolled patients"
        score = engine._compare_study_designs(text1, text2)
        assert score > 0.5

    def test_different_study_designs(self, engine):
        text1 = "A pivotal randomized controlled trial was conducted"
        text2 = "A retrospective registry study was analyzed"
        score = engine._compare_study_designs(text1, text2)
        assert score < 0.5

    def test_no_designs_detected(self, engine):
        text1 = "The device was tested in the laboratory"
        text2 = "Bench testing was performed"
        score = engine._compare_study_designs(text1, text2)
        assert score == 0.5  # Neutral when no designs detected

    def test_compare_endpoints(self, engine):
        text1 = "Primary endpoint was survival rate and sensitivity analysis"
        text2 = "Primary endpoint was survival and device success"
        score = engine._compare_endpoints(text1, text2)
        assert 0.0 < score < 1.0

    def test_compare_enrollment_similar(self, engine):
        text1 = "The study enrolled 1200 patients"
        text2 = "N = 1100 subjects were included"
        score = engine._compare_enrollment(text1, text2)
        assert score > 0.5

    def test_compare_enrollment_very_different(self, engine):
        text1 = "The study enrolled 50 patients"
        text2 = "N = 5000 subjects were included"
        score = engine._compare_enrollment(text1, text2)
        assert score < 0.5

    def test_compare_enrollment_unknown(self, engine):
        text1 = "The device was studied"
        text2 = "Testing was performed"
        score = engine._compare_enrollment(text1, text2)
        assert score == 0.5  # Neutral when unknown


class TestComparisonCaching:
    """Test comparison caching functionality."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_comparison import PMAComparisonEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAComparisonEngine(store=store)

    def test_save_and_load_cache(self, engine):
        result = {
            "comparison_id": "P170019_vs_P160035",
            "focus_areas": ["indications", "clinical_data"],
            "overall_similarity": 72.5,
        }
        engine._save_comparison_cache(result)

        cached = engine._check_comparison_cache(
            "P170019", ["P160035"], ["indications", "clinical_data"]
        )
        assert cached is not None
        assert cached["overall_similarity"] == 72.5

    def test_cache_returns_none_when_missing(self, engine):
        cached = engine._check_comparison_cache("P999999", ["P888888"], ["all"])
        assert cached is None

    def test_cache_returns_none_for_different_dimensions(self, engine):
        result = {
            "comparison_id": "P170019_vs_P160035",
            "focus_areas": ["indications"],
            "overall_similarity": 72.5,
        }
        engine._save_comparison_cache(result)

        # Request more dimensions than cached
        cached = engine._check_comparison_cache(
            "P170019", ["P160035"], ["indications", "clinical_data"]
        )
        assert cached is None


# ============================================================
# 2. TestClinicalIntelligence -- pma_intelligence.py
# ============================================================


class TestStudyDesignDetection:
    """Test study design pattern detection."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAIntelligenceEngine(store=store)

    def test_detect_rct(self, engine):
        text = "A randomized controlled trial was conducted"
        designs = engine.detect_study_designs(text)
        types = [d["type"] for d in designs]
        assert "rct" in types

    def test_detect_pivotal_rct(self, engine):
        text = "The pivotal randomized controlled trial enrolled patients"
        designs = engine.detect_study_designs(text)
        types = [d["type"] for d in designs]
        assert "pivotal_rct" in types

    def test_detect_single_arm(self, engine):
        text = "A single-arm study design was used"
        designs = engine.detect_study_designs(text)
        types = [d["type"] for d in designs]
        assert "single_arm" in types

    def test_detect_registry(self, engine):
        text = "Data from a patient registry was analyzed"
        designs = engine.detect_study_designs(text)
        types = [d["type"] for d in designs]
        assert "registry" in types

    def test_detect_multiple_designs(self, engine):
        text = "A pivotal randomized controlled trial and a post-approval study were conducted"
        designs = engine.detect_study_designs(text)
        assert len(designs) >= 2

    def test_detect_bayesian(self, engine):
        text = "A Bayesian adaptive design was employed"
        designs = engine.detect_study_designs(text)
        types = [d["type"] for d in designs]
        assert "bayesian" in types

    def test_detect_sham_controlled(self, engine):
        text = "A sham-controlled trial was conducted"
        designs = engine.detect_study_designs(text)
        types = [d["type"] for d in designs]
        assert "sham_controlled" in types

    def test_detect_no_designs(self, engine):
        text = "The device was tested on the bench"
        designs = engine.detect_study_designs(text)
        assert len(designs) == 0

    def test_detect_empty_text(self, engine):
        designs = engine.detect_study_designs("")
        assert designs == []

    def test_designs_sorted_by_position(self, engine):
        text = "A registry study was first. Then a pivotal randomized controlled trial."
        designs = engine.detect_study_designs(text)
        positions = [d["position"] for d in designs]
        assert positions == sorted(positions)

    def test_design_confidence_scores(self, engine):
        text = "A pivotal randomized controlled trial was conducted"
        designs = engine.detect_study_designs(text)
        for d in designs:
            assert 0.0 <= d["confidence"] <= 1.0


class TestEnrollmentExtraction:
    """Test enrollment data extraction."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAIntelligenceEngine(store=store)

    def test_extract_enrollment_basic(self, engine):
        text = "The study enrolled 1,200 patients across 15 clinical sites"
        result = engine.extract_enrollment_data(text)
        assert result["total_enrollment"] == 1200
        assert result["confidence"] > 0.5

    def test_extract_enrollment_n_equals(self, engine):
        text = "The sample size was N = 500 subjects"
        result = engine.extract_enrollment_data(text)
        assert result["total_enrollment"] == 500

    def test_extract_enrollment_sample_size(self, engine):
        text = "The sample size of 350 patients was determined"
        result = engine.extract_enrollment_data(text)
        assert result["total_enrollment"] == 350

    def test_extract_enrollment_none(self, engine):
        text = "The device was tested on the bench"
        result = engine.extract_enrollment_data(text)
        assert result["total_enrollment"] is None
        assert result["confidence"] == 0.0

    def test_extract_enrollment_empty(self, engine):
        result = engine.extract_enrollment_data("")
        assert result["total_enrollment"] is None

    def test_extract_demographics_mentioned(self, engine):
        text = "The study enrolled 500 patients. Mean age was 65.3 years."
        result = engine.extract_enrollment_data(text)
        assert result["demographics_mentioned"] is True

    def test_extract_sites_mentioned(self, engine):
        text = "A multicenter study at 12 clinical sites enrolled 500 patients."
        result = engine.extract_enrollment_data(text)
        assert result["sites_mentioned"] is True

    def test_filter_small_numbers(self, engine):
        text = "The 3 investigators reviewed 5 cases"
        result = engine.extract_enrollment_data(text)
        assert result["total_enrollment"] is None  # 3 and 5 are too small


class TestEndpointExtraction:
    """Test endpoint extraction."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAIntelligenceEngine(store=store)

    def test_extract_primary_endpoint(self, engine):
        text = "The primary endpoint was device success rate at 12 months"
        result = engine.extract_endpoints(text)
        assert len(result["primary"]) >= 1
        assert "device success" in result["primary"][0]["text"].lower()

    def test_extract_secondary_endpoint(self, engine):
        text = "Secondary endpoints included all-cause mortality and readmission rate"
        result = engine.extract_endpoints(text)
        assert len(result["secondary"]) >= 1

    def test_extract_safety_endpoint(self, engine):
        text = "The primary safety endpoint was device-related serious adverse events at 30 days"
        result = engine.extract_endpoints(text)
        assert len(result["safety"]) >= 1

    def test_extract_no_endpoints(self, engine):
        text = "The device was tested on the bench with standard methods"
        result = engine.extract_endpoints(text)
        assert result["confidence"] < 0.5

    def test_extract_empty_text(self, engine):
        result = engine.extract_endpoints("")
        assert result["primary"] == []
        assert result["secondary"] == []
        assert result["safety"] == []


class TestEfficacyExtraction:
    """Test efficacy result extraction."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAIntelligenceEngine(store=store)

    def test_extract_success_rate(self, engine):
        text = "Device success rate of 92.5% was achieved"
        result = engine.extract_efficacy_results(text)
        rates = [r for r in result["results"] if r["type"] == "success_rate"]
        assert len(rates) >= 1
        assert rates[0]["value"] == 92.5

    def test_extract_p_value(self, engine):
        text = "The p-value was 0.001, demonstrating significance"
        result = engine.extract_efficacy_results(text)
        p_vals = [r for r in result["results"] if r["type"] == "p_value"]
        assert len(p_vals) >= 1
        assert p_vals[0]["significant"] is True

    def test_extract_p_value_not_significant(self, engine):
        text = "p = 0.12 was not statistically significant"
        result = engine.extract_efficacy_results(text)
        p_vals = [r for r in result["results"] if r["type"] == "p_value"]
        assert len(p_vals) >= 1
        assert p_vals[0]["significant"] is False

    def test_extract_sensitivity(self, engine):
        text = "Sensitivity was 95.2% and specificity was 88.7%"
        result = engine.extract_efficacy_results(text)
        sens = [r for r in result["results"] if r["type"] == "sensitivity"]
        spec = [r for r in result["results"] if r["type"] == "specificity"]
        assert len(sens) >= 1
        assert len(spec) >= 1
        assert sens[0]["value"] == 95.2
        assert spec[0]["value"] == 88.7

    def test_extract_ppa(self, engine):
        text = "Positive percent agreement (PPA) was 93.1%"
        result = engine.extract_efficacy_results(text)
        ppa = [r for r in result["results"] if r["type"] == "PPA"]
        assert len(ppa) >= 1
        assert ppa[0]["value"] == 93.1

    def test_extract_empty(self, engine):
        result = engine.extract_efficacy_results("")
        assert result["results"] == []
        assert result["confidence"] == 0.0


class TestAdverseEventExtraction:
    """Test adverse event extraction."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAIntelligenceEngine(store=store)

    def test_extract_ae_rate(self, engine):
        text = "The adverse event rate was 3.2% at 30 days"
        result = engine.extract_adverse_events(text)
        assert len(result["events"]) >= 1

    def test_extract_sae_rate(self, engine):
        text = "The SAE rate was 1.5% in the treatment group"
        result = engine.extract_adverse_events(text)
        assert len(result["events"]) >= 1

    def test_extract_specific_ae(self, engine):
        text = "Thrombosis: 2.1% of patients"
        result = engine.extract_adverse_events(text)
        thrombosis = [e for e in result["events"] if e.get("event") == "thrombosis"]
        assert len(thrombosis) >= 1

    def test_extract_total_ae_count(self, engine):
        text = "15 serious adverse events were reported during the study"
        result = engine.extract_adverse_events(text)
        assert result["total_ae_count"] == 15

    def test_extract_empty(self, engine):
        result = engine.extract_adverse_events("")
        assert result["events"] == []


class TestFollowUpExtraction:
    """Test follow-up duration extraction."""

    @pytest.fixture
    def engine(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return PMAIntelligenceEngine(store=store)

    def test_extract_follow_up_months(self, engine):
        text = "Follow-up of 24 months was completed"
        result = engine._extract_follow_up(text)
        assert result["duration"] == 24
        assert result["unit"] == "month"

    def test_extract_follow_up_years(self, engine):
        text = "Patients were followed for 5 years"
        result = engine._extract_follow_up(text)
        assert result["duration"] == 5
        assert result["unit"] == "year"

    def test_extract_follow_up_none(self, engine):
        text = "The device was tested on the bench"
        result = engine._extract_follow_up(text)
        assert result["duration"] is None


# ============================================================
# 3. TestSupplementAnalysis
# ============================================================


class TestSupplementAnalysis:
    """Test supplement analysis functionality."""

    @pytest.fixture
    def engine(self, tmp_path):
        mock_client = MagicMock()
        with patch("pma_data_store.FDAClient", return_value=mock_client):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            store.client = mock_client
            return PMAIntelligenceEngine(store=store)

    def test_analyze_supplements(self, engine):
        engine.store.get_supplements = MagicMock(return_value=SAMPLE_SUPPLEMENTS)
        result = engine.analyze_supplements("P170019")
        assert result["total_supplements"] == 4

    def test_categorize_supplements(self, engine):
        result = engine._categorize_supplements(SAMPLE_SUPPLEMENTS)
        assert "labeling" in result
        assert result["labeling"]["count"] >= 1

    def test_track_labeling_changes(self, engine):
        result = engine._track_labeling_changes(SAMPLE_SUPPLEMENTS)
        assert len(result) >= 2  # S029 and S028 are labeling

    def test_identify_post_approval_studies(self, engine):
        result = engine._identify_post_approval_studies(SAMPLE_SUPPLEMENTS)
        assert len(result) >= 1  # S005 is PAS

    def test_build_timeline(self, engine):
        timeline = engine._build_supplement_timeline(SAMPLE_SUPPLEMENTS)
        assert len(timeline) == 4
        # Should be sorted by date ascending
        dates = [t["date"] for t in timeline if t["date"]]
        assert dates == sorted(dates)

    def test_analyze_frequency(self, engine):
        freq = engine._analyze_supplement_frequency(SAMPLE_SUPPLEMENTS)
        assert freq["first_supplement_year"] == 2018
        assert freq["latest_supplement_year"] == 2021
        assert freq["years_active"] == 3
        assert freq["avg_per_year"] > 0

    def test_analyze_empty_supplements(self, engine):
        engine.store.get_supplements = MagicMock(return_value=[])
        result = engine.analyze_supplements("P170019")
        assert result["total_supplements"] == 0

    def test_supplement_type_coverage(self, engine):
        """Test that known supplement types are properly categorized."""
        result = engine._categorize_supplements(SAMPLE_SUPPLEMENTS)
        # At least labeling and design_change or manufacturing should be found
        total_categorized = sum(v["count"] for v in result.values())
        assert total_categorized == len(SAMPLE_SUPPLEMENTS)


# ============================================================
# 4. TestPredicateIntelligence
# ============================================================


class TestPredicateIntelligence:
    """Test predicate intelligence functionality."""

    @pytest.fixture
    def engine(self, tmp_path):
        mock_client = MagicMock()
        with patch("pma_data_store.FDAClient", return_value=mock_client):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            store.client = mock_client
            return PMAIntelligenceEngine(store=store)

    def test_find_comparable_pmas(self, engine):
        engine.store.client.search_pma.return_value = {
            "results": [
                {"pma_number": "P160035", "trade_name": "MSK-IMPACT",
                 "applicant": "MSK", "decision_date": "20171115", "product_code": "NMH"},
                {"pma_number": "P200024", "trade_name": "Tempus xT",
                 "applicant": "Tempus", "decision_date": "20200315", "product_code": "NMH"},
                {"pma_number": "P170019", "trade_name": "FoundationOne CDx",
                 "applicant": "Foundation", "decision_date": "20171130", "product_code": "NMH"},
            ],
        }
        result = engine._find_comparable_pmas("P170019", "NMH", "CH")
        # Should exclude P170019 itself
        pma_nums = [p["pma_number"] for p in result]
        assert "P170019" not in pma_nums
        assert "P160035" in pma_nums

    def test_find_citing_510ks(self, engine):
        engine.store.client.get_clearances.return_value = {
            "results": [
                {"k_number": "K241001", "device_name": "Gene Panel",
                 "applicant": "Company A", "decision_date": "20240615",
                 "clearance_type": "510(k)"},
            ],
        }
        result = engine._find_citing_510ks("P170019", "NMH")
        assert len(result) >= 1
        assert result[0]["k_number"] == "K241001"

    def test_find_comparable_no_product_code(self, engine):
        result = engine._find_comparable_pmas("P170019", "", "CH")
        assert result == []

    def test_assess_predicate_suitability_high(self, engine):
        engine.store.get_pma_data = MagicMock(return_value=SAMPLE_API_DATA)
        engine.store.get_extracted_sections = MagicMock(return_value=SAMPLE_SECTIONS)

        subject = {
            "product_code": "NMH",
            "intended_use": "indicated for tumor profiling in patients with cancer",
            "device_description": "NGS-based genomic profiling test",
        }
        result = engine.assess_predicate_suitability("P170019", subject)
        assert result["score"] > 0
        assert "pma_number" in result
        assert "factors" in result
        assert len(result["factors"]) > 0

    def test_assess_predicate_api_error(self, engine):
        engine.store.get_pma_data = MagicMock(return_value={"error": "Not found"})
        engine.store.get_extracted_sections = MagicMock(return_value=None)

        result = engine.assess_predicate_suitability("P999999", {"product_code": "NMH"})
        assert result["suitable"] is False
        assert result["score"] == 0


# ============================================================
# 5. TestPMACompareCommand
# ============================================================


class TestPMACompareCommandParsing:
    """Test pma-compare.md command file presence and structure."""

    def test_command_file_exists(self):
        cmd_path = os.path.join(
            os.path.dirname(__file__), "..", "commands", "pma-compare.md"
        )
        assert os.path.exists(cmd_path)

    def test_command_has_frontmatter(self):
        cmd_path = os.path.join(
            os.path.dirname(__file__), "..", "commands", "pma-compare.md"
        )
        with open(cmd_path) as f:
            content = f.read()
        assert content.startswith("---")
        assert "name: pma-compare" in content
        assert "description:" in content
        assert "allowed-tools:" in content

    def test_command_has_argument_hint(self):
        cmd_path = os.path.join(
            os.path.dirname(__file__), "..", "commands", "pma-compare.md"
        )
        with open(cmd_path) as f:
            content = f.read()
        assert "argument-hint:" in content
        assert "--primary" in content
        assert "--comparators" in content


# ============================================================
# 6. TestPMAIntelligenceCommand
# ============================================================


class TestPMAIntelligenceCommandParsing:
    """Test pma-intelligence.md command file presence and structure."""

    def test_command_file_exists(self):
        cmd_path = os.path.join(
            os.path.dirname(__file__), "..", "commands", "pma-intelligence.md"
        )
        assert os.path.exists(cmd_path)

    def test_command_has_frontmatter(self):
        cmd_path = os.path.join(
            os.path.dirname(__file__), "..", "commands", "pma-intelligence.md"
        )
        with open(cmd_path) as f:
            content = f.read()
        assert content.startswith("---")
        assert "name: pma-intelligence" in content
        assert "description:" in content

    def test_command_documents_focus_areas(self):
        cmd_path = os.path.join(
            os.path.dirname(__file__), "..", "commands", "pma-intelligence.md"
        )
        with open(cmd_path) as f:
            content = f.read()
        assert "clinical" in content
        assert "supplements" in content
        assert "predicates" in content


# ============================================================
# 7. TestIntegration -- Cross-module tests
# ============================================================


class TestComparisonIntegration:
    """Test comparison engine integration with data store."""

    @pytest.fixture
    def engine(self, tmp_path):
        mock_client = MagicMock()
        with patch("pma_data_store.FDAClient", return_value=mock_client):
            from pma_comparison import PMAComparisonEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            store.client = mock_client
            return PMAComparisonEngine(store=store)

    def test_load_pma_data_combines_sources(self, engine):
        engine.store.get_pma_data = MagicMock(return_value=SAMPLE_API_DATA)
        engine.store.get_extracted_sections = MagicMock(return_value=SAMPLE_SECTIONS)
        engine.store.get_supplements = MagicMock(return_value=SAMPLE_SUPPLEMENTS)

        data = engine._load_pma_data("P170019")
        assert data["api_data"]["pma_number"] == "P170019"
        assert data["sections"] is not None
        assert data["supplement_count"] == 4

    def test_get_section_text_from_nested_structure(self, engine):
        pma_data = {"sections": SAMPLE_SECTIONS}
        text = engine._get_section_text(pma_data, "clinical_studies")
        assert text is not None
        assert "pivotal" in text.lower()

    def test_get_section_text_none_sections(self, engine):
        pma_data = {"sections": None}
        text = engine._get_section_text(pma_data, "clinical_studies")
        assert text is None


class TestIntelligenceIntegration:
    """Test intelligence engine integration."""

    @pytest.fixture
    def engine(self, tmp_path):
        mock_client = MagicMock()
        with patch("pma_data_store.FDAClient", return_value=mock_client):
            from pma_intelligence import PMAIntelligenceEngine
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            store.client = mock_client
            return PMAIntelligenceEngine(store=store)

    def test_full_clinical_extraction(self, engine):
        """Test complete clinical intelligence extraction from sample text."""
        result = engine.extract_clinical_intelligence(
            "P170019",
            api_data=SAMPLE_API_DATA,
            sections=SAMPLE_SECTIONS,
        )
        assert result["has_clinical_data"] is True
        assert result["confidence"] > 0.0
        assert len(result["study_designs"]) > 0
        assert result["enrollment"]["total_enrollment"] == 1200
        assert len(result["efficacy_results"]["results"]) > 0

    def test_generate_executive_summary(self, engine):
        """Test executive summary generation."""
        report = {
            "device_summary": {
                "device_name": "Test Device",
                "applicant": "Test Company",
                "decision_date": "20230101",
            },
            "clinical_intelligence": {
                "has_clinical_data": True,
                "confidence": 0.75,
                "study_designs": [{"label": "Pivotal RCT", "confidence": 0.9}],
                "enrollment": {"total_enrollment": 500},
                "efficacy_results": {"total_metrics_extracted": 3},
            },
            "supplement_intelligence": {
                "total_supplements": 10,
                "labeling_changes": [1, 2],
                "post_approval_studies": [1],
            },
            "predicate_intelligence": {
                "comparable_pmas": [1, 2, 3],
                "citing_510ks": [1, 2],
            },
        }

        summary = engine._generate_executive_summary(report)
        assert len(summary["key_findings"]) > 0
        assert summary["clinical_data_available"] is True
        assert summary["total_supplements"] == 10

    def test_clinical_extraction_no_sections(self, engine):
        """Test clinical extraction when no sections available."""
        result = engine.extract_clinical_intelligence(
            "P170019",
            api_data=SAMPLE_API_DATA,
            sections=None,
        )
        assert result["has_clinical_data"] is False
        assert result["confidence"] == 0.0


class TestCLIInterface:
    """Test CLI interfaces for both modules."""

    def test_comparison_cli_no_args(self):
        from pma_comparison import main
        with patch("sys.argv", ["pma_comparison.py"]):
            with pytest.raises(SystemExit):
                main()

    def test_intelligence_cli_no_args(self):
        from pma_intelligence import main
        with patch("sys.argv", ["pma_intelligence.py"]):
            with pytest.raises(SystemExit):
                main()


class TestDimensionWeights:
    """Test that dimension weights are properly configured."""

    def test_weights_sum_to_one(self):
        from pma_comparison import DIMENSION_WEIGHTS
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_dimensions_have_weights(self):
        from pma_comparison import DIMENSION_WEIGHTS, DIMENSION_SECTIONS
        for dim in DIMENSION_SECTIONS:
            assert dim in DIMENSION_WEIGHTS

    def test_all_dimensions_have_sections(self):
        from pma_comparison import DIMENSION_WEIGHTS, DIMENSION_SECTIONS
        for dim in DIMENSION_WEIGHTS:
            assert dim in DIMENSION_SECTIONS


class TestSimilarityThresholds:
    """Test similarity threshold configuration."""

    def test_threshold_ordering(self):
        from pma_comparison import SIMILARITY_HIGH, SIMILARITY_MODERATE, SIMILARITY_LOW
        assert SIMILARITY_HIGH > SIMILARITY_MODERATE > SIMILARITY_LOW

    def test_threshold_values(self):
        from pma_comparison import SIMILARITY_HIGH, SIMILARITY_MODERATE, SIMILARITY_LOW
        assert SIMILARITY_HIGH == 75
        assert SIMILARITY_MODERATE == 50
        assert SIMILARITY_LOW == 25
