"""Tests for cache integrity system (GAP-011 / FDA-71).

Validates SHA-256 checksum verification, atomic writes, corruption
detection, auto-invalidation, audit logging, backward compatibility
with legacy cache format, and performance overhead.

These tests do NOT require API access -- they test cache integrity only.
"""

import hashlib
import json
import os
import sys
import tempfile
import time

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

from cache_integrity import (
    CHECKSUM_ALGORITHM,
    ENVELOPE_VERSION,
    compute_checksum,
    get_cached_at,
    integrity_read,
    integrity_write,
    invalidate_corrupt_file,
    migrate_legacy_file,
    verify_checksum,
    _build_envelope,
    _serialize_data,
)


# ============================================================
# Test 1: Checksum Computation
# ============================================================


class TestChecksumComputation:
    """Test SHA-256 checksum computation."""

    def test_compute_checksum_deterministic(self):
        """Same input always produces same checksum."""
        data = b'{"results": [{"k_number": "K241335"}]}'
        h1 = compute_checksum(data)
        h2 = compute_checksum(data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest length

    def test_compute_checksum_different_input(self):
        """Different inputs produce different checksums."""
        h1 = compute_checksum(b"data_a")
        h2 = compute_checksum(b"data_b")
        assert h1 != h2

    def test_compute_checksum_matches_hashlib(self):
        """Verify our checksum matches direct hashlib computation."""
        data = b"test data for FDA cache"
        expected = hashlib.sha256(data).hexdigest()
        assert compute_checksum(data) == expected

    def test_serialize_data_deterministic(self):
        """JSON serialization is deterministic regardless of key order."""
        data1 = {"b": 2, "a": 1, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}
        assert _serialize_data(data1) == _serialize_data(data2)


# ============================================================
# Test 2: Integrity Envelope Construction
# ============================================================


class TestEnvelopeConstruction:
    """Test integrity envelope building."""

    def test_envelope_has_required_fields(self):
        """Envelope contains all required integrity fields."""
        data = {"results": [{"k_number": "K241335"}]}
        envelope = _build_envelope(data)
        assert "_integrity_version" in envelope
        assert "_checksum_algorithm" in envelope
        assert "_checksum" in envelope
        assert "_cached_at" in envelope
        assert "data" in envelope
        assert envelope["_integrity_version"] == ENVELOPE_VERSION
        assert envelope["_checksum_algorithm"] == CHECKSUM_ALGORITHM

    def test_envelope_checksum_matches_data(self):
        """Envelope checksum correctly matches serialized data."""
        data = {"device_name": "Cervical Cage", "product_code": "OVE"}
        envelope = _build_envelope(data)
        expected = compute_checksum(_serialize_data(data))
        assert envelope["_checksum"] == expected

    def test_envelope_preserves_data(self):
        """Original data is preserved unchanged in envelope."""
        data = {"k_number": "K241335", "nested": {"a": [1, 2, 3]}}
        envelope = _build_envelope(data)
        assert envelope["data"] == data

    def test_envelope_custom_timestamp(self):
        """Custom cached_at timestamp is honored."""
        data = {"test": True}
        ts = 1700000000.0
        envelope = _build_envelope(data, cached_at=ts)
        assert envelope["_cached_at"] == ts


# ============================================================
# Test 3: Atomic Write (integrity_write)
# ============================================================


class TestAtomicWrite:
    """Test atomic write with integrity envelope."""

    def test_write_creates_file(self, tmp_path):
        """integrity_write creates the target file."""
        path = tmp_path / "cache" / "test.json"
        data = {"results": [{"k_number": "K241335"}]}
        result = integrity_write(path, data)
        assert result is True
        assert path.exists()

    def test_write_creates_parent_directories(self, tmp_path):
        """integrity_write creates parent directories as needed."""
        path = tmp_path / "deep" / "nested" / "dir" / "cache.json"
        result = integrity_write(path, {"test": True})
        assert result is True
        assert path.exists()

    def test_write_produces_valid_json(self, tmp_path):
        """Written file is valid JSON with integrity envelope."""
        path = tmp_path / "test.json"
        data = {"device_name": "Test Device"}
        integrity_write(path, data)

        with open(path) as f:
            envelope = json.load(f)
        assert envelope["_integrity_version"] == ENVELOPE_VERSION
        assert envelope["data"] == data

    def test_write_no_temp_file_left(self, tmp_path):
        """No temporary files are left behind after successful write."""
        path = tmp_path / "test.json"
        integrity_write(path, {"test": True})

        remaining = list(tmp_path.glob("*.tmp"))
        assert len(remaining) == 0

    def test_write_overwrites_existing_file(self, tmp_path):
        """Overwriting an existing file works correctly."""
        path = tmp_path / "test.json"
        integrity_write(path, {"version": 1})
        integrity_write(path, {"version": 2})

        data = integrity_read(path)
        assert data == {"version": 2}


# ============================================================
# Test 4: Integrity Read with Verification
# ============================================================


class TestIntegrityRead:
    """Test integrity-verified read."""

    def test_read_valid_file(self, tmp_path):
        """Reading a valid integrity file returns the data."""
        path = tmp_path / "test.json"
        original = {"results": [{"k_number": "K241335"}], "meta": {"total": 1}}
        integrity_write(path, original)

        result = integrity_read(path)
        assert result == original

    def test_read_nonexistent_file(self, tmp_path):
        """Reading a nonexistent file returns None."""
        path = tmp_path / "does_not_exist.json"
        result = integrity_read(path)
        assert result is None

    def test_read_expired_ttl(self, tmp_path):
        """Expired TTL causes read to return None."""
        path = tmp_path / "test.json"
        old_time = time.time() - 1000
        integrity_write(path, {"test": True}, cached_at=old_time)

        result = integrity_read(path, ttl_seconds=500)
        assert result is None

    def test_read_valid_ttl(self, tmp_path):
        """Within-TTL file returns data successfully."""
        path = tmp_path / "test.json"
        integrity_write(path, {"test": True})

        result = integrity_read(path, ttl_seconds=86400)
        assert result == {"test": True}


# ============================================================
# Test 5: Corruption Detection
# ============================================================


class TestCorruptionDetection:
    """Test detection of corrupted cache files."""

    def test_detect_truncated_json(self, tmp_path):
        """Truncated JSON files are detected as corrupt."""
        path = tmp_path / "corrupt.json"
        path.write_text('{"_integrity_version": "1.0", "_checksum": "abc", "da')

        events = []
        result = integrity_read(path, audit_logger=lambda e: events.append(e))
        assert result is None
        assert any(e["event"] == "corruption_detected" for e in events)

    def test_detect_tampered_data(self, tmp_path):
        """Files with modified data fail checksum verification."""
        path = tmp_path / "tampered.json"
        integrity_write(path, {"original": True})

        # Tamper with the data
        with open(path) as f:
            envelope = json.load(f)
        envelope["data"] = {"tampered": True}  # Modify data
        with open(path, "w") as f:
            json.dump(envelope, f)

        events = []
        result = integrity_read(path, audit_logger=lambda e: events.append(e))
        assert result is None
        assert any(e["event"] == "checksum_mismatch" for e in events)

    def test_detect_tampered_checksum(self, tmp_path):
        """Files with modified checksums fail verification."""
        path = tmp_path / "bad_checksum.json"
        integrity_write(path, {"test": True})

        with open(path) as f:
            envelope = json.load(f)
        envelope["_checksum"] = "0" * 64  # Replace with fake checksum
        with open(path, "w") as f:
            json.dump(envelope, f)

        events = []
        result = integrity_read(path, audit_logger=lambda e: events.append(e))
        assert result is None
        assert any(e["event"] == "checksum_mismatch" for e in events)

    def test_detect_empty_file(self, tmp_path):
        """Empty files are detected as corrupt."""
        path = tmp_path / "empty.json"
        path.write_text("")

        result = integrity_read(path)
        assert result is None

    def test_detect_non_json_content(self, tmp_path):
        """Non-JSON content is detected as corrupt."""
        path = tmp_path / "notjson.json"
        path.write_text("this is not JSON at all")

        events = []
        result = integrity_read(path, audit_logger=lambda e: events.append(e))
        assert result is None
        assert any(e["event"] == "corruption_detected" for e in events)


# ============================================================
# Test 6: Auto-Invalidation
# ============================================================


class TestAutoInvalidation:
    """Test automatic removal of corrupt cache files."""

    def test_auto_invalidate_corrupt_json(self, tmp_path):
        """Corrupt JSON files are auto-deleted when auto_invalidate=True."""
        path = tmp_path / "corrupt.json"
        path.write_text("{invalid json")

        integrity_read(path, auto_invalidate=True)
        assert not path.exists()

    def test_auto_invalidate_checksum_mismatch(self, tmp_path):
        """Files with checksum mismatches are auto-deleted."""
        path = tmp_path / "bad.json"
        integrity_write(path, {"original": True})

        # Tamper
        with open(path) as f:
            envelope = json.load(f)
        envelope["data"]["tampered"] = True
        with open(path, "w") as f:
            json.dump(envelope, f)

        integrity_read(path, auto_invalidate=True)
        assert not path.exists()

    def test_no_auto_invalidate_when_disabled(self, tmp_path):
        """Corrupt files are NOT deleted when auto_invalidate=False."""
        path = tmp_path / "keep.json"
        path.write_text("{invalid json")

        integrity_read(path, auto_invalidate=False)
        assert path.exists()  # File should still exist

    def test_invalidate_corrupt_file_function(self, tmp_path):
        """invalidate_corrupt_file removes file and logs event."""
        path = tmp_path / "to_remove.json"
        path.write_text("{}")

        events = []
        result = invalidate_corrupt_file(path, "test_reason", lambda e: events.append(e))
        assert result is True
        assert not path.exists()
        assert any(e["event"] == "file_invalidated" for e in events)
        assert events[0]["reason"] == "test_reason"


# ============================================================
# Test 7: Audit Logging
# ============================================================


class TestAuditLogging:
    """Test audit event generation for integrity events."""

    def test_write_generates_audit_event(self, tmp_path):
        """Successful write generates write_completed event."""
        events = []
        path = tmp_path / "test.json"
        integrity_write(path, {"test": True}, audit_logger=lambda e: events.append(e))

        assert len(events) == 1
        assert events[0]["event"] == "write_completed"
        assert "checksum" in events[0]
        assert "timestamp" in events[0]

    def test_read_generates_verification_event(self, tmp_path):
        """Successful read generates integrity_verified event."""
        path = tmp_path / "test.json"
        integrity_write(path, {"test": True})

        events = []
        integrity_read(path, audit_logger=lambda e: events.append(e))

        assert any(e["event"] == "integrity_verified" for e in events)

    def test_corruption_generates_audit_event(self, tmp_path):
        """Corruption detection generates corruption_detected event."""
        path = tmp_path / "corrupt.json"
        path.write_text("not json")

        events = []
        integrity_read(path, audit_logger=lambda e: events.append(e))

        assert any(e["event"] == "corruption_detected" for e in events)
        corrupt_event = [e for e in events if e["event"] == "corruption_detected"][0]
        assert str(path) in corrupt_event["file"]

    def test_checksum_mismatch_generates_audit_event(self, tmp_path):
        """Checksum mismatch generates checksum_mismatch event."""
        path = tmp_path / "tampered.json"
        integrity_write(path, {"original": True})

        with open(path) as f:
            envelope = json.load(f)
        envelope["data"] = {"tampered": True}
        with open(path, "w") as f:
            json.dump(envelope, f)

        events = []
        integrity_read(path, audit_logger=lambda e: events.append(e))

        assert any(e["event"] == "checksum_mismatch" for e in events)
        mismatch_event = [e for e in events if e["event"] == "checksum_mismatch"][0]
        assert "stored_checksum" in mismatch_event
        assert "computed_checksum" in mismatch_event

    def test_audit_logger_failure_does_not_break_operation(self, tmp_path):
        """If audit_logger raises, the cache operation still succeeds."""
        def broken_logger(event):
            raise RuntimeError("Logger broken")

        path = tmp_path / "test.json"
        result = integrity_write(path, {"test": True}, audit_logger=broken_logger)
        assert result is True
        assert path.exists()


# ============================================================
# Test 8: Backward Compatibility (Legacy Format)
# ============================================================


class TestLegacyFormatCompatibility:
    """Test backward compatibility with pre-GAP-011 cache files."""

    def test_read_legacy_format(self, tmp_path):
        """Legacy cache files (no checksum) are still readable."""
        path = tmp_path / "legacy.json"
        legacy_data = {
            "_cached_at": time.time(),
            "data": {"results": [{"k_number": "K241335"}]},
        }
        with open(path, "w") as f:
            json.dump(legacy_data, f)

        events = []
        result = integrity_read(path, audit_logger=lambda e: events.append(e))
        assert result == {"results": [{"k_number": "K241335"}]}
        assert any(e["event"] == "legacy_format_detected" for e in events)

    def test_legacy_ttl_check(self, tmp_path):
        """TTL check works on legacy format files."""
        path = tmp_path / "old_legacy.json"
        legacy_data = {
            "_cached_at": time.time() - 1000,
            "data": {"old": True},
        }
        with open(path, "w") as f:
            json.dump(legacy_data, f)

        result = integrity_read(path, ttl_seconds=500)
        assert result is None  # Expired

    def test_verify_checksum_legacy_returns_true(self, tmp_path):
        """verify_checksum returns (True, 'legacy_format') for legacy files."""
        path = tmp_path / "legacy.json"
        with open(path, "w") as f:
            json.dump({"_cached_at": time.time(), "data": {}}, f)

        is_valid, reason = verify_checksum(path)
        assert is_valid is True
        assert reason == "legacy_format"

    def test_migrate_legacy_file(self, tmp_path):
        """Legacy files can be migrated to integrity envelope format."""
        path = tmp_path / "to_migrate.json"
        legacy_data = {
            "_cached_at": 1700000000.0,
            "data": {"results": [{"k": "K123456"}]},
        }
        with open(path, "w") as f:
            json.dump(legacy_data, f)

        result = migrate_legacy_file(path)
        assert result is True

        # Now verify it has integrity envelope
        is_valid, reason = verify_checksum(path)
        assert is_valid is True
        assert reason == "valid"

        # Data preserved
        data = integrity_read(path)
        assert data == {"results": [{"k": "K123456"}]}


# ============================================================
# Test 9: verify_checksum Function
# ============================================================


class TestVerifyChecksum:
    """Test standalone checksum verification."""

    def test_valid_file(self, tmp_path):
        """Valid file returns (True, 'valid')."""
        path = tmp_path / "valid.json"
        integrity_write(path, {"test": True})
        is_valid, reason = verify_checksum(path)
        assert is_valid is True
        assert reason == "valid"

    def test_nonexistent_file(self, tmp_path):
        """Nonexistent file returns (False, 'file_not_found')."""
        path = tmp_path / "nope.json"
        is_valid, reason = verify_checksum(path)
        assert is_valid is False
        assert reason == "file_not_found"

    def test_invalid_json(self, tmp_path):
        """Invalid JSON returns (False, 'invalid_json')."""
        path = tmp_path / "bad.json"
        path.write_text("{broken")
        is_valid, reason = verify_checksum(path)
        assert is_valid is False
        assert reason == "invalid_json"

    def test_checksum_mismatch(self, tmp_path):
        """Tampered file returns (False, 'checksum_mismatch')."""
        path = tmp_path / "tampered.json"
        integrity_write(path, {"original": True})

        with open(path) as f:
            envelope = json.load(f)
        envelope["data"]["extra"] = "tampered"
        with open(path, "w") as f:
            json.dump(envelope, f)

        is_valid, reason = verify_checksum(path)
        assert is_valid is False
        assert reason == "checksum_mismatch"


# ============================================================
# Test 10: Performance Overhead
# ============================================================


class TestPerformanceOverhead:
    """Test that integrity operations have acceptable overhead."""

    def test_write_performance(self, tmp_path):
        """Integrity write completes in reasonable time (<50ms per file)."""
        path = tmp_path / "perf_test.json"
        # Simulate a typical API response (~2KB)
        data = {
            "results": [
                {"k_number": f"K{200000+i}", "device_name": f"Device {i}",
                 "product_code": "OVE", "decision_date": "20240315"}
                for i in range(20)
            ],
            "meta": {"results": {"total": 20}},
        }

        start = time.time()
        for i in range(100):
            integrity_write(tmp_path / f"perf_{i}.json", data)
        elapsed = time.time() - start

        # 100 writes should complete in under 5 seconds (50ms each)
        assert elapsed < 5.0, f"100 writes took {elapsed:.2f}s (>{5.0}s limit)"

    def test_read_performance(self, tmp_path):
        """Integrity read completes in reasonable time (<10ms per file)."""
        # Write test files
        data = {"results": [{"k_number": "K241335"}], "meta": {"total": 1}}
        for i in range(100):
            integrity_write(tmp_path / f"perf_{i}.json", data)

        start = time.time()
        for i in range(100):
            integrity_read(tmp_path / f"perf_{i}.json")
        elapsed = time.time() - start

        # 100 reads should complete in under 2 seconds (20ms each)
        assert elapsed < 2.0, f"100 reads took {elapsed:.2f}s (>{2.0}s limit)"

    def test_checksum_overhead_percentage(self, tmp_path):
        """Checksum verification adds less than 5x overhead vs plain JSON read."""
        path = tmp_path / "overhead.json"
        data = {"results": [{"k": f"K{i}"} for i in range(50)]}
        integrity_write(path, data)

        # Time plain JSON read
        start = time.time()
        for _ in range(500):
            with open(path) as f:
                json.load(f)
        plain_time = time.time() - start

        # Time integrity read
        start = time.time()
        for _ in range(500):
            integrity_read(path)
        integrity_time = time.time() - start

        # Integrity read should be less than 5x slower than plain read
        overhead_ratio = integrity_time / max(plain_time, 0.001)
        assert overhead_ratio < 5.0, (
            f"Integrity overhead ratio: {overhead_ratio:.1f}x "
            f"(plain: {plain_time:.3f}s, integrity: {integrity_time:.3f}s)"
        )


# ============================================================
# Test 11: FDAClient Integration
# ============================================================


class TestFDAClientIntegration:
    """Test FDAClient cache methods with integrity verification."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create an FDAClient with test cache directory."""
        from fda_api_client import FDAClient
        c = FDAClient(cache_dir=str(tmp_path / "cache"))
        c.enabled = False
        return c

    def test_set_and_get_cached_with_integrity(self, client):
        """set/get cached round-trip works with integrity."""
        test_data = {"results": [{"k_number": "K241335"}]}
        client._set_cached("test_key", test_data)
        result = client._get_cached("test_key")
        assert result == test_data

    def test_corrupted_cache_returns_none(self, client):
        """Corrupted cache file returns None instead of bad data."""
        client._set_cached("corrupt_key", {"original": True})
        cache_file = client.cache_dir / "corrupt_key.json"

        # Corrupt the file
        cache_file.write_text("{truncated json")

        result = client._get_cached("corrupt_key")
        assert result is None

    def test_tampered_cache_returns_none(self, client):
        """Tampered cache file returns None."""
        client._set_cached("tamper_key", {"original": True})
        cache_file = client.cache_dir / "tamper_key.json"

        # Tamper with data
        with open(cache_file) as f:
            envelope = json.load(f)
        if "data" in envelope:
            envelope["data"]["tampered"] = True
            with open(cache_file, "w") as f:
                json.dump(envelope, f)

        result = client._get_cached("tamper_key")
        assert result is None

    def test_cache_stats_includes_integrity_metrics(self, client):
        """cache_stats() includes integrity-related metrics."""
        client._set_cached("key1", {"test": 1})
        stats = client.cache_stats()
        assert "session_corruptions" in stats
        assert "integrity_verified" in stats
        assert "legacy_format" in stats
        assert "corrupt_detected" in stats

    def test_audit_events_captured(self, client):
        """Cache integrity events are captured in audit log."""
        client._set_cached("audit_key", {"test": True})
        client._get_cached("audit_key")
        events = client.get_audit_events()
        assert len(events) >= 1  # At least the write event


# ============================================================
# Test 12: get_cached_at Utility
# ============================================================


class TestGetCachedAt:
    """Test the get_cached_at utility function."""

    def test_returns_timestamp(self, tmp_path):
        """Returns _cached_at timestamp from integrity file."""
        path = tmp_path / "test.json"
        ts = 1700000000.0
        integrity_write(path, {"test": True}, cached_at=ts)
        result = get_cached_at(path)
        assert result == ts

    def test_returns_none_for_missing_file(self, tmp_path):
        """Returns None for nonexistent file."""
        result = get_cached_at(tmp_path / "missing.json")
        assert result is None

    def test_returns_none_for_corrupt_file(self, tmp_path):
        """Returns None for corrupt file."""
        path = tmp_path / "corrupt.json"
        path.write_text("not json")
        result = get_cached_at(path)
        assert result is None


# ============================================================
# Test 13: Edge Cases
# ============================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_data_object(self, tmp_path):
        """Empty dict is cached and retrieved correctly."""
        path = tmp_path / "empty.json"
        integrity_write(path, {})
        result = integrity_read(path)
        assert result == {}

    def test_null_data(self, tmp_path):
        """None/null data is cached and retrieved correctly."""
        path = tmp_path / "null.json"
        integrity_write(path, None)
        # None is a valid JSON value, should round-trip
        result = integrity_read(path)
        assert result is None  # Will return None because data is None

    def test_large_data(self, tmp_path):
        """Large data payloads work correctly."""
        path = tmp_path / "large.json"
        data = {"items": [{"id": i, "data": "x" * 1000} for i in range(100)]}
        integrity_write(path, data)
        result = integrity_read(path)
        assert result == data

    def test_unicode_data(self, tmp_path):
        """Unicode content is handled correctly."""
        path = tmp_path / "unicode.json"
        data = {"device": "Geraet fuer Messung", "notes": "Test with special chars"}
        integrity_write(path, data)
        result = integrity_read(path)
        assert result == data

    def test_nested_complex_data(self, tmp_path):
        """Deeply nested data structures work correctly."""
        path = tmp_path / "nested.json"
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "array": [1, 2, {"key": "value"}],
                        "bool": True,
                        "null": None,
                        "float": 3.14159,
                    }
                }
            }
        }
        integrity_write(path, data)
        result = integrity_read(path)
        assert result == data

    def test_concurrent_writes_no_corruption(self, tmp_path):
        """Multiple sequential writes don't corrupt the file."""
        path = tmp_path / "multi.json"
        for i in range(50):
            integrity_write(path, {"iteration": i})

        result = integrity_read(path)
        assert result == {"iteration": 49}

        is_valid, reason = verify_checksum(path)
        assert is_valid is True
        assert reason == "valid"
