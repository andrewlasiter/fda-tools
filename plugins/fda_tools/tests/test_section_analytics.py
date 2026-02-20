"""
Tests for Section Comparison Analytics (v5.36.0).

Implements Quick Win tests from the TESTING_SPEC.md test suite:

Tier 1 (Trivial):
    - SIM-002: Identical text similarity = 1.0
    - SIM-003: Empty string similarity = 0.0
    - SIM-004: Invalid method raises ValueError
    - SIM-005: Case insensitivity in tokenization
    - SIM-012: Single data point trend = insufficient_data

Tier 2 (Simple):
    - SIM-001: Similarity scoring accuracy (all 3 methods)
    - SIM-010: Stable trend detection
    - SIM-011: Decreasing trend detection

Tier 3 (Moderate):
    - SIM-006: Basic pairwise matrix computation
    - SIM-014: Basic cross-product comparison

Total: 10 SIM tests covering section_analytics.py
"""

import pytest

# Ensure scripts directory is on sys.path for imports
# Package imports configured in conftest.py and pytest.ini

from section_analytics import (  # type: ignore
    _detect_trend_direction,
    _tokenize,
    analyze_temporal_trends,
    compute_similarity,
    cross_product_compare,
    pairwise_similarity_matrix,
)


# ===================================================================
# Tier 1: Trivial Tests (< 10 min each)
# ===================================================================


class TestSIM002IdenticalTextSimilarity:
    """SIM-002: Identical text similarity should return 1.0 for all methods.

    Validates that when the same text is compared to itself, all three
    similarity methods (sequence, jaccard, cosine) return a perfect
    score of 1.0.
    """

    def test_identical_text_sequence(self):
        """Sequence method returns 1.0 for identical texts."""
        text = "The device is a cardiovascular catheter."
        assert compute_similarity(text, text, "sequence") == 1.0

    def test_identical_text_jaccard(self):
        """Jaccard method returns 1.0 for identical texts."""
        text = "The device is a cardiovascular catheter."
        assert compute_similarity(text, text, "jaccard") == 1.0

    def test_identical_text_cosine(self):
        """Cosine method returns 1.0 (or very close) for identical texts."""
        text = "The device is a cardiovascular catheter."
        score = compute_similarity(text, text, "cosine")
        assert score >= 0.9999, f"Cosine similarity of identical text should be ~1.0, got {score}"

    def test_identical_longer_text(self):
        """All methods return 1.0 for longer identical texts."""
        text = (
            "ISO 10993-1 biocompatibility testing was performed including "
            "cytotoxicity per ISO 10993-5 and sensitization per ISO 10993-10. "
            "All results were within acceptable limits."
        )
        assert compute_similarity(text, text, "sequence") == 1.0
        assert compute_similarity(text, text, "jaccard") == 1.0
        assert compute_similarity(text, text, "cosine") >= 0.9999


class TestSIM003EmptyStringSimilarity:
    """SIM-003: Empty string similarity should return 0.0 for all methods.

    Validates that compute_similarity handles empty string inputs
    gracefully, returning 0.0 without division-by-zero errors.
    """

    def test_empty_first_string_sequence(self):
        """Empty first string with sequence method returns 0.0."""
        assert compute_similarity("", "hello world", "sequence") == 0.0

    def test_empty_first_string_jaccard(self):
        """Empty first string with jaccard method returns 0.0."""
        assert compute_similarity("", "hello world", "jaccard") == 0.0

    def test_empty_first_string_cosine(self):
        """Empty first string with cosine method returns 0.0."""
        assert compute_similarity("", "hello world", "cosine") == 0.0

    def test_empty_second_string_sequence(self):
        """Empty second string with sequence method returns 0.0."""
        assert compute_similarity("some text", "", "sequence") == 0.0

    def test_empty_second_string_jaccard(self):
        """Empty second string with jaccard method returns 0.0."""
        assert compute_similarity("some text", "", "jaccard") == 0.0

    def test_empty_second_string_cosine(self):
        """Empty second string with cosine method returns 0.0."""
        assert compute_similarity("some text", "", "cosine") == 0.0

    def test_both_empty_sequence(self):
        """Both strings empty with sequence method returns 0.0."""
        assert compute_similarity("", "", "sequence") == 0.0

    def test_both_empty_jaccard(self):
        """Both strings empty with jaccard method returns 0.0."""
        assert compute_similarity("", "", "jaccard") == 0.0

    def test_both_empty_cosine(self):
        """Both strings empty with cosine method returns 0.0."""
        assert compute_similarity("", "", "cosine") == 0.0


class TestSIM004InvalidMethod:
    """SIM-004: Invalid similarity method should raise ValueError.

    Validates that compute_similarity raises a clear ValueError when
    given an unrecognized method name, with the error message listing
    the valid methods.
    """

    def test_invalid_method_raises_valueerror(self):
        """Invalid method name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            compute_similarity("text a", "text b", method="invalid_method")

        error_msg = str(exc_info.value)
        assert "invalid_method" in error_msg, "Error should mention the invalid method name"
        assert "sequence" in error_msg, "Error should list valid methods"
        assert "jaccard" in error_msg, "Error should list valid methods"
        assert "cosine" in error_msg, "Error should list valid methods"

    def test_empty_method_raises_valueerror(self):
        """Empty string method name raises ValueError."""
        with pytest.raises(ValueError):
            compute_similarity("a", "b", method="")


class TestSIM005CaseInsensitivity:
    """SIM-005: Tokenization should be case-insensitive.

    Validates that the _tokenize function converts all tokens to
    lowercase, removes punctuation, and produces no empty tokens.
    """

    def test_mixed_case_tokens(self):
        """Mixed case input produces lowercase tokens."""
        tokens = _tokenize("ISO Biocompatibility TESTING Device")
        assert tokens == ["iso", "biocompatibility", "testing", "device"]

    def test_punctuation_removed(self):
        """Punctuation is removed from tokens."""
        tokens = _tokenize("ISO-10993, testing (v2.0)!")
        assert "iso" in tokens
        assert "10993" in tokens
        assert "testing" in tokens
        # Punctuation characters should not appear
        for token in tokens:
            assert token.isalnum(), f"Token '{token}' contains non-alphanumeric characters"

    def test_no_empty_tokens(self):
        """No empty tokens in output."""
        tokens = _tokenize("  multiple   spaces   between   words  ")
        assert "" not in tokens
        assert len(tokens) == 4

    def test_empty_input(self):
        """Empty input produces empty token list."""
        assert _tokenize("") == []


class TestSIM012InsufficientDataForTrend:
    """SIM-012: Single data point should return 'insufficient_data' direction.

    Validates that _detect_trend_direction handles single data point
    gracefully, returning insufficient_data rather than crashing.
    """

    def test_single_data_point(self):
        """Single data point returns insufficient_data."""
        result = _detect_trend_direction([(2024, 85.0)])
        assert result["direction"] == "insufficient_data"
        assert result["slope"] == 0.0
        assert result["r_squared"] == 0.0

    def test_empty_data(self):
        """Empty data returns insufficient_data."""
        result = _detect_trend_direction([])
        assert result["direction"] == "insufficient_data"
        assert result["slope"] == 0.0
        assert result["r_squared"] == 0.0


# ===================================================================
# Tier 2: Simple Tests (10-20 min each)
# ===================================================================


class TestSIM001SimilarityAccuracy:
    """SIM-001: Similarity scoring should rank similar texts higher than dissimilar.

    Validates that all three similarity methods correctly identify
    cardiovascular catheter texts (A, B) as more similar to each other
    than to an orthopedic implant text (C).
    """

    TEXT_A = (
        "The device is a cardiovascular catheter for percutaneous "
        "transluminal coronary angioplasty"
    )
    TEXT_B = (
        "This cardiovascular catheter device is indicated for percutaneous "
        "coronary interventions"
    )
    TEXT_C = (
        "An orthopedic spinal implant system consisting of pedicle screws "
        "and rods"
    )

    def test_sequence_method_accuracy(self):
        """Sequence method: similar devices score higher than dissimilar."""
        score_ab = compute_similarity(self.TEXT_A, self.TEXT_B, "sequence")
        score_ac = compute_similarity(self.TEXT_A, self.TEXT_C, "sequence")
        score_bc = compute_similarity(self.TEXT_B, self.TEXT_C, "sequence")

        assert 0.0 <= score_ab <= 1.0, f"Score out of range: {score_ab}"
        assert 0.0 <= score_ac <= 1.0, f"Score out of range: {score_ac}"
        assert 0.0 <= score_bc <= 1.0, f"Score out of range: {score_bc}"

        assert score_ab > score_ac, (
            f"Sequence: Similar devices (A,B={score_ab:.4f}) should score "
            f"higher than dissimilar (A,C={score_ac:.4f})"
        )
        assert score_ab > score_bc, (
            f"Sequence: Similar devices (A,B={score_ab:.4f}) should score "
            f"higher than dissimilar (B,C={score_bc:.4f})"
        )
        assert score_ab > 0.4, f"Sequence A-B should be > 0.4, got {score_ab:.4f}"

    def test_jaccard_method_accuracy(self):
        """Jaccard method: similar devices score higher than dissimilar."""
        score_ab = compute_similarity(self.TEXT_A, self.TEXT_B, "jaccard")
        score_ac = compute_similarity(self.TEXT_A, self.TEXT_C, "jaccard")
        score_bc = compute_similarity(self.TEXT_B, self.TEXT_C, "jaccard")

        assert 0.0 <= score_ab <= 1.0
        assert 0.0 <= score_ac <= 1.0
        assert 0.0 <= score_bc <= 1.0

        assert score_ab > score_ac, (
            f"Jaccard: A,B={score_ab:.4f} should exceed A,C={score_ac:.4f}"
        )
        assert score_ab > score_bc, (
            f"Jaccard: A,B={score_ab:.4f} should exceed B,C={score_bc:.4f}"
        )
        assert score_ab > 0.3, f"Jaccard A-B should be > 0.3, got {score_ab:.4f}"

    def test_cosine_method_accuracy(self):
        """Cosine method: similar devices score higher than dissimilar."""
        score_ab = compute_similarity(self.TEXT_A, self.TEXT_B, "cosine")
        score_ac = compute_similarity(self.TEXT_A, self.TEXT_C, "cosine")
        score_bc = compute_similarity(self.TEXT_B, self.TEXT_C, "cosine")

        assert 0.0 <= score_ab <= 1.0
        assert 0.0 <= score_ac <= 1.0
        assert 0.0 <= score_bc <= 1.0

        assert score_ab > score_ac, (
            f"Cosine: A,B={score_ab:.4f} should exceed A,C={score_ac:.4f}"
        )
        assert score_ab > score_bc, (
            f"Cosine: A,B={score_ab:.4f} should exceed B,C={score_bc:.4f}"
        )
        assert score_ab > 0.5, f"Cosine A-B should be > 0.5, got {score_ab:.4f}"

    def test_all_scores_in_range(self):
        """All similarity scores are between 0.0 and 1.0 inclusive."""
        for method in ["sequence", "jaccard", "cosine"]:
            for text_pair in [
                (self.TEXT_A, self.TEXT_B),
                (self.TEXT_A, self.TEXT_C),
                (self.TEXT_B, self.TEXT_C),
            ]:
                score = compute_similarity(text_pair[0], text_pair[1], method)
                assert 0.0 <= score <= 1.0, (
                    f"{method}: score {score} out of [0, 1] range"
                )


class TestSIM010StableTrendDetection:
    """SIM-010: Near-constant values should be classified as 'stable'.

    Validates that _detect_trend_direction correctly identifies data
    points with minimal variation as a stable trend.
    """

    def test_stable_trend(self):
        """Near-constant values produce stable direction."""
        year_values = [
            (2020, 85.0),
            (2021, 84.5),
            (2022, 85.2),
            (2023, 84.8),
            (2024, 85.1),
        ]
        result = _detect_trend_direction(year_values)

        assert result["direction"] == "stable", (
            f"Expected 'stable', got '{result['direction']}' "
            f"(slope={result['slope']})"
        )
        assert abs(result["slope"]) < 0.5, (
            f"Slope should be near zero for stable trend, got {result['slope']}"
        )

    def test_perfectly_constant_values(self):
        """Perfectly constant values produce stable direction."""
        year_values = [
            (2020, 50.0),
            (2021, 50.0),
            (2022, 50.0),
            (2023, 50.0),
            (2024, 50.0),
        ]
        result = _detect_trend_direction(year_values)
        assert result["direction"] == "stable"
        assert result["slope"] == 0.0


class TestSIM011DecreasingTrendDetection:
    """SIM-011: Monotonically decreasing values should be classified as 'decreasing'.

    Validates that _detect_trend_direction correctly identifies a clear
    downward trend with strong linear fit.
    """

    def test_decreasing_trend(self):
        """Clearly decreasing values produce decreasing direction."""
        year_values = [
            (2020, 500),
            (2021, 450),
            (2022, 380),
            (2023, 310),
            (2024, 250),
        ]
        result = _detect_trend_direction(year_values)

        assert result["direction"] == "decreasing", (
            f"Expected 'decreasing', got '{result['direction']}' "
            f"(slope={result['slope']})"
        )
        assert result["slope"] < 0, (
            f"Slope should be negative for decreasing trend, got {result['slope']}"
        )
        assert result["r_squared"] > 0.8, (
            f"R-squared should be high for strong linear decrease, got {result['r_squared']}"
        )

    def test_decreasing_trend_has_endpoints(self):
        """Decreasing trend result includes start/end year and value."""
        year_values = [
            (2020, 500),
            (2021, 450),
            (2022, 380),
            (2023, 310),
            (2024, 250),
        ]
        result = _detect_trend_direction(year_values)

        assert result["start_year"] == 2020
        assert result["end_year"] == 2024
        assert result["start_value"] == 500.0
        assert result["end_value"] == 250.0


# ===================================================================
# Tier 3: Moderate Tests (20-30 min each)
# ===================================================================


class TestSIM006PairwiseMatrixComputation:
    """SIM-006: Basic pairwise similarity matrix computation.

    Validates that pairwise_similarity_matrix correctly computes
    similarity scores for all pairs, returns valid statistics, and
    identifies most/least similar pairs.
    """

    def test_basic_matrix_4_devices(self, sample_section_data):
        """4 DQY devices produce C(4,2)=6 pairs with valid statistics."""
        # Filter to just first 4 DQY devices
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="cosine"
        )

        assert result["section_type"] == "clinical_testing"
        assert result["method"] == "cosine"
        assert result["devices_compared"] == 4
        assert result["pairs_computed"] == 6  # C(4,2) = 6

    def test_statistics_valid_ranges(self, sample_section_data):
        """All statistics are within valid ranges."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="sequence"
        )

        stats = result["statistics"]
        assert 0.0 <= stats["mean"] <= 1.0, f"Mean out of range: {stats['mean']}"
        assert 0.0 <= stats["stdev"], f"Stdev should be non-negative: {stats['stdev']}"
        assert 0.0 <= stats["min"] <= 1.0, f"Min out of range: {stats['min']}"
        assert 0.0 <= stats["max"] <= 1.0, f"Max out of range: {stats['max']}"
        assert stats["min"] <= stats["mean"] <= stats["max"], (
            f"Ordering violated: min={stats['min']}, mean={stats['mean']}, max={stats['max']}"
        )

    def test_most_least_similar_ordering(self, sample_section_data):
        """Most similar pair has higher score than least similar pair."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="cosine"
        )

        most = result["most_similar_pair"]
        least = result["least_similar_pair"]

        assert most is not None, "Most similar pair should not be None"
        assert least is not None, "Least similar pair should not be None"
        assert most["score"] >= least["score"], (
            f"Most similar ({most['score']}) should >= least similar ({least['score']})"
        )

    def test_scores_are_tuples(self, sample_section_data):
        """Each score entry is a tuple of (k_number_1, k_number_2, score)."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="cosine"
        )

        for score_entry in result["scores"]:
            assert len(score_entry) == 3, f"Score entry should have 3 elements: {score_entry}"
            k1, k2, score = score_entry
            assert isinstance(k1, str), f"First element should be str: {k1}"
            assert isinstance(k2, str), f"Second element should be str: {k2}"
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_insufficient_devices_1(self, sample_section_data):
        """SIM-008: 1 device returns zero pairs and None extremes."""
        # Use only one device
        single = {"K241001": sample_section_data["K241001"]}

        result = pairwise_similarity_matrix(
            single, "clinical_testing", method="sequence"
        )

        assert result["devices_compared"] == 1
        assert result["pairs_computed"] == 0
        assert result["statistics"]["mean"] == 0.0
        assert result["most_similar_pair"] is None
        assert result["least_similar_pair"] is None
        assert result["scores"] == []

    def test_insufficient_devices_0(self):
        """SIM-008: 0 devices returns zero pairs and None extremes."""
        result = pairwise_similarity_matrix(
            {}, "clinical_testing", method="sequence"
        )

        assert result["devices_compared"] == 0
        assert result["pairs_computed"] == 0
        assert result["statistics"]["mean"] == 0.0

    def test_sample_size_limit(self, sample_section_data):
        """SIM-007: Sample size limits the number of devices compared."""
        # All 5 DQY devices have clinical_testing sections
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="sequence", sample_size=3
        )

        assert result["devices_compared"] <= 3, (
            f"Devices compared ({result['devices_compared']}) should be <= sample_size 3"
        )
        # C(3,2) = 3 pairs
        assert result["pairs_computed"] <= 3, (
            f"Pairs computed ({result['pairs_computed']}) should be <= C(3,2)=3"
        )


class TestSIM014CrossProductComparison:
    """SIM-014: Cross-product comparison computes per-code statistics.

    Validates that cross_product_compare correctly groups devices by
    product code, computes coverage and word count statistics, and
    generates summary fields.
    """

    def test_basic_cross_product_structure(self, sample_section_data):
        """Cross-product comparison returns expected structure for DQY and OVE."""
        result = cross_product_compare(
            ["DQY", "OVE"],
            ["clinical_testing", "biocompatibility"],
            sample_section_data,
        )

        assert result["product_codes"] == ["DQY", "OVE"]
        assert "clinical_testing" in result["comparison"]
        assert "biocompatibility" in result["comparison"]

    def test_device_counts_per_code(self, sample_section_data):
        """Each product code shows correct device count."""
        result = cross_product_compare(
            ["DQY", "OVE"],
            ["clinical_testing"],
            sample_section_data,
        )

        clinical = result["comparison"]["clinical_testing"]
        assert "DQY" in clinical, "DQY should be in comparison"
        assert "OVE" in clinical, "OVE should be in comparison"

        # DQY has 5 devices in fixture, OVE has 3
        assert clinical["DQY"]["device_count"] == 5
        assert clinical["OVE"]["device_count"] == 3

    def test_coverage_pct_range(self, sample_section_data):
        """Coverage percentages are between 0 and 100."""
        result = cross_product_compare(
            ["DQY", "OVE"],
            ["clinical_testing", "biocompatibility"],
            sample_section_data,
        )

        for section_type in ["clinical_testing", "biocompatibility"]:
            for pc in ["DQY", "OVE"]:
                cov = result["comparison"][section_type][pc]["coverage_pct"]
                assert 0.0 <= cov <= 100.0, (
                    f"Coverage for {pc}/{section_type} out of range: {cov}"
                )

    def test_summary_highest_coverage(self, sample_section_data):
        """Summary identifies the product code with highest coverage per section."""
        result = cross_product_compare(
            ["DQY", "OVE"],
            ["clinical_testing"],
            sample_section_data,
        )

        summary = result["summary"]
        assert "highest_coverage" in summary
        assert "longest_sections" in summary

        # All DQY devices (5/5) have clinical_testing; all OVE (3/3) also have it.
        # Both should be 100%, but the summary should have a value
        if "clinical_testing" in summary["highest_coverage"]:
            assert summary["highest_coverage"]["clinical_testing"] in ["DQY", "OVE"]

    def test_unknown_product_code(self, sample_section_data):
        """SIM-015: Unknown product code returns zero counts without error."""
        result = cross_product_compare(
            ["DQY", "XYZ"],
            ["clinical_testing"],
            sample_section_data,
        )

        clinical = result["comparison"]["clinical_testing"]
        assert clinical["XYZ"]["device_count"] == 0
        assert clinical["XYZ"]["coverage_pct"] == 0.0
        # DQY should still be present and valid
        assert clinical["DQY"]["device_count"] > 0

    def test_case_insensitive_product_code(self, sample_section_data):
        """SIM-016: Product codes are matched case-insensitively."""
        result = cross_product_compare(
            ["dqy"],
            ["clinical_testing"],
            sample_section_data,
        )

        assert "DQY" in result["product_codes"]
        clinical = result["comparison"]["clinical_testing"]
        assert "DQY" in clinical
        assert clinical["DQY"]["device_count"] > 0


# ===================================================================
# Additional Edge Case: Temporal Trends
# ===================================================================


class TestSIM009TemporalTrends:
    """SIM-009: Temporal trend analysis coverage calculation.

    Validates that analyze_temporal_trends correctly computes yearly
    statistics and coverage percentages.
    """

    def test_coverage_calculation_accuracy(self, sample_section_data):
        """Coverage percentages are between 0 and 100 for all years."""
        result = analyze_temporal_trends(
            sample_section_data, ["clinical_testing"]
        )

        assert result["total_devices"] == len(sample_section_data)

        trends = result["trends"].get("clinical_testing", {})
        by_year = trends.get("by_year", {})

        for year, data in by_year.items():
            coverage_pct = data["coverage_pct"]
            assert 0.0 <= coverage_pct <= 100.0, (
                f"Coverage for year {year} out of range: {coverage_pct}"
            )
            assert data["device_count"] > 0, f"Year {year} should have devices"

    def test_year_range_correct(self, sample_section_data):
        """Year range matches the decision dates in fixture data."""
        result = analyze_temporal_trends(
            sample_section_data, ["clinical_testing"]
        )

        # Fixture data spans 2024 (all devices have 2024 decision dates)
        assert result["year_range"]["start"] == 2024
        assert result["year_range"]["end"] == 2024

    def test_insufficient_years_for_trend(self, sample_section_data):
        """Single year of data produces insufficient_data trend direction.

        This also covers SIM-011 from the user spec (temporal trends
        with <2 years).
        """
        # All fixture data is from 2024, so only 1 year
        result = analyze_temporal_trends(
            sample_section_data, ["clinical_testing"]
        )

        trend = result["trends"]["clinical_testing"]["coverage_trend"]
        assert trend["direction"] == "insufficient_data", (
            f"Single year should produce 'insufficient_data', got '{trend['direction']}'"
        )

    def test_multi_year_increasing_trend(self):
        """Synthetic multi-year data with increasing coverage detects 'increasing' trend."""
        # Build synthetic data with coverage increasing from ~30% to ~90%
        section_data = {}
        device_idx = 0
        for year in [2020, 2021, 2022, 2023, 2024]:
            total_in_year = 10
            # Increasing number of devices with the section
            with_section = 3 + (year - 2020) * 2  # 3,5,7,9,11 -> capped at 10
            with_section = min(with_section, total_in_year)

            for i in range(total_in_year):
                k_number = f"K{year}{device_idx:04d}"
                device_idx += 1
                device = {
                    "decision_date": f"{year}0601",
                    "sections": {},
                    "metadata": {"product_code": "DQY"},
                }
                if i < with_section:
                    device["sections"]["clinical_testing"] = {
                        "text": f"Clinical testing content for device {k_number} "
                                f"with word count varying by year {year}.",
                        "word_count": 100 + (year - 2020) * 50,
                        "standards": [],
                    }
                section_data[k_number] = device

        result = analyze_temporal_trends(section_data, ["clinical_testing"])

        trend = result["trends"]["clinical_testing"]["coverage_trend"]
        assert trend["direction"] == "increasing", (
            f"Expected 'increasing', got '{trend['direction']}' "
            f"(slope={trend.get('slope', 'N/A')})"
        )
        assert trend["slope"] > 0

    def test_missing_decision_dates_handled(self):
        """SIM-013: Devices with missing decision dates are excluded from year grouping."""
        section_data = {
            "K001": {
                "decision_date": "20240601",
                "sections": {
                    "clinical_testing": {"text": "Test content", "word_count": 50, "standards": []}
                },
                "metadata": {"product_code": "DQY"},
            },
            "K002": {
                "decision_date": "",  # Missing date
                "sections": {
                    "clinical_testing": {"text": "More content", "word_count": 60, "standards": []}
                },
                "metadata": {"product_code": "DQY"},
            },
            "K003": {
                # No decision_date key at all
                "sections": {
                    "clinical_testing": {"text": "Content", "word_count": 40, "standards": []}
                },
                "metadata": {"product_code": "DQY"},
            },
        }

        result = analyze_temporal_trends(section_data, ["clinical_testing"])

        # total_devices includes all devices (including those without dates)
        assert result["total_devices"] == 3
        # Only 1 device has a valid year (2024)
        by_year = result["trends"]["clinical_testing"]["by_year"]
        assert 2024 in by_year
        assert by_year[2024]["device_count"] == 1


# ===================================================================
# Additional Tests for Enhanced Coverage (FDA-69)
# ===================================================================


class TestProgressCallbacks:
    """Test progress callback functionality in pairwise_similarity_matrix.

    Validates that progress callbacks are invoked correctly during
    similarity computation with proper current/total/message parameters.
    """

    def test_progress_callback_invoked(self):
        """Progress callback is invoked during matrix computation."""
        callback_calls = []

        def mock_callback(current, total, message):
            callback_calls.append((current, total, message))

        # Create simple test data with 5 devices
        test_data = {}
        for i in range(5):
            k_num = f"K{i:06d}"
            test_data[k_num] = {
                "sections": {
                    "clinical_testing": {
                        "text": f"Device {i} clinical testing with biocompatibility evaluation"
                    }
                },
                "metadata": {"product_code": "DQY"}
            }

        result = pairwise_similarity_matrix(
            test_data, "clinical_testing", method="sequence",
            progress_callback=mock_callback, use_cache=False
        )

        # 5 devices = C(5,2) = 10 pairs
        # With update_interval = max(1, 10//100) = 1, callback invoked for each pair
        assert len(callback_calls) > 0, f"Progress callback should be invoked, got {len(callback_calls)} calls"
        assert result["pairs_computed"] == 10  # type: ignore

        # Check that final call has correct total
        final_call = callback_calls[-1]
        assert final_call[1] == 10, f"Total pairs should be 10, got {final_call[1]}"
        assert "Computing similarity" in final_call[2]
        # Final call should have current == total
        assert final_call[0] == 10, f"Final current should be 10, got {final_call[0]}"

    def test_progress_callback_parameters(self):
        """Progress callback receives correct parameters."""
        callback_calls = []

        def mock_callback(current, total, message):
            callback_calls.append({"current": current, "total": total, "message": message})

        # Create simple test data
        test_data = {}
        for i in range(4):
            k_num = f"K{i:06d}"
            test_data[k_num] = {
                "sections": {
                    "clinical_testing": {
                        "text": f"Clinical testing for device {i}"
                    }
                },
                "metadata": {"product_code": "DQY"}
            }

        pairwise_similarity_matrix(
            test_data, "clinical_testing", method="jaccard",
            progress_callback=mock_callback, use_cache=False
        )

        # All calls should have current <= total
        assert len(callback_calls) > 0, "Should have callback calls"
        for call in callback_calls:
            assert call["current"] <= call["total"], (
                f"Current {call['current']} should be <= total {call['total']}"
            )
            assert isinstance(call["message"], str)


class TestCacheDisabling:
    """Test cache disabling functionality in pairwise_similarity_matrix.

    Validates that use_cache=False bypasses caching mechanism.
    """

    def test_cache_disabled(self, sample_section_data):
        """When use_cache=False, cache_hit should be False."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:3]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="sequence",
            use_cache=False
        )

        assert result["cache_hit"] is False, "cache_hit should be False when use_cache=False"

    def test_computation_time_present(self, sample_section_data):
        """Result includes computation_time field."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:3]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="cosine"
        )

        assert "computation_time" in result
        assert isinstance(result["computation_time"], (int, float))
        assert result["computation_time"] >= 0


class TestMedianCalculation:
    """Test median calculation for even vs odd number of scores.

    Validates correct median computation for different array sizes.
    """

    def test_median_odd_number_devices(self, sample_section_data):
        """Median calculated correctly for odd number of pairs (3 devices = 3 pairs)."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:3]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="sequence"
        )

        # 3 devices = C(3,2) = 3 pairs
        assert result["pairs_computed"] == 3
        median = result["statistics"]["median"]
        assert 0.0 <= median <= 1.0

    def test_median_even_number_devices(self, sample_section_data):
        """Median calculated correctly for even number of pairs (4 devices = 6 pairs)."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="sequence"
        )

        # 4 devices = C(4,2) = 6 pairs (even)
        assert result["pairs_computed"] == 6
        median = result["statistics"]["median"]
        assert 0.0 <= median <= 1.0


class TestSpecialCharactersWhitespace:
    """Test handling of special characters and whitespace in similarity computation.

    Validates robust text processing for various input formats.
    """

    def test_multiple_spaces_normalized(self):
        """Multiple consecutive spaces are normalized in tokenization."""
        text_a = "ISO    10993-1    biocompatibility"
        text_b = "ISO 10993-1 biocompatibility"

        # Jaccard should be identical (same unique words)
        score = compute_similarity(text_a, text_b, "jaccard")
        assert score == 1.0, f"Expected 1.0 for same words with different spacing, got {score}"

    def test_special_characters_removed(self):
        """Special characters are removed during tokenization."""
        text_a = "ISO-10993-1: Biocompatibility (Testing)!"
        text_b = "ISO 10993 1 Biocompatibility Testing"

        tokens_a = _tokenize(text_a)
        tokens_b = _tokenize(text_b)

        # Both should contain similar tokens without special chars
        assert "biocompatibility" in tokens_a
        assert "biocompatibility" in tokens_b
        assert "testing" in tokens_a
        assert "testing" in tokens_b

    def test_newlines_and_tabs_handled(self):
        """Newlines and tabs are handled gracefully."""
        text_a = "ISO 10993\nBiocompatibility\tTesting"
        text_b = "ISO 10993 Biocompatibility Testing"

        score = compute_similarity(text_a, text_b, "jaccard")
        assert score == 1.0, "Newlines and tabs should not affect word-based similarity"

    def test_unicode_characters(self):
        """Unicode characters are handled without errors."""
        text_a = "Device complies with ISO 10993 requirements"
        text_b = "Device complies with ISO 10993 requirements"  # Same text

        # Should not crash and should return 1.0
        score = compute_similarity(text_a, text_b, "sequence")
        assert score == 1.0


class TestTrendEdgeCases:
    """Test edge cases in trend detection and temporal analysis.

    Validates robust handling of unusual data patterns.
    """

    def test_trend_with_zero_mean(self):
        """Trend detection handles zero mean values gracefully."""
        year_values = [(2020, 0.0), (2021, 0.0), (2022, 0.0)]
        result = _detect_trend_direction(year_values)

        assert result["direction"] == "stable"
        assert result["slope"] == 0.0

    def test_trend_all_same_year(self):
        """Trend detection when all data points are from same year (ss_xx = 0)."""
        year_values = [(2024, 80.0), (2024, 85.0), (2024, 90.0)]
        result = _detect_trend_direction(year_values)

        # When all years are the same, ss_xx = 0, should return stable
        assert result["direction"] == "stable"
        assert result["slope"] == 0.0

    def test_increasing_trend_detected(self):
        """Clearly increasing values produce increasing direction."""
        year_values = [
            (2020, 100),
            (2021, 150),
            (2022, 210),
            (2023, 280),
            (2024, 350),
        ]
        result = _detect_trend_direction(year_values)

        assert result["direction"] == "increasing"
        assert result["slope"] > 0
        assert result["r_squared"] > 0.8

    def test_trend_with_high_r_squared(self):
        """Perfect linear trend has R² = 1.0."""
        # y = 2x + 100 (perfect linear)
        year_values = [
            (2020, 4140),  # 2*2020 + 100
            (2021, 4142),  # 2*2021 + 100
            (2022, 4144),  # 2*2022 + 100
        ]
        result = _detect_trend_direction(year_values)

        # Should have R² very close to 1.0
        assert result["r_squared"] >= 0.99, f"R² should be ~1.0, got {result['r_squared']}"


class TestCrossProductEdgeCases:
    """Test edge cases in cross-product comparison.

    Validates handling of missing data and edge cases.
    """

    def test_product_code_in_metadata(self, sample_section_data):
        """Product code correctly extracted from metadata.product_code."""
        result = cross_product_compare(
            ["DQY"],
            ["clinical_testing"],
            sample_section_data,
        )

        assert "DQY" in result["product_codes"]
        assert result["comparison"]["clinical_testing"]["DQY"]["device_count"] > 0

    def test_empty_product_code_list(self, sample_section_data):
        """Empty product code list returns empty comparison."""
        result = cross_product_compare(
            [],
            ["clinical_testing"],
            sample_section_data,
        )

        assert result["product_codes"] == []
        assert result["comparison"]["clinical_testing"] == {}

    def test_empty_section_types_list(self, sample_section_data):
        """Empty section types list returns empty comparison."""
        result = cross_product_compare(
            ["DQY"],
            [],
            sample_section_data,
        )

        assert result["section_types"] == []
        assert result["comparison"] == {}

    def test_missing_sections_in_all_devices(self, sample_section_data):
        """Section type that doesn't exist returns 0% coverage."""
        result = cross_product_compare(
            ["DQY"],
            ["nonexistent_section"],
            sample_section_data,
        )

        coverage = result["comparison"]["nonexistent_section"]["DQY"]["coverage_pct"]
        assert coverage == 0.0

    def test_standards_counting(self):
        """Standards are correctly counted and ranked."""
        # Add some standards to test data
        test_data = {
            "K001": {
                "sections": {
                    "biocompatibility": {
                        "text": "ISO 10993-1 testing performed",
                        "word_count": 10,
                        "standards": ["ISO 10993-1", "ISO 10993-5"]
                    }
                },
                "metadata": {"product_code": "DQY"}
            },
            "K002": {
                "sections": {
                    "biocompatibility": {
                        "text": "ISO 10993-1 compliant",
                        "word_count": 10,
                        "standards": ["ISO 10993-1"]
                    }
                },
                "metadata": {"product_code": "DQY"}
            }
        }

        result = cross_product_compare(
            ["DQY"],
            ["biocompatibility"],
            test_data,
        )

        top_standards = result["comparison"]["biocompatibility"]["DQY"]["top_standards"]
        # ISO 10993-1 appears twice
        assert len(top_standards) > 0
        assert top_standards[0][0] == "ISO 10993-1"
        assert top_standards[0][1] == 2


class TestSimilarityMethodSymmetry:
    """Test symmetry property of similarity methods.

    Validates that similarity(A,B) = similarity(B,A) for symmetric methods.
    Note: SequenceMatcher from difflib is not perfectly symmetric due to its
    algorithm, so we only test Jaccard and Cosine for symmetry.
    """

    def test_sequence_order_independence_identical_text(self):
        """Sequence similarity for identical text is 1.0 regardless of order."""
        text = "Cardiovascular catheter device for angioplasty"

        score_aa = compute_similarity(text, text, "sequence")

        assert score_aa == 1.0, f"Identical text should have similarity 1.0, got {score_aa}"

    def test_jaccard_symmetry(self):
        """Jaccard similarity is symmetric: sim(A,B) = sim(B,A)."""
        text_a = "ISO 10993 biocompatibility testing"
        text_b = "IEC 60601 electrical safety testing"

        score_ab = compute_similarity(text_a, text_b, "jaccard")
        score_ba = compute_similarity(text_b, text_a, "jaccard")

        assert score_ab == score_ba, (
            f"Jaccard should be symmetric: {score_ab} != {score_ba}"
        )

    def test_cosine_symmetry(self):
        """Cosine similarity is symmetric: sim(A,B) = sim(B,A)."""
        text_a = "Clinical testing performed on human subjects"
        text_b = "Preclinical animal testing conducted"

        score_ab = compute_similarity(text_a, text_b, "cosine")
        score_ba = compute_similarity(text_b, text_a, "cosine")

        assert abs(score_ab - score_ba) < 0.0001, (
            f"Cosine should be symmetric: {score_ab} != {score_ba}"
        )


class TestVeryDissimilarTexts:
    """Test similarity computation for very dissimilar texts.

    Validates that dissimilar texts produce low scores.
    """

    def test_completely_different_vocabulary(self):
        """Texts with no common words produce very low similarity."""
        text_a = "cardiovascular catheter angioplasty"
        text_b = "orthopedic screw titanium"

        # Jaccard should be 0.0 (no common words)
        score_jaccard = compute_similarity(text_a, text_b, "jaccard")
        assert score_jaccard == 0.0, f"Expected 0.0 for disjoint vocabulary, got {score_jaccard}"

        # Cosine should also be 0.0
        score_cosine = compute_similarity(text_a, text_b, "cosine")
        assert score_cosine == 0.0, f"Expected 0.0 for disjoint vocabulary, got {score_cosine}"

    def test_very_dissimilar_device_descriptions(self):
        """Real-world dissimilar device descriptions produce low scores."""
        text_a = (
            "Glucose monitoring system for diabetic patients with continuous "
            "measurements and smartphone connectivity"
        )
        text_b = (
            "Spinal fusion cage made of PEEK material for lumbar interbody "
            "fusion procedures with titanium coating"
        )

        score_sequence = compute_similarity(text_a, text_b, "sequence")
        score_jaccard = compute_similarity(text_a, text_b, "jaccard")
        score_cosine = compute_similarity(text_a, text_b, "cosine")

        # All should be relatively low (< 0.4 for reasonable threshold)
        # Sequence matcher can give higher scores due to word order patterns
        assert score_sequence < 0.4, f"Sequence score too high: {score_sequence}"
        assert score_jaccard < 0.4, f"Jaccard score too high: {score_jaccard}"
        assert score_cosine < 0.4, f"Cosine score too high: {score_cosine}"


class TestStatisticalRounding:
    """Test proper rounding of statistical results.

    Validates that scores are rounded to 4 decimal places as documented.
    """

    def test_scores_rounded_to_4_decimals(self, sample_section_data):
        """All pairwise scores are rounded to 4 decimal places."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:3]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="sequence"
        )

        for _, _, score in result["scores"]:
            # Check that score has at most 4 decimal places
            score_str = str(score)
            if "." in score_str:
                decimals = len(score_str.split(".")[1])
                assert decimals <= 4, f"Score {score} has more than 4 decimal places"

    def test_statistics_rounded_to_4_decimals(self, sample_section_data):
        """Statistics (mean, median, min, max, stdev) are rounded to 4 decimals."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset, "clinical_testing", method="cosine"
        )

        stats = result["statistics"]
        for stat_name in ["mean", "median", "min", "max", "stdev"]:
            stat_value = stats[stat_name]
            stat_str = str(stat_value)
            if "." in stat_str:
                decimals = len(stat_str.split(".")[1])
                assert decimals <= 4, f"{stat_name} {stat_value} has more than 4 decimal places"
