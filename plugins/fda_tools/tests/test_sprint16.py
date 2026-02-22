"""
Sprint 16 — Supabase Foundation Layer
======================================
Tests for:
  - plugins/fda_tools/lib/supabase_client.py   (FDA-219)
  - plugins/fda_tools/lib/pgvector_schema.py   (FDA-220)

No real Supabase connection required — all network calls are mocked.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# ── ensure package is importable ──────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fda_tools.lib.supabase_client import (
    SupabaseConfig,
    SupabaseClient,
    SupabaseConnectionError,
    get_client,
    reset_singleton,
)
from fda_tools.lib.pgvector_schema import (
    EMBEDDING_DIM,
    TABLE_DDL,
    INDEX_DDL,
    MATCH_FUNCTION_DDL,
    EmbeddingRecord,
    SchemaManager,
    match_function_sql,
    _TABLES,
)


# ══════════════════════════════════════════════════════════════════════════════
#  SupabaseConfig
# ══════════════════════════════════════════════════════════════════════════════

class TestSupabaseConfig(unittest.TestCase):
    """SupabaseConfig credential loading from environment variables."""

    def tearDown(self) -> None:
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    def test_from_env_happy_path(self) -> None:
        os.environ["SUPABASE_URL"] = "https://abc.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "service-role-key-abc"
        cfg = SupabaseConfig.from_env()
        self.assertEqual(cfg.url, "https://abc.supabase.co")
        self.assertEqual(cfg.secret_key, "service-role-key-abc")

    def test_from_env_strips_whitespace(self) -> None:
        os.environ["SUPABASE_URL"] = "  https://abc.supabase.co  "
        os.environ["SUPABASE_SECRET_KEY"] = "  key  "
        cfg = SupabaseConfig.from_env()
        self.assertEqual(cfg.url, "https://abc.supabase.co")
        self.assertEqual(cfg.secret_key, "key")

    def test_from_env_missing_url_raises(self) -> None:
        os.environ.pop("SUPABASE_URL", None)
        os.environ["SUPABASE_SECRET_KEY"] = "key"
        with self.assertRaises(SupabaseConnectionError) as ctx:
            SupabaseConfig.from_env()
        self.assertIn("SUPABASE_URL", str(ctx.exception))

    def test_from_env_missing_secret_raises(self) -> None:
        os.environ["SUPABASE_URL"] = "https://abc.supabase.co"
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        with self.assertRaises(SupabaseConnectionError) as ctx:
            SupabaseConfig.from_env()
        self.assertIn("SUPABASE_SECRET_KEY", str(ctx.exception))

    def test_from_env_both_missing_lists_both(self) -> None:
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        with self.assertRaises(SupabaseConnectionError) as ctx:
            SupabaseConfig.from_env()
        msg = str(ctx.exception)
        self.assertIn("SUPABASE_URL", msg)
        self.assertIn("SUPABASE_SECRET_KEY", msg)

    def test_from_env_empty_string_raises(self) -> None:
        os.environ["SUPABASE_URL"] = ""
        os.environ["SUPABASE_SECRET_KEY"] = ""
        with self.assertRaises(SupabaseConnectionError):
            SupabaseConfig.from_env()

    def test_frozen_dataclass(self) -> None:
        cfg = SupabaseConfig(url="https://x.supabase.co", secret_key="k")
        with self.assertRaises(Exception):
            cfg.url = "mutated"  # type: ignore[misc]

    def test_redacted_hides_secret(self) -> None:
        cfg = SupabaseConfig(url="https://x.supabase.co", secret_key="super-secret-key-long")
        redacted = cfg.redacted()
        self.assertNotIn("super-secret-key-long", redacted["secret_key"])
        self.assertIn("(redacted)", redacted["secret_key"])
        self.assertEqual(redacted["url"], "https://x.supabase.co")

    def test_redacted_short_key(self) -> None:
        cfg = SupabaseConfig(url="https://x.supabase.co", secret_key="tiny")
        redacted = cfg.redacted()
        self.assertIn("(redacted)", redacted["secret_key"])


# ══════════════════════════════════════════════════════════════════════════════
#  SupabaseClient (with mocked SDK)
# ══════════════════════════════════════════════════════════════════════════════

def _make_client(url: str = "https://x.supabase.co", key: str = "key") -> SupabaseClient:
    return SupabaseClient(SupabaseConfig(url=url, secret_key=key))


class TestSupabaseClientInit(unittest.TestCase):
    """SupabaseClient lazy-init and error handling."""

    def test_client_stores_config(self) -> None:
        cfg = SupabaseConfig(url="https://x.supabase.co", secret_key="k")
        sc = SupabaseClient(cfg)
        self.assertIs(sc.config, cfg)
        self.assertIsNone(sc._client)

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", False)
    def test_ensure_connected_raises_when_sdk_missing(self) -> None:
        sc = _make_client()
        with self.assertRaises(SupabaseConnectionError) as ctx:
            sc._ensure_connected()
        self.assertIn("not installed", str(ctx.exception))

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", True)
    @patch("fda_tools.lib.supabase_client._create_client")
    def test_ensure_connected_lazy_creates_once(self, mock_create: MagicMock) -> None:
        mock_sdk = MagicMock()
        mock_create.return_value = mock_sdk
        sc = _make_client()
        c1 = sc._ensure_connected()
        c2 = sc._ensure_connected()
        self.assertIs(c1, mock_sdk)
        self.assertIs(c2, mock_sdk)
        mock_create.assert_called_once()

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", True)
    @patch("fda_tools.lib.supabase_client._create_client")
    def test_ensure_connected_wraps_sdk_error(self, mock_create: MagicMock) -> None:
        mock_create.side_effect = RuntimeError("bad network")
        sc = _make_client()
        with self.assertRaises(SupabaseConnectionError) as ctx:
            sc._ensure_connected()
        self.assertIn("bad network", str(ctx.exception))

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", True)
    @patch("fda_tools.lib.supabase_client._create_client")
    def test_health_check_true_on_success(self, mock_create: MagicMock) -> None:
        mock_sdk = MagicMock()
        mock_sdk.auth.get_session.return_value = {}
        mock_create.return_value = mock_sdk
        sc = _make_client()
        self.assertTrue(sc.health_check())

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", True)
    @patch("fda_tools.lib.supabase_client._create_client")
    def test_health_check_false_on_auth_error(self, mock_create: MagicMock) -> None:
        mock_sdk = MagicMock()
        mock_sdk.auth.get_session.side_effect = Exception("auth error")
        mock_create.return_value = mock_sdk
        sc = _make_client()
        self.assertFalse(sc.health_check())

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", False)
    def test_health_check_false_when_sdk_missing(self) -> None:
        sc = _make_client()
        self.assertFalse(sc.health_check())


class TestSupabaseClientHelpers(unittest.TestCase):
    """table(), rpc(), and vector_search() proxy helpers."""

    def _connected_client(self) -> tuple[SupabaseClient, MagicMock]:
        """Return a SupabaseClient with a pre-injected mock SDK."""
        sc = _make_client()
        mock_sdk = MagicMock()
        sc._client = mock_sdk
        return sc, mock_sdk

    def test_table_delegates_to_sdk(self) -> None:
        sc, mock_sdk = self._connected_client()
        mock_qb = MagicMock()
        mock_sdk.table.return_value = mock_qb
        result = sc.table("guidance_embeddings")
        mock_sdk.table.assert_called_once_with("guidance_embeddings")
        self.assertIs(result, mock_qb)

    def test_rpc_delegates_to_sdk(self) -> None:
        sc, mock_sdk = self._connected_client()
        sc.rpc("my_func", {"a": 1})
        mock_sdk.rpc.assert_called_once_with("my_func", {"a": 1})

    def test_rpc_defaults_to_empty_params(self) -> None:
        sc, mock_sdk = self._connected_client()
        sc.rpc("my_func")
        mock_sdk.rpc.assert_called_once_with("my_func", {})

    def test_vector_search_calls_correct_function(self) -> None:
        sc, mock_sdk = self._connected_client()
        vec = [0.1] * EMBEDDING_DIM
        sc.vector_search(
            table="guidance_embeddings",
            embedding_column="embedding",
            query_vector=vec,
            match_threshold=0.8,
            match_count=5,
        )
        mock_sdk.rpc.assert_called_once()
        args = mock_sdk.rpc.call_args
        self.assertEqual(args[0][0], "match_guidance_embeddings")
        params = args[0][1]
        self.assertEqual(params["query_embedding"], vec)
        self.assertAlmostEqual(params["match_threshold"], 0.8)
        self.assertEqual(params["match_count"], 5)

    def test_vector_search_default_threshold(self) -> None:
        sc, mock_sdk = self._connected_client()
        sc.vector_search(
            table="fda_510k_embeddings",
            embedding_column="embedding",
            query_vector=[0.0] * EMBEDDING_DIM,
        )
        params = mock_sdk.rpc.call_args[0][1]
        self.assertAlmostEqual(params["match_threshold"], 0.75)
        self.assertEqual(params["match_count"], 10)


class TestSupabaseClientStatus(unittest.TestCase):
    """is_available() and is_configured() reflect environment state."""

    def tearDown(self) -> None:
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", True)
    def test_is_available_true(self) -> None:
        self.assertTrue(_make_client().is_available())

    @patch("fda_tools.lib.supabase_client._SUPABASE_AVAILABLE", False)
    def test_is_available_false(self) -> None:
        self.assertFalse(_make_client().is_available())

    def test_is_configured_true(self) -> None:
        os.environ["SUPABASE_URL"] = "https://x.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "k"
        self.assertTrue(_make_client().is_configured())

    def test_is_configured_false_missing_url(self) -> None:
        os.environ.pop("SUPABASE_URL", None)
        os.environ["SUPABASE_SECRET_KEY"] = "k"
        self.assertFalse(_make_client().is_configured())

    def test_is_configured_false_missing_key(self) -> None:
        os.environ["SUPABASE_URL"] = "https://x.supabase.co"
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        self.assertFalse(_make_client().is_configured())


class TestSingleton(unittest.TestCase):
    """get_client() singleton and reset_singleton()."""

    def setUp(self) -> None:
        reset_singleton()

    def tearDown(self) -> None:
        reset_singleton()
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    def test_get_client_raises_without_env(self) -> None:
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        with self.assertRaises(SupabaseConnectionError):
            get_client()

    def test_get_client_returns_singleton(self) -> None:
        os.environ["SUPABASE_URL"] = "https://x.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "k"
        c1 = get_client()
        c2 = get_client()
        self.assertIs(c1, c2)

    def test_reset_singleton_clears(self) -> None:
        os.environ["SUPABASE_URL"] = "https://x.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "k"
        c1 = get_client()
        reset_singleton()
        c2 = get_client()
        self.assertIsNot(c1, c2)


# ══════════════════════════════════════════════════════════════════════════════
#  pgvector constants
# ══════════════════════════════════════════════════════════════════════════════

class TestPgvectorConstants(unittest.TestCase):
    """EMBEDDING_DIM and DDL dict completeness."""

    def test_embedding_dim(self) -> None:
        self.assertEqual(EMBEDDING_DIM, 384)

    def test_all_tables_in_table_ddl(self) -> None:
        for t in _TABLES:
            self.assertIn(t, TABLE_DDL)

    def test_all_tables_in_index_ddl(self) -> None:
        for t in _TABLES:
            self.assertIn(t, INDEX_DDL)

    def test_all_tables_in_match_function_ddl(self) -> None:
        for t in _TABLES:
            self.assertIn(t, MATCH_FUNCTION_DDL)

    def test_table_ddl_contains_vector_dim(self) -> None:
        for t, ddl in TABLE_DDL.items():
            self.assertIn(f"VECTOR({EMBEDDING_DIM})", ddl, msg=f"table={t}")

    def test_index_ddl_uses_hnsw(self) -> None:
        for t, ddl in INDEX_DDL.items():
            self.assertIn("hnsw", ddl.lower(), msg=f"table={t}")

    def test_index_ddl_uses_cosine_ops(self) -> None:
        for t, ddl in INDEX_DDL.items():
            self.assertIn("vector_cosine_ops", ddl, msg=f"table={t}")

    def test_match_function_references_table(self) -> None:
        for t, ddl in MATCH_FUNCTION_DDL.items():
            self.assertIn(t, ddl)

    def test_match_function_sql_helper(self) -> None:
        sql = match_function_sql("guidance_embeddings")
        self.assertIn("guidance_embeddings", sql)
        self.assertIn("384", sql)

    def test_match_function_sql_custom_dim(self) -> None:
        sql = match_function_sql("guidance_embeddings", dim=768)
        self.assertIn("768", sql)

    def test_three_registered_tables(self) -> None:
        self.assertEqual(len(_TABLES), 3)
        self.assertIn("guidance_embeddings", _TABLES)
        self.assertIn("fda_510k_embeddings", _TABLES)
        self.assertIn("project_embeddings", _TABLES)


# ══════════════════════════════════════════════════════════════════════════════
#  EmbeddingRecord
# ══════════════════════════════════════════════════════════════════════════════

class TestEmbeddingRecord(unittest.TestCase):
    """EmbeddingRecord validation and serialisation."""

    def _valid_record(self, table: str = "guidance_embeddings") -> EmbeddingRecord:
        return EmbeddingRecord(
            table=table,
            content="Risk management process for medical devices.",
            embedding=[0.1] * EMBEDDING_DIM,
            metadata={"doc_id": "G123"},
        )

    def test_valid_record_passes_validate(self) -> None:
        rec = self._valid_record()
        rec.validate()  # should not raise

    def test_unknown_table_raises(self) -> None:
        rec = EmbeddingRecord(
            table="nonexistent_table",
            content="text",
            embedding=[0.0] * EMBEDDING_DIM,
        )
        with self.assertRaises(ValueError) as ctx:
            rec.validate()
        self.assertIn("nonexistent_table", str(ctx.exception))

    def test_wrong_embedding_length_raises(self) -> None:
        rec = EmbeddingRecord(
            table="guidance_embeddings",
            content="text",
            embedding=[0.0] * 100,  # wrong length
        )
        with self.assertRaises(ValueError) as ctx:
            rec.validate()
        self.assertIn("384", str(ctx.exception))

    def test_empty_content_raises(self) -> None:
        rec = EmbeddingRecord(
            table="guidance_embeddings",
            content="   ",
            embedding=[0.0] * EMBEDDING_DIM,
        )
        with self.assertRaises(ValueError) as ctx:
            rec.validate()
        self.assertIn("empty", str(ctx.exception))

    def test_to_row_shape(self) -> None:
        rec = self._valid_record()
        row = rec.to_row()
        self.assertIn("content", row)
        self.assertIn("embedding", row)
        self.assertIn("metadata", row)
        self.assertNotIn("table", row)  # table name excluded from row dict

    def test_to_row_preserves_metadata(self) -> None:
        rec = self._valid_record()
        row = rec.to_row()
        self.assertEqual(row["metadata"]["doc_id"], "G123")

    def test_frozen_immutable(self) -> None:
        rec = self._valid_record()
        with self.assertRaises(Exception):
            rec.content = "mutated"  # type: ignore[misc]

    def test_all_tables_accepted(self) -> None:
        for t in _TABLES:
            rec = EmbeddingRecord(
                table=t,
                content="text chunk",
                embedding=[0.0] * EMBEDDING_DIM,
            )
            rec.validate()  # no exception


# ══════════════════════════════════════════════════════════════════════════════
#  SchemaManager
# ══════════════════════════════════════════════════════════════════════════════

def _mock_client() -> MagicMock:
    """Build a mock SupabaseClient with chainable .rpc().execute() and .table().insert().execute()."""
    mc = MagicMock()
    mc.rpc.return_value.execute.return_value = MagicMock()
    mc.table.return_value.insert.return_value.execute.return_value = MagicMock()
    return mc


class TestSchemaManager(unittest.TestCase):
    """SchemaManager DDL application and data helpers."""

    def test_apply_table_calls_rpc(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        mgr.apply_table("guidance_embeddings")
        mc.rpc.assert_called_once()
        sql = mc.rpc.call_args[0][1]["sql"]
        self.assertIn("CREATE TABLE IF NOT EXISTS guidance_embeddings", sql)

    def test_apply_index_calls_rpc(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        mgr.apply_index("fda_510k_embeddings")
        mc.rpc.assert_called_once()
        sql = mc.rpc.call_args[0][1]["sql"]
        self.assertIn("hnsw", sql.lower())

    def test_apply_match_function_calls_rpc(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        mgr.apply_match_function("project_embeddings")
        mc.rpc.assert_called_once()
        sql = mc.rpc.call_args[0][1]["sql"]
        self.assertIn("match_project_embeddings", sql)

    def test_apply_table_unknown_raises(self) -> None:
        mgr = SchemaManager(_mock_client())
        with self.assertRaises(ValueError):
            mgr.apply_table("nonexistent")

    def test_apply_index_unknown_raises(self) -> None:
        mgr = SchemaManager(_mock_client())
        with self.assertRaises(ValueError):
            mgr.apply_index("nonexistent")

    def test_apply_match_function_unknown_raises(self) -> None:
        mgr = SchemaManager(_mock_client())
        with self.assertRaises(ValueError):
            mgr.apply_match_function("nonexistent")

    def test_apply_all_calls_rpc_three_times_per_table(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        mgr.apply_all()
        # 3 tables × 3 calls (table + index + match function) = 9
        self.assertEqual(mc.rpc.call_count, 9)

    def test_apply_all_subset(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        mgr.apply_all(tables=["guidance_embeddings"])
        # 1 table × 3 calls = 3
        self.assertEqual(mc.rpc.call_count, 3)

    def test_insert_calls_supabase_table(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        rec = EmbeddingRecord(
            table="guidance_embeddings",
            content="test chunk",
            embedding=[0.1] * EMBEDDING_DIM,
            metadata={"k": "v"},
        )
        mgr.insert(rec)
        mc.table.assert_called_once_with("guidance_embeddings")
        mc.table.return_value.insert.assert_called_once()
        row = mc.table.return_value.insert.call_args[0][0]
        self.assertEqual(row["content"], "test chunk")

    def test_insert_validates_record(self) -> None:
        mgr = SchemaManager(_mock_client())
        bad_rec = EmbeddingRecord(
            table="guidance_embeddings",
            content="text",
            embedding=[0.0] * 100,  # wrong dim
        )
        with self.assertRaises(ValueError):
            mgr.insert(bad_rec)

    def test_bulk_insert_groups_by_table(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        records = [
            EmbeddingRecord(table="guidance_embeddings", content="a", embedding=[0.0] * EMBEDDING_DIM),
            EmbeddingRecord(table="guidance_embeddings", content="b", embedding=[0.0] * EMBEDDING_DIM),
            EmbeddingRecord(table="fda_510k_embeddings", content="c", embedding=[0.0] * EMBEDDING_DIM),
        ]
        responses = mgr.bulk_insert(records)
        # 2 distinct tables → 2 insert calls
        self.assertEqual(mc.table.call_count, 2)
        self.assertEqual(len(responses), 2)

    def test_bulk_insert_passes_list_for_same_table(self) -> None:
        mc = _mock_client()
        mgr = SchemaManager(mc)
        records = [
            EmbeddingRecord(table="guidance_embeddings", content="a", embedding=[0.0] * EMBEDDING_DIM),
            EmbeddingRecord(table="guidance_embeddings", content="b", embedding=[0.0] * EMBEDDING_DIM),
        ]
        mgr.bulk_insert(records)
        inserted_rows = mc.table.return_value.insert.call_args[0][0]
        self.assertIsInstance(inserted_rows, list)
        self.assertEqual(len(inserted_rows), 2)


if __name__ == "__main__":
    unittest.main()
