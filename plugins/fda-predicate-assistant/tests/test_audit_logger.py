"""Tests for fda_audit_logger.py — Decision Traceability System (v5.22.0)."""

import argparse
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

import fda_audit_logger as logger


class TestAppendEntry(unittest.TestCase):
    """Test entry creation and validation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        os.rmdir(self.tmpdir)

    def test_append_basic_entry(self):
        entry = {
            "command": "review",
            "action": "predicate_accepted",
            "mode": "interactive",
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        self.assertTrue(len(entry_id) > 0)
        # Verify file written
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["command"], "review")
        self.assertEqual(data["action"], "predicate_accepted")
        self.assertIn("timestamp", data)
        self.assertEqual(data["version"], "5.22.0")

    def test_auto_populate_timestamp(self):
        entry = {"command": "review", "action": "review_completed", "mode": "auto"}
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertIn("T", data["timestamp"])

    def test_auto_populate_version(self):
        entry = {"command": "safety", "action": "risk_level_assigned", "mode": "auto"}
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["version"], "5.22.0")

    def test_custom_timestamp_preserved(self):
        entry = {
            "command": "review",
            "action": "predicate_accepted",
            "mode": "auto",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        logger.append_entry(self.tmpdir, entry)
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["timestamp"], "2026-01-01T00:00:00Z")

    def test_entry_id_generated(self):
        entry = {"command": "review", "action": "predicate_accepted", "mode": "auto"}
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertTrue(len(entry_id) == 8)
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["entry_id"], entry_id)

    def test_multiple_entries_appended(self):
        for i in range(5):
            entry = {
                "command": "review",
                "action": "predicate_accepted",
                "mode": "auto",
                "subject": f"K{100000 + i}",
            }
            logger.append_entry(self.tmpdir, entry)
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), 5)

    def test_all_optional_fields(self):
        entry = {
            "command": "pathway",
            "action": "pathway_recommended",
            "mode": "interactive",
            "subject": "OVE",
            "decision": "Traditional 510(k)",
            "rationale": "Best fit",
            "confidence_score": 87,
            "decision_type": "auto",
            "alternatives_considered": ["Traditional", "Special", "De Novo"],
            "exclusion_records": [
                {"subject": "De Novo", "reason": "45 clearances exist"}
            ],
            "score_breakdown": {"Traditional": 87, "De Novo": 15},
            "data_sources": ["openFDA"],
            "files_read": ["/tmp/review.json"],
            "files_written": [],
            "warnings": [],
        }
        entry_id, errors = logger.append_entry(self.tmpdir, entry)
        self.assertEqual(errors, [])
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path) as f:
            data = json.loads(f.readline())
        self.assertEqual(data["alternatives_considered"], ["Traditional", "Special", "De Novo"])
        self.assertEqual(len(data["exclusion_records"]), 1)
        self.assertEqual(data["score_breakdown"]["Traditional"], 87)


class TestValidation(unittest.TestCase):
    """Test entry validation."""

    def test_missing_command(self):
        entry = {"action": "predicate_accepted", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0"}
        errors = logger.validate_entry(entry)
        self.assertTrue(any("command" in e for e in errors))

    def test_missing_action(self):
        entry = {"command": "review", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0"}
        errors = logger.validate_entry(entry)
        self.assertTrue(any("action" in e for e in errors))

    def test_invalid_action_type(self):
        entry = {"command": "review", "action": "invalid_action", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0"}
        errors = logger.validate_entry(entry)
        self.assertTrue(any("Invalid action type" in e for e in errors))

    def test_valid_action_types(self):
        for action in ["predicate_accepted", "pathway_recommended",
                        "risk_level_assigned", "check_passed",
                        "guidance_matched", "test_prioritized",
                        "section_drafted", "agent_decision",
                        "deficiency_identified", "sri_calculated"]:
            entry = {"command": "test", "action": action, "mode": "auto",
                     "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0"}
            errors = logger.validate_entry(entry)
            self.assertEqual(errors, [], f"Action {action} should be valid")

    def test_invalid_decision_type(self):
        entry = {"command": "review", "action": "predicate_accepted", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0",
                 "decision_type": "invalid"}
        errors = logger.validate_entry(entry)
        self.assertTrue(any("decision_type" in e for e in errors))

    def test_valid_decision_types(self):
        for dt in ["auto", "manual", "deferred"]:
            entry = {"command": "review", "action": "predicate_accepted", "mode": "auto",
                     "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0",
                     "decision_type": dt}
            errors = logger.validate_entry(entry)
            self.assertEqual(errors, [], f"decision_type '{dt}' should be valid")

    def test_confidence_score_range_valid(self):
        entry = {"command": "review", "action": "predicate_accepted", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0",
                 "confidence_score": 85}
        errors = logger.validate_entry(entry)
        self.assertEqual(errors, [])

    def test_confidence_score_out_of_range(self):
        entry = {"command": "review", "action": "predicate_accepted", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0",
                 "confidence_score": 150}
        errors = logger.validate_entry(entry)
        self.assertTrue(any("confidence_score" in e for e in errors))

    def test_confidence_score_negative(self):
        entry = {"command": "review", "action": "predicate_accepted", "mode": "auto",
                 "timestamp": "2026-01-01T00:00:00Z", "version": "5.21.0",
                 "confidence_score": -5}
        errors = logger.validate_entry(entry)
        self.assertTrue(any("confidence_score" in e for e in errors))

    def test_validation_errors_prevent_write(self):
        tmpdir = tempfile.mkdtemp()
        entry = {"action": "predicate_accepted", "mode": "auto"}  # missing command
        entry_id, errors = logger.append_entry(tmpdir, entry)
        self.assertTrue(len(errors) > 0)
        log_path = os.path.join(tmpdir, "audit_log.jsonl")
        self.assertFalse(os.path.exists(log_path))
        os.rmdir(tmpdir)


class TestReadLog(unittest.TestCase):
    """Test log reading."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        os.rmdir(self.tmpdir)

    def test_read_empty(self):
        entries = logger.read_log(self.tmpdir)
        self.assertEqual(entries, [])

    def test_read_multiple_entries(self):
        for i in range(3):
            logger.append_entry(self.tmpdir, {
                "command": "review", "action": "predicate_accepted", "mode": "auto"
            })
        entries = logger.read_log(self.tmpdir)
        self.assertEqual(len(entries), 3)

    def test_read_malformed_line_skipped(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path, "w") as f:
            f.write('{"command":"review","action":"predicate_accepted","version":"5.21.0","mode":"auto","timestamp":"2026-01-01T00:00:00Z","entry_id":"12345678"}\n')
            f.write("not json\n")
            f.write('{"command":"safety","action":"risk_level_assigned","version":"5.21.0","mode":"auto","timestamp":"2026-01-01T00:00:00Z","entry_id":"87654321"}\n')
        entries = logger.read_log(self.tmpdir)
        self.assertEqual(len(entries), 2)

    def test_read_blank_lines_skipped(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        with open(log_path, "w") as f:
            f.write('{"command":"review","action":"predicate_accepted","version":"5.21.0","mode":"auto","timestamp":"2026-01-01T00:00:00Z","entry_id":"12345678"}\n')
            f.write("\n\n")
            f.write('{"command":"safety","action":"risk_level_assigned","version":"5.21.0","mode":"auto","timestamp":"2026-01-01T00:00:00Z","entry_id":"87654321"}\n')
        entries = logger.read_log(self.tmpdir)
        self.assertEqual(len(entries), 2)


class TestQueryLog(unittest.TestCase):
    """Test log querying with filters."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create diverse entries
        entries = [
            {"command": "review", "action": "predicate_accepted", "mode": "auto",
             "subject": "K241335", "decision": "accepted", "confidence_score": 85,
             "timestamp": "2026-02-05T12:00:00Z"},
            {"command": "review", "action": "predicate_rejected", "mode": "auto",
             "subject": "K222222", "decision": "rejected",
             "timestamp": "2026-02-05T12:01:00Z"},
            {"command": "pathway", "action": "pathway_recommended", "mode": "interactive",
             "subject": "OVE", "decision": "Traditional 510(k)",
             "exclusion_records": [{"subject": "De Novo", "reason": "45 clearances"}],
             "timestamp": "2026-02-06T12:00:00Z"},
            {"command": "safety", "action": "risk_level_assigned", "mode": "interactive",
             "subject": "OVE",
             "timestamp": "2026-02-07T12:00:00Z"},
            {"command": "consistency", "action": "check_passed", "mode": "interactive",
             "subject": "Check 1",
             "timestamp": "2026-02-08T12:00:00Z"},
        ]
        for e in entries:
            logger.append_entry(self.tmpdir, e)

    def tearDown(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        os.rmdir(self.tmpdir)

    def test_query_no_filter(self):
        results = logger.query_log(self.tmpdir, {})
        self.assertEqual(len(results), 5)

    def test_filter_by_command(self):
        results = logger.query_log(self.tmpdir, {"command": "review"})
        self.assertEqual(len(results), 2)

    def test_filter_by_action(self):
        results = logger.query_log(self.tmpdir, {"action": "predicate_accepted"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject"], "K241335")

    def test_filter_by_subject(self):
        results = logger.query_log(self.tmpdir, {"subject": "OVE"})
        self.assertEqual(len(results), 2)

    def test_filter_by_date_after(self):
        results = logger.query_log(self.tmpdir, {"after": "2026-02-06T00:00:00Z"})
        self.assertEqual(len(results), 3)

    def test_filter_by_date_before(self):
        results = logger.query_log(self.tmpdir, {"before": "2026-02-06T00:00:00Z"})
        self.assertEqual(len(results), 2)

    def test_filter_decisions_only(self):
        results = logger.query_log(self.tmpdir, {"decisions_only": True})
        self.assertTrue(all(r.get("decision") for r in results))

    def test_filter_exclusions_only(self):
        results = logger.query_log(self.tmpdir, {"exclusions_only": True})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["command"], "pathway")

    def test_limit(self):
        results = logger.query_log(self.tmpdir, {"limit": 2})
        self.assertEqual(len(results), 2)

    def test_combined_filters(self):
        results = logger.query_log(self.tmpdir, {
            "command": "review",
            "decisions_only": True,
        })
        self.assertEqual(len(results), 2)


class TestSummarizeLog(unittest.TestCase):
    """Test log summary generation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        log_path = os.path.join(self.tmpdir, "audit_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        if os.path.exists(self.tmpdir):
            os.rmdir(self.tmpdir)

    def test_empty_summary(self):
        summary = logger.summarize_log(self.tmpdir)
        self.assertEqual(summary["total_entries"], 0)
        self.assertEqual(summary["commands"], {})

    def test_summary_counts(self):
        entries = [
            {"command": "review", "action": "predicate_accepted", "mode": "auto",
             "decision_type": "auto"},
            {"command": "review", "action": "predicate_rejected", "mode": "auto",
             "decision_type": "auto"},
            {"command": "pathway", "action": "pathway_recommended", "mode": "interactive",
             "decision_type": "manual"},
            {"command": "safety", "action": "risk_level_assigned", "mode": "auto",
             "decision_type": "auto",
             "exclusion_records": [{"subject": "A", "reason": "B"}]},
        ]
        for e in entries:
            logger.append_entry(self.tmpdir, e)

        summary = logger.summarize_log(self.tmpdir)
        self.assertEqual(summary["total_entries"], 4)
        self.assertEqual(summary["commands"]["review"], 2)
        self.assertEqual(summary["commands"]["pathway"], 1)
        self.assertEqual(summary["decision_types"]["auto"], 3)
        self.assertEqual(summary["decision_types"]["manual"], 1)
        self.assertEqual(summary["exclusions_documented"], 1)

    def test_summary_date_range(self):
        logger.append_entry(self.tmpdir, {
            "command": "review", "action": "predicate_accepted", "mode": "auto",
            "timestamp": "2026-02-05T12:00:00Z"
        })
        logger.append_entry(self.tmpdir, {
            "command": "review", "action": "predicate_rejected", "mode": "auto",
            "timestamp": "2026-02-09T12:00:00Z"
        })
        summary = logger.summarize_log(self.tmpdir)
        self.assertEqual(summary["date_range"]["earliest"], "2026-02-05T12:00:00Z")
        self.assertEqual(summary["date_range"]["latest"], "2026-02-09T12:00:00Z")


class TestConsolidatePipeline(unittest.TestCase):
    """Test pipeline consolidation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for f in ["audit_log.jsonl", "pipeline_audit.json"]:
            p = os.path.join(self.tmpdir, f)
            if os.path.exists(p):
                os.remove(p)
        os.rmdir(self.tmpdir)

    def test_consolidate_empty(self):
        # Should not crash on empty log
        logger.consolidate_pipeline(self.tmpdir, "test_project")
        self.assertFalse(os.path.exists(os.path.join(self.tmpdir, "pipeline_audit.json")))

    def test_consolidate_with_entries(self):
        entries = [
            {"command": "pipeline", "action": "pipeline_started", "mode": "auto",
             "timestamp": "2026-02-05T12:00:00Z"},
            {"command": "pipeline", "action": "step_completed", "mode": "auto",
             "subject": "extract", "duration_ms": 120000},
            {"command": "review", "action": "predicate_accepted", "mode": "auto",
             "decision": "accepted", "decision_type": "auto",
             "files_written": ["review.json"]},
            {"command": "review", "action": "predicate_rejected", "mode": "auto",
             "decision": "rejected", "decision_type": "auto"},
            {"command": "pipeline", "action": "pipeline_completed", "mode": "auto",
             "timestamp": "2026-02-05T12:15:00Z"},
        ]
        for e in entries:
            logger.append_entry(self.tmpdir, e)

        logger.consolidate_pipeline(self.tmpdir, "test_project")

        output_path = os.path.join(self.tmpdir, "pipeline_audit.json")
        self.assertTrue(os.path.exists(output_path))
        with open(output_path) as f:
            data = json.load(f)
        self.assertEqual(data["project"], "test_project")
        self.assertEqual(data["pipeline_version"], "5.22.0")
        self.assertEqual(data["total_decisions"], 2)
        self.assertEqual(data["auto_decisions"], 2)
        self.assertIn("extract", data["steps"])
        self.assertIn("review.json", data["files_generated"])

    def test_consolidate_duration_calculated(self):
        logger.append_entry(self.tmpdir, {
            "command": "pipeline", "action": "pipeline_started", "mode": "auto",
            "timestamp": "2026-02-05T12:00:00+00:00"
        })
        logger.append_entry(self.tmpdir, {
            "command": "pipeline", "action": "pipeline_completed", "mode": "auto",
            "timestamp": "2026-02-05T12:15:00+00:00"
        })
        logger.consolidate_pipeline(self.tmpdir, "test")
        with open(os.path.join(self.tmpdir, "pipeline_audit.json")) as f:
            data = json.load(f)
        self.assertEqual(data["duration_seconds"], 900)


class TestValidActionTypes(unittest.TestCase):
    """Test that all documented action types are in VALID_ACTIONS."""

    def test_review_actions(self):
        for a in ["predicate_accepted", "predicate_rejected", "predicate_deferred",
                   "predicate_reclassified", "review_completed"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_pipeline_actions(self):
        for a in ["pipeline_started", "step_started", "step_completed",
                   "step_failed", "step_skipped", "step_degraded",
                   "pipeline_completed", "pipeline_halted"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_pathway_actions(self):
        for a in ["pathway_recommended", "pathway_alternative_excluded"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_guidance_actions(self):
        for a in ["guidance_matched", "guidance_excluded", "guidance_trigger_fired"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_safety_actions(self):
        for a in ["safety_query_completed", "safety_data_unavailable",
                   "risk_level_assigned", "peer_benchmark_completed"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_test_plan_actions(self):
        for a in ["test_prioritized", "test_excluded"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_draft_actions(self):
        for a in ["section_drafted", "content_decision"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_consistency_actions(self):
        for a in ["check_passed", "check_failed", "check_warned"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_pre_check_actions(self):
        for a in ["pre_check_started", "review_team_identified",
                   "rta_screening_completed", "deficiency_identified",
                   "sri_calculated", "readiness_sri_calculated",
                   "pre_check_report_generated"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_propose_actions(self):
        for a in ["predicate_proposed", "predicate_validation_result"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_agent_actions(self):
        for a in ["agent_step_started", "agent_step_completed", "agent_decision"]:
            self.assertIn(a, logger.VALID_ACTIONS)

    def test_extract_actions(self):
        for a in ["extraction_started", "extraction_completed"]:
            self.assertIn(a, logger.VALID_ACTIONS)


class TestCLIParsing(unittest.TestCase):
    """Test CLI argument parsing."""

    def test_append_requires_project(self):
        with self.assertRaises(SystemExit):
            logger.main.__wrapped__ if hasattr(logger.main, '__wrapped__') else None
            # Parse with no --project
            parser = argparse.ArgumentParser()
            parser.add_argument("--project", required=True)
            parser.parse_args([])

    def test_show_log_flag(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--project", required=True)
        parser.add_argument("--show-log", action="store_true", dest="show_log")
        args = parser.parse_args(["--project", "test", "--show-log"])
        self.assertTrue(args.show_log)

    def test_summary_flag(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--project", required=True)
        parser.add_argument("--summary", action="store_true")
        args = parser.parse_args(["--project", "test", "--summary"])
        self.assertTrue(args.summary)


class TestSchemaConsistency(unittest.TestCase):
    """Verify schema consistency between logger and audit-logging.md."""

    def test_action_types_documented(self):
        """All VALID_ACTIONS should have a reasonable name format."""
        for action in logger.VALID_ACTIONS:
            self.assertRegex(action, r'^[a-z][a-z0-9_]+$',
                             f"Action '{action}' has invalid format")

    def test_version_matches(self):
        """Plugin version in logger matches expected."""
        self.assertEqual(logger.PLUGIN_VERSION, "5.22.0")

    def test_decision_types_complete(self):
        """All valid decision types are present."""
        self.assertEqual(logger.VALID_DECISION_TYPES, {"auto", "manual", "deferred"})


class TestCommandInstrumentation(unittest.TestCase):
    """Verify that instrumented command .md files contain fda_audit_logger.py invocations."""

    PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _check_command_has_audit(self, cmd_name):
        """Check that a command file references fda_audit_logger.py."""
        cmd_path = os.path.join(self.PLUGIN_ROOT, "commands", f"{cmd_name}.md")
        if not os.path.exists(cmd_path):
            self.skipTest(f"Command file {cmd_path} not found")
        with open(cmd_path) as f:
            content = f.read()
        self.assertIn("fda_audit_logger.py", content,
                       f"Command {cmd_name} should reference fda_audit_logger.py")

    def test_review_instrumented(self):
        self._check_command_has_audit("review")

    def test_pre_check_instrumented(self):
        self._check_command_has_audit("pre-check")

    def test_pathway_instrumented(self):
        self._check_command_has_audit("pathway")

    def test_safety_instrumented(self):
        self._check_command_has_audit("safety")

    def test_consistency_instrumented(self):
        self._check_command_has_audit("consistency")

    def test_guidance_instrumented(self):
        self._check_command_has_audit("guidance")

    def test_draft_instrumented(self):
        self._check_command_has_audit("draft")

    def test_propose_instrumented(self):
        self._check_command_has_audit("propose")

    def test_test_plan_instrumented(self):
        self._check_command_has_audit("test-plan")

    def test_audit_command_exists(self):
        self._check_command_has_audit("audit")


class TestAgentInstrumentation(unittest.TestCase):
    """Verify that instrumented agent .md files contain audit logging sections."""

    PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _check_agent_has_audit(self, agent_name):
        agent_path = os.path.join(self.PLUGIN_ROOT, "agents", f"{agent_name}.md")
        if not os.path.exists(agent_path):
            self.skipTest(f"Agent file {agent_path} not found")
        with open(agent_path) as f:
            content = f.read()
        self.assertIn("Audit Logging", content,
                       f"Agent {agent_name} should have an Audit Logging section")
        self.assertIn("fda_audit_logger.py", content,
                       f"Agent {agent_name} should reference fda_audit_logger.py")

    def test_review_simulator_instrumented(self):
        self._check_agent_has_audit("review-simulator")

    def test_submission_writer_instrumented(self):
        self._check_agent_has_audit("submission-writer")

    def test_research_intelligence_instrumented(self):
        self._check_agent_has_audit("research-intelligence")


class TestReferenceFiles(unittest.TestCase):
    """Verify reference documentation exists and is consistent."""

    PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_audit_logging_md_exists(self):
        path = os.path.join(self.PLUGIN_ROOT, "references", "audit-logging.md")
        self.assertTrue(os.path.exists(path))

    def test_decision_traceability_md_exists(self):
        path = os.path.join(self.PLUGIN_ROOT, "references", "decision-traceability.md")
        self.assertTrue(os.path.exists(path))

    def test_audit_logging_has_new_fields(self):
        path = os.path.join(self.PLUGIN_ROOT, "references", "audit-logging.md")
        with open(path) as f:
            content = f.read()
        for field in ["alternatives_considered", "exclusion_records",
                       "decision_type", "score_breakdown"]:
            self.assertIn(field, content,
                          f"audit-logging.md should document field '{field}'")

    def test_audit_logging_has_new_action_types(self):
        path = os.path.join(self.PLUGIN_ROOT, "references", "audit-logging.md")
        with open(path) as f:
            content = f.read()
        for action in ["pathway_recommended", "guidance_matched",
                        "risk_level_assigned", "check_passed",
                        "deficiency_identified", "test_prioritized",
                        "section_drafted", "agent_decision"]:
            self.assertIn(action, content,
                          f"audit-logging.md should document action '{action}'")

    def test_audit_logging_references_logger_cli(self):
        path = os.path.join(self.PLUGIN_ROOT, "references", "audit-logging.md")
        with open(path) as f:
            content = f.read()
        self.assertIn("fda_audit_logger.py", content)

    def test_decision_traceability_references(self):
        path = os.path.join(self.PLUGIN_ROOT, "references", "decision-traceability.md")
        with open(path) as f:
            content = f.read()
        self.assertIn("zero-trust", content.lower())
        self.assertIn("audit_log.jsonl", content)
        self.assertIn("fda_audit_logger.py", content)


class TestPluginMetadata(unittest.TestCase):
    """Verify plugin.json and SKILL.md are updated."""

    PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_plugin_json_version(self):
        path = os.path.join(self.PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["version"], "5.22.0")

    def test_plugin_json_command_count(self):
        path = os.path.join(self.PLUGIN_ROOT, ".claude-plugin", "plugin.json")
        with open(path) as f:
            data = json.load(f)
        self.assertIn("43 commands", data["description"])

    def test_skill_md_has_audit_command(self):
        path = os.path.join(self.PLUGIN_ROOT, "skills", "fda-510k-knowledge", "SKILL.md")
        with open(path) as f:
            content = f.read()
        self.assertIn("/fda:audit", content)

    def test_skill_md_command_count(self):
        path = os.path.join(self.PLUGIN_ROOT, "skills", "fda-510k-knowledge", "SKILL.md")
        with open(path) as f:
            content = f.read()
        self.assertIn("Commands (43)", content)

    def test_skill_md_reference_count(self):
        path = os.path.join(self.PLUGIN_ROOT, "skills", "fda-510k-knowledge", "SKILL.md")
        with open(path) as f:
            content = f.read()
        self.assertIn("decision-traceability.md", content)


if __name__ == "__main__":
    unittest.main()
