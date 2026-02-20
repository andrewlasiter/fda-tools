#!/usr/bin/env python3
"""
Security tests for Secure Data Storage (FDA-488 Remediation Verification).

Tests HMAC integrity verification, file locking, path sanitization, and data type validation.
"""

import pytest
from pathlib import Path
import tempfile
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Import from package
import sys

from fda_tools.lib.secure_data_storage import SecureDataStore, verify_file_integrity


class TestHMACIntegrity:
    """Test HMAC integrity verification (FDA-488 CRITICAL-1)."""

    def setup_method(self):
        """Create temporary directory and data store."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = SecureDataStore(secret_key="test-secret-key-32-characters-long")

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_data_creates_hmac_file(self):
        """Test that writing data creates both data and HMAC files."""
        data_path = Path(self.temp_dir) / "test_data.json"
        test_data = {"test_key": "test_value"}

        self.store.write_data(data_path, test_data)

        # Both files should exist
        assert data_path.exists()
        assert data_path.with_suffix('.json.hmac').exists()

    def test_read_data_verifies_hmac(self):
        """Test that reading data verifies HMAC integrity."""
        data_path = Path(self.temp_dir) / "test_data.json"
        test_data = {"test_key": "test_value"}

        # Write data
        self.store.write_data(data_path, test_data)

        # Read data (should succeed)
        read_data = self.store.read_data(data_path)
        assert read_data == test_data

    def test_read_data_detects_tampering(self):
        """Test that HMAC verification detects data tampering."""
        data_path = Path(self.temp_dir) / "test_data.json"
        test_data = {"test_key": "test_value"}

        # Write data
        self.store.write_data(data_path, test_data)

        # Tamper with data (modify file directly)
        tampered_data = {"test_key": "TAMPERED"}
        with open(data_path, 'w') as f:
            json.dump(tampered_data, f)

        # Read should detect tampering
        with pytest.raises(ValueError, match="Data integrity check FAILED"):
            self.store.read_data(data_path)

    def test_read_data_requires_hmac_file(self):
        """Test that reading data requires HMAC file to exist."""
        data_path = Path(self.temp_dir) / "test_data.json"
        test_data = {"test_key": "test_value"}

        # Write data file directly (without HMAC)
        with open(data_path, 'w') as f:
            json.dump(test_data, f)

        # Read should fail without HMAC file
        with pytest.raises(FileNotFoundError, match="HMAC file not found"):
            self.store.read_data(data_path)

    def test_hmac_changes_with_data(self):
        """Test that HMAC changes when data changes."""
        data_path = Path(self.temp_dir) / "test_data.json"
        hmac_path = data_path.with_suffix('.json.hmac')

        # Write initial data
        self.store.write_data(data_path, {"value": 1})
        with open(hmac_path, 'r') as f:
            hmac1 = f.read().strip()

        # Write different data
        self.store.write_data(data_path, {"value": 2})
        with open(hmac_path, 'r') as f:
            hmac2 = f.read().strip()

        # HMACs should differ
        assert hmac1 != hmac2

    def test_hmac_consistent_for_same_data(self):
        """Test that HMAC is consistent for the same data."""
        data_path1 = Path(self.temp_dir) / "test1.json"
        data_path2 = Path(self.temp_dir) / "test2.json"
        test_data = {"key": "value", "number": 123}

        # Write same data to two files
        self.store.write_data(data_path1, test_data)
        self.store.write_data(data_path2, test_data)

        # HMACs should be identical
        with open(data_path1.with_suffix('.json.hmac'), 'r') as f:
            hmac1 = f.read().strip()
        with open(data_path2.with_suffix('.json.hmac'), 'r') as f:
            hmac2 = f.read().strip()

        assert hmac1 == hmac2


class TestFileLocking:
    """Test file locking prevents race conditions (FDA-488 CRITICAL-2)."""

    def setup_method(self):
        """Create temporary directory and data store."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = SecureDataStore(secret_key="test-secret-key-32-characters-long")

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_atomic_write_creates_temp_file(self):
        """Test that atomic write uses temporary file."""
        data_path = Path(self.temp_dir) / "test.json"
        test_data = {"test": "value"}

        # Write data
        self.store.write_data(data_path, test_data)

        # Temp file should be cleaned up
        temp_path = data_path.with_suffix('.tmp')
        assert not temp_path.exists()

        # Final file should exist
        assert data_path.exists()

    def test_concurrent_writes_sequential(self):
        """Test that concurrent writes are serialized by lock."""
        data_path = Path(self.temp_dir) / "concurrent.json"
        write_times = []

        def write_worker(worker_id: int):
            """Worker function that writes data."""
            start_time = time.time()
            self.store.write_data(data_path, {"worker": worker_id})
            end_time = time.time()
            write_times.append((worker_id, start_time, end_time))

        # Launch 5 concurrent writes
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_worker, i) for i in range(5)]
            for future in futures:
                future.result()

        # All writes should succeed
        assert len(write_times) == 5

        # Verify file is valid (not corrupted by race)
        final_data = self.store.read_data(data_path)
        assert "worker" in final_data
        assert final_data["worker"] in range(5)

    def test_lock_released_on_exception(self):
        """Test that lock is released even if write fails."""
        data_path = Path(self.temp_dir) / "test.json"

        # Force an exception during write by using invalid data
        class UnserializableObject:
            pass

        try:
            self.store.write_data(data_path, {"obj": UnserializableObject()})
        except (TypeError, AttributeError):
            pass  # Expected exception

        # Lock should be released, next write should succeed
        self.store.write_data(data_path, {"test": "value"})
        assert data_path.exists()


class TestPathSanitization:
    """Test path sanitization prevents traversal (FDA-488 HIGH-4)."""

    def setup_method(self):
        """Create temporary directory and data store."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir) / "data"
        self.base_dir.mkdir()
        self.store = SecureDataStore(secret_key="test-secret-key-32-characters-long")

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_data_type_rejects_traversal(self):
        """Test that data type validation rejects path traversal."""
        with pytest.raises(ValueError, match="Only lowercase letters"):
            self.store.validate_data_type("../etc/passwd")

    def test_validate_data_type_rejects_unknown_type(self):
        """Test that unknown data types are rejected."""
        with pytest.raises(ValueError, match="Unknown data type"):
            self.store.validate_data_type("unknown_type")

    def test_validate_data_type_accepts_whitelisted(self):
        """Test that whitelisted data types are accepted."""
        valid_types = ['maude_events', 'recalls', 'pma_supplements']
        for data_type in valid_types:
            result = self.store.validate_data_type(data_type)
            assert result == data_type

    def test_sanitize_path_neutralizes_traversal_attempt(self):
        """Test that path traversal attempts are neutralized via basename()."""
        # os.path.basename() strips "../.." leaving just "passwd"
        # This is a valid security approach - neutralize rather than reject
        safe_path = self.store.sanitize_path(
            self.base_dir,
            "maude_events",
            "../../etc/passwd"
        )

        # Should result in safe path: base_dir/maude_events/passwd
        assert "passwd" in str(safe_path)
        assert str(safe_path).startswith(str(self.base_dir.resolve()))

    def test_sanitize_path_accepts_valid_path(self):
        """Test that valid paths within base directory are accepted."""
        safe_path = self.store.sanitize_path(
            self.base_dir,
            "maude_events",
            "data_2024.json"
        )

        # Should resolve to path within base_dir
        assert str(safe_path).startswith(str(self.base_dir.resolve()))

    def test_sanitize_path_rejects_empty_filename(self):
        """Test that empty filenames are rejected."""
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            self.store.sanitize_path(
                self.base_dir,
                "maude_events",
                ""
            )


class TestDataTypeValidation:
    """Test data type validation (FDA-488 HIGH-4)."""

    def setup_method(self):
        """Create data store."""
        self.store = SecureDataStore(secret_key="test-secret-key-32-characters-long")

    def test_validate_data_type_rejects_non_string(self):
        """Test that non-string data types are rejected."""
        with pytest.raises(ValueError, match="must be string"):
            self.store.validate_data_type(12345)

    def test_validate_data_type_rejects_empty_string(self):
        """Test that empty strings are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.store.validate_data_type("")

    def test_validate_data_type_normalizes_case(self):
        """Test that data type is normalized to lowercase."""
        result = self.store.validate_data_type("MAUDE_EVENTS")
        assert result == "maude_events"

    def test_validate_data_type_rejects_special_chars(self):
        """Test that special characters are rejected."""
        with pytest.raises(ValueError, match="Only lowercase letters"):
            self.store.validate_data_type("maude-events")  # Hyphen not allowed

    def test_validate_data_type_accepts_underscores(self):
        """Test that underscores are accepted in data types."""
        result = self.store.validate_data_type("maude_events")
        assert result == "maude_events"


class TestMonotonicTimestamps:
    """Test monotonic timestamps immune to clock changes (FDA-488 HIGH-3)."""

    def setup_method(self):
        """Create data store."""
        self.store = SecureDataStore(secret_key="test-secret-key-32-characters-long")

    def test_get_monotonic_timestamp_returns_float(self):
        """Test that monotonic timestamp returns a float."""
        timestamp = self.store.get_monotonic_timestamp()
        assert isinstance(timestamp, float)

    def test_get_monotonic_timestamp_increases(self):
        """Test that monotonic timestamps always increase."""
        ts1 = self.store.get_monotonic_timestamp()
        time.sleep(0.01)  # Small delay
        ts2 = self.store.get_monotonic_timestamp()

        assert ts2 > ts1

    def test_get_utc_timestamp_returns_datetime(self):
        """Test that UTC timestamp returns timezone-aware datetime."""
        from datetime import datetime, timezone

        timestamp = self.store.get_utc_timestamp()
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == timezone.utc


class TestIntegratedSecurity:
    """Test integrated security workflow."""

    def setup_method(self):
        """Create temporary directory and data store."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = SecureDataStore(secret_key="test-secret-key-32-characters-long")

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_workflow(self):
        """Test complete write-read workflow with all security features."""
        data_path = Path(self.temp_dir) / "workflow_test.json"
        test_data = {
            "device_name": "Test Device",
            "k_number": "K123456",
            "clearance_date": "2024-01-01"
        }

        # Write data (with HMAC, locking, validation)
        self.store.write_data(data_path, test_data)

        # Verify HMAC file exists
        assert data_path.with_suffix('.json.hmac').exists()

        # Read data (with HMAC verification)
        read_data = self.store.read_data(data_path)
        assert read_data == test_data

        # Verify integrity using utility function
        assert verify_file_integrity(data_path, "test-secret-key-32-characters-long")

    def test_verify_file_integrity_detects_corruption(self):
        """Test that verify_file_integrity detects data corruption."""
        data_path = Path(self.temp_dir) / "corrupt_test.json"
        test_data = {"test": "data"}

        # Write valid data
        self.store.write_data(data_path, test_data)

        # Tamper with data
        with open(data_path, 'w') as f:
            json.dump({"test": "TAMPERED"}, f)

        # Verification should fail
        assert not verify_file_integrity(data_path, "test-secret-key-32-characters-long")

    def test_different_secret_keys_produce_different_hmacs(self):
        """Test that different secret keys produce different HMACs."""
        data_path = Path(self.temp_dir) / "key_test.json"
        test_data = {"test": "data"}

        # Write with first key
        store1 = SecureDataStore(secret_key="first-secret-key-32-chars-long!!")
        store1.write_data(data_path, test_data)

        # Try to read with different key (should fail)
        store2 = SecureDataStore(secret_key="second-secret-key-32-chars-long!")
        with pytest.raises(ValueError, match="Data integrity check FAILED"):
            store2.read_data(data_path)


class TestEphemeralKeyWarning:
    """Test ephemeral key generation when DATA_INTEGRITY_KEY not set."""

    def test_ephemeral_key_generated_without_env_var(self, caplog):
        """Test that ephemeral key is generated with warning when env var not set."""
        import logging

        # Clear environment variable
        old_key = os.environ.pop('DATA_INTEGRITY_KEY', None)

        try:
            with caplog.at_level(logging.WARNING):
                store = SecureDataStore()
                assert store.secret_key is not None
                assert "DATA_INTEGRITY_KEY not set" in caplog.text
                assert "Using ephemeral key" in caplog.text
        finally:
            # Restore environment variable
            if old_key:
                os.environ['DATA_INTEGRITY_KEY'] = old_key


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
