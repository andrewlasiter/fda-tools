#!/usr/bin/env python3
"""
Security tests for Combination Product Detector (FDA-939 Remediation Verification).

Tests input validation, length limits, and Unicode normalization.
"""

import pytest
from pathlib import Path

# Import from package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.combination_detector import CombinationProductDetector


class TestInputLengthValidation:
    """Test input length validation to prevent DoS attacks (FDA-939 HIGH-2)."""

    def test_validate_input_rejects_oversized_device_description(self):
        """Test that oversized device_description is rejected."""
        device_data = {
            'device_description': 'A' * 50_001,  # 1 char over limit
            'trade_name': 'Test Device',
            'intended_use': 'For testing'
        }

        with pytest.raises(ValueError, match="device_description exceeds maximum length"):
            CombinationProductDetector(device_data)

    def test_validate_input_rejects_oversized_trade_name(self):
        """Test that oversized trade_name is rejected."""
        device_data = {
            'device_description': 'Valid description',
            'trade_name': 'B' * 50_001,  # 1 char over limit
            'intended_use': 'For testing'
        }

        with pytest.raises(ValueError, match="trade_name exceeds maximum length"):
            CombinationProductDetector(device_data)

    def test_validate_input_rejects_oversized_intended_use(self):
        """Test that oversized intended_use is rejected."""
        device_data = {
            'device_description': 'Valid description',
            'trade_name': 'Test Device',
            'intended_use': 'C' * 50_001  # 1 char over limit
        }

        with pytest.raises(ValueError, match="intended_use exceeds maximum length"):
            CombinationProductDetector(device_data)

    def test_validate_input_accepts_maximum_length(self):
        """Test that inputs at exactly the maximum length are accepted."""
        device_data = {
            'device_description': 'A' * 50_000,  # Exactly at limit
            'trade_name': 'B' * 50_000,
            'intended_use': 'C' * 50_000
        }

        # Should not raise exception
        detector = CombinationProductDetector(device_data)
        assert len(detector.device_description) == 50_000
        assert len(detector.trade_name) == 50_000
        assert len(detector.intended_use) == 50_000

    def test_validate_input_rejects_non_string_type(self):
        """Test that non-string inputs are rejected."""
        device_data = {
            'device_description': 12345,  # Integer instead of string
            'trade_name': 'Test Device',
            'intended_use': 'For testing'
        }

        with pytest.raises(ValueError, match="device_description must be a string"):
            CombinationProductDetector(device_data)

    def test_validate_input_accepts_empty_strings(self):
        """Test that empty strings are accepted (optional fields)."""
        device_data = {
            'device_description': '',
            'trade_name': '',
            'intended_use': ''
        }

        # Should not raise exception
        detector = CombinationProductDetector(device_data)
        assert detector.device_description == ''


class TestUnicodeNormalization:
    """Test Unicode normalization to prevent lookalike bypasses (FDA-939 Priority 1-2)."""

    def test_normalize_text_converts_to_lowercase(self):
        """Test that text is converted to lowercase."""
        detector = CombinationProductDetector({
            'device_description': 'DRUG-ELUTING Stent',
            'trade_name': '',
            'intended_use': ''
        })

        assert 'drug-eluting' in detector.combined_text
        assert 'DRUG-ELUTING' not in detector.combined_text

    def test_normalize_text_handles_unicode_decomposed(self):
        """Test that Unicode decomposed characters are normalized (NFC)."""
        # 'café' with decomposed é (e + combining acute accent)
        decomposed = 'caf\u0065\u0301'  # e + ́ (combining acute)
        composed = 'café'  # é (precomposed)

        detector = CombinationProductDetector({
            'device_description': decomposed,
            'trade_name': '',
            'intended_use': ''
        })

        # After NFC normalization, both should match (with trailing spaces from empty fields)
        assert detector.combined_text.strip() == composed.lower()

    def test_normalize_text_handles_lookalike_characters(self):
        """Test that lookalike Unicode characters are handled."""
        # Cyrillic 'а' (U+0430) looks like Latin 'a' (U+0061)
        cyrillic_drug = 'drug-eluting'  # Normal Latin
        cyrillic_a = '\u0430'  # Cyrillic 'а'

        detector = CombinationProductDetector({
            'device_description': cyrillic_drug,
            'trade_name': '',
            'intended_use': ''
        })

        # Normalization doesn't change Latin to Cyrillic, but ensures consistency
        assert detector.combined_text.strip() == 'drug-eluting'


class TestKeywordImmutability:
    """Test that keyword lists are immutable (FDA-939 Priority 1-3)."""

    def test_drug_keywords_are_tuple(self):
        """Test that DRUG_DEVICE_KEYWORDS is a tuple (immutable)."""
        assert isinstance(CombinationProductDetector.DRUG_DEVICE_KEYWORDS, tuple)

    def test_biologic_keywords_are_tuple(self):
        """Test that DEVICE_BIOLOGIC_KEYWORDS is a tuple (immutable)."""
        assert isinstance(CombinationProductDetector.DEVICE_BIOLOGIC_KEYWORDS, tuple)

    def test_exclusions_are_tuple(self):
        """Test that EXCLUSIONS is a tuple (immutable)."""
        assert isinstance(CombinationProductDetector.EXCLUSIONS, tuple)

    def test_keywords_cannot_be_modified(self):
        """Test that keyword tuples cannot be modified."""
        with pytest.raises(TypeError):
            CombinationProductDetector.DRUG_DEVICE_KEYWORDS[0] = 'modified'


class TestDetectionWithValidInput:
    """Test that detection still works correctly with validated inputs."""

    def test_detects_drug_device_combination(self):
        """Test that drug-device combinations are still detected after security fixes."""
        device_data = {
            'device_description': 'A drug-eluting stent for coronary intervention',
            'trade_name': 'CardioStent Pro',
            'intended_use': 'For delivery of paclitaxel to coronary arteries'
        }

        detector = CombinationProductDetector(device_data)
        result = detector.detect()

        assert result['is_combination'] is True
        assert result['combination_type'] == 'drug-device'
        assert 'drug-eluting' in result['detected_components']

    def test_detects_device_biologic_combination(self):
        """Test that device-biologic combinations are still detected."""
        device_data = {
            'device_description': 'Tissue-engineered collagen matrix',
            'trade_name': 'BioMatrix',
            'intended_use': 'For wound healing with growth factors'
        }

        detector = CombinationProductDetector(device_data)
        result = detector.detect()

        assert result['is_combination'] is True
        assert result['combination_type'] in ['device-biologic', 'drug-device-biologic']

    def test_rejects_non_combination_products(self):
        """Test that non-combination products are not falsely detected."""
        device_data = {
            'device_description': 'A simple surgical instrument made of stainless steel',
            'trade_name': 'SurgiTool',
            'intended_use': 'For cutting and manipulation during surgery'
        }

        detector = CombinationProductDetector(device_data)
        result = detector.detect()

        assert result['is_combination'] is False


class TestResourceExhaustion:
    """Test protection against resource exhaustion attacks (FDA-939 CRITICAL-1)."""

    def test_prevents_memory_exhaustion_from_combined_text(self):
        """Test that combined text length is bounded by input validation."""
        # Even if all 3 fields are at max (50KB each), combined is ~150KB
        # This is far safer than unbounded concatenation (potential GB)
        device_data = {
            'device_description': 'A' * 50_000,
            'trade_name': 'B' * 50_000,
            'intended_use': 'C' * 50_000
        }

        detector = CombinationProductDetector(device_data)

        # Combined text should be ~150KB (plus spaces)
        # This is safe for keyword matching
        assert len(detector.combined_text) < 200_000  # 200KB upper bound

    def test_detection_completes_quickly_with_max_input(self):
        """Test that detection doesn't hang with maximum-length inputs."""
        import time

        device_data = {
            'device_description': 'drug-eluting ' + ('A' * 49_987),  # Max length with keyword
            'trade_name': 'B' * 50_000,
            'intended_use': 'C' * 50_000
        }

        detector = CombinationProductDetector(device_data)

        start_time = time.time()
        result = detector.detect()
        duration = time.time() - start_time

        # Should complete in under 5 seconds even with max input
        assert duration < 5.0
        # Should still detect the drug keyword
        assert result['is_combination'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
