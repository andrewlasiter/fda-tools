"""Tests for JSON Schema validation of project data files (FDA-147).

Coverage:
- validate_dict() accepts valid device_profile, review, standards_lookup data
- validate_dict() rejects missing required fields
- validate_dict() rejects wrong field types
- validate_dict() returns actionable error messages including field path
- validate_project_file() loads and validates a file on disk
- validate_project_file() handles missing file gracefully
- validate_project_file() handles malformed JSON gracefully
- validate_project_file() returns error for unrecognised filename
- validate_project_dir() validates all recognised files in a directory
- validate_project_dir() skips files that are absent
- ValidationResult.error_summary() formats errors correctly
"""

import json
from pathlib import Path

import pytest

from fda_tools.lib.project_schema_validator import (
    ValidationResult,
    validate_dict,
    validate_project_dir,
    validate_project_file,
)


# ---------------------------------------------------------------------------
# Minimal valid fixtures
# ---------------------------------------------------------------------------

VALID_DEVICE_PROFILE = {
    "product_code": "DQY",
    "device_name": "Catheter, Percutaneous",
    "applicant": "Acme Corp",
    "device_class": "2",
    "regulation_number": "870.1250",
    "review_panel": "CV",
    "implant_flag": "N",
    "intended_use": "Used to deliver implants.",
    "materials": ["stainless steel"],
    "standards_referenced": ["ISO 11135"],
    "extracted_sections": {},
    "peer_devices": [],
    "created_at": "2026-02-21T00:00:00Z",
    "source": "seed_generator",
}

VALID_REVIEW = {
    "product_code": "DQY",
    "project": "batch_DQY",
    "device_name": "Catheter, Percutaneous",
    "created_at": "2026-02-21T00:00:00Z",
    "reviewed_at": "2026-02-21T00:00:00Z",
    "predicates": {
        "K241234": {
            "device_name": "Example Catheter",
            "score": 85.0,
            "accepted": True,
        }
    },
    "reference_devices": {},
    "summary": {
        "total_evaluated": 1,
        "accepted": 1,
        "rejected": 0,
        "average_score": 85.0,
    },
}

VALID_STANDARDS_LOOKUP = {
    "product_code": "DQY",
    "device_name": "Catheter, Percutaneous",
    "device_class": "2",
    "regulation_number": "870.1250",
    "generated_at": "2026-02-21",
    "standards": [
        {
            "standard": "IEC 60601-1:2005",
            "title": "Medical electrical equipment",
            "category": "Electrical Safety",
        }
    ],
    "total_standards": 1,
    "categories": {"Electrical Safety": 1},
}


# ---------------------------------------------------------------------------
# validate_dict — happy path
# ---------------------------------------------------------------------------


class TestValidateDictHappyPath:
    """Valid documents should return ValidationResult(valid=True)."""

    def test_valid_device_profile(self):
        result = validate_dict(VALID_DEVICE_PROFILE, "device_profile")
        assert result.valid, result.errors

    def test_valid_review(self):
        result = validate_dict(VALID_REVIEW, "review")
        assert result.valid, result.errors

    def test_valid_standards_lookup(self):
        result = validate_dict(VALID_STANDARDS_LOOKUP, "standards_lookup")
        assert result.valid, result.errors

    def test_result_is_truthy_when_valid(self):
        result = validate_dict(VALID_DEVICE_PROFILE, "device_profile")
        assert bool(result) is True

    def test_no_errors_when_valid(self):
        result = validate_dict(VALID_REVIEW, "review")
        assert result.errors == []

    def test_schema_type_set_on_result(self):
        result = validate_dict(VALID_DEVICE_PROFILE, "device_profile")
        assert result.schema_type == "device_profile"


# ---------------------------------------------------------------------------
# validate_dict — required field missing
# ---------------------------------------------------------------------------


class TestValidateDictMissingRequired:
    """Missing required fields should produce validation errors."""

    def test_device_profile_missing_product_code(self):
        data = {k: v for k, v in VALID_DEVICE_PROFILE.items() if k != "product_code"}
        result = validate_dict(data, "device_profile")
        assert not result.valid
        assert result.errors

    def test_device_profile_missing_device_name(self):
        data = {k: v for k, v in VALID_DEVICE_PROFILE.items() if k != "device_name"}
        result = validate_dict(data, "device_profile")
        assert not result.valid

    def test_review_missing_product_code(self):
        data = {k: v for k, v in VALID_REVIEW.items() if k != "product_code"}
        result = validate_dict(data, "review")
        assert not result.valid

    def test_standards_lookup_missing_product_code(self):
        data = {k: v for k, v in VALID_STANDARDS_LOOKUP.items() if k != "product_code"}
        result = validate_dict(data, "standards_lookup")
        assert not result.valid

    def test_result_is_falsy_when_invalid(self):
        data = {}
        result = validate_dict(data, "device_profile")
        assert bool(result) is False


# ---------------------------------------------------------------------------
# validate_dict — type errors
# ---------------------------------------------------------------------------


class TestValidateDictTypeErrors:
    """Wrong field types should produce descriptive errors."""

    def test_product_code_must_be_string(self):
        data = {**VALID_DEVICE_PROFILE, "product_code": 123}
        result = validate_dict(data, "device_profile")
        assert not result.valid

    def test_materials_must_be_array(self):
        data = {**VALID_DEVICE_PROFILE, "materials": "stainless steel"}
        result = validate_dict(data, "device_profile")
        assert not result.valid

    def test_summary_total_evaluated_must_be_integer(self):
        data = {
            **VALID_REVIEW,
            "summary": {**VALID_REVIEW["summary"], "total_evaluated": "one"},
        }
        result = validate_dict(data, "review")
        assert not result.valid

    def test_standards_array_items_must_be_objects(self):
        data = {**VALID_STANDARDS_LOOKUP, "standards": ["IEC 60601-1"]}
        result = validate_dict(data, "standards_lookup")
        assert not result.valid

    def test_total_standards_must_be_integer(self):
        data = {**VALID_STANDARDS_LOOKUP, "total_standards": "fourteen"}
        result = validate_dict(data, "standards_lookup")
        assert not result.valid


# ---------------------------------------------------------------------------
# validate_dict — error messages
# ---------------------------------------------------------------------------


class TestValidateDictErrorMessages:
    """Error messages should identify the offending field path."""

    def test_error_mentions_field_path_for_nested_error(self):
        data = {
            **VALID_REVIEW,
            "summary": {**VALID_REVIEW["summary"], "total_evaluated": "bad"},
        }
        result = validate_dict(data, "review")
        # Should mention path to total_evaluated
        combined = " ".join(result.errors)
        assert "total_evaluated" in combined or "summary" in combined

    def test_multiple_errors_reported(self):
        """Two bad fields → two errors."""
        data = {
            **VALID_DEVICE_PROFILE,
            "product_code": 99,
            "materials": "steel",
        }
        result = validate_dict(data, "device_profile")
        assert len(result.errors) >= 2

    def test_unknown_schema_type_returns_error(self):
        result = validate_dict({}, "nonexistent_schema")
        assert not result.valid
        assert result.errors


# ---------------------------------------------------------------------------
# ValidationResult helpers
# ---------------------------------------------------------------------------


class TestValidationResultHelpers:
    """Tests for ValidationResult utility methods."""

    def test_error_summary_ok_when_valid(self):
        result = ValidationResult(valid=True)
        assert result.error_summary() == "OK"

    def test_error_summary_shows_count_and_first_error(self):
        result = ValidationResult(valid=False, errors=["err1", "err2", "err3"])
        summary = result.error_summary()
        assert "3" in summary
        assert "err1" in summary

    def test_error_summary_ellipsis_for_multiple_errors(self):
        result = ValidationResult(valid=False, errors=["err1", "err2"])
        assert "…" in result.error_summary()

    def test_error_summary_no_ellipsis_for_single_error(self):
        result = ValidationResult(valid=False, errors=["err1"])
        assert "…" not in result.error_summary()


# ---------------------------------------------------------------------------
# validate_project_file
# ---------------------------------------------------------------------------


class TestValidateProjectFile:
    """Tests for file-based validation."""

    def test_validates_valid_device_profile_file(self, tmp_path):
        f = tmp_path / "device_profile.json"
        f.write_text(json.dumps(VALID_DEVICE_PROFILE))
        result = validate_project_file(f)
        assert result.valid, result.errors

    def test_validates_valid_review_file(self, tmp_path):
        f = tmp_path / "review.json"
        f.write_text(json.dumps(VALID_REVIEW))
        result = validate_project_file(f)
        assert result.valid, result.errors

    def test_validates_valid_standards_lookup_file(self, tmp_path):
        f = tmp_path / "standards_lookup.json"
        f.write_text(json.dumps(VALID_STANDARDS_LOOKUP))
        result = validate_project_file(f)
        assert result.valid, result.errors

    def test_invalid_json_returns_error(self, tmp_path):
        f = tmp_path / "device_profile.json"
        f.write_text("{ not valid json }")
        result = validate_project_file(f)
        assert not result.valid
        assert any("Invalid JSON" in e or "JSON" in e for e in result.errors)

    def test_missing_file_returns_error(self, tmp_path):
        f = tmp_path / "device_profile.json"
        result = validate_project_file(f)
        assert not result.valid
        assert any("not found" in e.lower() or "File" in e for e in result.errors)

    def test_unrecognised_filename_returns_error(self, tmp_path):
        f = tmp_path / "unknown_data.json"
        f.write_text("{}")
        result = validate_project_file(f)
        assert not result.valid
        assert result.errors

    def test_source_path_set_on_result(self, tmp_path):
        f = tmp_path / "device_profile.json"
        f.write_text(json.dumps(VALID_DEVICE_PROFILE))
        result = validate_project_file(f)
        assert result.source_path == f


# ---------------------------------------------------------------------------
# validate_project_dir
# ---------------------------------------------------------------------------


class TestValidateProjectDir:
    """Tests for directory-level validation."""

    def test_validates_all_three_files(self, tmp_path):
        (tmp_path / "device_profile.json").write_text(json.dumps(VALID_DEVICE_PROFILE))
        (tmp_path / "review.json").write_text(json.dumps(VALID_REVIEW))
        (tmp_path / "standards_lookup.json").write_text(json.dumps(VALID_STANDARDS_LOOKUP))

        results = validate_project_dir(tmp_path)
        assert set(results.keys()) == {
            "device_profile.json",
            "review.json",
            "standards_lookup.json",
        }
        for filename, result in results.items():
            assert result.valid, f"{filename}: {result.errors}"

    def test_skips_absent_files(self, tmp_path):
        (tmp_path / "device_profile.json").write_text(json.dumps(VALID_DEVICE_PROFILE))
        # review.json and standards_lookup.json are absent

        results = validate_project_dir(tmp_path)
        assert "device_profile.json" in results
        assert "review.json" not in results
        assert "standards_lookup.json" not in results

    def test_returns_error_for_invalid_file(self, tmp_path):
        bad_profile = {"device_name": "Missing product_code"}
        (tmp_path / "device_profile.json").write_text(json.dumps(bad_profile))

        results = validate_project_dir(tmp_path)
        assert not results["device_profile.json"].valid

    def test_empty_directory_returns_empty_dict(self, tmp_path):
        results = validate_project_dir(tmp_path)
        assert results == {}
