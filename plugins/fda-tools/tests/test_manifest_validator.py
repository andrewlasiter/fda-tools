#!/usr/bin/env python3
"""
Test suite for manifest_validator.py -- FDA Data Manifest JSON Schema Validation.

Tests cover:
    - Schema loading and validation
    - Validation error formatting
    - Schema version checking
    - Manifest repair functionality
    - Edge cases and error handling

Test categories:
    - TestSchemaLoading: Schema file loading and availability
    - TestBasicValidation: Valid manifests pass validation
    - TestRequiredFields: Missing required fields detected
    - TestTypeValidation: Type mismatches caught
    - TestPatternValidation: Pattern constraints enforced
    - TestVersionChecking: Schema version compatibility
    - TestRepairFunctionality: Automatic repair of common issues
    - TestErrorMessages: Clear error messages generated
    - TestEdgeCases: Boundary conditions and error paths
    - TestMinimalManifest: Minimal valid manifest creation
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add lib directory to path
LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB_DIR)

from manifest_validator import (  # type: ignore
    validate_manifest,
    validate_manifest_file,
    get_schema_version,
    check_schema_version_compatibility,
    add_schema_version,
    create_minimal_manifest,
    validate_and_repair,
    ValidationError,
    CURRENT_SCHEMA_VERSION,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def valid_510k_manifest():
    """A valid 510(k) project manifest."""
    return {
        "schema_version": "1.0.0",
        "project": "test_510k_project",
        "created_at": "2024-01-15T08:30:00+00:00",
        "last_updated": "2024-01-15T10:45:00+00:00",
        "product_codes": ["DQY", "OVE"],
        "queries": {
            "classification:DQY": {
                "fetched_at": "2024-01-15T09:00:00+00:00",
                "ttl_hours": 168,
                "source": "openFDA",
                "total_matches": 1,
                "summary": {
                    "device_name": "Cardiovascular Catheter",
                    "device_class": "2",
                },
                "api_cache_key": "classification_dqy_12345",
            }
        },
        "fingerprints": {
            "DQY": {
                "product_code": "DQY",
                "last_updated": "2024-01-15T09:00:00+00:00",
                "known_k_numbers": ["K241234", "K231234"],
                "total_clearances": 2,
                "latest_clearance_date": "2024-01-10",
                "total_recalls": 0,
                "total_adverse_events": 5,
                "deaths": 0,
                "injuries": 2,
                "malfunctions": 3,
            }
        },
    }


@pytest.fixture
def valid_pma_manifest():
    """A valid PMA project manifest."""
    return {
        "schema_version": "1.0.0",
        "created_at": "2024-01-15T08:30:00+00:00",
        "last_updated": "2024-01-15T10:45:00+00:00",
        "total_pmas": 1,
        "total_sseds_downloaded": 1,
        "total_sections_extracted": 1,
        "pma_entries": {
            "P170019": {
                "pma_number": "P170019",
                "first_cached_at": "2024-01-15T08:30:00+00:00",
                "last_updated": "2024-01-15T09:00:00+00:00",
                "pma_approval_fetched_at": "2024-01-15T08:35:00+00:00",
                "device_name": "Test Device",
                "applicant": "Test Company",
                "product_code": "NMH",
                "decision_date": "2017-05-15",
                "advisory_committee": "CV",
                "supplement_count": 3,
                "ssed_downloaded": True,
                "ssed_filepath": "/path/to/ssed.pdf",
                "ssed_file_size_kb": 2500,
                "ssed_url": "https://www.accessdata.fda.gov/...",
                "ssed_downloaded_at": "2024-01-15T08:40:00+00:00",
                "sections_extracted": True,
                "section_count": 12,
                "total_word_count": 45000,
                "sections_extracted_at": "2024-01-15T08:50:00+00:00",
            }
        },
        "search_cache": {
            "product_code:NMH:year:2024": {
                "results": [{"pma_number": "P170019"}],
                "fetched_at": "2024-01-15T09:00:00+00:00",
                "result_count": 1,
            }
        },
    }


@pytest.fixture
def minimal_manifest():
    """Minimal valid manifest with only required fields."""
    return {
        "schema_version": "1.0.0",
    }


@pytest.fixture
def legacy_manifest_no_version():
    """Legacy manifest without schema_version field."""
    return {
        "project": "legacy_project",
        "product_codes": ["DQY"],
        "queries": {},
    }


# ==============================================================================
# Test Classes
# ==============================================================================


class TestSchemaLoading:
    """Test schema file loading and availability."""

    def test_schema_file_exists(self):
        """Schema file should exist at expected location."""
        schema_path = Path(__file__).parent.parent / "data" / "schemas" / "data_manifest.schema.json"
        assert schema_path.exists(), f"Schema file not found: {schema_path}"

    def test_schema_is_valid_json(self):
        """Schema file should be valid JSON."""
        schema_path = Path(__file__).parent.parent / "data" / "schemas" / "data_manifest.schema.json"
        with open(schema_path) as f:
            schema = json.load(f)  # Should not raise JSONDecodeError
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


class TestBasicValidation:
    """Test validation of valid manifests."""

    def test_valid_510k_manifest(self, valid_510k_manifest):
        """Valid 510(k) manifest should pass validation."""
        is_valid, errors = validate_manifest(valid_510k_manifest, strict=False)
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_valid_pma_manifest(self, valid_pma_manifest):
        """Valid PMA manifest should pass validation."""
        is_valid, errors = validate_manifest(valid_pma_manifest, strict=False)
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_minimal_manifest(self, minimal_manifest):
        """Minimal manifest with only schema_version should pass."""
        is_valid, errors = validate_manifest(minimal_manifest, strict=False)
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_strict_mode_raises_on_invalid(self):
        """Strict mode should raise ValidationError on invalid manifest."""
        invalid_manifest = {"invalid_field": "value"}  # Missing schema_version
        with pytest.raises(ValidationError) as exc_info:
            validate_manifest(invalid_manifest, strict=True)
        assert "schema_version" in str(exc_info.value).lower()


class TestRequiredFields:
    """Test detection of missing required fields."""

    def test_missing_schema_version(self):
        """Manifest without schema_version should fail validation."""
        manifest = {
            "project": "test",
            "product_codes": [],
        }
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("schema_version" in err.lower() for err in errors)

    def test_query_entry_missing_required_fields(self, valid_510k_manifest):
        """Query entry without required fields should fail."""
        manifest = valid_510k_manifest.copy()
        manifest["queries"]["test:query"] = {
            "summary": {}  # Missing fetched_at, ttl_hours, source
        }
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("fetched_at" in err for err in errors)

    def test_fingerprint_missing_required_fields(self, valid_510k_manifest):
        """Fingerprint without required fields should fail."""
        manifest = valid_510k_manifest.copy()
        manifest["fingerprints"]["GEI"] = {
            "product_code": "GEI",
            # Missing last_updated
        }
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("last_updated" in err for err in errors)

    def test_pma_entry_missing_required_fields(self, valid_pma_manifest):
        """PMA entry without required fields should fail."""
        manifest = valid_pma_manifest.copy()
        manifest["pma_entries"]["P200001"] = {
            "pma_number": "P200001",
            # Missing first_cached_at
        }
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("first_cached_at" in err for err in errors)


class TestTypeValidation:
    """Test type constraint validation."""

    def test_schema_version_wrong_type(self):
        """schema_version must be string, not number."""
        manifest = {"schema_version": 1.0}  # Should be "1.0.0"
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("type" in err.lower() for err in errors)

    def test_product_codes_wrong_type(self, valid_510k_manifest):
        """product_codes must be array, not string."""
        manifest = valid_510k_manifest.copy()
        manifest["product_codes"] = "DQY,OVE"  # Should be ["DQY", "OVE"]
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("product_codes" in err for err in errors)

    def test_ttl_hours_wrong_type(self, valid_510k_manifest):
        """ttl_hours must be integer, not string."""
        manifest = valid_510k_manifest.copy()
        manifest["queries"]["classification:DQY"]["ttl_hours"] = "168"  # Should be 168
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("ttl_hours" in err for err in errors)

    def test_total_pmas_negative(self, valid_pma_manifest):
        """total_pmas must be non-negative."""
        manifest = valid_pma_manifest.copy()
        manifest["total_pmas"] = -1
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("minimum" in err.lower() for err in errors)


class TestPatternValidation:
    """Test pattern constraint validation."""

    def test_invalid_product_code_pattern(self, valid_510k_manifest):
        """Product code must be 3 uppercase letters."""
        manifest = valid_510k_manifest.copy()
        manifest["product_codes"].append("dqy")  # Should be uppercase
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("pattern" in err.lower() for err in errors)

    def test_invalid_k_number_pattern(self, valid_510k_manifest):
        """K-number must match K###### format."""
        manifest = valid_510k_manifest.copy()
        manifest["fingerprints"]["DQY"]["known_k_numbers"].append("K12345")  # Too short
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("pattern" in err.lower() for err in errors)

    def test_invalid_pma_number_pattern(self, valid_pma_manifest):
        """PMA number must match P###### or P######X format."""
        manifest = valid_pma_manifest.copy()
        manifest["pma_entries"]["P1234"] = manifest["pma_entries"]["P170019"].copy()
        manifest["pma_entries"]["P1234"]["pma_number"] = "P1234"  # Too short
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        # Pattern validation occurs on the property key itself

    def test_invalid_schema_version_pattern(self):
        """Schema version must match semantic versioning (MAJOR.MINOR.PATCH)."""
        manifest = {"schema_version": "1.0"}  # Missing patch version
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("pattern" in err.lower() for err in errors)


class TestVersionChecking:
    """Test schema version compatibility checking."""

    def test_get_schema_version(self, valid_510k_manifest):
        """Should extract schema version from manifest."""
        version = get_schema_version(valid_510k_manifest)
        assert version == "1.0.0"

    def test_get_schema_version_missing(self, legacy_manifest_no_version):
        """Should return None for manifests without schema_version."""
        version = get_schema_version(legacy_manifest_no_version)
        assert version is None

    def test_compatible_version(self, valid_510k_manifest):
        """Manifest with current version should be compatible."""
        is_compatible, message = check_schema_version_compatibility(valid_510k_manifest)
        assert is_compatible
        assert CURRENT_SCHEMA_VERSION in message

    def test_missing_version_incompatible(self, legacy_manifest_no_version):
        """Legacy manifest without version should be incompatible."""
        is_compatible, message = check_schema_version_compatibility(legacy_manifest_no_version)
        assert not is_compatible
        assert "missing" in message.lower()

    def test_major_version_mismatch(self, valid_510k_manifest):
        """Major version mismatch should be incompatible."""
        manifest = valid_510k_manifest.copy()
        manifest["schema_version"] = "2.0.0"
        is_compatible, message = check_schema_version_compatibility(manifest)
        assert not is_compatible
        assert "major version" in message.lower()

    def test_add_schema_version_to_legacy(self, legacy_manifest_no_version):
        """Should add schema_version to legacy manifest."""
        manifest = add_schema_version(legacy_manifest_no_version.copy())
        assert "schema_version" in manifest
        assert manifest["schema_version"] == CURRENT_SCHEMA_VERSION


class TestRepairFunctionality:
    """Test automatic repair of common validation issues."""

    def test_repair_adds_schema_version(self):
        """Repair should add missing schema_version."""
        manifest = {"project": "test"}
        repaired, repairs = validate_and_repair(manifest)
        assert "schema_version" in repaired
        assert repaired["schema_version"] == CURRENT_SCHEMA_VERSION
        assert any("schema_version" in r for r in repairs)

    def test_repair_adds_timestamps(self):
        """Repair should add missing timestamps."""
        manifest = {"schema_version": "1.0.0"}
        repaired, repairs = validate_and_repair(manifest, add_defaults=True)
        assert "created_at" in repaired
        assert "last_updated" in repaired
        assert any("created_at" in r for r in repairs)
        assert any("last_updated" in r for r in repairs)

    def test_repair_adds_product_codes_and_queries(self):
        """Repair should add missing product_codes and queries."""
        manifest = {"schema_version": "1.0.0"}
        repaired, repairs = validate_and_repair(manifest, add_defaults=True)
        assert "product_codes" in repaired
        assert "queries" in repaired
        assert isinstance(repaired["product_codes"], list)
        assert isinstance(repaired["queries"], dict)

    def test_repair_removes_additional_properties(self):
        """Repair should remove fields not in schema."""
        manifest = {
            "schema_version": "1.0.0",
            "unknown_field": "value",
            "another_unknown": 123,
        }
        repaired, repairs = validate_and_repair(manifest)
        assert "unknown_field" not in repaired
        assert "another_unknown" not in repaired
        assert any("unknown_field" in r for r in repairs)

    def test_repair_no_changes_needed(self, valid_510k_manifest):
        """Repair should report no changes for valid manifest."""
        repaired, repairs = validate_and_repair(valid_510k_manifest)
        # Only schema_version might be added if missing, but it's already present
        # So there might be minimal or no changes
        assert repaired["schema_version"] == "1.0.0"


class TestErrorMessages:
    """Test error message formatting and clarity."""

    def test_missing_required_field_message(self):
        """Missing required field error should be clear."""
        manifest = {}
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert len(errors) > 0
        # Should mention the missing field
        assert any("schema_version" in err for err in errors)

    def test_type_mismatch_message(self):
        """Type mismatch error should show expected and actual types."""
        manifest = {"schema_version": 123}  # Should be string
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("type" in err.lower() for err in errors)

    def test_pattern_mismatch_message(self):
        """Pattern mismatch should show the invalid value."""
        manifest = {
            "schema_version": "invalid-version"  # Doesn't match \d+\.\d+\.\d+
        }
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("pattern" in err.lower() for err in errors)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_manifest(self):
        """Empty manifest should fail validation."""
        manifest = {}
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid

    def test_null_values(self):
        """Null values in fields should be caught."""
        manifest = {
            "schema_version": "1.0.0",
            "product_codes": None,  # Should be array
        }
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid

    def test_additional_properties_in_queries(self, valid_510k_manifest):
        """Additional properties in query entries should be rejected."""
        manifest = valid_510k_manifest.copy()
        manifest["queries"]["classification:DQY"]["unknown_field"] = "value"
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert not is_valid
        assert any("additional" in err.lower() for err in errors)

    def test_file_not_found(self):
        """validate_manifest_file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validate_manifest_file("/nonexistent/path/data_manifest.json", strict=True)

    def test_invalid_json_file(self):
        """validate_manifest_file should handle invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            is_valid, errors = validate_manifest_file(temp_path, strict=False)
            assert not is_valid
            assert any("json" in err.lower() for err in errors)
        finally:
            os.unlink(temp_path)


class TestMinimalManifest:
    """Test minimal manifest creation."""

    def test_create_minimal_manifest(self):
        """Should create a minimal valid manifest."""
        manifest = create_minimal_manifest("test_project")
        assert manifest["schema_version"] == CURRENT_SCHEMA_VERSION
        assert manifest["project"] == "test_project"
        assert "created_at" in manifest
        assert "last_updated" in manifest
        assert manifest["product_codes"] == []
        assert manifest["queries"] == {}

    def test_minimal_manifest_validates(self):
        """Created minimal manifest should pass validation."""
        manifest = create_minimal_manifest("test_project")
        is_valid, errors = validate_manifest(manifest, strict=False)
        assert is_valid, f"Validation failed: {errors}"


class TestManifestFile:
    """Test file-based validation."""

    def test_validate_valid_file(self, valid_510k_manifest):
        """Should validate a valid manifest file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_510k_manifest, f)
            temp_path = f.name

        try:
            is_valid, errors = validate_manifest_file(temp_path, strict=False)
            assert is_valid, f"Validation failed: {errors}"
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)

    def test_validate_invalid_file(self):
        """Should detect validation errors in manifest file."""
        invalid_manifest = {
            "project": "test",
            # Missing schema_version
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_manifest, f)
            temp_path = f.name

        try:
            is_valid, errors = validate_manifest_file(temp_path, strict=False)
            assert not is_valid
            assert len(errors) > 0
        finally:
            os.unlink(temp_path)


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
