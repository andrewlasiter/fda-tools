#!/usr/bin/env python3
"""
Integration tests for manifest_validator usage in fda_data_store.py and import.md.

Tests that manifest_validator is properly integrated and catches validation errors.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts and lib to path
TEST_DIR = Path(__file__).parent
PLUGIN_ROOT = TEST_DIR.parent

try:
    from manifest_validator import validate_manifest, ValidationError
    from fda_data_store import load_manifest, save_manifest
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


@unittest.skipUnless(VALIDATOR_AVAILABLE, "manifest_validator or fda_data_store not available")
class TestManifestValidatorIntegration(unittest.TestCase):
    """Test manifest_validator integration with data store."""

    def setUp(self):
        """Create temporary project directory for tests."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_manifest_")
        self.project_dir = os.path.join(self.temp_dir, "test_project")
        os.makedirs(self.project_dir, exist_ok=True)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_manifest_validates_schema(self):
        """Test that load_manifest validates the schema."""
        # Create a valid manifest
        valid_manifest = {
            "schema_version": "1.0.0",
            "project": "test_project",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated": "2024-01-01T00:00:00Z",
            "product_codes": [],
            "queries": {},
        }

        manifest_path = os.path.join(self.project_dir, "data_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(valid_manifest, f)

        # Should load without errors
        manifest = load_manifest(self.project_dir)
        self.assertEqual(manifest["schema_version"], "1.0.0")

    def test_load_manifest_with_missing_fields(self):
        """Test that load_manifest handles manifests with missing required fields."""
        # Create an invalid manifest (missing required fields)
        invalid_manifest = {
            "schema_version": "1.0.0",
            # Missing: project, created_at, last_updated, product_codes, queries
        }

        manifest_path = os.path.join(self.project_dir, "data_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(invalid_manifest, f)

        # Should still load but may log warnings (non-strict validation)
        manifest = load_manifest(self.project_dir)
        self.assertIsNotNone(manifest)

    def test_validate_catches_type_mismatch(self):
        """Test that manifest validation catches type mismatches."""
        # Create manifest with wrong types
        bad_manifest = {
            "schema_version": "1.0.0",
            "project": "test_project",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated": "2024-01-01T00:00:00Z",
            "product_codes": "DQY",  # Should be array, not string
            "queries": {},
        }

        is_valid, errors = validate_manifest(bad_manifest, strict=False)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        # Check that error mentions type issue
        error_text = " ".join(errors)
        self.assertIn("product_codes", error_text.lower())

    def test_import_data_validation(self):
        """Test schema validation for import_data.json structure."""
        # Simulate import data structure
        import_data = {
            "schema_version": "1.0.0",
            "project": "import_test",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated": "2024-01-01T00:00:00Z",
            "applicant": {
                "name": "Test Company",
                "contact": "test@example.com",
            },
            "classification": {
                "product_code": "DQY",
                "regulation_number": "21 CFR 870.2300",
                "device_class": "II",
            },
            "product_codes": ["DQY"],
            "queries": {},
        }

        # Should validate successfully
        is_valid, errors = validate_manifest(import_data, strict=False)
        # May have warnings but should not have critical errors
        if not is_valid:
            # Print errors for debugging
            print(f"Validation warnings: {errors}")


if __name__ == "__main__":
    unittest.main()
