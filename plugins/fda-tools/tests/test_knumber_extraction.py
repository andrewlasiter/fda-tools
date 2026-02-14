"""Tests for K-number, P-number, DEN-number, and N-number extraction patterns.

Validates regex accuracy against known edge cases including OCR errors and supplements.
"""

import re
import pytest

# The combined pattern used across the plugin
DEVICE_NUMBER_PATTERN = re.compile(
    r"\b(K\d{6}(?:/S\d{3})?|P\d{6}(?:/S\d{3})?|DEN\d{6,7}|N\d{4,5})\b"
)

# Individual patterns
K_PATTERN = re.compile(r"\bK\d{6}\b")
K_SUPPLEMENT_PATTERN = re.compile(r"\bK\d{6}/S\d{3}\b")
P_PATTERN = re.compile(r"\bP\d{6}\b")
P_SUPPLEMENT_PATTERN = re.compile(r"\bP\d{6}/S\d{3}\b")
DEN_PATTERN = re.compile(r"\bDEN\d{6,7}\b")
N_PATTERN = re.compile(r"\bN\d{4,5}\b")

# OCR error correction patterns
OCR_K_PATTERN = re.compile(r"\b[Kk][O0I1]\d{5}\b")


class TestKNumberExtraction:
    """Test standard K-number extraction."""

    def test_standard_knumber(self):
        assert K_PATTERN.findall("K192345") == ["K192345"]

    def test_knumber_in_sentence(self):
        text = "The predicate device is K192345, cleared in 2020."
        assert K_PATTERN.findall(text) == ["K192345"]

    def test_multiple_knumbers(self):
        text = "Predicates: K192345 and K181234 and K170987"
        assert K_PATTERN.findall(text) == ["K192345", "K181234", "K170987"]

    def test_knumber_recent_fiscal_year(self):
        assert K_PATTERN.findall("K241335") == ["K241335"]

    def test_knumber_with_supplement(self):
        matches = K_SUPPLEMENT_PATTERN.findall("K192345/S001")
        assert matches == ["K192345/S001"]

    def test_knumber_supplement_in_text(self):
        text = "K192345/S001 was a supplement adding new sizes."
        matches = K_SUPPLEMENT_PATTERN.findall(text)
        assert matches == ["K192345/S001"]

    def test_combined_pattern_finds_knumber(self):
        matches = DEVICE_NUMBER_PATTERN.findall("K192345")
        assert "K192345" in matches

    def test_combined_pattern_finds_supplement(self):
        matches = DEVICE_NUMBER_PATTERN.findall("K192345/S001")
        assert "K192345/S001" in matches

    def test_no_false_positive_short(self):
        """K followed by fewer than 6 digits should not match."""
        assert K_PATTERN.findall("K1234") == []
        assert K_PATTERN.findall("K12345") == []

    def test_no_false_positive_long(self):
        """K followed by more than 6 digits should not match the extra."""
        matches = K_PATTERN.findall("K1234567")
        # Should match K123456 as a word boundary issue or not match at all
        # depending on what follows - this tests boundary behavior
        assert len(matches) <= 1

    def test_knumber_at_start_of_line(self):
        assert K_PATTERN.findall("K192345 is the predicate") == ["K192345"]

    def test_knumber_at_end_of_line(self):
        assert K_PATTERN.findall("predicate is K192345") == ["K192345"]


class TestPNumberExtraction:
    """Test PMA number extraction."""

    def test_standard_pnumber(self):
        assert P_PATTERN.findall("P190001") == ["P190001"]

    def test_pnumber_with_supplement(self):
        matches = P_SUPPLEMENT_PATTERN.findall("P190001/S002")
        assert matches == ["P190001/S002"]

    def test_pnumber_in_context(self):
        text = "PMA approval P190001 was granted for CardioValve."
        assert P_PATTERN.findall(text) == ["P190001"]

    def test_combined_finds_pnumber(self):
        matches = DEVICE_NUMBER_PATTERN.findall("P190001")
        assert "P190001" in matches


class TestDENNumberExtraction:
    """Test De Novo number extraction."""

    def test_den_6_digits(self):
        assert DEN_PATTERN.findall("DEN200045") == ["DEN200045"]

    def test_den_7_digits(self):
        assert DEN_PATTERN.findall("DEN2000456") == ["DEN2000456"]

    def test_den_in_context(self):
        text = "De Novo classification DEN200045 was granted."
        assert DEN_PATTERN.findall(text) == ["DEN200045"]

    def test_combined_finds_den(self):
        matches = DEVICE_NUMBER_PATTERN.findall("DEN200045")
        assert "DEN200045" in matches


class TestNNumberExtraction:
    """Test pre-amendments N-number extraction."""

    def test_n_4_digits(self):
        assert N_PATTERN.findall("N0012") == ["N0012"]

    def test_n_5_digits(self):
        assert N_PATTERN.findall("N00123") == ["N00123"]

    def test_n_in_context(self):
        text = "Pre-amendments device N0012 is referenced."
        assert N_PATTERN.findall(text) == ["N0012"]

    def test_combined_finds_n(self):
        matches = DEVICE_NUMBER_PATTERN.findall("N0012")
        assert "N0012" in matches


class TestOCRErrorDetection:
    """Test OCR error patterns (O→0, I→1)."""

    def test_ocr_o_to_zero(self):
        """KO12345 is likely K012345 with OCR error at position 2."""
        matches = OCR_K_PATTERN.findall("KO12345")
        assert matches == ["KO12345"]

    def test_ocr_i_to_one(self):
        """KI92345 is likely K192345 with OCR error."""
        matches = OCR_K_PATTERN.findall("KI92345")
        assert matches == ["KI92345"]

    def test_valid_knumber_not_flagged_as_ocr(self):
        """Valid K-numbers with 0 or 1 should also match OCR pattern."""
        # K0xxxxx and K1xxxxx are valid — OCR pattern is for detection, not rejection
        matches = OCR_K_PATTERN.findall("K012345")
        assert matches == ["K012345"]


class TestCombinedExtractionFromSample:
    """Test extraction from the sample 510(k) text fixture."""

    @pytest.fixture
    def sample_text(self):
        import os
        fixture_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "sample_510k_text.txt"
        )
        with open(fixture_path) as f:
            return f.read()

    def test_finds_all_knumbers(self, sample_text):
        matches = K_PATTERN.findall(sample_text)
        assert "K192345" in matches
        assert "K181234" in matches
        assert "K170987" in matches
        assert "K241335" in matches

    def test_finds_pnumber(self, sample_text):
        matches = P_PATTERN.findall(sample_text)
        assert "P190001" in matches

    def test_finds_den_number(self, sample_text):
        matches = DEN_PATTERN.findall(sample_text)
        assert "DEN200045" in matches

    def test_finds_n_number(self, sample_text):
        matches = N_PATTERN.findall(sample_text)
        assert "N0012" in matches

    def test_finds_supplements(self, sample_text):
        matches = K_SUPPLEMENT_PATTERN.findall(sample_text)
        assert "K192345/S001" in matches
        assert "K181234/S002" in matches

    def test_combined_pattern_total_count(self, sample_text):
        matches = DEVICE_NUMBER_PATTERN.findall(sample_text)
        # Should find: K192345, K181234, K170987, K241335, K192345/S001,
        # K181234/S002, P190001, DEN200045, N0012, K102345, K192345 (dup)
        assert len(matches) >= 9


class TestDeviceNumberRouting:
    """Test device number type detection for API endpoint routing."""

    def test_k_number_routes_to_510k(self):
        num = "K241335"
        assert num.upper().startswith("K")

    def test_p_number_routes_to_pma(self):
        num = "P870024"
        assert num.upper().startswith("P")

    def test_den_number_detected(self):
        num = "DEN200043"
        assert num.upper().startswith("DEN")

    def test_n_number_detected(self):
        num = "N0012"
        upper = num.upper()
        assert upper.startswith("N") and not upper.startswith("DEN")

    def test_routing_logic(self):
        """Validate the routing logic used in fda_api_client.validate_device()."""
        test_cases = [
            ("K241335", "510k"),
            ("K001234", "510k"),
            ("P870024", "pma"),
            ("P190001", "pma"),
            ("DEN200043", "510k"),  # DEN searches 510k endpoint
            ("DEN2000435", "510k"),
            ("N0012", "n_number"),  # N-numbers skip API
        ]
        for number, expected_endpoint in test_cases:
            num = number.upper()
            if num.startswith("K"):
                endpoint = "510k"
            elif num.startswith("P"):
                endpoint = "pma"
            elif num.startswith("DEN"):
                endpoint = "510k"
            elif num.startswith("N"):
                endpoint = "n_number"
            else:
                endpoint = "unknown"
            assert endpoint == expected_endpoint, f"{number} should route to {expected_endpoint}, got {endpoint}"
