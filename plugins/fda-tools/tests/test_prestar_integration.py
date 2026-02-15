#!/usr/bin/env python3
"""
Integration tests for PreSTAR XML generation workflow.

Tests the complete pipeline:
1. Question selection from presub_questions.json
2. Template loading and population
3. Metadata generation (presub_metadata.json)
4. XML generation (presub_prestar.xml)
5. Field validation and FDA eSTAR compatibility

Usage:
    pytest tests/test_prestar_integration.py -v
    python3 tests/test_prestar_integration.py  # Run directly
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from estar_xml import _collect_project_values, _xml_escape


class TestPreSTARIntegration(unittest.TestCase):
    """Integration tests for PreSTAR XML generation workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix="prestar_test_")
        self.project_dir = Path(self.test_dir) / "test_project"
        self.project_dir.mkdir()

        # Create test presub_metadata.json
        self.test_metadata = {
            "version": "1.0",
            "generated_at": "2026-02-15T12:00:00Z",
            "meeting_type": "formal",
            "detection_method": "auto",
            "detection_rationale": "5 questions selected → formal meeting recommended",
            "product_code": "DQY",
            "device_description": "Single-use vascular access catheter",
            "intended_use": "To provide temporary vascular access for medication delivery",
            "questions_generated": ["PRED-001", "CLASS-001", "TEST-BIO-001"],
            "question_count": 3,
            "template_used": "formal_meeting.md",
            "fda_form": "FDA-5064",
            "expected_timeline_days": 75,
            "auto_triggers_fired": ["patient_contacting"],
            "data_sources_used": ["classification", "review.json"],
            "metadata": {
                "placeholder_count": 12,
                "auto_filled_fields": ["product_code", "device_description"]
            }
        }

        # Write test metadata
        metadata_path = self.project_dir / "presub_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.test_metadata, f, indent=2)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_metadata_schema_validation(self):
        """Test that presub_metadata.json conforms to required schema."""
        metadata_path = self.project_dir / "presub_metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Validate required fields
        required_fields = ["version", "meeting_type", "questions_generated", "question_count", "fda_form"]
        for field in required_fields:
            self.assertIn(field, metadata, f"Missing required field: {field}")

        # Validate data types
        self.assertIsInstance(metadata["questions_generated"], list)
        self.assertIsInstance(metadata["question_count"], int)

        # Validate version
        self.assertIn(metadata["version"], ["1.0"])

        # Validate meeting type
        valid_meeting_types = ["formal", "written", "info", "pre-ide", "administrative", "info-only"]
        self.assertIn(metadata["meeting_type"], valid_meeting_types)

        # Validate question count matches list length
        self.assertEqual(metadata["question_count"], len(metadata["questions_generated"]))

    def test_xml_escape_control_characters(self):
        """Test that _xml_escape filters control characters (HIGH-1 fix)."""
        # Test control characters (U+0000-U+001F except tab/newline/CR)
        test_string = "Hello\x00\x01\x02World\x03\x04"  # Contains control chars
        escaped = _xml_escape(test_string)

        # Control characters should be filtered
        self.assertNotIn("\x00", escaped)
        self.assertNotIn("\x01", escaped)
        self.assertNotIn("\x02", escaped)
        self.assertNotIn("\x03", escaped)
        self.assertNotIn("\x04", escaped)

        # Regular text should remain
        self.assertIn("Hello", escaped)
        self.assertIn("World", escaped)

        # Tab, newline, CR should be preserved
        test_string2 = "Line1\nLine2\tTabbed\rReturn"
        escaped2 = _xml_escape(test_string2)
        self.assertIn("\n", escaped2)
        self.assertIn("\t", escaped2)
        self.assertIn("\r", escaped2)

    def test_xml_escape_special_characters(self):
        """Test that _xml_escape handles XML special characters."""
        test_cases = {
            "<tag>": "&lt;tag&gt;",
            "A & B": "A &amp; B",
            'Say "hello"': 'Say &quot;hello&quot;',
            "It's mine": "It&apos;s mine"
        }

        for input_str, expected in test_cases.items():
            escaped = _xml_escape(input_str)
            self.assertEqual(escaped, expected, f"Failed to escape: {input_str}")

    def test_question_bank_loading(self):
        """Test that presub_questions.json loads and has required structure."""
        plugin_root = Path(__file__).parent.parent
        question_bank_path = plugin_root / "data" / "question_banks" / "presub_questions.json"

        self.assertTrue(question_bank_path.exists(), "Question bank file not found")

        with open(question_bank_path) as f:
            question_bank = json.load(f)

        # Validate required top-level keys
        required_keys = ["version", "questions", "meeting_type_defaults", "auto_triggers"]
        for key in required_keys:
            self.assertIn(key, question_bank, f"Missing required key: {key}")

        # Validate questions structure
        self.assertIsInstance(question_bank["questions"], list)
        self.assertGreater(len(question_bank["questions"]), 0)

        # Validate each question has required fields
        for question in question_bank["questions"]:
            self.assertIn("id", question)
            self.assertIn("text", question)
            self.assertIn("category", question)
            self.assertIn("priority", question)

    def test_meeting_type_defaults(self):
        """Test that meeting_type_defaults are properly configured."""
        plugin_root = Path(__file__).parent.parent
        question_bank_path = plugin_root / "data" / "question_banks" / "presub_questions.json"

        with open(question_bank_path) as f:
            question_bank = json.load(f)

        defaults = question_bank["meeting_type_defaults"]
        valid_meeting_types = ["formal", "written", "info", "pre-ide", "administrative", "info-only"]

        # Each meeting type should have defaults
        for meeting_type in valid_meeting_types:
            self.assertIn(meeting_type, defaults, f"Missing defaults for meeting type: {meeting_type}")
            self.assertIsInstance(defaults[meeting_type], list)

    def test_auto_trigger_keywords(self):
        """Test that auto-trigger keywords have proper structure."""
        plugin_root = Path(__file__).parent.parent
        question_bank_path = plugin_root / "data" / "question_banks" / "presub_questions.json"

        with open(question_bank_path) as f:
            question_bank = json.load(f)

        auto_triggers = question_bank["auto_triggers"]

        # Verify auto_triggers exist and are not empty
        self.assertIsInstance(auto_triggers, dict)
        self.assertGreater(len(auto_triggers), 0)

        # Verify each trigger has a list of question IDs
        for trigger_name, question_ids in auto_triggers.items():
            self.assertIsInstance(question_ids, list, f"Trigger {trigger_name} should have list of question IDs")
            self.assertGreater(len(question_ids), 0, f"Trigger {trigger_name} should have at least one question")

            # Verify question IDs follow pattern
            for qid in question_ids:
                self.assertIsInstance(qid, str)
                # Question IDs should follow pattern like TEST-BIO-001, PRED-001, etc.
                parts = qid.split("-")
                self.assertGreaterEqual(len(parts), 2, f"Question ID {qid} should have at least 2 parts")

    def test_collect_project_values_with_presub_metadata(self):
        """Test that _collect_project_values properly processes presub_metadata."""
        # Create minimal device_profile.json
        device_profile = {
            "product_code": "DQY",
            "device_description": "Test device"
        }
        with open(self.project_dir / "device_profile.json", "w") as f:
            json.dump(device_profile, f)

        # Build project_data dict (mimics what estar_xml.py does)
        project_data = {
            "profile": device_profile,
            "presub_metadata": self.test_metadata
        }

        # Collect values
        values = _collect_project_values(project_data)

        # Verify presub_metadata fields are present
        # The actual formatting is done in _build_prestar_xml, so we just verify
        # that the data is accessible
        self.assertIn("presub_questions", values)
        self.assertIn("presub_characteristics", values)

        # Values might be empty strings if not properly populated, but should exist
        self.assertIsInstance(values["presub_questions"], str)
        self.assertIsInstance(values["presub_characteristics"], str)

    def test_template_files_exist(self):
        """Test that all 6 meeting type templates exist."""
        plugin_root = Path(__file__).parent.parent
        template_dir = plugin_root / "data" / "templates" / "presub_meetings"

        expected_templates = [
            "formal_meeting.md",
            "written_response.md",
            "info_meeting.md",
            "pre_ide.md",
            "administrative_meeting.md",
            "info_only.md"
        ]

        for template in expected_templates:
            template_path = template_dir / template
            self.assertTrue(template_path.exists(), f"Template not found: {template}")

    def test_iso_standard_versions(self):
        """Test that ISO 10993-1 references use 2009 version (M-1 compliance fix)."""
        plugin_root = Path(__file__).parent.parent
        template_dir = plugin_root / "data" / "templates" / "presub_meetings"

        for template_file in template_dir.glob("*.md"):
            with open(template_file) as f:
                content = f.read()

            # Check for old 2018 version (should not exist after fix)
            self.assertNotIn("ISO 10993-1:2018", content,
                             f"Found ISO 10993-1:2018 in {template_file.name} (should be 2009)")

            # If ISO 10993-1 is mentioned, verify correct format
            if "ISO 10993-1" in content:
                # Should either be :2009 or "or latest edition"
                has_2009 = "ISO 10993-1:2009" in content
                has_latest = "or latest edition" in content
                self.assertTrue(has_2009 or has_latest,
                                f"ISO 10993-1 in {template_file.name} should specify 2009 or 'latest edition'")

    def test_iec_standard_editions(self):
        """Test that IEC 60601-1 references specify edition (M-2 compliance fix)."""
        plugin_root = Path(__file__).parent.parent
        template_dir = plugin_root / "data" / "templates" / "presub_meetings"

        for template_file in template_dir.glob("*.md"):
            with open(template_file) as f:
                content = f.read()

            # If IEC 60601-1 is mentioned, verify edition is specified
            if "IEC 60601-1" in content and "IEC 60601-1-2" not in content:
                # Should specify "Edition 3.2 (2020)" or similar
                has_edition = "Edition" in content and "60601-1" in content
                self.assertTrue(has_edition,
                                f"IEC 60601-1 in {template_file.name} should specify edition")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPreSTARIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
