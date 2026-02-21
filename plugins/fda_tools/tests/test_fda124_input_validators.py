"""
Input Validators Tests (FDA-124).
====================================

Verifies that lib/input_validators provides safe, consistent validation
for all user-supplied inputs used throughout the FDA tools CLI.

Tests cover:
  - validate_product_code(): normalisation, length, pattern
  - validate_product_codes(): batch wrapper, empty list guard
  - validate_k_number(): K and P prefixes, 6-7 digit formats
  - validate_k_numbers(): comma-separated parsing
  - validate_pma_number(): P###### and P######/S### formats
  - validate_project_name(): alphanumeric + safe punctuation; blocks separators
  - validate_path_safe(): base_dir containment, traversal rejection
  - validate_positive_int(): bounds, non-integer rejection
  - validate_email(): structural validity, '@' count, domain format
  - validate_url(): scheme whitelist, netloc presence, credential rejection
  - validate_json_schema(): type checking, required fields, nested objects,
    arrays, string length constraints, numeric bounds, enum, unknown type

Test count: 63
Target: pytest plugins/fda_tools/tests/test_fda124_input_validators.py -v
"""

from __future__ import annotations

import os

import pytest

from fda_tools.lib.input_validators import (
    validate_email,
    validate_json_schema,
    validate_k_number,
    validate_k_numbers,
    validate_path_safe,
    validate_pma_number,
    validate_positive_int,
    validate_product_code,
    validate_product_codes,
    validate_project_name,
    validate_url,
)


# ---------------------------------------------------------------------------
# TestProductCode
# ---------------------------------------------------------------------------


class TestProductCode:
    def test_valid_code_returned_uppercase(self):
        assert validate_product_code("DQY") == "DQY"

    def test_lowercase_normalised(self):
        assert validate_product_code("dqy") == "DQY"

    def test_mixed_case_normalised(self):
        assert validate_product_code("Dqy") == "DQY"

    def test_strips_whitespace(self):
        assert validate_product_code("  OVE  ") == "OVE"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            validate_product_code("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            validate_product_code(None)  # type: ignore[arg-type]

    def test_two_letters_raises(self):
        with pytest.raises(ValueError):
            validate_product_code("AB")

    def test_four_letters_raises(self):
        with pytest.raises(ValueError):
            validate_product_code("ABCD")

    def test_digits_raises(self):
        with pytest.raises(ValueError):
            validate_product_code("A1B")

    def test_special_chars_raises(self):
        with pytest.raises(ValueError):
            validate_product_code("A-B")


class TestProductCodes:
    def test_list_of_valid_codes(self):
        assert validate_product_codes(["DQY", "OVE"]) == ["DQY", "OVE"]

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            validate_product_codes([])

    def test_any_invalid_code_raises(self):
        with pytest.raises(ValueError):
            validate_product_codes(["DQY", "TOOLONG"])


# ---------------------------------------------------------------------------
# TestKNumber
# ---------------------------------------------------------------------------


class TestKNumber:
    def test_valid_k_number_7_digits(self):
        assert validate_k_number("K2412345") == "K2412345"

    def test_valid_k_number_6_digits(self):
        assert validate_k_number("K241335") == "K241335"

    def test_lowercase_k_normalised(self):
        assert validate_k_number("k241335") == "K241335"

    def test_p_prefix_accepted(self):
        assert validate_k_number("P241335") == "P241335"

    def test_strips_whitespace(self):
        assert validate_k_number("  K241335  ") == "K241335"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_k_number("")

    def test_wrong_prefix_raises(self):
        with pytest.raises(ValueError):
            validate_k_number("X241335")

    def test_too_few_digits_raises(self):
        with pytest.raises(ValueError):
            validate_k_number("K12345")

    def test_too_many_chars_raises(self):
        with pytest.raises(ValueError):
            validate_k_number("K241335678")


class TestKNumbers:
    def test_comma_separated_parsed(self):
        assert validate_k_numbers("K241335,K241336") == ["K241335", "K241336"]

    def test_whitespace_around_commas_stripped(self):
        assert validate_k_numbers("K241335 , K241336") == ["K241335", "K241336"]

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            validate_k_numbers("")

    def test_invalid_entry_raises(self):
        with pytest.raises(ValueError):
            validate_k_numbers("K241335,BAD")


# ---------------------------------------------------------------------------
# TestPMANumber
# ---------------------------------------------------------------------------


class TestPMANumber:
    def test_valid_pma(self):
        assert validate_pma_number("P170019") == "P170019"

    def test_supplement_suffix_accepted(self):
        assert validate_pma_number("P170019/S001") == "P170019/S001"

    def test_lowercase_normalised(self):
        assert validate_pma_number("p170019") == "P170019"

    def test_invalid_prefix_raises(self):
        with pytest.raises(ValueError):
            validate_pma_number("K170019")

    def test_too_few_digits_raises(self):
        with pytest.raises(ValueError):
            validate_pma_number("P17001")


# ---------------------------------------------------------------------------
# TestProjectName
# ---------------------------------------------------------------------------


class TestProjectName:
    def test_valid_name(self):
        assert validate_project_name("my-device") == "my-device"

    def test_name_with_underscores(self):
        assert validate_project_name("my_device_v2") == "my_device_v2"

    def test_strips_whitespace(self):
        assert validate_project_name("  device  ") == "device"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_project_name("")

    def test_path_separator_raises(self):
        with pytest.raises(ValueError):
            validate_project_name("a/b")

    def test_backslash_raises(self):
        with pytest.raises(ValueError):
            validate_project_name("a\\b")

    def test_dotdot_raises(self):
        with pytest.raises(ValueError):
            validate_project_name("../evil")

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_project_name("a" * 200)


# ---------------------------------------------------------------------------
# TestPathSafe
# ---------------------------------------------------------------------------


class TestPathSafe:
    def test_returns_absolute_path(self, tmp_path):
        result = validate_path_safe(str(tmp_path))
        assert os.path.isabs(result)

    def test_path_within_base_allowed(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        result = validate_path_safe(str(sub), base_dir=str(tmp_path))
        assert result == str(sub.resolve())

    def test_path_outside_base_raises(self, tmp_path):
        with pytest.raises(ValueError, match="traversal"):
            validate_path_safe("/etc/passwd", base_dir=str(tmp_path))

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_path_safe("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_path_safe("/" + "a" * 5000)


# ---------------------------------------------------------------------------
# TestPositiveInt
# ---------------------------------------------------------------------------


class TestPositiveInt:
    def test_valid_int_returned(self):
        assert validate_positive_int("5") == 5

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            validate_positive_int("0")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            validate_positive_int("-1")

    def test_non_integer_raises(self):
        with pytest.raises(ValueError):
            validate_positive_int("abc")

    def test_exceeds_max_raises(self):
        with pytest.raises(ValueError):
            validate_positive_int("200000", max_val=100000)

    def test_custom_name_in_error(self):
        with pytest.raises(ValueError, match="limit"):
            validate_positive_int("-1", name="limit")


# ---------------------------------------------------------------------------
# TestEmail
# ---------------------------------------------------------------------------


class TestEmail:
    def test_valid_email_returned_lowercase(self):
        assert validate_email("User@Example.COM") == "user@example.com"

    def test_simple_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_subdomain_accepted(self):
        assert validate_email("u@mail.example.co.uk") == "u@mail.example.co.uk"

    def test_strips_whitespace(self):
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_email("")

    def test_no_at_sign_raises(self):
        with pytest.raises(ValueError):
            validate_email("userexample.com")

    def test_two_at_signs_raises(self):
        with pytest.raises(ValueError):
            validate_email("user@@example.com")

    def test_empty_local_raises(self):
        with pytest.raises(ValueError):
            validate_email("@example.com")

    def test_empty_domain_raises(self):
        with pytest.raises(ValueError):
            validate_email("user@")

    def test_invalid_domain_no_dot_raises(self):
        with pytest.raises(ValueError):
            validate_email("user@localhost")

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_email("a" * 250 + "@example.com")


# ---------------------------------------------------------------------------
# TestURL
# ---------------------------------------------------------------------------


class TestURL:
    def test_https_url_accepted(self):
        assert validate_url("https://example.com/hook") == "https://example.com/hook"

    def test_http_url_accepted(self):
        assert validate_url("http://example.com/") == "http://example.com/"

    def test_strips_whitespace(self):
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_url("")

    def test_missing_scheme_raises(self):
        with pytest.raises(ValueError):
            validate_url("example.com")

    def test_ftp_scheme_rejected(self):
        with pytest.raises(ValueError):
            validate_url("ftp://example.com")

    def test_missing_netloc_raises(self):
        with pytest.raises(ValueError):
            validate_url("https://")

    def test_embedded_credentials_rejected(self):
        with pytest.raises(ValueError):
            validate_url("https://user:pass@example.com")

    def test_custom_scheme_allowed(self):
        result = validate_url("ftp://example.com", allow_schemes=["ftp"])
        assert result == "ftp://example.com"

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_url("https://example.com/" + "a" * 3000)


# ---------------------------------------------------------------------------
# TestJSONSchema
# ---------------------------------------------------------------------------


class TestJSONSchema:
    # --- type checks ---

    def test_string_type_passes(self):
        validate_json_schema("hello", {"type": "string"})

    def test_wrong_type_raises(self):
        with pytest.raises(ValueError):
            validate_json_schema(42, {"type": "string"})

    def test_integer_type_passes(self):
        validate_json_schema(5, {"type": "integer"})

    def test_bool_rejected_as_integer(self):
        with pytest.raises(ValueError):
            validate_json_schema(True, {"type": "integer"})

    def test_number_type_accepts_float(self):
        validate_json_schema(3.14, {"type": "number"})

    def test_null_type_passes(self):
        validate_json_schema(None, {"type": "null"})

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            validate_json_schema("x", {"type": "unicorn"})

    # --- required / properties ---

    def test_required_field_present_passes(self):
        validate_json_schema({"a": 1}, {"type": "object", "required": ["a"]})

    def test_missing_required_field_raises(self):
        with pytest.raises(ValueError, match="missing required property"):
            validate_json_schema({}, {"type": "object", "required": ["a"]})

    def test_nested_property_validated(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        with pytest.raises(ValueError):
            validate_json_schema({"name": 42}, schema)

    # --- array / items ---

    def test_array_items_validated(self):
        schema = {"type": "array", "items": {"type": "integer"}}
        with pytest.raises(ValueError):
            validate_json_schema([1, "oops", 3], schema)

    def test_valid_array_passes(self):
        validate_json_schema([1, 2, 3], {"type": "array", "items": {"type": "integer"}})

    # --- string constraints ---

    def test_min_length_passes(self):
        validate_json_schema("abc", {"type": "string", "minLength": 3})

    def test_min_length_violated_raises(self):
        with pytest.raises(ValueError):
            validate_json_schema("ab", {"type": "string", "minLength": 3})

    def test_max_length_passes(self):
        validate_json_schema("ab", {"type": "string", "maxLength": 5})

    def test_max_length_violated_raises(self):
        with pytest.raises(ValueError):
            validate_json_schema("abcdef", {"type": "string", "maxLength": 5})

    # --- numeric constraints ---

    def test_minimum_passes(self):
        validate_json_schema(5, {"type": "integer", "minimum": 1})

    def test_minimum_violated_raises(self):
        with pytest.raises(ValueError):
            validate_json_schema(0, {"type": "integer", "minimum": 1})

    def test_maximum_passes(self):
        validate_json_schema(10, {"type": "integer", "maximum": 100})

    def test_maximum_violated_raises(self):
        with pytest.raises(ValueError):
            validate_json_schema(101, {"type": "integer", "maximum": 100})

    # --- enum ---

    def test_enum_value_passes(self):
        validate_json_schema("A", {"enum": ["A", "B", "C"]})

    def test_enum_value_not_allowed_raises(self):
        with pytest.raises(ValueError, match="not in allowed values"):
            validate_json_schema("D", {"enum": ["A", "B", "C"]})

    # --- schema type check ---

    def test_non_dict_schema_raises(self):
        with pytest.raises(TypeError):
            validate_json_schema("x", "not-a-dict")  # type: ignore[arg-type]
