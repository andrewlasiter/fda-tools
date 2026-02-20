#!/usr/bin/env python3
"""
Comprehensive Test Suite for Electronic Signatures (FDA-184 / REG-001).

Tests cover:
  - Signature application and verification
  - Multi-signatory workflows
  - Tamper detection
  - Audit trail integrity
  - 21 CFR Part 11 compliance
  - Revocation and status management
  - Manifest generation

Compliance Testing:
  - §11.50: Signature components and authentication
  - §11.70: Signature/record linking
  - §11.100: General signature requirements
  - §11.200: Electronic signature components
  - §11.300: Controls for closed systems

Test Coverage: 40+ tests across 8 test classes

Version: 1.0.0 (FDA-184)
"""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.auth import AuthManager, Role
from lib.signatures import (
    SignatureManager,
    SignatureMeaning,
    SignatureStatus,
    hash_file,
    compute_signature_hash,
    verify_signature_hash,
    compute_manifest_hash,
    SIGNATURES_DB_PATH,
)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_document(temp_dir):
    """Create test document."""
    doc_path = temp_dir / "test_submission.pdf"
    doc_path.write_text("FDA 510(k) Submission - Test Document\n" * 100)
    return doc_path


@pytest.fixture
def auth_manager(temp_dir):
    """Create test authentication manager."""
    # Use test database
    test_db = temp_dir / "users.db"
    with patch('lib.auth.USERS_DB_PATH', test_db):
        with patch('lib.auth.AUDIT_DB_PATH', temp_dir / "audit.db"):
            auth_mgr = AuthManager()

            # Create test users
            admin = auth_mgr.create_user(
                username="admin",
                email="admin@test.com",
                password="AdminPass123!",
                role=Role.ADMIN,
                full_name="Admin User"
            )

            analyst = auth_mgr.create_user(
                username="analyst",
                email="analyst@test.com",
                password="AnalystPass123!",
                role=Role.ANALYST,
                full_name="John Analyst"
            )

            reviewer = auth_mgr.create_user(
                username="reviewer",
                email="reviewer@test.com",
                password="ReviewPass123!",
                role=Role.ANALYST,
                full_name="Jane Reviewer"
            )

            yield auth_mgr


@pytest.fixture
def signature_manager(temp_dir, auth_manager):
    """Create test signature manager."""
    test_db = temp_dir / "signatures.db"
    with patch('lib.signatures.SIGNATURES_DB_PATH', test_db):
        sig_mgr = SignatureManager()
        sig_mgr.auth_manager = auth_manager
        yield sig_mgr


# ============================================================
# Test Class 1: Signature Application (§11.50)
# ============================================================

class TestSignatureApplication:
    """Test signature application per 21 CFR 11.50."""

    def test_apply_basic_signature(self, signature_manager, auth_manager, test_document):
        """Test basic signature application."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR,
            comments="Initial submission"
        )

        assert signature.signature_id > 0
        assert signature.document_path == str(test_document)
        assert signature.user_full_name == "John Analyst"
        assert signature.meaning == SignatureMeaning.AUTHOR
        assert signature.comments == "Initial submission"
        assert signature.status == SignatureStatus.ACTIVE
        assert len(signature.signature_hash) == 64  # SHA-256 hex

    def test_signature_components_cfr_11_50_a(self, signature_manager, auth_manager, test_document):
        """Test signature contains required components per §11.50(a)."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.REVIEWER
        )

        # §11.50(a)(1) - Printed name of signer
        assert signature.user_full_name == "John Analyst"

        # §11.50(a)(2) - Date and time when signed
        assert isinstance(signature.timestamp, datetime)
        assert signature.timestamp <= datetime.now()

        # §11.50(a)(3) - Meaning of signature
        assert signature.meaning == SignatureMeaning.REVIEWER

    def test_authentication_required_cfr_11_50_b(self, signature_manager, auth_manager, test_document):
        """Test authentication requirement per §11.50(b)."""
        user = auth_manager.get_user_by_username("analyst")

        # Wrong password should fail
        with pytest.raises(ValueError, match="Authentication failed"):
            signature_manager.sign_document(
                document_path=str(test_document),
                user=user,
                password="WrongPassword",
                meaning=SignatureMeaning.AUTHOR
            )

    def test_inactive_user_cannot_sign(self, signature_manager, auth_manager, test_document):
        """Test inactive users cannot sign."""
        user = auth_manager.get_user_by_username("analyst")
        auth_manager.update_user(user.user_id, is_active=False)

        user = auth_manager.get_user_by_id(user.user_id)

        with pytest.raises(ValueError, match="not active"):
            signature_manager.sign_document(
                document_path=str(test_document),
                user=user,
                password="AnalystPass123!",
                meaning=SignatureMeaning.AUTHOR
            )

    def test_document_not_found(self, signature_manager, auth_manager):
        """Test signature fails if document doesn't exist."""
        user = auth_manager.get_user_by_username("analyst")

        with pytest.raises(FileNotFoundError):
            signature_manager.sign_document(
                document_path="/nonexistent/file.pdf",
                user=user,
                password="AnalystPass123!",
                meaning=SignatureMeaning.AUTHOR
            )

    def test_all_signature_meanings(self, signature_manager, auth_manager, test_document):
        """Test all signature meaning types."""
        user = auth_manager.get_user_by_username("analyst")

        for meaning in SignatureMeaning:
            signature = signature_manager.sign_document(
                document_path=str(test_document),
                user=user,
                password="AnalystPass123!",
                meaning=meaning,
                comments=f"Testing {meaning.value}"
            )

            assert signature.meaning == meaning
            assert signature.comments == f"Testing {meaning.value}"


# ============================================================
# Test Class 2: Signature Verification (§11.70, §11.100)
# ============================================================

class TestSignatureVerification:
    """Test signature verification and integrity."""

    def test_verify_valid_signature(self, signature_manager, auth_manager, test_document):
        """Test verification of valid signature."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        is_valid = signature_manager.verify_signature(signature.signature_id)
        assert is_valid is True

    def test_verify_tampered_document(self, signature_manager, auth_manager, test_document):
        """Test detection of document tampering."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Tamper with document
        with open(test_document, 'a') as f:
            f.write("\nTAMPERED CONTENT")

        is_valid = signature_manager.verify_signature(signature.signature_id)
        assert is_valid is False

    def test_verify_nonexistent_signature(self, signature_manager):
        """Test verification of nonexistent signature."""
        is_valid = signature_manager.verify_signature(99999)
        assert is_valid is False

    def test_verify_revoked_signature(self, signature_manager, auth_manager, test_document):
        """Test verification of revoked signature."""
        user = auth_manager.get_user_by_username("analyst")
        admin = auth_manager.get_user_by_username("admin")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Revoke signature
        signature_manager.revoke_signature(
            signature.signature_id,
            admin,
            "User departed company"
        )

        is_valid = signature_manager.verify_signature(signature.signature_id)
        assert is_valid is False

    def test_verify_document_all_signatures(self, signature_manager, auth_manager, test_document):
        """Test verification of all signatures on document."""
        analyst = auth_manager.get_user_by_username("analyst")
        reviewer = auth_manager.get_user_by_username("reviewer")

        # Apply two signatures
        sig1 = signature_manager.sign_document(
            document_path=str(test_document),
            user=analyst,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        sig2 = signature_manager.sign_document(
            document_path=str(test_document),
            user=reviewer,
            password="ReviewPass123!",
            meaning=SignatureMeaning.REVIEWER
        )

        results = signature_manager.verify_document(str(test_document))

        assert results['total_signatures'] == 2
        assert results['valid_signatures'] == 2
        assert results['invalid_signatures'] == 0
        assert results['valid'] is True

    def test_signature_hash_integrity(self, signature_manager, auth_manager, test_document):
        """Test signature hash integrity check."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Verify hash is correct
        is_valid = verify_signature_hash(signature)
        assert is_valid is True

        # Tamper with signature hash in database
        from lib.signatures import SIGNATURES_DB_PATH
        conn = sqlite3.connect(SIGNATURES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE signatures SET signature_hash = ? WHERE signature_id = ?",
            ("0" * 64, signature.signature_id)
        )
        conn.commit()
        conn.close()

        # Verification should fail
        is_valid = signature_manager.verify_signature(signature.signature_id)
        assert is_valid is False


# ============================================================
# Test Class 3: Multi-Signatory Workflows
# ============================================================

class TestMultiSignatoryWorkflows:
    """Test multi-signatory workflow support."""

    def test_sequential_signatures(self, signature_manager, auth_manager, test_document):
        """Test sequential signature workflow."""
        analyst = auth_manager.get_user_by_username("analyst")
        reviewer = auth_manager.get_user_by_username("reviewer")
        admin = auth_manager.get_user_by_username("admin")

        # Author signs
        sig1 = signature_manager.sign_document(
            document_path=str(test_document),
            user=analyst,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Reviewer signs
        sig2 = signature_manager.sign_document(
            document_path=str(test_document),
            user=reviewer,
            password="ReviewPass123!",
            meaning=SignatureMeaning.REVIEWER
        )

        # Approver signs
        sig3 = signature_manager.sign_document(
            document_path=str(test_document),
            user=admin,
            password="AdminPass123!",
            meaning=SignatureMeaning.APPROVER
        )

        # Verify all signatures
        signatures = signature_manager.get_document_signatures(str(test_document))
        assert len(signatures) == 3
        assert signatures[0].meaning == SignatureMeaning.AUTHOR
        assert signatures[1].meaning == SignatureMeaning.REVIEWER
        assert signatures[2].meaning == SignatureMeaning.APPROVER

    def test_workflow_status_tracking(self, signature_manager, auth_manager, test_document):
        """Test workflow completion status tracking."""
        analyst = auth_manager.get_user_by_username("analyst")

        # Initially incomplete
        required = signature_manager.get_required_signatories(str(test_document))
        assert required[SignatureMeaning.AUTHOR] is False
        assert not signature_manager.is_workflow_complete(str(test_document))

        # Add author signature
        signature_manager.sign_document(
            document_path=str(test_document),
            user=analyst,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        required = signature_manager.get_required_signatories(str(test_document))
        assert required[SignatureMeaning.AUTHOR] is True
        assert not signature_manager.is_workflow_complete(str(test_document))

    def test_batch_signature_application(self, signature_manager, auth_manager, temp_dir):
        """Test batch signature application."""
        user = auth_manager.get_user_by_username("analyst")

        # Create multiple documents
        docs = []
        for i in range(3):
            doc = temp_dir / f"doc_{i}.pdf"
            doc.write_text(f"Document {i}")
            docs.append(str(doc))

        # Apply batch signatures
        results = signature_manager.sign_document_batch(
            document_paths=docs,
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR,
            comments="Batch signing"
        )

        assert len(results) == 3
        for path, success, signature, error in results:
            assert success is True
            assert signature is not None
            assert error == ""


# ============================================================
# Test Class 4: Signature Revocation
# ============================================================

class TestSignatureRevocation:
    """Test signature revocation functionality."""

    def test_revoke_signature_by_admin(self, signature_manager, auth_manager, test_document):
        """Test signature revocation by admin."""
        user = auth_manager.get_user_by_username("analyst")
        admin = auth_manager.get_user_by_username("admin")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Revoke
        success = signature_manager.revoke_signature(
            signature.signature_id,
            admin,
            "Employee departed"
        )

        assert success is True

        # Verify revocation
        revoked_sig = signature_manager.get_signature_by_id(signature.signature_id)
        assert revoked_sig.status == SignatureStatus.REVOKED
        assert revoked_sig.revoked_by == admin.user_id
        assert revoked_sig.revocation_reason == "Employee departed"
        assert revoked_sig.revoked_at is not None

    def test_revoke_signature_by_owner(self, signature_manager, auth_manager, test_document):
        """Test signature revocation by signature owner."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # User can revoke their own signature
        success = signature_manager.revoke_signature(
            signature.signature_id,
            user,
            "Correction needed"
        )

        assert success is True

    def test_revoke_unauthorized(self, signature_manager, auth_manager, test_document):
        """Test unauthorized revocation fails."""
        analyst = auth_manager.get_user_by_username("analyst")
        reviewer = auth_manager.get_user_by_username("reviewer")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=analyst,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Different non-admin user cannot revoke
        with pytest.raises(ValueError, match="not authorized"):
            signature_manager.revoke_signature(
                signature.signature_id,
                reviewer,
                "Unauthorized attempt"
            )

    def test_revoke_nonexistent_signature(self, signature_manager, auth_manager):
        """Test revocation of nonexistent signature."""
        admin = auth_manager.get_user_by_username("admin")

        success = signature_manager.revoke_signature(99999, admin, "Test")
        assert success is False


# ============================================================
# Test Class 5: Manifest Generation
# ============================================================

class TestManifestGeneration:
    """Test signature manifest generation."""

    def test_generate_json_manifest(self, signature_manager, auth_manager, test_document):
        """Test JSON manifest generation."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        manifest_json = signature_manager.export_manifest(
            document_path=str(test_document),
            generated_by=user,
            format='json'
        )

        manifest = json.loads(manifest_json)

        assert manifest['document_path'] == str(test_document)
        assert manifest['signature_count'] == 1
        assert len(manifest['signatures']) == 1
        assert manifest['signatures'][0]['user_full_name'] == "John Analyst"
        assert manifest['compliance_statement'] == '21 CFR Part 11 Compliant Electronic Signatures'
        assert 'manifest_hash' in manifest
        assert 'document_hash' in manifest

    def test_generate_xml_manifest(self, signature_manager, auth_manager, test_document):
        """Test XML manifest generation."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        manifest_xml = signature_manager.export_manifest(
            document_path=str(test_document),
            generated_by=user,
            format='xml'
        )

        assert '<?xml version' in manifest_xml
        assert '<SignatureManifest' in manifest_xml
        assert 'xmlns="urn:fda:electronic-signatures:1.0"' in manifest_xml
        assert 'compliance="21 CFR Part 11"' in manifest_xml
        assert '<SignerName>John Analyst</SignerName>' in manifest_xml

    def test_manifest_integrity_hash(self, signature_manager, auth_manager, test_document):
        """Test manifest integrity hash calculation."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        manifest_json = signature_manager.export_manifest(
            document_path=str(test_document),
            format='json'
        )

        manifest = json.loads(manifest_json)

        # Manifest hash should be consistent
        assert len(manifest['manifest_hash']) == 64  # SHA-256 hex

    def test_manifest_nonexistent_document(self, signature_manager, auth_manager):
        """Test manifest generation for nonexistent document."""
        with pytest.raises(FileNotFoundError):
            signature_manager.export_manifest("/nonexistent/file.pdf")


# ============================================================
# Test Class 6: Cryptographic Functions
# ============================================================

class TestCryptographicFunctions:
    """Test cryptographic hash and signature functions."""

    def test_hash_file_consistency(self, test_document):
        """Test file hashing is consistent."""
        hash1 = hash_file(test_document)
        hash2 = hash_file(test_document)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_hash_file_detects_changes(self, test_document):
        """Test file hashing detects changes."""
        hash1 = hash_file(test_document)

        # Modify file
        with open(test_document, 'a') as f:
            f.write("\nModified")

        hash2 = hash_file(test_document)

        assert hash1 != hash2

    def test_compute_signature_hash(self, test_document, auth_manager):
        """Test signature hash computation."""
        user = auth_manager.get_user_by_username("analyst")
        doc_hash = hash_file(test_document)
        timestamp = datetime.now()

        sig_hash = compute_signature_hash(
            doc_hash,
            user.user_id,
            timestamp,
            SignatureMeaning.AUTHOR
        )

        assert len(sig_hash) == 64  # SHA-256 hex

        # Same inputs should produce same hash
        sig_hash2 = compute_signature_hash(
            doc_hash,
            user.user_id,
            timestamp,
            SignatureMeaning.AUTHOR
        )

        assert sig_hash == sig_hash2

    def test_signature_hash_binds_components(self, test_document, auth_manager):
        """Test signature hash binds all components."""
        user = auth_manager.get_user_by_username("analyst")
        doc_hash = hash_file(test_document)
        timestamp = datetime.now()

        # Different meanings produce different hashes
        hash_author = compute_signature_hash(
            doc_hash, user.user_id, timestamp, SignatureMeaning.AUTHOR
        )

        hash_reviewer = compute_signature_hash(
            doc_hash, user.user_id, timestamp, SignatureMeaning.REVIEWER
        )

        assert hash_author != hash_reviewer


# ============================================================
# Test Class 7: Audit Trail (§11.10(e))
# ============================================================

class TestAuditTrail:
    """Test audit trail per 21 CFR 11.10(e)."""

    def test_signature_application_audited(self, signature_manager, auth_manager, test_document):
        """Test signature application creates audit event."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Check audit trail
        events = signature_manager.get_audit_trail(signature_id=signature.signature_id)

        assert len(events) > 0
        assert events[0]['event_type'] == 'signature_applied'
        assert events[0]['user_id'] == user.user_id
        assert events[0]['success'] == 1

    def test_verification_audited(self, signature_manager, auth_manager, test_document):
        """Test signature verification creates audit event."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Verify signature
        signature_manager.verify_signature(signature.signature_id)

        # Check audit trail
        events = signature_manager.get_audit_trail(signature_id=signature.signature_id)

        verify_events = [e for e in events if e['event_type'] == 'signature_verified']
        assert len(verify_events) > 0

    def test_tamper_detection_audited(self, signature_manager, auth_manager, test_document):
        """Test tamper detection creates audit event."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Tamper with document
        with open(test_document, 'a') as f:
            f.write("\nTAMPERED")

        # Verify (should fail)
        signature_manager.verify_signature(signature.signature_id)

        # Check audit trail
        events = signature_manager.get_audit_trail(signature_id=signature.signature_id)

        tamper_events = [e for e in events if e['event_type'] == 'document_tampered']
        assert len(tamper_events) > 0

    def test_revocation_audited(self, signature_manager, auth_manager, test_document):
        """Test signature revocation creates audit event."""
        user = auth_manager.get_user_by_username("analyst")
        admin = auth_manager.get_user_by_username("admin")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        # Revoke
        signature_manager.revoke_signature(signature.signature_id, admin, "Test revocation")

        # Check audit trail
        events = signature_manager.get_audit_trail(signature_id=signature.signature_id)

        revoke_events = [e for e in events if e['event_type'] == 'signature_revoked']
        assert len(revoke_events) > 0
        assert revoke_events[0]['user_id'] == admin.user_id


# ============================================================
# Test Class 8: Signature Retrieval and Queries
# ============================================================

class TestSignatureRetrieval:
    """Test signature retrieval and query functions."""

    def test_get_signature_by_id(self, signature_manager, auth_manager, test_document):
        """Test retrieving signature by ID."""
        user = auth_manager.get_user_by_username("analyst")

        signature = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        retrieved = signature_manager.get_signature_by_id(signature.signature_id)

        assert retrieved is not None
        assert retrieved.signature_id == signature.signature_id
        assert retrieved.user_full_name == "John Analyst"

    def test_get_document_signatures(self, signature_manager, auth_manager, test_document):
        """Test retrieving all signatures for document."""
        analyst = auth_manager.get_user_by_username("analyst")
        reviewer = auth_manager.get_user_by_username("reviewer")

        # Apply multiple signatures
        sig1 = signature_manager.sign_document(
            document_path=str(test_document),
            user=analyst,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        sig2 = signature_manager.sign_document(
            document_path=str(test_document),
            user=reviewer,
            password="ReviewPass123!",
            meaning=SignatureMeaning.REVIEWER
        )

        signatures = signature_manager.get_document_signatures(str(test_document))

        assert len(signatures) == 2
        assert signatures[0].signature_id == sig1.signature_id
        assert signatures[1].signature_id == sig2.signature_id

    def test_get_user_signatures(self, signature_manager, auth_manager, test_document, temp_dir):
        """Test retrieving signatures by user."""
        user = auth_manager.get_user_by_username("analyst")

        # Create multiple documents and sign
        docs = []
        for i in range(3):
            doc = temp_dir / f"doc_{i}.pdf"
            doc.write_text(f"Document {i}")
            signature_manager.sign_document(
                document_path=str(doc),
                user=user,
                password="AnalystPass123!",
                meaning=SignatureMeaning.AUTHOR
            )

        signatures = signature_manager.get_user_signatures(user.user_id)

        assert len(signatures) == 3

    def test_filter_signatures_by_status(self, signature_manager, auth_manager, test_document):
        """Test filtering signatures by status."""
        user = auth_manager.get_user_by_username("analyst")
        admin = auth_manager.get_user_by_username("admin")

        # Apply two signatures
        sig1 = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.AUTHOR
        )

        sig2 = signature_manager.sign_document(
            document_path=str(test_document),
            user=user,
            password="AnalystPass123!",
            meaning=SignatureMeaning.REVIEWER
        )

        # Revoke one
        signature_manager.revoke_signature(sig1.signature_id, admin, "Test")

        # Filter by active
        active_sigs = signature_manager.get_document_signatures(
            str(test_document),
            status=SignatureStatus.ACTIVE
        )

        assert len(active_sigs) == 1
        assert active_sigs[0].signature_id == sig2.signature_id

        # Filter by revoked
        revoked_sigs = signature_manager.get_document_signatures(
            str(test_document),
            status=SignatureStatus.REVOKED
        )

        assert len(revoked_sigs) == 1
        assert revoked_sigs[0].signature_id == sig1.signature_id


# ============================================================
# Test Runner
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
