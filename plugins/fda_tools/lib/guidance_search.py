"""
FDA-233  [GD-003] Guidance Document Semantic Search
====================================================
Provides ``GuidanceSearcher.search(query, top_k, threshold)`` — on-the-fly
sentence-transformer embedding of the query followed by a pgvector cosine
similarity search against the ``guidance_chunks`` table.

Design goals
------------
- P95 latency < 200 ms (model warm, DB local/Supabase)
- Graceful degradation: returns [] when DB or model unavailable
- Model singleton — loaded once per process, reused across calls
- Works with both local PostgreSQL and Supabase (same pgvector schema)

Schema dependency
-----------------
The ``match_guidance`` Postgres function must exist:

    CREATE OR REPLACE FUNCTION match_guidance(
        query_embedding vector(384),
        match_threshold float,
        match_count     int
    )
    RETURNS TABLE (
        id          text,
        doc_id      text,
        doc_title   text,
        doc_url     text,
        chunk_index int,
        content     text,
        similarity  float
    )
    LANGUAGE sql STABLE AS $$
        SELECT
            id, doc_id, doc_title, doc_url, chunk_index, content,
            1 - (embedding <=> query_embedding) AS similarity
        FROM  guidance_chunks
        WHERE 1 - (embedding <=> query_embedding) > match_threshold
        ORDER BY embedding <=> query_embedding
        LIMIT match_count;
    $$;
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Optional dependencies ─────────────────────────────────────────────────────

try:
    from sentence_transformers import SentenceTransformer as _STClass
    _ST_AVAILABLE = True
except ImportError:
    _STClass = None  # type: ignore[assignment,misc]
    _ST_AVAILABLE = False

try:
    import psycopg2 as _psycopg2_module
    _PG_AVAILABLE = True
except ImportError:
    _psycopg2_module = None  # type: ignore[assignment]
    _PG_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_MODEL     = "all-MiniLM-L6-v2"
DEFAULT_TOP_K     = 10
DEFAULT_THRESHOLD = 0.70   # cosine similarity floor (0–1)

# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class GuidanceResult:
    id:          str
    doc_id:      str
    doc_title:   str
    doc_url:     str
    chunk_index: int
    content:     str
    similarity:  float


@dataclass
class SearchResponse:
    query:   str
    top_k:   int
    results: List[GuidanceResult] = field(default_factory=list)
    model:   str = DEFAULT_MODEL
    error:   Optional[str] = None

    @property
    def count(self) -> int:
        return len(self.results)


# ── Model singleton ───────────────────────────────────────────────────────────

_model_instance: Optional[object] = None
_model_name_loaded: str = ""


def _get_model(model_name: str = DEFAULT_MODEL):
    """Return cached SentenceTransformer, loading it the first time."""
    global _model_instance, _model_name_loaded
    if _model_instance is None or _model_name_loaded != model_name:
        if not _ST_AVAILABLE or _STClass is None:
            raise ImportError(
                "sentence-transformers is required for semantic search. "
                "Run: pip install sentence-transformers"
            )
        logger.info("Loading sentence-transformer model: %s", model_name)
        _model_instance = _STClass(model_name)
        _model_name_loaded = model_name
        logger.info("Model loaded")
    return _model_instance


# ── Core searcher ─────────────────────────────────────────────────────────────


class GuidanceSearcher:
    """
    Semantic search over FDA guidance chunks stored in pgvector.

    Parameters
    ----------
    db_url    : PostgreSQL DSN (``postgresql://user:pass@host/db``).
                Falls back to ``DATABASE_URL`` env var if None.
    model_name: sentence-transformers model identifier.
    """

    def __init__(
        self,
        db_url:     Optional[str] = None,
        model_name: str           = DEFAULT_MODEL,
    ) -> None:
        import os
        self._db_url     = db_url or os.getenv("DATABASE_URL")
        self._model_name = model_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query:     str,
        top_k:     int   = DEFAULT_TOP_K,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> SearchResponse:
        """
        Embed *query* and return the top-*top_k* guidance chunks whose
        cosine similarity exceeds *threshold*.

        Returns a :class:`SearchResponse` (empty ``results`` on failure,
        ``error`` field set with message).
        """
        if not query.strip():
            return SearchResponse(query=query, top_k=top_k,
                                  error="Empty query")

        # Embed query
        try:
            model  = _get_model(self._model_name)
            vector = model.encode(  # type: ignore[union-attr]
                [query],
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()[0]
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return SearchResponse(query=query, top_k=top_k,
                                  model=self._model_name,
                                  error=f"Embedding error: {exc}")

        # Query pgvector
        try:
            results = self._query_pgvector(vector, top_k, threshold)
        except Exception as exc:
            logger.warning("pgvector query failed: %s", exc)
            return SearchResponse(query=query, top_k=top_k,
                                  model=self._model_name,
                                  error=f"Database error: {exc}")

        return SearchResponse(
            query=query,
            top_k=top_k,
            results=results,
            model=self._model_name,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _query_pgvector(
        self,
        vector:    list,
        top_k:     int,
        threshold: float,
    ) -> List[GuidanceResult]:
        if not _PG_AVAILABLE or _psycopg2_module is None:
            raise ImportError("psycopg2 not installed")
        if not self._db_url:
            raise EnvironmentError(
                "DATABASE_URL not set; pass db_url= or set the env var"
            )

        conn = _psycopg2_module.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, doc_id, doc_title, doc_url,
                           chunk_index, content,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM   guidance_chunks
                    WHERE  1 - (embedding <=> %s::vector) > %s
                    ORDER  BY embedding <=> %s::vector
                    LIMIT  %s
                    """,
                    (
                        json.dumps(vector),
                        json.dumps(vector),
                        threshold,
                        json.dumps(vector),
                        top_k,
                    ),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        return [
            GuidanceResult(
                id=row[0], doc_id=row[1], doc_title=row[2],
                doc_url=row[3], chunk_index=row[4], content=row[5],
                similarity=float(row[6]),
            )
            for row in rows
        ]
