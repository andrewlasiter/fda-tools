"""Tests for FE-009: Similarity Method Auto-Selection (FDA-39).

Validates the auto_select_similarity_method() heuristic and the --method auto
integration with compute_similarity() and pairwise_similarity_matrix().

Test coverage:
    - Short text pairs (<100 words avg) -> jaccard
    - Long structured texts (low diversity) -> sequence
    - Mixed-length / high-diversity texts -> cosine
    - compute_similarity(method='auto') dispatches correctly
    - pairwise_similarity_matrix with method='auto'
    - Edge cases: empty text, identical text, single-word texts
"""

import sys
from pathlib import Path

import pytest

from section_analytics import (  # type: ignore
    auto_select_similarity_method,
    compute_similarity,
    pairwise_similarity_matrix,
)


# ============================================================================
# Test Data
# ============================================================================

# Short texts: <100 words each -> should select jaccard
SHORT_TEXT_A = "Biocompatibility testing per ISO 10993-1 and ISO 10993-5."
SHORT_TEXT_B = "ISO 10993-1 biocompatibility evaluation was performed."

# Long structured texts with repetitive vocabulary (low diversity) -> sequence
LONG_STRUCTURED_A = (
    "Clinical testing per ISO 10993-5 cytotoxicity was performed on the device "
    "materials. The testing included in vitro cytotoxicity assays, sensitization "
    "studies per ISO 10993-10, and irritation evaluations. All results demonstrated "
    "biocompatibility within acceptable limits as defined by the referenced standards. "
    "The device components were tested in direct and indirect contact configurations "
    "to evaluate potential cytotoxic effects on cell cultures. Testing was repeated "
    "for each device material per ISO 10993-5 cytotoxicity protocol. The testing "
    "results for cytotoxicity and sensitization per ISO 10993-10 confirmed the "
    "biocompatibility of all tested materials. The device testing included "
    "cytotoxicity testing per ISO 10993-5 and ISO 10993-10 sensitization testing."
)

LONG_STRUCTURED_B = (
    "Clinical evaluation included ISO 10993-5 cytotoxicity and ISO 10993-10 "
    "sensitization testing. Additional genotoxicity testing was performed per "
    "ISO 10993-3 to assess mutagenic potential. The comprehensive testing battery "
    "demonstrated that the device materials do not elicit adverse biological "
    "responses when used as intended. Supplementary implantation testing per "
    "ISO 10993-6 confirmed tissue compatibility for long-term implantation "
    "applications. The testing per ISO 10993-5 cytotoxicity and the testing "
    "per ISO 10993-10 sensitization were performed on all materials. The "
    "device materials testing per ISO 10993-5 confirmed cytotoxicity results. "
    "Additional testing for ISO 10993-10 sensitization was also completed."
)

# High-diversity texts (varied vocabulary) -> cosine
HIGH_DIVERSITY_A = (
    "The cardiovascular stent delivery catheter employs a novel polymer coating "
    "incorporating sirolimus-eluting technology for sustained pharmacological "
    "intervention. Angiographic assessment demonstrated luminal diameter "
    "preservation with minimal neointimal hyperplasia at six-month follow-up "
    "across a heterogeneous patient population encompassing diverse comorbidities "
    "including diabetes mellitus, hypertension, and chronic kidney disease. "
    "Quantitative coronary analysis revealed statistically significant reductions "
    "in target lesion revascularization compared to historical bare-metal controls."
)

HIGH_DIVERSITY_B = (
    "An orthopedic spinal fusion system comprising pedicle screws manufactured "
    "from titanium alloy with hydroxyapatite surface treatment, interconnecting "
    "rods featuring ergonomic locking mechanisms, and transverse connectors for "
    "supplementary stabilization. Biomechanical evaluation demonstrated superior "
    "pullout strength characteristics across osteoporotic bone density specimens. "
    "Finite element analysis corroborated experimental findings regarding stress "
    "distribution patterns within vertebral body constructs under physiological "
    "loading conditions representative of ambulatory and recumbent postures."
)


# ============================================================================
# Auto-Selection Heuristic Tests
# ============================================================================


class TestAutoSelectMethod:
    """Test suite for auto_select_similarity_method() heuristic."""

    def test_short_texts_select_jaccard(self):
        """Short texts (<100 words avg) should select jaccard."""
        method = auto_select_similarity_method(SHORT_TEXT_A, SHORT_TEXT_B)
        assert method == "jaccard", (
            f"Expected 'jaccard' for short texts, got '{method}'"
        )

    def test_long_structured_texts_select_sequence(self):
        """Long structured texts with low diversity should select sequence."""
        method = auto_select_similarity_method(LONG_STRUCTURED_A, LONG_STRUCTURED_B)
        assert method == "sequence", (
            f"Expected 'sequence' for long structured texts, got '{method}'"
        )

    def test_high_diversity_texts_select_cosine(self):
        """High-diversity texts should select cosine."""
        method = auto_select_similarity_method(HIGH_DIVERSITY_A, HIGH_DIVERSITY_B)
        assert method == "cosine", (
            f"Expected 'cosine' for high-diversity texts, got '{method}'"
        )

    def test_empty_texts_select_jaccard(self):
        """Empty texts have 0 words -> should select jaccard (short text rule)."""
        method = auto_select_similarity_method("", "")
        assert method == "jaccard"

    def test_one_empty_one_short_select_jaccard(self):
        """One empty text and one short text -> should select jaccard."""
        method = auto_select_similarity_method("", "hello world test")
        assert method == "jaccard"

    def test_single_word_texts_select_jaccard(self):
        """Single-word texts are short -> should select jaccard."""
        method = auto_select_similarity_method("biocompatibility", "cytotoxicity")
        assert method == "jaccard"

    def test_identical_long_texts_select_sequence(self):
        """Identical long texts have zero diversity after dedup -> sequence."""
        long_text = " ".join(["testing", "device", "materials"] * 50)
        method = auto_select_similarity_method(long_text, long_text)
        assert method == "sequence", (
            f"Expected 'sequence' for identical repetitive long texts, got '{method}'"
        )

    def test_return_type_is_string(self):
        """auto_select_similarity_method always returns a string."""
        result = auto_select_similarity_method("a", "b")
        assert isinstance(result, str)

    def test_return_value_is_valid_method(self):
        """Return value must be one of the three valid methods."""
        result = auto_select_similarity_method(SHORT_TEXT_A, SHORT_TEXT_B)
        assert result in {"jaccard", "sequence", "cosine"}

    def test_medium_length_diverse_text_selects_cosine(self):
        """Texts around 100 words with diverse vocab should select cosine."""
        # Build two texts of ~120 words each with high diversity
        words_a = [f"word{i}" for i in range(120)]
        words_b = [f"term{i}" for i in range(120)]
        text_a = " ".join(words_a)
        text_b = " ".join(words_b)
        method = auto_select_similarity_method(text_a, text_b)
        assert method == "cosine", (
            f"Expected 'cosine' for diverse medium-length texts, got '{method}'"
        )


# ============================================================================
# compute_similarity with method='auto' Tests
# ============================================================================


class TestComputeSimilarityAuto:
    """Test that compute_similarity(method='auto') dispatches correctly."""

    def test_auto_method_returns_float(self):
        """compute_similarity with method='auto' returns a float score."""
        score = compute_similarity(SHORT_TEXT_A, SHORT_TEXT_B, method="auto")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_auto_method_short_texts_matches_jaccard(self):
        """For short texts, auto should produce the same score as jaccard."""
        auto_score = compute_similarity(SHORT_TEXT_A, SHORT_TEXT_B, method="auto")
        jaccard_score = compute_similarity(SHORT_TEXT_A, SHORT_TEXT_B, method="jaccard")
        assert auto_score == pytest.approx(jaccard_score, abs=1e-6), (
            f"Auto ({auto_score}) != Jaccard ({jaccard_score}) for short texts"
        )

    def test_auto_method_long_structured_matches_sequence(self):
        """For long structured texts, auto should match sequence method."""
        auto_score = compute_similarity(
            LONG_STRUCTURED_A, LONG_STRUCTURED_B, method="auto"
        )
        sequence_score = compute_similarity(
            LONG_STRUCTURED_A, LONG_STRUCTURED_B, method="sequence"
        )
        assert auto_score == pytest.approx(sequence_score, abs=1e-6), (
            f"Auto ({auto_score}) != Sequence ({sequence_score}) for structured texts"
        )

    def test_auto_method_high_diversity_matches_cosine(self):
        """For high-diversity texts, auto should match cosine method."""
        auto_score = compute_similarity(
            HIGH_DIVERSITY_A, HIGH_DIVERSITY_B, method="auto"
        )
        cosine_score = compute_similarity(
            HIGH_DIVERSITY_A, HIGH_DIVERSITY_B, method="cosine"
        )
        assert auto_score == pytest.approx(cosine_score, abs=1e-6), (
            f"Auto ({auto_score}) != Cosine ({cosine_score}) for diverse texts"
        )

    def test_auto_method_empty_text_returns_zero(self):
        """Empty text with auto method returns 0.0."""
        score = compute_similarity("", "some text", method="auto")
        assert score == 0.0

    def test_auto_method_identical_texts_returns_high_score(self):
        """Identical texts with auto should return a high similarity score."""
        text = "Device biocompatibility testing per ISO 10993-1 standard."
        score = compute_similarity(text, text, method="auto")
        assert score > 0.9


# ============================================================================
# pairwise_similarity_matrix with method='auto' Tests
# ============================================================================


class TestPairwiseMatrixAuto:
    """Test pairwise_similarity_matrix with method='auto'."""

    @pytest.fixture
    def section_data_short(self):
        """Section data with short texts -> should trigger jaccard."""
        return {
            "K001": {
                "sections": {
                    "biocompatibility": {
                        "text": "ISO 10993-1 biocompatibility.",
                        "word_count": 4,
                        "standards": ["ISO 10993-1"],
                    }
                },
                "decision_date": "20240101",
            },
            "K002": {
                "sections": {
                    "biocompatibility": {
                        "text": "Biocompatibility per ISO 10993-5.",
                        "word_count": 5,
                        "standards": ["ISO 10993-5"],
                    }
                },
                "decision_date": "20240201",
            },
            "K003": {
                "sections": {
                    "biocompatibility": {
                        "text": "ISO 10993-10 sensitization testing.",
                        "word_count": 4,
                        "standards": ["ISO 10993-10"],
                    }
                },
                "decision_date": "20240301",
            },
        }

    def test_pairwise_auto_produces_valid_result(self, section_data_short):
        """pairwise_similarity_matrix with auto should return valid result dict."""
        result = pairwise_similarity_matrix(
            section_data_short,
            "biocompatibility",
            method="auto",
            use_cache=False,
        )

        assert result["method"] == "auto"
        assert result["devices_compared"] == 3
        assert result["pairs_computed"] == 3  # C(3,2) = 3
        assert 0.0 <= result["statistics"]["mean"] <= 1.0

    def test_pairwise_auto_all_scores_valid(self, section_data_short):
        """All pairwise scores should be between 0.0 and 1.0."""
        result = pairwise_similarity_matrix(
            section_data_short,
            "biocompatibility",
            method="auto",
            use_cache=False,
        )

        for k1, k2, score in result["scores"]:
            assert 0.0 <= score <= 1.0, (
                f"Score {score} for {k1}-{k2} is out of [0, 1] range"
            )


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.scripts,
    pytest.mark.sim,
]
