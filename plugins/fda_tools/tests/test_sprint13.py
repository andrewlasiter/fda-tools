"""
Sprint 13 tests — FDA-263
==========================
Covers:
  FDA-263 [SEC-012] 21 CFR Part 11 compliance implementation:
    - AuditRecord creation and fingerprinting
    - ElectronicSignature sign + verify
    - Part11AuditLog append-only semantics
    - AccessControlPolicy authority checks
    - Part11ComplianceReport generation
    - audit() decorator
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


# ═════════════════════════════════════════════════════════════════════════════
# AuditAction enumeration
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditAction:

    def test_all_required_actions_present(self):
        from plugins.fda_tools.lib.cfr_part11 import AuditAction
        required = {"CREATE", "READ", "UPDATE", "DELETE", "SIGN", "APPROVE",
                    "REJECT", "EXPORT", "LOGIN", "LOGOUT", "ACCESS_DENIED"}
        actual   = {a.value for a in AuditAction}
        assert required.issubset(actual)

    def test_approve_action_value(self):
        from plugins.fda_tools.lib.cfr_part11 import AuditAction
        assert AuditAction.APPROVE.value == "APPROVE"


# ═════════════════════════════════════════════════════════════════════════════
# AuditRecord creation and integrity
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditRecord:

    def _make_record(self, content="Test content"):
        from plugins.fda_tools.lib.cfr_part11 import AuditRecord, AuditAction
        return AuditRecord.create(
            user_id      = "alice@example.com",
            display_name = "Alice Smith",
            action       = AuditAction.UPDATE,
            record_type  = "submission_section",
            subject_id   = "section-desc",
            content      = content,
        )

    def test_record_has_unique_id(self):
        r1 = self._make_record()
        r2 = self._make_record()
        assert r1.record_id != r2.record_id

    def test_timestamp_is_utc_aware(self):
        r = self._make_record()
        dt = datetime.fromisoformat(r.timestamp)
        assert dt.tzinfo is not None

    def test_fingerprint_is_sha256_of_content(self):
        import hashlib
        r = self._make_record("Hello Part 11")
        expected = hashlib.sha256("Hello Part 11".encode()).hexdigest()
        assert r.fingerprint == expected

    def test_verify_integrity_pass(self):
        from plugins.fda_tools.lib.cfr_part11 import RecordIntegrity
        r = self._make_record("unchanged content")
        assert r.verify_integrity() == RecordIntegrity.VALID

    def test_verify_integrity_tampered(self):
        from plugins.fda_tools.lib.cfr_part11 import RecordIntegrity
        r = self._make_record("original content")
        r.content = "tampered content"  # simulates post-hoc modification
        assert r.verify_integrity() == RecordIntegrity.TAMPERED

    def test_to_dict_is_json_serialisable(self):
        r = self._make_record()
        json.dumps(r.to_dict())  # must not raise

    def test_to_dict_contains_required_keys(self):
        r = self._make_record()
        d = r.to_dict()
        for key in ["record_id", "user_id", "action", "timestamp", "fingerprint"]:
            assert key in d

    def test_signature_absent_by_default(self):
        from plugins.fda_tools.lib.cfr_part11 import SignatureStatus
        r = self._make_record()
        assert r.signature_status() == SignatureStatus.ABSENT


# ═════════════════════════════════════════════════════════════════════════════
# ElectronicSignature
# ═════════════════════════════════════════════════════════════════════════════

class TestElectronicSignature:

    SIGNING_KEY = "test_key_abc123def456ghi789jkl012mno345p"

    def _make_sig(self, record_hash: str = "abc123"):
        from plugins.fda_tools.lib.cfr_part11 import ElectronicSignature
        return ElectronicSignature.sign(
            record_hash  = record_hash,
            signer_id    = "alice@example.com",
            signer_name  = "Alice Smith",
            meaning      = "I authored this section",
            signing_key  = self.SIGNING_KEY,
        )

    def test_sign_creates_signature(self):
        sig = self._make_sig()
        assert len(sig.signature) == 64  # SHA-256 hex = 64 chars
        assert sig.signer_id == "alice@example.com"

    def test_verify_valid_signature(self):
        sig = self._make_sig("fingerprint_abc")
        assert sig.verify(signing_key=self.SIGNING_KEY) is True

    def test_verify_invalid_key_fails(self):
        sig = self._make_sig()
        assert sig.verify(signing_key="wrong_key") is False

    def test_tampered_hash_fails_verification(self):
        sig = self._make_sig("original_hash")
        sig.record_hash = "tampered_hash"
        assert sig.verify(signing_key=self.SIGNING_KEY) is False

    def test_signature_timestamp_is_utc(self):
        sig = self._make_sig()
        dt = datetime.fromisoformat(sig.timestamp)
        assert dt.tzinfo is not None

    def test_to_dict_contains_all_fields(self):
        sig = self._make_sig()
        d   = sig.to_dict()
        for key in ["signer_id", "signer_name", "meaning", "timestamp", "signature", "record_hash"]:
            assert key in d


# ═════════════════════════════════════════════════════════════════════════════
# AuditRecord with attached signature
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditRecordSignature:

    SIGNING_KEY = "test_key_abc123def456ghi789jkl012mno345p"

    def _signed_record(self):
        from plugins.fda_tools.lib.cfr_part11 import (
            AuditRecord, AuditAction, ElectronicSignature, SignatureStatus
        )
        record = AuditRecord.create(
            user_id="alice@example.com", display_name="Alice",
            action=AuditAction.APPROVE, record_type="submission",
            subject_id="k000000", content="Approved section content",
        )
        sig = ElectronicSignature.sign(
            record_hash = record.fingerprint,
            signer_id   = "alice@example.com",
            signer_name = "Alice",
            meaning     = "Electronic approval",
            signing_key = self.SIGNING_KEY,
        )
        record.attach_signature(sig)
        return record

    def test_signature_attached_is_valid(self):
        from plugins.fda_tools.lib.cfr_part11 import SignatureStatus
        r = self._signed_record()
        assert r.signature_status(signing_key=self.SIGNING_KEY) == SignatureStatus.VALID

    def test_signature_in_dict_export(self):
        r = self._signed_record()
        d = r.to_dict()
        assert "signature" in d
        assert d["signature"]["signer_id"] == "alice@example.com"


# ═════════════════════════════════════════════════════════════════════════════
# Part11AuditLog
# ═════════════════════════════════════════════════════════════════════════════

class TestPart11AuditLog:

    def _make_record(self, content="Content"):
        from plugins.fda_tools.lib.cfr_part11 import AuditRecord, AuditAction
        return AuditRecord.create(
            user_id="alice@example.com", display_name="Alice",
            action=AuditAction.CREATE, record_type="section",
            subject_id="s1", content=content,
        )

    def test_append_increases_length(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog
        log = Part11AuditLog()
        log.append(self._make_record())
        assert len(log) == 1

    def test_append_duplicate_id_raises(self):
        import pytest
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog
        log    = Part11AuditLog()
        record = self._make_record()
        log.append(record)
        with pytest.raises(ValueError, match="Duplicate"):
            log.append(record)

    def test_records_returns_copy(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog
        log = Part11AuditLog()
        log.append(self._make_record())
        snapshot = log.records()
        snapshot.clear()  # clearing the copy must not affect the log
        assert len(log) == 1

    def test_filter_by_user_id(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog, AuditRecord, AuditAction
        log = Part11AuditLog()
        log.append(self._make_record())
        r2 = AuditRecord.create(
            user_id="bob@example.com", display_name="Bob",
            action=AuditAction.READ, record_type="section",
            subject_id="s2", content="",
        )
        log.append(r2)
        alice_records = log.filter(user_id="alice@example.com")
        assert all(r.user_id == "alice@example.com" for r in alice_records)
        assert len(alice_records) == 1

    def test_filter_by_action(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog, AuditAction
        log = Part11AuditLog()
        log.append(self._make_record())
        results = log.filter(action=AuditAction.CREATE)
        assert len(results) == 1

    def test_verify_all_clean_log(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog, RecordIntegrity
        log = Part11AuditLog()
        log.append(self._make_record("Clean content"))
        integrity = log.verify_all()
        assert all(v == RecordIntegrity.VALID for v in integrity.values())

    def test_verify_all_detects_tampering(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog, RecordIntegrity
        log    = Part11AuditLog()
        record = self._make_record("Original")
        log.append(record)
        record.content = "Tampered"  # bypass immutability for test
        integrity = log.verify_all()
        assert any(v == RecordIntegrity.TAMPERED for v in integrity.values())

    def test_export_json_is_valid(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog
        log = Part11AuditLog()
        log.append(self._make_record())
        raw = log.export_json()
        parsed = json.loads(raw)
        assert parsed["record_count"] == 1
        assert len(parsed["records"]) == 1

    def test_filter_by_date_range(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11AuditLog
        log = Part11AuditLog()
        log.append(self._make_record())
        since = datetime.now(timezone.utc) - timedelta(minutes=1)
        until = datetime.now(timezone.utc) + timedelta(minutes=1)
        results = log.filter(since=since, until=until)
        assert len(results) == 1


# ═════════════════════════════════════════════════════════════════════════════
# AccessControlPolicy
# ═════════════════════════════════════════════════════════════════════════════

class TestAccessControlPolicy:

    def test_viewer_can_read(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("viewer", AuditAction.READ) is True

    def test_viewer_cannot_create(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("viewer", AuditAction.CREATE) is False

    def test_engineer_can_create(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("engineer", AuditAction.CREATE) is True

    def test_engineer_cannot_approve(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("engineer", AuditAction.APPROVE) is False

    def test_ra_lead_can_approve(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("ra_lead", AuditAction.APPROVE) is True

    def test_ra_lead_cannot_delete(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("ra_lead", AuditAction.DELETE) is False

    def test_admin_can_delete(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("admin", AuditAction.DELETE) is True

    def test_unknown_role_denied(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        assert policy.is_authorised("hacker", AuditAction.READ) is False

    def test_admin_has_all_access(self):
        from plugins.fda_tools.lib.cfr_part11 import AccessControlPolicy, AuditAction
        policy = AccessControlPolicy()
        for action in AuditAction:
            assert policy.is_authorised("admin", action) is True


# ═════════════════════════════════════════════════════════════════════════════
# Part11ComplianceReport
# ═════════════════════════════════════════════════════════════════════════════

class TestPart11ComplianceReport:

    SIGNING_KEY = "test_key_abc123def456ghi789jkl012mno345p"

    def _passing_config(self):
        return {
            "retention_days":         3650,
            "training_records_exist": True,
        }

    def _populated_log(self):
        from plugins.fda_tools.lib.cfr_part11 import (
            Part11AuditLog, AuditRecord, AuditAction, ElectronicSignature
        )
        log = Part11AuditLog()
        # CREATE record
        r1 = AuditRecord.create(
            user_id="alice@example.com", display_name="Alice",
            action=AuditAction.CREATE, record_type="submission",
            subject_id="k000000", content="Section content",
        )
        log.append(r1)
        # APPROVE record with signature
        r2 = AuditRecord.create(
            user_id="bob@example.com", display_name="Bob",
            action=AuditAction.APPROVE, record_type="submission",
            subject_id="k000000", content="Approved section",
        )
        sig = ElectronicSignature.sign(
            record_hash = r2.fingerprint,
            signer_id   = "bob@example.com",
            signer_name = "Bob",
            meaning     = "Electronic approval",
            signing_key = self.SIGNING_KEY,
        )
        r2.attach_signature(sig)
        log.append(r2)
        return log

    def test_report_generated_from_log(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log    = self._populated_log()
        report = Part11ComplianceReport.generate(log, self._passing_config())
        assert report.record_count == 2

    def test_passing_log_has_no_failures(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log    = self._populated_log()
        report = Part11ComplianceReport.generate(log, self._passing_config())
        assert len(report.failed_controls()) == 0

    def test_missing_training_records_fails(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log = self._populated_log()
        cfg = {**self._passing_config(), "training_records_exist": False}
        report = Part11ComplianceReport.generate(log, cfg)
        failed = [f.control for f in report.failed_controls()]
        assert any("11.10(i)" in c for c in failed)

    def test_short_retention_fails(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log = self._populated_log()
        cfg = {**self._passing_config(), "retention_days": 365}
        report = Part11ComplianceReport.generate(log, cfg)
        failed = [f.control for f in report.failed_controls()]
        assert any("11.10(c)" in c for c in failed)

    def test_tampered_record_fails(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log = self._populated_log()
        log.records()[0].content = "tampered!"  # bypass for test
        report = Part11ComplianceReport.generate(log, self._passing_config())
        failed = [f.control for f in report.failed_controls()]
        assert any("11.10(f)" in c for c in failed)

    def test_unsigned_approved_record_fails(self):
        from plugins.fda_tools.lib.cfr_part11 import (
            Part11ComplianceReport, Part11AuditLog, AuditRecord, AuditAction
        )
        log = Part11AuditLog()
        r = AuditRecord.create(
            user_id="alice@example.com", display_name="Alice",
            action=AuditAction.APPROVE, record_type="submission",
            subject_id="s1", content="Content",
        )
        # No signature attached
        log.append(r)
        report = Part11ComplianceReport.generate(log, self._passing_config())
        failed = [f.control for f in report.failed_controls()]
        assert any("11.50" in c for c in failed)

    def test_summary_contains_pass_fail(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log    = self._populated_log()
        report = Part11ComplianceReport.generate(log, self._passing_config())
        summary = report.summary()
        assert "PASS" in summary

    def test_as_dict_is_json_serialisable(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log    = self._populated_log()
        report = Part11ComplianceReport.generate(log, self._passing_config())
        json.dumps(report.as_dict())  # must not raise

    def test_passed_returns_true_for_clean_log(self):
        from plugins.fda_tools.lib.cfr_part11 import Part11ComplianceReport
        log    = self._populated_log()
        report = Part11ComplianceReport.generate(log, self._passing_config())
        assert report.passed() is True


# ═════════════════════════════════════════════════════════════════════════════
# audit() decorator
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditDecorator:

    def test_decorator_appends_record(self):
        from plugins.fda_tools.lib.cfr_part11 import (
            Part11AuditLog, AuditAction, audit
        )
        log = Part11AuditLog()

        @audit(log, "alice@example.com", "Alice", AuditAction.UPDATE,
               "section", "section-desc")
        def update_section(html: str) -> str:
            return html

        result = update_section("<p>Content</p>")
        assert result == "<p>Content</p>"
        assert len(log) == 1

    def test_decorator_record_has_correct_action(self):
        from plugins.fda_tools.lib.cfr_part11 import (
            Part11AuditLog, AuditAction, audit
        )
        log = Part11AuditLog()

        @audit(log, "alice@example.com", "Alice", AuditAction.CREATE,
               "section", "s1")
        def create_section() -> str:
            return "New section"

        create_section()
        assert log.records()[0].action == AuditAction.CREATE

    def test_decorator_preserves_return_value(self):
        from plugins.fda_tools.lib.cfr_part11 import (
            Part11AuditLog, AuditAction, audit
        )
        log = Part11AuditLog()

        @audit(log, "u", "User", AuditAction.READ, "t", "s")
        def get_data() -> dict:
            return {"key": "value"}

        result = get_data()
        assert result == {"key": "value"}
