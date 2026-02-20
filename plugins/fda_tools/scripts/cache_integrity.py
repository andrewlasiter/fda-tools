#!/usr/bin/env python3
"""
Cache Integrity Module -- SHA-256 Checksum Verification and Atomic Writes.

Provides integrity verification for FDA cache files per GAP-011 (FDA-71).
Implements 21 CFR Part 11-aligned electronic record integrity controls:

  - SHA-256 checksum embedded in each cache file envelope
  - Checksum verification on every cache read
  - Atomic write (temp file + os.replace) to prevent partial corruption
  - Audit logging of all integrity events (corruption, invalidation, recovery)

Usage:
    from cache_integrity import (
        integrity_write, integrity_read, verify_checksum,
        compute_checksum, invalidate_corrupt_file
    )

    # Write with integrity envelope
    integrity_write(path, data, audit_logger=logger_fn)

    # Read with integrity verification
    data = integrity_read(path, audit_logger=logger_fn)

    # Verify a file's integrity without loading data
    is_valid = verify_checksum(path)
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# Module-level logger for cache integrity events
_logger = logging.getLogger("fda.cache_integrity")

# Integrity envelope version -- bump if envelope schema changes
ENVELOPE_VERSION = "1.0"

# Checksum algorithm identifier stored in envelope for forward compatibility
CHECKSUM_ALGORITHM = "sha256"


def compute_checksum(data_bytes: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes.

    Args:
        data_bytes: The bytes to hash.

    Returns:
        Lowercase hex string of the SHA-256 digest.
    """
    return hashlib.sha256(data_bytes).hexdigest()


def _serialize_data(data: Any) -> bytes:
    """Deterministically serialize data to bytes for checksum computation.

    Uses sorted keys and no extra whitespace to produce a canonical form.
    This ensures the same logical data always produces the same checksum.

    Args:
        data: JSON-serializable data.

    Returns:
        UTF-8 encoded bytes of the canonical JSON representation.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _build_envelope(data: Any, cached_at: Optional[float] = None) -> Dict:
    """Build an integrity envelope wrapping the cached data.

    The envelope contains:
      - _integrity_version: Envelope schema version
      - _checksum_algorithm: Hash algorithm used
      - _checksum: SHA-256 of the canonical serialized data
      - _cached_at: Unix timestamp of cache write
      - data: The actual cached payload

    Args:
        data: The data to cache.
        cached_at: Optional timestamp override. Defaults to time.time().

    Returns:
        Envelope dictionary ready for JSON serialization.
    """
    data_bytes = _serialize_data(data)
    checksum = compute_checksum(data_bytes)

    return {
        "_integrity_version": ENVELOPE_VERSION,
        "_checksum_algorithm": CHECKSUM_ALGORITHM,
        "_checksum": checksum,
        "_cached_at": cached_at or time.time(),
        "data": data,
    }


def _log_event(
    event_type: str,
    file_path: str,
    details: Optional[Dict] = None,
    audit_logger: Optional[Callable] = None,
) -> None:
    """Log a cache integrity event.

    Emits to both the Python logger and an optional audit callback.

    Args:
        event_type: One of 'corruption_detected', 'checksum_mismatch',
                    'file_invalidated', 'integrity_verified', 'write_completed',
                    'legacy_format_detected'.
        file_path: Absolute path to the cache file.
        details: Optional additional context.
        audit_logger: Optional callable(event_dict) for structured audit logging.
    """
    event = {
        "event": event_type,
        "file": str(file_path),
        "timestamp": time.time(),
    }
    if details:
        event.update(details)

    # Python logging
    if event_type in ("corruption_detected", "checksum_mismatch"):
        _logger.warning("Cache integrity: %s -- %s", event_type, file_path)
    elif event_type == "file_invalidated":
        _logger.info("Cache integrity: invalidated corrupt file -- %s", file_path)
    else:
        _logger.debug("Cache integrity: %s -- %s", event_type, file_path)

    # Structured audit callback
    if audit_logger:
        try:
            audit_logger(event)
        except Exception:
            pass  # Audit logging failures must not break cache operations


def integrity_write(
    file_path,
    data: Any,
    cached_at: Optional[float] = None,
    audit_logger: Optional[Callable] = None,
) -> bool:
    """Write data to a cache file with integrity envelope and atomic write.

    Process:
      1. Build integrity envelope with SHA-256 checksum
      2. Serialize to JSON
      3. Write to a temporary file in the same directory
      4. Atomically replace the target file (os.replace)

    The atomic write ensures that readers will see either the old complete
    file or the new complete file, never a partial/corrupt write.

    Args:
        file_path: Target cache file path (str or Path).
        data: JSON-serializable data to cache.
        cached_at: Optional timestamp override.
        audit_logger: Optional audit callback.

    Returns:
        True if write succeeded, False on error.
    """
    file_path = Path(file_path)
    envelope = _build_envelope(data, cached_at)

    try:
        # Create temp file in the same directory to ensure same filesystem
        # (required for atomic os.replace)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix=".cache_",
            dir=str(file_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(envelope, f)
                f.flush()
                os.fsync(f.fileno())

            # Atomic replace
            os.replace(tmp_path, str(file_path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        _log_event(
            "write_completed",
            str(file_path),
            {"checksum": envelope["_checksum"]},
            audit_logger,
        )
        return True

    except OSError as e:
        _log_event(
            "write_failed",
            str(file_path),
            {"error": str(e)},
            audit_logger,
        )
        return False


def integrity_read(
    file_path,
    ttl_seconds: Optional[float] = None,
    audit_logger: Optional[Callable] = None,
    auto_invalidate: bool = True,
) -> Optional[Any]:
    """Read and verify a cache file with integrity checking.

    Process:
      1. Read JSON from file
      2. Check for integrity envelope fields
      3. Verify SHA-256 checksum matches data
      4. Optionally check TTL expiration
      5. Return data payload if valid, None if invalid/expired

    For backward compatibility, files without integrity envelopes (legacy
    format) are accepted but logged as 'legacy_format_detected'. This
    allows a graceful migration period.

    Args:
        file_path: Cache file path (str or Path).
        ttl_seconds: Optional TTL in seconds. If provided, checks _cached_at.
        audit_logger: Optional audit callback.
        auto_invalidate: If True, corrupt files are automatically deleted.

    Returns:
        The cached data payload, or None if file is invalid/expired/missing.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            envelope = json.load(f)
    except json.JSONDecodeError as e:
        _log_event(
            "corruption_detected",
            str(file_path),
            {"error": f"Invalid JSON: {e}"},
            audit_logger,
        )
        if auto_invalidate:
            invalidate_corrupt_file(file_path, "invalid_json", audit_logger)
        return None
    except OSError as e:
        _log_event(
            "corruption_detected",
            str(file_path),
            {"error": f"Read error: {e}"},
            audit_logger,
        )
        return None

    # Check for integrity envelope
    if "_checksum" not in envelope or "_integrity_version" not in envelope:
        # Legacy format (pre-GAP-011): accept but log
        _log_event(
            "legacy_format_detected",
            str(file_path),
            audit_logger=audit_logger,
        )

        # TTL check for legacy format
        if ttl_seconds is not None:
            cached_at = envelope.get("_cached_at", 0)
            if time.time() - cached_at > ttl_seconds:
                return None

        return envelope.get("data")

    # Verify checksum
    stored_checksum = envelope.get("_checksum", "")
    data = envelope.get("data")

    data_bytes = _serialize_data(data)
    computed_checksum = compute_checksum(data_bytes)

    if computed_checksum != stored_checksum:
        _log_event(
            "checksum_mismatch",
            str(file_path),
            {
                "stored_checksum": stored_checksum[:16] + "...",
                "computed_checksum": computed_checksum[:16] + "...",
            },
            audit_logger,
        )
        if auto_invalidate:
            invalidate_corrupt_file(file_path, "checksum_mismatch", audit_logger)
        return None

    # TTL check
    if ttl_seconds is not None:
        cached_at = envelope.get("_cached_at", 0)
        if time.time() - cached_at > ttl_seconds:
            return None

    _log_event(
        "integrity_verified",
        str(file_path),
        {"checksum": stored_checksum[:16] + "..."},
        audit_logger,
    )
    return data


def verify_checksum(file_path) -> Tuple[bool, str]:
    """Verify the integrity of a cache file without returning its data.

    Args:
        file_path: Cache file path (str or Path).

    Returns:
        Tuple of (is_valid, reason).
        - (True, "valid") if checksum matches
        - (True, "legacy_format") if no checksum present (pre-GAP-011)
        - (False, reason_string) if verification failed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return False, "file_not_found"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            envelope = json.load(f)
    except json.JSONDecodeError:
        return False, "invalid_json"
    except OSError as e:
        return False, f"read_error: {e}"

    if "_checksum" not in envelope or "_integrity_version" not in envelope:
        return True, "legacy_format"

    stored_checksum = envelope.get("_checksum", "")
    data = envelope.get("data")
    data_bytes = _serialize_data(data)
    computed_checksum = compute_checksum(data_bytes)

    if computed_checksum != stored_checksum:
        return False, "checksum_mismatch"

    return True, "valid"


def invalidate_corrupt_file(
    file_path,
    reason: str = "unknown",
    audit_logger: Optional[Callable] = None,
) -> bool:
    """Remove a corrupt cache file and log the invalidation.

    Args:
        file_path: Path to the corrupt file.
        reason: Reason for invalidation.
        audit_logger: Optional audit callback.

    Returns:
        True if file was removed, False if removal failed.
    """
    file_path = Path(file_path)

    try:
        if file_path.exists():
            file_path.unlink()
            _log_event(
                "file_invalidated",
                str(file_path),
                {"reason": reason},
                audit_logger,
            )
            return True
    except OSError as e:
        _log_event(
            "invalidation_failed",
            str(file_path),
            {"reason": reason, "error": str(e)},
            audit_logger,
        )
    return False


def get_cached_at(file_path) -> Optional[float]:
    """Extract the _cached_at timestamp from a cache file without full verification.

    Useful for TTL checks without the overhead of checksum verification.

    Args:
        file_path: Cache file path.

    Returns:
        Unix timestamp float, or None if file is unreadable.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            envelope = json.load(f)
        return envelope.get("_cached_at")
    except (json.JSONDecodeError, OSError):
        return None


def migrate_legacy_file(
    file_path,
    audit_logger: Optional[Callable] = None,
) -> bool:
    """Migrate a legacy (pre-GAP-011) cache file to the integrity envelope format.

    Reads the existing file, wraps its data in an integrity envelope, and
    atomically rewrites it.

    Args:
        file_path: Path to legacy cache file.
        audit_logger: Optional audit callback.

    Returns:
        True if migration succeeded, False otherwise.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            legacy = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    # Already has integrity envelope
    if "_checksum" in legacy and "_integrity_version" in legacy:
        return True

    data = legacy.get("data", legacy)
    cached_at = legacy.get("_cached_at", time.time())

    return integrity_write(
        file_path, data, cached_at=cached_at, audit_logger=audit_logger
    )
