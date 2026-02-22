"""
FDA-220  pgvector Schema: Guidance + 510k + Project Embeddings
==============================================================
SQL DDL constants and helper utilities for the three pgvector tables used by
the Regulatory Intelligence platform.

Tables
------
``guidance_embeddings``   — FDA guidance document chunks (text + metadata)
``fda_510k_embeddings``   — 510(k) submission chunks (title, section, text)
``project_embeddings``    — Per-project NPD document chunks

All tables share the same embedding dimension (``EMBEDDING_DIM = 384``),
produced by the *all-MiniLM-L6-v2* sentence-transformer model.  Each table
has an HNSW index for sub-linear approximate-nearest-neighbour (ANN) search
and a companion stored function ``match_<table>`` consumed by
:func:`~fda_tools.lib.supabase_client.SupabaseClient.vector_search`.

Design
------
``EMBEDDING_DIM``       — constant (384) for all-MiniLM-L6-v2
``TABLE_DDL``           — dict mapping table name → CREATE TABLE SQL
``INDEX_DDL``           — dict mapping table name → CREATE INDEX SQL
``MATCH_FUNCTION_DDL``  — dict mapping table name → match function SQL
``EmbeddingRecord``     — frozen dataclass for a single row ready to insert
``SchemaManager``       — applies DDL via a ``SupabaseClient`` instance

Usage
-----
    from fda_tools.lib.pgvector_schema import SchemaManager, EmbeddingRecord
    from fda_tools.lib.supabase_client import get_client

    mgr = SchemaManager(get_client())
    mgr.apply_all()                      # idempotent — uses IF NOT EXISTS

    record = EmbeddingRecord(
        table="guidance_embeddings",
        content="Risk management process ...",
        embedding=[0.1, 0.2, ...],       # 384 floats
        metadata={"doc_id": "G123", "section": "4.1"},
    )
    mgr.insert(record)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

EMBEDDING_DIM: int = 384
"""Dimensionality for all-MiniLM-L6-v2 sentence embeddings."""

# ── DDL strings ───────────────────────────────────────────────────────────────

# Each CREATE TABLE adds:
#   id         — surrogate PK
#   content    — original text chunk
#   embedding  — pgvector column (vector(384))
#   metadata   — JSONB for flexible filtering
#   created_at — insert timestamp

_TABLE_DDL_TEMPLATE = """
CREATE TABLE IF NOT EXISTS {table} (
    id         BIGSERIAL PRIMARY KEY,
    content    TEXT        NOT NULL,
    embedding  VECTOR({dim}) NOT NULL,
    metadata   JSONB        NOT NULL DEFAULT '{{}}',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
""".strip()

# HNSW index for sub-linear cosine ANN search.
# m=16, ef_construction=64 — sensible defaults for 384-dim embeddings.
_INDEX_DDL_TEMPLATE = """
CREATE INDEX IF NOT EXISTS {table}_embedding_hnsw_idx
    ON {table}
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
""".strip()

# Stored function expected by SupabaseClient.vector_search().
# Returns rows ordered by cosine similarity above match_threshold.
_MATCH_FN_TEMPLATE = """
CREATE OR REPLACE FUNCTION match_{table}(
    query_embedding  VECTOR({dim}),
    match_threshold  FLOAT   DEFAULT 0.75,
    match_count      INT     DEFAULT 10
)
RETURNS TABLE (
    id         BIGINT,
    content    TEXT,
    metadata   JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.content,
        t.metadata,
        1 - (t.embedding <=> query_embedding) AS similarity
    FROM {table} t
    WHERE 1 - (t.embedding <=> query_embedding) >= match_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
""".strip()

# ── Registered tables ─────────────────────────────────────────────────────────

_TABLES = (
    "guidance_embeddings",
    "fda_510k_embeddings",
    "project_embeddings",
)

TABLE_DDL: Dict[str, str] = {
    t: _TABLE_DDL_TEMPLATE.format(table=t, dim=EMBEDDING_DIM)
    for t in _TABLES
}

INDEX_DDL: Dict[str, str] = {
    t: _INDEX_DDL_TEMPLATE.format(table=t)
    for t in _TABLES
}

MATCH_FUNCTION_DDL: Dict[str, str] = {
    t: _MATCH_FN_TEMPLATE.format(table=t, dim=EMBEDDING_DIM)
    for t in _TABLES
}


def match_function_sql(table: str, dim: int = EMBEDDING_DIM) -> str:
    """
    Return the SQL for a ``match_<table>`` stored function.

    Args:
        table: Table name (e.g. ``"guidance_embeddings"``).
        dim:   Embedding dimension (default: ``EMBEDDING_DIM``).

    Returns:
        SQL string that can be executed via ``supabase.rpc`` or ``psycopg2``.
    """
    return _MATCH_FN_TEMPLATE.format(table=table, dim=dim)


# ── Data record ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EmbeddingRecord:
    """
    An immutable row ready to be inserted into one of the embedding tables.

    Attributes:
        table:     Target table name (must be in ``TABLE_DDL``).
        content:   Raw text chunk.
        embedding: Embedding vector as a list of ``EMBEDDING_DIM`` floats.
        metadata:  Arbitrary key/value dict stored as JSONB.
    """
    table:     str
    content:   str
    embedding: List[float]
    metadata:  Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Raise ``ValueError`` if the record is malformed.

        Checks:
        - ``table`` is one of the registered tables.
        - ``embedding`` has exactly ``EMBEDDING_DIM`` dimensions.
        - ``content`` is non-empty.
        """
        if self.table not in TABLE_DDL:
            raise ValueError(
                f"Unknown table '{self.table}'; must be one of {sorted(TABLE_DDL)}"
            )
        if len(self.embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"Expected embedding of length {EMBEDDING_DIM}, "
                f"got {len(self.embedding)} for table '{self.table}'"
            )
        if not self.content.strip():
            raise ValueError("content must not be empty")

    def to_row(self) -> Dict[str, Any]:
        """Return a dict suitable for ``supabase.table(table).insert(row)``."""
        return {
            "content":   self.content,
            "embedding": self.embedding,
            "metadata":  self.metadata,
        }


# ── SchemaManager ─────────────────────────────────────────────────────────────

class SchemaManager:
    """
    Applies pgvector DDL (tables, indexes, functions) via a SupabaseClient.

    All operations are idempotent (``IF NOT EXISTS`` / ``CREATE OR REPLACE``).

    Args:
        client: A connected :class:`~fda_tools.lib.supabase_client.SupabaseClient`.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    # ── DDL application ───────────────────────────────────────────────────────

    def _exec_sql(self, sql: str, label: str) -> None:
        """Execute raw SQL via the ``exec_sql`` RPC function."""
        try:
            self._client.rpc("exec_sql", {"sql": sql}).execute()
            logger.debug("SchemaManager: applied %s", label)
        except Exception as exc:
            logger.error("SchemaManager: failed to apply %s: %s", label, exc)
            raise

    def apply_table(self, table: str) -> None:
        """Create *table* if it does not already exist."""
        if table not in TABLE_DDL:
            raise ValueError(f"Unknown table '{table}'")
        self._exec_sql(TABLE_DDL[table], f"CREATE TABLE {table}")

    def apply_index(self, table: str) -> None:
        """Create the HNSW index on *table* if it does not already exist."""
        if table not in INDEX_DDL:
            raise ValueError(f"Unknown table '{table}'")
        self._exec_sql(INDEX_DDL[table], f"CREATE INDEX {table}_embedding_hnsw_idx")

    def apply_match_function(self, table: str) -> None:
        """Create or replace the ``match_<table>`` stored function."""
        if table not in MATCH_FUNCTION_DDL:
            raise ValueError(f"Unknown table '{table}'")
        self._exec_sql(MATCH_FUNCTION_DDL[table], f"CREATE FUNCTION match_{table}")

    def apply_all(self, tables: Optional[List[str]] = None) -> None:
        """
        Apply tables, indexes, and match functions for all (or specified) tables.

        Args:
            tables: Optional list of table names; defaults to all registered tables.
        """
        targets = tables or list(_TABLES)
        for t in targets:
            self.apply_table(t)
            self.apply_index(t)
            self.apply_match_function(t)
        logger.info("SchemaManager.apply_all: applied %d table(s)", len(targets))

    # ── Data helpers ──────────────────────────────────────────────────────────

    def insert(self, record: EmbeddingRecord) -> Any:
        """
        Insert a validated ``EmbeddingRecord`` into its target table.

        Args:
            record: The record to insert.

        Returns:
            Raw Supabase insert response.

        Raises:
            ValueError: If the record fails validation.
        """
        record.validate()
        return self._client.table(record.table).insert(record.to_row()).execute()

    def bulk_insert(self, records: List[EmbeddingRecord]) -> List[Any]:
        """
        Insert a list of records, validating each before insertion.

        Inserts are grouped by table for efficiency.

        Args:
            records: List of ``EmbeddingRecord`` objects.

        Returns:
            List of Supabase insert responses (one per table group).
        """
        # Group by table
        by_table: Dict[str, List[Dict[str, Any]]] = {}
        for rec in records:
            rec.validate()
            by_table.setdefault(rec.table, []).append(rec.to_row())

        responses = []
        for table_name, rows in by_table.items():
            resp = self._client.table(table_name).insert(rows).execute()
            responses.append(resp)
            logger.debug("SchemaManager.bulk_insert: inserted %d rows into %s", len(rows), table_name)
        return responses
