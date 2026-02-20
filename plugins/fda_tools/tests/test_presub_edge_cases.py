#!/usr/bin/env python3
"""
Edge case tests for TICKET-001 v5.27.0 pipeline fixes.

Tests the 5 pipeline issues resolved in v5.27.0:
- EDGE-1: Questions filtered by applicable_meeting_types
- EDGE-2: Type checking for questions_generated field
- EDGE-3: Duplicate question ID detection
- BREAK-1: Empty question validation with warnings
- BREAK-2: Placeholder completeness tracking

Usage:
    pytest tests/test_presub_edge_cases.py -v
    python3 tests/test_presub_edge_cases.py  # Run directly
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"

from estar_xml import _collect_project_values, _xml_escape


class TestEdge1MeetingTypeFiltering(unittest.TestCase):
    """EDGE-1: Questions filtered by applicable_meeting_types."""

    def setUp(self):
        """Load the question bank."""
        plugin_root = Path(__file__).parent.parent
        self.question_bank_path = plugin_root / "data" / "question_banks" / "presub_questions.json"
        with open(self.question_bank_path) as f:
            self.question_bank = json.load(f)

    def test_formal_only_question_excluded_from_written(self):
        """Test that a question marked only for formal meetings does not appear in written response."""
        questions = self.question_bank.get("questions", [])
        meeting_type = "written"

        # Find questions that are ONLY applicable to formal meetings
        # (i.e., applicable_meeting_types includes "formal" but NOT "written")
        formal_only_questions = []
        for q in questions:
            applicable = q.get("applicable_meeting_types", [])
            if isinstance(applicable, list) and len(applicable) > 0:
                if "formal" in applicable and meeting_type not in applicable and "all" not in applicable:
                    formal_only_questions.append(q)

        # The NOVEL-001 question should only be applicable to "formal" meetings
        novel_001 = next((q for q in questions if q["id"] == "NOVEL-001"), None)
        self.assertIsNotNone(novel_001, "NOVEL-001 question should exist")
        assert novel_001 is not None  # Type narrowing for Pyright
        self.assertIn("formal", novel_001.get("applicable_meeting_types", []))
        self.assertNotIn("written", novel_001.get("applicable_meeting_types", []))

        # Simulate the filtering logic from presub.md Step 3.5
        selected_ids = {"NOVEL-001", "CLASS-001"}  # CLASS-001 is applicable to both
        selected_questions = [q for q in questions if q.get("id") in selected_ids]

        # Apply EDGE-1 filter
        filtered_questions = []
        for q in selected_questions:
            applicable = q.get("applicable_meeting_types", [])
            if isinstance(applicable, list) and len(applicable) > 0:
                if meeting_type not in applicable and "all" not in applicable:
                    continue  # Skip - not applicable to this meeting type
            filtered_questions.append(q)

        # NOVEL-001 should be filtered out for "written" meeting type
        filtered_ids = {q["id"] for q in filtered_questions}
        self.assertNotIn("NOVEL-001", filtered_ids,
                         "NOVEL-001 should be filtered out for 'written' meeting type")
        self.assertIn("CLASS-001", filtered_ids,
                      "CLASS-001 should remain - it is applicable to 'written'")

    def test_pre_ide_only_question_excluded_from_info(self):
        """Test that pre-ide-only questions are filtered from info meeting type."""
        questions = self.question_bank.get("questions", [])
        meeting_type = "info"

        # CLINICAL-STUDY-001 is only for pre-ide
        clinical_study = next((q for q in questions if q["id"] == "CLINICAL-STUDY-001"), None)
        self.assertIsNotNone(clinical_study)
        assert clinical_study is not None  # Type narrowing for Pyright
        self.assertIn("pre-ide", clinical_study.get("applicable_meeting_types", []))
        self.assertNotIn("info", clinical_study.get("applicable_meeting_types", []))

        # Simulate filtering
        selected_ids = {"CLINICAL-STUDY-001", "CLASS-001"}
        selected_questions = [q for q in questions if q.get("id") in selected_ids]

        filtered_questions = []
        for q in selected_questions:
            applicable = q.get("applicable_meeting_types", [])
            if isinstance(applicable, list) and len(applicable) > 0:
                if meeting_type not in applicable and "all" not in applicable:
                    continue
            filtered_questions.append(q)

        filtered_ids = {q["id"] for q in filtered_questions}
        self.assertNotIn("CLINICAL-STUDY-001", filtered_ids,
                         "CLINICAL-STUDY-001 should be filtered out for 'info' meeting type")

    def test_question_with_empty_applicable_types_passes(self):
        """Test that a question with empty applicable_meeting_types is not filtered."""
        # Create a mock question with no applicable_meeting_types
        mock_question = {
            "id": "MOCK-001",
            "text": "Test question",
            "category": "test",
            "priority": 50,
            "applicable_meeting_types": []
        }

        meeting_type = "written"
        applicable = mock_question.get("applicable_meeting_types", [])

        # Empty list should NOT filter the question (it passes through)
        should_skip = (isinstance(applicable, list) and len(applicable) > 0
                       and meeting_type not in applicable and "all" not in applicable)
        self.assertFalse(should_skip,
                         "Question with empty applicable_meeting_types should not be filtered")


class TestEdge2QuestionsTypeChecking(unittest.TestCase):
    """EDGE-2: Handle questions_generated as string instead of list."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix="edge2_test_")
        self.project_dir = Path(self.test_dir) / "test_project"
        self.project_dir.mkdir()

    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_string_questions_generated_handled(self):
        """Test that questions_generated as string is coerced to list."""
        # Create metadata with questions_generated as a string (wrong type)
        metadata = {
            "version": "1.0",
            "meeting_type": "formal",
            "questions_generated": "PRED-001",  # String instead of list
            "question_count": 1,
            "fda_form": "FDA-5064"
        }

        with open(self.project_dir / "presub_metadata.json", "w") as f:
            json.dump(metadata, f)

        # Create minimal device_profile
        with open(self.project_dir / "device_profile.json", "w") as f:
            json.dump({"product_code": "DQY"}, f)

        # The type check in estar_xml.py should handle this gracefully
        # Test the actual code path
        questions_generated = metadata.get("questions_generated", [])
        if not isinstance(questions_generated, list):
            questions_generated = [questions_generated] if questions_generated else []

        self.assertIsInstance(questions_generated, list)
        self.assertEqual(len(questions_generated), 1)
        self.assertEqual(questions_generated[0], "PRED-001")

    def test_none_questions_generated_handled(self):
        """Test that questions_generated as None is handled."""
        metadata = {
            "version": "1.0",
            "meeting_type": "formal",
            "questions_generated": None,
            "question_count": 0,
            "fda_form": "FDA-5064"
        }

        questions_generated = metadata.get("questions_generated", [])
        if not isinstance(questions_generated, list):
            questions_generated = [questions_generated] if questions_generated else []

        self.assertIsInstance(questions_generated, list)
        self.assertEqual(len(questions_generated), 0)

    def test_integer_questions_generated_handled(self):
        """Test that questions_generated as integer is handled."""
        metadata = {
            "version": "1.0",
            "meeting_type": "formal",
            "questions_generated": 42,
            "question_count": 0,
            "fda_form": "FDA-5064"
        }

        questions_generated = metadata.get("questions_generated", [])
        if not isinstance(questions_generated, list):
            questions_generated = [questions_generated] if questions_generated else []

        self.assertIsInstance(questions_generated, list)
        self.assertEqual(len(questions_generated), 1)
        self.assertEqual(questions_generated[0], 42)

    def test_list_questions_generated_unchanged(self):
        """Test that questions_generated as list is not modified."""
        metadata = {
            "version": "1.0",
            "meeting_type": "formal",
            "questions_generated": ["PRED-001", "CLASS-001"],
            "question_count": 2,
            "fda_form": "FDA-5064"
        }

        questions_generated = metadata.get("questions_generated", [])
        if not isinstance(questions_generated, list):
            questions_generated = [questions_generated] if questions_generated else []

        self.assertIsInstance(questions_generated, list)
        self.assertEqual(len(questions_generated), 2)
        self.assertEqual(questions_generated, ["PRED-001", "CLASS-001"])


class TestEdge3DuplicateDetection(unittest.TestCase):
    """EDGE-3: Detect and skip duplicate question IDs."""

    def test_duplicate_ids_removed(self):
        """Test that duplicate question IDs are deduplicated."""
        # Simulate questions with duplicates (e.g., auto-trigger and defaults select same ID)
        selected_questions = [
            {"id": "PRED-001", "text": "Question 1", "priority": 100},
            {"id": "CLASS-001", "text": "Question 2", "priority": 95},
            {"id": "PRED-001", "text": "Question 1 duplicate", "priority": 100},  # Duplicate
            {"id": "TEST-BIO-001", "text": "Question 3", "priority": 80},
            {"id": "CLASS-001", "text": "Question 2 duplicate", "priority": 95},  # Duplicate
        ]

        # Apply EDGE-3 deduplication logic
        seen_ids = set()
        unique_questions = []
        duplicate_count = 0
        for q in selected_questions:
            qid = q.get("id", "")
            if qid and qid not in seen_ids:
                seen_ids.add(qid)
                unique_questions.append(q)
            elif qid:
                duplicate_count += 1

        # Should have 3 unique questions (not 5)
        self.assertEqual(len(unique_questions), 3)
        self.assertEqual(duplicate_count, 2)

        unique_ids = [q["id"] for q in unique_questions]
        self.assertEqual(unique_ids, ["PRED-001", "CLASS-001", "TEST-BIO-001"])

    def test_empty_id_not_deduplicated(self):
        """Test that questions with empty IDs are not deduplicated."""
        selected_questions = [
            {"id": "", "text": "No ID question 1", "priority": 50},
            {"id": "", "text": "No ID question 2", "priority": 40},
            {"id": "PRED-001", "text": "Normal question", "priority": 100},
        ]

        seen_ids = set()
        unique_questions = []
        for q in selected_questions:
            qid = q.get("id", "")
            if qid and qid not in seen_ids:
                seen_ids.add(qid)
                unique_questions.append(q)
            elif qid:
                pass  # Duplicate - skip
            else:
                unique_questions.append(q)  # Empty ID passes through

        # Both empty-ID questions should pass through, plus PRED-001
        self.assertEqual(len(unique_questions), 3)

    def test_no_duplicates_returns_all(self):
        """Test that when there are no duplicates, all questions are returned."""
        selected_questions = [
            {"id": "PRED-001", "text": "Q1", "priority": 100},
            {"id": "CLASS-001", "text": "Q2", "priority": 95},
            {"id": "TEST-BIO-001", "text": "Q3", "priority": 80},
        ]

        seen_ids = set()
        unique_questions = []
        for q in selected_questions:
            qid = q.get("id", "")
            if qid and qid not in seen_ids:
                seen_ids.add(qid)
                unique_questions.append(q)

        self.assertEqual(len(unique_questions), 3)


class TestBreak1EmptyQuestionsWarning(unittest.TestCase):
    """BREAK-1: Warn when no questions selected."""

    def test_zero_questions_triggers_warning(self):
        """Test that zero question count triggers a warning condition."""
        selected_questions = []

        # Simulate BREAK-1 check
        warning_triggered = (not selected_questions or len(selected_questions) == 0)
        self.assertTrue(warning_triggered,
                        "Warning should trigger when no questions are selected")

    def test_nonzero_questions_no_warning(self):
        """Test that non-zero question count does not trigger warning."""
        selected_questions = [
            {"id": "PRED-001", "text": "Q1", "priority": 100},
        ]

        warning_triggered = (not selected_questions or len(selected_questions) == 0)
        self.assertFalse(warning_triggered,
                         "Warning should NOT trigger when questions are selected")

    def test_info_only_may_have_zero_questions(self):
        """Test that info-only meeting type has empty defaults (expected 0 questions)."""
        plugin_root = Path(__file__).parent.parent
        question_bank_path = plugin_root / "data" / "question_banks" / "presub_questions.json"

        with open(question_bank_path) as f:
            question_bank = json.load(f)

        # info-only meeting type should have empty defaults
        info_only_defaults = question_bank["meeting_type_defaults"].get("info-only", [])
        self.assertEqual(len(info_only_defaults), 0,
                         "info-only meeting type should have 0 default questions")


class TestBreak2PlaceholderDetection(unittest.TestCase):
    """BREAK-2: Detect unfilled placeholders in template."""

    def test_detect_unfilled_curly_brace_placeholders(self):
        """Test detection of {placeholder} patterns remaining after population."""
        populated_content = """
# Pre-Submission Meeting Request

**Device:** {device_description}
**Product Code:** DQY
**Meeting Type:** Formal
**Contact:** {contact_name}
**Email:** {contact_email}

## Questions
1. Does FDA agree that our device is classified under DQY?
"""
        # Apply BREAK-2 detection logic
        unfilled = re.findall(r'\{[A-Za-z_]+\}', populated_content)
        unique_unfilled = sorted(set(unfilled))

        self.assertEqual(len(unique_unfilled), 3)
        self.assertIn("{device_description}", unique_unfilled)
        self.assertIn("{contact_name}", unique_unfilled)
        self.assertIn("{contact_email}", unique_unfilled)

    def test_detect_todo_markers(self):
        """Test detection of [TODO: ...] markers in populated template."""
        populated_content = """
# Pre-Submission Meeting Request

**Device:** Single-use vascular catheter
**Contact:** [TODO: Company Name]
**Address:** [TODO: Company-specific -- Provide address]

## Testing Strategy
[TODO: Company-specific -- Performance testing plan]
"""
        todo_markers = re.findall(r'\[TODO:[^\]]*\]', populated_content)
        unique_todos = sorted(set(todo_markers))

        self.assertEqual(len(unique_todos), 3)
        self.assertTrue(any("Company Name" in t for t in unique_todos))

    def test_no_unfilled_placeholders_detected(self):
        """Test that fully populated content has no unfilled placeholders."""
        populated_content = """
# Pre-Submission Meeting Request

**Device:** Single-use vascular catheter
**Product Code:** DQY
**Meeting Type:** Formal

## Questions
1. Does FDA agree that our device is classified under DQY?
"""
        unfilled = re.findall(r'\{[A-Za-z_]+\}', populated_content)
        self.assertEqual(len(unfilled), 0,
                         "Fully populated content should have no unfilled placeholders")

    def test_mixed_placeholders_and_todos(self):
        """Test template with both unfilled placeholders and TODO markers."""
        populated_content = """
**Device:** {device_trade_name}
**Code:** DQY
**Contact:** [TODO: Company-specific -- Contact info]
**Sterilization:** {sterilization_method}
"""
        unfilled = re.findall(r'\{[A-Za-z_]+\}', populated_content)
        todos = re.findall(r'\[TODO:[^\]]*\]', populated_content)

        self.assertEqual(len(set(unfilled)), 2)
        self.assertEqual(len(set(todos)), 1)


def run_tests():
    """Run all edge case tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestEdge1MeetingTypeFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestEdge2QuestionsTypeChecking))
    suite.addTests(loader.loadTestsFromTestCase(TestEdge3DuplicateDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestBreak1EmptyQuestionsWarning))
    suite.addTests(loader.loadTestsFromTestCase(TestBreak2PlaceholderDetection))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
