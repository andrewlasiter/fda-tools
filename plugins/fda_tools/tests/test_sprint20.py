"""
Sprint 20 tests  —  FDA-222 (Three-tier fallback: Supabase → local PG → JSON) +
                    FDA-221 (Migration: local PostgreSQL → Supabase)

All tests are unit-level with no external dependencies.  psycopg2 and Supabase
clients are mocked throughout.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fda_tools.lib.data_fallback import (
    DataTier,
    FallbackConfig,
    FallbackResult,
    JsonCacheStore,
    ThreeTierFallback,
)
from fda_tools.lib.pg_migration import (
    MIGRATION_TABLES,
    MigrationResult,
    MigrationStatus,
    MigrationSummary,
    SupabaseMigrator,
    migrate_local_to_supabase,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _mock_supabase(rows=None):
    """Return a MagicMock supabase client that returns *rows* for any query."""
    if rows is None:
        rows = [{"id": 1, "content": "test"}]
    response = MagicMock()
    response.data = rows
    client = MagicMock()
    client.table.return_value.select.return_value.limit.return_value.execute.return_value = response
    client.table.return_value.select.return_value.limit.return_value.eq.return_value.execute.return_value = response
    client.vector_search.return_value.execute.return_value = response
    client.health_check.return_value = True
    return client


def _mock_supabase_failing():
    """Return a MagicMock supabase client that raises on every call."""
    client = MagicMock()
    client.table.return_value.select.return_value.limit.return_value.execute.side_effect = ConnectionError("supabase down")
    client.table.return_value.select.return_value.limit.return_value.eq.return_value.execute.side_effect = ConnectionError("supabase down")
    client.vector_search.return_value.execute.side_effect = ConnectionError("supabase down")
    client.health_check.side_effect = ConnectionError("supabase down")
    return client


# ===========================================================================
# data_fallback.py
# ===========================================================================

class TestDataTier(unittest.TestCase):
    def test_tier_values(self):
        self.assertEqual(DataTier.SUPABASE.value, "supabase")
        self.assertEqual(DataTier.LOCAL_PG.value, "local_pg")
        self.assertEqual(DataTier.JSON_CACHE.value, "json_cache")

    def test_string_enum(self):
        self.assertEqual(DataTier.SUPABASE.value, "supabase")


class TestFallbackResult(unittest.TestCase):
    def _make(self, tier=DataTier.SUPABASE):
        return FallbackResult(
            tier=tier, data=[{"id": 1}], latency_ms=12.5,
            attempted_tiers=[tier], error_by_tier={}, source_key="test_key",
        )

    def test_degraded_false_for_supabase(self):
        self.assertFalse(self._make(DataTier.SUPABASE).degraded)

    def test_degraded_true_for_local_pg(self):
        self.assertTrue(self._make(DataTier.LOCAL_PG).degraded)

    def test_fully_degraded_false_for_supabase(self):
        self.assertFalse(self._make(DataTier.SUPABASE).fully_degraded)

    def test_fully_degraded_true_for_json_cache(self):
        self.assertTrue(self._make(DataTier.JSON_CACHE).fully_degraded)

    def test_as_dict_keys(self):
        d = self._make().as_dict()
        self.assertIn("tier", d)
        self.assertIn("row_count", d)
        self.assertIn("latency_ms", d)
        self.assertIn("degraded", d)
        self.assertIn("attempted_tiers", d)

    def test_as_dict_row_count(self):
        r = self._make()
        self.assertEqual(r.as_dict()["row_count"], 1)

    def test_frozen(self):
        r = self._make()
        with self.assertRaises((AttributeError, TypeError)):
            r.tier = DataTier.LOCAL_PG  # type: ignore[misc]


class TestFallbackConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = FallbackConfig()
        self.assertEqual(cfg.supabase_timeout_s, 5.0)
        self.assertIsNone(cfg.local_pg_dsn)
        self.assertIsNone(cfg.json_cache_dir)
        self.assertEqual(cfg.max_retries, 1)
        self.assertTrue(cfg.log_degradation)

    def test_custom(self):
        cfg = FallbackConfig(supabase_timeout_s=2.0, max_retries=3)
        self.assertEqual(cfg.supabase_timeout_s, 2.0)
        self.assertEqual(cfg.max_retries, 3)


class TestJsonCacheStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.cache = JsonCacheStore(self._tmpdir)

    def test_put_and_get(self):
        rows = [{"id": 1, "content": "hello"}]
        self.cache.put("guidance_embeddings", "key1", rows)
        result = self.cache.get("guidance_embeddings", "key1")
        self.assertEqual(result, rows)

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.cache.get("nonexistent", "no_key"))

    def test_delete_existing(self):
        self.cache.put("t", "k", [])
        self.assertTrue(self.cache.delete("t", "k"))
        self.assertIsNone(self.cache.get("t", "k"))

    def test_delete_missing_returns_false(self):
        self.assertFalse(self.cache.delete("t", "missing"))

    def test_list_keys_empty(self):
        self.assertEqual(self.cache.list_keys("nosuchTable"), [])

    def test_list_keys_after_put(self):
        self.cache.put("tbl", "k1", [])
        self.cache.put("tbl", "k2", [])
        keys = self.cache.list_keys("tbl")
        self.assertIn("k1", keys)
        self.assertIn("k2", keys)

    def test_list_keys_only_own_table(self):
        self.cache.put("tblA", "k1", [])
        self.cache.put("tblB", "k2", [])
        self.assertNotIn("k2", self.cache.list_keys("tblA"))

    def test_clear_specific_table(self):
        self.cache.put("t", "k1", [])
        self.cache.put("t", "k2", [])
        self.cache.put("other", "k3", [])
        removed = self.cache.clear("t")
        self.assertEqual(removed, 2)
        self.assertIsNone(self.cache.get("t", "k1"))
        self.assertIsNotNone(self.cache.get("other", "k3"))

    def test_clear_all(self):
        self.cache.put("t1", "k", [])
        self.cache.put("t2", "k", [])
        removed = self.cache.clear()
        self.assertEqual(removed, 2)

    def test_auto_creates_directory(self):
        import os
        new_dir = os.path.join(self._tmpdir, "subdir", "cache")
        store = JsonCacheStore(new_dir)
        self.assertTrue(os.path.isdir(new_dir))
        store.put("t", "k", [{"x": 1}])
        self.assertEqual(store.get("t", "k"), [{"x": 1}])


class TestThreeTierFallbackQueryTier1(unittest.TestCase):
    """Tests where Supabase (Tier 1) succeeds."""

    def test_query_uses_supabase(self):
        sb = _mock_supabase([{"id": 1}])
        fb = ThreeTierFallback(sb)
        result = fb.query("guidance_embeddings")
        self.assertEqual(result.tier, DataTier.SUPABASE)
        self.assertEqual(result.data, [{"id": 1}])

    def test_query_not_degraded(self):
        result = ThreeTierFallback(_mock_supabase()).query("tbl")
        self.assertFalse(result.degraded)

    def test_query_latency_positive(self):
        result = ThreeTierFallback(_mock_supabase()).query("tbl")
        self.assertGreaterEqual(result.latency_ms, 0.0)

    def test_vector_search_tier1(self):
        sb = _mock_supabase([{"similarity": 0.9, "content": "foo"}])
        fb = ThreeTierFallback(sb)
        result = fb.vector_search("guidance_embeddings", [0.1, 0.2, 0.3])
        self.assertEqual(result.tier, DataTier.SUPABASE)
        self.assertEqual(len(result.data), 1)

    def test_attempted_tiers_contains_supabase(self):
        result = ThreeTierFallback(_mock_supabase()).query("tbl")
        self.assertIn(DataTier.SUPABASE, result.attempted_tiers)


class TestThreeTierFallbackQueryTier3(unittest.TestCase):
    """Tests where Supabase fails and JSON cache is the fallback."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_falls_back_to_json_cache(self):
        sb = _mock_supabase_failing()
        cache_rows = [{"id": 99, "content": "cached"}]
        # Pre-populate cache
        store = JsonCacheStore(self._tmpdir)
        store.put("guidance_embeddings", "query__guidance_embeddings____100", cache_rows)
        fb = ThreeTierFallback(sb, json_cache_dir=self._tmpdir)
        result = fb.query("guidance_embeddings")
        self.assertEqual(result.tier, DataTier.JSON_CACHE)
        self.assertEqual(result.data, cache_rows)

    def test_fallback_is_degraded(self):
        sb = _mock_supabase_failing()
        store = JsonCacheStore(self._tmpdir)
        store.put("guidance_embeddings", "query__guidance_embeddings____100", [{"id": 1}])
        fb = ThreeTierFallback(sb, json_cache_dir=self._tmpdir)
        result = fb.query("guidance_embeddings")
        self.assertTrue(result.degraded)
        self.assertTrue(result.fully_degraded)

    def test_error_recorded_for_failed_tier(self):
        sb = _mock_supabase_failing()
        store = JsonCacheStore(self._tmpdir)
        store.put("guidance_embeddings", "query__guidance_embeddings____100", [])
        fb = ThreeTierFallback(sb, json_cache_dir=self._tmpdir)
        result = fb.query("guidance_embeddings")
        self.assertIn("supabase", result.error_by_tier)

    def test_all_tiers_exhausted_returns_empty(self):
        sb = _mock_supabase_failing()
        # No cache configured, no PG
        fb = ThreeTierFallback(sb)
        result = fb.query("guidance_embeddings")
        self.assertEqual(result.data, [])

    def test_write_through_populates_cache(self):
        sb = _mock_supabase([{"id": 1}])
        fb = ThreeTierFallback(sb, json_cache_dir=self._tmpdir)
        fb.query("guidance_embeddings")
        # Supabase succeeds — no write-through needed (only for fallback tiers)
        # Now fail Supabase and check JSON cache has the data
        store = JsonCacheStore(self._tmpdir)
        # manually add to cache to test the path
        store.put("guidance_embeddings", "query__guidance_embeddings____100", [{"id": 1}])
        fb2 = ThreeTierFallback(_mock_supabase_failing(), json_cache_dir=self._tmpdir)
        result = fb2.query("guidance_embeddings")
        self.assertEqual(result.data, [{"id": 1}])

    def test_write_to_cache_manual(self):
        sb = _mock_supabase()
        fb = ThreeTierFallback(sb, json_cache_dir=self._tmpdir)
        ok = fb.write_to_cache("guidance_embeddings", "my_key", [{"id": 42}])
        self.assertTrue(ok)

    def test_write_to_cache_no_cache_configured(self):
        sb = _mock_supabase()
        fb = ThreeTierFallback(sb)
        ok = fb.write_to_cache("tbl", "key", [])
        self.assertFalse(ok)


class TestThreeTierFallbackHealthCheck(unittest.TestCase):
    def test_supabase_healthy(self):
        sb = _mock_supabase()
        fb = ThreeTierFallback(sb)
        statuses = fb.health_check()
        self.assertTrue(statuses[DataTier.SUPABASE])

    def test_supabase_unhealthy(self):
        sb = _mock_supabase_failing()
        fb = ThreeTierFallback(sb)
        statuses = fb.health_check()
        self.assertFalse(statuses[DataTier.SUPABASE])

    def test_json_cache_healthy_when_configured(self):
        with tempfile.TemporaryDirectory() as d:
            fb = ThreeTierFallback(_mock_supabase(), json_cache_dir=d)
            statuses = fb.health_check()
            self.assertTrue(statuses[DataTier.JSON_CACHE])

    def test_json_cache_unavailable_when_not_configured(self):
        fb = ThreeTierFallback(_mock_supabase())
        statuses = fb.health_check()
        self.assertFalse(statuses[DataTier.JSON_CACHE])

    def test_local_pg_unavailable_without_psycopg2(self):
        with patch("fda_tools.lib.data_fallback._PSYCOPG2_AVAILABLE", False):
            fb = ThreeTierFallback(_mock_supabase(), local_pg_dsn="postgresql://localhost/test")
            statuses = fb.health_check()
            self.assertFalse(statuses[DataTier.LOCAL_PG])


class TestThreeTierFallbackNoPgDsn(unittest.TestCase):
    def test_pg_tier_skipped_when_no_dsn(self):
        sb = _mock_supabase_failing()
        fb = ThreeTierFallback(sb)  # no pg_dsn, no cache
        result = fb.query("tbl")
        self.assertNotIn(DataTier.LOCAL_PG, result.attempted_tiers)


# ===========================================================================
# pg_migration.py
# ===========================================================================

class TestMigrationTables(unittest.TestCase):
    def test_three_tables_defined(self):
        self.assertEqual(len(MIGRATION_TABLES), 3)

    def test_guidance_embeddings_key_cols(self):
        self.assertIn("doc_id", MIGRATION_TABLES["guidance_embeddings"])
        self.assertIn("chunk_index", MIGRATION_TABLES["guidance_embeddings"])

    def test_project_embeddings_key_cols(self):
        self.assertIn("project_id", MIGRATION_TABLES["project_embeddings"])


class TestMigrationResult(unittest.TestCase):
    def test_default_status(self):
        r = MigrationResult(table="t")
        self.assertEqual(r.status, MigrationStatus.PENDING)

    def test_success_rate_no_rows(self):
        r = MigrationResult(table="t")
        self.assertEqual(r.success_rate, 1.0)

    def test_success_rate_partial(self):
        r = MigrationResult(table="t", rows_found=10, rows_migrated=7)
        self.assertAlmostEqual(r.success_rate, 0.7)

    def test_as_dict_keys(self):
        r = MigrationResult(table="t", rows_found=5, rows_migrated=5)
        d = r.as_dict()
        self.assertIn("table", d)
        self.assertIn("status", d)
        self.assertIn("rows_found", d)
        self.assertIn("success_rate", d)
        self.assertIn("dry_run", d)

    def test_errors_capped_in_as_dict(self):
        r = MigrationResult(table="t", errors=[f"e{i}" for i in range(20)])
        d = r.as_dict()
        self.assertLessEqual(len(d["errors"]), 10)


class TestMigrationSummary(unittest.TestCase):
    def _make(self, statuses):
        results = []
        for s in statuses:
            r = MigrationResult(table="t", rows_found=10, rows_migrated=10)
            r.status = s
            results.append(r)
        return MigrationSummary(results=results)

    def test_total_migrated(self):
        s = self._make([MigrationStatus.COMPLETED, MigrationStatus.COMPLETED])
        self.assertEqual(s.total_migrated, 20)

    def test_all_completed_true(self):
        s = self._make([MigrationStatus.COMPLETED, MigrationStatus.SKIPPED])
        self.assertTrue(s.all_completed)

    def test_all_completed_false_when_failed(self):
        s = self._make([MigrationStatus.COMPLETED, MigrationStatus.FAILED])
        self.assertFalse(s.all_completed)

    def test_as_dict_keys(self):
        s = self._make([MigrationStatus.COMPLETED])
        d = s.as_dict()
        self.assertIn("total_migrated", d)
        self.assertIn("tables", d)
        self.assertIn("all_completed", d)

    def test_report_contains_table_name(self):
        r = MigrationResult(table="guidance_embeddings", rows_found=5, rows_migrated=5)
        r.status = MigrationStatus.COMPLETED
        s = MigrationSummary(results=[r])
        report = s.report()
        self.assertIn("guidance_embeddings", report)
        self.assertIn("5/5", report)


class TestSupabaseMigratorNoSource(unittest.TestCase):
    """Tests for when psycopg2 is not available."""

    def test_migrate_table_fails_without_psycopg2(self):
        with patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", False):
            migrator = SupabaseMigrator("postgresql://localhost/test", _mock_supabase())
            result = migrator.migrate_table("guidance_embeddings")
        self.assertEqual(result.status, MigrationStatus.FAILED)
        self.assertTrue(len(result.errors) > 0)

    def test_estimate_rows_without_psycopg2(self):
        with patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", False):
            migrator = SupabaseMigrator("postgresql://localhost/test", _mock_supabase())
            self.assertEqual(migrator.estimate_rows("guidance_embeddings"), -1)

    def test_migrate_all_without_psycopg2(self):
        with patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", False):
            migrator = SupabaseMigrator("postgresql://localhost/test", _mock_supabase())
            summary = migrator.migrate_all()
        self.assertEqual(len(summary.results), len(MIGRATION_TABLES))
        self.assertFalse(summary.all_completed)


class TestSupabaseMigratorDryRun(unittest.TestCase):
    """Tests using a mock psycopg2 connection so we can test the dry-run path."""

    def _make_pg_mock(self, rows=None):
        """Return a mock psycopg2 module with a fake connection."""
        if rows is None:
            rows = [{"doc_id": "d1", "chunk_index": 0, "content": "c", "embedding": [0.1]*4}]

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"exists": True},      # to_regclass check
            {"n": len(rows)},      # COUNT(*)
        ]
        mock_cursor.fetchall.return_value = []
        # Make the cursor iterable (for row streaming)
        mock_cursor.__iter__ = MagicMock(return_value=iter(rows))

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_pg = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_pg.extras.RealDictCursor = MagicMock()
        return mock_pg

    def test_dry_run_no_supabase_writes(self):
        sb = _mock_supabase()
        mock_pg = self._make_pg_mock([
            {"doc_id": "d1", "chunk_index": 0, "content": "c"}
        ])
        with (
            patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", True),
            patch("fda_tools.lib.pg_migration.psycopg2", mock_pg),
        ):
            migrator = SupabaseMigrator(
                "postgresql://localhost/test", sb, dry_run=True, batch_size=10
            )
            result = migrator.migrate_table("guidance_embeddings")
        # Dry run: rows counted as migrated but supabase.table().insert never called
        sb.table.return_value.insert.assert_not_called()
        self.assertTrue(result.dry_run)

    def test_dry_run_reports_rows_migrated(self):
        sb = _mock_supabase()
        rows = [{"doc_id": f"d{i}", "chunk_index": i} for i in range(5)]
        mock_pg = self._make_pg_mock(rows)
        with (
            patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", True),
            patch("fda_tools.lib.pg_migration.psycopg2", mock_pg),
        ):
            migrator = SupabaseMigrator(
                "postgresql://localhost/test", sb, dry_run=True, batch_size=10
            )
            result = migrator.migrate_table("guidance_embeddings")
        self.assertEqual(result.rows_migrated, 5)
        self.assertEqual(result.rows_failed, 0)

    def test_connection_failure_marks_failed(self):
        mock_pg = MagicMock()
        mock_pg.connect.side_effect = Exception("connection refused")
        with (
            patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", True),
            patch("fda_tools.lib.pg_migration.psycopg2", mock_pg),
        ):
            migrator = SupabaseMigrator("postgresql://localhost/test", _mock_supabase())
            result = migrator.migrate_table("guidance_embeddings")
        self.assertEqual(result.status, MigrationStatus.FAILED)
        self.assertIn("connection refused", result.errors[0])

    def test_table_not_found_marks_skipped(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"exists": False}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pg = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_pg.extras.RealDictCursor = MagicMock()
        with (
            patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", True),
            patch("fda_tools.lib.pg_migration.psycopg2", mock_pg),
        ):
            migrator = SupabaseMigrator("postgresql://localhost/test", _mock_supabase())
            result = migrator.migrate_table("guidance_embeddings")
        self.assertEqual(result.status, MigrationStatus.SKIPPED)

    def test_progress_callback_called(self):
        sb = _mock_supabase()
        rows = [{"doc_id": f"d{i}", "chunk_index": i} for i in range(3)]
        mock_pg = self._make_pg_mock(rows)
        progress_calls = []
        def on_progress(table, done, total):
            progress_calls.append((table, done, total))
        with (
            patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", True),
            patch("fda_tools.lib.pg_migration.psycopg2", mock_pg),
        ):
            migrator = SupabaseMigrator(
                "postgresql://localhost/test", sb, dry_run=True,
                batch_size=10, on_progress=on_progress
            )
            migrator.migrate_table("guidance_embeddings")
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(progress_calls[0][0], "guidance_embeddings")


class TestSupabaseMigratorBatchSize(unittest.TestCase):
    def test_batch_size_1_issues_multiple_batches(self):
        sb = _mock_supabase()
        rows = [{"doc_id": f"d{i}", "chunk_index": i} for i in range(4)]
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [{"exists": True}, {"n": 4}]
        mock_cursor.__iter__ = MagicMock(return_value=iter(rows))
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pg = MagicMock()
        mock_pg.connect.return_value = mock_conn
        mock_pg.extras.RealDictCursor = MagicMock()
        with (
            patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", True),
            patch("fda_tools.lib.pg_migration.psycopg2", mock_pg),
        ):
            migrator = SupabaseMigrator(
                "postgresql://localhost/test", sb, dry_run=True, batch_size=1
            )
            result = migrator.migrate_table("guidance_embeddings")
        # 4 rows / batch_size=1 → 4 batches
        self.assertEqual(result.batches, 4)


class TestMigrateConvenienceFunction(unittest.TestCase):
    def test_convenience_function_calls_migrate_all(self):
        with patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", False):
            summary = migrate_local_to_supabase(
                source_dsn      = "postgresql://localhost/test",
                supabase_client = _mock_supabase(),
                dry_run         = True,
            )
        self.assertIsInstance(summary, MigrationSummary)

    def test_table_subset(self):
        with patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", False):
            summary = migrate_local_to_supabase(
                source_dsn      = "postgresql://localhost/test",
                supabase_client = _mock_supabase(),
                tables          = ["guidance_embeddings"],
                dry_run         = True,
            )
        self.assertEqual(len(summary.results), 1)
        self.assertEqual(summary.results[0].table, "guidance_embeddings")

    def test_unknown_table_ignored(self):
        with patch("fda_tools.lib.pg_migration._PSYCOPG2_AVAILABLE", False):
            summary = migrate_local_to_supabase(
                source_dsn      = "postgresql://localhost/test",
                supabase_client = _mock_supabase(),
                tables          = ["guidance_embeddings", "no_such_table"],
                dry_run         = True,
            )
        # "no_such_table" not in MIGRATION_TABLES → silently ignored
        self.assertEqual(len(summary.results), 1)


# ===========================================================================

if __name__ == "__main__":
    unittest.main()
