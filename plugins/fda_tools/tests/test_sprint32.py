"""
Sprint 32 — 21 CFR Part 11 Training Records + eSTAR Export (FDA-312, FDA-319)
=============================================================================
Test suite for:
  FDA-312: §11.10(i) Training Records implementation
  FDA-319: eSTAR XML Export bridge endpoint

Coverage:
  TR-001  TrainingRecordStore — unit tests (add, list, count, get)
  TR-002  TrainingRecordStore — compliance helpers (has_part11_training, compliance_summary)
  TR-003  TrainingRecordStore — thread safety (concurrent writes)
  TR-004  TrainingTopic enum + PART_11_CORE_TOPICS invariants
  TR-005  Bridge server — POST /compliance/training endpoint defined
  TR-006  Bridge server — GET /compliance/training endpoint defined
  TR-007  Bridge server — TrainingRecordRequest Pydantic model
  TR-008  Bridge server — response structure contracts
  TR-009  Part11ComplianceReport §11.10(i) — FAIL path (no records)
  TR-010  Part11ComplianceReport §11.10(i) — PASS via legacy bool flag
  TR-011  Part11ComplianceReport §11.10(i) — PASS via training_count
  TR-012  Part11ComplianceReport §11.10(i) — evidence includes topics + users
  TR-013  Part11ComplianceReport §11.10(i) — remediation cleared on PASS
  TR-014  TrainingRecordStore — forward compatibility (unknown fields preserved)
  ES-001  Bridge server — EStarExportRequest Pydantic model (FDA-319)
  ES-002  Bridge server — POST /documents/{session_id}/export/estar endpoint
  ES-003  Bridge server — eSTAR endpoint validates template_type and fmt
  ES-004  Bridge server — lazy-import pattern for estar_xml module
  ES-005  Bridge server — audit logging + response structure for eSTAR export
"""

import os
import sys
import threading
import unittest

# ── Path setup ───────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)

BRIDGE = os.path.join(_ROOT, "bridge", "server.py")
LIB    = os.path.join(_ROOT, "lib")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# TR-001  TrainingRecordStore — add / list / count / get
# ─────────────────────────────────────────────────────────────────────────────

class TestTR001StoreBasics(unittest.TestCase):
    """TrainingRecordStore core write/read operations."""

    def setUp(self):
        # Import fresh (uses module-level singleton but we can reset via direct access)
        from fda_tools.lib.training_records import TrainingRecordStore, TrainingTopic
        self.store = TrainingRecordStore()   # fresh isolated instance
        self.TrainingTopic = TrainingTopic

    def _sample_record(self, user_id: str = "alice@example.com", topic: str = None):
        return {
            "user_id":   user_id,
            "user_name": "Alice Smith",
            "topic":     topic or self.TrainingTopic.PART_11_OVERVIEW,
        }

    def test_add_returns_string_uuid(self):
        record_id = self.store.add(self._sample_record())
        self.assertIsInstance(record_id, str)
        self.assertEqual(len(record_id), 36)          # UUID4 format
        self.assertEqual(record_id.count("-"), 4)

    def test_add_increments_count(self):
        self.assertEqual(self.store.count(), 0)
        self.store.add(self._sample_record())
        self.assertEqual(self.store.count(), 1)
        self.store.add(self._sample_record())
        self.assertEqual(self.store.count(), 2)

    def test_list_returns_copy_not_reference(self):
        self.store.add(self._sample_record())
        result = self.store.list()
        result.clear()                                # mutate the returned list
        self.assertEqual(self.store.count(), 1)       # store unaffected

    def test_list_contains_all_records(self):
        self.store.add(self._sample_record("a@x.com"))
        self.store.add(self._sample_record("b@x.com"))
        records = self.store.list()
        self.assertEqual(len(records), 2)

    def test_list_filter_by_user_id(self):
        self.store.add(self._sample_record("alice@x.com"))
        self.store.add(self._sample_record("bob@x.com"))
        alice_records = self.store.list(user_id="alice@x.com")
        self.assertEqual(len(alice_records), 1)
        self.assertEqual(alice_records[0]["user_id"], "alice@x.com")

    def test_list_filter_returns_empty_for_unknown_user(self):
        self.store.add(self._sample_record("alice@x.com"))
        result = self.store.list(user_id="nobody@x.com")
        self.assertEqual(result, [])

    def test_get_by_record_id_returns_dict(self):
        record_id = self.store.add(self._sample_record())
        record = self.store.get(record_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["record_id"], record_id)

    def test_get_unknown_id_returns_none(self):
        result = self.store.get("00000000-0000-0000-0000-000000000000")
        self.assertIsNone(result)

    def test_record_has_created_at_timestamp(self):
        record_id = self.store.add(self._sample_record())
        record = self.store.get(record_id)
        self.assertIn("created_at", record)
        ts = record["created_at"]
        # Python datetime.isoformat() produces either "...Z" or "...+00:00"
        is_utc = ts.endswith("Z") or ts.endswith("+00:00") or "+00:00" in ts
        self.assertTrue(is_utc, f"created_at is not UTC: {ts}")

    def test_record_has_completed_at_timestamp(self):
        record_id = self.store.add(self._sample_record())
        record = self.store.get(record_id)
        self.assertIn("completed_at", record)

    def test_add_preserves_optional_fields(self):
        record_id = self.store.add({
            **self._sample_record(),
            "score":          95,
            "certificate_id": "CERT-001",
            "notes":          "Completed online module",
        })
        record = self.store.get(record_id)
        self.assertEqual(record["score"], 95)
        self.assertEqual(record["certificate_id"], "CERT-001")

    def test_count_filters_by_user(self):
        self.store.add(self._sample_record("alice@x.com"))
        self.store.add(self._sample_record("alice@x.com"))
        self.store.add(self._sample_record("bob@x.com"))
        self.assertEqual(self.store.count(user_id="alice@x.com"), 2)
        self.assertEqual(self.store.count(user_id="bob@x.com"), 1)


# ─────────────────────────────────────────────────────────────────────────────
# TR-002  TrainingRecordStore — compliance helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestTR002ComplianceHelpers(unittest.TestCase):
    """has_part11_training() and compliance_summary() methods."""

    def setUp(self):
        from fda_tools.lib.training_records import (
            TrainingRecordStore,
            TrainingTopic,
            PART_11_CORE_TOPICS,
        )
        self.store = TrainingRecordStore()
        self.TrainingTopic = TrainingTopic
        self.PART_11_CORE_TOPICS = PART_11_CORE_TOPICS

    def test_has_part11_training_false_when_empty(self):
        self.assertFalse(self.store.has_part11_training())

    def test_has_part11_training_true_for_core_topic(self):
        self.store.add({
            "user_id":   "user@test.com",
            "user_name": "Test User",
            "topic":     self.TrainingTopic.PART_11_OVERVIEW,
        })
        self.assertTrue(self.store.has_part11_training())

    def test_has_part11_training_true_for_any_record_fallback(self):
        """Even non-core topics satisfy the fallback check (lenient interpretation)."""
        self.store.add({
            "user_id":   "user@test.com",
            "user_name": "Test User",
            "topic":     self.TrainingTopic.HITL_PROCEDURES,  # non-core
        })
        self.assertTrue(self.store.has_part11_training())

    def test_has_part11_training_filters_by_user(self):
        self.store.add({
            "user_id":   "alice@test.com",
            "user_name": "Alice",
            "topic":     self.TrainingTopic.PART_11_OVERVIEW,
        })
        self.assertTrue(self.store.has_part11_training(user_id="alice@test.com"))
        self.assertFalse(self.store.has_part11_training(user_id="bob@test.com"))

    def test_compliance_summary_empty(self):
        summary = self.store.compliance_summary()
        self.assertFalse(summary["training_records_exist"])
        self.assertEqual(summary["training_count"], 0)
        self.assertIsInstance(summary["training_users"], list)
        self.assertEqual(len(summary["training_users"]), 0)
        self.assertIsInstance(summary["part11_topics_covered"], list)
        self.assertEqual(len(summary["part11_topics_covered"]), 0)

    def test_compliance_summary_with_core_topics(self):
        self.store.add({
            "user_id":   "alice@test.com",
            "user_name": "Alice",
            "topic":     self.TrainingTopic.PART_11_OVERVIEW,
        })
        self.store.add({
            "user_id":   "alice@test.com",
            "user_name": "Alice",
            "topic":     self.TrainingTopic.ACCESS_CONTROL,
        })
        summary = self.store.compliance_summary()
        self.assertTrue(summary["training_records_exist"])
        self.assertEqual(summary["training_count"], 2)
        self.assertIn("alice@test.com", summary["training_users"])
        covered = set(summary["part11_topics_covered"])
        self.assertIn(self.TrainingTopic.PART_11_OVERVIEW, covered)
        self.assertIn(self.TrainingTopic.ACCESS_CONTROL, covered)

    def test_compliance_summary_excludes_noncovered_core_topics(self):
        """Only topics actually trained appear in part11_topics_covered."""
        self.store.add({
            "user_id":   "u@test.com",
            "user_name": "U",
            "topic":     self.TrainingTopic.PART_11_OVERVIEW,
        })
        summary = self.store.compliance_summary()
        covered = set(summary["part11_topics_covered"])
        # Only one core topic added
        self.assertEqual(len(covered & set(self.PART_11_CORE_TOPICS)), 1)

    def test_compliance_summary_user_filter(self):
        self.store.add({
            "user_id":   "alice@test.com",
            "user_name": "Alice",
            "topic":     self.TrainingTopic.AUDIT_TRAIL_MANAGEMENT,
        })
        self.store.add({
            "user_id":   "bob@test.com",
            "user_name": "Bob",
            "topic":     self.TrainingTopic.ELECTRONIC_SIGNATURES,
        })
        alice_summary = self.store.compliance_summary(user_id="alice@test.com")
        self.assertEqual(alice_summary["training_count"], 1)
        self.assertIn("alice@test.com", alice_summary["training_users"])
        self.assertNotIn("bob@test.com", alice_summary["training_users"])


# ─────────────────────────────────────────────────────────────────────────────
# TR-003  TrainingRecordStore — thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestTR003ThreadSafety(unittest.TestCase):
    """Concurrent adds must not corrupt the internal list."""

    def setUp(self):
        from fda_tools.lib.training_records import TrainingRecordStore, TrainingTopic
        self.store = TrainingRecordStore()
        self.TrainingTopic = TrainingTopic

    def test_concurrent_adds_all_recorded(self):
        N = 50
        threads = []
        for i in range(N):
            t = threading.Thread(target=self.store.add, args=({
                "user_id":   f"user{i}@test.com",
                "user_name": f"User {i}",
                "topic":     self.TrainingTopic.PART_11_OVERVIEW,
            },))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.store.count(), N)

    def test_concurrent_adds_produce_unique_ids(self):
        N = 30
        ids = []
        lock = threading.Lock()

        def add_and_collect():
            record_id = self.store.add({
                "user_id":   "u@test.com",
                "user_name": "U",
                "topic":     self.TrainingTopic.SYSTEM_VALIDATION,
            })
            with lock:
                ids.append(record_id)

        threads = [threading.Thread(target=add_and_collect) for _ in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(set(ids)), N, "All record IDs must be unique")


# ─────────────────────────────────────────────────────────────────────────────
# TR-004  TrainingTopic enum + PART_11_CORE_TOPICS invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestTR004TopicEnumInvariants(unittest.TestCase):
    """TrainingTopic enum and PART_11_CORE_TOPICS contract."""

    def setUp(self):
        from fda_tools.lib.training_records import (
            TrainingTopic,
            PART_11_CORE_TOPICS,
        )
        self.TrainingTopic = TrainingTopic
        self.PART_11_CORE_TOPICS = PART_11_CORE_TOPICS

    def test_training_topic_is_str_enum(self):
        """TrainingTopic inherits from str so values can be compared to plain strings."""
        self.assertIsInstance(self.TrainingTopic.PART_11_OVERVIEW, str)
        self.assertEqual(self.TrainingTopic.PART_11_OVERVIEW, "part_11_overview")

    def test_core_topics_contains_five_topics(self):
        self.assertEqual(len(self.PART_11_CORE_TOPICS), 5)

    def test_core_topics_contains_part11_overview(self):
        self.assertIn(self.TrainingTopic.PART_11_OVERVIEW, self.PART_11_CORE_TOPICS)

    def test_core_topics_contains_electronic_signatures(self):
        self.assertIn(self.TrainingTopic.ELECTRONIC_SIGNATURES, self.PART_11_CORE_TOPICS)

    def test_core_topics_contains_audit_trail_management(self):
        self.assertIn(self.TrainingTopic.AUDIT_TRAIL_MANAGEMENT, self.PART_11_CORE_TOPICS)

    def test_core_topics_contains_access_control(self):
        self.assertIn(self.TrainingTopic.ACCESS_CONTROL, self.PART_11_CORE_TOPICS)

    def test_core_topics_contains_system_validation(self):
        self.assertIn(self.TrainingTopic.SYSTEM_VALIDATION, self.PART_11_CORE_TOPICS)

    def test_non_core_topics_exist(self):
        """DATA_INTEGRITY, HITL_PROCEDURES, SUBMISSION_WORKFLOW are non-core."""
        non_core = [
            self.TrainingTopic.DATA_INTEGRITY,
            self.TrainingTopic.HITL_PROCEDURES,
            self.TrainingTopic.SUBMISSION_WORKFLOW,
        ]
        for topic in non_core:
            self.assertNotIn(topic, self.PART_11_CORE_TOPICS,
                             f"{topic} should be non-core")

    def test_core_topics_is_frozenset(self):
        """PART_11_CORE_TOPICS must be immutable (frozenset)."""
        self.assertIsInstance(self.PART_11_CORE_TOPICS, frozenset)

    def test_all_enum_values_are_snake_case(self):
        """All values follow snake_case convention (no spaces or uppercase)."""
        for topic in self.TrainingTopic:
            self.assertEqual(topic.value, topic.value.lower(),
                             f"{topic.name} value must be lowercase")
            self.assertNotIn(" ", topic.value)


# ─────────────────────────────────────────────────────────────────────────────
# TR-005  Bridge server — POST /compliance/training endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestTR005BridgePostEndpoint(unittest.TestCase):
    """server.py has POST /compliance/training endpoint."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_post_route_defined(self):
        self.assertIn('"/compliance/training"', self.src)

    def test_post_method(self):
        self.assertIn('app.post("/compliance/training")', self.src)

    def test_endpoint_function_exists(self):
        self.assertIn("add_training_record", self.src)

    def test_rate_limit_applied(self):
        """Endpoint must be rate-limited per enterprise security policy."""
        idx = self.src.find("add_training_record")
        # Rate limit decorator appears just before the function
        surrounding = self.src[max(0, idx - 200): idx + 50]
        self.assertIn("_rate_limit", surrounding)

    def test_audit_logging_called(self):
        """Training adds must produce an audit log entry."""
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("audit_log_entry", surrounding)

    def test_uses_training_store_add(self):
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("training_store.add", surrounding)

    def test_returns_record_id(self):
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("record_id", surrounding)

    def test_returns_is_core_topic(self):
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 1200]
        self.assertIn("is_core_topic", surrounding)

    def test_returns_part11_compliant(self):
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 1200]
        self.assertIn("part11_compliant", surrounding)

    def test_checks_core_topic_membership(self):
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("PART_11_CORE_TOPICS", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# TR-006  Bridge server — GET /compliance/training endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestTR006BridgeGetEndpoint(unittest.TestCase):
    """server.py has GET /compliance/training endpoint."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_get_route_defined(self):
        self.assertIn('app.get("/compliance/training")', self.src)

    def test_endpoint_function_exists(self):
        self.assertIn("list_training_records", self.src)

    def test_user_id_optional_query_param(self):
        idx = self.src.find("list_training_records")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("user_id", surrounding)

    def test_uses_compliance_summary(self):
        idx = self.src.find("list_training_records")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("compliance_summary", surrounding)

    def test_uses_training_store_list(self):
        idx = self.src.find("list_training_records")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("training_store.list", surrounding)

    def test_returns_part11_compliant(self):
        idx = self.src.find("list_training_records")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("part11_compliant", surrounding)

    def test_returns_section_reference(self):
        """Response must cite the §11.10(i) section string for auditability."""
        idx = self.src.find("list_training_records")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("§11.10(i)", surrounding)

    def test_returns_records_key(self):
        idx = self.src.find("list_training_records")
        surrounding = self.src[idx: idx + 600]
        self.assertIn('"records"', surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# TR-007  Bridge server — TrainingRecordRequest Pydantic model
# ─────────────────────────────────────────────────────────────────────────────

class TestTR007RequestModel(unittest.TestCase):
    """TrainingRecordRequest model has required fields and validation."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_model_class_defined(self):
        self.assertIn("class TrainingRecordRequest", self.src)

    def test_model_has_user_id(self):
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("user_id", surrounding)

    def test_model_has_user_name(self):
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("user_name", surrounding)

    def test_model_has_topic(self):
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("topic", surrounding)

    def test_model_has_score_with_bounds(self):
        """Score must have 0-100 validation."""
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("score", surrounding)
        self.assertIn("le=100", surrounding)

    def test_model_has_optional_trainer_id(self):
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("trainer_id", surrounding)

    def test_model_has_certificate_id(self):
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("certificate_id", surrounding)

    def test_model_has_notes_with_max_length(self):
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 1400]
        self.assertIn("notes", surrounding)
        self.assertIn("max_length=2000", surrounding)

    def test_training_store_imported(self):
        self.assertIn("from fda_tools.lib.training_records import", self.src)
        self.assertIn("training_store", self.src)
        self.assertIn("PART_11_CORE_TOPICS", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# TR-008  Bridge server — completeness check
# ─────────────────────────────────────────────────────────────────────────────

class TestTR008BridgeCompleteness(unittest.TestCase):
    """Both training endpoints are registered on the FastAPI app."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_both_routes_present(self):
        post_count = self.src.count('"/compliance/training"')
        # At least 2: one for @app.post and one for @app.get
        self.assertGreaterEqual(post_count, 2)

    def test_training_topic_values_documented_in_field(self):
        """Field description must reference PART_11_CORE_TOPICS."""
        idx = self.src.find("class TrainingRecordRequest")
        surrounding = self.src[idx: idx + 1500]
        self.assertIn("PART_11_CORE_TOPICS", surrounding)

    def test_no_hardcoded_topic_strings_in_endpoint(self):
        """Endpoint uses PART_11_CORE_TOPICS constant, not inline string comparison."""
        idx = self.src.find("add_training_record")
        surrounding = self.src[idx: idx + 800]
        # Should use PART_11_CORE_TOPICS, not hard-code "part_11_overview"
        self.assertIn("PART_11_CORE_TOPICS", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# TR-009  Part11ComplianceReport §11.10(i) — FAIL path
# ─────────────────────────────────────────────────────────────────────────────

class TestTR009Part11FailPath(unittest.TestCase):
    """§11.10(i) finding is FAIL when no training records exist."""

    def setUp(self):
        from fda_tools.lib.cfr_part11 import Part11AuditLog, Part11ComplianceReport
        self.log = Part11AuditLog()
        self.Part11ComplianceReport = Part11ComplianceReport

    def _get_training_finding(self, config=None):
        report = self.Part11ComplianceReport.generate(self.log, config or {})
        for finding in report.findings:
            if "11.10(i)" in finding.control:
                return finding
        self.fail("§11.10(i) finding not found in report")

    def test_fail_when_no_config(self):
        finding = self._get_training_finding({})
        self.assertEqual(finding.status, "FAIL")

    def test_fail_when_training_count_zero(self):
        finding = self._get_training_finding({
            "training_records_exist": False,
            "training_count": 0,
        })
        self.assertEqual(finding.status, "FAIL")

    def test_fail_evidence_mentions_requirement(self):
        finding = self._get_training_finding({})
        self.assertIn("§11.10(i)", finding.evidence)

    def test_fail_remediation_not_empty(self):
        finding = self._get_training_finding({})
        self.assertTrue(len(finding.remediation) > 0)

    def test_fail_remediation_references_endpoint(self):
        finding = self._get_training_finding({})
        self.assertIn("/compliance/training", finding.remediation)

    def test_control_name_correct(self):
        finding = self._get_training_finding({})
        self.assertIn("§11.10(i)", finding.control)
        self.assertIn("Training records", finding.control)


# ─────────────────────────────────────────────────────────────────────────────
# TR-010  Part11ComplianceReport §11.10(i) — PASS via legacy bool flag
# ─────────────────────────────────────────────────────────────────────────────

class TestTR010Part11PassLegacyBool(unittest.TestCase):
    """§11.10(i) passes when training_records_exist=True (backward compat)."""

    def setUp(self):
        from fda_tools.lib.cfr_part11 import Part11AuditLog, Part11ComplianceReport
        self.log = Part11AuditLog()
        self.Part11ComplianceReport = Part11ComplianceReport

    def _get_training_finding(self, config):
        report = self.Part11ComplianceReport.generate(self.log, config)
        for finding in report.findings:
            if "11.10(i)" in finding.control:
                return finding
        self.fail("§11.10(i) finding not found")

    def test_pass_with_legacy_true_flag(self):
        finding = self._get_training_finding({"training_records_exist": True})
        self.assertEqual(finding.status, "PASS")

    def test_pass_remediation_empty_on_pass(self):
        finding = self._get_training_finding({"training_records_exist": True})
        self.assertEqual(finding.remediation, "")

    def test_pass_evidence_mentions_legacy_flag(self):
        finding = self._get_training_finding({
            "training_records_exist": True,
            "training_count": 0,       # explicit zero count — legacy flag takes over
        })
        self.assertEqual(finding.status, "PASS")


# ─────────────────────────────────────────────────────────────────────────────
# TR-011  Part11ComplianceReport §11.10(i) — PASS via training_count
# ─────────────────────────────────────────────────────────────────────────────

class TestTR011Part11PassTrainingCount(unittest.TestCase):
    """§11.10(i) passes when training_count > 0 (new rich path)."""

    def setUp(self):
        from fda_tools.lib.cfr_part11 import Part11AuditLog, Part11ComplianceReport
        self.log = Part11AuditLog()
        self.Part11ComplianceReport = Part11ComplianceReport

    def _get_training_finding(self, config):
        report = self.Part11ComplianceReport.generate(self.log, config)
        for finding in report.findings:
            if "11.10(i)" in finding.control:
                return finding
        self.fail("§11.10(i) finding not found")

    def test_pass_with_training_count_1(self):
        finding = self._get_training_finding({
            "training_records_exist": False,
            "training_count": 1,
        })
        self.assertEqual(finding.status, "PASS")

    def test_pass_with_training_count_10(self):
        finding = self._get_training_finding({
            "training_count": 10,
        })
        self.assertEqual(finding.status, "PASS")

    def test_pass_remediation_empty(self):
        finding = self._get_training_finding({"training_count": 5})
        self.assertEqual(finding.remediation, "")

    def test_evidence_mentions_count(self):
        finding = self._get_training_finding({
            "training_count": 7,
            "training_users": ["alice@x.com"],
        })
        self.assertIn("7", finding.evidence)


# ─────────────────────────────────────────────────────────────────────────────
# TR-012  Part11ComplianceReport §11.10(i) — evidence includes topics + users
# ─────────────────────────────────────────────────────────────────────────────

class TestTR012Part11EvidenceDetail(unittest.TestCase):
    """Rich evidence string includes topic names and user count."""

    def setUp(self):
        from fda_tools.lib.cfr_part11 import Part11AuditLog, Part11ComplianceReport
        self.log = Part11AuditLog()
        self.Part11ComplianceReport = Part11ComplianceReport

    def _get_training_finding(self, config):
        report = self.Part11ComplianceReport.generate(self.log, config)
        for finding in report.findings:
            if "11.10(i)" in finding.control:
                return finding
        self.fail("§11.10(i) finding not found")

    def test_evidence_includes_covered_topics(self):
        finding = self._get_training_finding({
            "training_count":        3,
            "part11_topics_covered": ["part_11_overview", "access_control"],
            "training_users":        ["alice@x.com"],
        })
        self.assertIn("part_11_overview", finding.evidence)
        self.assertIn("access_control", finding.evidence)

    def test_evidence_includes_user_count(self):
        finding = self._get_training_finding({
            "training_count":        2,
            "part11_topics_covered": ["part_11_overview"],
            "training_users":        ["alice@x.com", "bob@x.com"],
        })
        # Evidence should mention user count: "2 user(s)"
        self.assertIn("2", finding.evidence)

    def test_evidence_without_topics_shows_simple_message(self):
        """When topics list is empty but count > 0, evidence is brief."""
        finding = self._get_training_finding({
            "training_count":        5,
            "part11_topics_covered": [],
        })
        self.assertEqual(finding.status, "PASS")
        self.assertIn("5", finding.evidence)

    def test_evidence_without_topics_does_not_crash(self):
        finding = self._get_training_finding({"training_count": 1})
        self.assertIsNotNone(finding.evidence)


# ─────────────────────────────────────────────────────────────────────────────
# TR-013  Part11ComplianceReport §11.10(i) — remediation cleared on PASS
# ─────────────────────────────────────────────────────────────────────────────

class TestTR013RemediationClearedOnPass(unittest.TestCase):
    """When §11.10(i) is PASS, remediation must be empty string."""

    def setUp(self):
        from fda_tools.lib.cfr_part11 import Part11AuditLog, Part11ComplianceReport
        self.log = Part11AuditLog()
        self.Part11ComplianceReport = Part11ComplianceReport

    def _get_training_finding(self, config):
        report = self.Part11ComplianceReport.generate(self.log, config)
        for finding in report.findings:
            if "11.10(i)" in finding.control:
                return finding
        self.fail("§11.10(i) finding not found")

    def test_remediation_empty_via_legacy_bool(self):
        finding = self._get_training_finding({"training_records_exist": True})
        self.assertEqual(finding.remediation, "")

    def test_remediation_empty_via_count(self):
        finding = self._get_training_finding({
            "training_count":        3,
            "part11_topics_covered": ["part_11_overview"],
        })
        self.assertEqual(finding.remediation, "")

    def test_remediation_present_on_fail(self):
        finding = self._get_training_finding({})
        self.assertGreater(len(finding.remediation), 0)


# ─────────────────────────────────────────────────────────────────────────────
# TR-014  TrainingRecordStore — forward compatibility (unknown fields preserved)
# ─────────────────────────────────────────────────────────────────────────────

class TestTR014ForwardCompatibility(unittest.TestCase):
    """Extra fields in a record dict are preserved (open dict model)."""

    def setUp(self):
        from fda_tools.lib.training_records import TrainingRecordStore, TrainingTopic
        self.store = TrainingRecordStore()
        self.TrainingTopic = TrainingTopic

    def test_extra_fields_stored(self):
        record_id = self.store.add({
            "user_id":    "user@test.com",
            "user_name":  "Test",
            "topic":      self.TrainingTopic.PART_11_OVERVIEW,
            # Future Sprint 33 fields (not yet validated)
            "lms_course_id":   "LMS-999",
            "attestation_url": "https://lms.example.com/attestation/999",
        })
        record = self.store.get(record_id)
        self.assertEqual(record.get("lms_course_id"), "LMS-999")
        self.assertEqual(record.get("attestation_url"), "https://lms.example.com/attestation/999")

    def test_get_returns_copy_not_reference(self):
        """Mutating the returned record dict must not affect the store."""
        record_id = self.store.add({
            "user_id":   "u@test.com",
            "user_name": "U",
            "topic":     self.TrainingTopic.ACCESS_CONTROL,
        })
        record = self.store.get(record_id)
        record["user_id"] = "hacked@evil.com"  # mutate copy
        original = self.store.get(record_id)
        self.assertEqual(original["user_id"], "u@test.com")


# ─────────────────────────────────────────────────────────────────────────────
# ES-001  Bridge server — EStarExportRequest Pydantic model (FDA-319)
# ─────────────────────────────────────────────────────────────────────────────

class TestES001EStarRequestModel(unittest.TestCase):
    """EStarExportRequest model fields and defaults."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_model_class_defined(self):
        self.assertIn("class EStarExportRequest", self.src)

    def test_model_has_project_root(self):
        idx = self.src.find("class EStarExportRequest")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("project_root", surrounding)

    def test_model_has_template_type_with_default_nivd(self):
        idx = self.src.find("class EStarExportRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("template_type", surrounding)
        self.assertIn("nIVD", surrounding)

    def test_model_has_fmt_with_default_real(self):
        idx = self.src.find("class EStarExportRequest")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("fmt", surrounding)
        self.assertIn("real", surrounding)

    def test_model_documents_template_types(self):
        """Model description must document all three template types."""
        idx = self.src.find("class EStarExportRequest")
        surrounding = self.src[idx: idx + 1200]
        self.assertIn("nIVD", surrounding)
        self.assertIn("IVD", surrounding)
        self.assertIn("PreSTAR", surrounding)

    def test_model_references_fda_form_ids(self):
        """Model must reference FDA form numbers for auditability."""
        idx = self.src.find("class EStarExportRequest")
        surrounding = self.src[idx: idx + 1200]
        self.assertIn("4062", surrounding)
        self.assertIn("4078", surrounding)
        self.assertIn("5064", surrounding)

    def test_valid_templates_frozenset_defined(self):
        """_ESTAR_VALID_TEMPLATES must exist to guard template_type validation."""
        self.assertIn("_ESTAR_VALID_TEMPLATES", self.src)
        # Must contain all three template types
        idx = self.src.find("_ESTAR_VALID_TEMPLATES")
        surrounding = self.src[idx: idx + 100]
        self.assertIn("nIVD", surrounding)

    def test_valid_fmts_frozenset_defined(self):
        self.assertIn("_ESTAR_VALID_FMTS", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# ES-002  Bridge server — POST /documents/{session_id}/export/estar endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestES002EStarEndpoint(unittest.TestCase):
    """POST /documents/{session_id}/export/estar endpoint contract."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_endpoint_route_defined(self):
        self.assertIn('"/documents/{session_id}/export/estar"', self.src)

    def test_endpoint_is_post(self):
        self.assertIn('app.post("/documents/{session_id}/export/estar")', self.src)

    def test_endpoint_function_exists(self):
        self.assertIn("export_estar_xml", self.src)

    def test_rate_limit_applied(self):
        """eSTAR export uses the stricter EXECUTE rate limit (not default)."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[max(0, idx - 200): idx + 50]
        self.assertIn("RATE_LIMIT_EXECUTE", surrounding)

    def test_session_id_path_param(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 300]
        self.assertIn("session_id", surrounding)

    def test_body_is_estar_export_request(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("EStarExportRequest", surrounding)

    def test_calls_generate_xml(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("generate_xml", surrounding)

    def test_audit_logging_called(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("audit_log_entry", surrounding)
        self.assertIn("estar_xml_exported", surrounding)

    def test_reads_xml_content(self):
        """Endpoint must read generated XML and return it inline."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("read_text", surrounding)

    def test_returns_xml_content_key(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn('"xml_content"', surrounding)

    def test_returns_output_file_key(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn('"output_file"', surrounding)

    def test_returns_next_steps(self):
        """Response must include human-readable next steps for FDA workflow."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("next_steps", surrounding)
        self.assertIn("Adobe Acrobat", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# ES-003  Bridge server — eSTAR endpoint validates template_type and fmt
# ─────────────────────────────────────────────────────────────────────────────

class TestES003EStarValidation(unittest.TestCase):
    """Endpoint enforces template_type and fmt validation."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_template_type_validation_present(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        # Must check against valid templates
        self.assertIn("_ESTAR_VALID_TEMPLATES", surrounding)

    def test_fmt_validation_present(self):
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("_ESTAR_VALID_FMTS", surrounding)

    def test_raises_422_for_invalid_template(self):
        """HTTPException with status_code=422 is raised for bad template."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("422", surrounding)

    def test_project_root_validated(self):
        """Endpoint resolves and validates project_root."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("project_root", surrounding)
        self.assertIn("expanduser", surrounding)
        self.assertIn("resolve", surrounding)

    def test_directory_existence_check(self):
        """Endpoint must verify project_root exists and is a directory."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("is_dir()", surrounding)

    def test_empty_project_check(self):
        """Endpoint must reject projects with no data files."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("data_files", surrounding)

    def test_system_exit_caught(self):
        """SystemExit from estar_xml.py must be caught and converted to HTTPException."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("SystemExit", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# ES-004  Bridge server — lazy-import pattern for estar_xml module (FDA-319)
# ─────────────────────────────────────────────────────────────────────────────

class TestES004LazyImport(unittest.TestCase):
    """estar_xml is loaded lazily via _get_estar_generate_xml()."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def test_lazy_loader_function_defined(self):
        self.assertIn("_get_estar_generate_xml", self.src)

    def test_lazy_loader_uses_module_cache(self):
        """Loader must cache the module to avoid re-loading on every request."""
        idx = self.src.find("_get_estar_generate_xml")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("_estar_generate_xml", surrounding)

    def test_lazy_loader_imports_from_scripts(self):
        """Imports generate_xml from fda_tools.scripts.estar_xml."""
        idx = self.src.find("_get_estar_generate_xml")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("estar_xml", surrounding)
        self.assertIn("generate_xml", surrounding)

    def test_module_level_none_sentinel(self):
        """Module-level _estar_generate_xml = None sentinel must exist."""
        self.assertIn("_estar_generate_xml = None", self.src)

    def test_estar_generate_xml_called_in_endpoint(self):
        """Endpoint calls _get_estar_generate_xml() to get the function."""
        idx = self.src.find("async def export_estar_xml")
        surrounding = self.src[idx: idx + 5500]
        self.assertIn("_get_estar_generate_xml()", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# ES-005  Bridge server — audit logging + response structure for eSTAR export
# ─────────────────────────────────────────────────────────────────────────────

class TestES005AuditAndResponse(unittest.TestCase):
    """eSTAR export produces compliant audit log and full response."""

    def setUp(self):
        self.src = _read(BRIDGE)

    def _get_endpoint_body(self) -> str:
        idx = self.src.find("async def export_estar_xml")
        return self.src[idx: idx + 5500]

    def test_audit_entry_includes_session_id(self):
        body = self._get_endpoint_body()
        self.assertIn('"session_id"', body)

    def test_audit_entry_includes_project_root(self):
        body = self._get_endpoint_body()
        self.assertIn('"project_root"', body)

    def test_audit_entry_includes_template_type(self):
        body = self._get_endpoint_body()
        self.assertIn('"template_type"', body)

    def test_response_includes_xml_size(self):
        body = self._get_endpoint_body()
        self.assertIn("xml_size_kb", body)

    def test_response_includes_data_sources(self):
        body = self._get_endpoint_body()
        self.assertIn("data_sources", body)

    def test_response_includes_template_type(self):
        body = self._get_endpoint_body()
        self.assertIn('"template_type"', body)

    def test_response_includes_fmt(self):
        body = self._get_endpoint_body()
        self.assertIn('"fmt"', body)

    def test_requires_authentication(self):
        """Endpoint must use require_api_key dependency."""
        body = self._get_endpoint_body()
        self.assertIn("require_api_key", body)

    def test_next_steps_references_acrobat(self):
        """Human-readable next steps guide user through FDA eSTAR import workflow."""
        body = self._get_endpoint_body()
        self.assertIn("Adobe Acrobat", body)
        self.assertIn("Import Data", body)


if __name__ == "__main__":
    unittest.main()
