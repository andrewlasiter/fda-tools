"""
Tests for input_validators.py (FDA-25: Missing Input Validation).

Validates all CLI argument validation functions including product codes,
K-numbers, project names, path traversal prevention, and PMA numbers.

These tests ensure data integrity per 21 CFR Part 11 by verifying that
all user-provided inputs are sanitized before use.
"""

import os
import sys

import pytest

# Ensure scripts directory is importable
# Package imports configured in conftest.py and pytest.ini

from input_validators import (
    validate_product_code,
    validate_product_codes,
    validate_k_number,
    validate_k_numbers,
    validate_project_name,
    validate_path_safe,
    validate_pma_number,
    validate_positive_int,
)


# ============================================================================
# Product Code Validation
# ============================================================================


class TestProductCodeValidation:
    """Test FDA product code validation (3 uppercase letters)."""

    def test_valid_product_codes(self):
        assert validate_product_code("DQY") == "DQY"
        assert validate_product_code("OVE") == "OVE"
        assert validate_product_code("GEI") == "GEI"

    def test_lowercase_normalized_to_uppercase(self):
        assert validate_product_code("dqy") == "DQY"
        assert validate_product_code("ove") == "OVE"

    def test_mixed_case_normalized(self):
        assert validate_product_code("Dqy") == "DQY"

    def test_whitespace_stripped(self):
        assert validate_product_code("  DQY  ") == "DQY"

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_product_code("")

    def test_none_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_product_code(None)

    def test_too_short_rejected(self):
        with pytest.raises(ValueError, match="exactly 3"):
            validate_product_code("DQ")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="exactly 3"):
            validate_product_code("DQYY")

    def test_numeric_rejected(self):
        with pytest.raises(ValueError, match="3 uppercase letters"):
            validate_product_code("123")

    def test_special_chars_rejected(self):
        with pytest.raises(ValueError, match="3 uppercase letters"):
            validate_product_code("D-Y")

    def test_spaces_in_code_rejected(self):
        with pytest.raises(ValueError, match="3 uppercase letters"):
            validate_product_code("D Q")

    def test_validate_product_codes_list(self):
        result = validate_product_codes(["DQY", "OVE", "gei"])
        assert result == ["DQY", "OVE", "GEI"]

    def test_validate_product_codes_empty_list(self):
        with pytest.raises(ValueError, match="At least one"):
            validate_product_codes([])


# ============================================================================
# K-Number Validation
# ============================================================================


class TestKNumberValidation:
    """Test 510(k) K-number validation."""

    def test_valid_k_numbers(self):
        assert validate_k_number("K241335") == "K241335"
        assert validate_k_number("K2413357") == "K2413357"  # 7 digits

    def test_lowercase_k_normalized(self):
        assert validate_k_number("k241335") == "K241335"

    def test_pma_style_p_number(self):
        assert validate_k_number("P170019") == "P170019"

    def test_whitespace_stripped(self):
        assert validate_k_number("  K241335  ") == "K241335"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_k_number("")

    def test_none_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_k_number(None)

    def test_no_letter_prefix_rejected(self):
        with pytest.raises(ValueError, match="Invalid K-number"):
            validate_k_number("241335")

    def test_wrong_prefix_rejected(self):
        with pytest.raises(ValueError, match="Invalid K-number"):
            validate_k_number("X241335")

    def test_too_few_digits_rejected(self):
        with pytest.raises(ValueError, match="Invalid K-number"):
            validate_k_number("K12345")  # Only 5 digits

    def test_too_many_digits_rejected(self):
        with pytest.raises(ValueError, match="too long"):
            validate_k_number("K12345678")  # 8 digits

    def test_letters_in_digits_rejected(self):
        with pytest.raises(ValueError, match="Invalid K-number"):
            validate_k_number("K24133A")

    def test_validate_k_numbers_csv(self):
        result = validate_k_numbers("K241335,K200123,k999888")
        assert result == ["K241335", "K200123", "K999888"]

    def test_validate_k_numbers_with_spaces(self):
        result = validate_k_numbers("K241335, K200123")
        assert result == ["K241335", "K200123"]

    def test_validate_k_numbers_empty_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_k_numbers("")


# ============================================================================
# Project Name Validation
# ============================================================================


class TestProjectNameValidation:
    """Test project name validation (safe filesystem names)."""

    def test_valid_project_names(self):
        assert validate_project_name("my-project") == "my-project"
        assert validate_project_name("test_123") == "test_123"
        assert validate_project_name("device.v2") == "device.v2"

    def test_whitespace_stripped(self):
        assert validate_project_name("  my-project  ") == "my-project"

    def test_path_separator_rejected(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_project_name("path/to/project")

    def test_backslash_rejected(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_project_name("path\\to\\project")

    def test_parent_traversal_rejected(self):
        with pytest.raises(ValueError, match="\\.\\."):
            validate_project_name("../../etc")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_project_name("")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="too long"):
            validate_project_name("a" * 200)

    def test_special_chars_rejected(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            validate_project_name("project!@#$")

    def test_starts_with_hyphen_rejected(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            validate_project_name("-project")


# ============================================================================
# Path Validation
# ============================================================================


class TestPathValidation:
    """Test path traversal prevention."""

    def test_valid_path_within_base(self, tmp_path):
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        result = validate_path_safe(str(sub_dir), str(tmp_path))
        assert result == str(sub_dir)

    def test_traversal_outside_base_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="traversal detected"):
            validate_path_safe(
                str(tmp_path / ".." / ".." / "etc"),
                str(tmp_path)
            )

    def test_no_base_dir_allows_any_path(self, tmp_path):
        result = validate_path_safe(str(tmp_path))
        assert os.path.isabs(result)

    def test_empty_path_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_path_safe("")

    def test_extremely_long_path_rejected(self):
        with pytest.raises(ValueError, match="too long"):
            validate_path_safe("a" * 5000)

    def test_tilde_expansion(self, tmp_path):
        # Just verify it does not crash — tilde expands to home
        result = validate_path_safe("~/test-path")
        assert os.path.isabs(result)


# ============================================================================
# PMA Number Validation
# ============================================================================


class TestPMANumberValidation:
    """Test PMA number validation."""

    def test_valid_pma_number(self):
        assert validate_pma_number("P170019") == "P170019"

    def test_valid_pma_with_supplement(self):
        assert validate_pma_number("P170019/S001") == "P170019/S001"

    def test_lowercase_normalized(self):
        assert validate_pma_number("p170019") == "P170019"

    def test_invalid_prefix_rejected(self):
        with pytest.raises(ValueError, match="Invalid PMA"):
            validate_pma_number("K170019")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_pma_number("")


# ============================================================================
# Positive Integer Validation
# ============================================================================


class TestPositiveIntValidation:
    """Test positive integer validation for numeric CLI args."""

    def test_valid_positive_int(self):
        assert validate_positive_int("42", "limit") == 42

    def test_string_one(self):
        assert validate_positive_int("1", "limit") == 1

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            validate_positive_int("0", "limit")

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            validate_positive_int("-5", "limit")

    def test_non_numeric_rejected(self):
        with pytest.raises(ValueError, match="positive integer"):
            validate_positive_int("abc", "limit")

    def test_exceeds_max_rejected(self):
        with pytest.raises(ValueError, match="too large"):
            validate_positive_int("999999", "limit", max_val=1000)
