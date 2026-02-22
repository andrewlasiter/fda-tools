"""
FDA-232  [GD-002] Sentence-Transformer Embedding Pipeline
==========================================================
Generates 384-dimensional embeddings for FDA guidance chunks using the
``all-MiniLM-L6-v2`` model and upserts them to the ``guidance_chunks``
PostgreSQL table via pgvector.

Usage
-----
python3 guidance_embedder.py [OPTIONS]

  --batch-size N   Chunks per embedding batch (default: 64)
  --db-url URL     PostgreSQL DSN (default: $DATABASE_URL)
  --dry-run        Compute embeddings but do not write to database
  --incremental    Only embed rows where embedding IS NULL (default: True)
  --model NAME     Sentence-transformers model name (default: all-MiniLM-L6-v2)

Pipeline
--------
1. Query guidance_chunks WHERE embedding IS NULL (or all rows if not incremental)
2. Batch content strings through sentence-transformers
3. Upsert embedding vector back to the same row via pgvector UPDATE
4. Report throughput and remaining count

Performance targets (FDA-232 acceptance criteria)
-------------------------------------------------
- > 1000 chunks/minute on CPU  (all-MiniLM-L6-v2 is ~3000 chunks/min on CPU)
- Incremental: skip already-embedded rows
- Batch size 64 balances memory vs throughput
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Optional dependencies ─────────────────────────────────────────────────────

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    _SentenceTransformer = None  # type: ignore[assignment,misc]
    ST_AVAILABLE = False

try:
    import psycopg2 as _psycopg2_module
    from psycopg2.extras import execute_batch as _execute_batch
    PSYCOPG2_AVAILABLE = True
except ImportError:
    _psycopg2_module  = None  # type: ignore[assignment]
    _execute_batch    = None  # type: ignore[assignment]
    PSYCOPG2_AVAILABLE = False

try:
    from tqdm import tqdm as _tqdm
    TQDM_AVAILABLE = True
except ImportError:
    _tqdm = None  # type: ignore[assignment]
    TQDM_AVAILABLE = False

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_MODEL      = "all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 64
EMBEDDING_DIM      = 384


# ── Database helpers ───────────────────────────────────────────────────────────

def _count_unembedded(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM guidance_chunks WHERE embedding IS NULL")
        return cur.fetchone()[0]


def _fetch_unembedded_batch(conn, batch_size: int, offset: int) -> list[tuple[str, str]]:
    """Return (id, content) tuples for un-embedded rows."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content
            FROM   guidance_chunks
            WHERE  embedding IS NULL
            ORDER  BY id
            LIMIT  %s OFFSET %s
            """,
            (batch_size, offset),
        )
        return cur.fetchall()


def _fetch_all_batch(conn, batch_size: int, offset: int) -> list[tuple[str, str]]:
    """Return (id, content) tuples for all rows (incremental=False)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content
            FROM   guidance_chunks
            ORDER  BY id
            LIMIT  %s OFFSET %s
            """,
            (batch_size, offset),
        )
        return cur.fetchall()


def _upsert_embeddings(conn, id_vectors: list[tuple[str, list[float]]]) -> None:
    """Write embedding vectors back to guidance_chunks."""
    sql = "UPDATE guidance_chunks SET embedding = %s::vector WHERE id = %s"
    rows = [(json.dumps(vec), row_id) for row_id, vec in id_vectors]
    with conn.cursor() as cur:
        _execute_batch(cur, sql, rows, page_size=128)  # type: ignore[operator]
    conn.commit()


# ── Embedding pipeline ─────────────────────────────────────────────────────────

def run(
    db_url:      Optional[str] = None,
    model_name:  str           = DEFAULT_MODEL,
    batch_size:  int           = DEFAULT_BATCH_SIZE,
    dry_run:     bool          = False,
    incremental: bool          = True,
) -> dict:
    """
    Run the embedding pipeline.

    Returns summary dict:
        model, total_chunks, embedded_chunks, skipped_chunks, elapsed_seconds,
        chunks_per_minute, dry_run
    """
    db_url = db_url or os.getenv("DATABASE_URL")
    if not db_url and not dry_run:
        raise EnvironmentError(
            "DATABASE_URL not set.  Pass --db-url or set DATABASE_URL."
        )

    if not ST_AVAILABLE:
        raise ImportError(
            "sentence-transformers is required.  "
            "Run: pip install sentence-transformers"
        )

    # ── Load model ────────────────────────────────────────────────────────────
    logger.info("Loading model: %s", model_name)
    model = _SentenceTransformer(model_name)  # type: ignore[operator]
    logger.info("Model loaded (embedding dim: %d)", model.get_sentence_embedding_dimension())

    # ── Connect to DB ─────────────────────────────────────────────────────────
    conn = None
    total_available = 0

    if not dry_run and PSYCOPG2_AVAILABLE and _psycopg2_module is not None:
        conn = _psycopg2_module.connect(db_url)
        total_available = (
            _count_unembedded(conn) if incremental
            else _get_total_count(conn)
        )
        logger.info(
            "Chunks to embed: %d (%s mode)",
            total_available,
            "incremental" if incremental else "full",
        )
    else:
        logger.info("DRY-RUN or psycopg2 unavailable — skipping DB connection")
        total_available = 0

    # ── Embedding loop ────────────────────────────────────────────────────────
    stats = {
        "model":             model_name,
        "total_chunks":      total_available,
        "embedded_chunks":   0,
        "skipped_chunks":    0,
        "elapsed_seconds":   0.0,
        "chunks_per_minute": 0.0,
        "dry_run":           dry_run,
    }

    t_start = time.monotonic()
    offset  = 0

    pbar = _tqdm(total=total_available, unit="chunk", desc="Embedding") if (TQDM_AVAILABLE and _tqdm is not None) else None  # type: ignore[operator]

    while True:
        # Fetch next batch
        if conn:
            fetch_fn = _fetch_unembedded_batch if incremental else _fetch_all_batch
            rows = fetch_fn(conn, batch_size, offset)
        else:
            # Dry-run: generate synthetic rows for timing test
            if offset >= 128:
                break
            rows = [(str(i), f"Synthetic guidance text chunk {i}") for i in range(offset, offset + batch_size)]

        if not rows:
            break

        ids      = [r[0] for r in rows]
        contents = [r[1] for r in rows]

        logger.debug("Embedding batch of %d chunks (offset=%d)", len(rows), offset)

        # Encode
        vectors = model.encode(
            contents,
            batch_size        = batch_size,
            show_progress_bar = False,
            normalize_embeddings = True,
        ).tolist()

        if not dry_run and conn:
            _upsert_embeddings(conn, list(zip(ids, vectors)))

        stats["embedded_chunks"] += len(rows)
        offset += len(rows)

        if pbar:
            pbar.update(len(rows))

    if pbar:
        pbar.close()

    if conn:
        conn.close()

    elapsed                  = time.monotonic() - t_start
    stats["elapsed_seconds"] = round(elapsed, 2)
    stats["chunks_per_minute"] = (
        round(stats["embedded_chunks"] / elapsed * 60, 1)
        if elapsed > 0
        else 0.0
    )

    logger.info(
        "Embedding complete: %d chunks in %.1fs (%.0f chunks/min)",
        stats["embedded_chunks"],
        elapsed,
        stats["chunks_per_minute"],
    )
    return stats


def _get_total_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM guidance_chunks")
        return cur.fetchone()[0]


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Guidance Chunk Embedding Pipeline — all-MiniLM-L6-v2 (FDA-232)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Embedding batch size (default: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="PostgreSQL DSN (overrides DATABASE_URL)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute embeddings but do not write to DB"
    )
    parser.add_argument(
        "--no-incremental", action="store_true",
        help="Re-embed all rows including already-embedded ones"
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Sentence-transformers model (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    stats = run(
        db_url      = args.db_url,
        model_name  = args.model,
        batch_size  = args.batch_size,
        dry_run     = args.dry_run,
        incremental = not args.no_incremental,
    )

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    _cli()
