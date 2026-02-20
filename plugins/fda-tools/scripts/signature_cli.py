#!/usr/bin/env python3
"""
Electronic Signature CLI (FDA-184 / REG-001).

Command-line interface for managing electronic signatures per 21 CFR Part 11.

Commands:
  sign          Apply electronic signature to document
  verify        Verify signature or document
  list          List signatures
  revoke        Revoke signature
  manifest      Export signature manifest
  audit         View audit trail

Usage:
    python3 scripts/signature_cli.py sign --document file.pdf --meaning author
    python3 scripts/signature_cli.py verify --signature 123
    python3 scripts/signature_cli.py list --document file.pdf
    python3 scripts/signature_cli.py manifest --document file.pdf --output manifest.json

Version: 1.0.0 (FDA-184)
"""

import argparse
import getpass
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.auth import AuthManager, Role
from lib.signatures import (
    SignatureManager,
    SignatureMeaning,
    SignatureStatus,
)

logger = logging.getLogger(__name__)


# ============================================================
# Authentication Helpers
# ============================================================

def authenticate_user(auth_mgr: AuthManager) -> Optional[tuple]:
    """Interactively authenticate user.

    Returns:
        Tuple of (user, password) or None on failure
    """
    print("\n" + "=" * 60)
    print("USER AUTHENTICATION (21 CFR 11.50(b))")
    print("=" * 60)

    username = input("Username: ").strip()
    if not username:
        print("Authentication cancelled.")
        return None

    password = getpass.getpass("Password (hidden): ")
    if not password:
        print("Authentication cancelled.")
        return None

    # Authenticate
    session = auth_mgr.login(username, password)
    if not session:
        print("✗ Authentication failed - incorrect username or password")
        return None

    user = auth_mgr.get_user_by_username(username)
    print(f"✓ Authenticated as: {user.full_name} ({user.role.value})")

    return (user, password)


def re_authenticate(user_full_name: str) -> str:
    """Re-authenticate user for signature (21 CFR 11.50(b)).

    Args:
        user_full_name: User's full name for display

    Returns:
        Password or empty string on cancellation
    """
    print(f"\nRe-authentication required for: {user_full_name}")
    password = getpass.getpass("Password (hidden): ")
    return password


# ============================================================
# Command Implementations
# ============================================================

def cmd_sign(args, auth_mgr: AuthManager, sig_mgr: SignatureManager):
    """Sign document command."""
    # Authenticate user
    auth_result = authenticate_user(auth_mgr)
    if not auth_result:
        return 1

    user, password = auth_result

    # Get document path
    doc_path = Path(args.document).resolve()
    if not doc_path.exists():
        print(f"✗ Document not found: {doc_path}")
        return 1

    # Get signature meaning
    try:
        meaning = SignatureMeaning(args.meaning)
    except ValueError:
        print(f"✗ Invalid signature meaning: {args.meaning}")
        print(f"Valid values: {[m.value for m in SignatureMeaning]}")
        return 1

    # Get optional comments
    comments = None
    if args.comments:
        comments = args.comments
    elif args.interactive:
        print("\nOptional signature comments:")
        comments = input("Comments (or press Enter to skip): ").strip() or None

    # Confirmation
    print("\n" + "-" * 60)
    print("CONFIRM ELECTRONIC SIGNATURE")
    print("-" * 60)
    print(f"Document:  {doc_path.name}")
    print(f"Signer:    {user.full_name}")
    print(f"Meaning:   {meaning.value}")
    if comments:
        print(f"Comments:  {comments}")

    if args.interactive:
        confirm = input("\nApply signature? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Signature cancelled.")
            return 0

    # Re-authentication required (21 CFR 11.50(b))
    if args.interactive:
        reauth_password = re_authenticate(user.full_name)
        if not reauth_password:
            print("Signature cancelled.")
            return 0
    else:
        reauth_password = password

    # Apply signature
    try:
        signature = sig_mgr.sign_document(
            document_path=str(doc_path),
            user=user,
            password=reauth_password,
            meaning=meaning,
            comments=comments
        )

        print("\n" + "=" * 60)
        print("✓ SIGNATURE APPLIED SUCCESSFULLY")
        print("=" * 60)
        print(f"Signature ID:   {signature.signature_id}")
        print(f"Document:       {doc_path.name}")
        print(f"Signer:         {signature.user_full_name}")
        print(f"Timestamp:      {signature.timestamp.isoformat()}")
        print(f"Meaning:        {signature.meaning.value}")
        if signature.comments:
            print(f"Comments:       {signature.comments}")
        print(f"Hash:           {signature.signature_hash[:16]}...")

        # Show workflow status
        if args.show_workflow:
            required = sig_mgr.get_required_signatories(str(doc_path))
            print("\nSignature Workflow Status:")
            for sig_meaning, completed in required.items():
                status = "✓" if completed else "○"
                print(f"  {status} {sig_meaning.value.replace('_', ' ').title()}")

        return 0

    except Exception as e:
        print(f"\n✗ Failed to apply signature: {e}")
        logger.exception("Signature application failed")
        return 1


def cmd_verify(args, auth_mgr: AuthManager, sig_mgr: SignatureManager):
    """Verify signature or document command."""
    if args.signature:
        # Verify specific signature
        print("\n" + "=" * 60)
        print(f"VERIFYING SIGNATURE: {args.signature}")
        print("=" * 60)

        is_valid = sig_mgr.verify_signature(args.signature)

        if is_valid:
            signature = sig_mgr.get_signature_by_id(args.signature)
            print("✓ SIGNATURE VALID")
            print(f"\nSignature ID:   {signature.signature_id}")
            print(f"Document:       {Path(signature.document_path).name}")
            print(f"Signer:         {signature.user_full_name}")
            print(f"Timestamp:      {signature.timestamp.isoformat()}")
            print(f"Meaning:        {signature.meaning.value}")
            print(f"Status:         {signature.status.value}")
            if signature.comments:
                print(f"Comments:       {signature.comments}")
            return 0
        else:
            print("✗ SIGNATURE INVALID")
            print("\nPossible reasons:")
            print("  - Signature has been revoked")
            print("  - Document has been modified")
            print("  - Signature integrity compromised")
            print("  - User account invalid")
            return 1

    elif args.document:
        # Verify all signatures on document
        doc_path = Path(args.document).resolve()
        if not doc_path.exists():
            print(f"✗ Document not found: {doc_path}")
            return 1

        print("\n" + "=" * 60)
        print(f"VERIFYING DOCUMENT: {doc_path.name}")
        print("=" * 60)

        results = sig_mgr.verify_document(str(doc_path))

        print(f"\nTotal signatures: {results['total_signatures']}")
        print(f"Valid:            {results['valid_signatures']}")
        print(f"Invalid:          {results['invalid_signatures']}")

        if results['total_signatures'] == 0:
            print("\nNo signatures found on document.")
            return 0

        print("\nSignature Details:")
        print("-" * 60)

        for signature, is_valid in results['signatures']:
            status = "✓ VALID" if is_valid else "✗ INVALID"
            print(f"\n{status}")
            print(f"  ID:        {signature.signature_id}")
            print(f"  Signer:    {signature.user_full_name}")
            print(f"  Meaning:   {signature.meaning.value}")
            print(f"  Timestamp: {signature.timestamp.isoformat()}")
            if signature.comments:
                print(f"  Comments:  {signature.comments}")

        if results['valid']:
            print("\n✓ ALL SIGNATURES VALID")
            return 0
        else:
            print("\n✗ SOME SIGNATURES INVALID")
            return 1

    else:
        print("Error: Must specify --signature or --document")
        return 1


def cmd_list(args, auth_mgr: AuthManager, sig_mgr: SignatureManager):
    """List signatures command."""
    if args.document:
        # List signatures for document
        doc_path = Path(args.document).resolve()
        signatures = sig_mgr.get_document_signatures(str(doc_path))

        print("\n" + "=" * 80)
        print(f"SIGNATURES FOR: {doc_path.name}")
        print("=" * 80)
        print(f"Total signatures: {len(signatures)}\n")

        if not signatures:
            print("No signatures found.")
            return 0

        # Header
        print(f"{'ID':<6} {'Signer':<25} {'Meaning':<20} {'Timestamp':<20} {'Status':<10}")
        print("-" * 80)

        # Signatures
        for sig in signatures:
            sig_id = str(sig.signature_id)
            signer = sig.user_full_name[:24]
            meaning = sig.meaning.value[:19]
            timestamp = sig.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = sig.status.value

            print(f"{sig_id:<6} {signer:<25} {meaning:<20} {timestamp:<20} {status:<10}")

            if args.verbose and sig.comments:
                print(f"       Comments: {sig.comments}")

    elif args.user:
        # List signatures by user
        user = auth_mgr.get_user_by_username(args.user)
        if not user:
            print(f"✗ User not found: {args.user}")
            return 1

        signatures = sig_mgr.get_user_signatures(user.user_id, limit=args.limit)

        print("\n" + "=" * 100)
        print(f"SIGNATURES BY: {user.full_name} ({user.username})")
        print("=" * 100)
        print(f"Total signatures: {len(signatures)}\n")

        if not signatures:
            print("No signatures found.")
            return 0

        # Header
        print(f"{'ID':<6} {'Document':<30} {'Meaning':<20} {'Timestamp':<20} {'Status':<10}")
        print("-" * 100)

        # Signatures
        for sig in signatures:
            sig_id = str(sig.signature_id)
            doc_name = Path(sig.document_path).name[:29]
            meaning = sig.meaning.value[:19]
            timestamp = sig.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = sig.status.value

            print(f"{sig_id:<6} {doc_name:<30} {meaning:<20} {timestamp:<20} {status:<10}")

    else:
        print("Error: Must specify --document or --user")
        return 1

    return 0


def cmd_revoke(args, auth_mgr: AuthManager, sig_mgr: SignatureManager):
    """Revoke signature command."""
    # Authenticate admin user
    auth_result = authenticate_user(auth_mgr)
    if not auth_result:
        return 1

    user, password = auth_result

    # Get signature
    signature = sig_mgr.get_signature_by_id(args.signature)
    if not signature:
        print(f"✗ Signature not found: {args.signature}")
        return 1

    # Check if already revoked
    if signature.status == SignatureStatus.REVOKED:
        print(f"✗ Signature already revoked: {args.signature}")
        return 1

    # Display signature details
    print("\n" + "=" * 60)
    print("REVOKE SIGNATURE")
    print("=" * 60)
    print(f"Signature ID:   {signature.signature_id}")
    print(f"Document:       {Path(signature.document_path).name}")
    print(f"Signer:         {signature.user_full_name}")
    print(f"Timestamp:      {signature.timestamp.isoformat()}")
    print(f"Meaning:        {signature.meaning.value}")

    # Get revocation reason
    if args.reason:
        reason = args.reason
    else:
        print("\nRevocation reason:")
        reason = input("Reason: ").strip()
        if not reason:
            print("Revocation cancelled.")
            return 0

    # Confirmation
    print(f"\nReason: {reason}")
    confirm = input("\nRevoke this signature? (yes/no): ").strip().lower()
    if confirm not in ('yes', 'y'):
        print("Revocation cancelled.")
        return 0

    # Revoke signature
    try:
        sig_mgr.revoke_signature(
            signature_id=args.signature,
            revoked_by=user,
            reason=reason
        )

        print("\n✓ Signature revoked successfully")
        return 0

    except Exception as e:
        print(f"\n✗ Failed to revoke signature: {e}")
        logger.exception("Signature revocation failed")
        return 1


def cmd_manifest(args, auth_mgr: AuthManager, sig_mgr: SignatureManager):
    """Export signature manifest command."""
    # Get document path
    doc_path = Path(args.document).resolve()
    if not doc_path.exists():
        print(f"✗ Document not found: {doc_path}")
        return 1

    # Optional authentication
    user = None
    if args.authenticate:
        auth_result = authenticate_user(auth_mgr)
        if not auth_result:
            return 1
        user, _ = auth_result

    # Determine output format
    format = args.format.lower()
    if format not in ('json', 'xml'):
        print(f"✗ Invalid format: {format}. Use 'json' or 'xml'.")
        return 1

    # Generate manifest
    try:
        manifest_str = sig_mgr.export_manifest(
            document_path=str(doc_path),
            generated_by=user,
            format=format
        )

        # Output manifest
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(manifest_str)
            print(f"\n✓ Manifest exported to: {output_path}")
        else:
            print("\n" + "=" * 60)
            print("SIGNATURE MANIFEST")
            print("=" * 60)
            print(manifest_str)

        # Show summary
        manifest_data = json.loads(manifest_str) if format == 'json' else {}
        if manifest_data:
            print(f"\nDocument:         {Path(manifest_data['document_path']).name}")
            print(f"Signature count:  {manifest_data.get('signature_count', 0)}")
            print(f"Document hash:    {manifest_data['document_hash'][:16]}...")
            print(f"Manifest hash:    {manifest_data['manifest_hash'][:16]}...")

        return 0

    except Exception as e:
        print(f"\n✗ Failed to export manifest: {e}")
        logger.exception("Manifest export failed")
        return 1


def cmd_audit(args, auth_mgr: AuthManager, sig_mgr: SignatureManager):
    """View audit trail command."""
    # Authenticate user (audit access requires authentication)
    auth_result = authenticate_user(auth_mgr)
    if not auth_result:
        return 1

    user, _ = auth_result

    # Check authorization (only admins can view full audit trail)
    if args.all and user.role != Role.ADMIN:
        print("✗ Admin privileges required to view full audit trail")
        return 1

    # Get audit events
    signature_id = args.signature if args.signature else None
    document_path = args.document if args.document else None
    user_id = None

    if args.user:
        target_user = auth_mgr.get_user_by_username(args.user)
        if not target_user:
            print(f"✗ User not found: {args.user}")
            return 1
        user_id = target_user.user_id

    events = sig_mgr.get_audit_trail(
        signature_id=signature_id,
        document_path=document_path,
        user_id=user_id,
        limit=args.limit
    )

    # Display audit trail
    print("\n" + "=" * 100)
    print("SIGNATURE AUDIT TRAIL")
    print("=" * 100)
    print(f"Total events: {len(events)}\n")

    if not events:
        print("No audit events found.")
        return 0

    # Header
    print(f"{'Timestamp':<20} {'Event':<30} {'User':<20} {'Sig ID':<8} {'Success':<8}")
    print("-" * 100)

    # Events
    for event in events:
        timestamp = event['timestamp'][:19]  # Strip microseconds
        event_type = event['event_type'][:29]
        username = (event.get('username') or 'system')[:19]
        sig_id = str(event.get('signature_id') or '-')
        success = "✓" if event['success'] else "✗"

        print(f"{timestamp:<20} {event_type:<30} {username:<20} {sig_id:<8} {success:<8}")

        if args.verbose:
            details = json.loads(event.get('details', '{}'))
            if details:
                print(f"         Details: {json.dumps(details, separators=(',', ':'))}")

    return 0


# ============================================================
# Main CLI
# ============================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Electronic Signature Management (21 CFR Part 11)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply signature to document
  python3 scripts/signature_cli.py sign --document submission.pdf --meaning author

  # Verify signature
  python3 scripts/signature_cli.py verify --signature 123

  # Verify all signatures on document
  python3 scripts/signature_cli.py verify --document submission.pdf

  # List signatures for document
  python3 scripts/signature_cli.py list --document submission.pdf

  # List signatures by user
  python3 scripts/signature_cli.py list --user jsmith

  # Revoke signature
  python3 scripts/signature_cli.py revoke --signature 123 --reason "User departed"

  # Export manifest
  python3 scripts/signature_cli.py manifest --document submission.pdf --output manifest.json

  # View audit trail
  python3 scripts/signature_cli.py audit --signature 123

Compliance: 21 CFR Part 11 (Electronic Records and Signatures)
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Sign command
    sign_parser = subparsers.add_parser('sign', help='Apply electronic signature')
    sign_parser.add_argument('--document', required=True, help='Document to sign')
    sign_parser.add_argument(
        '--meaning',
        required=True,
        help=f'Signature meaning ({", ".join([m.value for m in SignatureMeaning])})'
    )
    sign_parser.add_argument('--comments', help='Signature comments')
    sign_parser.add_argument(
        '--interactive',
        action='store_true',
        default=True,
        help='Interactive mode (default)'
    )
    sign_parser.add_argument(
        '--show-workflow',
        action='store_true',
        help='Show signature workflow status'
    )

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify signature or document')
    verify_group = verify_parser.add_mutually_exclusive_group(required=True)
    verify_group.add_argument('--signature', type=int, help='Signature ID to verify')
    verify_group.add_argument('--document', help='Document to verify all signatures')

    # List command
    list_parser = subparsers.add_parser('list', help='List signatures')
    list_group = list_parser.add_mutually_exclusive_group(required=True)
    list_group.add_argument('--document', help='List signatures for document')
    list_group.add_argument('--user', help='List signatures by user')
    list_parser.add_argument('--limit', type=int, default=100, help='Maximum results')
    list_parser.add_argument('--verbose', action='store_true', help='Show details')

    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke signature')
    revoke_parser.add_argument('--signature', type=int, required=True, help='Signature ID')
    revoke_parser.add_argument('--reason', help='Revocation reason')

    # Manifest command
    manifest_parser = subparsers.add_parser('manifest', help='Export signature manifest')
    manifest_parser.add_argument('--document', required=True, help='Document path')
    manifest_parser.add_argument('--output', help='Output file (default: stdout)')
    manifest_parser.add_argument(
        '--format',
        choices=['json', 'xml'],
        default='json',
        help='Output format'
    )
    manifest_parser.add_argument(
        '--authenticate',
        action='store_true',
        help='Require authentication'
    )

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='View audit trail')
    audit_parser.add_argument('--signature', type=int, help='Filter by signature ID')
    audit_parser.add_argument('--document', help='Filter by document')
    audit_parser.add_argument('--user', help='Filter by username')
    audit_parser.add_argument('--all', action='store_true', help='View all events (admin only)')
    audit_parser.add_argument('--limit', type=int, default=100, help='Maximum events')
    audit_parser.add_argument('--verbose', action='store_true', help='Show event details')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    if not args.command:
        parser.print_help()
        return 0

    # Initialize managers
    auth_mgr = AuthManager()
    sig_mgr = SignatureManager()

    # Execute command
    if args.command == 'sign':
        return cmd_sign(args, auth_mgr, sig_mgr)
    elif args.command == 'verify':
        return cmd_verify(args, auth_mgr, sig_mgr)
    elif args.command == 'list':
        return cmd_list(args, auth_mgr, sig_mgr)
    elif args.command == 'revoke':
        return cmd_revoke(args, auth_mgr, sig_mgr)
    elif args.command == 'manifest':
        return cmd_manifest(args, auth_mgr, sig_mgr)
    elif args.command == 'audit':
        return cmd_audit(args, auth_mgr, sig_mgr)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
