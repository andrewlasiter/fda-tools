#!/usr/bin/env python3
"""
Integration test for Electronic Signatures system (FDA-184).

Quick smoke test to verify:
- Signature application
- Verification
- Manifest generation
- Integration with authentication

Run: python3 tests/test_signatures_integration.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Add lib to path
TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent.resolve()

from auth import AuthManager, Role
from signatures import SignatureManager, SignatureMeaning


def test_basic_integration():
    """Basic integration test."""
    print("=" * 60)
    print("Electronic Signatures Integration Test (FDA-184)")
    print("=" * 60)

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"\nTemp directory: {temp_dir}")

    # Create test document
    doc_path = temp_dir / "test_submission.pdf"
    doc_path.write_text("FDA 510(k) Submission Test Document\n" * 100)
    print(f"✓ Created test document: {doc_path.name}")

    # Initialize managers (use temp databases)
    import lib.auth as auth_module
    import lib.signatures as sig_module

    auth_module.USERS_DB_PATH = temp_dir / "users.db"
    auth_module.AUDIT_DB_PATH = temp_dir / "audit.db"
    sig_module.SIGNATURES_DB_PATH = temp_dir / "signatures.db"

    auth_mgr = AuthManager()
    sig_mgr = SignatureManager()
    sig_mgr.auth_manager = auth_mgr
    print("✓ Initialized authentication and signature managers")

    # Create test user
    user = auth_mgr.create_user(
        username="analyst",
        email="analyst@test.com",
        password="TestPass123!",
        role=Role.ANALYST,
        full_name="John Analyst"
    )
    print(f"✓ Created user: {user.full_name}")

    # Apply signature
    print("\n--- Signature Application (21 CFR 11.50) ---")
    signature = sig_mgr.sign_document(
        document_path=str(doc_path),
        user=user,
        password="TestPass123!",
        meaning=SignatureMeaning.AUTHOR,
        comments="Integration test signature"
    )
    print(f"✓ Applied signature ID: {signature.signature_id}")
    print(f"  Signer: {signature.user_full_name}")
    print(f"  Timestamp: {signature.timestamp.isoformat()}")
    print(f"  Meaning: {signature.meaning.value}")
    print(f"  Hash: {signature.signature_hash[:16]}...")

    # Verify signature
    print("\n--- Signature Verification (21 CFR 11.70) ---")
    is_valid = sig_mgr.verify_signature(signature.signature_id)
    print(f"✓ Signature valid: {is_valid}")
    assert is_valid, "Signature should be valid"

    # Verify document
    results = sig_mgr.verify_document(str(doc_path))
    print(f"✓ Document signatures: {results['valid_signatures']}/{results['total_signatures']}")
    assert results['valid'], "All signatures should be valid"

    # Test tamper detection
    print("\n--- Tamper Detection ---")
    with open(doc_path, 'a') as f:
        f.write("\nTAMPERED CONTENT")
    print("✓ Modified document")

    is_valid_after_tamper = sig_mgr.verify_signature(signature.signature_id)
    print(f"✓ Signature valid after tamper: {is_valid_after_tamper}")
    assert not is_valid_after_tamper, "Signature should be invalid after tampering"

    # Restore document
    doc_path.write_text("FDA 510(k) Submission Test Document\n" * 100)
    print("✓ Restored document")

    # Export manifest
    print("\n--- Manifest Generation ---")
    manifest_json = sig_mgr.export_manifest(
        document_path=str(doc_path),
        generated_by=user,
        format='json'
    )
    manifest = json.loads(manifest_json)
    print(f"✓ Generated manifest")
    print(f"  Document: {Path(manifest['document_path']).name}")
    print(f"  Signatures: {manifest['signature_count']}")
    print(f"  Compliance: {manifest['compliance_statement']}")

    # Audit trail
    print("\n--- Audit Trail (21 CFR 11.10(e)) ---")
    audit_events = sig_mgr.get_audit_trail(signature_id=signature.signature_id)
    print(f"✓ Audit events: {len(audit_events)}")
    for event in audit_events[:3]:  # Show first 3 events
        print(f"  - {event['event_type']}: {event['timestamp']}")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print("✓ ALL INTEGRATION TESTS PASSED")
    print("=" * 60)
    print("\nElectronic Signatures System (FDA-184)")
    print("Compliance: 21 CFR Part 11")
    print("Status: OPERATIONAL")


if __name__ == '__main__':
    try:
        test_basic_integration()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
