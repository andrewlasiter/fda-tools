"""Tests for v5.22.0 — End-to-End Decision Traceability.

Covers: schema extensions (parent_entry_id, related_entries), 7 new action types,
command instrumentation (compare-se, presub, submission-outline, research),
agent instrumentation (presub-planner, extraction-analyzer, submission-assembler,
data-pipeline-manager), review.json audit_entry_id integration, and documentation.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

import fda_audit_logger as logger

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════════
# 1. Schema Extension Tests (8 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestSchemaExtensions(unittest.TestCase):
    """Test parent_entry_id and related_entries schema fields."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        os.rmdir(self.tmpdir)

    def test_parent_entry_id_accepted(self):
        """parent_entry_id field is accepted and written to JSONL."""
        entry = {
            "command": "compare-se",
            "action": "predicate_inferred",
            "mode": "auto",
            "parent_entry_id": "abc12345",
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["parent_entry_id"], "abc12345")

    def test_related_entries_accepted(self):
        """related_entries field is accepted and written to JSONL."""
        entry = {
            "command": "compare-se",
            "action": "table_generated",
            "mode": "auto",
            "related_entries": ["entry1", "entry2", "entry3"],
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["related_entries"], ["entry1", "entry2", "entry3"])

    def test_parent_and_related_together(self):
        """Both parent_entry_id and related_entries can coexist."""
        entry = {
            "command": "presub",
            "action": "qsub_type_recommended",
            "mode": "pipeline",
            "parent_entry_id": "parent1",
            "related_entries": ["rel1", "rel2"],
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["parent_entry_id"], "parent1")
        self.assertEqual(data["related_entries"], ["rel1", "rel2"])

    def test_empty_parent_entry_id_stripped(self):
        """Empty parent_entry_id is stripped from output."""
        entry = {
            "command": "review",
            "action": "predicate_accepted",
            "mode": "auto",
            "parent_entry_id": "",
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertNotIn("parent_entry_id", data)

    def test_empty_related_entries_stripped(self):
        """Empty related_entries list is stripped from output."""
        entry = {
            "command": "review",
            "action": "predicate_accepted",
            "mode": "auto",
            "related_entries": [],
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertNotIn("related_entries", data)

    def test_parent_entry_id_in_query_display(self):
        """parent_entry_id appears in print_query_results output."""
        entry = {
            "command": "compare-se",
            "action": "predicate_inferred",
            "mode": "auto",
            "parent_entry_id": "xyz789",
            "timestamp": "2026-02-09T12:00:00Z",
            "version": "5.22.0",
            "entry_id": "test1",
        }
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            logger.print_query_results([entry])
        output = buf.getvalue()
        self.assertIn("Parent: xyz789", output)

    def test_related_entries_in_query_display(self):
        """related_entries appear in print_query_results output."""
        entry = {
            "command": "compare-se",
            "action": "table_generated",
            "mode": "auto",
            "related_entries": ["aaa", "bbb"],
            "timestamp": "2026-02-09T12:00:00Z",
            "version": "5.22.0",
            "entry_id": "test2",
        }
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            logger.print_query_results([entry])
        output = buf.getvalue()
        self.assertIn("Related: aaa, bbb", output)

    def test_cli_parent_entry_id_argument(self):
        """CLI --parent-entry-id argument is accepted."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "fda_audit_logger.py"),
             "--project", "test_v522",
             "--command", "compare-se",
             "--action", "predicate_inferred",
             "--parent-entry-id", "cli_parent_test",
             "--mode", "auto"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertIn("AUDIT_STATUS:OK", result.stdout)

    # Note: The entry is written to ~/fda-510k-data/projects/test_v522/
    # which is acceptable for testing; cleanup not needed for transient tests


# ═══════════════════════════════════════════════════════════════════════
# 2. Action Type Tests (7 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestNewActionTypes(unittest.TestCase):
    """Test all 7 new action types from v5.22.0."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        os.rmdir(self.tmpdir)

    def _test_action(self, action_name):
        """Helper to test a single action type."""
        entry = {
            "command": "test",
            "action": action_name,
            "mode": "auto",
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [], f"Action '{action_name}' should be valid")
        return entry_id

    def test_template_selected(self):
        self._test_action("template_selected")

    def test_comparison_decision(self):
        self._test_action("comparison_decision")

    def test_qsub_type_recommended(self):
        self._test_action("qsub_type_recommended")

    def test_predicate_ranked(self):
        self._test_action("predicate_ranked")

    def test_report_generated(self):
        self._test_action("report_generated")

    def test_testing_gap_identified(self):
        self._test_action("testing_gap_identified")

    def test_section_applicability_determined(self):
        self._test_action("section_applicability_determined")


# ═══════════════════════════════════════════════════════════════════════
# 3. Command Instrumentation Tests (4 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestCommandInstrumentation(unittest.TestCase):
    """Verify commands have fda_audit_logger calls."""

    def _read_command(self, name):
        path = os.path.join(PLUGIN_ROOT, "commands", f"{name}.md")
        with open(path) as f:
            return f.read()

    def test_compare_se_has_audit_calls(self):
        """compare-se.md has at least 3 fda_audit_logger calls."""
        content = self._read_command("compare-se")
        count = content.count("fda_audit_logger.py")
        self.assertGreaterEqual(count, 3,
            f"compare-se.md should have >=3 audit logger calls, found {count}")

    def test_presub_has_audit_calls(self):
        """presub.md has at least 3 fda_audit_logger calls."""
        content = self._read_command("presub")
        count = content.count("fda_audit_logger.py")
        self.assertGreaterEqual(count, 3,
            f"presub.md should have >=3 audit logger calls, found {count}")

    def test_submission_outline_has_audit_calls(self):
        """submission-outline.md has at least 3 fda_audit_logger calls."""
        content = self._read_command("submission-outline")
        count = content.count("fda_audit_logger.py")
        self.assertGreaterEqual(count, 3,
            f"submission-outline.md should have >=3 audit logger calls, found {count}")

    def test_research_has_audit_calls(self):
        """research.md has at least 3 fda_audit_logger calls."""
        content = self._read_command("research")
        count = content.count("fda_audit_logger.py")
        self.assertGreaterEqual(count, 3,
            f"research.md should have >=3 audit logger calls, found {count}")


# ═══════════════════════════════════════════════════════════════════════
# 4. Agent Instrumentation Tests (4 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestAgentInstrumentation(unittest.TestCase):
    """Verify agents have audit logging sections."""

    def _read_agent(self, name):
        path = os.path.join(PLUGIN_ROOT, "agents", f"{name}.md")
        with open(path) as f:
            return f.read()

    def test_presub_planner_has_audit(self):
        """presub-planner.md has audit logging section with logger calls."""
        content = self._read_agent("presub-planner")
        self.assertIn("## Audit Logging", content)
        self.assertIn("fda_audit_logger.py", content)

    def test_extraction_analyzer_has_audit(self):
        """extraction-analyzer.md has audit logging section with logger calls."""
        content = self._read_agent("extraction-analyzer")
        self.assertIn("## Audit Logging", content)
        self.assertIn("fda_audit_logger.py", content)

    def test_submission_assembler_has_audit(self):
        """submission-assembler.md has audit logging section with logger calls."""
        content = self._read_agent("submission-assembler")
        self.assertIn("## Audit Logging", content)
        self.assertIn("fda_audit_logger.py", content)

    def test_data_pipeline_manager_has_audit(self):
        """data-pipeline-manager.md has audit logging section with logger calls."""
        content = self._read_agent("data-pipeline-manager")
        self.assertIn("## Audit Logging", content)
        self.assertIn("fda_audit_logger.py", content)


# ═══════════════════════════════════════════════════════════════════════
# 5. review.json Integration Tests (3 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestReviewJsonIntegration(unittest.TestCase):
    """Verify review.json audit_entry_id integration."""

    def _read_review_md(self):
        path = os.path.join(PLUGIN_ROOT, "commands", "review.md")
        with open(path) as f:
            return f.read()

    def test_audit_entry_id_in_schema(self):
        """review.md JSON schema example includes audit_entry_id."""
        content = self._read_review_md()
        self.assertIn('"audit_entry_id"', content)

    def test_audit_output_capture_pattern(self):
        """review.md uses AUDIT_OUTPUT capture pattern."""
        content = self._read_review_md()
        self.assertIn("AUDIT_OUTPUT=$(python3", content)
        self.assertIn("AUDIT_ENTRY_ID=$(echo", content)

    def test_audit_entry_id_comment(self):
        """review.md has comment about writing audit_entry_id to review.json."""
        content = self._read_review_md()
        self.assertIn("audit_entry_id", content)
        # Should appear in both the schema and the logging section
        count = content.count("audit_entry_id")
        self.assertGreaterEqual(count, 2,
            f"audit_entry_id should appear at least twice in review.md, found {count}")


# ═══════════════════════════════════════════════════════════════════════
# 6. Documentation Tests (3 tests)
# ═══════════════════════════════════════════════════════════════════════

class TestDocumentation(unittest.TestCase):
    """Verify documentation updates for v5.22.0."""

    def _read_reference(self, name):
        path = os.path.join(PLUGIN_ROOT, "references", name)
        with open(path) as f:
            return f.read()

    def test_decision_traceability_cross_command_linking(self):
        """decision-traceability.md documents cross-command linking."""
        content = self._read_reference("decision-traceability.md")
        self.assertIn("parent_entry_id", content)
        self.assertIn("related_entries", content)
        self.assertIn("Cross-Command Linking", content)

    def test_audit_logging_new_fields(self):
        """audit-logging.md documents parent_entry_id and related_entries."""
        content = self._read_reference("audit-logging.md")
        self.assertIn("parent_entry_id", content)
        self.assertIn("related_entries", content)
        self.assertIn("Parent-Child Linking", content)

    def test_audit_logging_new_action_types(self):
        """audit-logging.md documents all 7 new action types."""
        content = self._read_reference("audit-logging.md")
        new_actions = [
            "template_selected", "comparison_decision",
            "qsub_type_recommended", "predicate_ranked",
            "report_generated", "testing_gap_identified",
            "section_applicability_determined",
        ]
        for action in new_actions:
            self.assertIn(action, content,
                f"audit-logging.md should document action '{action}'")


# ═══════════════════════════════════════════════════════════════════════
# 7. Version Tests
# ═══════════════════════════════════════════════════════════════════════

class TestVersion(unittest.TestCase):
    """Verify version is updated to 5.22.0."""

    def test_logger_version(self):
        """fda_audit_logger.py PLUGIN_VERSION is 5.22.0."""
        self.assertEqual(logger.PLUGIN_VERSION, "5.22.0")

    def test_logger_writes_522_version(self):
        """New entries are stamped with version 5.22.0."""
        tmpdir = tempfile.mkdtemp()
        try:
            entry = {
                "command": "test",
                "action": "predicate_accepted",
                "mode": "auto",
            }
            logger.append_entry(tmpdir, entry)
            log_path = os.path.join(tmpdir, "audit_log.jsonl")
            with open(log_path) as f:
                data = json.loads(f.readline())
            self.assertEqual(data["version"], "5.22.0")
        finally:
            log_path = os.path.join(tmpdir, "audit_log.jsonl")
            if os.path.exists(log_path):
                os.remove(log_path)
            os.rmdir(tmpdir)


if __name__ == "__main__":
    unittest.main()
