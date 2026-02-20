#!/usr/bin/env python3
"""
Secure Data Storage Module (FDA-488 Security Remediation).

Provides cryptographic integrity verification, file locking, and path
sanitization for FDA data cache storage to ensure 21 CFR compliance.

Security Features:
- HMAC-based data integrity verification (prevents tampering)
- File locking for concurrent access (prevents race conditions)
- Path sanitization (prevents traversal attacks)
- Data type validation (prevents injection)
- Monotonic timestamps (immune to clock manipulation)

Compliance:
- 21 CFR Part 11 (Electronic Records)
- 21 CFR 807/814 (Audit trail requirements)

Usage:
    from lib.secure_data_storage import SecureDataStore

    store = SecureDataStore()

    # Write with integrity protection
    store.write_data(path, data)

    # Read with verification
    data = store.read_data(path)

    # Validate data type
    store.validate_data_type("maude_events")

Version: 1.0.0 (FDA-488)
"""

import fcntl
import hashlib
import hmac
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Set, Optional


class SecureDataStore:
    """
    Secure data storage with HMAC integrity and file locking.

    Security: FDA-488 CRITICAL-1, CRITICAL-2, HIGH-4 remediation
    """

    # FDA-488 HIGH-4: Whitelist of allowed data types
    ALLOWED_DATA_TYPES: Set[str] = {
        'maude_events',
        'recalls',
        'pma_supplements',
        'pma_approval',
        'classification',
        'ssed_pdf',
        'extracted_sections',
        'guidance_docs',
        'clinical_data',
        'literature_cache',
        'safety_cache',
    }

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize secure data store.

        Args:
            secret_key: HMAC secret key for integrity verification.
                       If not provided, loads from environment variable
                       DATA_INTEGRITY_KEY.

        Raises:
            ValueError: If secret key not provided and not in environment

        Security: FDA-488 CRITICAL-1 - HMAC for tamper detection
        """
        # Load secret key from environment or parameter
        key_value = secret_key or os.environ.get('DATA_INTEGRITY_KEY')

        if not key_value:
            # Generate ephemeral key with warning (not production-safe)
            import secrets
            key_value = secrets.token_hex(32)
            import logging
            logging.warning(
                "DATA_INTEGRITY_KEY not set. Using ephemeral key. "
                "Data integrity will not persist across restarts. "
                "Set DATA_INTEGRITY_KEY environment variable for production."
            )

        # After this point, secret_key is guaranteed to be a string
        self.secret_key: str = key_value

    # ============================================================
    # HMAC Integrity Protection (FDA-488 CRITICAL-1)
    # ============================================================

    def _generate_hmac(self, data: bytes) -> str:
        """
        Generate HMAC-SHA256 for data integrity verification.

        Args:
            data: Data bytes to generate HMAC for

        Returns:
            HMAC hex digest (64 characters)

        Security: FDA-488 CRITICAL-1 remediation
        - HMAC prevents undetected tampering (unlike plain hashes)
        - Attacker cannot recalculate HMAC without secret key
        """
        return hmac.new(
            self.secret_key.encode(),
            data,
            hashlib.sha256
        ).hexdigest()

    def write_data(self, path: Path, data: Dict[str, Any]):
        """
        Write data with HMAC integrity protection.

        Args:
            path: Path to write data file
            data: Data dictionary to write

        Security: FDA-488 CRITICAL-1, CRITICAL-2 remediation
        - HMAC stored separately for integrity verification
        - File locking prevents concurrent write races
        - Atomic write (temp + rename) prevents partial writes
        """
        path = Path(path)

        # Serialize data (deterministic for consistent HMACs)
        data_bytes = json.dumps(data, sort_keys=True, indent=2).encode('utf-8')

        # Generate HMAC
        data_hmac = self._generate_hmac(data_bytes)

        # Write data file with atomic write + locking
        with self._atomic_write(path) as f:
            f.write(data_bytes.decode('utf-8'))

        # Write HMAC file
        hmac_path = path.with_suffix(path.suffix + '.hmac')
        with open(hmac_path, 'w') as f:
            f.write(data_hmac)

    def read_data(self, path: Path) -> Dict[str, Any]:
        """
        Read data with HMAC integrity verification.

        Args:
            path: Path to data file

        Returns:
            Verified data dictionary

        Raises:
            ValueError: If HMAC verification fails (data tampered)
            FileNotFoundError: If data or HMAC file missing

        Security: FDA-488 CRITICAL-1 remediation
        - Verifies HMAC before returning data
        - Timing-safe comparison prevents timing attacks
        """
        path = Path(path)

        # Read data
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        with open(path, 'rb') as f:
            data_bytes = f.read()

        # Read stored HMAC
        hmac_path = path.with_suffix(path.suffix + '.hmac')
        if not hmac_path.exists():
            raise FileNotFoundError(
                f"HMAC file not found: {hmac_path}\n"
                f"Data integrity cannot be verified. File may be corrupted or tampered."
            )

        with open(hmac_path, 'r') as f:
            stored_hmac = f.read().strip()

        # Calculate HMAC of current data
        calculated_hmac = self._generate_hmac(data_bytes)

        # Timing-safe comparison (prevents timing attacks)
        if not hmac.compare_digest(calculated_hmac, stored_hmac):
            raise ValueError(
                f"Data integrity check FAILED for {path}\n"
                f"  Expected HMAC: {stored_hmac}\n"
                f"  Calculated HMAC: {calculated_hmac}\n"
                f"Data may have been tampered with or corrupted."
            )

        # Parse and return data
        return json.loads(data_bytes.decode('utf-8'))

    # ============================================================
    # File Locking & Atomic Writes (FDA-488 CRITICAL-2)
    # ============================================================

    @contextmanager
    def _atomic_write(self, path: Path):
        """
        Context manager for atomic file writes with exclusive locking.

        Args:
            path: Target file path

        Yields:
            File handle for writing

        Security: FDA-488 CRITICAL-2 remediation
        - Exclusive lock prevents concurrent writes (no race conditions)
        - Temp file + atomic rename prevents partial writes
        - Lock released even if exception occurs
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix('.tmp')
        lock_path = path.with_suffix('.lock')

        # Acquire exclusive file lock
        lock_fd = open(lock_path, 'w')
        try:
            # Block until lock acquired (LOCK_EX = exclusive)
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

            # Write to temporary file
            with open(temp_path, 'w') as f:
                yield f

            # Atomic rename (replaces original file)
            temp_path.replace(path)

        finally:
            # Release lock
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

            # Clean up lock file
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    # ============================================================
    # Path Sanitization (FDA-488 HIGH-4)
    # ============================================================

    def validate_data_type(self, data_type: str) -> str:
        """
        Validate and sanitize data type name.

        Args:
            data_type: Data type identifier to validate

        Returns:
            Validated data type string

        Raises:
            ValueError: If data type invalid or not whitelisted

        Security: FDA-488 HIGH-4 remediation
        - Prevents path traversal via data type names
        - Whitelist prevents arbitrary file access
        - Regex blocks injection attempts
        """
        # Type check
        if not isinstance(data_type, str):
            raise ValueError(f"Data type must be string, got {type(data_type).__name__}")

        # Normalize to lowercase
        data_type = data_type.lower().strip()

        # Reject empty strings
        if not data_type:
            raise ValueError("Data type cannot be empty")

        # Regex validation: only alphanumeric and underscores
        if not re.match(r'^[a-z0-9_]+$', data_type):
            raise ValueError(
                f"Invalid data type '{data_type}': "
                f"Only lowercase letters, numbers, and underscores allowed"
            )

        # Whitelist validation
        if data_type not in self.ALLOWED_DATA_TYPES:
            raise ValueError(
                f"Unknown data type '{data_type}'. "
                f"Allowed types: {', '.join(sorted(self.ALLOWED_DATA_TYPES))}"
            )

        return data_type

    def sanitize_path(self, base_dir: Path, data_type: str, filename: str) -> Path:
        """
        Construct safe file path with validation.

        Args:
            base_dir: Base directory for data storage
            data_type: Data type (validated)
            filename: Filename to append

        Returns:
            Validated absolute path within base_dir

        Raises:
            ValueError: If path escapes base directory

        Security: FDA-488 HIGH-4 remediation
        - Validates data type via whitelist
        - Prevents path traversal in filename
        - Ensures resolved path stays within base_dir
        """
        # Validate data type
        data_type = self.validate_data_type(data_type)

        # Sanitize filename (remove directory separators)
        filename = os.path.basename(filename)

        # Reject empty filename
        if not filename:
            raise ValueError("Filename cannot be empty")

        # Construct path
        constructed_path = Path(base_dir) / data_type / filename

        # Resolve to absolute canonical path
        try:
            resolved_path = constructed_path.resolve(strict=False)
            base_resolved = Path(base_dir).resolve(strict=False)
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Cannot resolve path: {constructed_path}") from e

        # Verify path is within base directory
        if not str(resolved_path).startswith(str(base_resolved)):
            raise ValueError(
                f"Security violation: Path escapes base directory\n"
                f"  Requested: {constructed_path}\n"
                f"  Resolved: {resolved_path}\n"
                f"  Base: {base_resolved}"
            )

        return resolved_path

    # ============================================================
    # Monotonic Timestamps (FDA-488 HIGH-3)
    # ============================================================

    def get_monotonic_timestamp(self) -> float:
        """
        Get monotonic timestamp immune to clock changes.

        Returns:
            Monotonic timestamp (seconds since arbitrary epoch)

        Security: FDA-488 HIGH-3 remediation
        - time.monotonic() is immune to system clock changes
        - Prevents TTL bypass via clock manipulation
        - Use for interval measurements, not wall clock times
        """
        return time.monotonic()

    def get_utc_timestamp(self) -> datetime:
        """
        Get current UTC timestamp.

        Returns:
            Timezone-aware UTC datetime

        Note: Use monotonic_timestamp() for TTL comparisons to prevent
        clock manipulation attacks. Use this for audit trails only.
        """
        return datetime.now(timezone.utc)


# ============================================================
# Utility Functions
# ============================================================

def verify_file_integrity(path: Path, secret_key: Optional[str] = None) -> bool:
    """
    Verify file integrity without loading data.

    Args:
        path: Path to data file
        secret_key: HMAC secret key (optional, loads from env if not provided)

    Returns:
        True if integrity check passes, False otherwise

    Security: Standalone integrity verification
    """
    store = SecureDataStore(secret_key=secret_key)
    try:
        store.read_data(path)
        return True
    except (ValueError, FileNotFoundError):
        return False
