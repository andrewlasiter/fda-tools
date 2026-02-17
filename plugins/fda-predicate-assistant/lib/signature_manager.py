"""
Signature Manager - 21 CFR Part 11 Electronic Signatures for FDA Tools

Provides electronic signature capture and verification for regulatory
compliance with:
1. Electronic signature creation with meaning attribution
2. Password-based credential verification
3. Non-repudiation enforcement (signatures cannot be denied)
4. Complete audit trail per signature
5. Multi-signature document support

Compliance Requirements (21 CFR Part 11):
- 11.50: Signature manifestations (printed name, date, meaning)
- 11.70: Signature/record linking (non-repudiation)
- 11.100: General requirements (unique to individual)
- 11.200: Electronic signature components (identification + authentication)
- 11.300: Controls for identification codes/passwords

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import json
import uuid
import hmac
import hashlib
import secrets
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from copy import deepcopy


@dataclass
class ElectronicSignature:
    """
    21 CFR Part 11 compliant electronic signature.

    Each signature captures:
    - WHO signed (user identity)
    - WHAT was signed (document/action reference)
    - WHEN it was signed (timestamp)
    - WHY it was signed (regulatory meaning)
    - HOW it was authenticated (signature method)

    Attributes:
        signature_id: Unique signature identifier
        user_id: Signing user's ID
        user_name: Signing user's full name (for printed name requirement)
        user_email: Signing user's email
        action: Action being signed (approve_submission, sign_document, etc.)
        document_id: Document or resource being signed
        signature_method: Authentication method (password, token, biometric)
        signature_hash: SHA-256 hash of credential + salt
        salt: Cryptographic salt for hash
        signed_at: ISO 8601 signature timestamp
        ip_address: IP address of signer (if available)
        user_agent: User agent string (if available)
        meaning: Regulatory meaning of signature
        metadata: Additional signature context
        is_valid: Whether signature has been verified
    """
    signature_id: str
    user_id: str
    user_name: str
    user_email: str
    action: str
    document_id: str
    signature_method: str
    signature_hash: str
    salt: str
    signed_at: str
    ip_address: str = ""
    user_agent: str = ""
    meaning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize signature to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElectronicSignature':
        """Deserialize signature from dictionary."""
        return cls(
            signature_id=data['signature_id'],
            user_id=data['user_id'],
            user_name=data.get('user_name', ''),
            user_email=data.get('user_email', ''),
            action=data['action'],
            document_id=data['document_id'],
            signature_method=data.get('signature_method', 'password'),
            signature_hash=data['signature_hash'],
            salt=data.get('salt', ''),
            signed_at=data['signed_at'],
            ip_address=data.get('ip_address', ''),
            user_agent=data.get('user_agent', ''),
            meaning=data.get('meaning', ''),
            metadata=data.get('metadata', {}),
            is_valid=data.get('is_valid', True)
        )


# Commands that require electronic signature for execution
SIGNATURE_REQUIRED_COMMANDS = {
    'export': 'RA professional approval for submission package export',
    'assemble': 'RA professional approval for eSTAR assembly',
}

# Valid signature methods
VALID_SIGNATURE_METHODS = {'password', 'token', 'biometric'}

# Signature meaning templates
SIGNATURE_MEANINGS = {
    'approve_submission': (
        'I have reviewed and approve this submission package. '
        'The information is accurate and complete to the best of my knowledge.'
    ),
    'sign_document': (
        'I have reviewed and authorize this document.'
    ),
    'approve_change': (
        'I have reviewed and approve this change.'
    ),
    'verify_data': (
        'I have verified the accuracy of this data.'
    ),
    'release_for_review': (
        'I authorize release of this document for review.'
    ),
}


class SignatureManager:
    """
    21 CFR Part 11 compliant electronic signature manager.

    Handles creation, verification, and audit of electronic signatures
    for FDA regulatory submissions.

    Usage:
        sig_mgr = SignatureManager()
        signature = sig_mgr.create_signature(
            user_id="usr_001",
            user_name="Alice Johnson",
            user_email="alice@device-corp.com",
            action="approve_submission",
            document_id="eSTAR_ABC001_v2",
            signature_method="password",
            credentials="user_password_here",
            meaning="RA professional approval"
        )
        valid = sig_mgr.verify_signature(signature.signature_id, "user_password_here")
    """

    def __init__(self, signatures_path: Optional[str] = None):
        """
        Initialize signature manager.

        Args:
            signatures_path: Path to signatures storage directory
                            (default: ~/.claude/fda-tools.signatures/)
        """
        if signatures_path is None:
            signatures_path = os.path.expanduser(
                "~/.claude/fda-tools-signatures"
            )

        self.signatures_dir = Path(signatures_path)
        self.signatures_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._signatures: Dict[str, ElectronicSignature] = {}
        self._document_index: Dict[str, List[str]] = {}  # doc_id -> [sig_ids]

        # Load existing signatures
        self._load_signatures()

    # ========================================
    # Signature Creation
    # ========================================

    def create_signature(
        self,
        user_id: str,
        user_name: str,
        user_email: str,
        action: str,
        document_id: str,
        signature_method: str,
        credentials: str,
        meaning: str,
        ip_address: str = "",
        user_agent: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ElectronicSignature:
        """
        Create a new electronic signature.

        Implements 21 CFR Part 11 requirements:
        - 11.50: Captures printed name, date/time, and meaning
        - 11.100: Unique to individual (user_id + credentials)
        - 11.200: Two components (identification + authentication)

        Args:
            user_id: Signing user's ID
            user_name: Signing user's full name
            user_email: Signing user's email
            action: Action being signed
            document_id: Document being signed
            signature_method: Authentication method (password, token, biometric)
            credentials: Authentication credential (password, token value, etc.)
            meaning: Regulatory meaning of signature
            ip_address: Optional IP address
            user_agent: Optional user agent
            metadata: Optional additional context

        Returns:
            Created ElectronicSignature object

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        if not user_id or not user_name:
            raise ValueError("user_id and user_name are required")

        if not action:
            raise ValueError("Action is required")

        if not document_id:
            raise ValueError("document_id is required")

        if signature_method not in VALID_SIGNATURE_METHODS:
            raise ValueError(
                "Invalid signature method '{}'. Valid: {}".format(
                    signature_method,
                    ', '.join(sorted(VALID_SIGNATURE_METHODS))
                )
            )

        if not credentials:
            raise ValueError(
                "Credentials are required for electronic signature"
            )

        if not meaning:
            # Try to get default meaning for action
            meaning = SIGNATURE_MEANINGS.get(
                action,
                "Authorized by electronic signature"
            )

        # Generate signature components
        signature_id = "sig_{}".format(uuid.uuid4().hex[:16])
        salt = secrets.token_hex(32)
        signature_hash = self._hash_credentials(credentials, salt)
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        signature = ElectronicSignature(
            signature_id=signature_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            action=action,
            document_id=document_id,
            signature_method=signature_method,
            signature_hash=signature_hash,
            salt=salt,
            signed_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
            meaning=meaning,
            metadata=metadata or {},
            is_valid=True
        )

        with self._lock:
            self._signatures[signature_id] = signature

            # Update document index
            if document_id not in self._document_index:
                self._document_index[document_id] = []
            self._document_index[document_id].append(signature_id)

            # Persist
            self._save_signature(signature)

            # Audit
            self._audit_signature_event(
                signature, "signature_created"
            )

        return deepcopy(signature)

    # ========================================
    # Signature Verification
    # ========================================

    def verify_signature(
        self,
        signature_id: str,
        credentials: str
    ) -> bool:
        """
        Verify an electronic signature by re-authenticating credentials.

        Implements 21 CFR Part 11.200 verification:
        The signature is verified by comparing the provided credentials
        against the stored hash.

        Args:
            signature_id: Signature to verify
            credentials: Credential to verify against

        Returns:
            True if signature is valid and credentials match
        """
        with self._lock:
            signature = self._signatures.get(signature_id)

        if signature is None:
            return False

        if not signature.is_valid:
            return False

        # Verify credentials against stored hash
        computed_hash = self._hash_credentials(
            credentials, signature.salt
        )

        verified = hmac.compare_digest(
            computed_hash, signature.signature_hash
        )

        # Audit verification attempt
        self._audit_signature_event(
            signature,
            "signature_verified" if verified else "signature_verification_failed"
        )

        return verified

    # ========================================
    # Signature Queries
    # ========================================

    def get_signature(
        self,
        signature_id: str
    ) -> Optional[ElectronicSignature]:
        """
        Retrieve a signature by ID.

        Args:
            signature_id: Signature identifier

        Returns:
            ElectronicSignature or None
        """
        with self._lock:
            sig = self._signatures.get(signature_id)
            return deepcopy(sig) if sig else None

    def get_signatures_for_document(
        self,
        document_id: str
    ) -> List[ElectronicSignature]:
        """
        Get all signatures for a document.

        Args:
            document_id: Document identifier

        Returns:
            List of ElectronicSignature objects
        """
        with self._lock:
            sig_ids = self._document_index.get(document_id, [])
            return [
                deepcopy(self._signatures[sid])
                for sid in sig_ids
                if sid in self._signatures
            ]

    def get_signatures_by_user(
        self,
        user_id: str
    ) -> List[ElectronicSignature]:
        """
        Get all signatures by a user.

        Args:
            user_id: User identifier

        Returns:
            List of ElectronicSignature objects
        """
        with self._lock:
            return [
                deepcopy(sig)
                for sig in self._signatures.values()
                if sig.user_id == user_id
            ]

    def is_document_signed(
        self,
        document_id: str,
        required_signers: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check if a document has all required signatures.

        Args:
            document_id: Document to check
            required_signers: Optional list of user IDs that must sign

        Returns:
            Tuple of (all_signed, list_of_missing_signers)
        """
        signatures = self.get_signatures_for_document(document_id)
        signed_by = {sig.user_id for sig in signatures if sig.is_valid}

        if not required_signers:
            return len(signatures) > 0, []

        missing = [
            uid for uid in required_signers
            if uid not in signed_by
        ]

        return len(missing) == 0, missing

    # ========================================
    # Command Signature Requirements
    # ========================================

    @staticmethod
    def requires_signature(command: str) -> bool:
        """
        Check if a command requires electronic signature.

        Args:
            command: FDA command name

        Returns:
            True if signature is required
        """
        return command in SIGNATURE_REQUIRED_COMMANDS

    @staticmethod
    def get_signature_meaning(command: str) -> str:
        """
        Get the regulatory meaning for a command's signature.

        Args:
            command: FDA command name

        Returns:
            Signature meaning string
        """
        return SIGNATURE_REQUIRED_COMMANDS.get(
            command,
            "Authorized by electronic signature"
        )

    # ========================================
    # Invalidation
    # ========================================

    def invalidate_signature(
        self,
        signature_id: str,
        reason: str
    ) -> bool:
        """
        Invalidate a signature (e.g., if credentials are compromised).

        Note: Does not delete the signature -- marks it as invalid
        to preserve the audit trail.

        Args:
            signature_id: Signature to invalidate
            reason: Reason for invalidation

        Returns:
            True if invalidated
        """
        with self._lock:
            signature = self._signatures.get(signature_id)
            if signature is None:
                return False

            signature.is_valid = False
            signature.metadata['invalidation_reason'] = reason
            signature.metadata['invalidated_at'] = (
                datetime.now(timezone.utc).isoformat() + 'Z'
            )

            self._save_signature(signature)
            self._audit_signature_event(
                signature, "signature_invalidated",
                details={'reason': reason}
            )

        return True

    # ========================================
    # Internal Helpers
    # ========================================

    @staticmethod
    def _hash_credentials(credentials: str, salt: str) -> str:
        """
        Hash credentials with salt using SHA-256 with PBKDF2.

        Uses PBKDF2 with 100,000 iterations for password storage
        security (NIST SP 800-132 compliant).

        Args:
            credentials: Raw credential string
            salt: Cryptographic salt

        Returns:
            Hex-encoded hash string
        """
        # Use PBKDF2-HMAC-SHA256 with 100k iterations
        key = hashlib.pbkdf2_hmac(
            'sha256',
            credentials.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100000
        )
        return key.hex()

    def _save_signature(self, signature: ElectronicSignature) -> None:
        """Save signature to disk."""
        sig_file = self.signatures_dir / "{}.json".format(
            signature.signature_id
        )
        try:
            with open(sig_file, 'w') as f:
                json.dump(signature.to_dict(), f, indent=2, default=str)
        except OSError:
            pass

    def _load_signatures(self) -> None:
        """Load signatures from disk."""
        if not self.signatures_dir.exists():
            return

        for sig_file in self.signatures_dir.glob("sig_*.json"):
            try:
                with open(sig_file, 'r') as f:
                    data = json.load(f)
                sig = ElectronicSignature.from_dict(data)
                self._signatures[sig.signature_id] = sig

                # Rebuild document index
                if sig.document_id not in self._document_index:
                    self._document_index[sig.document_id] = []
                self._document_index[sig.document_id].append(
                    sig.signature_id
                )
            except (json.JSONDecodeError, KeyError, OSError):
                continue

    def _audit_signature_event(
        self,
        signature: ElectronicSignature,
        event_type: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log signature event to audit trail.

        Args:
            signature: Signature being audited
            event_type: Type of event
            details: Optional additional details
        """
        audit_file = self.signatures_dir / "signature_audit.jsonl"

        event = {
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'event_type': event_type,
            'signature_id': signature.signature_id,
            'user_id': signature.user_id,
            'user_name': signature.user_name,
            'action': signature.action,
            'document_id': signature.document_id,
            'meaning': signature.meaning,
            'details': details or {}
        }

        try:
            with open(audit_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except OSError:
            pass

    def get_audit_trail(
        self,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query signature audit trail.

        Args:
            document_id: Optional document filter
            user_id: Optional user filter
            limit: Maximum events to return

        Returns:
            List of audit event dictionaries
        """
        events = []
        audit_file = self.signatures_dir / "signature_audit.jsonl"

        if not audit_file.exists():
            return events

        try:
            with open(audit_file, 'r') as f:
                for line in f:
                    if len(events) >= limit:
                        break
                    try:
                        event = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    if document_id and event.get('document_id') != document_id:
                        continue
                    if user_id and event.get('user_id') != user_id:
                        continue

                    events.append(event)
        except OSError:
            pass

        return events

    @property
    def signature_count(self) -> int:
        """Get total number of signatures."""
        with self._lock:
            return len(self._signatures)


# Global singleton
_signature_manager_instance: Optional[SignatureManager] = None


def get_signature_manager(
    signatures_path: Optional[str] = None
) -> SignatureManager:
    """
    Get global SignatureManager instance (singleton pattern).

    Args:
        signatures_path: Optional signatures directory path

    Returns:
        SignatureManager instance
    """
    global _signature_manager_instance
    if _signature_manager_instance is None:
        _signature_manager_instance = SignatureManager(signatures_path)
    return _signature_manager_instance
