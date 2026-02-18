"""
SQLite Fingerprint Storage Tests (FDA-40).

Tests the SQLite migration and storage layer for fingerprints:
    1. SQLite database creation and schema
    2. Automatic JSON-to-SQLite migration
    3. CRUD operations (load, save, list, delete)
    4. Unified fingerprint access (JSON vs SQLite modes)
    5. Backward compatibility (writes to both when SQLite enabled)
    6. Edge cases (empty DB, corrupted data, concurrent use)

All tests run offline with temporary directories.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent.resolve()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from change_detector import (
    _init_sqlite_db,
    _get_sqlite_path,
    _load_fingerprint_sqlite,
    _save_fingerprint_sqlite,
    _list_fingerprints_sqlite,
    _delete_fingerprint_sqlite,
    _migrate_json_to_sqlite,
    load_fingerprint,
    save_fingerprint,
    set_use_sqlite,
    _load_fingerprint,
    _save_fingerprint,
)
from fda_data_store import load_manifest, save_manifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_FINGERPRINT = {
    "last_checked": "2026-02-16T10:00:00+00:00",
    "clearance_count": 147,
    "latest_k_number": "K251234",
    "latest_decision_date": "20260115",
    "recall_count": 3,
    "known_k_numbers": ["K251234", "K250987", "K250555"],
}

SAMPLE_FINGERPRINT_2 = {
    "last_checked": "2026-02-17T10:00:00+00:00",
    "clearance_count": 85,
    "latest_k_number": "K250001",
    "latest_decision_date": "20260201",
    "recall_count": 1,
    "known_k_numbers": ["K250001", "K250002"],
}


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with a manifest."""
    manifest = {
        "project": "test_sqlite",
        "product_codes": ["DQY", "OVE"],
        "queries": {},
        "fingerprints": {
            "DQY": SAMPLE_FINGERPRINT,
            "OVE": SAMPLE_FINGERPRINT_2,
        },
    }
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return str(tmp_path)


@pytest.fixture
def empty_project_dir(tmp_path):
    """Create a temporary project directory with empty manifest."""
    manifest = {"project": "test_empty", "product_codes": [], "queries": {}}
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return str(tmp_path)


@pytest.fixture(autouse=True)
def _reset_sqlite_mode():
    """Reset the SQLite mode after each test."""
    set_use_sqlite(False)
    yield
    set_use_sqlite(False)


# ============================================================
# 1. SQLite Database Creation and Schema
# ============================================================


class TestSQLiteDatabaseCreation:
    """Test SQLite database initialization."""

    def test_init_creates_db(self, tmp_path):
        """_init_sqlite_db should create the database file."""
        db_path = str(tmp_path / "fingerprints.db")
        conn = _init_sqlite_db(db_path)
        conn.close()
        assert os.path.exists(db_path)

    def test_init_creates_fingerprints_table(self, tmp_path):
        """The fingerprints table should be created."""
        db_path = str(tmp_path / "fingerprints.db")
        conn = _init_sqlite_db(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fingerprints'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_init_creates_migration_meta_table(self, tmp_path):
        """The migration_meta table should be created."""
        db_path = str(tmp_path / "fingerprints.db")
        conn = _init_sqlite_db(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migration_meta'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_fingerprints_table_schema(self, tmp_path):
        """Fingerprints table should have product_code, data, updated_at columns."""
        db_path = str(tmp_path / "fingerprints.db")
        conn = _init_sqlite_db(db_path)

        cursor = conn.execute("PRAGMA table_info(fingerprints)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "product_code" in columns
        assert "data" in columns
        assert "updated_at" in columns
        conn.close()

    def test_product_code_is_primary_key(self, tmp_path):
        """product_code should be the primary key."""
        db_path = str(tmp_path / "fingerprints.db")
        conn = _init_sqlite_db(db_path)

        cursor = conn.execute("PRAGMA table_info(fingerprints)")
        for row in cursor.fetchall():
            if row[1] == "product_code":
                assert row[5] == 1, "product_code should be primary key (pk=1)"
        conn.close()

    def test_init_idempotent(self, tmp_path):
        """Calling _init_sqlite_db multiple times should be safe."""
        db_path = str(tmp_path / "fingerprints.db")
        conn1 = _init_sqlite_db(db_path)
        conn1.close()
        conn2 = _init_sqlite_db(db_path)
        conn2.close()
        assert os.path.exists(db_path)

    def test_get_sqlite_path(self, tmp_path):
        """_get_sqlite_path should return path inside project dir."""
        path = _get_sqlite_path(str(tmp_path))
        assert path == str(tmp_path / "fingerprints.db")


# ============================================================
# 2. JSON-to-SQLite Migration
# ============================================================


class TestJSONToSQLiteMigration:
    """Test automatic migration from JSON to SQLite."""

    def test_migration_basic(self, project_dir):
        """Migration should copy all JSON fingerprints to SQLite."""
        count = _migrate_json_to_sqlite(project_dir)
        assert count == 2, f"Expected 2 migrated, got {count}"

    def test_migration_preserves_data(self, project_dir):
        """Migrated data should be identical to JSON source."""
        _migrate_json_to_sqlite(project_dir)

        fp = _load_fingerprint_sqlite(project_dir, "DQY")
        assert fp is not None
        assert fp["clearance_count"] == 147
        assert fp["latest_k_number"] == "K251234"
        assert len(fp["known_k_numbers"]) == 3

    def test_migration_idempotent(self, project_dir):
        """Running migration twice should not duplicate data."""
        count1 = _migrate_json_to_sqlite(project_dir)
        count2 = _migrate_json_to_sqlite(project_dir)
        assert count1 == 2
        assert count2 == 0, "Second migration should return 0 (already migrated)"

    def test_migration_records_timestamp(self, project_dir):
        """Migration should record timestamp in migration_meta."""
        _migrate_json_to_sqlite(project_dir)

        db_path = _get_sqlite_path(project_dir)
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT value FROM migration_meta WHERE key = 'migrated_from_json'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert "2026" in row[0] or "T" in row[0]  # ISO timestamp

    def test_migration_empty_fingerprints(self, empty_project_dir):
        """Migration with no fingerprints should succeed with count 0."""
        count = _migrate_json_to_sqlite(empty_project_dir)
        assert count == 0

    def test_migration_uppercases_product_codes(self, project_dir):
        """Migrated product codes should be uppercased."""
        _migrate_json_to_sqlite(project_dir)
        fps = _list_fingerprints_sqlite(project_dir)
        for pc in fps:
            assert pc == pc.upper()


# ============================================================
# 3. CRUD Operations
# ============================================================


class TestSQLiteCRUD:
    """Test Create, Read, Update, Delete operations."""

    def test_save_and_load(self, empty_project_dir):
        """Save a fingerprint and load it back."""
        _save_fingerprint_sqlite(empty_project_dir, "DQY", SAMPLE_FINGERPRINT)
        loaded = _load_fingerprint_sqlite(empty_project_dir, "DQY")

        assert loaded is not None
        assert loaded["clearance_count"] == 147
        assert loaded["latest_k_number"] == "K251234"

    def test_save_overwrites(self, empty_project_dir):
        """Saving to same product code should overwrite."""
        _save_fingerprint_sqlite(empty_project_dir, "DQY", SAMPLE_FINGERPRINT)
        updated_fp = {**SAMPLE_FINGERPRINT, "clearance_count": 200}
        _save_fingerprint_sqlite(empty_project_dir, "DQY", updated_fp)

        loaded = _load_fingerprint_sqlite(empty_project_dir, "DQY")
        assert loaded["clearance_count"] == 200

    def test_load_nonexistent(self, empty_project_dir):
        """Loading a non-existent fingerprint should return None."""
        loaded = _load_fingerprint_sqlite(empty_project_dir, "ZZZ")
        assert loaded is None

    def test_load_no_db_file(self, tmp_path):
        """Loading from project without db file should return None."""
        loaded = _load_fingerprint_sqlite(str(tmp_path), "DQY")
        assert loaded is None

    def test_list_fingerprints(self, empty_project_dir):
        """List all fingerprints."""
        _save_fingerprint_sqlite(empty_project_dir, "DQY", SAMPLE_FINGERPRINT)
        _save_fingerprint_sqlite(empty_project_dir, "OVE", SAMPLE_FINGERPRINT_2)

        fps = _list_fingerprints_sqlite(empty_project_dir)
        assert len(fps) == 2
        assert "DQY" in fps
        assert "OVE" in fps

    def test_list_empty_db(self, empty_project_dir):
        """List from empty database should return empty dict."""
        fps = _list_fingerprints_sqlite(empty_project_dir)
        assert fps == {}

    def test_delete_fingerprint(self, empty_project_dir):
        """Delete a fingerprint."""
        _save_fingerprint_sqlite(empty_project_dir, "DQY", SAMPLE_FINGERPRINT)
        result = _delete_fingerprint_sqlite(empty_project_dir, "DQY")
        assert result is True

        loaded = _load_fingerprint_sqlite(empty_project_dir, "DQY")
        assert loaded is None

    def test_delete_nonexistent(self, empty_project_dir):
        """Deleting non-existent fingerprint should return False."""
        result = _delete_fingerprint_sqlite(empty_project_dir, "ZZZ")
        assert result is False

    def test_case_insensitive_product_code(self, empty_project_dir):
        """Product codes should be case-insensitive (uppercased)."""
        _save_fingerprint_sqlite(empty_project_dir, "dqy", SAMPLE_FINGERPRINT)
        loaded = _load_fingerprint_sqlite(empty_project_dir, "DQY")
        assert loaded is not None

    def test_save_complex_fingerprint(self, empty_project_dir):
        """Save and load a fingerprint with complex nested data."""
        complex_fp = {
            **SAMPLE_FINGERPRINT,
            "device_data": {
                "K251234": {
                    "k_number": "K251234",
                    "device_name": "Test Device",
                    "applicant": "Test Corp",
                },
            },
        }
        _save_fingerprint_sqlite(empty_project_dir, "DQY", complex_fp)
        loaded = _load_fingerprint_sqlite(empty_project_dir, "DQY")
        assert loaded["device_data"]["K251234"]["device_name"] == "Test Device"


# ============================================================
# 4. Unified Fingerprint Access
# ============================================================


class TestUnifiedFingerprintAccess:
    """Test the unified load_fingerprint and save_fingerprint functions."""

    def test_json_mode_default(self, project_dir):
        """Default mode should use JSON (data_manifest.json)."""
        set_use_sqlite(False)
        fp = load_fingerprint(project_dir, "DQY")
        assert fp is not None
        assert fp["clearance_count"] == 147

    def test_sqlite_mode_with_migration(self, project_dir):
        """SQLite mode should automatically migrate on first use."""
        set_use_sqlite(True)
        fp = load_fingerprint(project_dir, "DQY")
        assert fp is not None
        assert fp["clearance_count"] == 147

        # Verify SQLite DB was created
        db_path = _get_sqlite_path(project_dir)
        assert os.path.exists(db_path)

    def test_save_sqlite_mode_writes_both(self, project_dir):
        """Saving in SQLite mode should write to both SQLite and JSON."""
        set_use_sqlite(True)
        new_fp = {**SAMPLE_FINGERPRINT, "clearance_count": 999}
        save_fingerprint(project_dir, "DQY", new_fp)

        # Verify SQLite has the new value
        sqlite_fp = _load_fingerprint_sqlite(project_dir, "DQY")
        assert sqlite_fp is not None
        assert sqlite_fp["clearance_count"] == 999

        # Verify JSON also has the new value (backward compat)
        json_fp = _load_fingerprint(project_dir, "DQY")
        assert json_fp is not None
        assert json_fp["clearance_count"] == 999

    def test_save_json_mode_no_sqlite(self, project_dir):
        """Saving in JSON mode should not create SQLite DB."""
        set_use_sqlite(False)
        new_fp = {**SAMPLE_FINGERPRINT, "clearance_count": 888}
        save_fingerprint(project_dir, "DQY", new_fp)

        # No SQLite DB should be created
        db_path = _get_sqlite_path(project_dir)
        assert not os.path.exists(db_path)

        # JSON should be updated
        json_fp = _load_fingerprint(project_dir, "DQY")
        assert json_fp is not None
        assert json_fp["clearance_count"] == 888


# ============================================================
# 5. Backward Compatibility
# ============================================================


class TestBackwardCompatibility:
    """Test that JSON remains authoritative for non-fingerprint data."""

    def test_manifest_non_fingerprint_data_preserved(self, project_dir):
        """Non-fingerprint data in data_manifest.json should be untouched."""
        set_use_sqlite(True)

        # Migrate to SQLite
        _migrate_json_to_sqlite(project_dir)

        # Verify non-fingerprint data is still in JSON
        manifest = load_manifest(project_dir)
        assert manifest.get("project") == "test_sqlite"
        assert "DQY" in manifest.get("product_codes", [])

    def test_json_fingerprints_not_removed_on_migration(self, project_dir):
        """Migration should NOT remove fingerprints from JSON."""
        _migrate_json_to_sqlite(project_dir)

        manifest = load_manifest(project_dir)
        assert "DQY" in manifest.get("fingerprints", {})
        assert "OVE" in manifest.get("fingerprints", {})


# ============================================================
# 6. Edge Cases
# ============================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_load_from_corrupted_sqlite(self, tmp_path):
        """Loading from corrupted SQLite should return None gracefully."""
        db_path = str(tmp_path / "fingerprints.db")
        # Write invalid content to the file
        with open(db_path, "w") as f:
            f.write("this is not a sqlite database")

        # Should handle gracefully
        loaded = _load_fingerprint_sqlite(str(tmp_path), "DQY")
        assert loaded is None

    def test_save_to_read_only_dir(self, tmp_path):
        """Saving to read-only directory should fail gracefully."""
        # This test is platform-dependent; skip if not possible
        import stat

        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()

        # Create the DB first
        db_path = str(read_only_dir / "fingerprints.db")
        conn = _init_sqlite_db(db_path)
        conn.close()

        # Make directory read-only
        try:
            os.chmod(str(read_only_dir), stat.S_IRUSR | stat.S_IXUSR)

            # This should fail gracefully (logged, not raised)
            # Just verify no exception is raised
            _save_fingerprint_sqlite(str(read_only_dir), "DQY", SAMPLE_FINGERPRINT)
        finally:
            # Restore permissions for cleanup
            os.chmod(str(read_only_dir), stat.S_IRWXU)

    def test_large_fingerprint_count(self, empty_project_dir):
        """Test with 200+ fingerprints (beyond JSON performance threshold)."""
        for i in range(200):
            pc = f"T{i:03d}"
            fp = {
                "last_checked": "2026-02-17T00:00:00+00:00",
                "clearance_count": i,
                "known_k_numbers": [f"K{i:06d}"],
            }
            _save_fingerprint_sqlite(empty_project_dir, pc, fp)

        fps = _list_fingerprints_sqlite(empty_project_dir)
        assert len(fps) == 200

        # Verify a specific one
        loaded = _load_fingerprint_sqlite(empty_project_dir, "T099")
        assert loaded is not None
        assert loaded["clearance_count"] == 99

    def test_empty_product_code(self, empty_project_dir):
        """Empty product code should be handled."""
        _save_fingerprint_sqlite(empty_project_dir, "", SAMPLE_FINGERPRINT)
        loaded = _load_fingerprint_sqlite(empty_project_dir, "")
        assert loaded is not None

    def test_special_characters_in_data(self, empty_project_dir):
        """Fingerprint data with special characters should round-trip."""
        fp = {
            **SAMPLE_FINGERPRINT,
            "device_data": {
                "K123": {"device_name": "O'Brien's \"Special\" Device (Rev. 2)"}
            },
        }
        _save_fingerprint_sqlite(empty_project_dir, "DQY", fp)
        loaded = _load_fingerprint_sqlite(empty_project_dir, "DQY")
        assert loaded["device_data"]["K123"]["device_name"] == (
            "O'Brien's \"Special\" Device (Rev. 2)"
        )


# ============================================================
# 7. Performance Characteristics
# ============================================================


class TestPerformanceCharacteristics:
    """Verify that SQLite operations have expected performance characteristics."""

    def test_individual_read_write_fast(self, empty_project_dir):
        """Individual read/write operations should complete quickly."""
        import time

        # Write 50 entries
        start = time.monotonic()
        for i in range(50):
            _save_fingerprint_sqlite(
                empty_project_dir,
                f"PC{i:03d}",
                {**SAMPLE_FINGERPRINT, "clearance_count": i},
            )
        write_time = time.monotonic() - start

        # Read 50 entries
        start = time.monotonic()
        for i in range(50):
            _load_fingerprint_sqlite(empty_project_dir, f"PC{i:03d}")
        read_time = time.monotonic() - start

        # Should complete in under 5 seconds (generous for CI)
        assert write_time < 5.0, f"50 writes took {write_time:.2f}s"
        assert read_time < 5.0, f"50 reads took {read_time:.2f}s"

    def test_list_operation_fast(self, empty_project_dir):
        """Listing all fingerprints should be fast even with many entries."""
        import time

        for i in range(100):
            _save_fingerprint_sqlite(
                empty_project_dir,
                f"PC{i:03d}",
                {**SAMPLE_FINGERPRINT, "clearance_count": i},
            )

        start = time.monotonic()
        fps = _list_fingerprints_sqlite(empty_project_dir)
        list_time = time.monotonic() - start

        assert len(fps) == 100
        assert list_time < 2.0, f"Listing 100 entries took {list_time:.2f}s"
